# core/tools/arxiv.py

import requests
import feedparser
from urllib.parse import urlencode


class ArXivFetcher:
    """
    Fetches scientific papers from arXiv using its public API.
    Returns a concise summary built from the top matching entry.
    """

    BASE_URL = "https://export.arxiv.org/api/query"

    def fetch(self, query: str):
        print(f"DEBUG: ArXivFetcher.fetch() called with query='{query}'")

        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": 3,
            "sortBy": "relevance",
            "sortOrder": "descending",
        }

        url = f"{self.BASE_URL}?{urlencode(params)}"
        print(f"DEBUG: ArXivFetcher requesting URL={url}")

        try:
            resp = requests.get(url, timeout=20)
            if resp.status_code != 200:
                print(f"DEBUG: ArXiv HTTP {resp.status_code}")
                return None

            feed = feedparser.parse(resp.text)

            if not feed.entries:
                print("DEBUG: ArXiv returned no entries")
                return None

            entry = feed.entries[0]

            title = getattr(entry, "title", "").strip()
            summary = getattr(entry, "summary", "").strip()
            link = getattr(entry, "link", "").strip()
            authors = [a.name for a in getattr(entry, "authors", [])] if hasattr(entry, "authors") else []
            published = getattr(entry, "published", "").strip()

            if not summary:
                print("DEBUG: ArXiv entry has no summary")
                return None

            # Build a compact content block
            parts = []
            if title:
                parts.append(f"Title: {title}")
            if authors:
                parts.append(f"Authors: {', '.join(authors)}")
            if published:
                parts.append(f"Published: {published}")
            parts.append(f"Abstract: {summary}")

            content = "\n".join(parts)

            print(f"DEBUG: ArXivFetcher returning {len(content)} characters from {link}")

            return {
                "source": "ArXiv",
                "url": link or "https://arxiv.org/",
                "content": content,
            }

        except Exception as e:
            print(f"DEBUG: ArXivFetcher exception: {e}")
            return None