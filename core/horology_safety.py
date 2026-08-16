# core/horology_safety.py

import re
from typing import Optional, Tuple


SHELLAC_SAFETY_RULE = (
    "SAFETY CRITICAL RULE: You must never recommend using acetone, ethanol, "
    "denatured alcohol, or water baths on complete balance assemblies or pallet "
    "forks, as these solvents dissolve the foundational shellac holding roller "
    "jewels and pallet stones, and water causes flash-rusting on steel hairsprings. "
    "For hairspring/balance degreasing, you must strictly mandate specialized "
    "volatile fluorocarbon cleaners (like Zenith One-Dip or petroleum ether/hexane "
    "rinses) that protect shellac and leave zero moisture residue."
)

SHELLAC_SAFETY_CORRECTION = (
    "\n\n⚠️ SAFETY CORRECTION — SHELLAC / HAIRSPRING PROTECTION:\n"
    "Do NOT use acetone, ethanol, denatured alcohol, isopropyl alcohol, or water "
    "baths on complete balance assemblies, hairsprings, roller jewels, or pallet "
    "forks. These dissolve shellac seatings and cause flash-rust on steel springs.\n"
    "Approved degreasing for balance/hairspring work: specialized volatile "
    "fluorocarbon cleaners (e.g. Zenith One-Dip) or petroleum ether / hexane "
    "rinses only — zero moisture residue, shellac-safe.\n"
)

PROHIBITED_SOLVENTS = (
    "acetone",
    "ethanol",
    "ethyl alcohol",
    "denatured alcohol",
    "methylated spirit",
    "isopropyl alcohol",
    "rubbing alcohol",
    " ipa ",
)

PROHIBITED_AQUEOUS = (
    "water bath",
    "distilled water",
    " deionized water",
    " warm water",
    " soapy water",
    " ultrasonic water",
)

PROTECTED_COMPONENTS = (
    "balance assembly",
    "balance wheel",
    "balance complete",
    "hairspring",
    "hair spring",
    "roller jewel",
    "roller table",
    "pallet fork",
    "pallet jewels",
    "escapement",
    "staff",
)

CLEANING_INTENT_MARKERS = (
    "clean",
    "degreas",
    "rinse",
    "solvent",
    "wash",
    "bath",
    "ultrasonic",
    "dip",
    "wipe down",
    "remove oil",
    "strip oil",
)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def _mentions_cleaning(text: str) -> bool:
    lower = _normalize(text)
    return any(marker in lower for marker in CLEANING_INTENT_MARKERS)


def _mentions_protected_components(text: str) -> bool:
    lower = _normalize(text)
    if any(component in lower for component in PROTECTED_COMPONENTS):
        return True
    # Shorthand horology terms in cleaning context.
    return bool(re.search(r"\bbalance\b", lower)) or bool(re.search(r"\bhair\s*spring\b", lower))


def _mentions_prohibited_solvents(text: str) -> bool:
    lower = f" {_normalize(text)} "
    return any(solvent in lower for solvent in PROHIBITED_SOLVENTS)


def _mentions_prohibited_aqueous_on_components(text: str) -> bool:
    lower = f" {_normalize(text)} "
    has_aqueous = any(term in lower for term in PROHIBITED_AQUEOUS) or re.search(
        r"\bwater\b", lower
    )
    return bool(has_aqueous and _mentions_protected_components(text))


def validate_shellac_safety(text: str) -> Tuple[bool, Optional[str]]:
    """
    Return (is_safe, correction_text).
    correction_text is populated when a shellac/hairspring safety violation is found.
    """
    if not text or not _mentions_cleaning(text):
        return True, None

    lower = _normalize(text)
    component_context = _mentions_protected_components(text)
    solvent_violation = _mentions_prohibited_solvents(text) and component_context
    aqueous_violation = _mentions_prohibited_aqueous_on_components(text)

    # Catch explicit multi-solvent bench recipes even if component wording is loose.
    recipe_pattern = re.search(
        r"(acetone|ethanol|denatured alcohol).{0,80}(water|distilled water)",
        lower,
    )
    if recipe_pattern and _mentions_cleaning(text):
        return False, SHELLAC_SAFETY_CORRECTION

    if solvent_violation or aqueous_violation:
        return False, SHELLAC_SAFETY_CORRECTION

    return True, None


def enforce_shellac_safety(text: str) -> str:
    """Append mandatory correction block when a violation is detected."""
    is_safe, correction = validate_shellac_safety(text)
    if is_safe or not correction:
        return text
    if correction.strip() in text:
        return text
    return f"{text.rstrip()}{correction}"
