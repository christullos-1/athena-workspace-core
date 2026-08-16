# core/agent/task_classifier.py

import re


class AgenticTaskClassifier:
    """
    Determines when LogicLoop should use the Reflection + Tool-Execution pipeline.
    """

    DATABASE_KEYWORDS = [
        "database", "sqlite", "sql", "table", "record", "insert", "update",
        "delete", "store", "save to db", "write to db", "add to database",
        "caliber_specs", "electrical_diagrams", "documents table",
    ]

    COMPLEXITY_SIGNALS = [
        "design", "architecture", "migrate", "orchestrat", "pipeline",
        "multi-step", "constraint", "conflict", "transaction", "schema",
        "debug", "traceback", "exception", "error", "implement", "refactor",
    ]

    FACTUAL_DOMAIN_KEYWORDS = [
        "caliber", "gauge", "wiring", "diagram", "schematic", "electrical",
        "pinout", "specification", "ballistic", "cartridge",
    ]

    CODE_PATTERN = re.compile(r"[{};=<>]|```|def |class |import ")

    def needs_agentic_pipeline(self, message: str) -> bool:
        if not message or not isinstance(message, str):
            return False

        lower = message.lower().strip()
        is_technical = self._is_technical(lower)
        is_database = any(kw in lower for kw in self.DATABASE_KEYWORDS)
        is_complex = any(sig in lower for sig in self.COMPLEXITY_SIGNALS)
        is_factual_domain = any(kw in lower for kw in self.FACTUAL_DOMAIN_KEYWORDS)

        if is_database:
            return True
        if is_factual_domain and (is_technical or is_complex):
            return True
        if is_technical and is_complex:
            return True
        if is_technical and len(message.split()) >= 12:
            return True
        return False

    def _is_technical(self, lower_message: str) -> bool:
        if self.CODE_PATTERN.search(lower_message):
            return True

        tech_terms = [
            "python", "api", "server", "client", "function", "module",
            "database", "sql", "error", "bug", "stack trace",
        ]
        return any(term in lower_message for term in tech_terms)
