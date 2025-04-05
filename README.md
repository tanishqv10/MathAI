# MathAI - Symbolic Math Solver using SymPy & LangChain

MathAI is a lightweight symbolic math engine built using Python, SymPy, and LangChain. It supports natural-language and LaTeX-style inputs to perform:

- Derivatives
- Integrals
- Simplification
- Equation Solving

All computations include step-by-step outputs.

---

## Features

- Implicit multiplication parsing (e.g., `2x`, `sin x y`)
- Smart handling of powers like `sin^2 x` or `cos^3(x)`
- LangChain Agent powered by OpenAI for tool routing
- AWS Lambda-ready backend
- Preprocessing powered by SymPy's `parse_expr`

---

## Folder Structure

```bash
.
├── app.py                     # AWS Lambda handler and API entrypoint
├── chains/
│   └── mathAgent.py          # LangChain agent with OpenAI-powered tools
├── tools/
│   └── llmTools.py           # Utility to create LangChain tools using LLM
├── utils/
│   └── preprocess.py         # SymPy-powered preprocessing for parsing math input
```
  
---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/tanishqv10/MathAI.git
cd MathAI

```

### 2. Install requirements

```bash
pip install -r requirements.txt
```
---

## Deployment
You can deploy the backend as an AWS Lambda using app.py and connect it to a React frontend or LangChain chatbot.

```bash
sam build
sam deploy --guided
```
Enter your OpenAI key when prompted to enter

---

## Frontend

Create a .env.local file and store NEXT_PUBLIC_API_URL here.

```bash
cd mathai-frontend
npm run dev
```

## Agent Workflow (LangChain)

### 1. Query sent to LangChain agent (mathAgent.py)

### 2. Agent routes to appropriate LLM tool (e.g., Derivative, Integral)

### 3. Tool invokes OpenAI with a structured math tutoring prompt

### 4. Response is formatted with:

```bash

Result: <Final Answer>

Explanation:
1. Step one...
2. Step two...
```

## Acknowledgements

LangChain

AWS SAM

OpenAI
