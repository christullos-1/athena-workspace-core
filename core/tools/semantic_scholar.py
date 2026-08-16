# core/tools/semantic_scholar.py

import requests
import time


class SemanticScholarFetcher:
    """
    Fetches academic paper metadata from Semantic Scholar's public API.
    Includes retry + backoff logic to handle 429 rate limits.
    """

    BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"

    def fetch(self, query: str):
        print(f"DEBUG: SemanticScholarFetcher.fetch() called with query='{query}'")

        params = {
            "query": query,
            "limit": 1,
            "fields": "title,abstract,authors,year,citationCount,externalIds,url"
        }

        # Retry settings
        max_retries = 2
        backoff_seconds = 2

        for attempt in range(max_retries + 1):
            try:
                resp = requests.get(self.BASE_URL, params=params, timeout=12)

                # Handle rate limit
                if resp.status_code == 429:
                    print(f"DEBUG: Semantic Scholar 429 rate limit (attempt {attempt + 1})")

                    if attempt < max_retries:
                        print(f"DEBUG: Backing off for {backoff_seconds} seconds before retry...")
                        time.sleep(backoff_seconds)
                        backoff_seconds *= 2  # exponential backoff
                        continue
                    else:
                        print("DEBUG: Semantic Scholar 429 persisted after retries → giving up")
                        return None

                # Handle other HTTP errors
                if resp.status_code != 200:
                    print(f"DEBUG: Semantic Scholar HTTP {resp.status_code}")
                    return None

                data = resp.json()
                papers = data.get("data", [])
                if not papers:
                    print("DEBUG: Semantic Scholar returned no papers")
                    return None

                paper = papers[0]

                title = paper.get("title", "").strip()
                abstract = (paper.get("abstract") or "").strip()
                year = paper.get("year", "")
                citation_count = paper.get("citationCount", 0)
                url = paper.get("url", "")
                authors = [a.get("name", "") for a in paper.get("authors", [])]

                if not title and not abstract:
                    print("DEBUG: Semantic Scholar entry missing content")
                    return None

                parts = []
                if title:
                    parts.append(f"Title: {title}")
                if authors:
                    parts.append(f"Authors: {', '.join(authors)}")
                if year:
                    parts.append(f"Year: {year}")
                parts.append(f"Citations: {citation_count}")
                if abstract:
                    parts.append(f"Abstract: {abstract}")
                if url:
                    parts.append(f"URL: {url}")

                content = "\n".join(parts)

                print(f"DEBUG: SemanticScholarFetcher returning {len(content)} characters from {url}")

                return {
                    "source": "Semantic Scholar",
                    "url": url or "https://semanticscholar.org",
                    "content": content,
                }

            except Exception as e:
                print(f"DEBUG: SemanticScholarFetcher exception: {e}")
                return None

        return None