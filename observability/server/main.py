from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import os
import json
import httpx

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Adjust path to point to the root logs directory
# Assuming server is in kairosity_bot_final/observability/server
# and logs are in kairosity_bot_final/logs
LOGS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../logs"))

@app.get("/runs")
async def get_runs():
    runs = []
    if not os.path.exists(LOGS_DIR):
        return []
    for run_id in sorted(os.listdir(LOGS_DIR), reverse=True):
        run_path = os.path.join(LOGS_DIR, run_id)
        if os.path.isdir(run_path):
            runs.append(run_id)
    return runs

@app.get("/runs/{run_id}/events")
async def get_run_events(run_id: str):
    events_path = os.path.join(LOGS_DIR, run_id, "events.jsonl")
    if not os.path.exists(events_path):
        raise HTTPException(status_code=404, detail="Events file not found")
    
    events = []
    with open(events_path, "r") as f:
        for line in f:
            try:
                events.append(json.loads(line))
            except:
                pass
    return events

@app.get("/proxy")
async def proxy(url: str):
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, headers=headers, follow_redirects=True)
            # Return raw HTML. Note: Relative links in the page will break.
            # This is a basic implementation.
            return HTMLResponse(content=resp.text, status_code=resp.status_code)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
