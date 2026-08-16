# core/agent/document_store.py

import json
import os
from pathlib import Path
from typing import List, Dict


class DocumentStore:
    """
    Local document store for caliber specs, electrical diagrams, and reference files.
    Searches documents/ directory and SQLite documents table.
    """

    DOCUMENTS_DIR = "documents"
    SEARCH_EXTENSIONS = {".txt", ".md", ".json"}

    FACTUAL_KEYWORDS = [
        "caliber", "gauge", "mm", "inch", "bullet", "cartridge",
        "wiring", "diagram", "schematic", "electrical", "voltage",
        "amp", "ohm", "circuit", "pinout",
    ]

    def __init__(self, db_manager=None):
        self.db_manager = db_manager
        self._ensure_documents_dir()

    def _ensure_documents_dir(self) -> None:
        os.makedirs(self.DOCUMENTS_DIR, exist_ok=True)

    def needs_document_lookup(self, message: str) -> bool:
        lower = message.lower()
        return any(kw in lower for kw in self.FACTUAL_KEYWORDS)

    def search(self, query: str, limit: int = 5) -> List[Dict[str, str]]:
        results: List[Dict[str, str]] = []
        query_terms = [t.lower() for t in query.split() if len(t) > 2]

        results.extend(self._search_files(query_terms, limit))
        results.extend(self._search_database(query_terms, limit))

        # Deduplicate by title
        seen = set()
        unique: List[Dict[str, str]] = []
        for item in results:
            key = item.get("title", "")
            if key not in seen:
                seen.add(key)
                unique.append(item)
            if len(unique) >= limit:
                break
        return unique

    def _search_files(self, query_terms: List[str], limit: int) -> List[Dict[str, str]]:
        results: List[Dict[str, str]] = []
        docs_path = Path(self.DOCUMENTS_DIR)
        if not docs_path.exists():
            return results

        for path in docs_path.rglob("*"):
            if path.suffix.lower() not in self.SEARCH_EXTENSIONS:
                continue
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue

            lower_content = content.lower()
            score = sum(1 for term in query_terms if term in lower_content)
            if score == 0:
                continue

            excerpt = content[:800].strip()
            results.append({
                "source": "local_file",
                "title": path.name,
                "path": str(path),
                "excerpt": excerpt,
                "score": str(score),
            })

        results.sort(key=lambda x: int(x.get("score", "0")), reverse=True)
        return results[:limit]

    def _search_database(self, query_terms: List[str], limit: int) -> List[Dict[str, str]]:
        if self.db_manager is None:
            try:
                from core.database.db_manager import DatabaseManager
                self.db_manager = DatabaseManager()
            except Exception:
                return []

        results: List[Dict[str, str]] = []
        try:
            with self.db_manager.connection() as conn:
                rows = conn.execute(
                    "SELECT title, doc_type, content, tags FROM documents"
                ).fetchall()
        except Exception:
            return results

        for row in rows:
            haystack = " ".join([
                row["title"] or "",
                row["doc_type"] or "",
                row["content"] or "",
                row["tags"] or "",
            ]).lower()
            score = sum(1 for term in query_terms if term in haystack)
            if score == 0:
                continue
            results.append({
                "source": "sqlite_documents",
                "title": row["title"],
                "doc_type": row["doc_type"],
                "excerpt": (row["content"] or "")[:800],
                "score": str(score),
            })

        results.sort(key=lambda x: int(x.get("score", "0")), reverse=True)
        return results[:limit]

    def format_for_prompt(self, results: List[Dict[str, str]]) -> str:
        if not results:
            return (
                "LOCAL DOCUMENT STORE: No matching documents found. "
                "Do NOT invent caliber numbers, wiring details, or diagram specs."
            )

        lines = ["LOCAL DOCUMENT STORE RESULTS:"]
        for item in results:
            lines.append(
                f"- [{item.get('source')}] {item.get('title')}: "
                f"{item.get('excerpt', '')[:500]}"
            )
        return "\n".join(lines)
