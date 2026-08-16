# core/tools/calculator.py

import ast
import operator as op

class SafeCalculator:
    """
    A safe math evaluator using Python's AST.
    Supports +, -, *, /, **, %, parentheses.
    """

    # Allowed operators
    operators = {
        ast.Add: op.add,
        ast.Sub: op.sub,
        ast.Mult: op.mul,
        ast.Div: op.truediv,
        ast.Pow: op.pow,
        ast.Mod: op.mod,
        ast.USub: op.neg,
    }

    def evaluate(self, expression: str):
        try:
            node = ast.parse(expression, mode='eval').body
            return self._eval(node)
        except Exception:
            return None

    def _eval(self, node):
        if isinstance(node, ast.Num):  # number
            return node.n

        if isinstance(node, ast.BinOp):  # binary operation
            left = self._eval(node.left)
            right = self._eval(node.right)
            operator = self.operators.get(type(node.op))
            if operator:
                return operator(left, right)

        if isinstance(node, ast.UnaryOp):  # unary operation
            operator = self.operators.get(type(node.op))
            operand = self._eval(node.operand)
            if operator:
                return operator(operand)

        raise ValueError("Unsupported expression")