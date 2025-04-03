from sympy import symbols, sympify, diff
from sympy.core.sympify import SympifyError
from utils.preprocess import preprocess_expression

def differentiate_expression(expr: str) -> dict:
    try:
        expr = preprocess_expression(expr)
        x = symbols("x")
        parsed = sympify(expr)
        terms = parsed.as_ordered_terms()

        steps = []
        derivative_terms = []

        for term in terms:
            d_term = diff(term, x)
            steps.append(f"d({term})/dx = {d_term}")
            derivative_terms.append(d_term)

        derivative = sum(derivative_terms)

        return {
            "success": 1,
            "input": expr,
            "steps": steps,
            "derivative": str(derivative),
            "latex": str(derivative)
        }

    except SympifyError as e:
        return {"success": 0, "error": f"Invalid derivative: {str(e)}"}
