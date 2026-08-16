# core/tools/crossref.py

import requests


class CrossRefFetcher:
    """
    Fetches publication metadata from CrossRef's public API.
    Returns the top matching work plus a summary of its references (if available).
    """

    BASE_URL = "https://api.crossref.org/works"

    def fetch(self, query: str):
        print(f"DEBUG: CrossRefFetcher.fetch() called with query='{query}'")

        params = {
            "query": query,
            "rows": 1,
            "select": "DOI,title,author,issued,container-title,publisher,reference,URL"
        }

        try:
            resp = requests.get(self.BASE_URL, params=params, timeout=12)
            if resp.status_code != 200:
                print(f"DEBUG: CrossRef HTTP {resp.status_code}")
                return None

            data = resp.json()
            message = data.get("message", {})
            items = message.get("items", [])
            if not items:
                print("DEBUG: CrossRef returned no items")
                return None

            work = items[0]

            doi = work.get("DOI", "")
            titles = work.get("title", [])
            title = titles[0].strip() if titles else ""

            authors_raw = work.get("author", [])
            authors = []
            for a in authors_raw:
                given = a.get("given", "")
                family = a.get("family", "")
                name = " ".join(part for part in [given, family] if part).strip()
                if name:
                    authors.append(name)

            issued = work.get("issued", {})
            year = ""
            if "date-parts" in issued:
                parts = issued["date-parts"]
                if parts and isinstance(parts[0], list) and parts[0]:
                    year = parts[0][0]

            container_titles = work.get("container-title", [])
            journal = container_titles[0].strip() if container_titles else ""

            publisher = work.get("publisher", "")
            url = work.get("URL", "")

            # References summary
            references = work.get("reference", [])
            ref_summaries = []
            for ref in references[:5]:
                ref_title = (ref.get("article-title") or ref.get("series-title") or ref.get("volume-title") or "").strip()
                ref_doi = (ref.get("DOI") or "").strip()
                ref_parts = []
                if ref_title:
                    ref_parts.append(ref_title)
                if ref_doi:
                    ref_parts.append(f"DOI: {ref_doi}")
                if ref_parts:
                    ref_summaries.append(" - " + " | ".join(ref_parts))

            parts = []
            if title:
                parts.append(f"Title: {title}")
            if authors:
                parts.append(f"Authors: {', '.join(authors)}")
            if year:
                parts.append(f"Year: {year}")
            if journal:
                parts.append(f"Journal: {journal}")
            if publisher:
                parts.append(f"Publisher: {publisher}")
            if doi:
                parts.append(f"DOI: {doi}")
            if url:
                parts.append(f"URL: {url}")

            if ref_summaries:
                parts.append("References (sample):")
                parts.extend(ref_summaries)

            content = "\n".join(parts)

            if not content:
                print("DEBUG: CrossRef entry missing usable content")
                return None

            print(f"DEBUG: CrossRefFetcher returning {len(content)} characters from {url or 'N/A'}")

            return {
                "source": "CrossRef",
                "url": url or "https://api.crossref.org",
                "content": content,
            }

        except Exception as e:
            print(f"DEBUG: CrossRefFetcher exception: {e}")
            return None