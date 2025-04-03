from tools.simplify import simplify_expression

def test_basic_simplification():
    result = simplify_expression("sin(x)**2 + cos(x)**2")
    assert result["success"] == 1
    assert result["simplified"] == "1"

if __name__ == "__main__":
    print(simplify_expression("sin(x)**2 + cos(x)**2"))
