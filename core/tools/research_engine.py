# core/tools/research_engine.py

import re
from core.tools.wikipedia import WikipediaFetcher
from core.tools.stackoverflow import StackOverflowFetcher
from core.tools.duckduckgo import DuckDuckGoFetcher
from core.tools.mdn import MDNFetcher
from core.tools.arxiv import ArXivFetcher
from core.tools.github import GitHubFetcher
from core.tools.semantic_scholar import SemanticScholarFetcher
from core.tools.youtube_transcript import YouTubeTranscriptFetcher
from core.tools.fetchers.crossref_fetcher import CrossRefFetcher


class ResearchEngine:
    """
    Multi-source research engine with confidence scoring and synthesis.
    """

    def __init__(self):
        self.wikipedia = WikipediaFetcher()
        self.duckduckgo = DuckDuckGoFetcher()
        self.stackoverflow = StackOverflowFetcher()
        self.mdn = MDNFetcher()
        self.arxiv = ArXivFetcher()
        self.github = GitHubFetcher()
        self.semantic_scholar = SemanticScholarFetcher()
        self.crossref = CrossRefFetcher()
        self.youtube = YouTubeTranscriptFetcher()

    # ---------------------------------------------------------
    # Confidence Scoring
    # ---------------------------------------------------------
    def score_result(self, result: dict, query: str) -> float:
        """
        Centralized scoring logic for all sources.
        Produces a confidence score between 0.0 and 1.0.
        """

        source = result.get("source", "").lower()
        content = result.get("content", "") or ""
        title = result.get("title", "") or ""
        abstract = result.get("abstract", "") or ""

        # -----------------------------------------
        # STEP 1: BASE SCORES PER SOURCE
        # -----------------------------------------
        base_scores = {
            "semanticscholar": 0.85,
            "arxiv": 0.80,
            "crossref": 0.75,
            "wikipedia": 0.65,
            "duckduckgo": 0.50,
            "stackoverflow": 0.60,
            "mdn": 0.65,
            "github": 0.65,
            "youtube transcript": 0.68,
        }

        score = base_scores.get(source, 0.40)

        # -----------------------------------------
        # STEP 2: CONTENT QUALITY BONUS
        # -----------------------------------------
        length_bonus = min(len(content) / 2000, 0.10)
        score += length_bonus

        if abstract and len(abstract) > 50:
            score += 0.05

        # -----------------------------------------
        # STEP 3: QUERY RELEVANCE BONUS
        # -----------------------------------------
        q = query.lower()
        t = title.lower()
        a = abstract.lower()

        if q in t:
            score += 0.05

        if q in a:
            score += 0.05

        overlap = sum(1 for word in q.split() if word in content.lower())
        score += min(overlap * 0.01, 0.05)

        # -----------------------------------------
        # STEP 4: NORMALIZE
        # -----------------------------------------
        score = max(0.0, min(score, 1.0))

        print(f"[SCORING] {source}: {score:.2f}")

        return score

    # ---------------------------------------------------------
    # Query Classification
    # ---------------------------------------------------------
    def is_technical_query(self, query):
        tech_keywords = [
            "python", "error", "code", "function", "java", "c++",
            "bug", "stack trace", "javascript", "typescript",
            "api", "compiler", "html", "css", "react", "node",
            "browser", "dom",
        ]
        return any(word in query.lower() for word in tech_keywords)

    def is_web_tech_query(self, query):
        web_keywords = [
            "javascript", "js", "html", "css", "dom", "web api",
            "fetch", "promise", "async", "await", "event loop",
            "localstorage", "sessionstorage", "service worker",
            "websocket", "browser",
        ]
        return any(word in query.lower() for word in web_keywords)

    def is_scientific_query(self, query):
        sci_keywords = [
            "quantum", "physics", "relativity", "neural network",
            "machine learning", "deep learning", "theorem",
            "algebra", "topology", "cosmology", "astrophysics",
            "graph theory", "complexity theory", "algorithm",
            "probability", "statistics", "stochastic", "bayesian",
            "markov", "tensor", "manifold", "lattice",
        ]
        q = query.lower()
        return any(word in q for word in sci_keywords)

    def is_code_query(self, query):
        code_keywords = [
            "github", "repo", "repository", "library", "framework",
            "sdk", "open source", "cli tool", "plugin", "extension",
            "api client", "implementation", "example code",
        ]
        q = query.lower()
        return any(word in q for word in code_keywords)

    def is_academic_query(self, query):
        academic_keywords = [
            "research", "paper", "study", "journal", "conference",
            "publication", "citation", "peer review", "academic",
        ]
        q = query.lower()
        return any(word in q for word in academic_keywords)

    def is_publication_query(self, query):
        pub_keywords = [
            "doi", "journal", "conference", "proceedings",
            "published in", "publication", "volume", "issue",
            "crossref", "publisher",
        ]
        q = query.lower()
        return any(word in q for word in pub_keywords)

    def is_video_query(self, query):
        q = query.lower()

        if "youtube.com/watch" in q or "youtu.be/" in q:
            return True

        video_keywords = [
            "youtube", "video", "talk", "lecture", "keynote",
            "conference talk", "tutorial", "recording",
        ]
        return any(word in q for word in video_keywords)

    # ---------------------------------------------------------
    # Main Research Pipeline
    # ---------------------------------------------------------
    def research(self, query: str):
        print(f"DEBUG: ResearchEngine.research() called with query: {query}")

        results = []

        # Wikipedia
        wiki = self.wikipedia.fetch(query)
        if wiki:
            print("DEBUG: Wikipedia result added")
            wiki["confidence"] = self.score_result(wiki, query)
            results.append(wiki)

        # DuckDuckGo
        ddg = self.duckduckgo.fetch(query)
        if ddg:
            print("DEBUG: DuckDuckGo result added")
            ddg["confidence"] = self.score_result(ddg, query)
            results.append(ddg)

        # MDN (web tech only)
        if self.is_web_tech_query(query):
            print("DEBUG: Query classified as web-tech → enabling MDN")
            mdn = self.mdn.fetch(query)
            if mdn:
                print("DEBUG: MDN result added")
                mdn["confidence"] = self.score_result(mdn, query)
                results.append(mdn)
        else:
            print("DEBUG: Query not web-tech → skipping MDN")

        # StackOverflow
        if self.is_technical_query(query):
            print("DEBUG: Query classified as technical → enabling StackOverflow")
            so = self.stackoverflow.fetch(query)
            if so:
                print("DEBUG: StackOverflow result added")
                so["confidence"] = self.score_result(so, query)
                results.append(so)
        else:
            print("DEBUG: Query not technical → skipping StackOverflow")

        # GitHub
        if self.is_code_query(query) or self.is_technical_query(query):
            print("DEBUG: Query classified as code-related → enabling GitHub")
            gh = self.github.fetch(query)
            if gh:
                print("DEBUG: GitHub result added")
                gh["confidence"] = self.score_result(gh, query)
                results.append(gh)
        else:
            print("DEBUG: Query not code-related → skipping GitHub")

        # ArXiv
        if self.is_scientific_query(query):
            print("DEBUG: Query classified as scientific → enabling ArXiv")
            ax = self.arxiv.fetch(query)
            if ax:
                print("DEBUG: ArXiv result added")
                ax["confidence"] = self.score_result(ax, query)
                results.append(ax)
        else:
            print("DEBUG: Query not scientific → skipping ArXiv")

        # Semantic Scholar
        if self.is_academic_query(query) or self.is_scientific_query(query):
            print("DEBUG: Query classified as academic → enabling Semantic Scholar")
            ss = self.semantic_scholar.fetch(query)
            if ss:
                print("DEBUG: Semantic Scholar result added")
                ss["confidence"] = self.score_result(ss, query)
                results.append(ss)
        else:
            print("DEBUG: Query not academic → skipping Semantic Scholar")

        # CrossRef
        if self.is_publication_query(query) or self.is_academic_query(query):
            print("DEBUG: Query classified as publication-related → enabling CrossRef")
            cr = self.crossref.fetch(query)
            if cr:
                print("DEBUG: CrossRef result added")
                cr["confidence"] = self.score_result(cr, query)
                results.append(cr)
        else:
            print("DEBUG: Query not publication-related → skipping CrossRef")

        # YouTube Transcript
        if self.is_video_query(query):
            print("DEBUG: Query classified as video-related → enabling YouTubeTranscript")
            yt = self.youtube.fetch(query)
            if yt:
                print("DEBUG: YouTube Transcript result added")
                yt["confidence"] = self.score_result(yt, query)
                results.append(yt)
        else:
            print("DEBUG: Query not video-related → skipping YouTubeTranscript")

        return results
    # ---------------------------------------------------------
    # C‑1.1 — Sentence Cleaning & Splitting
    # ---------------------------------------------------------
    def _clean_and_split_sentences(self, text: str):
        """
        Cleans raw text and splits it into meaningful sentences.
        Removes boilerplate, HTML, citations, and very short fragments.
        """

        if not text:
            return []

        # Normalize whitespace
        cleaned = (
            text.replace("\n", " ")
                .replace("\r", " ")
                .replace("  ", " ")
                .strip()
        )

        # Remove HTML tags
        import re
        cleaned = re.sub(r"<[^>]+>", "", cleaned)

        # Remove citation markers like [1], [2], [3]
        cleaned = re.sub(r"\[\d+\]", "", cleaned)

        # Remove leftover weird unicode artifacts
        cleaned = cleaned.replace("â", "").replace("€", "").replace("™", "")

        # Split into sentences
        raw_sentences = re.split(r"[.!?]", cleaned)

        # Filter meaningful sentences
        sentences = [
            s.strip()
            for s in raw_sentences
            if len(s.strip()) > 40  # avoid fragments
        ]

        return sentences
        # ---------------------------------------------------------
        # Synthesis Helpers (C‑3)
        # ---------------------------------------------------------
    # ---------------------------------------------------------
    # C‑1.2 — Intelligent Key Point Extraction
    # ---------------------------------------------------------
    def _extract_key_points(self, results):
        """
        Extracts and scores sentences from all sources using:
        - query relevance
        - clarity scoring
        - definition/claim detection
        - source confidence weighting
        - length quality
        """
        key_points = []
        import re

        def score_sentence(sentence, query, source_conf):
            score = 0

            # Query relevance (keyword overlap)
            query_words = set(query.lower().split())
            sent_words = set(sentence.lower().split())
            overlap = len(query_words.intersection(sent_words))
            score += overlap * 1.5

            # Definition detection
            if " is " in sentence.lower() or " refers to " in sentence.lower():
                score += 3

            # Claim/result detection
            if any(x in sentence.lower() for x in ["shows that", "demonstrates", "results", "indicates"]):
                score += 2

            # Clarity scoring (medium-length sentences are best)
            length = len(sentence.split())
            if 12 < length < 40:
                score += 2
            elif length >= 40:
                score += 1

            # Source confidence weighting
            score += source_conf * 2

            return score

        # Process each source
        for r in results:
            content = r.get("content", "")
            source = r.get("source")
            conf = r.get("confidence", 0)

            # Use upgraded sentence splitter
            sentences = self._clean_and_split_sentences(content)

            for s in sentences:
                s_score = score_sentence(s, r.get("query", ""), conf)
                key_points.append({
                    "text": s,
                    "source": source,
                    "confidence": conf,
                    "score": s_score
                })

        # Sort by score
        key_points.sort(key=lambda x: x["score"], reverse=True)

        # Deduplicate
        deduped = self._deduplicate_key_points(key_points)

        # Balanced selection (C‑1.5)
        return self._select_balanced_key_points(deduped, limit=8)

    # ---------------------------------------------------------
    # C‑1.3 — Semantic Deduplication
    # ---------------------------------------------------------
    def _deduplicate_key_points(self, key_points):
        """
        Removes near-duplicate sentences using simple semantic similarity.
        Uses token overlap as a lightweight similarity metric.
        """

        def similarity(a, b):
            a_words = set(a.lower().split())
            b_words = set(b.lower().split())
            if not a_words or not b_words:
                return 0
            return len(a_words.intersection(b_words)) / len(a_words.union(b_words))

        deduped = []
        for kp in key_points:
            text = kp["text"]
            is_duplicate = False

            for existing in deduped:
                if similarity(text, existing["text"]) > 0.55:
                    is_duplicate = True
                    break

            if not is_duplicate:
                deduped.append(kp)

        return deduped

    # ---------------------------------------------------------
    # C‑1.4 — Category Extraction
    # ---------------------------------------------------------
    def _categorize_sentence(self, sentence: str):
        """
        Assigns a semantic category to a sentence:
        - definition
        - claim
        - result
        - example
        - mechanism
        - implication
        - other
        """

        s = sentence.lower()

        # Definition patterns
        if " is " in s or " refers to " in s or " defined as " in s:
            return "definition"

        # Claim patterns
        if any(x in s for x in ["suggests that", "argues that", "claims that", "proposes that"]):
            return "claim"

        # Result / finding patterns
        if any(x in s for x in ["results show", "we find that", "the study finds", "demonstrates that", "indicates that"]):
            return "result"

        # Example patterns
        if any(x in s for x in ["for example", "for instance", "such as"]):
            return "example"

        # Mechanism patterns
        if any(x in s for x in ["because", "due to", "as a result of", "leads to", "causes"]):
            return "mechanism"

        # Implication patterns
        if any(x in s for x in ["this means that", "implies that", "therefore", "consequently"]):
            return "implication"

        return "other"
    # ---------------------------------------------------------
    # C‑1.5 — Balanced Key Point Selection
    # ---------------------------------------------------------
    def _select_balanced_key_points(self, key_points, limit=8):
        """
        Selects a diverse, balanced set of key points across categories.
        Ensures:
        - at least one definition (if available)
        - at least one result/claim (if available)
        - category diversity
        - highest scoring items preserved
        """

        # Group by category
        categories = {}
        for kp in key_points:
            cat = kp.get("category", "other")
            categories.setdefault(cat, [])
            categories[cat].append(kp)

        # Sort each category by score
        for cat in categories:
            categories[cat].sort(key=lambda x: x["score"], reverse=True)

        selected = []

        # 1. Ensure at least one definition
        if "definition" in categories and categories["definition"]:
            selected.append(categories["definition"][0])

        # 2. Ensure at least one result or claim
        for cat in ["result", "claim"]:
            if cat in categories and categories[cat]:
                selected.append(categories[cat][0])
                break

        # 3. Fill remaining slots with highest scoring items across all categories
        remaining = []
        for cat_list in categories.values():
            remaining.extend(cat_list)

        # Remove duplicates
        remaining = [kp for kp in remaining if kp not in selected]

        # Sort remaining by score
        remaining.sort(key=lambda x: x["score"], reverse=True)

        # Fill up to limit
        for kp in remaining:
            if len(selected) >= limit:
                break
            selected.append(kp)

        return selected[:limit]
    # ---------------------------------------------------------
    # Agreement / Difference Helpers
    # ---------------------------------------------------------
    def _find_agreements(self, results):
        phrases = {}
        for r in results:
            content = r.get("content", "").lower()
            for phrase in content.split("."):
                phrase = phrase.strip()
                if len(phrase) < 40:
                    continue
                phrases.setdefault(phrase, 0)
                phrases[phrase] += 1

        agreements = [p for p, count in phrases.items() if count > 1]
        return agreements[:3]


    def _find_differences(self, results):
        differences = []
        for r in results:
            content = r.get("content", "")
            source = r.get("source")
            sentences = [s.strip() for s in content.split(".") if len(s.strip()) > 40]
            if sentences:
                differences.append(f"{source}: {sentences[0]}")
        return differences[:3]
    # ---------------------------------------------------------
    # C‑2 — Narrative Synthesis Upgrade
    # ---------------------------------------------------------
    def _build_narrative(self, key_points, agreements, differences):
        """
        Builds a coherent, human-style narrative explanation using:
        - balanced key points (C‑1.5)
        - category tags (C‑1.4)
        - agreements/differences (C‑3)
        """

        if not key_points:
            return "The available sources provide limited information, but the topic can be summarized at a high level."

        # Organize by category
        by_cat = {}
        for kp in key_points:
            cat = kp.get("category", "other")
            by_cat.setdefault(cat, [])
            by_cat[cat].append(kp["text"])

        narrative_parts = []

        # 1. Start with definition if available
        if "definition" in by_cat:
            narrative_parts.append(
                f"The topic is generally defined as: {by_cat['definition'][0]}."
            )

        # 2. Add results/claims
        if "result" in by_cat or "claim" in by_cat:
            rc = by_cat.get("result", []) + by_cat.get("claim", [])
            if rc:
                narrative_parts.append(
                    f"Research findings indicate that {rc[0]}."
                )

        # 3. Add mechanisms
        if "mechanism" in by_cat:
            narrative_parts.append(
                f"This occurs because {by_cat['mechanism'][0]}."
            )

        # 4. Add examples
        if "example" in by_cat:
            narrative_parts.append(
                f"For example, {by_cat['example'][0]}."
            )

        # 5. Add implications
        if "implication" in by_cat:
            narrative_parts.append(
                f"This suggests that {by_cat['implication'][0]}."
            )

        # 6. Add agreements
        if agreements:
            narrative_parts.append(
                f"Multiple sources agree on key points such as: {agreements[0]}."
            )

        # 7. Add differences
        if differences:
            narrative_parts.append(
                f"However, some sources differ, noting: {differences[0]}."
            )

        # Combine into a single narrative paragraph
        return " ".join(narrative_parts)
    # ---------------------------------------------------------
    # Synthesis (Hybrid C‑3)
    # ---------------------------------------------------------
    def synthesize(self, results):
        print("DEBUG: Synthesizing research results (Hybrid C‑3)...")

        if not results:
            return "No reliable information found."

        # Sort by confidence
        results = sorted(results, key=lambda r: r.get("confidence", 0), reverse=True)

        # Extract synthesis components
        key_points = self._extract_key_points(results)
        agreements = self._find_agreements(results)
        differences = self._find_differences(results)

        # Overview section
        overview = (
            f"This topic is discussed across {len(results)} sources. "
            f"The highest confidence source is {results[0].get('source')}."
        )

        # Key Findings section
        key_findings_text = "\n".join(
            [f"- {kp['text']} (from {kp['source']})" for kp in key_points]
        )

        # Agreement section
        agreement_text = (
            "\n".join([f"- {a}" for a in agreements])
            if agreements else "No strong cross-source agreement detected."
        )

        # Differences section
        difference_text = (
            "\n".join([f"- {d}" for d in differences])
            if differences else "No major differences detected."
        )

        # Narrative explanation (C‑2)
        narrative = self._build_narrative(key_points, agreements, differences)

        # Source list
        source_list = ", ".join([r.get("source") for r in results])

        # Final hybrid output
        return (
            f"### Overview\n{overview}\n\n"
            f"### Key Findings\n{key_findings_text}\n\n"
            f"### Cross-Source Agreement\n{agreement_text}\n\n"
            f"### Notable Differences\n{difference_text}\n\n"
            f"### Narrative Explanation\n{narrative}\n\n"
            f"### Sources\nBased on: {source_list}"
        )
