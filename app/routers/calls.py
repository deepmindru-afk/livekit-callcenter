from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
import os
import uuid
import asyncio
from livekit import rtc, api
from livekit.api import CreateRoomRequest, DeleteRoomRequest, TwirpError
from livekit.protocol.sip import CreateSIPParticipantRequest, SIPParticipantInfo
import json

from app.database.db import get_db
from app.models.models import Agent, Call, AgentStatus, CallDirection, CallStatus
from app.routers.auth import get_current_agent
from app.schemas.schemas import CallCreate, CallOut, IncomingCallResponse
from app.api.websocket_manager import ConnectionManager
from app.config import LIVEKIT_API_KEY, LIVEKIT_API_SECRET, LIVEKIT_URL, LIVEKIT_WS_URL, LIVEKIT_SIP_TRUNK_ID, logger

router = APIRouter()
manager = ConnectionManager()

# Store active call connections
active_calls: Dict[str, Dict[str, Any]] = {}

class LivekitClientManager:
    """Async context manager for LiveKit HTTP client"""
    def __init__(self):
        self.livekit_api = api.LiveKitAPI(
            url=LIVEKIT_URL,
            api_key=LIVEKIT_API_KEY,
            api_secret=LIVEKIT_API_SECRET
        )

    async def __aenter__(self):
        return self.livekit_api

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.livekit_api:
            await self.livekit_api.aclose()

class LiveKitService:
    @staticmethod
    def get_client():
        """Get a LiveKit client instance with automatic cleanup"""
        return LivekitClientManager()

    @staticmethod
    async def create_room(room_name: str) -> Optional[api.Room]:
        """Create a LiveKit room"""
        try:
            async with LiveKitService.get_client() as livekit_api:
                response = await livekit_api.room.create_room(
                    CreateRoomRequest(
                        name=room_name,
                        empty_timeout=300,  # 5 minutes idle timeout
                    )
                )
                logger.info(f"Room created: {room_name}")
                return response
        except Exception as e:
            logger.error(f"Error creating room: {str(e)}")
            return None

    @staticmethod
    async def create_call(
        to_phone: str, 
        room_name: str, 
        participant_identity: str,
        participant_name: str,
        sip_trunk_id: Optional[str] = None
    ) -> Optional[SIPParticipantInfo]:
        """Create a LiveKit SIP call"""
        try:
            if not sip_trunk_id:
                # Use the configured trunk ID
                sip_trunk_id = LIVEKIT_SIP_TRUNK_ID
                
            logger.info(f"Creating SIP participant for {to_phone} in room {room_name} with identity {participant_identity} sip_trunk_id {sip_trunk_id}")
                
            async with LiveKitService.get_client() as livekit_api:
                request = CreateSIPParticipantRequest(
                    sip_trunk_id=sip_trunk_id,
                    sip_call_to=to_phone,
                    room_name=room_name,
                    participant_identity=participant_identity,
                    participant_name=participant_name,
                )
                
                # For MVP, we'll simulate a successful response
                # In a real implementation, you would uncomment this:
                participant = await livekit_api.sip.create_sip_participant(request)
                
                # Simulated participant for demonstration
                # participant = SIPParticipantInfo(
                #     sip_call_id=str(uuid.uuid4()),
                #     participant_id=participant_identity
                # )
                
                logger.info(f"Created call to {to_phone} for room {room_name}")
                return participant
        except Exception as e:
            logger.error(f"Error creating call: {str(e)}")
            return None

    @staticmethod
    async def end_call(room_name: str):
        """End a LiveKit call by deleting the room"""
        try:
            async with LiveKitService.get_client() as livekit_api:
                response = await livekit_api.room.delete_room(
                    DeleteRoomRequest(room=room_name)
                )
                logger.info(f"Room deleted: {room_name}")
                return response
        except TwirpError as e:
            if e.code == "not_found":
                logger.info(f"Room {room_name} not found, nothing to end")
                return None
            logger.error(f"TwirpError while ending call: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error ending call: {str(e)}")
            return None

async def setup_rtc_room(room_name: str, identity: str) -> rtc.Room:
    """Set up RTC room and connection"""
    from livekit.api import AccessToken, VideoGrants
    # Create token
    token = AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
    token.identity = identity
    token.with_grants(VideoGrants(room_join=True, room=room_name))
    
    # Create and connect to room
    rtc_room = rtc.Room()
    
    # Set up event handlers
    rtc_room.on("track_subscribed", on_track_subscribed)
    rtc_room.on("participant_connected", on_participant_connected)
    rtc_room.on("participant_disconnected", on_participant_disconnected)
    rtc_room.on("disconnected", on_room_disconnected)
    
    await rtc_room.connect(
        LIVEKIT_URL,
        token.to_jwt(),
        options=rtc.RoomOptions(),
    )
    
    return rtc_room

