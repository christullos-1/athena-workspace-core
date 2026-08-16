# core/research/evidence.py

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class Evidence:
    """
    Base class for all evidence types used in Athena's research engine.
    Every fact Athena outputs must trace back to one or more Evidence objects.
    """

    text: str
    source_url: str
    excerpt: Optional[str] = None

    # Subclasses will set this in __post_init__
    source_type: str = "unknown"

    # Confidence scoring fields
    confidence_base: float = 0.0
    confidence_final: float = 0.0

    # Arbitrary metadata (timestamps, video IDs, publication dates, etc.)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def set_final_confidence(self, value: float) -> None:
        """Assign the final confidence score after modifiers are applied."""
        self.confidence_final = max(0.0, min(1.0, value))

    def summary(self) -> str:
        """Short human-readable summary for debugging and logs."""
        return (
            f"[{self.source_type}] {self.source_url} "
            f"(base={self.confidence_base:.2f}, final={self.confidence_final:.2f})"
        )

@dataclass
class TranscriptEvidence(Evidence):
    """
    Evidence derived from YouTube transcripts.
    Includes timestamps and video metadata.
    """

    def __post_init__(self):
        self.source_type = "youtube_transcript"
        # If ASR auto-captions, base confidence is lower
        if self.metadata.get("is_auto_generated", False):
            self.confidence_base = 0.65
        else:
            self.confidence_base = 0.80


@dataclass
class WebEvidence(Evidence):
    """
    Evidence derived from webpage fetchers.
    Includes domain, snippet, and publication metadata.
    """

    def __post_init__(self):
        self.source_type = "webpage"

        domain = self.metadata.get("domain", "")
        if domain.endswith(".gov"):
            self.confidence_base = 0.90
        elif domain.endswith(".edu"):
            self.confidence_base = 0.88
        elif domain.endswith(".org"):
            self.confidence_base = 0.82
        else:
            self.confidence_base = 0.75


@dataclass
class PdfEvidence(Evidence):
    """
    Placeholder for future PDF/document evidence.
    """

    def __post_init__(self):
        self.source_type = "pdf_document"
        self.confidence_base = 0.85