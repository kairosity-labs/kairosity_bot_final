from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import os
import json
import httpx
import asyncio
from pathlib import Path
import time

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

@app.websocket("/ws/runs/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str):
    await websocket.accept()
    events_path = Path(LOGS_DIR) / run_id / "events.jsonl"
    
    last_size = 0
    if events_path.exists():
        last_size = events_path.stat().st_size
    
    try:
        while True:
            await asyncio.sleep(1)
            if events_path.exists():
                current_size = events_path.stat().st_size
                if current_size > last_size:
                    with open(events_path, 'r') as f:
                        f.seek(last_size)
                        new_lines = f.readlines()
                    
                    for line in new_lines:
                        try:
                            event = json.loads(line)
                            await websocket.send_json({
                                "type": "new_event",
                                "event": event
                            })
                        except:
                            pass
                    
                    last_size = current_size
    except:
        pass

@app.get("/runs/{run_id}/status")
async def get_run_status(run_id: str):
    events_path = Path(LOGS_DIR) / run_id / "events.jsonl"
    if not events_path.exists():
        return {"status": "not_found"}
    
    last_modified = events_path.stat().st_mtime
    is_active = (time.time() - last_modified) < 10
    
    return {
        "status": "active" if is_active else "complete",
        "last_update": last_modified
    }

@app.get("/proxy")
async def proxy(url: str):
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, headers=headers, follow_redirects=True)
            return HTMLResponse(content=resp.text, status_code=resp.status_code)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
