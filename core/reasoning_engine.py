# core/reasoning_engine.py

import re
from typing import Any, Dict, Iterator, List, Optional, Tuple

from core.horology_lubrication import detect_primary_topic
from core.horology_safety import enforce_shellac_safety, validate_shellac_safety
from core.output_sanitize import (
    build_shellac_correction_prompt,
    is_leaked_stream_chunk,
    sanitize_model_output,
)
from core.tools.live_web_search import (
    execute_web_search,
    format_system_context_alert,
)
from core.vault.pdf_vault import (
    get_document_context_from_cache,
    is_vault_loading,
    vault_context_matched,
)
from core.vintage_modern_crossref import (
    build_vintage_modern_document_context,
    run_modern_cross_reference,
)


def _token_mentions_off_topic(token: str) -> bool:
    lower = token.lower()
    off_topic = (
        "balance",
        "hairspring",
        "ultrasonic",
        "9010",
        "pallet",
        "roller jewel",
        "shellac",
        "fluorocarbon",
    )
    return any(term in lower for term in off_topic)


def _should_emit_token(token: str, topic: str) -> bool:
    if not isinstance(token, str) or not token:
        return False
    if is_leaked_stream_chunk(token):
        return False
    if topic == "mainspring" and _token_mentions_off_topic(token):
        return False
    return True


