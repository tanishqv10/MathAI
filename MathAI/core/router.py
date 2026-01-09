"""
LLM-based Router for classifying math operations.

This lightweight router classifies user requests into exactly one operation:
differentiate, integrate, simplify, or solve. It also extracts structured
inputs like the expression and the variable.
"""
import json
from typing import Optional
from openai import OpenAI
from langfuse import observe
from langfuse.openai import openai  # LangFuse-wrapped OpenAI for token tracking
from .models import RoutingDecision


ROUTER_SYSTEM_PROMPT = """You are a mathematical query router. Your job is to:
1. Classify the user's math request into exactly ONE operation: differentiate, integrate, simplify, or solve
2. Extract the mathematical expression from the query
3. Identify the variable (default to 'x' if not specified)
4. Note any explicit assumptions mentioned

Classification guidelines:
- "differentiate", "derivative", "d/dx", "find the rate of change" → differentiate
- "integrate", "integral", "antiderivative", "find the area" → integrate  
- "simplify", "reduce", "expand", "factor", "combine" → simplify
- "solve", "find x", "what is x", "evaluate for", "find roots", "find zeros" → solve

You MUST respond with valid JSON only, no other text. Schema:
{
    "operation": "differentiate" | "integrate" | "simplify" | "solve",
    "expression": "<the math expression>",
    "variable": "<variable, default 'x'>",
    "solve_for": "<variable to solve for, only if operation is solve>",
    "assumptions": ["<any assumptions>"],
    "confidence": <0.0 to 1.0>
}

Examples:

Query: "differentiate sin(x^2) with respect to x"
Response: {"operation": "differentiate", "expression": "sin(x^2)", "variable": "x", "solve_for": null, "assumptions": [], "confidence": 1.0}

Query: "find the integral of e^x * cos(x) dx"
Response: {"operation": "integrate", "expression": "e^x * cos(x)", "variable": "x", "solve_for": null, "assumptions": [], "confidence": 1.0}

"""


class MathRouter:
    """
    Lightweight LLM-based router for classifying math operations.
    Uses a smaller, faster model (gpt-4o-mini) for routing decisions.
    """
    
    def __init__(
        self,
        client: Optional[OpenAI] = None,
        model: str = "gpt-4o-mini"
    ):
        # Use LangFuse-wrapped client for automatic token tracking
        self.client = openai.OpenAI()
        self.model = model
    
    @observe(name="math_router")
    def route(self, query: str) -> RoutingDecision:
        """
        Classify a math query into an operation and extract structured inputs.
        
        Args:
            query: The user's natural language math query
            
        Returns:
            RoutingDecision with operation, expression, variable, etc.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
                    {"role": "user", "content": query}
                ],
                temperature=0,
                max_tokens=256,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            parsed = json.loads(content)
            
            # Validate and create RoutingDecision
            return RoutingDecision(
                operation=parsed.get("operation", "simplify"),
                expression=parsed.get("expression", query),
                variable=parsed.get("variable", "x"),
                solve_for=parsed.get("solve_for"),
                assumptions=parsed.get("assumptions", []),
                confidence=parsed.get("confidence", 0.8)
            )
            
        except json.JSONDecodeError as e:
            # Fallback: try to parse as simplify operation
            return RoutingDecision(
                operation="simplify",
                expression=query,
                variable="x",
                confidence=0.3,
                assumptions=[f"Parse error, defaulting to simplify: {str(e)}"]
            )
        except Exception as e:
            raise RuntimeError(f"Router failed: {str(e)}")

