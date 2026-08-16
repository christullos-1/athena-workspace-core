-- Athena local SQLite schema
-- Tables are whitelisted in sql_executor.py

CREATE TABLE IF NOT EXISTS caliber_specs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    caliber_number TEXT NOT NULL UNIQUE,
    specification TEXT NOT NULL,
    source_doc TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS electrical_diagrams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    diagram_id TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    description TEXT,
    file_path TEXT,
    metadata_json TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    doc_type TEXT NOT NULL,
    content TEXT NOT NULL,
    tags TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,
    table_name TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    success INTEGER NOT NULL,
    message TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
