from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# Authentication schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# Agent schemas
class AgentBase(BaseModel):
    username: str
    full_name: str

class AgentCreate(AgentBase):
    password: str

class AgentOut(AgentBase):
    id: int
    status: str
    livekit_identity: str
    
    class Config:
        orm_mode = True

# Status update schema
class StatusUpdate(BaseModel):
    status: str

# Call schemas
class CallCreate(BaseModel):
    phone_number: str
    room_name: Optional[str] = None

class CallOut(BaseModel):
    id: int
    agent_id: int
    caller_id: str
    direction: str
    start_time: datetime
    duration: float
    status: str
    livekit_room_name: str
    livekit_token: Optional[str] = None
    
    class Config:
        orm_mode = True

class IncomingCallResponse(BaseModel):
    accept: bool 