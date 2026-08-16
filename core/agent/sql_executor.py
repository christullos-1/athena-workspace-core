# core/agent/sql_executor.py

import json
import re
import sqlite3
from dataclasses import dataclass
from typing import Any, Dict, Optional

from core.database.db_manager import DatabaseManager


@dataclass
class SqlExecutionResult:
    success: bool
    message: str
    rows_affected: int = 0
    conflict: bool = False
    data: Optional[Dict[str, Any]] = None


class SqlExecutor:
    """
    Secure SQLite execution layer.
    Only whitelisted tables/columns and parameterized INSERT/UPDATE are allowed.
    """

    ALLOWED_ACTIONS = {"insert", "update"}

    TABLE_COLUMNS: Dict[str, set] = {
        "caliber_specs": {
            "caliber_number", "specification", "source_doc", "notes",
        },
        "electrical_diagrams": {
            "diagram_id", "title", "description", "file_path", "metadata_json",
        },
        "documents": {
            "title", "doc_type", "content", "tags",
        },
    }

    UNIQUE_KEYS: Dict[str, str] = {
        "caliber_specs": "caliber_number",
        "electrical_diagrams": "diagram_id",
    }

    IDENTIFIER_PATTERN = re.compile(r"^[a-z_][a-z0-9_]*$")

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager()

    def execute(self, tool_call: Dict[str, Any]) -> SqlExecutionResult:
        try:
            normalized = self._validate_tool_call(tool_call)
        except ValueError as exc:
            return SqlExecutionResult(
                success=False,
                message=str(exc),
                conflict=False,
            )

        action = normalized["action"]
        table = normalized["table"]
        fields = normalized["fields"]
        where_clause = normalized.get("where", {})

        try:
            with self.db.connection() as conn:
                if action == "insert":
                    result = self._execute_insert(conn, table, fields)
                else:
                    result = self._execute_update(conn, table, fields, where_clause)

                self._write_audit_log(conn, action, table, normalized, result)
                conn.commit()
                return result
        except sqlite3.IntegrityError as exc:
            return SqlExecutionResult(
                success=False,
                message=f"Database conflict: {exc}",
                conflict=True,
            )
        except sqlite3.Error as exc:
            return SqlExecutionResult(
                success=False,
                message=f"Database error: {exc}",
                conflict=False,
            )

    def _validate_tool_call(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(tool_call, dict):
            raise ValueError("SQL tool call must be a JSON object.")

        action = str(tool_call.get("action", "")).lower().strip()
        table = str(tool_call.get("table", "")).lower().strip()
        fields = tool_call.get("fields")
        parameters = tool_call.get("parameters") or {}

        if action not in self.ALLOWED_ACTIONS:
            raise ValueError(f"Unsupported action '{action}'. Allowed: insert, update.")

        if table not in self.TABLE_COLUMNS:
            allowed = ", ".join(sorted(self.TABLE_COLUMNS))
            raise ValueError(f"Table '{table}' is not allowed. Allowed tables: {allowed}.")

        if not isinstance(fields, dict) or not fields:
            raise ValueError("'fields' must be a non-empty object.")

        if not isinstance(parameters, dict):
            raise ValueError("'parameters' must be an object when provided.")

        allowed_cols = self.TABLE_COLUMNS[table]
        clean_fields: Dict[str, Any] = {}
        for key, value in fields.items():
            col = str(key).lower().strip()
            if col not in allowed_cols:
                raise ValueError(
                    f"Column '{col}' is not allowed on table '{table}'."
                )
            clean_fields[col] = value

        where_clause: Dict[str, Any] = {}
        raw_where = tool_call.get("where") or parameters.get("where") or {}
        if action == "update":
            if not isinstance(raw_where, dict) or not raw_where:
                raise ValueError("'where' is required for update operations.")
            for key, value in raw_where.items():
                col = str(key).lower().strip()
                if col not in allowed_cols and col != "id":
                    raise ValueError(
                        f"Where column '{col}' is not allowed on table '{table}'."
                    )
                where_clause[col] = value

        if action == "insert":
            self._check_required_fields(table, clean_fields)

        return {
            "action": action,
            "table": table,
            "fields": clean_fields,
            "where": where_clause,
            "parameters": parameters,
        }

    def _check_required_fields(self, table: str, fields: Dict[str, Any]) -> None:
        required = {
            "caliber_specs": {"caliber_number", "specification"},
            "electrical_diagrams": {"diagram_id", "title"},
            "documents": {"title", "doc_type", "content"},
        }[table]

        missing = required - set(fields.keys())
        if missing:
            raise ValueError(
                f"Missing required fields for {table}: {', '.join(sorted(missing))}"
            )

    def _execute_insert(
        self,
        conn: sqlite3.Connection,
        table: str,
        fields: Dict[str, Any],
    ) -> SqlExecutionResult:
        unique_col = self.UNIQUE_KEYS.get(table)
        if unique_col and unique_col in fields:
            existing = conn.execute(
                f"SELECT id FROM {table} WHERE {unique_col} = ?",
                (fields[unique_col],),
            ).fetchone()
            if existing:
                return SqlExecutionResult(
                    success=False,
                    message=(
                        f"Conflict: {unique_col}='{fields[unique_col]}' already exists "
                        f"in {table} (id={existing['id']})."
                    ),
                    conflict=True,
                )

        columns = list(fields.keys())
        placeholders = ", ".join("?" for _ in columns)
        col_sql = ", ".join(columns)
        values = [fields[col] for col in columns]

        cursor = conn.execute(
            f"INSERT INTO {table} ({col_sql}) VALUES ({placeholders})",
            values,
        )
        row_id = cursor.lastrowid
        return SqlExecutionResult(
            success=True,
            message=f"Inserted 1 row into {table} (id={row_id}).",
            rows_affected=1,
            data={"id": row_id, **fields},
        )

    def _execute_update(
        self,
        conn: sqlite3.Connection,
        table: str,
        fields: Dict[str, Any],
        where_clause: Dict[str, Any],
    ) -> SqlExecutionResult:
        if not fields:
            raise ValueError("Update requires at least one field.")

        unique_col = self.UNIQUE_KEYS.get(table)
        if unique_col and unique_col in fields:
            conflict = conn.execute(
                f"SELECT id FROM {table} WHERE {unique_col} = ? "
                f"AND id != COALESCE(?, id)",
                (fields[unique_col], where_clause.get("id")),
            ).fetchone()
            if conflict:
                return SqlExecutionResult(
                    success=False,
                    message=(
                        f"Conflict: {unique_col}='{fields[unique_col]}' already exists "
                        f"in {table} (id={conflict['id']})."
                    ),
                    conflict=True,
                )

        set_sql = ", ".join(f"{col} = ?" for col in fields)
        where_sql = " AND ".join(f"{col} = ?" for col in where_clause)
        params = list(fields.values()) + list(where_clause.values())

        cursor = conn.execute(
            f"UPDATE {table} SET {set_sql}, updated_at = datetime('now') "
            f"WHERE {where_sql}",
            params,
        )

        if cursor.rowcount == 0:
            return SqlExecutionResult(
                success=False,
                message="No rows matched the update criteria.",
                rows_affected=0,
                conflict=True,
            )

        return SqlExecutionResult(
            success=True,
            message=f"Updated {cursor.rowcount} row(s) in {table}.",
            rows_affected=cursor.rowcount,
            data={"where": where_clause, "fields": fields},
        )

    def _write_audit_log(
        self,
        conn: sqlite3.Connection,
        action: str,
        table: str,
        payload: Dict[str, Any],
        result: SqlExecutionResult,
    ) -> None:
        conn.execute(
            """
            INSERT INTO audit_log (action, table_name, payload_json, success, message)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                action,
                table,
                json.dumps(payload),
                1 if result.success else 0,
                result.message,
            ),
        )
