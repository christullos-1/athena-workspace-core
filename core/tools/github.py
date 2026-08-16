# core/tools/github.py

import requests
from urllib.parse import urlencode


class GitHubFetcher:
    """
    Fetches repository-level information from GitHub's search API.
    Focused on code / library / framework / tool queries.
    """

    SEARCH_URL = "https://api.github.com/search/repositories"

    def fetch(self, query: str):
        print(f"DEBUG: GitHubFetcher.fetch() called with query='{query}'")

        params = {
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": 3,
        }

        url = f"{self.SEARCH_URL}?{urlencode(params)}"
        print(f"DEBUG: GitHubFetcher requesting URL={url}")

        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "Athena-Research-Engine",
        }

        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                print(f"DEBUG: GitHub HTTP {resp.status_code}")
                return None

            data = resp.json()
            items = data.get("items", [])
            if not items:
                print("DEBUG: GitHub returned no repositories")
                return None

            repo = items[0]

            name = repo.get("full_name", "")
            description = (repo.get("description") or "").strip()
            stars = repo.get("stargazers_count", 0)
            language = repo.get("language", "")
            html_url = repo.get("html_url", "")
            topics = repo.get("topics", [])

            parts = []
            if name:
                parts.append(f"Repository: {name}")
            if description:
                parts.append(f"Description: {description}")
            if language:
                parts.append(f"Language: {language}")
            parts.append(f"Stars: {stars}")
            if topics:
                parts.append(f"Topics: {', '.join(topics)}")
            if html_url:
                parts.append(f"URL: {html_url}")

            content = "\n".join(parts)

            print(f"DEBUG: GitHubFetcher returning {len(content)} characters from {html_url}")

            return {
                "source": "GitHub",
                "url": html_url or "https://github.com",
                "content": content,
            }

        except Exception as e:
            print(f"DEBUG: GitHubFetcher exception: {e}")
            return None