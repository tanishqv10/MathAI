import os
import io
import re
import sys
import json
from openai import OpenAI
from chains.mathAgent import agent
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS for frontend (Vercel)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def strip_ansi(text):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

@app.post("/solve")
async def handle_query(request: Request):
    try:
        body = await request.json()
        query = body.get("query", "").strip()
        print(f"Received query: {query}")

        if not query:
            return {"success": 0, "error": "Missing 'query' in request."}

        buffer = io.StringIO()
        sys_stdout = sys.stdout
        sys.stdout = buffer

        result = agent.invoke(query)

        sys.stdout = sys_stdout
        print(f"Agent result: {result}")

        return {
            "success": 1,
            "query": query,
            "result": result
        }

    except Exception as e:
        sys.stdout = sys.__stdout__
        print(f"Exception: {str(e)}")
        return {
            "success": 0,
            "error": str(e)
        }
