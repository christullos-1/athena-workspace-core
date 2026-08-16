# core/vault/manual_downloader.py

import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import unquote, urlparse

try:
    from duckduckgo_search import DDGS
except ImportError as exc:
    raise ImportError(
        "duckduckgo-search is required. Install with: pip install duckduckgo-search"
    ) from exc

from core.vault.pdf_vault import VAULT_DIR, ensure_vault_directory, hot_ingest_vault_file


NEW_DOWNLOADS_SUBDIR = "New_Downloads"
PDF_SEARCH_SUFFIX = "watch repair technical guide datasheet filetype:pdf"
MAX_SEARCH_RESULTS = 12
DOWNLOAD_TIMEOUT_SECONDS = 90
MAX_PDF_BYTES = 50 * 1024 * 1024


def build_caliber_search_query(caliber: str) -> str:
    caliber = (caliber or "").strip()
    return f"{caliber} {PDF_SEARCH_SUFFIX}"


def find_caliber_pdf_urls(caliber: str) -> List[Dict[str, str]]:
    """
    Search DuckDuckGo for open PDF links related to a watch caliber.
    """
    query = build_caliber_search_query(caliber)
    results: List[Dict[str, str]] = []
    seen_urls = set()

    try:
        with DDGS() as ddgs:
            raw_items = ddgs.text(query, region="wt-wt", max_results=MAX_SEARCH_RESULTS)
            for item in raw_items:
                url = (item.get("href") or item.get("link") or "").strip()
                title = (item.get("title") or "Untitled").strip()
                if not url or url in seen_urls:
                    continue
                if not _looks_like_pdf_candidate(url, title):
                    continue
                seen_urls.add(url)
                results.append({"url": url, "title": title})
    except Exception as exc:
        print(f"[Downloader Warning] Search failed: {exc}")

    return results


def _looks_like_pdf_candidate(url: str, title: str) -> bool:
    combined = f"{url} {title}".lower()
    if combined.endswith(".pdf") or ".pdf" in combined:
        return True
    if "filetype:pdf" in combined or "datasheet" in combined:
        return True
    if any(token in combined for token in ("technical guide", "service manual", "repair manual")):
        return True
    return False


def _safe_pdf_filename(caliber: str) -> str:
    base = re.sub(r"[^\w\-.]+", "_", caliber.strip())
    base = base.strip("_") or "caliber_manual"
    if not base.lower().endswith(".pdf"):
        base = f"{base}.pdf"
    return base


def _unique_destination(dest_dir: Path, filename: str) -> Path:
    candidate = dest_dir / filename
    if not candidate.exists():
        return candidate

    stem = Path(filename).stem
    suffix = Path(filename).suffix
    timestamp = int(time.time())
    return dest_dir / f"{stem}_{timestamp}{suffix}"


def stream_download_pdf(url: str, caliber: str, dest_dir: Path) -> Path:
    """
    Stream a PDF from URL to disk using urllib.request.
    Validates PDF magic bytes before saving.
    """
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": "application/pdf,application/octet-stream,*/*",
        },
    )

    dest_dir.mkdir(parents=True, exist_ok=True)
    filename = _safe_pdf_filename(caliber)
    dest_path = _unique_destination(dest_dir, filename)

    try:
        with urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
            content_type = (response.headers.get("Content-Type") or "").lower()
            if content_type and "pdf" not in content_type and "octet-stream" not in content_type:
                raise ValueError(f"Unexpected content type: {content_type}")

            chunks: List[bytes] = []
            total = 0
            while True:
                chunk = response.read(65536)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_PDF_BYTES:
                    raise ValueError("PDF exceeds maximum allowed size (50 MB).")
                chunks.append(chunk)

            payload = b"".join(chunks)
    except urllib.error.URLError as exc:
        raise ValueError(f"Download failed: {exc}") from exc

    if not payload.startswith(b"%PDF"):
        raise ValueError("Downloaded file is not a valid PDF.")

    dest_path.write_bytes(payload)
    return dest_path


def download_caliber_manual(caliber: str) -> Dict[str, Any]:
    """
    Find, download, and hot-index a caliber manual PDF.
    """
    caliber = (caliber or "").strip()
    if not caliber:
        return {"success": False, "message": "Caliber string is required."}

    ensure_vault_directory()
    dest_dir = Path(VAULT_DIR) / NEW_DOWNLOADS_SUBDIR
    candidates = find_caliber_pdf_urls(caliber)

    if not candidates:
        return {
            "success": False,
            "caliber": caliber,
            "message": "No PDF download links found for that caliber.",
            "search_query": build_caliber_search_query(caliber),
        }

    errors: List[str] = []
    for candidate in candidates:
        url = candidate["url"]
        try:
            saved_path = stream_download_pdf(url, caliber, dest_dir)
            relative_path = saved_path.relative_to(Path(VAULT_DIR)).as_posix()
            ingest_result = hot_ingest_vault_file(relative_path)

            return {
                "success": True,
                "caliber": caliber,
                "message": "Caliber sheet downloaded and indexed.",
                "search_query": build_caliber_search_query(caliber),
                "source_url": url,
                "source_title": candidate.get("title", ""),
                "saved_path": relative_path,
                "ingest": ingest_result,
            }
        except Exception as exc:
            errors.append(f"{url}: {exc}")
            continue

    return {
        "success": False,
        "caliber": caliber,
        "message": "Found links but all downloads failed.",
        "search_query": build_caliber_search_query(caliber),
        "errors": errors,
    }
