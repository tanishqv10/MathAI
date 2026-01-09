"""
LangFuse Instrumentation Module.

Provides end-to-end tracing with spans for:
- Routing
- Symbolic execution
- Retrieval
- LLM explanation generation

Logs prompt versions, token usage, latency, retrieved chunk IDs, and outputs.
"""
import os
from typing import Optional, Callable, Any
from functools import wraps
from contextlib import contextmanager
import time

# Try to import langfuse
try:
    from langfuse import Langfuse, observe, get_client
    LANGFUSE_AVAILABLE = True
    
    def update_current_span(**kwargs):
        """Helper to update current span with new langfuse API."""
        try:
            get_client().update_current_span(**kwargs)
        except Exception:
            pass
            
except ImportError:
    LANGFUSE_AVAILABLE = False
    
    # Create no-op decorators if langfuse not available
    def observe(*args, **kwargs):
        def decorator(func):
            return func
        if len(args) == 1 and callable(args[0]):
            return args[0]
        return decorator
    
    def update_current_span(**kwargs):
        """No-op when langfuse not available."""
        pass


class MathAIInstrumentation:
    """
    Centralized instrumentation for MathAI v2.
    Handles LangFuse configuration and provides tracing utilities.
    """
    
    # Prompt versions for tracking
    PROMPT_VERSIONS = {
        "router": "v2.0.0",
        "explainer": "v2.0.0"
    }
    
    def __init__(self):
        self.enabled = False
        self.langfuse = None
        
        if LANGFUSE_AVAILABLE:
            self._try_init_langfuse()
    
    def _try_init_langfuse(self):
        """Try to initialize LangFuse with environment variables."""
        required_vars = ["LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"]
        optional_host = "LANGFUSE_HOST"
        
        if all(os.environ.get(var) for var in required_vars):
            try:
                self.langfuse = Langfuse(
                    public_key=os.environ.get("LANGFUSE_PUBLIC_KEY"),
                    secret_key=os.environ.get("LANGFUSE_SECRET_KEY"),
                    host=os.environ.get(optional_host, "https://cloud.langfuse.com")
                )
                self.enabled = True
                print("LangFuse instrumentation enabled")
            except Exception as e:
                print(f"Warning: LangFuse initialization failed: {e}")
                self.enabled = False
        else:
            print("LangFuse not configured (missing environment variables)")
    
    @contextmanager
    def trace(self, name: str, **metadata):
        """
        Context manager for creating a trace span.
        
        Usage:
            with instrumentation.trace("my_operation", user_id="123"):
                # Your code here
                pass
        """
        start_time = time.perf_counter()
        
        if self.enabled and self.langfuse:
            trace = self.langfuse.trace(
                name=name,
                metadata=metadata
            )
            try:
                yield trace
            finally:
                latency_ms = (time.perf_counter() - start_time) * 1000
                trace.update(metadata={"latency_ms": latency_ms, **metadata})
        else:
            yield None
    
    @contextmanager
    def span(self, name: str, parent_trace=None, **metadata):
        """
        Context manager for creating a span within a trace.
        """
        start_time = time.perf_counter()
        
        if self.enabled and parent_trace:
            span = parent_trace.span(
                name=name,
                metadata=metadata
            )
            try:
                yield span
            finally:
                latency_ms = (time.perf_counter() - start_time) * 1000
                span.end(metadata={"latency_ms": latency_ms, **metadata})
        else:
            yield None
    
    def log_routing(
        self,
        query: str,
        operation: str,
        expression: str,
        variable: str,
        confidence: float,
        latency_ms: float
    ):
        """Log a routing decision."""
        if self.enabled and self.langfuse:
            self.langfuse.event(
                name="routing_decision",
                metadata={
                    "query": query,
                    "operation": operation,
                    "expression": expression,
                    "variable": variable,
                    "confidence": confidence,
                    "latency_ms": latency_ms,
                    "prompt_version": self.PROMPT_VERSIONS["router"]
                }
            )
    
    def log_computation(
        self,
        operation: str,
        expression: str,
        success: bool,
        result: Optional[str],
        error: Optional[str],
        latency_ms: float
    ):
        """Log a symbolic computation."""
        if self.enabled and self.langfuse:
            self.langfuse.event(
                name="symbolic_computation",
                metadata={
                    "operation": operation,
                    "expression": expression,
                    "success": success,
                    "result": result,
                    "error": error,
                    "latency_ms": latency_ms
                }
            )
    
    def log_retrieval(
        self,
        query: str,
        operation: str,
        chunk_ids: list,
        chunk_scores: list,
        latency_ms: float
    ):
        """Log a RAG retrieval."""
        if self.enabled and self.langfuse:
            self.langfuse.event(
                name="rag_retrieval",
                metadata={
                    "query": query,
                    "operation": operation,
                    "chunk_ids": chunk_ids,
                    "chunk_scores": chunk_scores,
                    "num_chunks": len(chunk_ids),
                    "latency_ms": latency_ms
                }
            )
    
    def log_explanation(
        self,
        operation: str,
        model: str,
        token_usage: Optional[dict],
        latency_ms: float
    ):
        """Log an LLM explanation generation."""
        if self.enabled and self.langfuse:
            self.langfuse.event(
                name="explanation_generation",
                metadata={
                    "operation": operation,
                    "model": model,
                    "token_usage": token_usage,
                    "latency_ms": latency_ms,
                    "prompt_version": self.PROMPT_VERSIONS["explainer"]
                }
            )
    
    def log_request(
        self,
        query: str,
        success: bool,
        operation: str,
        total_latency_ms: float,
        error: Optional[str] = None
    ):
        """Log a complete request."""
        if self.enabled and self.langfuse:
            self.langfuse.event(
                name="request_complete",
                level="DEFAULT" if success else "ERROR",
                metadata={
                    "query": query,
                    "success": success,
                    "operation": operation,
                    "total_latency_ms": total_latency_ms,
                    "error": error
                }
            )
    
    def flush(self):
        """Flush any pending events to LangFuse."""
        if self.enabled and self.langfuse:
            self.langfuse.flush()


# Global instrumentation instance
instrumentation = MathAIInstrumentation()


def traced(name: Optional[str] = None, capture_input: bool = True, capture_output: bool = True):
    """
    Decorator for tracing function calls.
    
    Usage:
        @traced("my_function")
        def my_function(x):
            return x * 2
    """
    def decorator(func: Callable) -> Callable:
        trace_name = name or func.__name__
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            
            if instrumentation.enabled:
                update_current_span(
                    name=trace_name,
                    input={"args": str(args), "kwargs": str(kwargs)} if capture_input else None
                )
            
            try:
                result = func(*args, **kwargs)
                
                if instrumentation.enabled and capture_output:
                    latency_ms = (time.perf_counter() - start_time) * 1000
                    update_current_span(
                        output=str(result)[:500] if result else None,
                        metadata={"latency_ms": latency_ms}
                    )
                
                return result
                
            except Exception as e:
                if instrumentation.enabled:
                    update_current_span(
                        level="ERROR",
                        metadata={"error": str(e)}
                    )
                raise
        
        return wrapper
    
    return decorator

