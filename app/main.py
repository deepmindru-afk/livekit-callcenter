import uvicorn
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.websockets import WebSocket, WebSocketDisconnect
import os
from pathlib import Path

from app.database.db import engine, Base
from app.api.websocket_manager import ConnectionManager
from app.routers import auth, agents, calls
from app.config import LIVEKIT_WS_URL  # Import the LiveKit WebSocket URL

app = FastAPI(title="Call Center API")

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create database tables
Base.metadata.create_all(bind=engine)

# Mount static files
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")

# Templates
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

# Create WebSocket connection manager
manager = ConnectionManager()

# Include routers
app.include_router(auth.router, prefix="/api", tags=["Authentication"])
app.include_router(agents.router, prefix="/api", tags=["Agents"])
app.include_router(calls.router, prefix="/api", tags=["Calls"])

@app.get("/", response_class=HTMLResponse)
async def get_homepage(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "livekit_ws_url": LIVEKIT_WS_URL})

@app.get("/login", response_class=HTMLResponse)
async def get_login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/login.html", response_class=HTMLResponse)
async def get_login_page_html(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.websocket("/ws/{agent_id}")
async def websocket_endpoint(websocket: WebSocket, agent_id: str):
    await manager.connect(websocket, agent_id)
    try:
        while True:
            data = await websocket.receive_json()
            # Handle different message types as needed
            if data.get("type") == "status_update":
                # Process status update and broadcast to other agents if needed
                await manager.broadcast_status_update(agent_id, data.get("status"))
    except WebSocketDisconnect:
        manager.disconnect(agent_id)
        await manager.broadcast_status_update(agent_id, "Offline")

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True) 