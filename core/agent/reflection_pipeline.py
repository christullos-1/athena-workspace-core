# core/agent/reflection_pipeline.py

from typing import Optional

from core.agent.document_store import DocumentStore
from core.agent.response_parser import ResponseParser
from core.agent.sql_executor import SqlExecutor
from core.database.db_manager import DatabaseManager


class AgenticReflectionPipeline:
    """
    Strict Reflection + Tool-Execution pipeline for complex technical
    and database tasks.
    """

    STRUCTURED_OUTPUT_INSTRUCTIONS = """
You are in AGENTIC PROBLEM-SOLVER MODE.

You MUST respond using EXACTLY these blocks in order:

<THOUGHT_PROCESS>
Analyze the request before answering. Include:
- Potential errors or failure modes
- Technical caliber specifications (if relevant)
- Database constraints, uniqueness rules, and conflict risks
- Whether local document data is sufficient or missing
- Your planned action (answer only, or database write/update)
</THOUGHT_PROCESS>

[Include ONLY if a database write or update is required:]
<SQL_TOOL_CALL>
{
  "action": "insert" or "update",
  "table": "caliber_specs | electrical_diagrams | documents",
  "fields": { "column_name": "value" },
  "where": { "id": 1 },
  "parameters": {}
}
</SQL_TOOL_CALL>

<FINAL_RESPONSE>
User-facing answer only. Do not repeat THOUGHT_PROCESS content.
If data is missing, state constraints explicitly.
If a SQL tool call was issued, summarize what will be stored/updated.
</FINAL_RESPONSE>

Rules:
- Never skip THOUGHT_PROCESS.
- Never hallucinate caliber numbers, wiring specs, or diagram details.
- If local document store results are insufficient, say so explicitly.
- SQL_TOOL_CALL must be valid JSON with only allowed tables/columns.
- For updates, 'where' is required.
"""

    SQL_RESULT_INSTRUCTIONS = """
The SQL tool execution has completed. Update your answer accordingly.

Respond using ONLY:
<FINAL_RESPONSE>
...revised user-facing answer reflecting SQL success or failure...
</FINAL_RESPONSE>
"""

    def __init__(self, model_client, db_manager: Optional[DatabaseManager] = None):
        self.client = model_client
        self.db_manager = db_manager or DatabaseManager()
        self.document_store = DocumentStore(self.db_manager)
        self.sql_executor = SqlExecutor(self.db_manager)
        self.parser = ResponseParser()

    def process(
        self,
        user_message: str,
        memory_text: str = "",
        conversation_context: str = "",
    ) -> str:
        document_context = ""
        if self.document_store.needs_document_lookup(user_message):
            doc_results = self.document_store.search(user_message)
            document_context = self.document_store.format_for_prompt(doc_results)

        schema_summary = self.db_manager.get_schema_summary()

        prompt = self._build_initial_prompt(
            user_message=user_message,
            memory_text=memory_text,
            conversation_context=conversation_context,
            document_context=document_context,
            schema_summary=schema_summary,
        )

        raw_response = self.client.send_agentic_message(
            prompt,
            extra_system=self.STRUCTURED_OUTPUT_INSTRUCTIONS,
        )
        parsed = self.parser.parse(raw_response)

        if not parsed.sql_tool_call:
            return parsed.final_response

        sql_result = self.sql_executor.execute(parsed.sql_tool_call)

        refinement_prompt = (
            f"Original user message:\n{user_message}\n\n"
            f"Your prior THOUGHT_PROCESS:\n{parsed.thought_process}\n\n"
            f"SQL tool call:\n{parsed.sql_tool_call}\n\n"
            f"SQL execution result:\n"
            f"- success: {sql_result.success}\n"
            f"- message: {sql_result.message}\n"
            f"- conflict: {sql_result.conflict}\n\n"
            f"{self.SQL_RESULT_INSTRUCTIONS}"
        )

        refined_raw = self.client.send_agentic_message(
            refinement_prompt,
            extra_system=self.STRUCTURED_OUTPUT_INSTRUCTIONS,
        )
        refined = self.parser.parse(refined_raw)

        if refined.final_response:
            return refined.final_response

        status = "succeeded" if sql_result.success else "failed"
        return (
            f"{parsed.final_response}\n\n"
            f"[Database action {status}: {sql_result.message}]"
        ).strip()

    def _build_initial_prompt(
        self,
        user_message: str,
        memory_text: str,
        conversation_context: str,
        document_context: str,
        schema_summary: str,
    ) -> str:
        sections = [
            "=== DATABASE SCHEMA ===",
            schema_summary,
            "",
            "=== LOCAL DOCUMENT CONTEXT ===",
            document_context or "No document lookup was triggered.",
            "",
        ]

        if memory_text.strip():
            sections.extend(["=== LONG-TERM MEMORY ===", memory_text.strip(), ""])

        if conversation_context.strip():
            sections.extend(["=== CONVERSATION CONTEXT ===", conversation_context.strip(), ""])

        sections.extend([
            "=== USER REQUEST ===",
            user_message.strip(),
            "",
            "Produce THOUGHT_PROCESS, optional SQL_TOOL_CALL, then FINAL_RESPONSE.",
        ])

        return "\n".join(sections)
