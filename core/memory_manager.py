# core/memory_manager.py

import json
import os

class MemoryManager:
    """
    Handles persistent long-term memory for Athena.
    Stores user facts across sessions.
    """

    def __init__(self, memory_file="memory/long_term_memory.json"):
        self.memory_file = memory_file
        self._ensure_file()

    def _ensure_file(self):
        if not os.path.exists(self.memory_file):
            os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)
            with open(self.memory_file, "w") as f:
                json.dump({"facts": []}, f)

    def load(self):
        with open(self.memory_file, "r") as f:
            return json.load(f)

    def save(self, data):
        with open(self.memory_file, "w") as f:
            json.dump(data, f, indent=4)

    def add_fact(self, fact: str):
        data = self.load()
        if fact not in data["facts"]:
            data["facts"].append(fact)
            self.save(data)

    def get_facts(self):
        data = self.load()
        return data["facts"]