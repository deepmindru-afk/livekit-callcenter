#!/usr/bin/env python3
import sqlite3
import requests
import argparse
import sys
import os
import json
import time

def emergency_reset(username="agent2", password="password123"):
    """
    Emergency reset of call center agent status
    This script fixes ALL possible issues that could prevent making calls
    """
    print("===== EMERGENCY CALL CENTER RESET =====")
    print(f"Resetting all states for agent: {username}")
    
    # Step 1: Direct database reset
    print("\n[1/5] Resetting database state...")
    try:
        conn = sqlite3.connect('callcenter.db')
        cursor = conn.cursor()
        
        # Find the agent ID
        cursor.execute("SELECT id FROM agents WHERE username = ?", (username,))
        result = cursor.fetchone()
        
        if not result:
            print(f"Error: Agent '{username}' not found!")
            return False
            
        agent_id = result[0]
        
        # Reset agent status
        cursor.execute("UPDATE agents SET status = 'Available' WHERE id = ?", (agent_id,))
        
        # Mark all calls as completed
        cursor.execute("UPDATE calls SET status = 'Completed' WHERE agent_id = ? AND status = 'In_Progress'", (agent_id,))
        
        conn.commit()
        conn.close()
        print("  ✓ Database reset successful")
    except Exception as e:
        print(f"  ✗ Database reset failed: {str(e)}")
    
    # Step 2: Get auth token
    print("\n[2/5] Getting auth token...")
    token = None
    try:
        response = requests.post(
            "http://localhost:8000/api/login",
            data={"username": username, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            print("  ✓ Authentication successful")
        else:
            print(f"  ✗ Authentication failed: {response.text}")
    except Exception as e:
        print(f"  ✗ Authentication request failed: {str(e)}")
    
    # Step 3: Reset status via API
    if token:
        print("\n[3/5] Resetting status via API...")
        try:
            response = requests.put(
                "http://localhost:8000/api/agents/status",
                json={"status": "Available"},
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code == 200:
                print("  ✓ API status reset successful")
            else:
                print(f"  ✗ API status reset failed: {response.text}")
        except Exception as e:
            print(f"  ✗ API request failed: {str(e)}")
    
    # Step 4: Verify agent status
    if token:
        print("\n[4/5] Verifying agent status...")
        try:
            response = requests.get(
                "http://localhost:8000/api/agents/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get('status')
                print(f"  ✓ Current agent status: {status}")
                
                if status != 'Available':
                    print("  ✗ WARNING: Status is still not 'Available'!")
            else:
                print(f"  ✗ Status verification failed: {response.text}")
        except Exception as e:
            print(f"  ✗ Status verification request failed: {str(e)}")
    
    # Step 5: Look for code issues
    print("\n[5/5] Checking API code issue...")
    try:
        # Let's check the actual code that's making this check
        calls_py_path = os.path.join('app', 'routers', 'calls.py')
        if os.path.exists(calls_py_path):
            with open(calls_py_path, 'r') as f:
                code = f.read()
                
                # Look for the status check that's generating the error
                if "Agent must be in Available status to make a call" in code:
                    print("  ✓ Found the error check in the code")
                    
                    # Look for surrounding context
                    status_check_lines = []
                    for i, line in enumerate(code.split('\n')):
                        if "Agent must be in Available status" in line:
                            start = max(0, i-10)
                            end = min(len(code.split('\n')), i+10)
                            status_check_lines = code.split('\n')[start:end]
                            break
                    
                    if status_check_lines:
                        print("\nRelevant code section:")
                        for line in status_check_lines:
                            print(f"  {line}")
                    
                    print("\nIssue could be in the status comparison. Try editing calls.py to debug.")
                    
                else:
                    print("  ✗ Could not find the exact error message in code")
        else:
            print(f"  ✗ Could not find calls.py at {calls_py_path}")
    except Exception as e:
        print(f"  ✗ Code check failed: {str(e)}")
    
    print("\n===== EMERGENCY RESET COMPLETE =====")
    print("\nRECOMMENDED NEXT STEPS:")
    print("1. Restart the server: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")
    print("2. Clear your browser cache and cookies")
    print("3. Try to log in again")
    
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Emergency reset for call center agent')
    parser.add_argument('--username', default='agent2', help='Agent username')
    parser.add_argument('--password', default='password123', help='Agent password')
    
    args = parser.parse_args()
    emergency_reset(args.username, args.password) 