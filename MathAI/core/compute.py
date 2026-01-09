"""
Deterministic SymPy Computation Engine.

This is the ONLY place where math is actually computed. 
All results are authoritative and come directly from SymPy.
"""
import re
from typing import Optional, List, Tuple
from sympy import (
    symbols, Symbol, diff, integrate, simplify, solve, expand, factor,
    sin, cos, tan, cot, sec, csc,
    sinh, cosh, tanh, coth, sech, csch,
    asin, acos, atan, acot, asec, acsc,
    asinh, acosh, atanh, acoth, asech, acsch,
    log, ln, exp, sqrt, Abs, sign,
    pi, E, I, oo,
    Eq, latex, S
)
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
    convert_xor,
    function_exponentiation
)
from sympy.parsing.latex import parse_latex
from langfuse import observe
from .models import RoutingDecision, ComputeResult


class SymPyEngine:
    """
    Deterministic symbolic computation engine using SymPy.
    Executes differentiate, integrate, simplify, and solve operations.
    """
    
    # Standard symbol mapping
    SYMBOL_MAP = {
        "x": symbols("x"),
        "y": symbols("y"),
        "z": symbols("z"),
        "t": symbols("t"),
        "n": symbols("n", integer=True),
        "theta": symbols("theta"),
        "phi": symbols("phi"),
        "alpha": symbols("alpha"),
        "beta": symbols("beta"),
        "a": symbols("a"),
        "b": symbols("b"),
        "c": symbols("c"),
    }
    
    # Function mapping for parsing
    FUNCTION_MAP = {
        "sin": sin, "cos": cos, "tan": tan,
        "cot": cot, "sec": sec, "csc": csc,
        "sinh": sinh, "cosh": cosh, "tanh": tanh,
        "coth": coth, "sech": sech, "csch": csch,
        "asin": asin, "acos": acos, "atan": atan,
        "arcsin": asin, "arccos": acos, "c": atan,
        "acot": acot, "asec": asec, "acsc": acsc,
        "asinh": asinh, "acosh": acosh, "atanh": atanh,
        "acoth": acoth, "asech": asech, "acsch": acsch,
        "log": log, "ln": ln, "exp": exp,
        "sqrt": sqrt, "abs": Abs, "sign": sign,
        "pi": pi, "e": E, "i": I
    }
    
    def __init__(self):
        self.transformations = (
            standard_transformations +
            (implicit_multiplication_application, convert_xor, function_exponentiation)
        )
        self.local_dict = {**self.SYMBOL_MAP, **self.FUNCTION_MAP}
    
    def _parse_expression(self, expr_str: str) -> Tuple[Optional[any], Optional[str]]:
        """
        Parse a mathematical expression from string.
        Handles plain text, LaTeX, and mixed formats.
        
        Returns:
            Tuple of (parsed_expr, error_message)
        """
        expr_str = expr_str.strip()
        
        # Try LaTeX parsing first if it looks like LaTeX
        if any(tex in expr_str for tex in ["\\frac", "\\sqrt", "\\int", "\\sum", "\\cdot", "^{", "_{", "\\", "{"]):
            try:
                # Clean up LaTeX
                cleaned = expr_str.replace("\\,", "").replace("\\;", "").replace("\\!", "")
                parsed = parse_latex(cleaned)
                return parsed, None
            except Exception:
                pass  # Fall through to standard parsing
        
        # Preprocess for common patterns
        expr_str = self._preprocess(expr_str)
        
        # Try standard parsing
        try:
            parsed = parse_expr(
                expr_str,
                transformations=self.transformations,
                local_dict=self.local_dict,
                evaluate=False
            )
            return parsed, None
        except Exception as e:
            return None, f"Failed to parse expression: {str(e)}"
    
    def _preprocess(self, expr: str) -> str:
        """Preprocess expression string for better parsing."""
        # Remove 'dx', 'dy' etc. at the end (common in integrals)
        expr = re.sub(r'\s*d[a-z]\s*$', '', expr, flags=re.IGNORECASE)
        
        # Handle = 0 for solve operations
        expr = expr.replace("= 0", "").replace("=0", "").strip()
        
        # Replace ^ with ** for exponentiation
        # (convert_xor should handle this, but just in case)
        
        # Handle multiplication notation
        expr = expr.replace("×", "*").replace("·", "*")
        
        # Handle common LaTeX-ish patterns
        expr = expr.replace("\\cdot", "*")
        expr = expr.replace("\\times", "*")
        
        return expr
    
    def _get_variable(self, var_name: str) -> Symbol:
        """Get or create a SymPy symbol for the variable."""
        if var_name in self.SYMBOL_MAP:
            return self.SYMBOL_MAP[var_name]
        return symbols(var_name)
    
    @observe(name="sympy_compute")
    def compute(self, routing: RoutingDecision) -> ComputeResult:
        """
        Execute the mathematical operation specified by the routing decision.
        
        Args:
            routing: The RoutingDecision from the router
            
        Returns:
            ComputeResult with the authoritative SymPy result
        """
        # Parse the expression
        expr, parse_error = self._parse_expression(routing.expression)
        if parse_error:
            return ComputeResult(
                success=False,
                error=parse_error,
                error_type="parse_error"
            )
        
        # Get the variable
        var = self._get_variable(routing.variable)
        
        try:
            if routing.operation == "differentiate":
                return self._differentiate(expr, var)
            elif routing.operation == "integrate":
                return self._integrate(expr, var)
            elif routing.operation == "simplify":
                return self._simplify(expr)
            elif routing.operation == "solve":
                solve_var = self._get_variable(routing.solve_for or routing.variable)
                return self._solve(expr, solve_var, routing.expression)
            else:
                return ComputeResult(
                    success=False,
                    error=f"Unknown operation: {routing.operation}",
                    error_type="computation_error"
                )
        except Exception as e:
            return ComputeResult(
                success=False,
                error=f"Computation failed: {str(e)}",
                error_type="computation_error"
            )
    
    def _differentiate(self, expr, var: Symbol) -> ComputeResult:
        """Compute the derivative."""
        result = diff(expr, var)
        simplified = simplify(result)
        
        return ComputeResult(
            success=True,
            result=str(simplified),
            latex_result=latex(simplified),
            intermediate_steps=[
                f"Original: {latex(expr)}",
                f"Apply d/d{var}: {latex(result)}",
                f"Simplified: {latex(simplified)}"
            ]
        )
    
    def _integrate(self, expr, var: Symbol) -> ComputeResult:
        """Compute the indefinite integral."""
        result = integrate(expr, var)
        
        # Check if integration was successful (SymPy returns unevaluated integral if it can't solve)
        if result.has(integrate):
            return ComputeResult(
                success=False,
                error="Could not find closed-form antiderivative",
                error_type="computation_error",
                result=str(result),
                latex_result=latex(result)
            )
        
        return ComputeResult(
            success=True,
            result=f"{str(result)} + C",
            latex_result=f"{latex(result)} + C",
            intermediate_steps=[
                f"Integrand: {latex(expr)}",
                f"∫ {latex(expr)} d{var} = {latex(result)} + C"
            ]
        )
    
    def _simplify(self, expr) -> ComputeResult:
        """Simplify the expression."""
        # Try multiple simplification strategies
        simplified = simplify(expr)
        expanded = expand(expr)
        factored = factor(expr)
        
        # Choose the "simplest" form (shortest string representation)
        candidates = [
            ("simplified", simplified),
            ("expanded", expanded),
            ("factored", factored)
        ]
        best_name, best_result = min(candidates, key=lambda x: len(str(x[1])))
        
        steps = [f"Original: {latex(expr)}"]
        if str(simplified) != str(expr):
            steps.append(f"Simplified: {latex(simplified)}")
        if str(expanded) != str(expr) and str(expanded) != str(simplified):
            steps.append(f"Expanded: {latex(expanded)}")
        if str(factored) != str(expr) and str(factored) not in [str(simplified), str(expanded)]:
            steps.append(f"Factored: {latex(factored)}")
        steps.append(f"Best form ({best_name}): {latex(best_result)}")
        
        return ComputeResult(
            success=True,
            result=str(best_result),
            latex_result=latex(best_result),
            intermediate_steps=steps
        )
    
    def _solve(self, expr, var: Symbol, original_expr: str) -> ComputeResult:
        """Solve the equation for the given variable."""
        # Check if it's an equation (contains =)
        if "=" in original_expr:
            parts = original_expr.split("=")
            if len(parts) == 2:
                left, _ = self._parse_expression(parts[0])
                right, _ = self._parse_expression(parts[1])
                if left is not None and right is not None:
                    expr = left - right
        
        solutions = solve(expr, var)
        
        if not solutions:
            return ComputeResult(
                success=False,
                error="No solutions found",
                error_type="computation_error"
            )
        
        if isinstance(solutions, dict):
            solutions = list(solutions.values())
        
        # Format solutions
        if len(solutions) == 1:
            result_str = f"{var} = {solutions[0]}"
            latex_str = f"{latex(var)} = {latex(solutions[0])}"
        else:
            result_str = f"{var} = " + " or ".join(str(s) for s in solutions)
            latex_str = f"{latex(var)} = " + " \\text{{ or }} ".join(latex(s) for s in solutions)
        
        steps = [
            f"Equation: {latex(expr)} = 0",
            f"Solving for {var}...",
            f"Solutions: {latex_str}"
        ]
        
        return ComputeResult(
            success=True,
            result=result_str,
            latex_result=latex_str,
            intermediate_steps=steps
        )

