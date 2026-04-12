import os
import json
import time
import uvicorn
from google import genai
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse

# Ensure these functions are in your tools.py
from tools import get_live_flights, filter_flights_by_country, get_aviation_incidents

app = FastAPI()

# =========================
# CONFIGURE GEMINI
# =========================
# Priority: 1. Environment Variable, 2. Hardcoded Fallback
API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyB4kZ4Z4jbMt5DDprbTe2uxNE1blXJSHf4")

client = genai.Client(api_key=API_KEY)

# =========================
# FALLBACK (NO-FAIL MODE)
# =========================
def fallback_summary(data, query):
    return f"""
### Aviation Intelligence Report (Fallback)

**Query:** {query}  
**Records Found:** {len(data)}

**Status:** Moderate  
**Risk:** Low  

**Note:** The AI is currently at capacity or the API key is restricted. 
Showing raw data count only.
"""

# =========================
# ROUTES
# =========================

@app.get("/")
def root():
    return RedirectResponse(url="/ui")

@app.get("/ui", response_class=HTMLResponse)
def ui():
    return """
    <html>
    <head>
        <title>Aviation Intelligence Agent</title>
        <style>
            body { font-family: 'Segoe UI', sans-serif; padding: 40px; background: #0b1120; color: #e2e8f0; margin: 0; }
            .container { max-width: 800px; margin: auto; background: #1e293b; padding: 30px; border-radius: 12px; border: 1px solid #334155; }
            h2 { color: #38bdf8; margin-top: 0; }
            .input-group { display: flex; gap: 10px; margin: 20px 0; }
            input { flex-grow: 1; padding: 12px; background: #0f172a; border: 1px solid #334155; border-radius: 8px; color: white; outline: none; }
            button { padding: 12px 24px; background: #0284c7; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; }
            #output { margin-top: 20px; padding: 20px; background: #0f172a; border-radius: 10px; border: 1px solid #1e293b; line-height: 1.6; min-height: 100px; }
            .tag { color: #38bdf8; font-size: 11px; text-transform: uppercase; display: block; margin-bottom: 10px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>✈️ Aviation Intelligence Command</h2>
            <div class="input-group">
                <input id="query" type="text" placeholder="e.g. Flight status in India" />
                <button onclick="sendQuery()">EXECUTE</button>
            </div>
            <div id="output">SYSTEM_READY...</div>
        </div>
        <script>
        async function sendQuery() {
            const q = document.getElementById("query").value;
            if (!q) return;
            const out = document.getElementById("output");
            out.innerHTML = "<b style='color: #38bdf8;'>UPLINKING...</b>";
            try {
                const res = await fetch(`/ask?query=${encodeURIComponent(q)}`);
                const data = await res.json();
                if (data.status === "success") {
                    out.innerHTML = `<span class="tag">SOURCE: ${data.tool_used}</span>${data.summary}`;
                } else {
                    out.innerHTML = `<b style="color: #ef4444;">ERROR:</b> ${data.error}`;
                }
            } catch (e) {
                out.innerHTML = "Connection Error.";
            }
        }
        </script>
    </body>
    </html>
    """

@app.get("/ask")
def ask(query: str):
    q_low = query.lower()
    tool_results = []
    tool_name = "general_flights"

    # 1. TOOL SELECTION
    try:
        if any(x in q_low for x in ["incident", "safety", "crash"]):
            tool_name = "get_aviation_incidents"
            raw = get_aviation_incidents()
            tool_results = raw.get("incidents", [])[:2]
        elif any(x in q_low for x in ["india", "usa", "uk", "iran"]):
            tool_name = "filter_flights_by_country"
            country = next((c for c in ["india", "usa", "uk", "iran"] if c in q_low), "india")
            raw = filter_flights_by_country(country)
            tool_results = raw.get("filtered_flights", [])[:3]
        else:
            tool_name = "get_live_flights"
            raw = get_live_flights()
            tool_results = raw.get("flights", [])[:3]
    except Exception as e:
        return {"status": "failed", "error": f"Tool error: {str(e)}"}

    # 2. AI CALL
    prompt = f"Analyze this aviation data for '{query}': {json.dumps(tool_results)}. Provide status, risk, and advice in Markdown."

    try:
        # 3-second sleep to respect Free Tier RPM limits
        time.sleep(3) 
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        summary = response.text
    except Exception as e:
        # Log the error to your terminal so you can see why it failed
        print(f"AI Error: {e}")
        summary = fallback_summary(tool_results, query)

    return {
        "query": query,
        "tool_used": tool_name,
        "summary": summary,
        "status": "success"
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)