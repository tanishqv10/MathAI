from sympy import symbols, sympify, integrate
from sympy.core.sympify import SympifyError
from utils.preprocess import preprocess_expression

def integrate_expression(expr: str) -> dict:
    try:
        expr = preprocess_expression(expr)
        x = symbols("x")
        parsed = sympify(expr)
        terms = parsed.as_ordered_terms()

        steps = []
        integral_terms = []

        for term in terms:
            i_term = integrate(term, x)
            steps.append(f"∫({term}) dx = {i_term}")
            integral_terms.append(i_term)

        result = sum(integral_terms)

        return {
            "success": 1,
            "input": expr,
            "steps": steps,
            "integral": str(result),
            "latex": str(result)
        }

    except SympifyError as e:
        return {"success": 0, "error": f"Invalid integral: {str(e)}"}
