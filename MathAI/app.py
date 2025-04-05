import os
import io
import re
import sys
import json
from openai import OpenAI
from chains.mathAgent import agent


client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def strip_ansi(text):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

def lambda_handler(event, context):
    try:
        body = json.loads(event["body"])
        query = body.get("query", "").strip()

        if not query:
            return {
                "statusCode": 400,
                "body": json.dumps({"success": 0, "error": "Missing 'query' in request."})
            }
        
        buffer = io.StringIO()
        sys_stdout = sys.stdout
        sys.stdout = buffer
        
        result = agent.invoke(query)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "success": 1,
                "query": query,
                "result": result
            })
        }

    except Exception as e:
        sys.stdout = sys.__stdout__  # Ensure stdout is restored on error
        return {
            "statusCode": 500,
            "body": json.dumps({"success": 0, "error": str(e)})
        }

