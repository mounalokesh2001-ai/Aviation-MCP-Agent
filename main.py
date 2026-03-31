import os
from fastapi import FastAPI
import google.generativeai as genai
from tools import get_live_flights, filter_flights_by_country

app = FastAPI()

# Configure Gemini
genai.configure(api_key=os.getenv("AIzaSyA3T6kgvwjJE2ig1bWB-TdAL7b83LAZXl0"))
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

@app.get("/check-key")
def check_key():
    import os
    return {"key_loaded": os.getenv("GEMINI_API_KEY") is not None}


# Core AI Agent endpoint
@app.get("/ask")
def ask(query: str):

    prompt = f"""
    You are an aviation AI agent.

    Available tools:
    1. get_live_flights → for real-time flight data
    2. filter_flights_by_country → requires "country"

    User query: {query}

    Strictly return JSON:
    {{
      "tool": "tool_name",
      "arguments": {{
        "country": "value_if_needed"
      }}
    }}
    """

    response = model.generate_content(prompt)
    text = response.text.strip()

    import json

    try:
        decision = json.loads(text)

    except:
        # fallback (ensures demo never fails)
        decision = {
            "tool": "get_live_flights",
            "arguments": {}
        }

    tool_name = decision.get("tool")
    args = decision.get("arguments", {})

    if tool_name in TOOLS:
        result = TOOLS[tool_name](**args)

        # Trim data for clean screenshots
        trimmed_result = result
        if isinstance(result, dict) and "flights" in result:
            trimmed_result = {"flights": result["flights"][:3]}

        summary_prompt = f"""
        User asked: {query}

        Data: {trimmed_result}

        Give a short, clear insight in 2–3 lines.
        """

        final_response = model.generate_content(summary_prompt)

        return {
            "query": query,
            "tool_used": tool_name,
            "summary": final_response.text
        }

    return {"error": "Tool execution failed"}