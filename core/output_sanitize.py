# core/output_sanitize.py

import re

from core.horology_lubrication import (
    detect_primary_topic,
    filter_off_topic_lines,
    validate_lubricant_mentions,
)

FINAL_RESPONSE_PATTERN = re.compile(
    r"<FINAL_RESPONSE>\s*(.*?)\s*</FINAL_RESPONSE>",
    re.IGNORECASE | re.DOTALL,
)

LEAKED_CHUNK_MARKERS = (
    "LOCAL DOCUMENT REFTXT",
    "SYSTEM CONTEXT ALERT",
    "SAFETY CRITICAL RULE",
    "HIDDEN SAFETY RULE",
    "SAFETY CORRECTION",
    "MODERN CROSS-REFERENCE",
    "Modern Cross-Reference (live)",
    "Live Context ---",
    "LITERATURE CROSS-REFERENCE",
    "VINTAGE vs. MODERN",
    "HIERARCHICAL LUBRICATION MATRIX",
    "SINGLE-TOPIC LOCK",
    "HIDDEN CONTEXT",
    "developer rule",
    "<FINAL_RESPONSE>",
    "</FINAL_RESPONSE>",
    "THOUGHT_PROCESS",
    "<SQL_TOOL_CALL>",
    "USER-VISIBLE OUTPUT ONLY",
    "mandatory — never",
)

STRUCTURAL_TAG_PATTERN = re.compile(
    r"</?(?:FINAL_RESPONSE|THOUGHT_PROCESS|SQL_TOOL_CALL)[^>]*>",
    re.IGNORECASE,
)

ROBOTIC_PREFIX_PATTERN = re.compile(
    r"^(?:Sure!|Certainly!|Of course!|I'd be happy to|Here is|Here's|Let me|As an AI).*?\n",
    re.IGNORECASE | re.MULTILINE,
)

SECTION_HEADER_PATTERN = re.compile(
    r"^(Required Tools:|Specific Lubricants:|Step-by-Step Application:)",
    re.IGNORECASE,
)


def _normalize_mobile_spacing(text: str) -> str:
    """Ensure generous vertical spacing for mobile markdown readability."""
    if not text:
        return ""

    output: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            if output and output[-1] != "":
                output.append("")
            continue

        if SECTION_HEADER_PATTERN.match(stripped):
            if output and output[-1] != "":
                output.append("")
            output.append(stripped)
            output.append("")
            continue

        if stripped.startswith(("-", "•", "*")) or re.match(r"^\d+\.", stripped):
            output.append(stripped)
            output.append("")
            continue

        output.append(stripped)

    return re.sub(r"\n{3,}", "\n\n", "\n".join(output)).strip()


def is_leaked_stream_chunk(token: str) -> bool:
    """Drop model tokens that echo hidden context or structural tags."""
    if not token or not token.strip():
        return True

    upper = token.upper()
    return any(marker.upper() in upper for marker in LEAKED_CHUNK_MARKERS)


def sanitize_model_output(text: str, prompt: str = "") -> str:
    """Strip leaks, off-topic sections, and structural noise from a completed reply."""
    if not text:
        return ""

    topic = detect_primary_topic(prompt)

    match = FINAL_RESPONSE_PATTERN.search(text)
    if match and match.group(1).strip():
        text = match.group(1).strip()

    text = FINAL_RESPONSE_PATTERN.sub("", text)
    text = STRUCTURAL_TAG_PATTERN.sub("", text)
    text = ROBOTIC_PREFIX_PATTERN.sub("", text)

    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            lines.append("")
            continue
        if any(marker.upper() in stripped.upper() for marker in LEAKED_CHUNK_MARKERS):
            continue
        if stripped.startswith("⚠️"):
            continue
        lines.append(line)

    cleaned = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    cleaned = _normalize_mobile_spacing(cleaned)
    cleaned = filter_off_topic_lines(cleaned, topic)

    violations = validate_lubricant_mentions(cleaned, topic)
    if violations:
        print(f"[Output Sanitize] Lubricant violations: {violations}")

    return cleaned


def build_shellac_correction_prompt() -> str:
    """Hidden continuation instruction — balance/hairspring cleaning only."""
    return (
        "Rewrite ONLY the balance/hairspring cleaning steps using shellac-safe fluorocarbon "
        "or petroleum ether/hexane. Use the three-section bench format. "
        "Do not mention mainsprings or barrel grease."
    )
