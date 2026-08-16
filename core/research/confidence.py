# core/research/confidence.py

from __future__ import annotations
from typing import List, Dict
from datetime import datetime
from core.research.evidence import Evidence


class ConfidenceCalculator:
    """
    Computes final confidence scores for sets of Evidence objects.
    This is the core of Athena's reliability and traceability.
    """

    AGREEMENT_BONUS = 0.05
    CONTRADICTION_PENALTY = 0.10
    RECENCY_BONUS = 0.10  # Only applied if metadata contains a recent timestamp
    RECENT_THRESHOLD_DAYS = 365

    def calculate(self, evidence_list: List[Evidence]) -> None:
        """
        Applies all modifiers and assigns final confidence scores
        to each Evidence object in the list.
        """
        if not evidence_list:
            return

        # Step 1: Apply recency bonuses
        for ev in evidence_list:
            self._apply_recency_bonus(ev)

        # Step 2: Detect agreement/contradiction patterns
        self._apply_agreement_and_contradiction(evidence_list)

        # Step 3: Clamp and finalize
        for ev in evidence_list:
            ev.set_final_confidence(ev.confidence_base)

    def _apply_recency_bonus(self, ev: Evidence) -> None:
        """
        If the evidence has a publication or creation date,
        apply a recency bonus if it's within the threshold.
        """
        date_str = ev.metadata.get("published_date")
        if not date_str:
            return

        try:
            published = datetime.fromisoformat(date_str)
            delta = datetime.now() - published
            if delta.days <= self.RECENT_THRESHOLD_DAYS:
                ev.confidence_base += self.RECENCY_BONUS
        except Exception:
            # Ignore malformed dates
            pass

    def _apply_agreement_and_contradiction(self, evidence_list: List[Evidence]) -> None:
        """
        Simple heuristic:
        - If multiple evidence items contain similar text, apply agreement bonus.
        - If they contradict (negation or conflicting claims), apply penalty.
        """

        texts = [ev.text.lower() for ev in evidence_list]

        for i, ev in enumerate(evidence_list):
            for j, other in enumerate(evidence_list):
                if i == j:
                    continue

                if self._is_agreement(ev.text, other.text):
                    ev.confidence_base += self.AGREEMENT_BONUS

                if self._is_contradiction(ev.text, other.text):
                    ev.confidence_base -= self.CONTRADICTION_PENALTY

    def _is_agreement(self, a: str, b: str) -> bool:
        """
        Very simple heuristic for agreement:
        - Shared key phrases
        - Overlapping content
        """
        a_words = set(a.lower().split())
        b_words = set(b.lower().split())
        overlap = a_words.intersection(b_words)
        return len(overlap) >= 5  # Tunable threshold

    def _is_contradiction(self, a: str, b: str) -> bool:
        """
        Simple contradiction detection:
        - Negation patterns
        - Opposing claims
        """
        a_low = a.lower()
        b_low = b.lower()

        negation_patterns = [
            ("is", "is not"),
            ("are", "are not"),
            ("has", "has not"),
            ("did", "did not"),
        ]

        for pos, neg in negation_patterns:
            if pos in a_low and neg in b_low:
                return True
            if neg in a_low and pos in b_low:
                return True

        return False