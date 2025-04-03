from sympy import sympify, simplify
from sympy.core.sympify import SympifyError
from utils.preprocess import preprocess_expression

def simplify_expression(expr: str) -> dict:
    try:
        expr = preprocess_expression(expr)
        parsed = sympify(expr)
        simplified = simplify(parsed)

        return {
            "success": 1,
            "input": expr,
            "steps": [f"Original: {parsed}", f"Simplified: {simplified}"],
            "simplified": str(simplified),
            "latex": str(simplified)
        }

    except SympifyError as e:
        return {"success": 0, "error": f"Invalid expression: {str(e)}"}
