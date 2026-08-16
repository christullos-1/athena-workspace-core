# core/tools/live_web_search.py

import html as html_module
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Callable, Dict, List, Optional, Tuple

try:
    from duckduckgo_search import DDGS
except ImportError as exc:
    raise ImportError(
        "duckduckgo-search is required. Install with: pip install duckduckgo-search"
    ) from exc

from core.tools.duckduckgo import DuckDuckGoFetcher


DEFAULT_MAX_RESULTS = 5
MIN_TARGET_RESULTS = 3

BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)

DDG_LITE_URL = "https://lite.duckduckgo.com/lite/"
DDG_HTML_URL = "https://html.duckduckgo.com/html/"


def execute_web_search(query: str, max_results: int = DEFAULT_MAX_RESULTS) -> List[Dict[str, str]]:
    """
    Resilient live web search with multi-backend fallbacks.
    Returns 3-5 clean {title, url, summary} dicts when possible.
    """
    query = (query or "").strip()
    if not query:
        return []

    target = max(MIN_TARGET_RESULTS, min(max_results, DEFAULT_MAX_RESULTS))
    is_weather_query = "weather" in query.lower()
    collected: List[Dict[str, str]] = []

    search_steps: List[Tuple[str, Callable[[], List[Dict[str, str]]]]] = [
        ("ddgs-auto", lambda: _search_ddgs(query, target, backend="auto")),
        ("ddgs-html", lambda: _search_ddgs(query, target, backend="html")),
        ("ddgs-lite", lambda: _search_ddgs(query, target, backend="lite")),
        ("urllib-lite", lambda: _search_ddg_lite_urllib(query, target)),
        ("urllib-html", lambda: _search_ddg_html_urllib(query, target)),
        ("instant-answer", lambda: _search_instant_answer(query)),
    ]

    for step_name, step_fn in search_steps:
        if len(collected) >= target:
            break
        try:
            batch = step_fn()
        except Exception as exc:
            print(f"[LiveSearch] {step_name} failed: {exc}")
            batch = []

        if not batch:
            print(f"[LiveSearch] {step_name} returned 0 results for: {query!r}")
            continue

        before = len(collected)
        collected = _merge_results(collected, batch, target)
        added = len(collected) - before
        print(f"[LiveSearch] {step_name} added {added} result(s)")

    if not collected and is_weather_query:
        weather_result = _fetch_wttr_weather(query)
        if weather_result:
            collected = [weather_result]

    final = collected[:target]
    _log_live_urls(query, final)
    return final


def search_top_summaries(query: str, max_results: int = DEFAULT_MAX_RESULTS) -> List[Dict[str, str]]:
    """Backward-compatible alias for execute_web_search."""
    return execute_web_search(query, max_results=max_results)


def _search_ddgs(query: str, max_results: int, backend: str) -> List[Dict[str, str]]:
    results: List[Dict[str, str]] = []
    with DDGS() as ddgs:
        raw_items = ddgs.text(
            query,
            region="wt-wt",
            safesearch="moderate",
            max_results=max_results,
            backend=backend,
        )
        for item in raw_items:
            normalized = _normalize_ddg_result(item)
            if normalized:
                results.append(normalized)
    return results


