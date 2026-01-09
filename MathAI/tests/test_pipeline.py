"""
Integration tests for the full MathAI v2 pipeline.
"""
import os
import pytest
from unittest.mock import Mock, patch
from core.pipeline import MathPipeline
from core.models import RoutingDecision, ComputeResult


# Skip integration tests if no API key is set
requires_api_key = pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set - skipping integration tests"
)


class TestPipelineIntegration:
    """Integration tests requiring API keys."""
    
    @requires_api_key
    def test_differentiation_flow(self):
        """Test complete differentiation flow with real API."""
        pipeline = MathPipeline(langfuse_enabled=False)
        result = pipeline.process("differentiate x^2")
        
        assert result.success
        assert result.operation == "differentiate"
        assert "2*x" in result.answer
        assert result.explanation is not None


class TestComputeOnly:
    """Tests that only use the compute engine (no API calls)."""
    
    @pytest.fixture
    def engine(self):
        from core.compute import SymPyEngine
        return SymPyEngine()
    
    def test_various_derivatives(self, engine):
        test_cases = [
            ("x^3", "x", "3*x**2"),
            ("sin(x)", "x", "cos(x)"),
            ("exp(x)", "x", "exp(x)"),
            ("x*y", "x", "y"),
        ]
        
        for expr, var, expected_substr in test_cases:
            routing = RoutingDecision(
                operation="differentiate",
                expression=expr,
                variable=var
            )
            result = engine.compute(routing)
            assert result.success, f"Failed for {expr}"
            assert expected_substr in result.result.replace(" ", ""), f"Expected {expected_substr} in {result.result}"
    
    def test_various_integrals(self, engine):
        test_cases = [
            ("x", "x", "x**2/2"),
            ("sin(x)", "x", "cos"),
            ("1/x", "x", "log"),
        ]
        
        for expr, var, expected_substr in test_cases:
            routing = RoutingDecision(
                operation="integrate",
                expression=expr,
                variable=var
            )
            result = engine.compute(routing)
            assert result.success, f"Failed for {expr}"
            assert expected_substr in result.result, f"Expected {expected_substr} in {result.result}"
    
    def test_various_simplifications(self, engine):
        test_cases = [
            ("x + x", "2*x"),
            ("x*x", "x**2"),
            ("x/x", "1"),
        ]
        
        for expr, expected_substr in test_cases:
            routing = RoutingDecision(
                operation="simplify",
                expression=expr,
                variable="x"
            )
            result = engine.compute(routing)
            assert result.success, f"Failed for {expr}"
            assert expected_substr in result.result, f"Expected {expected_substr} in {result.result}"
    
    def test_various_solves(self, engine):
        test_cases = [
            ("x^2 - 4", "x", ["2", "-2"]),
            ("x + 5", "x", ["-5"]),
            ("x^2", "x", ["0"]),
        ]
        
        for expr, var, expected_substrs in test_cases:
            routing = RoutingDecision(
                operation="solve",
                expression=expr,
                variable=var,
                solve_for=var
            )
            result = engine.compute(routing)
            assert result.success, f"Failed for {expr}"
            for substr in expected_substrs:
                assert substr in result.result, f"Expected {substr} in {result.result}"