class ReasoningEngine:
    """
    Universal assistant reasoning layer with vault grounding,
    live context injection, and vintage vs. modern cross-reference.
    """

    FINAL_RESPONSE_PATTERN = re.compile(
        r"<FINAL_RESPONSE>\s*(.*?)\s*</FINAL_RESPONSE>",
        re.IGNORECASE | re.DOTALL,
    )

    LIVE_INTENT_TRIGGERS = [
        "weather",
        "forecast",
        "temperature",
        "what time does",
        "what time do",
        "when does",
        "when do",
        "close",
        "closing",
        "hours",
        "open until",
        "store hours",
        "business hours",
        "news",
        "headline",
        "headlines",
        "breaking news",
        "right now",
        "currently",
        "today's",
        "live score",
        "stock price",
        "exchange rate",
    ]

    LIVE_RESPONSE_INSTRUCTIONS = """
Use the live web details in hidden system context as your primary factual source.
Do not refuse or invent current facts when live snippets are present.
Reply with a concise, numbered bench guide only. No structural tags or context headers.
"""

    BENCH_OUTPUT_INSTRUCTIONS = (
        "Reply with numbered bench steps, exact tools, and specific greases/solvents only. "
        "No preamble, meta commentary, or hidden-context labels."
    )

    def __init__(self, client):
        self.client = client

    def get_stream_plan(self, prompt: str) -> Dict[str, Any]:
        """
        Classify streaming route: vault cross-ref, live web intent, or plain chat.
        Web scraping always deferred — never blocks vault grounding.
        """
        prompt = prompt.strip()
        vault_grounding = ""

        if not is_vault_loading() and vault_context_matched(prompt):
            vault_grounding = get_document_context_from_cache(prompt)

        if vault_grounding:
            return {
                "mode": "vault_crossref",
                "vault_grounding": vault_grounding,
                "needs_web": True,
                "web_kind": "modern",
                "primary_topic": detect_primary_topic(prompt),
            }

        if self._detect_live_intent(prompt):
            return {
                "mode": "live_intent",
                "vault_grounding": "",
                "needs_web": True,
                "web_kind": "live",
                "primary_topic": detect_primary_topic(prompt),
            }

        return {
            "mode": "plain",
            "vault_grounding": "",
            "needs_web": False,
            "web_kind": None,
            "primary_topic": detect_primary_topic(prompt),
        }

    def prepare_unified_stream(
        self,
        prompt: str,
        history: Optional[List[Dict[str, str]]] = None,
        plan: Optional[Dict[str, Any]] = None,
        web_payload: Any = None,
    ) -> Tuple[str, List[Dict[str, str]], str]:
        """
        Single-pass stream prep: merge vault + web into hidden system context only.
        User message stays the raw question — no continuation phases.
        """
        history = history or []
        prompt = prompt.strip()
        plan = plan or self.get_stream_plan(prompt)
        document_context = ""

        if plan["mode"] == "vault_crossref" and web_payload:
            modern_context, _ = web_payload
            document_context = build_vintage_modern_document_context(
                plan["vault_grounding"],
                modern_context,
            )
        elif plan["mode"] == "vault_crossref":
            document_context = plan.get("vault_grounding", "")
        elif plan["mode"] == "live_intent" and web_payload:
            document_context = format_system_context_alert(prompt, web_payload)
        elif plan["mode"] == "live_intent":
            document_context = ""

        return prompt, history, document_context

    def prepare_primary_stream(
        self,
        prompt: str,
        history: Optional[List[Dict[str, str]]] = None,
        plan: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, List[Dict[str, str]], str]:
        """
        Build Ollama inputs for immediate generation — vault/local only, no web wait.
        """
        history = history or []
        prompt = prompt.strip()
        plan = plan or self.get_stream_plan(prompt)
        document_context = ""
        user_prompt = prompt

        if plan["mode"] == "vault_crossref":
            document_context = plan["vault_grounding"]
            user_prompt = prompt
        elif plan["mode"] == "live_intent":
            user_prompt = prompt

        return user_prompt, history, document_context

    def prepare_modern_continuation(
        self,
        prompt: str,
        history: List[Dict[str, str]],
        partial_assistant: str,
        modern_context: str,
        vault_context: str,
    ) -> Tuple[str, List[Dict[str, str]], str]:
        document_context = build_vintage_modern_document_context(
            vault_context,
            modern_context,
        )
        continuation_history = list(history)
        if partial_assistant.strip():
            continuation_history.append(
                {"role": "assistant", "content": partial_assistant.strip()}
            )

        continuation_prompt = (
            "Continue from your prior answer using the updated hidden system context. "
            "Complete the vintage vs. modern comparison as numbered bench steps only. "
            f"{self.BENCH_OUTPUT_INSTRUCTIONS}"
        )
        return continuation_prompt, continuation_history, document_context

    def prepare_live_continuation(
        self,
        prompt: str,
        history: List[Dict[str, str]],
        partial_assistant: str,
        summaries: List[Dict[str, str]],
    ) -> Tuple[str, List[Dict[str, str]], str]:
        context_alert = format_system_context_alert(prompt, summaries)
        continuation_history = list(history)
        if partial_assistant.strip():
            continuation_history.append(
                {"role": "assistant", "content": partial_assistant.strip()}
            )

        continuation_prompt = (
            f"Continue your answer using hidden live context already in system messages. "
            f"{self.LIVE_RESPONSE_INSTRUCTIONS.strip()} "
            f"{self.BENCH_OUTPUT_INSTRUCTIONS}"
        )
        return continuation_prompt, continuation_history, context_alert

    def prepare_shellac_correction_continuation(
        self,
        history: List[Dict[str, str]],
        partial_assistant: str,
        document_context: str = "",
    ) -> Tuple[str, List[Dict[str, str]], str]:
        continuation_history = list(history)
        if partial_assistant.strip():
            continuation_history.append(
                {"role": "assistant", "content": partial_assistant.strip()}
            )
        return build_shellac_correction_prompt(), continuation_history, document_context

    def iter_ollama_tokens(
        self,
        user_prompt: str,
        history: List[Dict[str, str]],
        document_context: str,
        model_name: Optional[str] = None,
    ) -> Iterator[str]:
        topic = detect_primary_topic(user_prompt)
        for token in self.client.chat_stream(
            prompt=user_prompt,
            history=history,
            document_context=document_context,
            model_name=model_name,
        ):
            if _should_emit_token(token, topic):
                yield token

    def iter_cloud_tokens(
        self,
        provider: str,
        user_prompt: str,
        history: List[Dict[str, str]],
        document_context: str,
        cloud_gateway,
    ) -> Iterator[str]:
        """Stream cloud brain tokens with the same leak/topic filters as local."""
        topic = detect_primary_topic(user_prompt)
        for token in cloud_gateway.iter_cloud_tokens(
            provider,
            user_prompt,
            history,
            document_context,
        ):
            if _should_emit_token(token, topic):
                yield token

    def iter_scavenger_tokens(
        self,
        user_prompt: str,
        history: List[Dict[str, str]],
        document_context: str,
    ) -> Iterator[str]:
        """Local Ollama Llama3 fallback — vault context preserved."""
        scavenger_model = getattr(
            self.client,
            "scavenger_model_name",
            "llama3",
        )
        yield from self.iter_ollama_tokens(
            user_prompt,
            history,
            document_context,
            model_name=scavenger_model,
        )

    def format_modern_merge_stream(self, modern_context: str) -> str:
        """Server-side only — must never be streamed to the client."""
        return modern_context.strip()

    def format_live_merge_stream(
        self,
        prompt: str,
        summaries: List[Dict[str, str]],
    ) -> str:
        """Server-side only — must never be streamed to the client."""
        return format_system_context_alert(prompt, summaries)

    def _prepare_chat_inputs(
        self,
        prompt: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> Tuple[str, List[Dict[str, str]], str]:
        """
        Chat prep workflow:
        1) Vault match → mandatory vintage vs. modern cross-reference
        2) Live-data intent → SYSTEM CONTEXT ALERT web injection
        Returns (user_prompt, history, document_context).
        """
        history = history or []
        user_prompt = prompt.strip()
        document_context = ""
        vintage_modern_active = False

        if not is_vault_loading() and vault_context_matched(user_prompt):
            try:
                vault_context = get_document_context_from_cache(user_prompt)
                if vault_context:
                    print(
                        "[CrossRef] Vault match — scheduling modern web cross-reference..."
                    )
                    modern_context, _ = run_modern_cross_reference(user_prompt)
                    document_context = build_vintage_modern_document_context(
                        vault_context,
                        modern_context,
                    )
                    vintage_modern_active = True
                    user_prompt = prompt.strip()
            except Exception as exc:
                print(f"[CrossRef Warning] Skipping cross-reference: {exc}")
                document_context = ""
                vintage_modern_active = False

        if not vintage_modern_active and self._detect_live_intent(user_prompt):
            summaries = execute_web_search(user_prompt, max_results=5)
            context_alert = format_system_context_alert(user_prompt, summaries)
            document_context = context_alert
            user_prompt = prompt.strip()

        return user_prompt, history, document_context

    def process_chat(
        self,
        prompt: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """
        Non-streaming chat: prepare context, call Ollama, extract final answer.
        """
        user_prompt, history, document_context = self._prepare_chat_inputs(
            prompt, history
        )
        raw_response = self.client.chat(
            prompt=user_prompt,
            history=history,
            document_context=document_context,
        )
        return sanitize_model_output(
            enforce_shellac_safety(self._extract_final_response(raw_response)),
            prompt=prompt,
        )

    def process_chat_stream(
        self,
        prompt: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> Iterator[str]:
        """
        Streaming chat: prepare context, then yield each Ollama token delta.
        """
        user_prompt, history, document_context = self._prepare_chat_inputs(
            prompt, history
        )
        yield from self.client.chat_stream(
            prompt=user_prompt,
            history=history,
            document_context=document_context,
        )

    def _detect_live_intent(self, prompt: str) -> bool:
        lower = prompt.lower()
        return any(trigger in lower for trigger in self.LIVE_INTENT_TRIGGERS)

    def _extract_final_response(self, text: str) -> str:
        if not text:
            return ""

        match = self.FINAL_RESPONSE_PATTERN.search(text)
        if match and match.group(1).strip():
            return match.group(1).strip()

        cleaned = self.FINAL_RESPONSE_PATTERN.sub("", text).strip()
        return sanitize_model_output(cleaned or text.strip(), prompt="")

    def plan(self, user_message: str, context: str = "") -> List[Dict[str, Any]]:
        prompt = f"""
You are Athena's internal planner.

User request:
{user_message}

Context:
{context}

Your job is to create a short, clear plan of 1–5 steps to solve this.

Respond ONLY in valid JSON, with this structure:

[
  {{
    "description": "string",
    "type": "thought" | "skill",
    "target": "skill_name_or_empty_string"
  }}
]

Rules:
- Use "thought" for internal reasoning steps.
- Use "skill" only if a known skill is clearly needed.
- If no skill is needed, use only "thought" steps.
- Keep steps minimal and necessary.
"""

        raw = self.client.send_message(prompt)

        try:
            import json
            plan = json.loads(raw)
            if isinstance(plan, list):
                return plan
        except Exception:
            pass

        return [
            {
                "description": "Think through the problem and answer directly.",
                "type": "thought",
                "target": "",
            }
        ]

    def execute_plan(
        self,
        plan: List[Dict[str, Any]],
        user_message: str,
        skills,
    ) -> str:
        scratchpad = []

        for step in plan:
            step_type = step.get("type", "thought")
            desc = step.get("description", "")
            target = step.get("target", "")

            if step_type == "skill" and target:
                skill = next((s for s in skills.skills if s.name == target), None)
                if skill:
                    result = skill.handle(user_message)
                    scratchpad.append(f"[SKILL:{target}] {result}")
                else:
                    scratchpad.append(f"[SKILL:{target}] Skill not found.")
            else:
                thought_prompt = f"""
You are Athena's internal reasoning process.

User request:
{user_message}

Scratchpad so far:
{chr(10).join(scratchpad)}

Current step:
{desc}

Think through this step and refine the solution.
Respond with a short paragraph.
"""
                thought = self.client.send_message(thought_prompt)
                scratchpad.append(f"[THOUGHT] {thought}")

        final_prompt = f"""
You are Athena.

User request:
{user_message}

Internal scratchpad:
{chr(10).join(scratchpad)}

Now produce a final answer for the user.
Do NOT mention the scratchpad or internal steps.
Just give the best possible response.
"""
        final_answer = self.client.send_message(final_prompt)
        return final_answer
