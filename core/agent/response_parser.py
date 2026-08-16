# core/agent/response_parser.py

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ParsedAgenticResponse:
    thought_process: str
    final_response: str
    sql_tool_call: Optional[Dict[str, Any]]
    raw: str


class ResponseParser:
    """
    Parses structured agentic model output blocks.
    """

    THOUGHT_PATTERN = re.compile(
        r"<THOUGHT_PROCESS>\s*(.*?)\s*</THOUGHT_PROCESS>",
        re.DOTALL | re.IGNORECASE,
    )
    FINAL_PATTERN = re.compile(
        r"<FINAL_RESPONSE>\s*(.*?)\s*</FINAL_RESPONSE>",
        re.DOTALL | re.IGNORECASE,
    )
    SQL_PATTERN = re.compile(
        r"<SQL_TOOL_CALL>\s*(.*?)\s*</SQL_TOOL_CALL>",
        re.DOTALL | re.IGNORECASE,
    )

    @classmethod
    def parse(cls, raw: str) -> ParsedAgenticResponse:
        thought = cls._extract(cls.THOUGHT_PATTERN, raw)
        final = cls._extract(cls.FINAL_PATTERN, raw)
        sql_raw = cls._extract(cls.SQL_PATTERN, raw)
        sql_tool_call = cls._parse_sql_json(sql_raw)

        if not final:
            final = cls._fallback_final(raw, thought)

        if not thought:
            thought = "No explicit THOUGHT_PROCESS block was provided by the model."

        return ParsedAgenticResponse(
            thought_process=thought.strip(),
            final_response=final.strip(),
            sql_tool_call=sql_tool_call,
            raw=raw,
        )

    @staticmethod
    def _extract(pattern: re.Pattern, text: str) -> str:
        match = pattern.search(text or "")
        return match.group(1).strip() if match else ""

    @classmethod
    def _parse_sql_json(cls, sql_raw: str) -> Optional[Dict[str, Any]]:
        if not sql_raw:
            return None

        candidate = sql_raw.strip()
        if candidate.startswith("```"):
            candidate = re.sub(r"^```(?:json)?\s*", "", candidate)
            candidate = re.sub(r"\s*```$", "", candidate)

        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        json_match = re.search(r"\{.*\}", candidate, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group(0))
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                return None
        return None

    @staticmethod
    def _fallback_final(raw: str, thought: str) -> str:
        cleaned = raw
        for pattern in (
            ResponseParser.THOUGHT_PATTERN,
            ResponseParser.SQL_PATTERN,
        ):
            cleaned = pattern.sub("", cleaned)
        cleaned = cleaned.strip()
        if cleaned:
            return cleaned
        if thought:
            return (
                "I analyzed the request internally but could not produce a "
                "structured FINAL_RESPONSE block."
            )
        return raw.strip()
