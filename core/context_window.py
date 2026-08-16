# core/context_window.py

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Iterable
import time
import uuid


# -----------------------------
# Token counting (pluggable)
# -----------------------------


class TokenCounter:
    """
    Pluggable token counter interface.

    Replace `SimpleTokenCounter` with a concrete implementation
    (e.g., OpenAI, HuggingFace) without changing ContextWindow.
    """

    def count(self, text: str) -> int:
        raise NotImplementedError


class SimpleTokenCounter(TokenCounter):
    """
    Very rough heuristic: ~1 token per 4 characters.
    This is a placeholder; swap it out for a real tokenizer.
    """

    def count(self, text: str) -> int:
        if not text:
            return 0
        return max(1, len(text) // 4)


# -----------------------------
# Core data structures
# -----------------------------


@dataclass
class ContextItem:
    id: str
    role: str  # "system" | "developer" | "user" | "assistant"
    text: str
    tokens: int
    timestamp: float
    tier: int  # 1–4
    relevance: float = 0.0
    recency: float = 0.0
    topic_tags: List[str] = field(default_factory=list)


# -----------------------------
# Context window
# -----------------------------


class ContextWindow:
    """
    Builds a deterministic, priority-aware, relevance-weighted context window
    for Athena's reasoning.

    Responsibilities:
    - Store raw messages as ContextItems
    - Assign tiers (1–4) based on role and importance
    - Compute relevance and recency scores
    - Sort by (tier, relevance, recency)
    - Greedily include items under a token budget
    - Optionally summarize dropped items (stubbed hook)
    - Never drop system/developer/core-task messages
    """

    def __init__(
        self,
        token_counter: Optional[TokenCounter] = None,
        default_tier_user: int = 2,
        default_tier_assistant: int = 2,
    ):
        self._token_counter: TokenCounter = token_counter or SimpleTokenCounter()
        self._items: List[ContextItem] = []

        # Tier defaults (can be tuned)
        self._default_tier_user = default_tier_user
        self._default_tier_assistant = default_tier_assistant

    # ------------- Public API -------------

    def add_message(
        self,
        role: str,
        content: str,
        tier: Optional[int] = None,
        topic_tags: Optional[Iterable[str]] = None,
    ) -> str:
        """
        Add a message to the context buffer.

        role:
            "system" | "developer" | "user" | "assistant"
        tier:
            Optional override. If None, tier is inferred from role.
        topic_tags:
            Optional list of topic tags for relevance scoring.
        """
        role = role.lower()
        tokens = self._token_counter.count(content)
        item_id = self._gen_id()
        ts = time.time()

        assigned_tier = tier if tier is not None else self._infer_tier(role)

        item = ContextItem(
            id=item_id,
            role=role,
            text=content,
            tokens=tokens,
            timestamp=ts,
            tier=assigned_tier,
            topic_tags=list(topic_tags) if topic_tags else [],
        )
        self._items.append(item)
        return item_id

    def build_context(
        self,
        query: str,
        token_budget: int,
        query_topic_tags: Optional[Iterable[str]] = None,
    ) -> List[ContextItem]:
        """
        Build the context window for a given query and token budget.

        Returns an ordered list of ContextItems that should be sent
        to the model as context.
        """
        if not self._items:
            return []

        # 1. Annotate items with recency and relevance
        annotated = self._annotate_items(self._items, query, query_topic_tags)

        # 2. Sort by (tier asc, relevance desc, recency desc)
        annotated.sort(key=lambda x: (x.tier, -x.relevance, -x.recency))

        # 3. Always include never-drop items (Tier 1 system/developer/core-task)
        core_items = [i for i in annotated if self._is_never_drop(i)]
        core_tokens = sum(i.tokens for i in core_items)

        if core_tokens > token_budget:
            # Extreme case: core alone exceeds budget.
            # In that case, we include core only and rely on upstream
            # to adjust the budget or prompt.
            return core_items

        used_tokens = core_tokens
        included_ids = {i.id for i in core_items}
        context: List[ContextItem] = list(core_items)

        # 4. Greedy inclusion of remaining items
        for item in annotated:
            if item.id in included_ids:
                continue
            if used_tokens + item.tokens <= token_budget:
                context.append(item)
                included_ids.add(item.id)
                used_tokens += item.tokens

        # 5. Optional summarization of excluded items (stubbed)
        #    This can be implemented later using a summarization skill.
        #    For now, we simply return the selected items.
        return context

    def clear(self) -> None:
        """Reset the context buffer."""
        self._items = []

    def get_all_items(self) -> List[ContextItem]:
        """Return a copy of all stored context items."""
        return list(self._items)

    # ------------- Internal helpers -------------

    def _infer_tier(self, role: str) -> int:
        """
        Assign tiers based on role.

        Tier 1 — Hard-pinned core:
            - system
            - developer
        Tier 2 — Local task state:
            - recent user/assistant messages (default)
        Tier 3 — Compressed history (not explicitly modeled here; can be used for summaries)
        Tier 4 — Raw historical chatter (older, low-relevance items; can be assigned manually)
        """
        if role in ("system", "developer"):
            return 1
        if role == "user":
            return self._default_tier_user
        if role == "assistant":
            return self._default_tier_assistant
        # Fallback: treat unknown roles as low-priority
        return 4

    def _annotate_items(
        self,
        items: List[ContextItem],
        query: str,
        query_topic_tags: Optional[Iterable[str]],
    ) -> List[ContextItem]:
        """
        Compute recency and relevance for each item.
        """
        if not items:
            return []

        q_tags = set(query_topic_tags or [])
        timestamps = [i.timestamp for i in items]
        t_min, t_max = min(timestamps), max(timestamps)
        t_range = max(t_max - t_min, 1e-6)

        for item in items:
            # Recency: normalized timestamp
            item.recency = (item.timestamp - t_min) / t_range

            # Semantic similarity: stubbed as simple lexical overlap
            semantic_sim = self._semantic_similarity_stub(query, item.text)

            # Topic match: 1.0 if any shared tag, else 0.0
            topic_match = 0.0
            if q_tags and item.topic_tags:
                if q_tags.intersection(item.topic_tags):
                    topic_match = 1.0

            # Relevance = 0.5 * semantic + 0.3 * topic + 0.2 * recency
            item.relevance = (
                0.5 * semantic_sim +
                0.3 * topic_match +
                0.2 * item.recency
            )

        return items

    def _semantic_similarity_stub(self, a: str, b: str) -> float:
        """
        Placeholder for semantic similarity.

        For now, we use a very simple lexical overlap heuristic:
        |intersection(words)| / |union(words)|

        This should be replaced with an embedding-based similarity
        when you wire in a vector store or embedding model.
        """
        a_words = {w.lower() for w in a.split() if w.strip()}
        b_words = {w.lower() for w in b.split() if w.strip()}
        if not a_words or not b_words:
            return 0.0
        inter = a_words.intersection(b_words)
        union = a_words.union(b_words)
        return len(inter) / max(len(union), 1)

    def _is_never_drop(self, item: ContextItem) -> bool:
        """
        Never-drop rules:
        - All system messages
        - All developer messages
        - Any item explicitly assigned Tier 1
        """
        if item.role in ("system", "developer"):
            return True
        if item.tier == 1:
            return True
        return False

    @staticmethod
    def _gen_id() -> str:
        return str(uuid.uuid4())