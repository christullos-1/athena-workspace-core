import requests

class StackOverflowFetcher:
    API_URL = "https://api.stackexchange.com/2.3/search/advanced"

    def fetch(self, query: str):
        params = {
            "order": "desc",
            "sort": "relevance",
            "q": query,
            "site": "stackoverflow"
        }

        try:
            response = requests.get(self.API_URL, params=params, timeout=5)
            data = response.json()

            if "items" not in data or len(data["items"]) == 0:
                return None

            top = data["items"][0]
            url = top.get("link", "")
            title = top.get("title", "")

            return {
                "source": "StackOverflow",
                "url": url,
                "content": title
            }

        except Exception:
            return None