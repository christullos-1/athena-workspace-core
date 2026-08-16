# core/tools/fetchers/wikipedia_fetcher.py

from __future__ import annotations
from typing import List, Dict, Any
import requests
import tldextract


class WikipediaFetcher:
    """
    Fetches Wikipedia summaries using:
      1. The search API to find the correct page title
      2. The summary API to retrieve structured content
    """

    SEARCH_URL = "https://en.wikipedia.org/w/api.php"
    SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/"

    def fetch(self, query: str) -> List[Dict[str, Any]]:
        title = self._search_title(query)
        if not title:
            return []

        return self._fetch_summary(title)

    # ------------------------------------------------------------
    # INTERNAL METHODS
    # ------------------------------------------------------------

    def _search_title(self, query: str) -> str:
        """
        Uses the Wikipedia search API to find the most relevant page title.
        """

        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "srlimit": 1,
        }

        try:
            resp = requests.get(self.SEARCH_URL, params=params, timeout=5)
            data = resp.json()
        except Exception:
            return ""

        search_results = data.get("query", {}).get("search", [])
        if not search_results:
            return ""

        return search_results[0].get("title", "")

    def _fetch_summary(self, title: str) -> List[Dict[str, Any]]:
        """
        Fetches the summary for the given Wikipedia page title.
        """

        url = f"{self.SUMMARY_URL}{title.replace(' ', '_')}"

        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code != 200:
                return []
            data = resp.json()
        except Exception:
            return []

        if "extract" not in data:
            return []

        domain = self._extract_domain("https://wikipedia.org")

        return [{
            "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
            "snippet": data.get("extract", "")[:300],
            "content": data.get("extract", ""),
            "domain": domain,
            "published_date": None,
        }]

    def _extract_domain(self, url: str) -> str:
        ext = tldextract.extract(url)
        return f"{ext.domain}.{ext.suffix}"