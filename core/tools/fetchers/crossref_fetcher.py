import httpx
import re
from html import unescape

class CrossRefFetcher:
    BASE_URL = "https://api.crossref.org/works"

    def _clean_abstract(self, abstract: str | None) -> str | None:
        if not abstract:
            return None

        # Remove JATS XML tags like <jats:p>...</jats:p>
        abstract = re.sub(r"<[^>]+>", "", abstract)

        # Decode HTML entities (&amp;, &lt;, etc.)
        abstract = unescape(abstract)

        # Normalize whitespace
        abstract = re.sub(r"\s+", " ", abstract).strip()

        return abstract if abstract else None

    def fetch(self, query: str) -> dict | None:
        params = {"query": query, "rows": 1}

        try:
            with httpx.Client(timeout=10) as client:
                response = client.get(self.BASE_URL, params=params)
                response.raise_for_status()
                data = response.json()

                print("DEBUG: CrossRef raw response:", data)

        except Exception:
            return None

        items = data.get("message", {}).get("items", [])
        if not items:
            return None

        item = items[0]

        # Basic fields
        title = item.get("title", [""])[0]
        subtitle = item.get("subtitle", [""])
        subtitle = subtitle[0] if subtitle else None

        abstract_raw = item.get("abstract", None)
        abstract = self._clean_abstract(abstract_raw)

        doi = item.get("DOI", None)
        authors = [
            f"{a.get('given', '')} {a.get('family', '')}".strip()
            for a in item.get("author", [])
        ]

        # Year extraction
        year = None
        if "published-print" in item:
            year = item["published-print"]["date-parts"][0][0]
        elif "published-online" in item:
            year = item["published-online"]["date-parts"][0][0]

        # Additional metadata
        journal = item.get("container-title", [""])
        journal = journal[0] if journal else None

        subjects = item.get("subject", None)
        publisher = item.get("publisher", None)
        work_type = item.get("type", None)

        # ---------------------------
        # STEP 3: SYNTHETIC ABSTRACT
        # ---------------------------
        if not abstract:
            parts = []

            if subtitle:
                parts.append(f"This work explores {subtitle.lower()}.")

            if journal:
                parts.append(f"It appears in the journal '{journal}'.")

            if subjects:
                parts.append(
                    "It covers topics such as " +
                    ", ".join(s.lower() for s in subjects) + "."
                )

            if publisher:
                parts.append(f"It is published by {publisher}.")

            if work_type:
                parts.append(f"The publication type is '{work_type}'.")

            if not parts:
                parts.append("No abstract is available for this work.")

            abstract = " ".join(parts)

        # Build content block
                # ---------------------------
        # STEP 4: FORMATTED CONTENT BLOCK
        # ---------------------------
        content_lines = []

        content_lines.append(f"Title: {title}")

        if authors:
            content_lines.append(f"Authors: {', '.join(authors)}")

        if year:
            content_lines.append(f"Year: {year}")

        if doi:
            content_lines.append(f"DOI: {doi}")

        if journal:
            content_lines.append(f"Journal: {journal}")

        if publisher:
            content_lines.append(f"Publisher: {publisher}")

        if work_type:
            # Normalize type formatting
            pretty_type = work_type.replace("-", " ").title()
            content_lines.append(f"Type: {pretty_type}")

        if subjects:
            # Lowercase subjects for consistency
            pretty_subjects = ", ".join(s.lower() for s in subjects)
            content_lines.append(f"Subjects: {pretty_subjects}")

        # Add a blank line before the abstract for readability
        content_lines.append("")
        content_lines.append(f"Abstract: {abstract}")

        content = "\n".join(content_lines)

        return {
            "source": "crossref",
            "content": content,
            "title": title,
            "abstract": abstract,
            "authors": authors,
            "year": year,
            "doi": doi,
            "journal": journal,
            "subjects": subjects,
            "publisher": publisher,
            "type": work_type,
        }