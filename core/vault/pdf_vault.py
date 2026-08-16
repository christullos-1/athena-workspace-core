# core/vault/pdf_vault.py

import hashlib
import json
import os
import re
import threading
import time
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple

try:
    from pypdf import PdfReader
except ImportError as exc:
    raise ImportError(
        "pypdf is required for the PDF vault. Install with: pip install pypdf"
    ) from exc


VAULT_DIR = "./athena_vault/"
VAULT_INDEX_PATH = "./vault_index.json"
VAULT_INDEX_VERSION = 1

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".text"}

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "could", "do", "does",
    "for", "from", "had", "has", "have", "how", "i", "if", "in", "into", "is", "it",
    "its", "me", "my", "of", "on", "or", "our", "should", "tell", "that", "the",
    "their", "them", "there", "these", "this", "to", "was", "we", "what", "when",
    "where", "which", "who", "why", "will", "with", "you", "your",
}

# ---------------------------------------------------------------------------
# Global startup cache — populated once at server boot, read-only during /chat
# ---------------------------------------------------------------------------

VAULT_CACHE: Dict[str, str] = {}
VAULT_STRUCTURE: Dict[str, Dict[str, str]] = {}
VAULT_TERM_INDEX: Set[str] = set()
VAULT_PARAGRAPH_INDEX: List[Tuple[str, str, Set[str]]] = []
VAULT_LOADING: bool = False
VAULT_READY: bool = False

_vault_lock = threading.Lock()


def ensure_vault_directory() -> Path:
    vault_path = Path(VAULT_DIR)
    vault_path.mkdir(parents=True, exist_ok=True)
    return vault_path


def is_vault_ready() -> bool:
    return VAULT_READY and bool(VAULT_CACHE)


def is_vault_loading() -> bool:
    return VAULT_LOADING


def _is_supported_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in SUPPORTED_EXTENSIONS


