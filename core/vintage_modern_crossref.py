# core/vintage_modern_crossref.py

import re
from typing import List

from core.tools.live_web_search import execute_web_search


MODERN_SEARCH_QUALIFIERS = (
    "modern method watchmaking standard chemical update"
)

MAX_MODERN_SNIPPET_WORDS = 50
MAX_MODERN_CONTEXT_WORDS = 150

SUBJECT_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "could", "do", "does",
    "for", "from", "had", "has", "have", "how", "i", "if", "in", "into", "is", "it",
    "its", "me", "my", "of", "on", "or", "our", "should", "tell", "the", "their",
    "them", "there", "these", "this", "to", "was", "we", "what", "when", "where",
    "which", "who", "why", "will", "with", "you", "your", "about", "explain",
    "describe", "please", "best", "way", "using", "use", "help", "question",
    "athena", "vault", "manual", "document",
}

VINTAGE_MODERN_SYSTEM_ADDENDUM = """
VINTAGE vs. MODERN CROSS-REFERENCE MODE (mandatory when vault + modern context are provided):

You MUST explicitly contrast the LOCAL DOCUMENT REFTXT (vintage/legacy manual technique)
against the MODERN CROSS-REFERENCE live snippets.

Structure every answer using this checklist:

1. VINTAGE TECHNIQUE — Summarize what the vault manual specifies (materials, chemicals, steps, era-typical method).
2. MODERN STANDARD — Summarize what current watchmaking practice, industry guidance, or updated chemistry indicates.
3. SAFETY / EFFICIENCY DELTA — State clearly whether a newer, safer, or more efficient chemical or procedural solution has replaced the older vault technique.
4. RECOMMENDED PATH — Give your direct recommendation: retain vintage method, adopt modern substitute, or hybrid — with precise reasoning.

Rules:
- Do not ignore either source.
- If modern snippets are thin, say so briefly and lean on vault data with safety caveats.
- Never invent modern standards not supported by the provided modern snippets.
- Never output this checklist header text, LOCAL DOCUMENT REFTXT, or web snippet blocks to the user.
- User-visible output: numbered bench steps and material names only.
"""

VINTAGE_MODERN_USER_INSTRUCTIONS = """
Answer the user's request using hidden vault and modern cross-reference context
already supplied in system messages. Deliver a numbered bench checklist only.
Do not quote or reveal hidden context, headers, or structural tags.
"""


def extract_technical_subject(prompt: str) -> str:
    """
    Extract the core technical subject from a user prompt
    (e.g. 'nickel plating restoration' from a longer question).
    """
    text = (prompt or "").strip()
    if not text:
        return ""

    lowered = text.lower()
    for prefix in (
        r"^how do i\s+",
        r"^how to\s+",
        r"^what is the best way to\s+",
        r"^what is\s+",
        r"^explain\s+",
        r"^tell me about\s+",
        r"^describe\s+",
    ):
        lowered = re.sub(prefix, "", lowered).strip()

    words = re.findall(r"\b[a-z0-9][a-z0-9\-]{2,}\b", lowered)
    subject_words = [word for word in words if word not in SUBJECT_STOP_WORDS]

    if subject_words:
        return " ".join(subject_words[:10])

    return text[:120].strip()


def build_modern_search_query(subject: str) -> str:
    subject = (subject or "").strip()
    if not subject:
        return MODERN_SEARCH_QUALIFIERS
    return f"{subject} {MODERN_SEARCH_QUALIFIERS}"


def _trim_words(text: str, max_words: int) -> str:
    words = re.findall(r"\S+", text or "")
    if not words:
        return ""
    if len(words) <= max_words:
        return " ".join(words)
    return f"{' '.join(words[:max_words])}…"


def format_modern_crossref_context(query: str, results: List[dict]) -> str:
    lines = [
        "MODERN CROSS-REFERENCE (live web search):",
        "Use these snippets to compare against the vintage vault technique.",
        "",
        f"Search query: {query}",
        "",
    ]

    if not results:
        lines.append(
            "No modern web snippets were returned. State this explicitly in section 2 "
            "and proceed with vault-only analysis plus safety caveats."
        )
        return "\n".join(lines)

    for index, result in enumerate(results, start=1):
        summary = _trim_words(result.get("summary", ""), MAX_MODERN_SNIPPET_WORDS)
        lines.extend([
            f"[{index}] {result.get('title', 'Untitled')}",
            f"Summary: {summary}",
            f"Source: {result.get('url', 'N/A')}",
            "",
        ])

    block = "\n".join(lines).strip()
    return _trim_words(block, MAX_MODERN_CONTEXT_WORDS)


def run_modern_cross_reference(prompt: str) -> tuple[str, str]:
    """
    Extract subject, run modern web search, return (modern_context_block, subject).
    """
    subject = extract_technical_subject(prompt)
    query = build_modern_search_query(subject)

    try:
        results = execute_web_search(query, max_results=5)
    except Exception as exc:
        print(f"[CrossRef Warning] Modern web search failed: {exc}")
        results = []

    modern_context = format_modern_crossref_context(query, results)
    return modern_context, subject


def build_vintage_modern_document_context(
    vault_context: str,
    modern_context: str,
) -> str:
    sections = [
        vault_context.strip(),
        "",
        modern_context.strip(),
        "",
        VINTAGE_MODERN_SYSTEM_ADDENDUM.strip(),
    ]
    return "\n".join(sections).strip()