def _urllib_post(url: str, query: str, timeout: int = 15) -> str:
    payload = urllib.parse.urlencode({"q": query}).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={
            "User-Agent": BROWSER_USER_AGENT,
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://duckduckgo.com/",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def _search_ddg_lite_urllib(query: str, max_results: int) -> List[Dict[str, str]]:
    page_html = _urllib_post(DDG_LITE_URL, query)
    return _parse_ddg_lite_html(page_html, max_results)


def _search_ddg_html_urllib(query: str, max_results: int) -> List[Dict[str, str]]:
    page_html = _urllib_post(DDG_HTML_URL, query)
    return _parse_ddg_classic_html(page_html, max_results)


def _search_instant_answer(query: str) -> List[Dict[str, str]]:
    fallback = DuckDuckGoFetcher().fetch(query)
    if not fallback:
        return []

    content = (fallback.get("content") or "").strip()
    if not content:
        return []

    return [{
        "title": fallback.get("source", "DuckDuckGo"),
        "url": fallback.get("url", ""),
        "summary": content,
    }]


def _parse_ddg_lite_html(page_html: str, max_results: int) -> List[Dict[str, str]]:
    results: List[Dict[str, str]] = []

    link_pattern = re.compile(
        r'class="result-link"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
        re.IGNORECASE | re.DOTALL,
    )
    snippet_pattern = re.compile(
        r'class="result-snippet"[^>]*>(.*?)</td>',
        re.IGNORECASE | re.DOTALL,
    )

    links = link_pattern.findall(page_html)
    snippets = snippet_pattern.findall(page_html)

    for index, (url, title_html) in enumerate(links):
        if len(results) >= max_results:
            break

        title = _clean_html_text(title_html)
        url = _clean_url(url)
        if not _is_valid_result_url(url):
            continue

        summary = ""
        if index < len(snippets):
            summary = _clean_html_text(snippets[index])

        results.append({
            "title": title or "Untitled",
            "url": url,
            "summary": summary or title or url,
        })

    return results


def _parse_ddg_classic_html(page_html: str, max_results: int) -> List[Dict[str, str]]:
    results: List[Dict[str, str]] = []

    # Modern + legacy DuckDuckGo HTML result blocks.
    blocks = re.split(r'<a[^>]+class="[^"]*result__a[^"]*"', page_html, flags=re.IGNORECASE)
    for block in blocks[1:]:
        if len(results) >= max_results:
            break

        url_match = re.search(r'href="([^"]+)"', block, flags=re.IGNORECASE)
        if not url_match:
            continue

        url = _clean_url(url_match.group(1))
        if not _is_valid_result_url(url):
            continue

        title_match = re.search(r'>([^<]+)</a>', block, flags=re.IGNORECASE | re.DOTALL)
        title = _clean_html_text(title_match.group(1) if title_match else "")

        snippet_match = re.search(
            r'class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</(?:a|span|div|td)>',
            block,
            flags=re.IGNORECASE | re.DOTALL,
        )
        summary = _clean_html_text(snippet_match.group(1) if snippet_match else "")

        results.append({
            "title": title or "Untitled",
            "url": url,
            "summary": summary or title or url,
        })

    if results:
        return results

    # Lite-style markup sometimes appears on html endpoint mirrors.
    return _parse_ddg_lite_html(page_html, max_results)


def _clean_html_text(raw: str) -> str:
    text = html_module.unescape(re.sub(r"<[^>]+>", " ", raw or ""))
    return re.sub(r"\s+", " ", text).strip()


def _clean_url(url: str) -> str:
    url = html_module.unescape((url or "").strip())
    if url.startswith("//"):
        return f"https:{url}"
    return url


def _is_valid_result_url(url: str) -> bool:
    if not url:
        return False
    lowered = url.lower()
    if not lowered.startswith(("http://", "https://")):
        return False
    if "duckduckgo.com" in lowered and "/l/?" not in lowered:
        return False
    return True


def _normalize_ddg_result(item: Dict[str, str]) -> Optional[Dict[str, str]]:
    summary = (item.get("body") or item.get("snippet") or "").strip()
    title = (item.get("title") or "Untitled").strip()
    url = _clean_url(item.get("href") or item.get("link") or "")

    if not summary and not title:
        return None
    if url and not _is_valid_result_url(url):
        return None

    return {
        "title": title,
        "url": url,
        "summary": _clean_html_text(summary or title),
    }


def _merge_results(
    existing: List[Dict[str, str]],
    new_items: List[Dict[str, str]],
    max_results: int,
) -> List[Dict[str, str]]:
    merged = list(existing)
    seen_urls = {item.get("url", "").lower() for item in merged if item.get("url")}

    for item in new_items:
        url = item.get("url", "")
        if url and url.lower() in seen_urls:
            continue
        merged.append(item)
        if url:
            seen_urls.add(url.lower())
        if len(merged) >= max_results:
            break

    return merged


def _log_live_urls(query: str, results: List[Dict[str, str]]) -> None:
    print(f"[LiveSearch] Query: {query!r}")
    if not results:
        print("[LiveSearch] No live URLs retrieved.")
        return

    print(f"[LiveSearch] Retrieved {len(results)} live result(s):")
    for index, result in enumerate(results, start=1):
        title = result.get("title", "Untitled")
        url = result.get("url", "N/A")
        summary = result.get("summary", "")
        snippet_preview = summary[:120].replace("\n", " ")
        print(f"[LiveSearch] [{index}] {title}")
        print(f"[LiveSearch]      URL: {url}")
        if snippet_preview:
            print(f"[LiveSearch]      Snippet: {snippet_preview}")


def _extract_weather_location(query: str) -> str:
    lower = query.lower()

    for prefix in ("weather in ", "weather for ", "weather at ", "weather near "):
        if prefix in lower:
            start = lower.index(prefix) + len(prefix)
            location = query[start:].strip()
            location = re.split(r"[?.!,;]", location)[0].strip()
            if location:
                return location

    cleaned = re.sub(
        r"\b(weather|forecast|temperature|today|tomorrow|current|what'?s|what is|the|please|tell me)\b",
        " ",
        query,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or query


def _fetch_wttr_weather(query: str) -> Optional[Dict[str, str]]:
    """
    Fetch a one-line live weather report from wttr.in.
    """
    location = _extract_weather_location(query)
    encoded_location = quote(location)
    url = f"https://wttr.in/{encoded_location}?format=3"

    try:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "curl/7.64.1"},
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            summary = response.read().decode("utf-8", errors="replace").strip()
    except (urllib.error.URLError, TimeoutError, OSError):
        return None

    if not summary:
        return None

    return {
        "title": f"wttr.in Live Weather ({location})",
        "url": url,
        "summary": summary,
    }


def format_system_context_alert(query: str, results: List[Dict[str, str]]) -> str:
    """
    Wrap live search snippets in a forced context envelope for the model.
    """
    lines = [
        "SYSTEM CONTEXT ALERT: Use these exact live details to fulfill the request.",
        "",
        f"Live search query: {query}",
        "",
    ]

    if not results:
        lines.append(
            "No live snippets were retrieved. Do not guess current facts; "
            "state that live data could not be fetched."
        )
        return "\n".join(lines)

    for index, result in enumerate(results, start=1):
        lines.extend([
            f"[{index}] {result.get('title', 'Untitled')}",
            f"Summary: {result.get('summary', '')}",
            f"Source: {result.get('url', 'N/A')}",
            "",
        ])

    return "\n".join(lines).strip()


def format_factual_context_reference(query: str, results: List[Dict[str, str]]) -> str:
    """
    Format live search results as a temporary factual context block.
    """
    lines = [
        "=== Factual Context Reference (live web search) ===",
        f"Search query: {query}",
        "",
    ]

    if not results:
        lines.append("No live search results were returned.")
        return "\n".join(lines)

    for index, result in enumerate(results, start=1):
        lines.extend([
            f"[{index}] {result.get('title', 'Untitled')}",
            f"URL: {result.get('url', 'N/A')}",
            f"Summary: {result.get('summary', '')}",
            "",
        ])

    return "\n".join(lines).strip()
