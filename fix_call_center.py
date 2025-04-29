import sqlite3
import sys
import requests
import json
import time

def run_diagnostics(username="agent2"):
    """Run comprehensive diagnostics on the call center database"""
    try:
        print("====== CALL CENTER DIAGNOSTIC TOOL ======")
        print(f"Running diagnostics for agent: {username}")
        print("\n1. Checking database connection...")
        
        # Connect to the SQLite database
        conn = sqlite3.connect('callcenter.db')
        cursor = conn.cursor()
        print("   ✓ Database connection successful")
        
        # Check agent exists and status
        print("\n2. Checking agent record...")
        cursor.execute("SELECT id, username, status, livekit_identity FROM agents WHERE username = ?", (username,))
        agent = cursor.fetchone()
        
        if not agent:
            print(f"   ✗ ERROR: Agent '{username}' not found in database!")
            return False
        
        agent_id, agent_username, agent_status, livekit_identity = agent
        print(f"   ✓ Found agent record: ID={agent_id}, Username={agent_username}")
        print(f"   ✓ Current status: {agent_status}")
        print(f"   ✓ LiveKit identity: {livekit_identity}")
        
        # Check if there are any active calls
        print("\n3. Checking for active calls...")
        cursor.execute("""
            SELECT id, caller_id, direction, status, livekit_room_name 
            FROM calls 
            WHERE agent_id = ? AND status = 'In_Progress'
        """, (agent_id,))
        
        active_calls = cursor.fetchall()
        if active_calls:
            print(f"   ✗ Found {len(active_calls)} active calls:")
            for call in active_calls:
                call_id, caller_id, direction, status, room_name = call
                print(f"     - Call ID: {call_id}, Caller: {caller_id}, Direction: {direction}, Room: {room_name}")
        else:
            print("   ✓ No active calls found")
        
        # Check all status values in the database
        print("\n4. Checking agent status definitions...")
        cursor.execute("PRAGMA table_info(agents)")
        agent_columns = [row[1] for row in cursor.fetchall()]
        
        if 'status' not in agent_columns:
            print("   ✗ ERROR: 'status' column not found in agents table!")
        else:
            cursor.execute("SELECT DISTINCT status FROM agents")
            status_values = [row[0] for row in cursor.fetchall()]
            print(f"   ✓ Found status values: {', '.join(status_values)}")
        
        # Check for case issues - sometimes 'Available' vs 'available'
        if agent_status != 'Available':
            print(f"   ✗ WARNING: Agent status '{agent_status}' is not exactly 'Available'")
            if agent_status.lower() == 'available':
                print("     → Case mismatch detected!")
        
        # Check for permissions issues
        print("\n5. Testing database write permissions...")
        try:
            # Try to update and immediately restore the status
            cursor.execute("UPDATE agents SET status = ? WHERE id = ?", ("Testing", agent_id))
            cursor.execute("UPDATE agents SET status = ? WHERE id = ?", (agent_status, agent_id))
            conn.commit()
            print("   ✓ Database write permissions OK")
        except sqlite3.Error as e:
            print(f"   ✗ ERROR: Cannot write to database: {str(e)}")
        
        print("\n====== DIAGNOSTICS COMPLETE ======")
        
        # Ask user if they want to fix issues
        print("\nWould you like to attempt to fix all detected issues? (y/n)")
        response = input("> ")
        
        if response.lower() in ['y', 'yes']:
            fix_all_issues(conn, cursor, agent_id, username)
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error during diagnostics: {str(e)}")
        return False

def fix_all_issues(conn, cursor, agent_id, username):
    print("\n====== FIXING ISSUES ======")
    
    # 1. Reset agent status to Available
    print("1. Setting agent status to Available...")
    cursor.execute("UPDATE agents SET status = ? WHERE id = ?", ("Available", agent_id))
    conn.commit()
    print("   ✓ Agent status updated to Available")
    
    # 2. Mark all active calls as Completed
    print("\n2. Marking all active calls as Completed...")
    cursor.execute("""
        UPDATE calls SET status = 'Completed'
        WHERE agent_id = ? AND status = 'In_Progress'
    """, (agent_id,))
    rows_affected = cursor.rowcount
    conn.commit()
    if rows_affected > 0:
        print(f"   ✓ {rows_affected} call(s) marked as Completed")
    else:
        print("   ✓ No active calls needed to be updated")
    
    # 3. Check for any LiveKit rooms that need cleanup
    print("\n3. Checking for LiveKit rooms to clean up...")
    cursor.execute("""
        SELECT livekit_room_name FROM calls
        WHERE agent_id = ? AND livekit_room_name IS NOT NULL
    """, (agent_id,))
    rooms = [row[0] for row in cursor.fetchall() if row[0]]
    if rooms:
        print(f"   ℹ Found {len(rooms)} LiveKit rooms to clean up")
        print("   ℹ To clean up these rooms, you would need to call the LiveKit API")
    else:
        print("   ✓ No LiveKit rooms to clean up")
    
    print("\n✅ All database fixes applied!")
    print("\nPlease restart your server and refresh your browser to apply these changes.")
    print("You can run this diagnostic tool again to verify the fixes.")

def get_agent_token(username, password):
    """Get authentication token for an agent"""
    try:
        print(f"\nAttempting to log in as {username}...")
        response = requests.post(
            "http://localhost:8000/api/login",
            data={"username": username, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            print("   ✓ Login successful")
            return token
        else:
            print(f"   ✗ Login failed: {response.text}")
            return None
    except Exception as e:
        print(f"   ✗ Error during login: {str(e)}")
        return None

def check_api_status(token):
    """Check the API status for the agent"""
    if not token:
        return
    
    try:
        print("\nChecking agent status via API...")
        response = requests.get(
            "http://localhost:8000/api/agents/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ API reports agent status as: {data.get('status')}")
        else:
            print(f"   ✗ Failed to get agent status: {response.text}")
    except Exception as e:
        print(f"   ✗ Error checking API status: {str(e)}")

def force_api_status_update(token):
    """Force agent status update via API"""
    if not token:
        return
    
    try:
        print("\nForcing agent status to Available via API...")
        response = requests.put(
            "http://localhost:8000/api/agents/status",
            json={"status": "Available"},
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ API status update successful: {data.get('status')}")
        else:
            print(f"   ✗ Failed to update status: {response.text}")
    except Exception as e:
        print(f"   ✗ Error updating status via API: {str(e)}")

if __name__ == "__main__":
    run_diagnostics()
    
    print("\nWould you like to test the API endpoints? (y/n)")
    response = input("> ")
    
    if response.lower() in ['y', 'yes']:
        password = input("\nEnter the password for agent2: ")
        token = get_agent_token("agent2", password)
        
        if token:
            check_api_status(token)
            
            print("\nWould you like to force update the status via API? (y/n)")
            api_response = input("> ")
            
            if api_response.lower() in ['y', 'yes']:
                force_api_status_update(token) 