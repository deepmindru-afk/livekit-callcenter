from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional

from app.database.db import get_db
from app.models.models import Agent, AgentStatus
from app.schemas.schemas import Token, AgentCreate, AgentOut
from app.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")

router = APIRouter()

# Security utilities
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def authenticate_agent(db: Session, username: str, password: str):
    agent = db.query(Agent).filter(Agent.username == username).first()
    if not agent or not verify_password(password, agent.hashed_password):
        return None
    return agent

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_agent(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    agent = db.query(Agent).filter(Agent.username == username).first()
    if agent is None:
        raise credentials_exception
    return agent

# Routes
@router.post("/login", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    agent = authenticate_agent(db, form_data.username, form_data.password)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Update agent status to Available on login
    agent.status = AgentStatus.AVAILABLE.value
    db.commit()
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": agent.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/logout")
async def logout(current_agent: Agent = Depends(get_current_agent), db: Session = Depends(get_db)):
    # Update agent status to Offline on logout
    current_agent.status = AgentStatus.OFFLINE.value
    db.commit()
    return {"message": "Successfully logged out"}

@router.post("/register", response_model=AgentOut)
async def register_agent(agent: AgentCreate, db: Session = Depends(get_db)):
    # Check if username already exists
    db_agent = db.query(Agent).filter(Agent.username == agent.username).first()
    if db_agent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Create new agent
    hashed_password = get_password_hash(agent.password)
    # Generate a unique LiveKit identity (can be username for simplicity)
    livekit_identity = agent.username
    
    db_agent = Agent(
        username=agent.username,
        hashed_password=hashed_password,
        full_name=agent.full_name,
        status=AgentStatus.OFFLINE.value,
        livekit_identity=livekit_identity
    )
    db.add(db_agent)
    db.commit()
    db.refresh(db_agent)
    
    return AgentOut(
        id=db_agent.id,
        username=db_agent.username,
        full_name=db_agent.full_name,
        status=db_agent.status,
        livekit_identity=db_agent.livekit_identity
    ) 