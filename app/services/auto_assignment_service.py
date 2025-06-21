import asyncio
import uuid
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from livekit.api import ListRoomsRequest

from app.database.db import get_db
from app.models.models import Agent, Call, AgentStatus, CallDirection, CallStatus
from app.routers.calls import LiveKitService
from app.api.websocket_manager import ConnectionManager
from app.config import logger


class AutoAssignmentService:
    def __init__(self, connection_manager: ConnectionManager):
        self.manager = connection_manager
        self.monitored_rooms: Set[str] = set()
        self.pending_assignments: Dict[str, Dict] = {}
        self.assignment_timeouts: Dict[str, asyncio.Task] = {}
        self.is_monitoring = False

    async def start_monitoring(self, interval: int = 5):
        """Start monitoring for new inbound rooms"""
        if self.is_monitoring:
            return

        self.is_monitoring = True
        logger.info("Starting auto-assignment monitoring service")

        while self.is_monitoring:
            try:
                await self._check_for_new_inbound_rooms()
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"Error in auto-assignment monitoring: {str(e)}")
                await asyncio.sleep(interval)

    async def stop_monitoring(self):
        """Stop monitoring for new inbound rooms"""
        self.is_monitoring = False

        # Cancel all pending timeouts
        for timeout_task in self.assignment_timeouts.values():
            timeout_task.cancel()

        self.assignment_timeouts.clear()
        self.pending_assignments.clear()
        logger.info("Stopped auto-assignment monitoring service")

    async def _check_for_new_inbound_rooms(self):
        """Check for new inbound rooms and initiate assignment process"""
        try:
            async with LiveKitService.get_client() as livekit_api:
                response = await livekit_api.room.list_rooms(ListRoomsRequest())

                current_rooms = set()
                if hasattr(response, "rooms"):
                    for room in response.rooms:
                        room_name = room.name
                        current_rooms.add(room_name)

                        # Check if it's an inbound room we haven't seen before
                        if (
                            room_name.startswith("inbound-")
                            and room_name not in self.monitored_rooms
                            and room_name not in self.pending_assignments
                        ):

                            logger.info(f"New inbound room detected: {room_name}")
                            await self._initiate_assignment(room_name)

                # Update monitored rooms
                self.monitored_rooms = current_rooms

        except Exception as e:
            logger.error(f"Error checking for new inbound rooms: {str(e)}")

    async def _initiate_assignment(self, room_name: str):
        """Initiate the assignment process for a new inbound room"""
        try:
            # Extract caller information from room name if possible
            caller_id = self._extract_caller_id(room_name)

            # Get available agents
            db = next(get_db())
            available_agents = self._get_available_agents(db)

            if not available_agents:
                logger.warning(f"No available agents for inbound room: {room_name}")
                return

            # Create pending assignment record
            assignment_data = {
                "room_name": room_name,
                "caller_id": caller_id,
                "available_agents": [agent.id for agent in available_agents],
                "current_agent_index": 0,
                "created_at": datetime.utcnow(),
                "db_call_id": None,
            }

            self.pending_assignments[room_name] = assignment_data

            # Start assignment process with first available agent
            await self._assign_to_next_agent(room_name)

        except Exception as e:
            logger.error(f"Error initiating assignment for room {room_name}: {str(e)}")

    async def _assign_to_next_agent(self, room_name: str):
        """Assign the call to the next available agent"""
        if room_name not in self.pending_assignments:
            return

        assignment = self.pending_assignments[room_name]
        available_agents = assignment["available_agents"]
        current_index = assignment["current_agent_index"]

        if current_index >= len(available_agents):
            logger.warning(f"No more available agents for room {room_name}")
            await self._handle_no_agents_available(room_name)
            return

        agent_id = available_agents[current_index]

        try:
            # Get fresh agent data
            db = next(get_db())
            agent = db.query(Agent).filter(Agent.id == agent_id).first()

            if not agent or agent.status != AgentStatus.AVAILABLE.value:
                # Agent no longer available, try next one
                assignment["current_agent_index"] += 1
                await self._assign_to_next_agent(room_name)
                return

            # Create call record if not exists
            if not assignment.get("db_call_id"):
                db_call = Call(
                    agent_id=agent.id,
                    caller_id=assignment["caller_id"],
                    direction=CallDirection.INBOUND,
                    start_time=datetime.utcnow(),
                    status=CallStatus.IN_PROGRESS,
                    livekit_room_name=room_name,
                )
                db.add(db_call)
                db.commit()
                db.refresh(db_call)
                assignment["db_call_id"] = db_call.id
            else:
                # Update existing call record with new agent
                db_call = (
                    db.query(Call).filter(Call.id == assignment["db_call_id"]).first()
                )
                if db_call:
                    db_call.agent_id = agent.id
                    db.commit()

            # Send call invitation to agent
            invitation_data = {
                "room_name": room_name,
                "caller_id": assignment["caller_id"],
                "call_id": assignment["db_call_id"],
                "timestamp": datetime.utcnow().isoformat(),
            }

            await self.manager.send_call_invitation(str(agent.id), invitation_data)

            logger.info(
                f"Sent invitation to agent {agent.id} via WebSocket for room {room_name}"
            )
            print(
                f"[AutoAssignment] Sent invitation to agent {agent.id} for room {room_name}"
            )

            # Set timeout for agent response (30 seconds)
            timeout_task = asyncio.create_task(
                self._handle_invitation_timeout(room_name, agent_id)
            )
            self.assignment_timeouts[f"{room_name}_{agent_id}"] = timeout_task

            logger.info(
                f"Call invitation sent to agent {agent_id} for room {room_name}"
            )

        except Exception as e:
            logger.error(
                f"Error assigning to agent {agent_id} for room {room_name}: {str(e)}"
            )
            assignment["current_agent_index"] += 1
            await self._assign_to_next_agent(room_name)

    async def _handle_invitation_timeout(
        self, room_name: str, agent_id: int, timeout: int = 30
    ):
        """Handle invitation timeout and move to next agent"""
        await asyncio.sleep(timeout)

        if room_name in self.pending_assignments:
            logger.info(f"Invitation timeout for agent {agent_id}, room {room_name}")
            await self.handle_invitation_response(room_name, agent_id, False, "timeout")

    async def handle_invitation_response(
        self, room_name: str, agent_id: int, accepted: bool, reason: str = ""
    ):
        """Handle agent's response to call invitation"""
        if room_name not in self.pending_assignments:
            return

        # Cancel timeout task
        timeout_key = f"{room_name}_{agent_id}"
        if timeout_key in self.assignment_timeouts:
            self.assignment_timeouts[timeout_key].cancel()
            del self.assignment_timeouts[timeout_key]

        assignment = self.pending_assignments[room_name]

        if accepted:
            logger.info(f"Agent {agent_id} accepted call for room {room_name}")
            await self._finalize_assignment(room_name, agent_id)
        else:
            logger.info(
                f"Agent {agent_id} rejected call for room {room_name}. Reason: {reason}"
            )
            # Move to next agent
            assignment["current_agent_index"] += 1
            await self._assign_to_next_agent(room_name)

    async def _finalize_assignment(self, room_name: str, agent_id: int):
        """Finalize the assignment and clean up"""
        try:
            assignment = self.pending_assignments[room_name]

            # Update agent status to busy
            db = next(get_db())
            agent = db.query(Agent).filter(Agent.id == agent_id).first()
            if agent:
                agent.status = AgentStatus.BUSY.value
                db.commit()

            # Send final assignment notification
            assignment_data = {
                "room_name": room_name,
                "call_id": assignment["db_call_id"],
                "agent_id": agent_id,
            }

            await self.manager.send_assignment_notification(
                str(agent_id), assignment_data
            )

            # Clean up
            del self.pending_assignments[room_name]

            logger.info(
                f"Call assignment finalized for agent {agent_id}, room {room_name}"
            )

        except Exception as e:
            logger.error(f"Error finalizing assignment for room {room_name}: {str(e)}")

    async def _handle_no_agents_available(self, room_name: str):
        """Handle case when no agents are available"""
        logger.warning(f"No agents available for room {room_name}, ending call")

        try:
            # End the LiveKit room
            await LiveKitService.end_call(room_name)

            # Update call status if exists
            if room_name in self.pending_assignments:
                assignment = self.pending_assignments[room_name]
                if assignment.get("db_call_id"):
                    db = next(get_db())
                    db_call = (
                        db.query(Call)
                        .filter(Call.id == assignment["db_call_id"])
                        .first()
                    )
                    if db_call:
                        db_call.status = CallStatus.REJECTED.value
                        db.commit()

                del self.pending_assignments[room_name]

        except Exception as e:
            logger.error(
                f"Error handling no agents available for room {room_name}: {str(e)}"
            )

    def _get_available_agents(self, db: Session) -> List[Agent]:
        """Get list of available agents"""
        return db.query(Agent).filter(Agent.status == AgentStatus.AVAILABLE.value).all()

    def _extract_caller_id(self, room_name: str) -> str:
        """Extract caller ID from room name if possible"""
        # Expected format: inbound-{caller_id}-{timestamp}
        try:
            parts = room_name.split("-")
            if len(parts) >= 2:
                return parts[1]
        except:
            pass
        return "Unknown"

    def get_pending_assignments(self) -> Dict[str, Dict]:
        """Get current pending assignments (for debugging/monitoring)"""
        return self.pending_assignments.copy()


# Global instance
auto_assignment_service = None


def get_auto_assignment_service(connection_manager=None) -> AutoAssignmentService:
    """Get the global auto-assignment service instance"""
    global auto_assignment_service
    if auto_assignment_service is None:
        if connection_manager is None:
            raise ValueError("ConnectionManager must be provided on first call")
        auto_assignment_service = AutoAssignmentService(connection_manager)
    return auto_assignment_service
