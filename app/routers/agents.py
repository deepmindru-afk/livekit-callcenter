from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database.db import get_db
from app.models.models import Agent, AgentStatus
from app.routers.auth import get_current_agent
from app.schemas.schemas import AgentOut, StatusUpdate
from app.api.websocket_manager import ConnectionManager

router = APIRouter()
manager = ConnectionManager()

@router.get("/agents/me", response_model=AgentOut)
async def get_current_agent_info(current_agent: Agent = Depends(get_current_agent)):
    return AgentOut(
        id=current_agent.id,
        username=current_agent.username,
        full_name=current_agent.full_name,
        status=current_agent.status,
        livekit_identity=current_agent.livekit_identity
    )

@router.get("/agents", response_model=List[AgentOut])
async def get_all_agents(db: Session = Depends(get_db), current_agent: Agent = Depends(get_current_agent)):
    agents = db.query(Agent).all()
    return [
        AgentOut(
            id=agent.id,
            username=agent.username,
            full_name=agent.full_name,
            status=agent.status,
            livekit_identity=agent.livekit_identity
        ) for agent in agents
    ]

@router.put("/agents/status", response_model=AgentOut)
async def update_agent_status(
    status_update: StatusUpdate,
    db: Session = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent)
):
    # Validate status
    if status_update.status not in [status.value for status in AgentStatus]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of {[s.value for s in AgentStatus]}"
        )
    
    # Update agent status in DB
    current_agent.status = status_update.status
    db.commit()
    db.refresh(current_agent)
    
    # Broadcast status update to all connected clients
    await manager.broadcast_status_update(str(current_agent.id), current_agent.status)
    
    return AgentOut(
        id=current_agent.id,
        username=current_agent.username,
        full_name=current_agent.full_name,
        status=current_agent.status,
        livekit_identity=current_agent.livekit_identity
    )

@router.get("/agents/available", response_model=List[AgentOut])
async def get_available_agents(db: Session = Depends(get_db), current_agent: Agent = Depends(get_current_agent)):
    agents = db.query(Agent).filter(Agent.status == AgentStatus.AVAILABLE).all()
    return [
        AgentOut(
            id=agent.id,
            username=agent.username,
            full_name=agent.full_name,
            status=agent.status,
            livekit_identity=agent.livekit_identity
        ) for agent in agents
    ] 