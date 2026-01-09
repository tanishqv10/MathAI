"""
Main Pipeline for MathAI v2.

Orchestrates the complete workflow:
1. Router classifies the operation
2. SymPy computes the result (parallel with RAG)
3. RAG retrieves explanation knowledge (parallel with compute)
4. LLM generates grounded explanation
5. Response is assembled

All steps are instrumented with LangFuse.
Includes caching for common queries.
"""
import time
import hashlib
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict, Any
from functools import lru_cache
from openai import OpenAI
from langfuse import Langfuse, observe, get_client

from .models import (
    RoutingDecision, ComputeResult, ExplanationContext,
    MathResponse, TraceMetadata, RetrievedChunk
)
from .router import MathRouter
from .compute import SymPyEngine
from .rag import MathRAG
from .explainer import MathExplainer

# Simple in-memory cache for responses
_response_cache: Dict[str, MathResponse] = {}
_CACHE_MAX_SIZE = 100


class MathPipeline:
    """
    Main orchestrator for the MathAI v2 pipeline.
    Coordinates all components and manages the end-to-end flow.
    Features: parallel execution, caching, and streaming support.
    """
    
    def __init__(
        self,
        openai_client: Optional[OpenAI] = None,
        router_model: str = "gpt-4o-mini",
        explainer_model: str = "gpt-4o-mini",
        langfuse_enabled: bool = True,
        cache_enabled: bool = True
    ):
        self.client = openai_client or OpenAI()
        
        # Initialize components
        self.router = MathRouter(client=self.client, model=router_model)
        self.compute_engine = SymPyEngine()
        self.rag = MathRAG(openai_client=self.client)
        self.explainer = MathExplainer(client=self.client, model=explainer_model)
        
        # Thread pool for parallel execution
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        # Caching
        self.cache_enabled = cache_enabled
        
        # LangFuse setup
        self.langfuse_enabled = langfuse_enabled
        if langfuse_enabled:
            try:
                self.langfuse = Langfuse()
            except Exception:
                self.langfuse = None
                self.langfuse_enabled = False
    
    def _get_cache_key(self, query: str) -> str:
        """Generate a cache key from the query."""
        return hashlib.md5(query.lower().strip().encode()).hexdigest()
    
    def _get_cached_response(self, query: str) -> Optional[MathResponse]:
        """Check if we have a cached response."""
        if not self.cache_enabled:
            return None
        cache_key = self._get_cache_key(query)
        return _response_cache.get(cache_key)
    
    def _cache_response(self, query: str, response: MathResponse):
        """Cache a successful response."""
        if not self.cache_enabled or not response.success:
            return
        # Limit cache size
        if len(_response_cache) >= _CACHE_MAX_SIZE:
            # Remove oldest entry (simple FIFO)
            oldest_key = next(iter(_response_cache))
            del _response_cache[oldest_key]
        cache_key = self._get_cache_key(query)
        _response_cache[cache_key] = response
    
    @observe(name="math_pipeline")
    def process(self, query: str) -> MathResponse:
        """
        Process a mathematical query through the full pipeline.
        Uses caching and parallel execution for performance.
        
        Args:
            query: The user's natural language math query
            
        Returns:
            MathResponse with answer, explanation, and metadata
        """
        # Check cache first
        cached = self._get_cached_response(query)
        if cached:
            return cached
        
        timings = {}
        
        # Step 1: Route the query
        start = time.perf_counter()
        try:
            routing = self.router.route(query)
            timings["routing"] = (time.perf_counter() - start) * 1000
        except Exception as e:
            return MathResponse(
                success=False,
                query=query,
                operation="unknown",
                error=f"Routing failed: {str(e)}",
                error_type="routing_error"
            )
        
        # Step 2 & 3: Run compute and RAG retrieval IN PARALLEL
        start = time.perf_counter()
        try:
            # Submit both tasks to thread pool
            compute_future = self.executor.submit(self.compute_engine.compute, routing)
            rag_future = self.executor.submit(self.rag.retrieve, routing, 5)
            
            # Wait for both to complete
            compute_result = compute_future.result()
            retrieved_chunks = rag_future.result()
            
            timings["compute_and_retrieval"] = (time.perf_counter() - start) * 1000
        except Exception as e:
            return MathResponse(
                success=False,
                query=query,
                operation=routing.operation,
                error=f"Computation failed: {str(e)}",
                error_type="computation_error"
            )
        
        # If computation failed, return early with the error
        if not compute_result.success:
            return MathResponse(
                success=False,
                query=query,
                operation=routing.operation,
                answer=compute_result.result,
                latex_answer=compute_result.latex_result,
                error=compute_result.error,
                error_type=compute_result.error_type,
                assumptions=routing.assumptions
            )
        
        # Step 4: Generate explanation
        start = time.perf_counter()
        try:
            explanation_context = ExplanationContext(
                original_query=query,
                routing_decision=routing,
                compute_result=compute_result,
                retrieved_chunks=retrieved_chunks
            )
            explanation = self.explainer.explain(explanation_context)
            timings["explanation"] = (time.perf_counter() - start) * 1000
        except Exception as e:
            # Non-fatal: return result without explanation
            explanation = f"(Explanation unavailable: {str(e)})"
            timings["explanation"] = 0
        
        # Step 5: Assemble response
        total_time = sum(timings.values())
        
        citations = [
            f"[{chunk.chunk_id}] {chunk.category}"
            for chunk in retrieved_chunks
            if chunk.relevance_score > 0.5
        ]
        
        # Update LangFuse with metadata
        if self.langfuse_enabled:
            try:
                get_client().update_current_span(
                    metadata={
                        "operation": routing.operation,
                        "expression": routing.expression,
                        "variable": routing.variable,
                        "timings_ms": timings,
                        "retrieved_chunk_ids": [c.chunk_id for c in retrieved_chunks],
                        "confidence": routing.confidence,
                        "cached": False
                    }
                )
            except Exception:
                pass  # LangFuse errors should not break the pipeline
        
        response = MathResponse(
            success=True,
            query=query,
            operation=routing.operation,
            answer=compute_result.result,
            latex_answer=compute_result.latex_result,
            explanation=explanation,
            assumptions=routing.assumptions,
            citations=citations
        )
        
        # Cache the successful response
        self._cache_response(query, response)
        
        return response
    
    def process_with_trace(self, query: str) -> tuple[MathResponse, Optional[TraceMetadata]]:
        """
        Process a query and return both the response and trace metadata.
        
        Args:
            query: The user's natural language math query
            
        Returns:
            Tuple of (MathResponse, TraceMetadata)
        """
        import uuid
        
        trace_id = str(uuid.uuid4())
        timings = {}
        
        # Route
        start = time.perf_counter()
        routing = self.router.route(query)
        timings["routing"] = (time.perf_counter() - start) * 1000
        
        # Compute
        start = time.perf_counter()
        compute_result = self.compute_engine.compute(routing)
        timings["compute"] = (time.perf_counter() - start) * 1000
        
        # Retrieve
        start = time.perf_counter()
        retrieved_chunks = self.rag.retrieve(routing)
        timings["retrieval"] = (time.perf_counter() - start) * 1000
        
        # Explain
        start = time.perf_counter()
        explanation_context = ExplanationContext(
            original_query=query,
            routing_decision=routing,
            compute_result=compute_result,
            retrieved_chunks=retrieved_chunks
        )
        explanation = self.explainer.explain(explanation_context)
        timings["explanation"] = (time.perf_counter() - start) * 1000
        
        total_time = sum(timings.values())
        
        response = MathResponse(
            success=compute_result.success,
            query=query,
            operation=routing.operation,
            answer=compute_result.result,
            latex_answer=compute_result.latex_result,
            explanation=explanation if compute_result.success else None,
            assumptions=routing.assumptions,
            citations=[c.chunk_id for c in retrieved_chunks if c.relevance_score > 0.5],
            error=compute_result.error,
            error_type=compute_result.error_type
        )
        
        metadata = TraceMetadata(
            trace_id=trace_id,
            routing_latency_ms=timings["routing"],
            compute_latency_ms=timings["compute"],
            retrieval_latency_ms=timings["retrieval"],
            explanation_latency_ms=timings["explanation"],
            total_latency_ms=total_time,
            retrieved_chunk_ids=[c.chunk_id for c in retrieved_chunks]
        )
        
        return response, metadata
    
    def initialize(self):
        """Initialize the pipeline (e.g., populate knowledge base)."""
        self.rag.initialize_knowledge_base()

