# core/research/engine.py

from __future__ import annotations
from typing import List, Dict, Any

from core.research.evidence import Evidence, TranscriptEvidence, WebEvidence
from core.research.synthesis import SynthesisEngine
from core.tools.youtube_transcript import YouTubeTranscriptFetcher
from core.tools.web_fetcher import WebFetcher


class ResearchEngine:
    """
    High-level orchestrator for Athena's research pipeline.
    Responsibilities:
      - Run fetchers
      - Normalize results into Evidence objects
      - Score evidence
      - Synthesize final answer
      - Attach citations + confidence
    """

    def __init__(self):
        self.synth = SynthesisEngine()
        self.transcript_fetcher = YouTubeTranscriptFetcher()
        self.web_fetcher = WebFetcher()

    # ------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------

    def research(self, query: str) -> Dict[str, Any]:
        """
        Main entry point for Athena's research engine.
        Returns:
          {
            "answer": str,
            "citations": [...],
            "confidence": float
          }
        """

        # Step 1: Run fetchers
        raw_results = self._run_fetchers(query)

        # Step 2: Convert raw results into Evidence objects
        evidence_list = self._normalize_evidence(raw_results)

        # Step 3: Synthesize final answer
        result = self.synth.synthesize(evidence_list)

        return result

    # ------------------------------------------------------------
    # INTERNAL METHODS
    # ------------------------------------------------------------

    def _run_fetchers(self, query: str) -> Dict[str, Any]:
        """
        Executes all fetchers and returns raw results.
        """

        results = {
            "transcript": None,
            "web": None,
        }

        # Transcript fetcher
        try:
            results["transcript"] = self.transcript_fetcher.fetch(query)
        except Exception:
            results["transcript"] = None

        # Web fetcher
        try:
            results["web"] = self.web_fetcher.fetch(query)
        except Exception:
            results["web"] = None

        return results

    def _normalize_evidence(self, raw: Dict[str, Any]) -> List[Evidence]:
        """
        Converts raw fetcher output into Evidence objects.
        """

        evidence_list: List[Evidence] = []

        # Transcript evidence
        if raw.get("transcript") and raw["transcript"].get("segments"):
            for seg in raw["transcript"]["segments"]:
                ev = TranscriptEvidence(
                    text=seg["text"],
                    source_url=raw["transcript"]["url"],
                    excerpt=seg["text"],
                    metadata={
                        "start": seg.get("start"),
                        "end": seg.get("end"),
                        "video_id": raw["transcript"].get("video_id"),
                        "is_auto_generated": raw["transcript"].get("auto_generated", False),
                    }
                )
                evidence_list.append(ev)

        # Web evidence
        if raw.get("web") and raw["web"].get("pages"):
            for page in raw["web"]["pages"]:
                ev = WebEvidence(
                    text=page.get("content", ""),
                    source_url=page.get("url", ""),
                    excerpt=page.get("snippet", ""),
                    metadata={
                        "domain": page.get("domain", ""),
                        "published_date": page.get("published_date"),
                    }
                )
                evidence_list.append(ev)

        return evidence_list