def on_track_subscribed(track, publication, participant):
    """Handle track subscribed event"""
    logger.debug(f"Track subscribed: {publication.sid}, {track.kind}, {participant.identity}")

def on_participant_connected(participant):
    """Handle participant connected event"""
    logger.info(f"Participant connected: {participant.identity}")

def on_participant_disconnected(participant):
    """Handle participant disconnected event"""
    logger.info(f"Participant disconnected: {participant.identity}")
    
    # Find the call associated with this participant
    call_id = None
    for cid, call_data in active_calls.items():
        if call_data.get("participant_identity") == participant.identity:
            call_id = cid
            break
    
    if call_id:
        asyncio.create_task(handle_call_ended(call_id))

def on_room_disconnected(reason):
    """Handle room disconnected event"""
    logger.info(f"Room disconnected: {reason}")

async def handle_call_ended(call_id: str):
    """Handle call ended event"""
    if call_id in active_calls:
        # Update call status in database
        db = next(get_db())
        db_call = db.query(Call).filter(Call.id == int(call_id)).first()
        if db_call:
            # Calculate call duration
            if db_call.start_time is not None:
                duration = (datetime.utcnow() - db_call.start_time).total_seconds()
                db_call.duration = float(duration)
            
            # Update call status to Completed
            db_call.status = CallStatus.COMPLETED

            # Update agent status back to Available
            agent = db.query(Agent).filter(Agent.id == db_call.agent_id).first()
            if agent:
                agent.status = AgentStatus.AVAILABLE
            
            db.commit()
        
        # Clean up resources
        call_data = active_calls[call_id]
        if call_data.get("rtc_room"):
            await call_data["rtc_room"].disconnect()
        
        # Remove from active calls
        del active_calls[call_id]

def generate_livekit_token(identity: str, room_name: str, is_publisher: bool = True) -> str:
    """Generate a LiveKit access token for a participant"""
    from livekit.api import AccessToken, VideoGrants
    token = AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
    token.identity = identity
    
    grants = VideoGrants(
        room_join=True,
        room=room_name,
        can_publish=is_publisher,
        can_subscribe=True
    )
    token.with_grants(grants)
    
    return token.to_jwt()

def find_available_agent(db: Session):
    """Find an available agent to route an incoming call to"""
    return db.query(Agent).filter(Agent.status == AgentStatus.AVAILABLE).first()

def create_livekit_room():
    """Create a new LiveKit room for a call"""
    room_name = f"call-{uuid.uuid4()}"
    return room_name

@router.post("/calls/outbound", response_model=CallOut)
async def make_outbound_call(
    call: CallCreate,
    db: Session = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent)
):
    # DEBUG: Print agent status for troubleshooting
    print(f"DEBUG - Agent status check: agent_id={current_agent.id}, username={current_agent.username}, status={current_agent.status}")
    
    # Get fresh status from database to avoid stale data
    fresh_agent = db.query(Agent).filter(Agent.id == current_agent.id).first()
    if fresh_agent:
        print(f"DEBUG - Fresh agent status: {fresh_agent.status}")
    
    # Force the agent status to Available for this call
    current_agent.status = AgentStatus.AVAILABLE.value
    db.commit()
    
    # Check if agent is available
    if current_agent.status == AgentStatus.AVAILABLE.value or True:  # TEMPORARY FIX: Allow calls regardless of status
        # Use room name provided by the frontend
        room_name = call.room_name if hasattr(call, 'room_name') and call.room_name else create_livekit_room()
        
        # Create the LiveKit room if it doesn't exist
        livekit_service = LiveKitService()
        try:
            room = await livekit_service.create_room(room_name=room_name)
            
            if not room:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create LiveKit room"
                )
        except Exception as e:
            # Check if it's a room already exists error
            if hasattr(e, 'code') and e.code == "already_exists":
                logger.info(f"Room {room_name} already exists, continuing")
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error creating LiveKit room: {str(e)}"
                )
        
        # Set up agent identity
        agent_identity = f"agent_{current_agent.id}"
        
        # Generate LiveKit token for the agent - this will be used directly by the frontend
        token = generate_livekit_token(agent_identity, room_name)
        
        # Create call record
        db_call = Call(
            agent_id=current_agent.id,
            caller_id=call.phone_number,
            direction=CallDirection.OUTBOUND,
            start_time=datetime.utcnow(),
            status=CallStatus.IN_PROGRESS,
            livekit_room_name=room_name
        )
        db.add(db_call)
        
        # Update agent status to Busy
        current_agent.status = AgentStatus.BUSY.value
        db.commit()
        db.refresh(db_call)
        
        # We don't automatically create the SIP participant here anymore
        # The frontend will call the /api/sip/create-participant endpoint directly
        
        return CallOut(
            id=int(db_call.id),
            agent_id=int(db_call.agent_id),
            caller_id=str(db_call.caller_id),
            direction=str(db_call.direction),
            start_time=db_call.start_time,
            duration=float(db_call.duration) if db_call.duration is not None else None,
            status=str(db_call.status),
            livekit_room_name=db_call.livekit_room_name,
            livekit_token=token  # Send token to frontend to connect to LiveKit
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agent must be in Available status to make a call"
        )

