# core/tools/fetchers/stackoverflow_fetcher.py

from __future__ import annotations
from typing import List, Dict, Any
import requests
import tldextract


class StackOverflowFetcher:
    """
    Fetches top StackOverflow answers for a query.
    """

    SEARCH_URL = "https://api.stackexchange.com/2.3/search/advanced"

    def fetch(self, query: str) -> List[Dict[str, Any]]:
        params = {
            "order": "desc",
            "sort": "relevance",
            "q": query,
            "site": "stackoverflow",
            "accepted": "True",
        }

        try:
            resp = requests.get(self.SEARCH_URL, params=params, timeout=5)
            data = resp.json()
        except Exception:
            return []

        results = []
        for item in data.get("items", []):
            url = item.get("link", "")
            snippet = item.get("title", "")
            domain = self._extract_domain(url)

            results.append({
                "url": url,
                "snippet": snippet,
                "content": snippet,
                "domain": domain,
                "published_date": item.get("creation_date"),
            })

        return results

    def _extract_domain(self, url: str) -> str:
        ext = tldextract.extract(url)
        return f"{ext.domain}.{ext.suffix}"