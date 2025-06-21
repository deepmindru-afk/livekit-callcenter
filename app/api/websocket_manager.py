from fastapi.websockets import WebSocket
import json
from typing import Dict, List, Optional
from datetime import datetime


class ConnectionManager:
    def __init__(self):
        # Maps agent_id to their active WebSocket connection
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, agent_id: str):
        """Connect a new WebSocket for an agent."""
        print(f"[ConnectionManager] Accepting WebSocket for agent {agent_id}")
        await websocket.accept()
        print(
            f"[ConnectionManager] WebSocket accepted, storing connection for agent {agent_id}"
        )
        self.active_connections[agent_id] = websocket
        print(
            f"[ConnectionManager] Active connections after connect: {list(self.active_connections.keys())}"
        )

    def disconnect(self, agent_id: str):
        """Disconnect and remove a WebSocket connection."""
        if agent_id in self.active_connections:
            del self.active_connections[agent_id]

    async def send_personal_message(self, message: dict, agent_id: str):
        """Send a message to a specific agent."""
        print(f"[WebSocket] Attempting to send message to agent {agent_id}: {message}")
        print(f"[WebSocket] Active connections: {list(self.active_connections.keys())}")

        if agent_id in self.active_connections:
            try:
                await self.active_connections[agent_id].send_json(message)
                print(f"[WebSocket] Message sent successfully to agent {agent_id}")
            except Exception as e:
                print(f"[WebSocket] Error sending message to agent {agent_id}: {e}")
        else:
            print(f"[WebSocket] Agent {agent_id} not found in active connections")

    async def broadcast(self, message: dict, exclude: Optional[List[str]] = None):
        """Broadcast a message to all connected agents except those in exclude list."""
        exclude = exclude or []
        for agent_id, connection in self.active_connections.items():
            if agent_id not in exclude:
                await connection.send_json(message)

    async def broadcast_status_update(self, agent_id: str, status: str):
        """Broadcast an agent's status change to all other agents."""
        await self.broadcast(
            {"type": "status_update", "agent_id": agent_id, "status": status},
            exclude=[agent_id],  # Don't send back to the originating agent
        )

    async def send_incoming_call(self, agent_id: str, call_data: dict):
        """Send incoming call notification to an agent."""
        message = {
            "type": "incoming_call",
            "call_id": call_data.get("call_id"),
            "caller_id": call_data.get("caller_id"),
            "timestamp": call_data.get("timestamp"),
        }
        await self.send_personal_message(message, agent_id)

    async def send_call_ended(
        self, agent_id: str, call_id: str, reason: str = "remote_hangup"
    ):
        """Notify an agent that a call has ended."""
        message = {"type": "call_ended", "call_id": call_id, "reason": reason}
        await self.send_personal_message(message, agent_id)

    async def broadcast_room_update(self, room_data: Optional[dict] = None):
        """Broadcast room updates to all connected agents."""
        message = {
            "type": "room_update",
            "timestamp": str(datetime.now()),
        }

        # Add room data if provided
        if room_data:
            message["room"] = room_data

        await self.broadcast(message)

    async def notify_incoming_call(self, agent_id: str, call_data: dict):
        """For backward compatibility with existing code."""
        await self.send_incoming_call(agent_id, call_data)

    async def send_call_invitation(self, agent_id: str, invitation_data: dict):
        """Send call invitation to an agent for auto-assignment"""
        message = {
            "type": "call_invitation",
            "room_name": invitation_data.get("room_name"),
            "caller_id": invitation_data.get("caller_id"),
            "call_id": invitation_data.get("call_id"),
            "timestamp": invitation_data.get("timestamp"),
            "timeout": 30,  # 30 seconds to respond
        }
        await self.send_personal_message(message, agent_id)

    async def send_assignment_notification(self, agent_id: str, assignment_data: dict):
        """Send final assignment notification to agent"""
        message = {
            "type": "call_assigned",
            "room_name": assignment_data.get("room_name"),
            "call_id": assignment_data.get("call_id"),
            "agent_id": assignment_data.get("agent_id"),
        }
        await self.send_personal_message(message, agent_id)
