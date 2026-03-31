import os
import json
import uvicorn
import google.generativeai as genai
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

# Ensure your tools.py is in the same directory and functions are defined
from tools import get_live_flights, filter_flights_by_country, get_aviation_incidents

app = FastAPI()

# =========================
# CONFIGURE GEMINI (2026)
# =========================

# Use environment variable for security; fallback is for local testing only
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyA3T6kgvwjJE2ig1bWB-TdAL7b83LAZXl0")
genai.configure(api_key=GEMINI_API_KEY)

# Gemini 3 Flash is the standard for high-speed agentic tasks in 2026
MODEL_NAME = "gemini-3-flash"
model = genai.GenerativeModel(MODEL_NAME)

# =========================
# SIMPLE WEB UI
# =========================

@app.get("/ui", response_class=HTMLResponse)
def ui():
    return """
    <html>
    <head><title>Aviation AI Agent</title></head>
    <body style="font-family: sans-serif; padding: 40px; background: #f4f7f6;">
        <div style="max-width: 700px; margin: auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <h2 style="color: #2c3e50;">✈️ Aviation Intelligence Agent</h2>
            <p style="color: #7f8c8d;">Query live flights, regional status, or safety incidents.</p>
            
            <input id="query" type="text" placeholder="e.g. Flight status in India" 
                   style="width: 80%; padding: 12px; border: 1px solid #ddd; border-radius: 8px;" />
            <button onclick="sendQuery()" style="padding: 12px 20px; background: #3498db; color: white; border: none; border-radius: 8px; cursor: pointer;">Ask</button>

            <div id="output" style="margin-top: 25px; padding: 15px; background: #ecf0f1; border-radius: 8px; min-height: 50px; line-height: 1.5;">
                System Ready...
            </div>
        </div>

        <script>
        async function sendQuery() {
            const q = document.getElementById("query").value;
            if (!q) return;
            const out = document.getElementById("output");
            out.innerHTML = "<b>Fetching aviation data...</b>";

            try {
                const res = await fetch(`/ask?query=${encodeURIComponent(q)}`);
                const data = await res.json();
                if (data.status === "success") {
                    out.innerHTML = `<small style="color:blue">Source: ${data.tool_used}</small><br><br>${data.summary}`;
                } else {
                    out.innerHTML = `<b style="color:red">Error:</b> ${data.error}`;
                }
            } catch (e) {
                out.innerHTML = "<b style='color:red'>Server Error. Check terminal.</b>";
            }
        }
        </script>
    </body>
    </html>
    """

# =========================
# CORE AI AGENT
# =========================

@app.get("/ask")
def ask(query: str):
    q_lower = query.lower()
    tool_results = {}
    tool_used = "get_live_flights"

    # --- STEP 1: KEYWORD SELECTION (Saves Quota) ---
    try:
        if any(x in q_lower for x in ["incident", "safety", "crash", "emergency", "accident"]):
            tool_used = "get_aviation_incidents"
            data = get_aviation_incidents()
            tool_results = data[:5] if isinstance(data, list) else data

        elif any(x in q_lower for x in ["india", "iran", "usa", "uk", "russia", "china", "germany"]):
            tool_used = "regional_multi_tool"
            countries = ["india", "iran", "usa", "uk", "russia", "china", "germany"]
            target = next((c for c in countries if c in q_lower), "global")
            
            tool_results = {
                "regional_flights": filter_flights_by_country(country=target)[:5],
                "global_context": get_live_flights()[:3],
                "local_incidents": get_aviation_incidents()[:2]
            }
        else:
            tool_used = "get_live_flights"
            tool_results = get_live_flights()[:8]

    except Exception as e:
        return {"status": "failed", "error": f"Tool error: {str(e)}"}

    # --- STEP 2: SUMMARY GENERATION (Single AI Call) ---
    summary_prompt = f"""
    Role: Aviation Intelligence Analyst.
    User Query: {query}
    Data: {json.dumps(tool_results)}

    Task: Provide a concise report on current flight density, risk level, and passenger advice. 
    Format: Markdown. Keep it technical but readable.
    """

    try:
        response = model.generate_content(summary_prompt)
        return {
            "query": query,
            "tool_used": tool_used,
            "summary": response.text,
            "status": "success"
        }
    except Exception as e:
        # Fallback if 429 Quota is hit
        return {
            "status": "success",
            "tool_used": tool_used,
            "query": query,
            "summary": f"<b>QUOTA NOTICE:</b> Data retrieved but AI summary failed. {len(str(tool_results))} bytes of data found. Try again in 60s."
        }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)