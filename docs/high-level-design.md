# LiveKit Call Center - High-Level Design Document

## 1. Overview

The LiveKit Call Center is a web-based telephony application that enables call center agents to handle inbound and outbound voice calls through a modern web interface. The system leverages LiveKit for real-time communication capabilities and provides a complete call center solution with agent management, call routing, and real-time status updates.

### Core Technologies

- **Backend**: Python 3.11 + FastAPI
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla JS)
- **Real-time Communication**: LiveKit SDK for WebRTC
- **Database**: SQLite (development) / PostgreSQL (production)
- **WebSockets**: Real-time agent communication and status updates
- **Authentication**: JWT-based with OAuth2

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Browser   │    │   FastAPI App   │    │  LiveKit Server │
│   (Frontend)    │◄───┤   (Backend)     │◄───┤   (Media)       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   WebSocket     │    │   SQLite DB     │    │   SIP Trunk     │
│   Connection    │    │   (Agents/Calls)│    │   (PSTN)        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 2.2 Component Architecture

The application follows a modular FastAPI structure:

```
app/
├── main.py                 # FastAPI application entry point
├── config.py              # Configuration and environment variables
├── routers/               # API route handlers
│   ├── auth.py           # Authentication & authorization
│   ├── agents.py         # Agent management
│   └── calls.py          # Call handling (main business logic)
├── models/               # Database models
│   └── models.py         # SQLAlchemy ORM models
├── schemas/              # Pydantic schemas
│   └── schemas.py        # API request/response models
├── database/             # Database configuration
│   └── db.py            # SQLAlchemy setup
├── api/                  # API utilities
│   └── websocket_manager.py  # WebSocket connection management
├── services/             # Business logic services
├── templates/            # Jinja2 HTML templates
└── static/              # Static assets (CSS, JS, sounds)
```

## 3. Data Models

### 3.1 Database Schema

#### Agent Model

```python
class Agent:
    id: int (Primary Key)
    username: str (Unique)
    hashed_password: str
    full_name: str
    status: str (Available, Busy, Offline)
    livekit_identity: str (Unique)
    calls: relationship -> Call[]
```

#### Call Model

```python
class Call:
    id: int (Primary Key)
    agent_id: int (Foreign Key -> Agent)
    caller_id: str (Phone number)
    direction: str (Inbound, Outbound)
    start_time: datetime
    duration: float (seconds)
    status: str (Completed, Rejected, Failed, In_Progress)
    livekit_room_name: str
    agent: relationship -> Agent
```

### 3.2 Enums

- **AgentStatus**: Available, Busy, Offline
- **CallDirection**: Inbound, Outbound
- **CallStatus**: Completed, Rejected, Failed, In_Progress

## 4. Core Components

### 4.1 Authentication System (`auth.py`)

- **JWT-based authentication** using OAuth2 flow
- **Password hashing** with bcrypt
- **Agent registration** and login endpoints
- **Token-based session management**
- **Automatic status updates** on login/logout

**Key Endpoints:**

- `POST /api/login` - Agent authentication
- `POST /api/logout` - Session termination
- `POST /api/register` - New agent registration

### 4.2 Agent Management (`agents.py`)

- **Status management** (Available, Busy, Offline)
- **Agent information** retrieval
- **Real-time status broadcasting** via WebSockets

**Key Endpoints:**

- `GET /api/agents/me` - Current agent info
- `GET /api/agents` - All agents list
- `PUT /api/agents/status` - Update agent status
- `GET /api/agents/available` - Available agents only

### 4.3 Call Management (`calls.py`)

- **LiveKit integration** for real-time communication
- **Outbound call initiation** via SIP trunks
- **Inbound call routing** to available agents
- **Call control** (answer, reject, hangup)
- **Room management** for call sessions

**Key Components:**

- `LiveKitService` - Manages LiveKit API interactions
- `LivekitClientManager` - Async context manager for API clients
- `active_calls` - In-memory store for active call sessions

**Key Endpoints:**

- `POST /api/calls/outbound` - Initiate outbound call
- `POST /api/calls/inbound` - Handle incoming call webhook
- `POST /api/calls/{call_id}/answer` - Answer incoming call
- `POST /api/calls/{call_id}/reject` - Reject incoming call
- `POST /api/calls/{call_id}/hangup` - End active call
- `GET /api/calls` - Agent's call history
- `POST /api/calls/join-room` - Join LiveKit room
- `POST /api/calls/end-room` - End LiveKit room

### 4.4 WebSocket Manager (`websocket_manager.py`)

- **Real-time communication** between agents and backend
- **Status update broadcasting** across all connected agents
- **Incoming call notifications** to specific agents
- **Room update notifications** for call events

**Key Features:**

