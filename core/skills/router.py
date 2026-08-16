# core/skills/router.py

from core.tools.math_tool import MathTool
from core.tools.web_search import WebSearchTool
from core.tools.research_engine import ResearchEngine


class SkillRouter:
    """
    Routes user messages to the appropriate skill/tool based on simple heuristics.
    """

    def try_skill(self, message: str):
        if not isinstance(message, str):
            return None

        lower = message.lower().strip()

        # ---------------------------------------------------------
        # Research Engine Skill
        # ---------------------------------------------------------
        # DEBUG: Confirm which ResearchEngine class is being imported
        print("DEBUG: Router using ResearchEngine from:", ResearchEngine, "MODULE:", ResearchEngine.__module__)

        if lower.startswith("research:"):
            query = message[len("research:"):].strip()
            if not query:
                return "What would you like me to research?"
            engine = ResearchEngine()
            return engine.research(query)

        # ---------------------------------------------------------
        # Web Search Skill (Wikipedia)
        # ---------------------------------------------------------
        if lower.startswith("search the web for"):
            query = message[len("search the web for"):].strip()
            if not query:
                return "What should I search for?"
            tool = WebSearchTool()
            return tool.search(query)

        if lower.startswith("web search:"):
            query = message[len("web search:"):].strip()
            if not query:
                return "What should I search for?"
            tool = WebSearchTool()
            return tool.search(query)

        # ---------------------------------------------------------
# core/skills/router.py

from core.tools.math_tool import MathTool
from core.tools.web_search import WebSearchTool
from core.tools.research_engine import ResearchEngine


class SkillRouter:
    """
    Routes user messages to the appropriate skill/tool based on simple heuristics.
    """

    def try_skill(self, message: str):
        if not isinstance(message, str):
            return None

        lower = message.lower().strip()

        # ---------------------------------------------------------
        # Research Engine Skill
        # ---------------------------------------------------------
        print("DEBUG: Router using ResearchEngine from:", ResearchEngine, "MODULE:", ResearchEngine.__module__)

        if lower.startswith("research:"):
            query = message[len("research:"):].strip()
            if not query:
                return "What would you like me to research?"

            engine = ResearchEngine()

            # Step 1: run research
            results = engine.research(query)

            # Step 2: synthesize results into final text
            final_text = engine.synthesize(results)

            # Step 3: return synthesized text
            return final_text

        # ---------------------------------------------------------
        # Web Search Skill (Wikipedia)
        # ---------------------------------------------------------
        if lower.startswith("search the web for"):
            query = message[len("search the web for"):].strip()
            if not query:
                return "What should I search for?"
            tool = WebSearchTool()
            return tool.search(query)

        if lower.startswith("web search:"):
            query = message[len("web search:"):].strip()
            if not query:
                return "What should I search for?"
            tool = WebSearchTool()
            return tool.search(query)

        # ---------------------------------------------------------
        # Math Skill
        # ---------------------------------------------------------
        if lower.startswith("calculate"):
            expr = message[len("calculate"):].strip()
            if not expr:
                return "What would you like me to calculate?"
            tool = MathTool()
            return tool.calculate(expr)

        if lower.startswith("math:"):
            expr = message[len("math:"):].strip()
            if not expr:
                return "What would you like me to calculate?"
            tool = MathTool()
            return tool.calculate(expr)

        # ---------------------------------------------------------
        # No skill matched
        # ---------------------------------------------------------
        return None
        # ---------------------------------------------------------
        if lower.startswith("calculate"):
            expr = message[len("calculate"):].strip()
            if not expr:
                return "What would you like me to calculate?"
            tool = MathTool()
            return tool.calculate(expr)

        if lower.startswith("math:"):
            expr = message[len("math:"):].strip()
            if not expr:
                return "What would you like me to calculate?"
            tool = MathTool()
            return tool.calculate(expr)

        # ---------------------------------------------------------
        # No skill matched
        # ---------------------------------------------------------
        return None