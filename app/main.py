import uvicorn
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.websockets import WebSocket, WebSocketDisconnect
import os
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from app.database.db import engine, Base
from app.api.websocket_manager import ConnectionManager
from app.routers import auth, agents, calls, auto_assignment
from app.config import LIVEKIT_WS_URL, logger  # Import logger as well

# Create WebSocket connection manager
manager = ConnectionManager()

# Initialize auto-assignment service with the connection manager
from app.services.auto_assignment_service import get_auto_assignment_service
auto_assignment_service = get_auto_assignment_service(manager)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown tasks"""
    # Startup
    logger.info("🚀 Starting LiveKit Call Center Application")
    
    # Start auto-assignment monitoring service
    try:
        logger.info("Starting auto-assignment monitoring service...")
        asyncio.create_task(auto_assignment_service.start_monitoring())
        logger.info("✅ Auto-assignment service started successfully")
    except Exception as e:
        logger.error(f"❌ Failed to start auto-assignment service: {str(e)}")
    
    yield
    
    # Shutdown
    logger.info("🔄 Shutting down LiveKit Call Center Application")
    
    # Stop auto-assignment monitoring service
    try:
        logger.info("Stopping auto-assignment monitoring service...")
        await auto_assignment_service.stop_monitoring()
        logger.info("✅ Auto-assignment service stopped successfully")
    except Exception as e:
        logger.error(f"❌ Failed to stop auto-assignment service: {str(e)}")
    
    logger.info("👋 Application shutdown complete")

app = FastAPI(title="Call Center API", lifespan=lifespan)

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
app.mount(
    "/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static"
)

# Templates
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

# Include routers
app.include_router(auth.router, prefix="/api", tags=["Authentication"])
app.include_router(agents.router, prefix="/api", tags=["Agents"])
app.include_router(calls.router, prefix="/api", tags=["Calls"])
app.include_router(auto_assignment.router, prefix="/api", tags=["Auto Assignment"])


@app.get("/", response_class=HTMLResponse)
async def get_homepage(request: Request):
    return templates.TemplateResponse(
        "index.html", {"request": request, "livekit_ws_url": LIVEKIT_WS_URL}
    )


@app.get("/login", response_class=HTMLResponse)
async def get_login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/login.html", response_class=HTMLResponse)
async def get_login_page_html(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/test-websocket", response_class=HTMLResponse)
async def get_websocket_test_page():
    with open("test_websocket_connection.html", "r") as f:
        return HTMLResponse(content=f.read())


@app.websocket("/ws/{agent_id}")
async def websocket_endpoint(websocket: WebSocket, agent_id: str):
    print(f"[WebSocket] New connection request from agent {agent_id}")
    await manager.connect(websocket, agent_id)
    print(f"[WebSocket] Agent {agent_id} connected successfully")
    print(
        f"[WebSocket] Active connections now: {list(manager.active_connections.keys())}"
    )
    try:
        while True:
            data = await websocket.receive_json()
            # Handle different message types as needed
            if data.get("type") == "status_update":
                # Process status update and broadcast to other agents if needed
                await manager.broadcast_status_update(agent_id, data.get("status"))
            elif data.get("type") == "call_invitation_response":
                # Handle response to call invitation for auto-assignment
                from app.services.auto_assignment_service import (
                    get_auto_assignment_service,
                )

                auto_service = get_auto_assignment_service()
                await auto_service.handle_invitation_response(
                    room_name=data.get("room_name"),
                    agent_id=int(agent_id),
                    accepted=data.get("accepted", False),
                    reason=data.get("reason", ""),
                )
    except WebSocketDisconnect:
        print(f"[WebSocket] Agent {agent_id} disconnected")
        manager.disconnect(agent_id)
        print(
            f"[WebSocket] Active connections now: {list(manager.active_connections.keys())}"
        )
        await manager.broadcast_status_update(agent_id, "Offline")

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
