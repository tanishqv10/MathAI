"""
MathAI v2 - AI-powered Mathematical Assistant

A hybrid system combining deterministic symbolic computation
with LLM-powered grounded explanations.
"""

__version__ = "2.0.0"

from .core.pipeline import MathPipeline
from .core.models import MathResponse, RoutingDecision, ComputeResult

__all__ = ["MathPipeline", "MathResponse", "RoutingDecision", "ComputeResult"]

