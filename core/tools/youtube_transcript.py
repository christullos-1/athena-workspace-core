# core/tools/youtube_transcript.py

from __future__ import annotations
from typing import Dict, Any, List, Optional
import requests
import re


class YouTubeTranscriptFetcher:
    """
    Fetches YouTube transcripts using the timedtext endpoint.
    Produces a normalized structure compatible with Athena's research engine:
      {
        "url": str,
        "video_id": str,
        "auto_generated": bool,
        "segments": [
            {"text": str, "start": float, "end": float},
            ...
        ]
      }
    """

    TIMEDTEXT_URL = "https://www.youtube.com/api/timedtext"

    # ------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------

    def fetch(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Accepts either:
          - a YouTube URL
          - a raw video ID
        Returns normalized transcript data or None.
        """

        video_id = self._extract_video_id(query)
        if not video_id:
            return None

        transcript = self._fetch_transcript(video_id)
        if not transcript:
            return None

        return {
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "video_id": video_id,
            "auto_generated": transcript.get("auto_generated", False),
            "segments": transcript.get("segments", []),
        }

    # ------------------------------------------------------------
    # INTERNAL METHODS
    # ------------------------------------------------------------

    def _extract_video_id(self, query: str) -> Optional[str]:
        """
        Extracts a YouTube video ID from:
          - full URLs
          - shortened URLs
          - raw IDs
        """

        # Full URL
        match = re.search(r"v=([A-Za-z0-9_-]{11})", query)
        if match:
            return match.group(1)

        # Short URL
        match = re.search(r"youtu\.be/([A-Za-z0-9_-]{11})", query)
        if match:
            return match.group(1)

        # Raw ID
        if len(query.strip()) == 11:
            return query.strip()

        return None

    def _fetch_transcript(self, video_id: str) -> Optional[Dict[str, Any]]:
        """
        Attempts to fetch transcript in multiple fallback modes:
          - lang=en
          - lang=en-US
          - auto-generated (a.en)
        """

        attempts = [
            {"lang": "en"},
            {"lang": "en-US"},
            {"lang": "a.en"},  # auto-generated
        ]

        for params in attempts:
            data = self._request_timedtext(video_id, params["lang"])
            if data:
                return data

        return None

    def _request_timedtext(self, video_id: str, lang: str) -> Optional[Dict[str, Any]]:
        """
        Calls the YouTube timedtext endpoint and parses XML.
        """

        url = f"{self.TIMEDTEXT_URL}?v={video_id}&lang={lang}"

        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code != 200:
                return None

            xml = resp.text.strip()
            if not xml or "<transcript" not in xml:
                return None

            segments = self._parse_xml_segments(xml)
            if not segments:
                return None

            return {
                "auto_generated": lang.startswith("a."),
                "segments": segments,
            }

        except Exception:
            return None

    def _parse_xml_segments(self, xml: str) -> List[Dict[str, Any]]:
        """
        Extracts <text> nodes from YouTube timedtext XML.
        """

        pattern = r'<text start="([\d.]+)" dur="([\d.]+)">(.*?)</text>'
        matches = re.findall(pattern, xml)

        segments = []
        for start, dur, text in matches:
            clean = (
                text.replace("&amp;", "&")
                    .replace("&quot;", '"')
                    .replace("&#39;", "'")
                    .replace("&lt;", "<")
                    .replace("&gt;", ">")
            )

            start_f = float(start)
            end_f = start_f + float(dur)

            segments.append({
                "text": clean,
                "start": start_f,
                "end": end_f,
            })

        return segments