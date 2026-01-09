"""
Tests for the SymPy computation engine.
"""
import pytest
from core.compute import SymPyEngine
from core.models import RoutingDecision


@pytest.fixture
def engine():
    return SymPyEngine()


class TestDifferentiation:
    """Test differentiation operations."""
    
    def test_simple_polynomial(self, engine):
        routing = RoutingDecision(
            operation="differentiate",
            expression="x^2",
            variable="x"
        )
        result = engine.compute(routing)
        assert result.success
        assert "2*x" in result.result
    
    def test_chain_rule(self, engine):
        routing = RoutingDecision(
            operation="differentiate",
            expression="sin(x^2)",
            variable="x"
        )
        result = engine.compute(routing)
        assert result.success
        assert "cos" in result.result
        assert "2" in result.result
    
    def test_product_rule(self, engine):
        routing = RoutingDecision(
            operation="differentiate",
            expression="x * exp(x)",
            variable="x"
        )
        result = engine.compute(routing)
        assert result.success
        assert "exp" in result.result
    
    def test_natural_log(self, engine):
        routing = RoutingDecision(
            operation="differentiate",
            expression="ln(x)",
            variable="x"
        )
        result = engine.compute(routing)
        assert result.success
        assert "1/x" in result.result or "x**(-1)" in result.result


class TestIntegration:
    """Test integration operations."""
    
    def test_simple_polynomial(self, engine):
        routing = RoutingDecision(
            operation="integrate",
            expression="x^2",
            variable="x"
        )
        result = engine.compute(routing)
        assert result.success
        assert "x**3" in result.result
        assert "C" in result.result
    
    def test_exponential(self, engine):
        routing = RoutingDecision(
            operation="integrate",
            expression="exp(x)",
            variable="x"
        )
        result = engine.compute(routing)
        assert result.success
        assert "exp" in result.result
    
    def test_trig(self, engine):
        routing = RoutingDecision(
            operation="integrate",
            expression="cos(x)",
            variable="x"
        )
        result = engine.compute(routing)
        assert result.success
        assert "sin" in result.result


class TestSimplification:
    """Test simplification operations."""
    
    def test_algebraic(self, engine):
        routing = RoutingDecision(
            operation="simplify",
            expression="(x^2 - 1)/(x - 1)",
            variable="x"
        )
        result = engine.compute(routing)
        assert result.success
        assert "x + 1" in result.result
    
    def test_trig_identity(self, engine):
        routing = RoutingDecision(
            operation="simplify",
            expression="sin(x)^2 + cos(x)^2",
            variable="x"
        )
        result = engine.compute(routing)
        assert result.success
        assert result.result == "1"


class TestSolve:
    """Test solve operations."""
    
    def test_linear(self, engine):
        routing = RoutingDecision(
            operation="solve",
            expression="2*x + 4 = 0",
            variable="x",
            solve_for="x"
        )
        result = engine.compute(routing)
        assert result.success
        assert "-2" in result.result
    
    def test_quadratic(self, engine):
        routing = RoutingDecision(
            operation="solve",
            expression="x^2 - 4",
            variable="x",
            solve_for="x"
        )
        result = engine.compute(routing)
        assert result.success
        assert "2" in result.result
        assert "-2" in result.result


class TestErrorHandling:
    """Test error handling."""
    
    def test_invalid_expression(self, engine):
        routing = RoutingDecision(
            operation="differentiate",
            expression="not a valid expression @#$",
            variable="x"
        )
        result = engine.compute(routing)
        assert not result.success
        assert result.error is not None
        assert result.error_type == "parse_error"