def _file_md5(file_path: Path) -> str:
    digest = hashlib.md5()
    with open(file_path, "rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _file_mtime(file_path: Path) -> float:
    return file_path.stat().st_mtime


def _folder_key(vault_root: Path, file_path: Path) -> str:
    relative_parent = file_path.relative_to(vault_root).parent
    if str(relative_parent) == ".":
        return "root"
    return str(relative_parent).replace("\\", "/")


def _extract_document_text(file_path: Path) -> str:
    suffix = file_path.suffix.lower()

    if suffix == ".pdf":
        return _extract_pdf_text(file_path)

    try:
        return file_path.read_text(encoding="utf-8", errors="ignore").strip()
    except OSError:
        return ""


def _extract_pdf_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    page_text: List[str] = []

    for page in reader.pages:
        extracted = page.extract_text() or ""
        if extracted.strip():
            page_text.append(extracted.strip())

    return "\n\n".join(page_text).strip()


def _extract_search_terms(text: str) -> Set[str]:
    words = re.findall(r"\b[a-z0-9][a-z0-9\-_/]{2,}\b", text.lower())
    return {word for word in words if word not in STOP_WORDS}


def _split_paragraphs(text: str) -> List[str]:
    chunks = re.split(r"\n\s*\n+", text)
    return [chunk.strip() for chunk in chunks if chunk.strip()]


def _build_term_index(documents: Dict[str, str]) -> Set[str]:
    terms: Set[str] = set()
    for doc_text in documents.values():
        terms.update(_extract_search_terms(doc_text))
    return terms


def _build_paragraph_index(
    documents: Dict[str, str],
) -> List[Tuple[str, str, Set[str]]]:
    index: List[Tuple[str, str, Set[str]]] = []

    for source_path, doc_text in documents.items():
        if not doc_text.strip():
            continue

        for paragraph in _split_paragraphs(doc_text):
            if len(paragraph) < 40:
                continue
            index.append((
                source_path,
                paragraph,
                _extract_search_terms(paragraph),
            ))

    return index


def _structure_from_documents(documents: Dict[str, str]) -> Dict[str, Dict[str, str]]:
    vault_path = ensure_vault_directory()
    structure: Dict[str, Dict[str, str]] = {}

    for relative_path, content in documents.items():
        file_path = vault_path / Path(relative_path)
        folder_name = _folder_key(vault_path, file_path)
        structure.setdefault(folder_name, {})[relative_path] = content

    return structure


def load_vault_index_from_disk() -> Dict[str, Any]:
    index_path = Path(VAULT_INDEX_PATH)
    if not index_path.exists():
        return {}

    try:
        with open(index_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            return {}
        if data.get("version") != VAULT_INDEX_VERSION:
            print("[Vault Warning] vault_index.json version mismatch — rebuilding.")
            return {}
        return data
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[Vault Warning] Failed to read vault_index.json: {exc}")
        return {}


def save_vault_index_to_disk(
    documents: Dict[str, Dict[str, Any]],
    file_registry: Dict[str, Dict[str, Any]],
) -> None:
    payload = {
        "version": VAULT_INDEX_VERSION,
        "saved_at": time.time(),
        "documents": documents,
        "file_registry": file_registry,
    }

    index_path = Path(VAULT_INDEX_PATH)
    temp_path = index_path.with_suffix(".json.tmp")

    with open(temp_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False)

    temp_path.replace(index_path)


def hot_ingest_vault_file(relative_path: str) -> Dict[str, Any]:
    """
    Hot-index a single vault file into vault_index.json and VAULT_CACHE.
    Does not run a full os.walk crawl.
    """
    vault_path = ensure_vault_directory()
    file_path = vault_path / Path(relative_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Vault file not found: {relative_path}")

    if not _is_supported_file(file_path.name):
        raise ValueError(f"Unsupported file type: {file_path.name}")

    disk_index = load_vault_index_from_disk()
    documents_meta: Dict[str, Dict[str, Any]] = dict(disk_index.get("documents", {}))
    registry: Dict[str, Dict[str, Any]] = dict(disk_index.get("file_registry", {}))

    seen_hashes: Dict[str, str] = {}
    for path, meta in documents_meta.items():
        content_hash = meta.get("content_hash")
        if content_hash:
            seen_hashes[content_hash] = path

    current_mtime = _file_mtime(file_path)
    content_hash = _file_md5(file_path)

    if content_hash in seen_hashes:
        canonical_path = seen_hashes[content_hash]
        registry[relative_path] = {
            "mtime": current_mtime,
            "content_hash": content_hash,
            "status": "duplicate",
            "canonical_path": canonical_path,
        }
        save_vault_index_to_disk(documents_meta, registry)
        canonical_text = {
            path: meta.get("text", "") for path, meta in documents_meta.items()
        }
        _apply_memory_cache(_structure_from_documents(canonical_text))
        return {
            "status": "duplicate",
            "relative_path": relative_path,
            "canonical_path": canonical_path,
        }

    try:
        text = _extract_document_text(file_path)
    except Exception as exc:
        raise ValueError(f"Failed to parse PDF: {exc}") from exc

    folder_name = _folder_key(vault_path, file_path)
    documents_meta[relative_path] = {
        "mtime": current_mtime,
        "content_hash": content_hash,
        "folder": folder_name,
        "text": text,
    }
    registry[relative_path] = {
        "mtime": current_mtime,
        "content_hash": content_hash,
        "status": "canonical",
        "canonical_path": relative_path,
    }

    save_vault_index_to_disk(documents_meta, registry)
    canonical_text = {
        path: meta.get("text", "") for path, meta in documents_meta.items()
    }
    _apply_memory_cache(_structure_from_documents(canonical_text))

    print(f"[Vault] Hot-ingested: {relative_path} ({len(text)} chars)")

    return {
        "status": "indexed",
        "relative_path": relative_path,
        "folder": folder_name,
        "characters": len(text),
    }


def sync_vault_documents_incremental() -> Dict[str, Dict[str, str]]:
    """
    Incremental vault sync:
    - Load vault_index.json instantly when present
    - os.walk only to compare mtimes
    - pypdf / MD5 only for new or modified files
    """
    vault_path = ensure_vault_directory()
    disk_index = load_vault_index_from_disk()

    cached_documents: Dict[str, Dict[str, Any]] = disk_index.get("documents", {})
    cached_registry: Dict[str, Dict[str, Any]] = disk_index.get("file_registry", {})

    new_documents_meta: Dict[str, Dict[str, Any]] = {}
    new_registry: Dict[str, Dict[str, Any]] = {}
    canonical_text: Dict[str, str] = {}
    seen_hashes: Dict[str, str] = {}

    scanned_paths: Set[str] = set()
    parsed_count = 0
    reused_count = 0

    if disk_index:
        print("[Vault] Loaded vault_index.json — checking for incremental updates...")
    else:
        print("[Vault] No vault_index.json found — performing full vault crawl...")

    for root, _, files in os.walk(vault_path):
        for filename in sorted(files):
            if not _is_supported_file(filename):
                continue

            file_path = Path(root) / filename
            relative_path = file_path.relative_to(vault_path).as_posix()
            scanned_paths.add(relative_path)

            try:
                current_mtime = _file_mtime(file_path)
            except OSError:
                print(f"[Vault Warning] Unreadable file skipped: {relative_path}")
                continue

            registry_entry = cached_registry.get(relative_path)
            if (
                registry_entry
                and registry_entry.get("mtime") == current_mtime
                and registry_entry.get("status") == "canonical"
                and relative_path in cached_documents
            ):
                canonical_path = relative_path
                doc_entry = cached_documents[canonical_path]
                content_hash = doc_entry.get("content_hash") or registry_entry.get("content_hash")
                text = doc_entry.get("text", "")

                if content_hash and content_hash in seen_hashes:
                    existing = seen_hashes[content_hash]
                    new_registry[relative_path] = {
                        "mtime": current_mtime,
                        "content_hash": content_hash,
                        "status": "duplicate",
                        "canonical_path": existing,
                    }
                    print(
                        "[Vault Warning] Duplicate skipped: "
                        f"{relative_path} is identical to {existing}"
                    )
                    reused_count += 1
                    continue

                if content_hash:
                    seen_hashes[content_hash] = canonical_path

                folder_name = doc_entry.get("folder") or _folder_key(vault_path, file_path)
                new_documents_meta[canonical_path] = {
                    "mtime": current_mtime,
                    "content_hash": content_hash,
                    "folder": folder_name,
                    "text": text,
                }
                new_registry[relative_path] = {
                    "mtime": current_mtime,
                    "content_hash": content_hash,
                    "status": "canonical",
                    "canonical_path": canonical_path,
                }
                canonical_text[canonical_path] = text
                reused_count += 1
                continue

            if (
                registry_entry
                and registry_entry.get("mtime") == current_mtime
                and registry_entry.get("status") == "duplicate"
            ):
                new_registry[relative_path] = dict(registry_entry)
                reused_count += 1
                continue

            try:
                content_hash = _file_md5(file_path)
            except OSError:
                print(f"[Vault Warning] Unreadable file skipped: {relative_path}")
                continue

            if content_hash in seen_hashes:
                original_path = seen_hashes[content_hash]
                new_registry[relative_path] = {
                    "mtime": current_mtime,
                    "content_hash": content_hash,
                    "status": "duplicate",
                    "canonical_path": original_path,
                }
                print(
                    "[Vault Warning] Duplicate skipped: "
                    f"{relative_path} is identical to {original_path}"
                )
                parsed_count += 1
                continue

            try:
                text = _extract_document_text(file_path)
            except Exception:
                print(f"[Vault Warning] Failed to parse: {relative_path}")
                text = ""

            seen_hashes[content_hash] = relative_path
            folder_name = _folder_key(vault_path, file_path)

            new_documents_meta[relative_path] = {
                "mtime": current_mtime,
                "content_hash": content_hash,
                "folder": folder_name,
                "text": text,
            }
            new_registry[relative_path] = {
                "mtime": current_mtime,
                "content_hash": content_hash,
                "status": "canonical",
                "canonical_path": relative_path,
            }
            canonical_text[relative_path] = text
            parsed_count += 1

    removed_count = len(set(cached_registry.keys()) - scanned_paths)
    if removed_count:
        print(f"[Vault] Removed {removed_count} stale index entr(y/ies).")

    save_vault_index_to_disk(new_documents_meta, new_registry)

    print(
        f"[Vault] Index sync complete — reused {reused_count}, "
        f"parsed {parsed_count}, canonical {len(canonical_text)}."
    )

    return _structure_from_documents(canonical_text)


def load_vault_documents() -> Dict[str, Dict[str, str]]:
    """Backward-compatible entry point for full/incremental vault sync."""
    return sync_vault_documents_incremental()


def flatten_vault_structure(structure: Dict[str, Dict[str, str]]) -> Dict[str, str]:
    flat: Dict[str, str] = {}
    for documents in structure.values():
        flat.update(documents)
    return flat


def _apply_memory_cache(structure: Dict[str, Dict[str, str]]) -> None:
    global VAULT_CACHE, VAULT_STRUCTURE, VAULT_TERM_INDEX, VAULT_PARAGRAPH_INDEX, VAULT_READY

    cache = flatten_vault_structure(structure)
    term_index = _build_term_index(cache)
    paragraph_index = _build_paragraph_index(cache)

    with _vault_lock:
        VAULT_STRUCTURE = structure
        VAULT_CACHE = cache
        VAULT_TERM_INDEX = term_index
        VAULT_PARAGRAPH_INDEX = paragraph_index
        VAULT_READY = True


def populate_vault_cache_once() -> None:
    """
    Build VAULT_CACHE at server boot using vault_index.json when available.
    Heavy pypdf work runs only for new or mtime-changed files.
    """
    global VAULT_LOADING, VAULT_READY, VAULT_CACHE, VAULT_STRUCTURE, VAULT_TERM_INDEX, VAULT_PARAGRAPH_INDEX

    with _vault_lock:
        if VAULT_READY:
            return

        VAULT_LOADING = True
        VAULT_READY = False

    try:
        ensure_vault_directory()
        structure = sync_vault_documents_incremental()
        _apply_memory_cache(structure)

        print(
            f"[Vault] VAULT_CACHE ready — {len(VAULT_CACHE)} unique document(s), "
            f"{len(VAULT_STRUCTURE)} folder group(s), "
            f"{len(VAULT_PARAGRAPH_INDEX)} indexed paragraph(s)."
        )
    except Exception as exc:
        with _vault_lock:
            VAULT_CACHE = {}
            VAULT_STRUCTURE = {}
            VAULT_TERM_INDEX = set()
            VAULT_PARAGRAPH_INDEX = []
            VAULT_READY = False
        print(f"[Vault Warning] Cache build failed: {exc}")
    finally:
        with _vault_lock:
            VAULT_LOADING = False


def start_vault_cache_loader() -> threading.Thread:
    thread = threading.Thread(
        target=populate_vault_cache_once,
        name="vault-cache-loader",
        daemon=True,
    )
    thread.start()
    return thread


def _prompt_matches_cache(prompt: str) -> bool:
    if not VAULT_CACHE or not VAULT_TERM_INDEX:
        return False

    prompt_terms = _extract_search_terms(prompt)
    if not prompt_terms:
        return False

    return bool(prompt_terms & VAULT_TERM_INDEX)


# Hard cap for vault grounding payload — never inject full file blocks.
MAX_VAULT_PARAGRAPHS = 3
MAX_VAULT_CONTEXT_WORDS = 300


def _count_words(text: str) -> int:
    return len(re.findall(r"\S+", text or ""))


def _trim_to_word_budget(text: str, max_words: int) -> str:
    words = re.findall(r"\S+", text or "")
    if not words or max_words <= 0:
        return ""
    if len(words) <= max_words:
        return " ".join(words)
    return f"{' '.join(words[:max_words])}…"


def _trim_paragraph(text: str, max_words: int) -> str:
    cleaned = " ".join((text or "").split())
    return _trim_to_word_budget(cleaned, max_words)


def _extract_paragraphs_from_index(
    prompt: str,
    max_paragraphs: int = MAX_VAULT_PARAGRAPHS,
    max_words: int = MAX_VAULT_CONTEXT_WORDS,
) -> List[Tuple[str, str]]:
    """
    Return only the top matching paragraphs, capped at max_words total.
    Never returns full document bodies or folder dumps.
    """
    prompt_terms = _extract_search_terms(prompt)
    if not prompt_terms or not VAULT_PARAGRAPH_INDEX:
        return []

    scored: List[Tuple[int, int, str, str]] = []

    for source_path, paragraph, paragraph_terms in VAULT_PARAGRAPH_INDEX:
        overlap = prompt_terms & paragraph_terms
        if overlap:
            scored.append((len(overlap), -len(paragraph), source_path, paragraph))

    # Stronger overlap first; tie-break toward shorter, more precise paragraphs.
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)

    selected: List[Tuple[str, str]] = []
    seen_paragraphs = set()
    used_words = 0

    for _, _, source_path, paragraph in scored:
        remaining_words = max_words - used_words
        if remaining_words <= 15:
            break

        key = paragraph[:120]
        if key in seen_paragraphs:
            continue
        seen_paragraphs.add(key)

        snippet = _trim_paragraph(paragraph, remaining_words)
        if not snippet:
            continue

        selected.append((source_path, snippet))
        used_words += _count_words(snippet)
        if len(selected) >= max_paragraphs or used_words >= max_words:
            break

    return selected


# ---------------------------------------------------------------------------
# AWI library catalog / index intelligence
# ---------------------------------------------------------------------------

CATALOG_SOURCE_MARKERS = (
    "awi_library",
    "library index",
    "libraryauthor",
    "librarytitle",
)

LITERATURE_REFTXT_PREAMBLE = """
LOCAL DOCUMENT REFTXT — LIBRARY INDEX / LITERATURE CROSS-REFERENCE:
The entries below are NOT procedural steps. They are authoritative source
citations (book titles, authors, catalog references) from the AWI vault index
matching the user's query.

LITERATURE CROSS-REFERENCE (mandatory):
1. Treat each cited title and author as an authoritative horological source text.
2. BRAIN SYNTHESIS: Draw on your deep training knowledge of those specific books,
   schools, and techniques (e.g. Abbott's Watchmaker, Glashütte curricula,
   Detent escapement repair texts) to produce the actual detailed mechanical work.
3. OUTPUT ENFORCEMENT: NEVER quote, echo, or display raw catalog codes, CALL numbers,
   tab-separated card strings, PRTFLAG fields, ISBN metadata, or index row data.
4. Deliver ONLY a crisp watchmaker's bench checklist — numbered steps, required tools,
   measurements, tolerances, and safety notes — translated from the historical baseline
   methods those sources represent.
"""

MANUAL_REFTXT_PREAMBLE = """
LOCAL DOCUMENT REFTXT — TECHNICAL MANUAL EXCERPTS:
Use these matching manual paragraphs as primary grounding for the user's prompt.

OUTPUT ENFORCEMENT: Translate into a crisp watchmaker's bench checklist. Never dump
raw index rows, catalog card strings, or CALL codes to the user.
"""


def _is_catalog_index_source(source_path: str) -> bool:
    normalized = source_path.lower().replace("\\", "/")
    return any(marker in normalized for marker in CATALOG_SOURCE_MARKERS)


def _looks_like_catalog_row(line: str) -> bool:
    stripped = line.strip()
    if not stripped or stripped.startswith("CALL1"):
        return False
    if "\t" not in stripped:
        return False

    parts = stripped.split("\t")
    if len(parts) < 8:
        return False

    first_col = parts[0].strip()
    if re.match(r"^[A-Z]?\d{3,4}$", first_col):
        return True
    if stripped.endswith("TRUE") and stripped.count("\t") >= 10:
        return True
    return False


def _looks_like_catalog_content(text: str) -> bool:
    if "CALL1\tCALL2\tCALL3" in text:
        return True
    sample_lines = text.split("\n")[:30]
    catalog_rows = sum(1 for line in sample_lines if _looks_like_catalog_row(line))
    return catalog_rows >= 3


def _parse_awi_catalog_line(line: str) -> Optional[Tuple[str, str]]:
    stripped = line.strip()
    if not _looks_like_catalog_row(stripped):
        return None

    parts = stripped.split("\t")
    author = parts[3].strip().strip('"').strip() if len(parts) > 3 else ""

    skip_tokens = {
        "true", "restricted", "b", "m", "reprint",
        "restricted- no circulation!", "restricted-numbered copy #1399",
    }

    title_parts: List[str] = []
    for index in (4, 5, 6):
        if index >= len(parts):
            continue
        value = parts[index].strip().strip('"').strip()
        if not value:
            continue
        lower = value.lower()
        if lower in skip_tokens:
            continue
        if re.fullmatch(r"C\.\d+", value, re.IGNORECASE):
            continue
        if re.fullmatch(r"[A-Z]?\d{3,4}", value):
            continue
        if value.endswith("TRUE"):
            continue
        if any(value in existing or existing in value for existing in title_parts):
            continue
        title_parts.append(value)

    title = re.sub(r"\s+", " ", " ".join(title_parts)).strip()
    author = re.sub(r"\s+", " ", author).strip()

    # Subject tags (e.g. DETENT) sometimes occupy the author column in AWI rows.
    if author and "," not in author and len(author.split()) == 1 and author.isupper():
        if len(author) <= 12:
            author = ""

    if not title and not author:
        return None
    if len(title) < 4 and len(author) < 4:
        return None
    return author, title


def _extract_literature_refs_from_catalog(
    paragraphs: List[Tuple[str, str]],
    prompt: str,
    max_refs: int = MAX_VAULT_PARAGRAPHS,
) -> List[Dict[str, str]]:
    prompt_terms = _extract_search_terms(prompt)
    seen: set[Tuple[str, str]] = set()
    scored_refs: List[Tuple[int, Dict[str, str]]] = []

    for source_path, paragraph in paragraphs:
        is_catalog = _is_catalog_index_source(source_path) or _looks_like_catalog_content(
            paragraph
        )
        if not is_catalog:
            continue

        for line in paragraph.split("\n"):
            parsed = _parse_awi_catalog_line(line)
            if not parsed:
                continue

            author, title = parsed
            combined = f"{author} {title}"
            entry_terms = _extract_search_terms(combined)
            overlap = len(prompt_terms & entry_terms) if prompt_terms else 1
            if prompt_terms and overlap == 0:
                continue

            key = (author.lower(), title.lower())
            if key in seen:
                continue
            seen.add(key)

            scored_refs.append(
                (
                    overlap,
                    {
                        "author": author,
                        "title": title,
                        "source": Path(source_path).name,
                    },
                )
            )

    scored_refs.sort(key=lambda item: item[0], reverse=True)
    return [entry for _, entry in scored_refs[:max_refs]]


def _paragraphs_are_catalog_index(paragraphs: List[Tuple[str, str]]) -> bool:
    if not paragraphs:
        return False

    catalog_hits = 0
    for source_path, paragraph in paragraphs:
        if _is_catalog_index_source(source_path) or _looks_like_catalog_content(paragraph):
            catalog_hits += 1
    return catalog_hits >= max(1, len(paragraphs) // 2)


def format_literature_reftxt(refs: List[Dict[str, str]]) -> str:
    if not refs:
        return ""

    lines = [LITERATURE_REFTXT_PREAMBLE.strip(), "", "Authoritative sources located:"]
    for index, ref in enumerate(refs, start=1):
        author = ref.get("author", "").strip()
        title = ref.get("title", "").strip()
        source = ref.get("source", "").strip()

        citation = title or "Untitled reference"
        if author:
            citation = f"{citation} — {author}"

        lines.append(f"[{index}] {citation}")
        if source:
            lines.append(f"    Vault index: {source}")

    lines.extend(["", "Synthesize bench procedures from these sources now."])
    return "\n".join(lines).strip()


def format_document_reftxt(
    paragraphs: List[Tuple[str, str]],
    prompt: str = "",
) -> str:
    if not paragraphs:
        return ""

    literature_refs = _extract_literature_refs_from_catalog(paragraphs, prompt)
    if literature_refs:
        context = format_literature_reftxt(literature_refs)
        print(
            f"[Vault RAG] Literature mode — {len(literature_refs)} source citation(s) "
            f"from catalog index"
        )
        return context

    if _paragraphs_are_catalog_index(paragraphs):
        # Catalog matched but no clean refs parsed — still block raw card output.
        context = format_literature_reftxt(
            [
                {
                    "author": "",
                    "title": "Matching AWI library index entries",
                    "source": Path(paragraphs[0][0]).name,
                }
            ]
        )
        return context

    lines = [MANUAL_REFTXT_PREAMBLE.strip(), ""]

    for index, (source_path, paragraph) in enumerate(paragraphs, start=1):
        lines.extend([
            f"[{index}] Source: {Path(source_path).name}",
            paragraph,
            "",
        ])

    return "\n".join(lines).strip()


def get_document_context_from_cache(prompt: str) -> str:
    if VAULT_LOADING or not VAULT_READY or not VAULT_CACHE:
        return ""

    try:
        if not _prompt_matches_cache(prompt):
            return ""

        paragraphs = _extract_paragraphs_from_index(
            prompt,
            max_paragraphs=MAX_VAULT_PARAGRAPHS,
            max_words=MAX_VAULT_CONTEXT_WORDS,
        )
        context = format_document_reftxt(paragraphs, prompt=prompt)
        word_total = _count_words(context)
        if context:
            print(
                f"[Vault RAG] {len(paragraphs)} paragraph(s), "
                f"{word_total} word(s) (cap {MAX_VAULT_CONTEXT_WORDS})"
            )
        return context
    except Exception as exc:
        print(f"[Vault Warning] Cache lookup skipped: {exc}")
        return ""


def vault_context_matched(prompt: str) -> bool:
    """Fast check — True when prompt terms hit the pre-loaded VAULT_CACHE."""
    if VAULT_LOADING or not VAULT_READY or not VAULT_CACHE:
        return False

    try:
        return _prompt_matches_cache(prompt)
    except Exception:
        return False


def iter_vault_grounding_chunks(
    prompt: str,
    chunk_words: int = 6,
) -> List[str]:
    """
    Split cached vault RAG grounding into small chunks for immediate SSE streaming.
    """
    context = get_document_context_from_cache(prompt)
    if not context:
        return []

    words = re.findall(r"\S+", context)
    if not words:
        return []

    chunks: List[str] = []
    for index in range(0, len(words), chunk_words):
        piece = " ".join(words[index:index + chunk_words])
        suffix = " " if index + chunk_words < len(words) else ""
        chunks.append(f"{piece}{suffix}")
    return chunks


class PdfVaultStore:
    @property
    def structure(self) -> Dict[str, Dict[str, str]]:
        return VAULT_STRUCTURE

    @structure.setter
    def structure(self, value: Dict[str, Dict[str, str]]) -> None:
        global VAULT_STRUCTURE
        VAULT_STRUCTURE = value

    @property
    def documents(self) -> Dict[str, str]:
        return VAULT_CACHE

    @documents.setter
    def documents(self, value: Dict[str, str]) -> None:
        global VAULT_CACHE
        VAULT_CACHE = value

    def initialize(self) -> None:
        populate_vault_cache_once()

    def reload(self) -> None:
        global VAULT_READY
        with _vault_lock:
            VAULT_READY = False
        populate_vault_cache_once()

    def get_document_context_for_prompt(self, prompt: str) -> str:
        return get_document_context_from_cache(prompt)


pdf_vault = PdfVaultStore()


def initialize_vault() -> PdfVaultStore:
    populate_vault_cache_once()
    return pdf_vault


def _collect_folder_files_from_index() -> Dict[str, List[Dict[str, str]]]:
    """Build folder -> file list from memory cache or vault_index.json (no pypdf)."""
    folders: Dict[str, List[Dict[str, str]]] = {}

    if VAULT_STRUCTURE:
        for folder_name, documents in VAULT_STRUCTURE.items():
            entries = []
            for path in sorted(documents.keys()):
                suffix = Path(path).suffix.lower()
                entries.append({
                    "path": path,
                    "name": Path(path).name,
                    "extension": suffix,
                    "kind": "pdf" if suffix == ".pdf" else "text",
                })
            folders[folder_name] = entries
        return folders

    disk_index = load_vault_index_from_disk()
    documents = disk_index.get("documents", {})

    for path, meta in documents.items():
        folder_name = meta.get("folder") or "root"
        suffix = Path(path).suffix.lower()
        folders.setdefault(folder_name, []).append({
            "path": path,
            "name": Path(path).name,
            "extension": suffix,
            "kind": "pdf" if suffix == ".pdf" else "text",
        })

    for folder_name in folders:
        folders[folder_name].sort(key=lambda item: item["name"].lower())

    return folders


def get_vault_cache_stats() -> Dict[str, Any]:
    """Lightweight vault stats for Scavenger Mode status and API health."""
    folders = _collect_folder_files_from_index()
    document_count = len(VAULT_CACHE) or sum(len(files) for files in folders.values())
    return {
        "ready": VAULT_READY,
        "loading": VAULT_LOADING,
        "document_count": document_count,
        "folder_count": len(folders),
    }


def get_vault_tree_layout() -> Dict[str, Any]:
    """
    Return JSON tree layout grouped by subfolder for /api/vault/tree.
    Reads from VAULT_CACHE / vault_index.json only — never runs os.walk here.
    """
    folders = _collect_folder_files_from_index()
    document_count = sum(len(files) for files in folders.values())

    disk_index = load_vault_index_from_disk()
    registry = disk_index.get("file_registry", {})
    duplicate_count = sum(
        1 for entry in registry.values() if entry.get("status") == "duplicate"
    )

    return {
        "ready": VAULT_READY,
        "loading": VAULT_LOADING,
        "document_count": document_count,
        "folder_count": len(folders),
        "duplicate_count": duplicate_count,
        "index_path": VAULT_INDEX_PATH,
        "folders": folders,
    }


def start_background_vault_sync() -> str:
    """
    Trigger incremental re-index in a background thread.
    Safe to call while server is running — does not restart the process.
    """
    global VAULT_LOADING

    with _vault_lock:
        if VAULT_LOADING:
            return "already_running"

    def _worker() -> None:
        global VAULT_LOADING
        with _vault_lock:
            VAULT_LOADING = True

        try:
            ensure_vault_directory()
            structure = sync_vault_documents_incremental()
            _apply_memory_cache(structure)
            print(
                f"[Vault] Background sync complete — {len(VAULT_CACHE)} document(s) in cache."
            )
        except Exception as exc:
            print(f"[Vault Warning] Background sync failed: {exc}")
        finally:
            with _vault_lock:
                VAULT_LOADING = False

    thread = threading.Thread(target=_worker, name="vault-background-sync", daemon=True)
    thread.start()
    return "started"