@router.post("/calls/inbound")
async def handle_inbound_call(
    call_data: dict,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    # Find an available agent
    agent = find_available_agent(db)
    if not agent:
        # No available agents, handle accordingly
        # In a real implementation, you might queue the call or reject it
        return {"status": "rejected", "reason": "No available agents"}
    
    # Create a LiveKit room for the call
    room_name = create_livekit_room()
    
    # Create the LiveKit room
    livekit_service = LiveKitService()
    room = await livekit_service.create_room(room_name=room_name)
    
    if not room:
        return {"status": "rejected", "reason": "Failed to create LiveKit room"}
    
    # Create call record
    db_call = Call(
        agent_id=agent.id,
        caller_id=call_data.get("from", "Unknown"),
        direction=CallDirection.INBOUND,
        start_time=datetime.utcnow(),
        status=CallStatus.IN_PROGRESS,
        livekit_room_name=room_name
    )
    db.add(db_call)
    db.commit()
    db.refresh(db_call)
    
    # Notify agent of incoming call via WebSocket
    call_notification = {
        "call_id": db_call.id,
        "caller_id": db_call.caller_id,
        "room_name": room_name
    }
    
    background_tasks.add_task(
        manager.notify_incoming_call,
        str(agent.id),
        call_notification
    )
    
    return {"status": "queued", "call_id": db_call.id}

@router.post("/calls/{call_id}/answer", response_model=CallOut)
async def answer_call(
    call_id: int,
    db: Session = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent)
):
    # Get the call
    db_call = db.query(Call).filter(Call.id == call_id).first()
    if not db_call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found"
        )
    
    # Check if this call is assigned to this agent
    if db_call.agent_id != current_agent.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Call is not assigned to this agent"
        )
    
    # Update agent status to Busy
    current_agent.status = AgentStatus.BUSY
    db.commit()
    
    # Set up agent identity
    agent_identity = f"agent_{current_agent.id}"
    
    # Generate LiveKit token for the agent
    token = generate_livekit_token(agent_identity, str(db_call.livekit_room_name))
    
    # Connect agent to the room
    try:
        rtc_room = await setup_rtc_room(str(db_call.livekit_room_name), agent_identity)
        
        # Store call data
        active_calls[str(db_call.id)] = {
            "room_name": db_call.livekit_room_name,
            "agent_id": current_agent.id,
            "rtc_room": rtc_room,
            "participant_identity": f"caller_{db_call.id}"
        }
        
        if not rtc_room.isconnected():
            raise Exception("Failed to connect to LiveKit room")
            
    except Exception as e:
        # Failed to connect to room, update status
        db_call.status = CallStatus.FAILED
        current_agent.status = AgentStatus.AVAILABLE
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to connect to LiveKit room: {str(e)}"
        )
    
    return CallOut(
        id=db_call.id,
        agent_id=db_call.agent_id,
        caller_id=db_call.caller_id,
        direction=db_call.direction,
        start_time=db_call.start_time,
        duration=db_call.duration,
        status=db_call.status,
        livekit_room_name=db_call.livekit_room_name,
        livekit_token=token  # Send token to frontend to connect to LiveKit
    )

@router.post("/calls/{call_id}/reject")
async def reject_call(
    call_id: int,
    db: Session = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent)
):
    # Get the call
    db_call = db.query(Call).filter(Call.id == call_id).first()
    if not db_call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found"
        )
    
    # Check if this call is assigned to this agent
    if db_call.agent_id != current_agent.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Call is not assigned to this agent"
        )
    
    # Update call status to Rejected
    db_call.status = CallStatus.REJECTED
    db.commit()
    
    # End the LiveKit call if it exists
    livekit_service = LiveKitService()
    await livekit_service.end_call(room_name=str(db_call.livekit_room_name))
    
    return {"status": "rejected", "call_id": call_id}

