# core/tools/fetchers/duckduckgo_fetcher.py

from __future__ import annotations
from typing import List, Dict, Any
import requests
import tldextract


class DuckDuckGoFetcher:
    """
    Performs a DuckDuckGo search and returns normalized page results.
    """

    SEARCH_URL = "https://duckduckgo.com/html/"

    def fetch(self, query: str) -> List[Dict[str, Any]]:
        try:
            resp = requests.post(
                self.SEARCH_URL,
                data={"q": query},
                timeout=5
            )
            html = resp.text
        except Exception:
            return []

        return self._parse_results(html)

    def _parse_results(self, html: str) -> List[Dict[str, Any]]:
        """
        Very lightweight HTML parsing.
        We avoid heavy dependencies like BeautifulSoup.
        """
        results = []
        blocks = html.split('<a rel="nofollow" class="result__a"')

        for block in blocks[1:]:
            try:
                # Extract URL
                href_part = block.split('href="')[1]
                url = href_part.split('"')[0]

                # Extract snippet
                snippet_part = block.split('result__snippet">')[1]
                snippet = snippet_part.split("</a>")[0]

                domain = self._extract_domain(url)

                results.append({
                    "url": url,
                    "snippet": snippet,
                    "content": snippet,  # placeholder
                    "domain": domain,
                    "published_date": None,
                })
            except Exception:
                continue

        return results

    def _extract_domain(self, url: str) -> str:
        ext = tldextract.extract(url)
        return f"{ext.domain}.{ext.suffix}"