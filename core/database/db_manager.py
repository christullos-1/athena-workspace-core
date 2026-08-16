# core/database/db_manager.py

import os
import sqlite3
from pathlib import Path
from typing import Optional


class DatabaseManager:
    """
    Manages SQLite connection lifecycle and schema initialization.
    """

    DEFAULT_DB_PATH = "data/athena.db"
    SCHEMA_PATH = "core/database/schema.sql"

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or self.DEFAULT_DB_PATH
        self._ensure_database()

    def _ensure_database(self) -> None:
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        schema_file = Path(self.SCHEMA_PATH)
        if not schema_file.exists():
            raise FileNotFoundError(f"Schema file not found: {self.SCHEMA_PATH}")

        with self.connection() as conn:
            schema_sql = schema_file.read_text(encoding="utf-8")
            conn.executescript(schema_sql)
            conn.commit()

    def connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def get_schema_summary(self) -> str:
        """Return a human-readable schema summary for agent prompts."""
        tables = {
            "caliber_specs": {
                "caliber_number": "TEXT UNIQUE NOT NULL",
                "specification": "TEXT NOT NULL",
                "source_doc": "TEXT optional",
                "notes": "TEXT optional",
            },
            "electrical_diagrams": {
                "diagram_id": "TEXT UNIQUE NOT NULL",
                "title": "TEXT NOT NULL",
                "description": "TEXT optional",
                "file_path": "TEXT optional",
                "metadata_json": "TEXT optional JSON",
            },
            "documents": {
                "title": "TEXT NOT NULL",
                "doc_type": "TEXT NOT NULL",
                "content": "TEXT NOT NULL",
                "tags": "TEXT optional comma-separated",
            },
        }

        lines = ["Available SQLite tables and writable fields:"]
        for table, columns in tables.items():
            cols = ", ".join(f"{name} ({meta})" for name, meta in columns.items())
            lines.append(f"- {table}: {cols}")
        return "\n".join(lines)
