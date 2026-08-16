# core/cloud_gateway.py
"""
Cloud brain routing with automatic Scavenger Mode fallback to local Ollama.

Providers: local, chatgpt, gemini, grok, copilot
"""

from __future__ import annotations

import os
from typing import Dict, Iterator, List, Optional, Set

from core.model_client import ModelClient, build_athena_messages


PROVIDER_LOCAL = "local"
PROVIDER_CHATGPT = "chatgpt"
PROVIDER_GEMINI = "gemini"
PROVIDER_GROK = "grok"
PROVIDER_COPILOT = "copilot"

VALID_PROVIDERS: Set[str] = {
    PROVIDER_LOCAL,
    PROVIDER_CHATGPT,
    PROVIDER_GEMINI,
    PROVIDER_GROK,
    PROVIDER_COPILOT,
}

SCAVENGER_STATUS = "[SCAVENGER MODE]"

OPENAI_MODEL = "gpt-4o"
GEMINI_MODEL = "gemini-1.5-pro"
GROK_MODEL = os.environ.get("XAI_MODEL", "grok-2")
GROK_BASE_URL = "https://api.x.ai/v1"

CLOUD_REQUEST_TIMEOUT = 90.0


class CloudProviderError(Exception):
    """Raised when a cloud brain fails — triggers Scavenger Mode."""

    def __init__(self, provider: str, cause: Exception):
        self.provider = provider
        self.cause = cause
        super().__init__(f"{provider} unavailable: {cause}")


def normalize_brain_provider(provider: Optional[str]) -> str:
    value = (provider or PROVIDER_LOCAL).lower().strip()
    if value not in VALID_PROVIDERS:
        return PROVIDER_LOCAL
    return value


def is_cloud_provider(provider: str) -> bool:
    return normalize_brain_provider(provider) != PROVIDER_LOCAL


