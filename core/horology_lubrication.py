# core/horology_lubrication.py

import re
from typing import List, Optional, Set

LUBRICATION_MATRIX = """
HIERARCHICAL LUBRICATION MATRIX (mandatory — validate every lubricant mention):
- Mainspring Coils (manual/automatic): Moebius 8200 or specialized mainspring grease ONLY.
- Automatic Barrel Walls: Moebius 8217 or Klüber P125 brake grease ONLY.
- Balance Pivots / Escape Teeth: Moebius 9010 ONLY.

NEVER apply 9010 to mainsprings. NEVER apply 8200/8217 to balance pivots or escape teeth.
"""

CONCISE_BENCH_FORMAT = """
User-visible output ONLY — exactly these three sections, nothing else:

Required Tools:
- (bulleted list)

Specific Lubricants:
- (component: exact product only — per lubrication matrix)

Step-by-Step Application:
1. (numbered steps only)
"""

MOBILE_MARKDOWN_FORMAT = """
MOBILE MARKDOWN (mandatory for every user-visible reply):
- Put a blank line (double line break) before and after each section header.
- Put a blank line between every bullet item and between every numbered step.
- Keep one idea per line — no dense paragraph walls.
- Write for a vertical phone screen (Opera mobile): short blocks, generous spacing.
"""

TOPIC_MAINSPRING = "mainspring"
TOPIC_BARREL = "barrel"
TOPIC_BALANCE = "balance_escapement"
TOPIC_GENERAL = "general"

MAINSRING_TOPIC_TERMS = (
    "mainspring",
    "mainspring barrel",
    "barrel wall",
    "barrel arbor",
    "mainspring grease",
    "8200",
    "8217",
    "kluber p125",
    "p125",
)

BALANCE_TOPIC_TERMS = (
    "balance wheel",
    "balance assembly",
    "hairspring",
    "escapement",
    "pallet fork",
    "roller jewel",
    "9010",
    "escape tooth",
)

MAINSRING_OFF_TOPIC_TERMS = (
    "balance wheel",
    "balance assembly",
    "hairspring",
    "hair spring",
    "ultrasonic",
    "pallet fork",
    "roller jewel",
    "pallet stone",
    "escapement",
    "moebius 9010",
    "9010",
    "one-dip",
    "fluorocarbon",
    "shellac",
    "degreas the balance",
    "clean the balance",
)

CLEANING_TOPIC_TERMS = (
    "clean",
    "degreas",
    "rinse",
    "solvent",
    "ultrasonic",
    "one-dip",
    "acetone",
    "ethanol",
)


def detect_primary_topic(prompt: str) -> str:
    lower = (prompt or "").lower()
    if any(term in lower for term in MAINSRING_TOPIC_TERMS):
        return TOPIC_MAINSPRING
    if any(term in lower for term in BALANCE_TOPIC_TERMS):
        return TOPIC_BALANCE
    if "barrel" in lower and "mainspring" not in lower:
        return TOPIC_BARREL
    return TOPIC_GENERAL


def is_cleaning_related(prompt: str) -> bool:
    lower = (prompt or "").lower()
    return any(term in lower for term in CLEANING_TOPIC_TERMS)


def build_hidden_horology_context(topic: str) -> str:
    sections = [
        LUBRICATION_MATRIX.strip(),
        CONCISE_BENCH_FORMAT.strip(),
        MOBILE_MARKDOWN_FORMAT.strip(),
    ]

    if topic == TOPIC_MAINSPRING:
        sections.append(
            "SINGLE-TOPIC LOCK: User asked about MAINSPRING/BARREL lubrication only. "
            "Do NOT mention balance wheels, hairsprings, ultrasonic cleaning, pallet forks, "
            "escapements, or balance degreasing procedures."
        )
    elif topic == TOPIC_BALANCE:
        sections.append(
            "SINGLE-TOPIC LOCK: User asked about balance/escapement work only. "
            "Do NOT mention mainspring barrel grease or automatic barrel wall lubrication."
        )

    return "\n\n".join(sections)


def _line_is_off_topic(line: str, topic: str) -> bool:
    lower = line.lower()
    if topic != TOPIC_MAINSPRING:
        return False
    return any(term in lower for term in MAINSRING_OFF_TOPIC_TERMS)


def filter_off_topic_lines(text: str, topic: str) -> str:
    """Remove lines about balance/hairspring when user asked about mainsprings."""
    if not text or topic != TOPIC_MAINSPRING:
        return text

    kept: List[str] = []
    skip_section = False

    for line in text.splitlines():
        stripped = line.strip()
        lower = stripped.lower()

        if lower.startswith("required tools"):
            skip_section = False
        elif lower.startswith("specific lubricants"):
            skip_section = False
        elif lower.startswith("step-by-step"):
            skip_section = False
        elif any(
            header in lower
            for header in (
                "balance cleaning",
                "hairspring",
                "degreasing the balance",
                "cleaning the balance",
                "ultrasonic",
            )
        ):
            skip_section = True

        if skip_section:
            continue
        if _line_is_off_topic(stripped, topic):
            continue
        kept.append(line)

    return re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()


def validate_lubricant_mentions(text: str, topic: str) -> List[str]:
    """Return human-readable violations for post-check logging."""
    lower = (text or "").lower()
    violations: List[str] = []

    if topic in {TOPIC_MAINSPRING, TOPIC_BARREL, TOPIC_GENERAL}:
        if re.search(r"\b9010\b", lower) and any(
            term in lower for term in ("mainspring", "barrel", "coil")
        ):
            violations.append("9010 incorrectly assigned to mainspring/barrel")

    if topic == TOPIC_MAINSPRING:
        if "8217" in lower and "barrel wall" not in lower and "automatic" not in lower:
            violations.append("8217 mentioned outside automatic barrel wall context")

    return violations
