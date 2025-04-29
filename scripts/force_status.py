import sqlite3
import sys

def force_status_available(username):
    """Force an agent's status to Available directly in the database."""
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect('callcenter.db')
        cursor = conn.cursor()
        
        # Check current status
        cursor.execute("SELECT status FROM agents WHERE username = ?", (username,))
        result = cursor.fetchone()
        
        if not result:
            print(f"Error: Agent with username '{username}' not found in the database.")
            return False
        
        current_status = result[0]
        print(f"Current status for agent '{username}': {current_status}")
        
        # Update the status to Available
        cursor.execute(
            "UPDATE agents SET status = ? WHERE username = ?", 
            ("Available", username)
        )
        
        conn.commit()
        
        # Verify the update
        cursor.execute("SELECT status FROM agents WHERE username = ?", (username,))
        new_status = cursor.fetchone()[0]
        
        print(f"Status updated for agent '{username}': {new_status}")
        
        # Also check if there are any active calls for this agent
        cursor.execute("""
            SELECT id, status FROM calls 
            WHERE agent_id = (SELECT id FROM agents WHERE username = ?) 
            AND status = 'In_Progress'
        """, (username,))
        
        active_calls = cursor.fetchall()
        if active_calls:
            print(f"Found {len(active_calls)} active calls for this agent. Marking them as completed:")
            for call_id, call_status in active_calls:
                cursor.execute(
                    "UPDATE calls SET status = 'Completed' WHERE id = ?", 
                    (call_id,)
                )
                print(f"  - Call ID {call_id} status changed from '{call_status}' to 'Completed'")
            conn.commit()
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        username = sys.argv[1]
    else:
        username = "agent2"  # Default username
    
    print(f"Forcing status to Available for agent: {username}")
    success = force_status_available(username)
    
    if success:
        print("\nStatus update successful! You should now be able to make calls.")
        print("Please restart your browser and try again.")
    else:
        print("\nFailed to update status. Please check the error message above.")
        print("You may need to restart the server and try again.") 