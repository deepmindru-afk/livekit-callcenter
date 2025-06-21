from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any
from pydantic import BaseModel

from app.database.db import get_db
from app.models.models import Agent
from app.routers.auth import get_current_agent
from app.services.auto_assignment_service import get_auto_assignment_service
from app.config import logger

router = APIRouter()

class CallInvitationResponse(BaseModel):
    room_name: str
    accepted: bool
    reason: str = ""

class AutoAssignmentStatus(BaseModel):
    is_monitoring: bool
    pending_assignments: Dict[str, Any]

@router.post("/auto-assignment/respond")
async def respond_to_call_invitation(
    response: CallInvitationResponse,
    db: Session = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent)
):
    """Handle agent's response to call invitation"""
    try:
        auto_service = get_auto_assignment_service()
        
        await auto_service.handle_invitation_response(
            room_name=response.room_name,
            agent_id=int(current_agent.id),
            accepted=response.accepted,
            reason=response.reason
        )
        
        return {
            "status": "success",
            "message": f"Response {'accepted' if response.accepted else 'rejected'} for room {response.room_name}"
        }
        
    except Exception as e:
        logger.error(f"Error handling invitation response: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process invitation response: {str(e)}"
        )

@router.post("/auto-assignment/start")
async def start_auto_assignment(
    current_agent: Agent = Depends(get_current_agent)
):
    """Start the auto-assignment monitoring service"""
    try:
        auto_service = get_auto_assignment_service()
        
        # Start monitoring in background
        import asyncio
        asyncio.create_task(auto_service.start_monitoring())
        
        return {
            "status": "success",
            "message": "Auto-assignment monitoring started"
        }
        
    except Exception as e:
        logger.error(f"Error starting auto-assignment: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start auto-assignment: {str(e)}"
        )

@router.post("/auto-assignment/stop")
async def stop_auto_assignment(
    current_agent: Agent = Depends(get_current_agent)
):
    """Stop the auto-assignment monitoring service"""
    try:
        auto_service = get_auto_assignment_service()
        await auto_service.stop_monitoring()
        
        return {
            "status": "success",
            "message": "Auto-assignment monitoring stopped"
        }
        
    except Exception as e:
        logger.error(f"Error stopping auto-assignment: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop auto-assignment: {str(e)}"
        )

@router.get("/auto-assignment/status", response_model=AutoAssignmentStatus)
async def get_auto_assignment_status(
    current_agent: Agent = Depends(get_current_agent)
):
    """Get current auto-assignment service status"""
    try:
        auto_service = get_auto_assignment_service()
        
        return AutoAssignmentStatus(
            is_monitoring=auto_service.is_monitoring,
            pending_assignments=auto_service.get_pending_assignments()
        )
        
    except Exception as e:
        logger.error(f"Error getting auto-assignment status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get auto-assignment status: {str(e)}"
        )

@router.get("/auto-assignment/pending")
async def get_pending_assignments(
    current_agent: Agent = Depends(get_current_agent)
):
    """Get current pending call assignments"""
    try:
        auto_service = get_auto_assignment_service()
        pending = auto_service.get_pending_assignments()
        
        return {
            "pending_assignments": pending,
            "count": len(pending)
        }
        
    except Exception as e:
        logger.error(f"Error getting pending assignments: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get pending assignments: {str(e)}"
        ) 