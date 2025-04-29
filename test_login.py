import requests

# The URL for the login endpoint
url = "http://localhost:8000/api/login"

# Use the credentials we created earlier
login_data = {
    "username": "agent2",
    "password": "password123"
}

# Send the login request with the correct content type
response = requests.post(
    url, 
    data=login_data,  # Form data, not JSON
    headers={"Content-Type": "application/x-www-form-urlencoded"}
)

print(f"Status code: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    print(f"Access token: {data['access_token'][:20]}...")  # Only show start of token for security
    
    # Now test getting agent information with the token
    agent_url = "http://localhost:8000/api/agents/me"
    agent_response = requests.get(
        agent_url,
        headers={"Authorization": f"Bearer {data['access_token']}"}
    )
    
    print(f"\nAgent info request status: {agent_response.status_code}")
    if agent_response.status_code == 200:
        agent_data = agent_response.json()
        print(f"Agent info: {agent_data}")
    else:
        print(f"Error: {agent_response.text}")
else:
    print(f"Error: {response.text}") 