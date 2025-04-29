import requests
import json

# The URL for the registration endpoint - the correct endpoint is /api/login
url = "http://localhost:8000/api/register"  # For registration

# Agent details
agent_data = {
    "username": "agent2",
    "password": "password123",
    "full_name": "Agent Two"
}

# Send the registration request
response = requests.post(url, json=agent_data)

# Print the response
print(f"Status code: {response.status_code}")
print(f"Response: {response.json() if response.status_code == 200 else response.text}")

# Now let's also try logging in
login_url = "http://localhost:8000/api/login"
login_data = {
    "username": "agent2",
    "password": "password123"
}

# The login endpoint expects form data, not JSON
login_response = requests.post(
    login_url, 
    data={"username": "agent2", "password": "password123"}
)

print("\nLogin attempt:")
print(f"Status code: {login_response.status_code}")
print(f"Response: {login_response.json() if login_response.status_code == 200 else login_response.text}") 