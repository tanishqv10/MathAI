"""
Pydantic models for structured data throughout the pipeline.
"""
from typing import Optional, List, Literal
from pydantic import BaseModel, Field


class RoutingDecision(BaseModel):
    """Output from the router - classifies the math operation."""
    operation: Literal["differentiate", "integrate", "simplify", "solve"] = Field(
        description="The mathematical operation to perform"
    )
    expression: str = Field(
        description="The mathematical expression to operate on"
    )
    variable: Optional[str] = Field(
        default="x",
        description="The variable for differentiation/integration"
    )
    solve_for: Optional[str] = Field(
        default=None,
        description="Variable to solve for (for solve operations)"
    )
    assumptions: Optional[List[str]] = Field(
        default_factory=list,
        description="Any assumptions extracted from the query (e.g., 'x is positive')"
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score of the routing decision"
    )


class ComputeResult(BaseModel):
    """Output from the SymPy computation engine."""
    success: bool = Field(description="Whether computation succeeded")
    result: Optional[str] = Field(
        default=None,
        description="The computed result as a string"
    )
    latex_result: Optional[str] = Field(
        default=None,
        description="The result in LaTeX format"
    )
    intermediate_steps: Optional[List[str]] = Field(
        default_factory=list,
        description="Intermediate computation steps if available"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if computation failed"
    )
    error_type: Optional[Literal["parse_error", "computation_error", "underspecified"]] = Field(
        default=None,
        description="Type of error if computation failed"
    )


class RetrievedChunk(BaseModel):
    """A chunk retrieved from the knowledge base."""
    chunk_id: str = Field(description="Unique identifier for the chunk")
    content: str = Field(description="The text content of the chunk")
    category: str = Field(description="Category: rule_intuition, method_heuristic, pitfall, engine_note")
    relevance_score: float = Field(description="Similarity score from vector search")
    source: Optional[str] = Field(default=None, description="Source reference")


class ExplanationContext(BaseModel):
    """Context passed to the explanation generator."""
    original_query: str
    routing_decision: RoutingDecision
    compute_result: ComputeResult
    retrieved_chunks: List[RetrievedChunk]


class MathResponse(BaseModel):
    """Final response returned to the user."""
    success: bool
    query: str
    operation: str
    answer: Optional[str] = Field(default=None, description="Final answer from SymPy")
    latex_answer: Optional[str] = Field(default=None, description="Answer in LaTeX format")
    explanation: Optional[str] = Field(default=None, description="Step-by-step explanation from LLM")
    assumptions: Optional[List[str]] = Field(default_factory=list)
    citations: Optional[List[str]] = Field(
        default_factory=list,
        description="References to retrieved knowledge chunks"
    )
    error: Optional[str] = None
    error_type: Optional[str] = None


class TraceMetadata(BaseModel):
    """Metadata for LangFuse tracing."""
    trace_id: str
    routing_latency_ms: float
    compute_latency_ms: float
    retrieval_latency_ms: float
    explanation_latency_ms: float
    total_latency_ms: float
    retrieved_chunk_ids: List[str]
    token_usage: Optional[dict] = None

