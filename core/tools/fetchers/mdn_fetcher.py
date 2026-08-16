# core/tools/fetchers/mdn_fetcher.py

from __future__ import annotations
from typing import List, Dict, Any
import requests
import tldextract


class MDNFetcher:
    """
    Fetches MDN documentation pages using the MDN search API.
    """

    SEARCH_URL = "https://developer.mozilla.org/api/v1/search"

    def fetch(self, query: str) -> List[Dict[str, Any]]:
        try:
            resp = requests.get(self.SEARCH_URL, params={"q": query}, timeout=5)
            data = resp.json()
        except Exception:
            return []

        results = []
        for doc in data.get("documents", []):
            url = f"https://developer.mozilla.org{doc.get('mdn_url', '')}"
            snippet = doc.get("summary", "")
            domain = self._extract_domain(url)

            results.append({
                "url": url,
                "snippet": snippet,
                "content": snippet,
                "domain": domain,
                "published_date": doc.get("modified"),
            })

        return results

    def _extract_domain(self, url: str) -> str:
        ext = tldextract.extract(url)
        return f"{ext.domain}.{ext.suffix}"