# LiveKit Call Center

A modern, web-based call center application built with FastAPI and LiveKit, featuring real-time call management, auto-assignment, and agent status tracking.

## 🚀 Features

### Core Functionality

- **🔐 Authentication & Authorization** - JWT-based secure login system for agents
- **👥 Agent Management** - Real-time status tracking (Available, Busy, Offline)
- **📞 Inbound Call Handling** - Automatic call routing with WebRTC integration
- **📱 Outbound Call Management** - Web-based dialpad for PSTN calls
- **⚡ Auto-Assignment Service** - Intelligent automatic call routing to available agents
- **🔄 Real-time Communication** - WebSocket-based live updates and notifications
- **📊 Call Logging** - Comprehensive call history and analytics
- **🎯 Call Controls** - Mute/unmute, hold, transfer, and hangup functionality

### Technical Features

- **LiveKit SIP Integration** - Direct PSTN connectivity through LiveKit server
- **WebRTC Media Handling** - High-quality voice communication
- **Real-time Status Updates** - Instant agent status synchronization
- **Responsive Web Interface** - Modern HTML5/CSS3/JavaScript frontend
- **Database Persistence** - SQLAlchemy with SQLite/PostgreSQL support
- **Background Services** - Automated call monitoring and assignment

## 🏗️ Architecture

### Backend Stack

- **FastAPI** - Modern, high-performance web framework
- **SQLAlchemy** - Database ORM with support for multiple databases
- **WebSockets** - Real-time bidirectional communication
- **JWT Authentication** - Secure token-based authentication
- **Pydantic** - Data validation and serialization
- **LiveKit SDK** - Voice/video communication and SIP integration

### Frontend Stack

- **HTML5/CSS3/JavaScript** - Modern web standards
- **LiveKit Client SDK** - WebRTC client integration
- **WebSocket Client** - Real-time communication
- **Responsive Design** - Works on desktop and mobile devices

### Database Schema

- **Agents** - User accounts, credentials, and status
- **Calls** - Call records, duration, and metadata
- **Real-time Sessions** - Active WebSocket connections

## 📋 Prerequisites

- Python 3.11+
- LiveKit Server (local or cloud instance)
- SIP Trunk configuration (for PSTN connectivity)
- Modern web browser with WebRTC support

## ⚙️ Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/your-repo/livekit-callcenter.git
   cd livekit-callcenter
   ```

2. **Create and activate virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   Create a `.env` file in the root directory:

   ```env
   # Application Settings
   SECRET_KEY=your-secret-key-here
   DEBUG=False
   APP_NAME=Call Center API

   # Database Configuration
   DATABASE_URL=sqlite:///./callcenter.db  # For development
   # DATABASE_URL=postgresql://user:password@localhost/callcenter  # For production

   # LiveKit Configuration
   LIVEKIT_API_KEY=your-livekit-api-key
   LIVEKIT_API_SECRET=your-livekit-api-secret
   LIVEKIT_URL=https://your-livekit-server.com
   LIVEKIT_WS_URL=wss://your-livekit-server.com
   LIVEKIT_SIP_TRUNK_ID=your-sip-trunk-id

   # Security Settings
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=480
   ```

5. **Initialize the database**

   ```bash
   python -c "from app.database.db import engine, Base; Base.metadata.create_all(bind=engine)"
   ```

6. **Register your first agent** (optional)
   ```bash
   python scripts/register_agent.py
   ```

## 🚀 Running the Application

### Development Mode

```bash
# Using the provided script
./launch.sh

# Or directly with uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Or using the Python runner
python run.py
```

### Production Mode

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

The application will be available at `http://localhost:8000`

## 📖 Usage

### Agent Interface

1. **Login** - Navigate to `/login` and authenticate with agent credentials
2. **Set Status** - Update your availability status (Available/Busy/Offline)
3. **Handle Calls**:
   - **Outbound**: Use the dialpad to enter phone numbers and initiate calls
   - **Inbound**: Receive automatic call invitations when status is "Available"
4. **Call Controls** - Use in-call controls for mute, hold, transfer, and hangup
5. **View History** - Review call logs and performance metrics

### Auto-Assignment Feature

The auto-assignment service automatically routes incoming calls to available agents:

1. **Activation**: Set agent status to "Available"
2. **Call Detection**: System monitors for new inbound rooms (prefix: "inbound-")
3. **Agent Selection**: Finds available agents and sends call invitations
4. **Response Handling**: 30-second timeout per agent, automatic failover
5. **Call Connection**: Connects accepted calls via LiveKit rooms

### API Endpoints

- `POST /api/login` - Agent authentication
- `GET /api/agents/me` - Get current agent information
- `PUT /api/agents/status` - Update agent status
- `POST /api/calls/outbound` - Initiate outbound call
- `POST /api/calls/{id}/answer` - Answer incoming call
- `POST /api/calls/{id}/hangup` - End active call
- `GET /api/calls` - Get call history
- `WebSocket /ws/{agent_id}` - Real-time communication

## 🛠️ Scripts & Utilities

The `scripts/` directory contains helpful utilities:

- `emergency_reset.py` - Emergency system reset
- `fix_call_center.py` - Database and configuration fixes
- `force_status.py` - Force agent status updates
- `register_agent.py` - Register new agents
- `test_login.py` - Test authentication functionality

## 🔧 Configuration

### LiveKit Server Setup

1. **Install LiveKit Server**:

   ```bash
   # Using Docker
   docker run -d --name livekit \
     -p 7880:7880 -p 7881:7881 -p 7882:7882/udp \
     livekit/livekit-server
   ```

2. **Configure SIP Trunk** - Set up your SIP provider credentials in LiveKit
3. **Generate API Keys** - Create API key/secret pair for the application

### Database Configuration

For production, configure PostgreSQL:

```sql
CREATE DATABASE callcenter;
CREATE USER callcenter_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE callcenter TO callcenter_user;
```

Update `.env` with PostgreSQL connection string:

```env
DATABASE_URL=postgresql://callcenter_user:your_password@localhost/callcenter
```

## 🐛 Troubleshooting

### Common Issues

1. **WebSocket Connection Failed**

   - Check LIVEKIT_WS_URL configuration
   - Verify network connectivity to LiveKit server
   - Ensure WebSocket is not blocked by firewall

2. **SIP Calls Not Working**

   - Verify LIVEKIT_SIP_TRUNK_ID configuration
   - Check SIP trunk status in LiveKit dashboard
   - Confirm PSTN provider credentials

3. **Agent Not Receiving Calls**

   - Ensure agent status is "Available"
   - Check WebSocket connection in browser console
   - Verify auto-assignment service is running

4. **Database Connection Issues**
   - Check DATABASE_URL format
   - Ensure database server is running
   - Verify user permissions

### Debug Mode

Enable debug logging by setting `DEBUG=True` in `.env` file.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Related Projects

- [LiveKit](https://livekit.io/) - Real-time communication platform
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework for Python
- [SQLAlchemy](https://www.sqlalchemy.org/) - Database toolkit for Python

## 📞 Support

For questions and support:

- Create an issue in this repository
- Check the troubleshooting section above
- Review LiveKit documentation for SIP-related issues

---

Built with ❤️ using LiveKit and FastAPI
