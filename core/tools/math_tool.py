# core/tools/math_tool.py

class MathTool:
    """
    Safe math evaluation tool.
    Supports basic arithmetic expressions.
    """

    def calculate(self, expression: str) -> str:
        try:
            allowed = "0123456789+-*/(). "
            if any(ch not in allowed for ch in expression):
                return "I can only calculate basic arithmetic expressions."

            result = eval(expression, {"__builtins__": {}})
            return str(result)
        except Exception:
            return "I couldn't calculate that expression."