"""Safe calculator tool for mathematical expressions."""

import ast
import math
import operator
from langchain_core.tools import tool

# Allowed operators
OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

# Allowed math functions
SAFE_FUNCTIONS = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sum": sum,
    "sqrt": math.sqrt,
    "cbrt": lambda x: x ** (1/3),
    "log": math.log,
    "log2": math.log2,
    "log10": math.log10,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "atan2": math.atan2,
    "ceil": math.ceil,
    "floor": math.floor,
    "pi": math.pi,
    "e": math.e,
    "inf": math.inf,
    "factorial": math.factorial,
    "gcd": math.gcd,
    "degrees": math.degrees,
    "radians": math.radians,
}


class SafeEvaluator(ast.NodeVisitor):
    """AST-based safe expression evaluator."""

    def visit_Expression(self, node):
        return self.visit(node.body)

    def visit_BinOp(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        op_type = type(node.op)
        if op_type not in OPERATORS:
            raise ValueError(f"Operator {op_type.__name__} is not allowed")
        return OPERATORS[op_type](left, right)

    def visit_UnaryOp(self, node):
        operand = self.visit(node.operand)
        op_type = type(node.op)
        if op_type not in OPERATORS:
            raise ValueError(f"Operator {op_type.__name__} is not allowed")
        return OPERATORS[op_type](operand)

    def visit_Call(self, node):
        if not isinstance(node.func, ast.Name):
            raise ValueError("Only named functions are allowed")
        func_name = node.func.id
        if func_name not in SAFE_FUNCTIONS:
            raise ValueError(f"Function '{func_name}' is not allowed")
        func = SAFE_FUNCTIONS[func_name]
        args = [self.visit(arg) for arg in node.args]
        return func(*args)

    def visit_Num(self, node):  # Python < 3.8
        return node.n

    def visit_Constant(self, node):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"Constants of type {type(node.value)} are not allowed")

    def visit_Name(self, node):
        if node.id in SAFE_FUNCTIONS:
            val = SAFE_FUNCTIONS[node.id]
            if callable(val):
                raise ValueError(f"'{node.id}' is a function, not a constant")
            return val
        raise ValueError(f"Variable '{node.id}' is not allowed")

    def generic_visit(self, node):
        raise ValueError(f"Unsupported expression type: {type(node).__name__}")


def _safe_eval(expression: str) -> float:
    """Safely evaluate a mathematical expression."""
    tree = ast.parse(expression.strip(), mode="eval")
    evaluator = SafeEvaluator()
    return evaluator.visit(tree)


@tool
def calculate(expression: str) -> str:
    """
    Evaluate mathematical expressions safely.
    Supports: +, -, *, /, //, %, ** (power), sqrt, log, sin, cos, tan,
    ceil, floor, abs, round, factorial, degrees, radians, pi, e.

    Examples:
        - "2 + 2" → 4
        - "sqrt(144)" → 12.0
        - "2 ** 10" → 1024
        - "sin(pi / 2)" → 1.0
        - "log(100, 10)" → 2.0

    Args:
        expression: A mathematical expression to evaluate

    Returns:
        The computed result
    """
    try:
        # Normalize expression
        expr = expression.strip()
        expr = expr.replace("^", "**")  # Support ^ as power operator

        result = _safe_eval(expr)

        # Format output
        if isinstance(result, float):
            if result == int(result) and abs(result) < 1e15:
                return f"{expression} = {int(result)}"
            return f"{expression} = {result:.10g}"
        return f"{expression} = {result}"

    except ZeroDivisionError:
        return "Error: Division by zero"
    except ValueError as e:
        return f"Expression error: {str(e)}"
    except SyntaxError:
        return f"Syntax error in expression: '{expression}'"
    except OverflowError:
        return "Error: Result is too large to compute"
    except Exception as e:
        return f"Calculation failed: {str(e)}"
