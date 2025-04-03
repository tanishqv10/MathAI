from sympy import symbols, sympify, solve
from sympy.core.sympify import SympifyError
from utils.preprocess import preprocess_expression

def solve_equation(equation: str) -> dict:
    try:
        expr = preprocess_expression(expr)
        x = symbols("x")
        parsed = sympify(equation)
        solutions = solve(parsed, x)

        return {
            "success": 1,
            "input": equation,
            "steps": [f"Solving equation: {parsed}"],
            "solution": [str(sol) for sol in solutions],
            "latex": ', '.join([str(sol) for sol in solutions])
        }

    except SympifyError as e:
        return {"success": 0, "error": f"Invalid equation: {str(e)}"}
