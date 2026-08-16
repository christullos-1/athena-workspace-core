# core/technical_engine/technical_engine.py

import re
from dataclasses import dataclass
from typing import Optional, List, Dict, Any


@dataclass
class ExtractedError:
    error_type: Optional[str]
    message: Optional[str]
    raw_block: str


@dataclass
class ExtractedCode:
    code_blocks: List[str]


@dataclass
class AnalysisResult:
    category: str
    summary: str
    likely_causes: List[str]
    suggested_checks: List[str]


class TechnicalReasoningEngine:
    """
    Hybrid technical reasoning engine:
    1) Deterministic extraction
    2) Rule-based analysis
    3) LLM-based solution generation (via model_client)
    """

    ERROR_PATTERN = re.compile(
        r"(?P<etype>[A-Za-z_]+Error|Exception):?\s*(?P<msg>.+)?",
        re.IGNORECASE
    )

    CODE_FENCE_PATTERN = re.compile(r"```(.*?)```", re.DOTALL)
    INLINE_CODE_PATTERN = re.compile(r"`([^`]+)`")

    def __init__(self, model_client):
        self.client = model_client

    # ---------- PUBLIC ENTRY POINT ----------

    def process(self, message: str) -> str:
        """
        Main TRE pipeline:
        1. Extract signals (errors, code)
        2. Analyze deterministically
        3. Ask model to generate a solution-oriented explanation
        """

        extracted_error = self._extract_error(message)
        extracted_code = self._extract_code(message)
        analysis = self._analyze(extracted_error, extracted_code, message)

        llm_response = self._generate_solution(message, extracted_error, extracted_code, analysis)
        return llm_response

    # ---------- LAYER 1: EXTRACTION ----------

    def _extract_error(self, message: str) -> Optional[ExtractedError]:
        # Try to find an error-like line
        match = self.ERROR_PATTERN.search(message)
        if not match:
            return None

        error_type = match.group("etype")
        error_msg = match.group("msg").strip() if match.group("msg") else None

        # Grab a rough "block" around the error (for context)
        lines = message.splitlines()
        block_lines = [line for line in lines if error_type in line or "Traceback" in line]
        raw_block = "\n".join(block_lines) if block_lines else message

        return ExtractedError(
            error_type=error_type,
            message=error_msg,
            raw_block=raw_block,
        )

    def _extract_code(self, message: str) -> ExtractedCode:
        code_blocks = []

        # Fenced code
        for m in self.CODE_FENCE_PATTERN.finditer(message):
            code_blocks.append(m.group(1).strip())

        # Inline code
        for m in self.INLINE_CODE_PATTERN.finditer(message):
            code_blocks.append(m.group(1).strip())

        return ExtractedCode(code_blocks=code_blocks)

    # ---------- LAYER 2: RULE-BASED ANALYSIS ----------

    def _analyze(
        self,
        error: Optional[ExtractedError],
        code: ExtractedCode,
        message: str
    ) -> AnalysisResult:
        if error is None:
            return AnalysisResult(
                category="unknown",
                summary="No explicit error type detected.",
                likely_causes=[
                    "The issue may be conceptual rather than a runtime error.",
                    "The error message might be missing or incomplete."
                ],
                suggested_checks=[
                    "Include the full error message and stack trace.",
                    "Share the relevant code snippet that triggers the issue."
                ],
            )

        etype = (error.error_type or "").lower()

        if "keyerror" in etype:
            return self._analyze_keyerror(error, code, message)
        if "attributeerror" in etype:
            return self._analyze_attributeerror(error, code, message)
        if "typeerror" in etype:
            return self._analyze_typeerror(error, code, message)
        if "importerror" in etype or "modulenotfounderror" in etype:
            return self._analyze_importerror(error, code, message)

        # Fallback generic analysis
        return AnalysisResult(
            category="generic_error",
            summary=f"Detected error type: {error.error_type}",
            likely_causes=[
                "The error is raised due to unexpected input or state.",
                "There may be a mismatch between how the function is used and how it is defined."
            ],
            suggested_checks=[
                "Check the full stack trace to see where the error originates.",
                "Verify assumptions about variable types and values at the failing line."
            ],
        )

    def _analyze_keyerror(
        self,
        error: ExtractedError,
        code: ExtractedCode,
        message: str
    ) -> AnalysisResult:
        return AnalysisResult(
            category="key_error",
            summary="KeyError occurs when accessing a dictionary key that does not exist.",
            likely_causes=[
                "The key is misspelled or has different casing.",
                "The key was never added to the dictionary.",
                "The data structure is not what you expect (e.g., list vs dict)."
            ],
            suggested_checks=[
                "Print out dict.keys() before the failing line.",
                "Log the value of the key you are trying to access.",
                "Confirm the data type of the object you are indexing."
            ],
        )

    def _analyze_attributeerror(
        self,
        error: ExtractedError,
        code: ExtractedCode,
        message: str
    ) -> AnalysisResult:
        return AnalysisResult(
            category="attribute_error",
            summary="AttributeError occurs when an object does not have the requested attribute.",
            likely_causes=[
                "You are calling a method or attribute that does not exist on that object.",
                "The object is None due to an earlier failure.",
                "You are confusing instance attributes with class attributes."
            ],
            suggested_checks=[
                "Print type(obj) before the failing line.",
                "Check for None values before attribute access.",
                "Verify the attribute name against the class definition or docs."
            ],
        )
    def _analyze_typeerror(
        self,
        error: ExtractedError,
        code: ExtractedCode,
        message: str
    ) -> AnalysisResult:
        return AnalysisResult(
            category="type_error",
            summary="TypeError occurs when an operation is applied to an object of inappropriate type.",
            likely_causes=[
                "You are passing the wrong type into a function.",
                "You are combining incompatible types (e.g., str + int).",
                "A function returns a different type than you expect."
            ],
            suggested_checks=[
                "Print types of all arguments at the failing line.",
                "Add assertions about types where appropriate.",
                "Check function return types in the docs or implementation."
            ],
        )

    def _analyze_importerror(
        self,
        error: ExtractedError,
        code: ExtractedCode,
        message: str
    ) -> AnalysisResult:
        return AnalysisResult(
            category="import_error",
            summary="ImportError/ModuleNotFoundError occurs when Python cannot find the requested module or name.",
            likely_causes=[
                "The package is not installed in the current environment.",
                "The import path is incorrect.",
                "There is a circular import or name shadowing."
            ],
            suggested_checks=[
                "Run `pip show <package>` or `pip list` to confirm installation.",
                "Print sys.path to verify the module search path.",
                "Check for files that shadow package names (e.g., `requests.py`)."
            ],
        )

    # ---------- LAYER 3: LLM SOLUTION GENERATION ----------

    def _generate_solution(
        self,
        original_message: str,
        error: Optional[ExtractedError],
        code: ExtractedCode,
        analysis: AnalysisResult
    ) -> str:
        """
        Use the model client to turn structured analysis into a solution-oriented explanation.
        """

        error_section = ""
        if error is not None:
            error_section = (
                f"Detected error type: {error.error_type}\n"
                f"Error message: {error.message or 'N/A'}\n"
                f"Error context:\n{error.raw_block}\n"
            )

        code_section = ""
        if code.code_blocks:
            joined = "\n\n".join(code.code_blocks[:2])
            code_section = f"Relevant code snippets:\n{joined}\n"

        analysis_section = (
            f"Category: {analysis.category}\n"
            f"Summary: {analysis.summary}\n"
            f"Likely causes:\n- " + "\n- ".join(analysis.likely_causes) + "\n"
            f"Suggested checks:\n- " + "\n- ".join(analysis.suggested_checks) + "\n"
        )

        system_prompt = (
            "You are Athena's Technical Reasoning Engine. "
            "You receive:\n"
            "1) The user's original technical question\n"
            "2) Extracted error information\n"
            "3) Extracted code snippets\n"
            "4) A structured deterministic analysis\n\n"
            "Your job is to:\n"
            "- Explain clearly what is going wrong\n"
            "- Connect the analysis to the user's situation\n"
            "- Propose concrete next steps and possible fixes\n"
            "- Be precise, practical, and non-hallucinatory\n"
        )

        full_prompt = (
            f"{system_prompt}\n\n"
            f"=== USER MESSAGE ===\n{original_message}\n\n"
            f"=== ERROR INFO ===\n{error_section or 'No explicit error detected.'}\n\n"
            f"=== CODE INFO ===\n{code_section or 'No explicit code detected.'}\n\n"
            f"=== ANALYSIS ===\n{analysis_section}\n\n"
            "Now produce a helpful, step-by-step explanation and suggested fix."
        )

        response_text = self.client.send_message(full_prompt)
        return response_text