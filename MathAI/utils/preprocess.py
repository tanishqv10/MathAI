from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
    convert_xor,
    function_exponentiation
)
from sympy import symbols, sin, cos, tan, log, ln, sqrt, exp

def preprocess_expression(expr: str):
    transformations = (
        standard_transformations +
        (implicit_multiplication_application, convert_xor, function_exponentiation)
    )

    # Define variables
    x, y, theta = symbols('x y theta')

    # Define local dictionary with functions
    local_dict = {
        "x": x,
        "y": y,
        "theta": theta,
        "sin": sin,
        "cos": cos,
        "tan": tan,
        "log": log,
        "ln": ln,
        "sqrt": sqrt,
        "exp": exp
    }

    try:
        parsed = parse_expr(expr, transformations=transformations, local_dict=local_dict, evaluate=False)
        return str(parsed)
    except Exception as e:
        return f"ERROR: {e}"


if __name__ == "__main__":
    test_cases = [
        "5sin x - 3cos y",                # function + variable + coefficient
        "2x + 3y",                        # implicit multiplication
        "sin x + cos x",                 # basic function call
        "sin^2(x) + cos^2(x)",             # powers of functions
        "sin(x^2)",                      # nested powers
        "x(x + 1)",                      # variable followed by bracket
        "(x+1)(x-1)",                    # bracket followed by bracket
        "log x + ln y",                  # multiple log-like functions
        "sqrt x + exp x",                # root and exponential
        "tan theta + cos x y",           # function + implicit mult
        "3ln x + sin x y",               # ln + chained implicit mult
        "sin^3(x) + 2cos^2 (x) - x^2",     # complex powers & mult
        "4(x + 2)",                      # constant outside brackets
        "sin(x)cos(x)",                  # adjacent functions
        "5sin(x) + 6x*cos(x)"              # combo of proper and implicit
    ]

    print("Testing preprocess_expression...\n")
    for expr in test_cases:
        processed = preprocess_expression(expr)
        print(f"Original:  {expr}")
        print(f"Processed: {processed}")
        print("-" * 50)


