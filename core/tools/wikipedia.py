# core/tools/wikipedia.py

import requests
from bs4 import BeautifulSoup


class WikipediaFetcher:
    SEARCH_API = "https://en.wikipedia.org/w/api.php"
    PAGE_URL = "https://en.wikipedia.org/wiki/"

    def fetch(self, query: str):
        print(f"DEBUG: WikipediaFetcher.fetch() called with query='{query}'")

        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json"
        }

        headers = {
            # Use a real browser UA to avoid Wikipedia blocking
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        }

        try:
            search_response = requests.get(
                self.SEARCH_API, params=params, headers=headers, timeout=5
            )

            # Check for non-JSON responses
            if "application/json" not in search_response.headers.get("Content-Type", ""):
                print("DEBUG: Wikipedia returned non-JSON response for search API")
                print(f"DEBUG: Raw response: {search_response.text[:200]}")
                return None

            data = search_response.json()
            search_results = data.get("query", {}).get("search", [])

            if not search_results:
                print("DEBUG: Wikipedia search returned no results")
                return None

            title = search_results[0]["title"]
            url = f"{self.PAGE_URL}{title.replace(' ', '_')}"

            print(f"DEBUG: Wikipedia resolved title='{title}' → URL={url}")

            # Fetch the actual page
            page_response = requests.get(url, headers=headers, timeout=5)

            if page_response.status_code != 200:
                print(f"DEBUG: Wikipedia HTTP {page_response.status_code} for URL={url}")
                return None

            soup = BeautifulSoup(page_response.text, "html.parser")
            paragraphs = soup.find_all("p")

            if not paragraphs:
                print("DEBUG: Wikipedia returned no <p> elements")
                return None

            text = " ".join(p.get_text() for p in paragraphs[:3]).strip()

            if not text:
                print("DEBUG: Wikipedia extracted empty text")
                return None

            print(f"DEBUG: WikipediaFetcher returning {len(text)} characters from {url}")

            return {
                "source": "Wikipedia",
                "url": url,
                "content": text
            }

        except Exception as e:
            print(f"DEBUG: WikipediaFetcher exception: {e}")
            return None