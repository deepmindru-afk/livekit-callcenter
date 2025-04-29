from fastapi.websockets import WebSocket
import json
from typing import Dict, List, Optional


class ConnectionManager:
    def __init__(self):
        # Maps agent_id to their active WebSocket connection
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, agent_id: str):
        """Connect a new WebSocket for an agent."""
        await websocket.accept()
        self.active_connections[agent_id] = websocket

    def disconnect(self, agent_id: str):
        """Disconnect and remove a WebSocket connection."""
        if agent_id in self.active_connections:
            del self.active_connections[agent_id]

    async def send_personal_message(self, message: dict, agent_id: str):
        """Send a message to a specific agent."""
        if agent_id in self.active_connections:
            await self.active_connections[agent_id].send_json(message)

    async def broadcast(self, message: dict, exclude: Optional[List[str]] = None):
        """Broadcast a message to all connected agents except those in exclude list."""
        exclude = exclude or []
        for agent_id, connection in self.active_connections.items():
            if agent_id not in exclude:
                await connection.send_json(message)

    async def broadcast_status_update(self, agent_id: str, status: str):
        """Broadcast an agent's status change to all other agents."""
        await self.broadcast(
            {
                "type": "status_update",
                "agent_id": agent_id,
                "status": status
            },
            exclude=[agent_id]  # Don't send back to the originating agent
        )

    async def send_incoming_call(self, agent_id: str, call_data: dict):
        """Send incoming call notification to an agent."""
        message = {
            "type": "incoming_call",
            "call_id": call_data.get("call_id"),
            "caller_id": call_data.get("caller_id"),
            "timestamp": call_data.get("timestamp")
        }
        await self.send_personal_message(message, agent_id)

    async def send_call_ended(self, agent_id: str, call_id: str, reason: str = "remote_hangup"):
        """Notify an agent that a call has ended."""
        message = {
            "type": "call_ended",
            "call_id": call_id,
            "reason": reason
        }
        await self.send_personal_message(message, agent_id) 