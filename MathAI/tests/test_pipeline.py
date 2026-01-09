"""
Integration tests for the full MathAI v2 pipeline.
"""
import pytest
from unittest.mock import Mock, patch
from core.pipeline import MathPipeline
from core.models import RoutingDecision, ComputeResult


class TestPipelineIntegration:
    """Integration tests requiring API keys."""
    
    @pytest.fixture
    def mock_pipeline(self):
        """Create a pipeline with mocked LLM calls."""
        with patch('core.router.OpenAI') as mock_openai:
            with patch('core.explainer.OpenAI') as mock_explainer_openai:
                # Mock router response
                mock_response = Mock()
                mock_response.choices = [Mock()]
                mock_response.choices[0].message.content = '''
                {
                    "operation": "differentiate",
                    "expression": "x^2",
                    "variable": "x",
                    "solve_for": null,
                    "assumptions": [],
                    "confidence": 1.0
                }
                '''
                mock_openai.return_value.chat.completions.create.return_value = mock_response
                
                # Mock explainer response
                mock_explain = Mock()
                mock_explain.choices = [Mock()]
                mock_explain.choices[0].message.content = "Step 1: Apply power rule..."
                mock_explainer_openai.return_value.chat.completions.create.return_value = mock_explain
                
                pipeline = MathPipeline(langfuse_enabled=False)
                yield pipeline
    
    def test_differentiation_flow(self, mock_pipeline):
        """Test complete differentiation flow."""
        result = mock_pipeline.process("differentiate x^2")
        
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

