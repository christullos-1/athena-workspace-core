# core/tools/mdn.py

import requests
from bs4 import BeautifulSoup
import re


class MDNFetcher:
    """
    Fetches technical documentation-style explanations from MDN.
    Uses both search and robust direct URL heuristics for maximum accuracy.
    """

    SEARCH_URL = "https://developer.mozilla.org/en-US/search"
    BASE_URL = "https://developer.mozilla.org"

    DOC_PREFIXES = [
        "/en-US/docs/Web/JavaScript/",
        "/en-US/docs/Web/API/",
        "/en-US/docs/Web/HTML/",
        "/en-US/docs/Web/CSS/",
    ]

    def fetch(self, query: str):
        print(f"DEBUG: MDNFetcher.fetch() called with query='{query}'")

        heuristic_result = self.try_direct_url_patterns(query)
        if heuristic_result:
            return heuristic_result

        return self.search_mdn(query)

    # ---------------------------------------------------------
    # Heuristic URL Resolution
    # ---------------------------------------------------------
    def try_direct_url_patterns(self, query: str):
        """
        Converts query into likely MDN documentation paths.
        Example: "javascript event loop" -> /docs/Web/JavaScript/Event_loop
        """

        print("DEBUG: MDN heuristic URL resolution starting")

        cleaned = re.sub(r"[^a-zA-Z0-9 ]", " ", query).strip()
        words = [w for w in cleaned.split() if w]

        if not words:
            print("DEBUG: MDN heuristic: no usable words")
            return None

        # Common patterns MDN uses
        base_tokens = [w.lower() for w in words]

        patterns = set()

        # Single-word patterns (for things like "Promise", "Fetch", etc.)
        if len(base_tokens) == 1:
            t = base_tokens[0]
            patterns.update([
                t,
                t.capitalize(),
            ])

        # Multi-word patterns
        joined = "".join(w.capitalize() for w in base_tokens)          # EventLoop
        snake_lower = "_".join(base_tokens)                             # event_loop
        snake_cap = "_".join(w.capitalize() for w in base_tokens)       # Event_Loop
        kebab_lower = "-".join(base_tokens)                             # event-loop
        kebab_cap = "-".join(w.capitalize() for w in base_tokens)       # Event-Loop

        patterns.update([
            joined,
            snake_lower,
            snake_cap,
            kebab_lower,
            kebab_cap,
        ])

        # Also try first word capitalized, rest lower (Event_loop)
        if len(base_tokens) > 1:
            first_cap_rest_lower = base_tokens[0].capitalize() + "_" + "_".join(base_tokens[1:])
            patterns.add(first_cap_rest_lower)

        print(f"DEBUG: MDN heuristic generated patterns: {patterns}")

        for prefix in self.DOC_PREFIXES:
            for pattern in patterns:
                url = f"{self.BASE_URL}{prefix}{pattern}"
                print(f"DEBUG: MDN heuristic trying URL={url}")
                try:
                    resp = requests.get(url, timeout=5)
                    if resp.status_code == 200:
                        print(f"DEBUG: MDN heuristic matched URL={url}")
                        return self.extract_content(resp.text, url)
                except Exception as e:
                    print(f"DEBUG: MDN heuristic exception for {url}: {e}")

        print("DEBUG: MDN heuristic found no valid pages")
        return None

    # ---------------------------------------------------------
    # MDN Search
    # ---------------------------------------------------------
    def search_mdn(self, query: str):
        print("DEBUG: MDN search fallback starting")

        params = {"q": query, "locale": "en-US"}

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        }

        try:
            resp = requests.get(self.SEARCH_URL, params=params, headers=headers, timeout=5)
            if resp.status_code != 200:
                print(f"DEBUG: MDN search HTTP {resp.status_code}")
                return None

            soup = BeautifulSoup(resp.text, "html.parser")

            link = (
                soup.select_one("a.search-result-link")
                or soup.select_one("a.SearchResult-link")
                or soup.select_one("a.ResultList-item")
            )

            if not link or not link.get("href"):
                print("DEBUG: MDN search returned no usable results")
                return None

            href = link.get("href")
            url = href if href.startswith("http") else f"{self.BASE_URL}{href}"

            print(f"DEBUG: MDN search resolved URL={url}")

            doc_resp = requests.get(url, headers=headers, timeout=5)
            if doc_resp.status_code != 200:
                print(f"DEBUG: MDN doc HTTP {doc_resp.status_code}")
                return None

            return self.extract_content(doc_resp.text, url)

        except Exception as e:
            print(f"DEBUG: MDN search exception: {e}")
            return None

    # ---------------------------------------------------------
    # Content Extraction
    # ---------------------------------------------------------
    def extract_content(self, html: str, url: str):
        soup = BeautifulSoup(html, "html.parser")

        article = soup.select_one("article") or soup.select_one("main")
        if not article:
            print("DEBUG: MDN extract: no article/main found")
            return None

        paragraphs = article.find_all("p")
        if not paragraphs:
            print("DEBUG: MDN extract: no <p> elements found")
            return None

        text = " ".join(p.get_text(strip=True) for p in paragraphs[:4]).strip()
        if not text:
            print("DEBUG: MDN extract: empty text")
            return None

        print(f"DEBUG: MDNFetcher returning {len(text)} characters from {url}")

        return {
            "source": "MDN",
            "url": url,
            "content": text
        }