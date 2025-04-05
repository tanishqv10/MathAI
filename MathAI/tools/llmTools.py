# tools/llm_math_tools.py

from langchain.agents import Tool
from langchain_core.language_models import BaseLanguageModel

def make_llm_math_tool(tool_name: str, instruction: str, llm: BaseLanguageModel) -> Tool:
    def tool_func(query: str) -> str:
        prompt = (
            f"You are a helpful and detailed math tutor.\n"
            f"{instruction}\n"
            f"Problem: {query}\n\n"
            f"Follow this output format exactly. Do NOT change the headings or order:\n\n"
            f"Result: <Final Answer>\n\n"
            f"Explanation:\n"
            f"1. <Step one>\n"
            f"2. <Step two>\n"
            f"..."
        )
        return llm.invoke(prompt)

    return Tool(
        name=tool_name,
        func=tool_func,
        description=instruction
    )
