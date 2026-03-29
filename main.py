from fastapi import FastAPI
import pandas as pd

app = FastAPI(title="Aviation MCP Server")

df = pd.read_csv("aviation_data.csv")

@app.get("/")
def home():
    return {"status": "running"}

@app.get("/get_incidents")
def get_incidents(cause: str = "", location: str = ""):
    data = df

    if cause:
        data = data[data['cause'].str.contains(cause, case=False)]

    if location:
        data = data[data['location'].str.contains(location, case=False)]

    return data.to_dict(orient="records")