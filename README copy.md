# Call Center Application

A simple MVP web-based call center application that enables agents to handle inbound and outbound voice calls through a web interface using LiveKit for media handling.

## Features

- Agent authentication (login/logout)
- Agent status management (Available, Busy, Offline)
- Make outbound calls via LiveKit
- Receive inbound calls
- Basic call controls (mute/unmute, hang up)
- Call logging and history

## Prerequisites

- Python 3.11+
- LiveKit server (for media handling)
- A PSTN provider integration with LiveKit (for production use)

## Setup

1. Clone the repository:

```bash
git clone <repository-url>
cd call-center-app
```

2. Create a virtual environment and activate it:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Configure LiveKit:

   Edit the `.env` file or set the following environment variables:

   ```
   LIVEKIT_API_KEY=your_livekit_api_key
   LIVEKIT_API_SECRET=your_livekit_api_secret
   LIVEKIT_URL=http://localhost:7880
   LIVEKIT_WS_URL=ws://localhost:7880
   ```

5. Create a test agent:

```bash
uvicorn app.main:app --reload
```

Then use the API to create an agent by sending a POST request to `/api/register` with:

```json
{
  "username": "agent1",
  "password": "password123",
  "full_name": "Agent One"
}
```

You can use curl, Postman, or any API testing tool.

## Running the Application

1. Start the application:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

2. Access the application in your browser:

```
http://localhost:8000
```

3. Log in with the credentials of the agent you created.

## Development

- The backend is built with FastAPI
- The frontend is a simple HTML/CSS/JS application
- Database: SQLite for development (can be switched to PostgreSQL for production)
- WebSockets are used for real-time communication

## Production Deployment Considerations

For a production deployment, consider:

1. Using a production-grade database like PostgreSQL
2. Setting proper environment variables for security (e.g., JWT secret key)
3. Setting up proper CORS configuration
4. Using a production ASGI server like Gunicorn with Uvicorn workers
5. Implementing proper error handling and monitoring
6. Setting up SSL/TLS for secure connections
7. Implementing rate limiting and other security measures

## License

[MIT License](LICENSE) 