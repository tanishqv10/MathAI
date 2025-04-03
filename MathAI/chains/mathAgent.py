from langchain.agents import initialize_agent, Tool
from langchain.agents.agent_types import AgentType
from langchain_community.llms import OpenAI
from tools.simplify import simplify_expression
from tools.solve import solve_equation
from tools.derivative import differentiate_expression
from tools.integral import integrate_expression

llm = OpenAI(temperature=0)

tools = [
    Tool(
        name="DifferentiateTool",
        func=differentiate_expression,
        description="Use this to compute derivatives. Show the derivative of each term step-by-step using proper rules."
    ),
    Tool(
        name="IntegrateTool",
        func=integrate_expression,
        description="Use this to compute integrals. Show how each term is integrated and mention the rule used."
    ),
    Tool(
        name="SimplifyTool",
        func=simplify_expression,
        description="Use this to simplify expressions. Return the simplified form along with steps if possible."
    ),
    Tool(
        name="SolveTool",
        func=solve_equation,
        description="Use this to solve algebraic equations. Provide the input and final solutions."
    )
]

agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)
