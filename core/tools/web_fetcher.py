# core/tools/web_fetcher.py

from __future__ import annotations
from typing import Dict, Any, List

from core.tools.fetchers.duckduckgo_fetcher import DuckDuckGoFetcher
from core.tools.fetchers.wikipedia_fetcher import WikipediaFetcher
from core.tools.fetchers.stackoverflow_fetcher import StackOverflowFetcher
from core.tools.fetchers.mdn_fetcher import MDNFetcher


class WebFetcher:
    """
    Intelligent multi-source fetcher coordinator.
    Applies:
      - query classification
      - source relevance weighting
      - per-source result limiting
    """

    def __init__(self):
        self.ddg = DuckDuckGoFetcher()
        self.wiki = WikipediaFetcher()
        self.so = StackOverflowFetcher()
        self.mdn = MDNFetcher()

    # ------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------

    def fetch(self, query: str) -> Dict[str, Any]:
        """
        Runs only the fetchers relevant to the query.
        Applies result limiting and merges results.
        """

        fetchers = self._classify_query(query)
        pages: List[Dict[str, Any]] = []

        # DuckDuckGo
        if fetchers.get("ddg"):
            try:
                pages.extend(self.ddg.fetch(query)[:5])
            except Exception:
                pass

        # Wikipedia
        if fetchers.get("wiki"):
            try:
                pages.extend(self.wiki.fetch(query)[:1])
            except Exception:
                pass

        # StackOverflow
        if fetchers.get("so"):
            try:
                pages.extend(self.so.fetch(query)[:3])
            except Exception:
                pass

        # MDN
        if fetchers.get("mdn"):
            try:
                pages.extend(self.mdn.fetch(query)[:3])
            except Exception:
                pass

        return {"pages": pages}

    # ------------------------------------------------------------
    # INTERNAL METHODS
    # ------------------------------------------------------------

    def _classify_query(self, query: str) -> Dict[str, bool]:
        """
        Lightweight rule-based classifier.
        Determines which fetchers are relevant.
        """

        q = query.lower()

        is_technical = any(word in q for word in [
            "python", "javascript", "css", "html", "api", "error", "stack trace",
            "function", "variable", "class", "react", "node", "typescript"
        ])

        is_webdev = any(word in q for word in [
            "html", "css", "javascript", "dom", "browser", "web", "element"
        ])

        is_scientific = any(word in q for word in [
            "paradox", "physics", "quantum", "astronomy", "biology", "chemistry",
            "universe", "cosmology", "fermi", "relativity"
        ])

        is_general = not (is_technical or is_webdev or is_scientific)

        return {
            "ddg": True,  # always include general search
            "wiki": is_scientific or is_general,
            "so": is_technical,
            "mdn": is_webdev or is_technical,
        }