from fastapi import FastAPI
import google.generativeai as genai
from tools import get_live_flights, filter_flights_by_country

app = FastAPI()

# Configure Gemini
genai.configure(api_key="YOUR_GEMINI_API_KEY")

model = genai.GenerativeModel("gemini-1.5-flash")

# MCP-style tool registry
TOOLS = {
    "get_live_flights": get_live_flights,
    "filter_flights_by_country": filter_flights_by_country,
}

# Health check
@app.get("/")
def home():
    return {"status": "Aviation MCP Agent running"}


# Core AI Agent endpoint
@app.get("/ask")
def ask(query: str):

    prompt = f"""
    You are an aviation AI agent.

    Available tools:
    1. get_live_flights → for real-time flight data
    2. filter_flights_by_country → requires country name

    User query: {query}

    Step 1: Decide which tool to use
    Step 2: Respond ONLY in this JSON format:

    {{
      "tool": "tool_name",
      "arguments": {{}}
    }}
    """

    response = model.generate_content(prompt)
    text = response.text.strip()

    try:
        import json
        decision = json.loads(text)

        tool_name = decision.get("tool")
        args = decision.get("arguments", {})

        if tool_name in TOOLS:
            result = TOOLS[tool_name](**args)

            # Final summarization
            summary_prompt = f"""
            User query: {query}
            Tool result: {result}

            Summarize clearly for user.
            """

            final_response = model.generate_content(summary_prompt)

            return {
                "query": query,
                "tool_used": tool_name,
                "result": result,
                "summary": final_response.text
            }

        else:
            return {"error": "Invalid tool selected"}

    except Exception as e:
        return {
            "error": "Parsing or execution failed",
            "details": str(e),
            "raw_model_output": text
        }