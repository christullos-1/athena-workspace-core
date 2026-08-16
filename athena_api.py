"""
Athena Mobile API — standalone FastAPI server with JWT auth.

Run from the project root:
    python athena_api.py

Then expose port 8000 via your tunnel and connect from Opera mobile.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import secrets
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, Optional

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from core.cloud_gateway import (
    SCAVENGER_STATUS,
    CloudGateway,
    CloudProviderError,
    is_cloud_provider,
    normalize_brain_provider,
)
from core.logic_loop import LogicLoop
from core.model_client import ModelClient
from core.output_sanitize import sanitize_model_output
from core.reasoning_engine import ReasoningEngine
from core.tools.live_web_search import execute_web_search
from core.vault.manual_downloader import download_caliber_manual
from core.vault.pdf_vault import (
    PdfVaultStore,
    VAULT_CACHE,
    VAULT_INDEX_PATH,
    ensure_vault_directory,
    get_vault_cache_stats,
    get_vault_tree_layout,
    is_vault_ready,
    pdf_vault,
    populate_vault_cache_once,
    start_background_vault_sync,
    start_vault_cache_loader,
)
from core.vintage_modern_crossref import run_modern_cross_reference


# ---------------------------------------------------------------------------
# Auth configuration — change these before exposing via a public tunnel
# ---------------------------------------------------------------------------

ATHENA_USERNAME = "athena"
ATHENA_PASSWORD = "mobile_access_2026"
JWT_SECRET = "athena-local-jwt-secret-change-me"
JWT_EXPIRE_SECONDS = 60 * 60 * 24  # 24 hours


# ---------------------------------------------------------------------------
# JWT helpers (stdlib only — HS256)
# ---------------------------------------------------------------------------


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_jwt(payload: Dict[str, Any], secret: str, expires_in_seconds: int) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    full_payload = {
        **payload,
        "iat": now,
        "exp": now + expires_in_seconds,
    }

    header_segment = _b64url_encode(
        json.dumps(header, separators=(",", ":")).encode("utf-8")
    )
    payload_segment = _b64url_encode(
        json.dumps(full_payload, separators=(",", ":")).encode("utf-8")
    )
    signing_input = f"{header_segment}.{payload_segment}".encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    signature_segment = _b64url_encode(signature)
    return f"{header_segment}.{payload_segment}.{signature_segment}"


def verify_jwt(token: str, secret: str) -> Optional[Dict[str, Any]]:
    try:
        header_segment, payload_segment, signature_segment = token.split(".")
    except ValueError:
        return None

    signing_input = f"{header_segment}.{payload_segment}".encode("utf-8")
    expected_signature = hmac.new(
        secret.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()

    if not hmac.compare_digest(_b64url_encode(expected_signature), signature_segment):
        return None

    try:
        payload = json.loads(_b64url_decode(payload_segment))
    except (json.JSONDecodeError, ValueError):
        return None

    if not isinstance(payload, dict):
        return None

    expires_at = payload.get("exp")
    if not isinstance(expires_at, (int, float)) or expires_at < time.time():
        return None

    return payload


UI_TEMPLATE_PATH = Path(__file__).resolve().parent / "core" / "ui" / "athena_shell.html"


def _load_ui_html() -> str:
    return UI_TEMPLATE_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Vault bootstrap — linked to core/vault/pdf_vault.py indexing engine
# ---------------------------------------------------------------------------

vault_store: PdfVaultStore = pdf_vault
_vault_loader_thread = None


def bootstrap_vault_index() -> None:
    """
    Kick off incremental vault sync in a background thread.
    Loads ./vault_index.json instantly when present; pypdf only for changed files.
    """
    global _vault_loader_thread
    ensure_vault_directory()
    _vault_loader_thread = start_vault_cache_loader()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[Athena] Starting vault sync (index: {VAULT_INDEX_PATH})...")
    print("[Athena] Vintage vs. Modern cross-reference active on vault matches.")
    bootstrap_vault_index()
    print("[Athena] FastAPI online — /chat will use VAULT_CACHE when ready.")
    yield
    print(
        "[Athena] Vault status — "
        f"ready={is_vault_ready()}, cached_docs={len(VAULT_CACHE)}"
    )


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Athena API",
    description="Secure mobile API for the Athena reasoning backend.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

bearer_scheme = HTTPBearer(auto_error=False)

model_client = ModelClient()
ollama_client = model_client
reasoning_engine = ReasoningEngine(ollama_client)
cloud_gateway = CloudGateway(model_client)
athena = LogicLoop(model_client)


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class ChatHistoryMessage(BaseModel):
    role: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)


class ChatRequest(BaseModel):
    prompt: Optional[str] = None
    message: Optional[str] = None
    history: list[ChatHistoryMessage] = Field(default_factory=list)
    brain_provider: str = Field(default="local")

    def resolved_prompt(self) -> str:
        value = (self.prompt or self.message or "").strip()
        return value


class ChatResponse(BaseModel):
    response: str


class VaultDownloadRequest(BaseModel):
    caliber: str = Field(..., min_length=1)


class VaultDownloadResponse(BaseModel):
    success: bool
    caliber: str
    message: str
    search_query: Optional[str] = None
    source_url: Optional[str] = None
    source_title: Optional[str] = None
    saved_path: Optional[str] = None
    ingest: Optional[Dict[str, Any]] = None
    errors: Optional[list[str]] = None


def _authenticate_credentials(username: str, password: str) -> LoginResponse:
    username_ok = secrets.compare_digest(username, ATHENA_USERNAME)
    password_ok = secrets.compare_digest(password, ATHENA_PASSWORD)

    if not (username_ok and password_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    token = create_jwt(
        payload={"sub": ATHENA_USERNAME},
        secret=JWT_SECRET,
        expires_in_seconds=JWT_EXPIRE_SECONDS,
    )
    return LoginResponse(access_token=token, expires_in=JWT_EXPIRE_SECONDS)


def require_authenticated_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Dict[str, Any]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header. Use: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = verify_jwt(credentials.credentials, JWT_SECRET)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload



@app.get("/", response_class=HTMLResponse)
def root_ui() -> HTMLResponse:
    return HTMLResponse(content=_load_ui_html())


@app.get("/api/vault/tree")
def vault_tree(_token_payload: Dict[str, Any] = Depends(require_authenticated_user)) -> Dict[str, Any]:
    return get_vault_tree_layout()


@app.post("/api/vault/sync")
def vault_sync(_token_payload: Dict[str, Any] = Depends(require_authenticated_user)) -> Dict[str, str]:
    status = start_background_vault_sync()
    return {"status": status}


@app.post("/api/vault/download", response_model=VaultDownloadResponse)
def vault_download(
    request: VaultDownloadRequest,
    _token_payload: Dict[str, Any] = Depends(require_authenticated_user),
) -> VaultDownloadResponse:
    try:
        result = download_caliber_manual(request.caliber.strip())
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Manual download failed: {exc}",
        ) from exc

    return VaultDownloadResponse(**result)


@app.post("/login", response_model=LoginResponse)
def login(request: LoginRequest) -> LoginResponse:
    return _authenticate_credentials(request.username, request.password)


@app.post("/token", response_model=LoginResponse)
def token(request: LoginRequest) -> LoginResponse:
    return _authenticate_credentials(request.username, request.password)


def _chat_fallback_response(prompt: str, history: list) -> str:
    """
    Non-stream recovery path. Prefer a short model reply; never raise to the client.
    """
    try:
        text = reasoning_engine.process_chat(prompt=prompt, history=history)
        if isinstance(text, str) and text.strip():
            return text.strip()
    except Exception as exc:
        print(f"[Chat Fallback] Non-stream recovery failed: {exc}")

    return (
        "Athena recovered from a streaming interruption. "
        "Please retry with a shorter question if this continues."
    )


def _sse(payload: Dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


WEB_FETCH_TIMEOUT_SECONDS = 6.0


@app.post("/chat")
def chat(
    request: ChatRequest,
    _token_payload: Dict[str, Any] = Depends(require_authenticated_user),
) -> StreamingResponse:
    prompt = request.resolved_prompt()
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Prompt cannot be empty",
        )

    brain_provider = normalize_brain_provider(request.brain_provider)
    history = [
        {"role": item.role, "content": item.content}
        for item in request.history
    ]

    async def event_stream():
        emitted_tokens = False
        loop = asyncio.get_running_loop()
        plan = reasoning_engine.get_stream_plan(prompt)

        web_payload: Any = None
        if plan["needs_web"]:
            try:
                if plan["web_kind"] == "modern":
                    web_payload = await asyncio.wait_for(
                        asyncio.to_thread(run_modern_cross_reference, prompt),
                        timeout=WEB_FETCH_TIMEOUT_SECONDS,
                    )
                elif plan["web_kind"] == "live":
                    web_payload = await asyncio.wait_for(
                        asyncio.to_thread(execute_web_search, prompt, 5),
                        timeout=WEB_FETCH_TIMEOUT_SECONDS,
                    )
            except asyncio.TimeoutError:
                print("[Chat Stream] Web fetch timeout — continuing single-pass stream")
            except Exception as exc:
                print(f"[Chat Stream] Web fetch failed: {exc}")

        user_prompt, stream_history, document_context = (
            reasoning_engine.prepare_unified_stream(
                prompt,
                history,
                plan,
                web_payload,
            )
        )

        token_queue: asyncio.Queue[tuple[str, Any]] = asyncio.Queue()

        def _run_brain_pass() -> None:
            try:
                if is_cloud_provider(brain_provider):
                    try:
                        for token in reasoning_engine.iter_cloud_tokens(
                            brain_provider,
                            user_prompt,
                            stream_history,
                            document_context,
                            cloud_gateway,
                        ):
                            loop.call_soon_threadsafe(
                                token_queue.put_nowait,
                                ("token", token),
                            )
                    except CloudProviderError as exc:
                        vault_stats = get_vault_cache_stats()
                        doc_count = vault_stats.get("document_count", 0)
                        print(
                            f"[SCAVENGER MODE] {brain_provider} failed ({exc.cause}) "
                            f"— falling back to local Llama3 + {doc_count} vault docs"
                        )
                        loop.call_soon_threadsafe(
                            token_queue.put_nowait,
                            (
                                "status",
                                {
                                    "mode": SCAVENGER_STATUS,
                                    "brain_provider": brain_provider,
                                    "vault_documents": doc_count,
                                },
                            ),
                        )
                        for token in reasoning_engine.iter_scavenger_tokens(
                            user_prompt,
                            stream_history,
                            document_context,
                        ):
                            loop.call_soon_threadsafe(
                                token_queue.put_nowait,
                                ("token", token),
                            )
                else:
                    for token in reasoning_engine.iter_ollama_tokens(
                        user_prompt,
                        stream_history,
                        document_context,
                    ):
                        loop.call_soon_threadsafe(
                            token_queue.put_nowait,
                            ("token", token),
                        )
            except BaseException as exc:
                loop.call_soon_threadsafe(token_queue.put_nowait, ("error", exc))
            finally:
                loop.call_soon_threadsafe(
                    token_queue.put_nowait,
                    ("phase_done", "complete"),
                )

        threading.Thread(
            target=_run_brain_pass,
            name=f"chat-stream-{brain_provider}",
            daemon=True,
        ).start()

        try:
            while True:
                kind, payload = await token_queue.get()
                if kind == "token":
                    emitted_tokens = True
                    yield _sse({"token": payload})
                    await asyncio.sleep(0)
                elif kind == "status":
                    yield _sse({"status": payload})
                    await asyncio.sleep(0)
                elif kind == "error":
                    raise payload
                elif kind == "phase_done":
                    break

            if not emitted_tokens:
                print("[Chat Stream] Empty stream — using non-stream JSON fallback")
                fallback = sanitize_model_output(
                    await asyncio.to_thread(_chat_fallback_response, prompt, history),
                    prompt=prompt,
                )
                if fallback:
                    yield _sse({"token": fallback})

            yield _sse({"done": True})
        except Exception as exc:
            print(f"[Chat Stream] Stream failed ({exc}) — using non-stream JSON fallback")
            if not emitted_tokens:
                fallback = sanitize_model_output(
                    await asyncio.to_thread(_chat_fallback_response, prompt, history),
                    prompt=prompt,
                )
                if fallback:
                    yield _sse({"token": fallback})
            yield _sse({"done": True})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    uvicorn.run(
        "athena_api:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