class CloudGateway:
    """Routes chat streams to cloud APIs with strict disaster-recovery fallback."""

    def __init__(self, model_client: Optional[ModelClient] = None):
        self.model_client = model_client or ModelClient()

    def iter_cloud_tokens(
        self,
        provider: str,
        prompt: str,
        history: Optional[List[Dict[str, str]]] = None,
        document_context: str = "",
    ) -> Iterator[str]:
        """
        Stream tokens from the selected cloud brain.
        Raises CloudProviderError on any network/API failure.
        """
        provider = normalize_brain_provider(provider)
        if provider == PROVIDER_LOCAL:
            raise CloudProviderError(provider, ValueError("local is not a cloud provider"))

        dispatch = {
            PROVIDER_CHATGPT: self._stream_openai,
            PROVIDER_COPILOT: self._stream_copilot,
            PROVIDER_GEMINI: self._stream_gemini,
            PROVIDER_GROK: self._stream_grok,
        }
        stream_fn = dispatch.get(provider)
        if stream_fn is None:
            raise CloudProviderError(provider, ValueError(f"unknown provider: {provider}"))

        try:
            yield from stream_fn(prompt, history or [], document_context)
        except CloudProviderError:
            raise
        except Exception as exc:
            raise CloudProviderError(provider, exc) from exc

    def _openai_compatible_messages(
        self,
        prompt: str,
        history: List[Dict[str, str]],
        document_context: str,
    ) -> List[Dict[str, str]]:
        raw = build_athena_messages(prompt, history, document_context)
        converted: List[Dict[str, str]] = []
        for item in raw:
            role = item.get("role", "user")
            if role == "system":
                converted.append({"role": "system", "content": item["content"]})
            elif role in {"user", "assistant"}:
                converted.append({"role": role, "content": item["content"]})
        return converted

    def _stream_openai(
        self,
        prompt: str,
        history: List[Dict[str, str]],
        document_context: str,
    ) -> Iterator[str]:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise CloudProviderError(PROVIDER_CHATGPT, exc) from exc

        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise CloudProviderError(
                PROVIDER_CHATGPT,
                RuntimeError("OPENAI_API_KEY is not configured"),
            )

        try:
            client = OpenAI(api_key=api_key, timeout=CLOUD_REQUEST_TIMEOUT)
            messages = self._openai_compatible_messages(prompt, history, document_context)
            stream = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=messages,
                stream=True,
            )
            for chunk in stream:
                try:
                    delta = chunk.choices[0].delta.content or ""
                except (AttributeError, IndexError, TypeError):
                    delta = ""
                if delta:
                    yield delta
        except CloudProviderError:
            raise
        except Exception as exc:
            raise CloudProviderError(PROVIDER_CHATGPT, exc) from exc

    def _stream_copilot(
        self,
        prompt: str,
        history: List[Dict[str, str]],
        document_context: str,
    ) -> Iterator[str]:
        """
        Copilot route uses the OpenAI SDK against gpt-4o (same transport as ChatGPT).
        """
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise CloudProviderError(PROVIDER_COPILOT, exc) from exc

        api_key = (
            os.environ.get("COPILOT_API_KEY", "").strip()
            or os.environ.get("OPENAI_API_KEY", "").strip()
        )
        if not api_key:
            raise CloudProviderError(
                PROVIDER_COPILOT,
                RuntimeError("COPILOT_API_KEY or OPENAI_API_KEY is not configured"),
            )

        try:
            client = OpenAI(api_key=api_key, timeout=CLOUD_REQUEST_TIMEOUT)
            messages = self._openai_compatible_messages(prompt, history, document_context)
            stream = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=messages,
                stream=True,
            )
            for chunk in stream:
                try:
                    delta = chunk.choices[0].delta.content or ""
                except (AttributeError, IndexError, TypeError):
                    delta = ""
                if delta:
                    yield delta
        except CloudProviderError:
            raise
        except Exception as exc:
            raise CloudProviderError(PROVIDER_COPILOT, exc) from exc

    def _stream_gemini(
        self,
        prompt: str,
        history: List[Dict[str, str]],
        document_context: str,
    ) -> Iterator[str]:
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise CloudProviderError(PROVIDER_GEMINI, exc) from exc

        api_key = (
            os.environ.get("GOOGLE_API_KEY", "").strip()
            or os.environ.get("GEMINI_API_KEY", "").strip()
        )
        if not api_key:
            raise CloudProviderError(
                PROVIDER_GEMINI,
                RuntimeError("GOOGLE_API_KEY or GEMINI_API_KEY is not configured"),
            )

        try:
            client = genai.Client(api_key=api_key)
            raw_messages = build_athena_messages(prompt, history, document_context)
            system_parts: List[str] = []
            contents: List[types.Content] = []

            for item in raw_messages:
                role = item.get("role", "")
                content = item.get("content", "")
                if role == "system":
                    system_parts.append(content)
                elif role == "user":
                    contents.append(
                        types.Content(role="user", parts=[types.Part(text=content)])
                    )
                elif role == "assistant":
                    contents.append(
                        types.Content(role="model", parts=[types.Part(text=content)])
                    )

            if not contents:
                contents.append(
                    types.Content(role="user", parts=[types.Part(text=prompt)])
                )

            system_instruction = "\n\n".join(system_parts).strip() or None
            config_kwargs: Dict[str, object] = {}
            if system_instruction:
                config_kwargs["system_instruction"] = system_instruction

            for chunk in client.models.generate_content_stream(
                model=GEMINI_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(**config_kwargs),
            ):
                if chunk.text:
                    yield chunk.text
        except CloudProviderError:
            raise
        except Exception as exc:
            raise CloudProviderError(PROVIDER_GEMINI, exc) from exc

    def _stream_grok(
        self,
        prompt: str,
        history: List[Dict[str, str]],
        document_context: str,
    ) -> Iterator[str]:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise CloudProviderError(PROVIDER_GROK, exc) from exc

        api_key = os.environ.get("XAI_API_KEY", "").strip()
        if not api_key:
            raise CloudProviderError(
                PROVIDER_GROK,
                RuntimeError("XAI_API_KEY is not configured"),
            )

        try:
            client = OpenAI(
                api_key=api_key,
                base_url=GROK_BASE_URL,
                timeout=CLOUD_REQUEST_TIMEOUT,
            )
            messages = self._openai_compatible_messages(prompt, history, document_context)
            stream = client.chat.completions.create(
                model=GROK_MODEL,
                messages=messages,
                stream=True,
            )
            for chunk in stream:
                try:
                    delta = chunk.choices[0].delta.content or ""
                except (AttributeError, IndexError, TypeError):
                    delta = ""
                if delta:
                    yield delta
        except CloudProviderError:
            raise
        except Exception as exc:
            raise CloudProviderError(PROVIDER_GROK, exc) from exc
