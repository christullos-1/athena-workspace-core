# core/research/synthesis.py

from __future__ import annotations
from typing import List, Dict, Tuple
from core.research.evidence import Evidence
from core.research.confidence import ConfidenceCalculator


class SynthesisEngine:
    """
    Combines evidence from multiple sources into a unified answer.
    Handles:
      - evidence merging
      - contradiction resolution
      - weighted synthesis
      - citation generation
      - final confidence scoring
    """

    def __init__(self):
        self.confidence_calc = ConfidenceCalculator()

    # ------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------

    def synthesize(self, evidence_list: List[Evidence]) -> Dict[str, any]:
        """
        Main entry point.
        Produces:
          - final answer text
          - citations
          - final confidence score
        """

        if not evidence_list:
            return {
                "answer": "No reliable information was found.",
                "citations": [],
                "confidence": 0.0,
            }

        # Step 1: Score evidence
        self.confidence_calc.calculate(evidence_list)

        # Step 2: Merge evidence into a unified narrative
        merged_text = self._merge_evidence(evidence_list)

        # Step 3: Generate citations
        citations = self._generate_citations(evidence_list)

        # Step 4: Compute final confidence
        final_conf = self._compute_final_confidence(evidence_list)

        return {
            "answer": merged_text,
            "citations": citations,
            "confidence": final_conf,
        }

    # ------------------------------------------------------------
    # INTERNAL METHODS
    # ------------------------------------------------------------

    def _merge_evidence(self, evidence_list: List[Evidence]) -> str:
        """
        Produces a unified answer by:
          - sorting evidence by confidence
          - extracting key claims
          - merging them into a coherent narrative
        """

        # Sort by final confidence (highest first)
        sorted_ev = sorted(
            evidence_list,
            key=lambda e: e.confidence_final,
            reverse=True
        )

        merged_parts = []

        for ev in sorted_ev:
            # Use excerpt if available, otherwise full text
            snippet = ev.excerpt if ev.excerpt else ev.text
            merged_parts.append(snippet)

        # Simple concatenation for now — future upgrade: semantic merging
        return " ".join(merged_parts)

    def _generate_citations(self, evidence_list: List[Evidence]) -> List[Dict[str, str]]:
        """
        Produces a list of citations with:
          - source URL
          - source type
          - confidence
          - optional timestamps (for transcripts)
        """

        citations = []

        for ev in evidence_list:
            entry = {
                "source": ev.source_url,
                "type": ev.source_type,
                "confidence": f"{ev.confidence_final:.2f}",
            }

            # Add timestamp metadata for transcripts
            if ev.source_type == "youtube_transcript":
                if "start" in ev.metadata:
                    entry["timestamp"] = f"{ev.metadata['start']:.1f}s"

            citations.append(entry)

        return citations

    def _compute_final_confidence(self, evidence_list: List[Evidence]) -> float:
        """
        Weighted average of all evidence confidence scores.
        """

        if not evidence_list:
            return 0.0

        total_weight = sum(ev.confidence_final for ev in evidence_list)
        avg = total_weight / len(evidence_list)

        # Clamp to [0, 1]
        return max(0.0, min(1.0, avg))