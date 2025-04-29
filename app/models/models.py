from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, Float
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.database.db import Base

class AgentStatus(str, enum.Enum):
    AVAILABLE = "Available"
    BUSY = "Busy"
    OFFLINE = "Offline"

class CallDirection(str, enum.Enum):
    INBOUND = "Inbound"
    OUTBOUND = "Outbound"

class CallStatus(str, enum.Enum):
    COMPLETED = "Completed"
    REJECTED = "Rejected"
    FAILED = "Failed"
    IN_PROGRESS = "In_Progress"

class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String)
    status = Column(String, default=AgentStatus.OFFLINE)
    livekit_identity = Column(String, unique=True, index=True)
    
    calls = relationship("Call", back_populates="agent")

class Call(Base):
    __tablename__ = "calls"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"))
    caller_id = Column(String)  # From/To number
    direction = Column(String)  # Inbound/Outbound
    start_time = Column(DateTime, default=datetime.utcnow)
    duration = Column(Float, default=0.0)  # in seconds
    status = Column(String)  # Completed, Rejected, Failed
    livekit_room_name = Column(String, nullable=True)
    
    agent = relationship("Agent", back_populates="calls") 