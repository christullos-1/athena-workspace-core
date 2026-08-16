# core/logic_loop.py

from core.skills import SkillRouter
from core.context_window import ContextWindow
from core.memory_manager import MemoryManager
from core.classifiers.technical_classifier import TechnicalQueryClassifier
from core.technical_engine.technical_engine import TechnicalReasoningEngine
from core.agent.task_classifier import AgenticTaskClassifier
from core.agent.reflection_pipeline import AgenticReflectionPipeline


class LogicLoop:
    """
    The central reasoning loop for Athena.
    """

    def __init__(self, model_client):
        self.client = model_client
        self.skills = SkillRouter()
        self.context = ContextWindow()
        self.long_memory = MemoryManager()
        self.tqc = TechnicalQueryClassifier()
        self.technical_engine = TechnicalReasoningEngine(model_client)
        self.agentic_classifier = AgenticTaskClassifier()
        self.agentic_pipeline = AgenticReflectionPipeline(model_client)

    def process(self, user_message: str) -> str:

        # 1. Add user message to context
        self.context.add_message("user", user_message)

        # 2. Skill routing (math, summarize, remember)
        skill_response = self.skills.try_skill(user_message)
        if skill_response is not None:
            self.context.add_message("assistant", skill_response)
            return skill_response

        memory_text, conversation_context = self._build_context_sections(user_message)

        # 3. Agentic Reflection + Tool-Execution pipeline
        if self.agentic_classifier.needs_agentic_pipeline(user_message):
            agentic_output = self.agentic_pipeline.process(
                user_message=user_message,
                memory_text=memory_text,
                conversation_context=conversation_context,
            )
            self.context.add_message("assistant", agentic_output)
            return agentic_output

        # 4. Simple technical queries
        classification = self.tqc.classify(user_message)
        if classification == "technical":
            tre_output = self.technical_engine.process(user_message)
            self.context.add_message("assistant", tre_output)
            return tre_output

        # 5. Default conversational path
        full_prompt = (
            f"{memory_text}\n"
            f"{conversation_context}\n"
            f"ASSISTANT: Respond to the final user message above."
        )

        response_text = self.client.send_message(full_prompt)
        self.context.add_message("assistant", response_text)
        return response_text

    def _build_context_sections(self, user_message: str) -> tuple[str, str]:
        long_term_facts = self.long_memory.get_facts()
        memory_text = ""

        if long_term_facts:
            memory_text = "Here are important things the user has told you before:\n"
            for fact in long_term_facts:
                memory_text += f"- {fact}\n"

        context_items = self.context.build_context(
            query=user_message,
            token_budget=2048,
        )

        conversation_context = ""
        for item in context_items:
            role = item.role.upper()
            text = item.text
            conversation_context += f"{role}: {text}\n"

        return memory_text, conversation_context
