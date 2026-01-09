"""
MathAI v2 - FastAPI Application

A mathematical assistant that:
1. Routes queries to the correct operation (differentiate, integrate, simplify, solve)
2. Computes authoritative results using SymPy
3. Retrieves explanation knowledge from a RAG system
4. Generates grounded explanations using LLM
5. Instruments everything with LangFuse
6. Supports streaming responses for faster perceived latency
"""
import os
import sys
import json
from contextlib import asynccontextmanager
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from core.pipeline import MathPipeline
from core.models import MathResponse, ExplanationContext
from core.instrumentation import instrumentation
from langfuse import Langfuse

# Version
VERSION = "2.0.0"

# Global pipeline instance
pipeline: Optional[MathPipeline] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup."""
    global pipeline
    
    print(f"Starting MathAI v{VERSION}...")
    
    # Initialize the pipeline (using gpt-4o-mini for both router and explainer for speed)
    pipeline = MathPipeline(
        router_model=os.environ.get("ROUTER_MODEL", "gpt-4o-mini"),
        explainer_model=os.environ.get("EXPLAINER_MODEL", "gpt-4o-mini"),  # Changed from gpt-4o for speed
        langfuse_enabled=os.environ.get("LANGFUSE_ENABLED", "true").lower() == "true"
    )
    
    # Initialize knowledge base (if vector DB available)
    try:
        pipeline.initialize()
        print("Knowledge base initialized")
    except Exception as e:
        print(f"Warning: Could not initialize knowledge base: {e}")
    
    print("MathAI v2 ready!")
    
    yield
    
    # Cleanup
    instrumentation.flush()
    print("MathAI shutdown complete")


app = FastAPI(
    title="MathAI",
    version=VERSION,
    description="AI-powered mathematical assistant with grounded explanations",
    lifespan=lifespan
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class SolveRequest(BaseModel):
    query: str


class SolveResponse(BaseModel):
    success: bool
    query: str
    operation: str
    answer: Optional[str] = None
    latex_answer: Optional[str] = None
    explanation: Optional[str] = None
    assumptions: Optional[list] = None
    citations: Optional[list] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    langfuse_enabled: bool


# Endpoints
@app.get("/", response_model=dict)
async def root():
    """Root endpoint with API info."""
    return {
        "name": "MathAI",
        "version": VERSION,
        "description": "AI-powered mathematical assistant",
        "endpoints": {
            "/solve": "POST - Solve a math problem",
            "/health": "GET - Health check"
        }
    }


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version=VERSION,
        langfuse_enabled=instrumentation.enabled
    )


@app.post("/solve", response_model=SolveResponse)
async def solve(request: SolveRequest):
    """
    Solve a mathematical query.
    
    The query can be:
    - Plain text: "differentiate sin(x^2) with respect to x"
    - LaTeX: "\\int e^x \\cos(x) dx"
    - Mixed: "simplify (x^2 - 1)/(x - 1)"
    
    Returns the authoritative SymPy result with an AI-generated explanation.
    """
    global pipeline
    
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")
    
    query = request.query.strip()
    
    if not query:
        return SolveResponse(
            success=False,
            query="",
            operation="unknown",
            error="Missing 'query' in request"
        )
    
    print(f"[v2] Processing query: {query}")
    
    try:
        # Process through the pipeline
        result = pipeline.process(query)
        
        print(f"[v2] Result: {result.operation} -> {result.answer}")
        
        return SolveResponse(
            success=result.success,
            query=result.query,
            operation=result.operation,
            answer=result.answer,
            latex_answer=result.latex_answer,
            explanation=result.explanation,
            assumptions=result.assumptions,
            citations=result.citations,
            error=result.error
        )
        
    except Exception as e:
        print(f"[v2] Error: {str(e)}")
        return SolveResponse(
            success=False,
            query=query,
            operation="unknown",
            error=str(e)
        )


@app.post("/solve/stream")
async def solve_stream(request: SolveRequest):
    """
    Streaming endpoint that returns the answer immediately,
    then streams the explanation for better perceived latency.
    
    Returns Server-Sent Events (SSE) with:
    - First event: { type: "answer", data: {...} } with the computed answer
    - Following events: { type: "explanation", data: "token" } with explanation tokens
    - Final event: { type: "done" }
    
    Supports caching - cached responses return instantly without streaming.
    """
    global pipeline
    
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")
    
    query = request.query.strip()
    
    if not query:
        raise HTTPException(status_code=400, detail="Missing query")
    
    # Check cache first
    cached = pipeline._get_cached_response(query)
    if cached:
        # Return cached response as immediate stream
        def generate_cached():
            answer_data = {
                "type": "answer",
                "data": {
                    "success": cached.success,
                    "query": cached.query,
                    "operation": cached.operation,
                    "answer": cached.answer,
                    "latex_answer": cached.latex_answer,
                    "assumptions": cached.assumptions,
                    "citations": cached.citations
                }
            }
            yield f"data: {json.dumps(answer_data)}\n\n"
            
            # Send entire explanation at once (it's cached)
            if cached.explanation:
                yield f"data: {json.dumps({'type': 'explanation', 'data': cached.explanation})}\n\n"
            
            yield f"data: {json.dumps({'type': 'done', 'cached': True})}\n\n"
        
        return StreamingResponse(
            generate_cached(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
        )
    
    def generate():
        explanation_buffer = []  # Collect tokens to cache later
        
        try:
            # Step 1: Route the query
            routing = pipeline.router.route(query)
            
            # Step 2 & 3: Compute and retrieve (parallel via pipeline's executor)
            compute_future = pipeline.executor.submit(pipeline.compute_engine.compute, routing)
            rag_future = pipeline.executor.submit(pipeline.rag.retrieve, routing, 5)
            
            compute_result = compute_future.result()
            retrieved_chunks = rag_future.result()
            
            citations = [f"[{c.chunk_id}] {c.category}" for c in retrieved_chunks if c.relevance_score > 0.5]
            
            # Send the answer immediately
            answer_data = {
                "type": "answer",
                "data": {
                    "success": compute_result.success,
                    "query": query,
                    "operation": routing.operation,
                    "answer": compute_result.result,
                    "latex_answer": compute_result.latex_result,
                    "assumptions": routing.assumptions,
                    "citations": citations
                }
            }
            yield f"data: {json.dumps(answer_data)}\n\n"
            
            if not compute_result.success:
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                return
            
            # Step 4: Stream the explanation
            explanation_context = ExplanationContext(
                original_query=query,
                routing_decision=routing,
                compute_result=compute_result,
                retrieved_chunks=retrieved_chunks
            )
            
            for token in pipeline.explainer.explain_stream(explanation_context):
                explanation_buffer.append(token)
                yield f"data: {json.dumps({'type': 'explanation', 'data': token})}\n\n"
            
            # Cache the complete response
            full_explanation = "".join(explanation_buffer)
            from core.models import MathResponse
            response_to_cache = MathResponse(
                success=True,
                query=query,
                operation=routing.operation,
                answer=compute_result.result,
                latex_answer=compute_result.latex_result,
                explanation=full_explanation,
                assumptions=routing.assumptions,
                citations=citations
            )
            pipeline._cache_response(query, response_to_cache)
            
            # Flush LangFuse traces
            try:
                Langfuse().flush()
            except Exception:
                pass
            
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.post("/solve/v1")
async def solve_v1(request: Request):
    """
    Legacy v1 endpoint for backwards compatibility.
    Redirects to the v2 pipeline.
    """
    try:
        body = await request.json()
        query = body.get("query", "").strip()
        
        if not query:
            return {"success": 0, "error": "Missing 'query' in request."}
        
        # Use v2 pipeline
        result = pipeline.process(query)
        
        # Return in v1 format
        return {
            "success": 1 if result.success else 0,
            "query": query,
            "result": result.answer if result.success else result.error
        }
        
    except Exception as e:
        return {"success": 0, "error": str(e)}


# Debug endpoint (only in development)
if os.environ.get("MATHAI_ENV") == "development":
    @app.post("/debug/route")
    async def debug_route(request: SolveRequest):
        """Debug endpoint to see routing decision."""
        if not pipeline:
            raise HTTPException(status_code=503, detail="Pipeline not initialized")
        
        routing = pipeline.router.route(request.query)
        return {
            "operation": routing.operation,
            "expression": routing.expression,
            "variable": routing.variable,
            "solve_for": routing.solve_for,
            "assumptions": routing.assumptions,
            "confidence": routing.confidence
        }
    
    @app.post("/debug/compute")
    async def debug_compute(request: SolveRequest):
        """Debug endpoint to see compute result."""
        if not pipeline:
            raise HTTPException(status_code=503, detail="Pipeline not initialized")
        
        routing = pipeline.router.route(request.query)
        result = pipeline.compute_engine.compute(routing)
        return {
            "routing": {
                "operation": routing.operation,
                "expression": routing.expression
            },
            "compute": {
                "success": result.success,
                "result": result.result,
                "latex_result": result.latex_result,
                "intermediate_steps": result.intermediate_steps,
                "error": result.error
            }
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        reload=os.environ.get("MATHAI_ENV") == "development"
    )
