# mathAgent.py

from langchain.agents import initialize_agent, AgentType
from langchain_openai import ChatOpenAI
from tools.llmTools import make_llm_math_tool

llm = ChatOpenAI(model="gpt-4", temperature=0)

llm_tools = [
    make_llm_math_tool("LLMDerivativeTool", "Differentiate the expression", llm),
    make_llm_math_tool("LLMIntegrateTool", "Integrate the expression", llm),
    make_llm_math_tool("LLMSimplifyTool", "Simplify the expression", llm),
    make_llm_math_tool("LLMSolveTool", "Solve the algebraic or mathematical expressions and equations involving variables or numbers.", llm),
]

agent = initialize_agent(
    tools=llm_tools,
    llm=llm,
    agent=AgentType.OPENAI_FUNCTIONS,
    verbose=True
)
