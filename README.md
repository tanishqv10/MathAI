# MathAI 🧠

MathAI is a full-stack math tutor powered by GPT-4 and SymPy. 
It supports natural language queries like "Differentiate 3x^2 + 5x" and gives step-by-step explanations.

## Structure

- `MathAI/` - Python backend deployed to AWS Lambda via SAM
- `mathai-frontend/` - React-based frontend styled like ChatGPT

## Tech Stack

- 🧠 LangChain + OpenAI (GPT-4)
- ➗ SymPy for symbolic math
- ☁️ AWS Lambda + API Gateway
- 💻 React frontend

## Usage

```bash
cd MathAI/
sam build && sam deploy