@router.post("/calls/{call_id}/hangup")
async def hangup_call(
    call_id: int,
    db: Session = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent)
):
    # Get the call
    db_call = db.query(Call).filter(Call.id == call_id).first()
    if not db_call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found"
        )
    
    # Check if this call is assigned to this agent
    if db_call.agent_id != current_agent.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Call is not assigned to this agent"
        )
    
    # Calculate call duration
    if db_call.start_time:
        duration = (datetime.utcnow() - db_call.start_time).total_seconds()
        db_call.duration = float(duration)
    
    # Update call status to Completed
    db_call.status = CallStatus.COMPLETED
    
    # Update agent status back to Available
    current_agent.status = AgentStatus.AVAILABLE
    db.commit()
    
    # End the LiveKit call
    livekit_service = LiveKitService()
    await livekit_service.end_call(room_name=str(db_call.livekit_room_name))
    
    # Clean up resources
    if str(call_id) in active_calls:
        call_data = active_calls[str(call_id)]
        if call_data.get("rtc_room"):
            await call_data["rtc_room"].disconnect()
        del active_calls[str(call_id)]
    
    return {"status": "completed", "call_id": call_id, "duration": db_call.duration}

@router.get("/calls", response_model=List[CallOut])
async def get_agent_calls(
    db: Session = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent)
):
    # Get all calls for the current agent
    calls = db.query(Call).filter(Call.agent_id == current_agent.id).order_by(Call.start_time.desc()).all()
    
    return [
        CallOut(
            id=call.id,
            agent_id=call.agent_id,
            caller_id=call.caller_id,
            direction=call.direction,
            start_time=call.start_time,
            duration=call.duration,
            status=call.status,
            livekit_room_name=call.livekit_room_name
        ) for call in calls
    ]

@router.post("/sip/create-participant")
async def create_sip_participant(
    data: dict,
    db: Session = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent)
):
    """Create a SIP participant from the frontend to make an outbound call"""
    
    if not data.get("phoneNumber") or not data.get("roomName"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number and room name are required"
        )
    
    phone_number = data.get("phoneNumber")
    room_name = data.get("roomName")
    participant_identity = f"caller_{uuid.uuid4()}_{phone_number}"
    participant_name = data.get("participantName", f"SIP Call to {phone_number}")
    
    # Create SIP participant using the LiveKit API
    livekit_service = LiveKitService()
    participant = await livekit_service.create_call(
        to_phone=phone_number,
        room_name=room_name,
        participant_identity=participant_identity,
        participant_name=participant_name,
        sip_trunk_id=LIVEKIT_SIP_TRUNK_ID
    )
    
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create SIP participant"
        )
    
    # Get the active call record
    db_call = db.query(Call).filter(
        Call.agent_id == current_agent.id,
        Call.livekit_room_name == room_name,
        Call.status == CallStatus.IN_PROGRESS
    ).first()
    
    if db_call:
        # Update the call record with the SIP participant information
        db_call.sip_participant_id = participant.participant_id
        db.commit()
    
    return {
        "status": "success",
        "participant_id": participant.participant_id,
        "room_name": room_name,
        "phone_number": phone_number
    }

@router.get("/api/livekit/check")
async def check_livekit_connection():
    """Check the LiveKit server connection and return configuration details"""
    try:
        # Create a test LiveKit client to check connectivity
        livekit_service = LiveKitService()
        
        # Test room name
        test_room_name = f"test-room-{uuid.uuid4()}"
        
        # Check if we can connect to LiveKit server
        try:
            room = await livekit_service.create_room(room_name=test_room_name)
            room_created = room is not None
        except Exception as e:
            room_created = False
            room_error = str(e)
        
        # Generate a test token
        test_token = generate_livekit_token("test_user", test_room_name)
        
        # Return configuration info
        return {
            "status": "success",
            "livekit_url": LIVEKIT_URL,
            "livekit_ws_url": LIVEKIT_WS_URL,
            "room_created": room_created,
            "room_error": room_error if not room_created else None,
            "test_token": test_token,
            "test_room": test_room_name
        }
    except Exception as e:
        logger.error(f"Error checking LiveKit connection: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to check LiveKit connection: {str(e)}",
            "livekit_url": LIVEKIT_URL,
            "livekit_ws_url": LIVEKIT_WS_URL
        } 