# core/tools/web_search.py

import requests
import urllib.parse


class WebSearchTool:
    """
    Uses Wikipedia's official search API.
    Adds a User-Agent header to avoid 403 blocks.
    """

    API_URL = "https://en.wikipedia.org/w/api.php"

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    def search(self, query: str, max_results: int = 5) -> str:
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "utf8": 1
        }

        try:
            resp = requests.get(self.API_URL, params=params, headers=self.HEADERS, timeout=8)
            resp.raise_for_status()
        except Exception:
            return "I tried to search the web, but the request failed."

        data = resp.json()
        results = data.get("query", {}).get("search", [])

        if not results:
            return f"I searched for '{query}', but couldn't find useful results."

        lines = [f"Here are some results for: {query}"]

        for idx, item in enumerate(results[:max_results], start=1):
            title = item.get("title", "No title")
            url_title = urllib.parse.quote(title.replace(" ", "_"))
            url = f"https://en.wikipedia.org/wiki/{url_title}"
            lines.append(f"{idx}. {title}\n   {url}")

        return "\n".join(lines)