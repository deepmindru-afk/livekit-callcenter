# Call Center Login Instructions

## Account Details
We've successfully registered a new agent account with the following credentials:

- **Username:** agent2
- **Password:** password123

## How to Login

### Method 1: Using the Web Interface
1. Make sure the server is running with the correct command:
   ```
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
2. Open your web browser and navigate to: http://localhost:8000/login
3. Enter the username and password above
4. You'll be redirected to the agent interface where you can:
   - Make outbound calls
   - Receive inbound calls
   - Update your status
   - View call history

### Method 2: Using the API (for developers)
To get an authentication token programmatically:

```bash
# Important: The login endpoint expects form data, not JSON
curl -X POST http://localhost:8000/api/login \
  -d "username=agent2&password=password123" \
  -H "Content-Type: application/x-www-form-urlencoded"
```

The response will contain an access token that you can use for subsequent API calls:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### Troubleshooting Login Issues
- Make sure you're using the correct endpoint: `/api/login` (not `/api/auth/login`)
- The API expects form data with `Content-Type: application/x-www-form-urlencoded`
- If using the web interface, clear your browser cache if you see `[object Object]` errors

## Features Available After Login
- **Agent Status Management:** Set your status to Available, Busy, or Offline
- **Outbound Calls:** Enter a phone number and make calls
- **Inbound Calls:** Receive and handle incoming calls
- **Call Controls:** Mute/unmute and hang up during active calls
- **Call History:** View your recent call activity 