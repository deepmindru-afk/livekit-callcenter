# API Fix Instructions

We've updated the frontend code to match the correct API endpoints. Here's what we changed:

## 1. Agent Status Endpoint
- Changed from `POST /api/agents/status` to `PUT /api/agents/status`
- Changed status retrieval from `/api/agents/status/1` to `/api/agents/me`

## 2. Call Management Endpoints
- Changed from `/api/calls/accept` to `/api/calls/{call_id}/answer`
- Changed from `/api/calls/reject` to `/api/calls/{call_id}/reject`
- Changed from `/api/calls/hangup` to `/api/calls/{call_id}/hangup`
- Changed call history endpoint from `/api/calls/history` to `/api/calls`

## 3. Data Format Adjustments
- Removed call_id from request body (now in URL)
- Adjusted API response handling for call history
- Improved data field mapping for timestamps and caller IDs

## Instructions to Apply the Fix

1. **Restart the server** to ensure all changes take effect:
   ```
   # Stop the current server (Ctrl+C)
   # Then restart it with:
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

2. **Clear your browser cache**:
   - Press Ctrl+Shift+Delete
   - Select "Cached images and files"
   - Click "Clear data"

3. **Try accessing the application again** at http://localhost:8000/login

4. **Login with your credentials**:
   - Username: agent2
   - Password: password123

These changes should resolve the API-related errors you were experiencing. If you still encounter issues, check the server logs for more specific error messages.

## Testing API Endpoints Directly

You can test the endpoints with curl commands:

```bash
# Login to get a token
TOKEN=$(curl -s -X POST http://localhost:8000/api/login \
  -d "username=agent2&password=password123" \
  -H "Content-Type: application/x-www-form-urlencoded" | jq -r '.access_token')

# Test getting agent info
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/agents/me

# Test updating status
curl -X PUT -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status":"Available"}' \
  http://localhost:8000/api/agents/status

# Test getting call history
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/calls
``` 