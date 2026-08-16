# core/tools/duckduckgo.py

import requests


class DuckDuckGoFetcher:
    API_URL = "https://api.duckduckgo.com/"

    def fetch(self, query: str):
        """
        Fetches an instant-answer style summary from DuckDuckGo.
        Returns a dict with source, url, and content, or None if no useful data.
        """

        print(f"DEBUG: DuckDuckGoFetcher.fetch() called with query='{query}'")

        params = {
            "q": query,
            "format": "json",
            "no_html": 1,
            "skip_disambig": 1
        }

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        }

        try:
            response = requests.get(
                self.API_URL,
                params=params,
                headers=headers,
                timeout=5
            )

            # DuckDuckGo sometimes returns JSON with text/html content-type.
            try:
                data = response.json()
            except Exception:
                print("DEBUG: DuckDuckGo returned non-JSON response")
                print(f"DEBUG: Raw response: {response.text[:200]}")
                return None

            abstract = data.get("AbstractText")
            url = data.get("AbstractURL")

            if not abstract:
                print("DEBUG: DuckDuckGo returned no abstract text")
                return None

            print(f"DEBUG: DuckDuckGoFetcher returning {len(abstract)} characters")

            return {
                "source": "DuckDuckGo",
                "url": url or "https://duckduckgo.com/",
                "content": abstract
            }

        except Exception as e:
            print(f"DEBUG: DuckDuckGoFetcher exception: {e}")
            return None