# core/classifiers/technical_classifier.py

import re


class TechnicalQueryClassifier:
    """
    Determines whether a user message is a technical query.
    Returns:
        "technical" or "nontechnical"
    """

    TECH_KEYWORDS = [
        # programming languages
        "python", "java", "c++", "c#", "javascript", "typescript", "go", "rust",
        "ruby", "php", "swift", "kotlin",

        # frameworks / libraries
        "react", "django", "flask", "fastapi", "node", "express",
        "pytorch", "tensorflow", "sklearn",

        # debugging / errors
        "error", "exception", "traceback", "stack trace", "undefined",
        "nullpointer", "segfault", "crash", "bug",

        # commands / terminals
        "bash", "shell", "terminal", "cmd", "powershell",

        # file paths
        "/", "\\", ".py", ".js", ".json", ".yaml", ".yml",

        # architecture
        "api", "endpoint", "server", "client", "database", "sql",
        "schema", "docker", "container", "kubernetes",
    ]

    CODE_PATTERN = re.compile(r"[{};=<>]|```|def |class |import ")

    def classify(self, message: str) -> str:
        msg = message.lower()

        # 1. Code-like patterns
        if self.CODE_PATTERN.search(msg):
            return "technical"

        # 2. Keyword match
        for kw in self.TECH_KEYWORDS:
            if kw in msg:
                return "technical"

        return "nontechnical"