- Connection management per agent
- Personal messaging to specific agents
- Broadcast messaging to all agents
- Event-driven notifications (status changes, calls, room updates)

### 4.5 LiveKit Integration

The system integrates deeply with LiveKit for:

- **Room creation** for each call session
- **SIP participant management** for PSTN connectivity
- **WebRTC media handling** for browser-based audio
- **Token generation** for secure room access
- **Real-time communication** between agents and callers

## 5. Data Flow

### 5.1 Outbound Call Flow

```
1. Agent initiates call via frontend
2. POST /api/calls/outbound with phone number
3. Backend creates LiveKit room
4. Backend creates SIP participant for PSTN connection
5. Backend generates LiveKit token for agent
6. Agent joins room via LiveKit SDK
7. Call established between agent and external party
8. Call events tracked and stored in database
```

### 5.2 Inbound Call Flow

```
1. External caller dials configured number
2. SIP provider sends webhook to POST /api/calls/inbound
3. Backend finds available agent
4. WebSocket notification sent to agent's browser
5. Agent can accept/reject via frontend
6. If accepted: Room created, agent joins, call connected
7. If rejected: Call terminated
8. Call details logged to database
```

### 5.3 Agent Status Updates

```
1. Agent changes status via frontend
2. PUT /api/agents/status updates database
3. WebSocket broadcast notifies all other agents
4. Frontend updates reflect across all connected clients
```

## 6. Security Considerations

### 6.1 Authentication & Authorization

- **JWT tokens** with configurable expiration (default: 480 minutes)
- **Bcrypt password hashing** for secure credential storage
- **Bearer token authentication** for API access
- **Agent-scoped operations** - agents can only access their own data

### 6.2 Communication Security

- **LiveKit secure tokens** for room access
- **HTTPS enforcement** (configured via deployment)
- **CORS protection** with configurable origins
- **WebSocket authentication** via JWT tokens

### 6.3 Data Protection

- **SQL injection protection** via SQLAlchemy ORM
- **Input validation** via Pydantic schemas
- **Environment-based configuration** for sensitive credentials

## 7. Configuration Management

The system uses environment variables for configuration:

### 7.1 Core Settings

- `DEBUG` - Development mode flag
- `SECRET_KEY` - JWT signing key
- `DATABASE_URL` - Database connection string

### 7.2 LiveKit Configuration

- `LIVEKIT_API_KEY` - LiveKit API credentials
- `LIVEKIT_API_SECRET` - LiveKit API secret
- `LIVEKIT_URL` - LiveKit server URL
- `LIVEKIT_WS_URL` - WebSocket URL (auto-derived)
- `LIVEKIT_SIP_TRUNK_ID` - SIP trunk for PSTN connectivity

## 8. Real-time Features

### 8.1 WebSocket Events

- **status_update** - Agent status changes
- **incoming_call** - New inbound call notifications
- **call_ended** - Call termination events
- **room_update** - LiveKit room state changes

### 8.2 Live UI Updates

- **Agent status indicators** update in real-time
- **Incoming call alerts** appear instantly
- **Call duration timers** update during active calls
- **Room connectivity status** reflects LiveKit state

## 9. Deployment Architecture

### 9.1 Development Setup

- **SQLite database** for local development
- **FastAPI development server** with auto-reload
- **Local LiveKit server** or cloud LiveKit instance

### 9.2 Production Considerations

- **PostgreSQL database** for production data
- **ASGI server** (Uvicorn/Gunicorn) for production serving
- **Reverse proxy** (Nginx) for static file serving
- **SSL termination** for secure communications
- **Load balancing** for multiple FastAPI instances

## 10. Extensibility & Future Enhancements

The modular architecture supports future enhancements:

### 10.1 Planned Features (Out of Scope v1.0)

- **Call recording** via LiveKit recording service
- **Call transfer** and conference capabilities
- **Advanced call routing** with IVR support
- **Reporting dashboard** with analytics
- **CRM integration** for customer data
- **Administrator interface** for system management

### 10.2 Integration Points

- **Third-party CRM** via REST API extensions
- **Analytics platforms** via webhook events
- **Additional telephony providers** via abstraction layer
- **AI/ML services** for call analysis and routing

## 11. Performance Considerations

### 11.1 Scalability

- **Stateless backend design** enables horizontal scaling
- **Connection pooling** for database efficiency
- **WebSocket connection limits** managed per instance
- **LiveKit room cleanup** prevents resource leaks

### 11.2 Monitoring

- **Structured logging** via Python logging module
- **Call metrics tracking** in database
- **WebSocket connection monitoring**
- **LiveKit room status tracking**

---

This high-level design provides a comprehensive overview of the LiveKit Call Center application architecture, enabling developers to understand the system structure and extend functionality as needed.
