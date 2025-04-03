import re

def preprocess_expression(expr: str) -> str:
    expr = expr.replace("^", "**")  
    expr = re.sub(r"(\d)([a-zA-Z])", r"\1*\2", expr) 
    expr = re.sub(r"([a-zA-Z])\s+([a-zA-Z])", r"\1*\2", expr) 
    return expr.strip()