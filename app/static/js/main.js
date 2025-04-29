// Call Center Agent Interface Main Script
document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const agentName = document.getElementById('agentName');
    const statusSelect = document.getElementById('status');
    const logoutBtn = document.getElementById('logoutBtn');
    const phoneInput = document.getElementById('phoneNumber');
    const callBtn = document.getElementById('callBtn');
    const muteBtn = document.getElementById('muteBtn');
    const hangupBtn = document.getElementById('hangupBtn');
    const acceptBtn = document.getElementById('acceptBtn');
    const rejectBtn = document.getElementById('rejectBtn');
    const activeCallPanel = document.getElementById('activeCall');
    const incomingCallPanel = document.getElementById('incomingCall');
    const callerId = document.getElementById('callerId');
    const incomingCallerId = document.getElementById('incomingCallerId');
    const callDuration = document.getElementById('callDuration');
    const callLogBody = document.getElementById('callLogBody');
    const dialpadButtons = document.querySelectorAll('.dialpad-btn');
    const ringtone = document.getElementById('ringtone');
    
    // Tab navigation
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    const refreshInboundBtn = document.getElementById('refreshInboundBtn');
    const inboundCallsBody = document.getElementById('inboundCallsBody');

    // Authentication Check
    const token = localStorage.getItem('token');
    const agent = JSON.parse(localStorage.getItem('agent') || '{}');
    
    if (!token) {
        // Redirect to login if not authenticated
        window.location.href = '/login';
        return;
    }

    // Update agent name display
    agentName.textContent = agent.name || 'Unknown';

    // WebSocket connection
    let socket;
    connectWebSocket();

    // Livekit call handlers should be initialized from livekit-handler.js
    // We'll assume those functions are available to us
    const callHandler = window.callHandler; // Global from livekit-handler.js

    // Call state variables
    let activeCall = null;
    let callStartTime = null;
    let callTimerInterval = null;
    let isMuted = false;

    // Initialize UI
    loadCallHistory();
    loadInboundCalls();

    // Event Listeners
    logoutBtn.addEventListener('click', handleLogout);
    statusSelect.addEventListener('change', handleStatusChange);
    callBtn.addEventListener('click', handleOutboundCall);
    muteBtn.addEventListener('click', handleMute);
    hangupBtn.addEventListener('click', handleHangup);
    acceptBtn.addEventListener('click', handleAcceptCall);
    rejectBtn.addEventListener('click', handleRejectCall);
    refreshInboundBtn.addEventListener('click', loadInboundCalls);

    // Tab switching
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            // Remove active class from all buttons and tabs
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));
            
            // Add active class to clicked button and corresponding tab
            button.classList.add('active');
            const tabId = button.dataset.tab;
            document.getElementById(tabId).classList.add('active');
            
            // Refresh data when switching to a tab
            if (tabId === 'inbound-tab') {
                loadInboundCalls();
            } else if (tabId === 'recent-tab') {
                loadCallHistory();
            }
        });
    });

    // Dialpad buttons
    dialpadButtons.forEach(button => {
        button.addEventListener('click', () => {
            const digit = button.textContent;
            phoneInput.value += digit;
        });
    });

    // Set initial agent status (from server or localStorage)
    fetchCurrentStatus();

    // Functions
    function connectWebSocket() {
        // Connect to WebSocket for real-time events
        socket = new WebSocket(`${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/ws/${agent.id}`);
        
        socket.onopen = () => {
            console.log('WebSocket connection established');
        };
        
        socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            handleWebSocketMessage(data);
        };
        
        socket.onclose = () => {
            console.log('WebSocket connection closed');
            // Try to reconnect after a delay
            setTimeout(connectWebSocket, 3000);
        };
        
        socket.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }

    function handleWebSocketMessage(data) {
        switch (data.type) {
            case 'incoming_call':
                showIncomingCall(data);
                break;
            case 'status_update':
                // Update UI if another agent's status changes (if needed)
                break;
            case 'call_ended':
                handleCallEnded(data);
                break;
            case 'room_update':
                // Refresh inbound calls list when rooms change
                console.log('Room update received:', data);
                
                // Only auto-refresh if we're on the inbound calls tab
                const inboundTabActive = document.querySelector('#inbound-tab').classList.contains('active');
                if (inboundTabActive) {
                    // If we have specific room data, we could potentially just update that room
                    // instead of reloading everything
                    if (data.room && data.room.event) {
                        if (data.room.event === 'room_created') {
                            highlightNewRoom(data.room.room_name);
                        } else if (data.room.event === 'room_deleted') {
                            removeDeletedRoom(data.room.room_name);
                        }
                    } else {
                        // Just do a full refresh
                        loadInboundCalls();
                    }
                }
                break;
            default:
                console.log('Unknown message type:', data.type);
        }
    }

    function showIncomingCall(data) {
        // Show incoming call panel with caller information
        incomingCallerId.textContent = data.caller_id || 'Unknown';
        incomingCallPanel.classList.remove('hidden');
        
        // Play ringtone
        ringtone.play().catch(err => console.error('Could not play ringtone:', err));
    }

    async function handleOutboundCall() {
        const phoneNumber = phoneInput.value.trim();
        if (!phoneNumber) return;
        
        try {
            // Check microphone access first if available
            if (callHandler && callHandler.checkMicrophoneAccess) {
                const micStatus = await callHandler.checkMicrophoneAccess();
                if (!micStatus.supported) {
                    // Show warning but allow the call to continue
                    console.warn('Microphone issue:', micStatus.error);
                    
                    // Ask user if they want to continue without microphone
                    if (!confirm(`${micStatus.error}\n\nDo you want to continue without microphone access? You may not be able to speak in the call.`)) {
                        return; // User chose to cancel
                    }
                }
            }
            
            // Update status to Busy
            await updateAgentStatus('Busy');
            
            // Create a unique room name for the call
            const roomName = `call-${Date.now()}-${Math.floor(Math.random() * 1000)}`;
            
            // Create a call record in our database
            const callResponse = await fetch('/api/calls/outbound', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ 
                    phone_number: phoneNumber,
                    room_name: roomName
                })
            });
            
            const callData = await callResponse.json();
            
            if (!callResponse.ok) {
                throw new Error(callData.detail || 'Failed to initiate call');
            }
            
            // Populate active call information
            callerId.textContent = phoneNumber;
            activeCallPanel.classList.remove('hidden');
            
            // Start call timer
            startCallTimer();
            
            // Store call info
            activeCall = {
                id: callData.id,
                number: phoneNumber,
                direction: 'outbound',
                room_name: roomName
            };
            
            // Use callHandler to connect to room directly using the token from the backend
            if (callHandler) {
                // Wrap the call in try/catch to handle any errors
                try {
                    await callHandler.startOutboundCall(callData.livekit_token, phoneNumber, roomName);
                } catch (callError) {
                    console.error('Error in call setup:', callError);
                    alert(`Call connection error: ${callError.message}. Call record created but connection failed.`);
                    
                    // Continue with the call UI anyway - call is in progress even if client connection failed
                    console.log('Call record created, continuing with call UI');
                }
            }
            
        } catch (error) {
            console.error('Outbound call error:', error);
            alert(`Call failed: ${error.message}`);
            
            // Revert status to Available
            updateAgentStatus('Available');
        }
    }

    async function handleAcceptCall() {
        try {
            // Stop ringtone
            ringtone.pause();
            ringtone.currentTime = 0;
            
            // Hide incoming call panel
            incomingCallPanel.classList.remove('hidden');
            
            // Update status to Busy
            await updateAgentStatus('Busy');
            
            // Call the API to accept the call
            const response = await fetch(`/api/calls/${activeCall.id}/answer`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                }
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.detail || 'Failed to accept call');
            }
            
            // Show active call panel
            callerId.textContent = incomingCallerId.textContent;
            activeCallPanel.classList.remove('hidden');
            incomingCallPanel.classList.add('hidden');
            
            // Start call timer
            startCallTimer();
            
            // Initialize call with Livekit (should be handled in livekit-handler.js)
            if (callHandler) {
                callHandler.acceptIncomingCall(data.call_token);
            }
            
        } catch (error) {
            console.error('Accept call error:', error);
            alert(`Could not accept call: ${error.message}`);
            
            // Hide panels and revert status
            incomingCallPanel.classList.add('hidden');
            updateAgentStatus('Available');
        }
    }

    async function handleRejectCall() {
        try {
            // Stop ringtone
            ringtone.pause();
            ringtone.currentTime = 0;
            
            // Hide incoming call panel
            incomingCallPanel.classList.add('hidden');
            
            // Call the API to reject the call
            await fetch(`/api/calls/${activeCall.id}/reject`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                }
            });
            
        } catch (error) {
            console.error('Reject call error:', error);
        }
    }

    function handleMute() {
        isMuted = !isMuted;
        
        // Update button text
        muteBtn.textContent = isMuted ? 'Unmute' : 'Mute';
        
        // Call Livekit mute/unmute functionality
        if (callHandler) {
            callHandler.toggleMute(isMuted);
        }
    }

    async function handleHangup() {
        if (!activeCall) {
            return;
        }
        
        try {
            // If it's an inbound call from a room, end the room
            if (activeCall.direction === 'inbound' && activeCall.room_name) {
                await fetch('/api/calls/end-room', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    },
                    body: JSON.stringify({
                        room_name: activeCall.room_name,
                        call_id: activeCall.id
                    })
                });
            } else {
                // Regular call hangup logic
                await fetch(`/api/calls/${activeCall.id}/hangup`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    }
                });
            }
            
            // End the call in the UI and LiveKit
            handleCallEnded();
            
            if (callHandler) {
                callHandler.endCall();
            }
            
        } catch (error) {
            console.error('Hangup error:', error);
            alert(`Hangup failed: ${error.message}`);
        }
    }

    function handleCallEnded(data = {}) {
        // Stop timer
        stopCallTimer();
        
        // Hide call panels
        activeCallPanel.classList.add('hidden');
        incomingCallPanel.classList.add('hidden');
        
        // Reset active call
        activeCall = null;
        
        // Reset mute state
        isMuted = false;
        muteBtn.textContent = 'Mute';
        
        // Force update agent status to Available and wait for it to complete
        setTimeout(() => {
            updateAgentStatus('Available').then(() => {
                console.log('Agent status updated to Available after call ended');
                // Refresh call history after status is updated
                loadCallHistory();
            }).catch(error => {
                console.error('Failed to update agent status:', error);
                // Try one more time after a delay
                setTimeout(() => updateAgentStatus('Available'), 1000);
            });
        }, 500);
    }

    function startCallTimer() {
        callStartTime = new Date();
        
        callTimerInterval = setInterval(() => {
            const now = new Date();
            const diffInSeconds = Math.floor((now - callStartTime) / 1000);
            const minutes = Math.floor(diffInSeconds / 60).toString().padStart(2, '0');
            const seconds = (diffInSeconds % 60).toString().padStart(2, '0');
            
            callDuration.textContent = `${minutes}:${seconds}`;
        }, 1000);
    }

    function stopCallTimer() {
        if (callTimerInterval) {
            clearInterval(callTimerInterval);
            callTimerInterval = null;
        }
        callDuration.textContent = '00:00';
    }

    async function updateAgentStatus(status) {
        try {
            // Update UI first
            statusSelect.value = status;
            
            console.log('Updating agent status to:', status);
            
            // Then send to server - corrected to PUT instead of POST
            const response = await fetch('/api/agents/status', {
                method: 'PUT',  // Changed from POST to PUT
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ status })
            });
            
            // Check if the server didn't like our request
            if (!response.ok) {
                const errorData = await response.json();
                console.error('Server rejected status update:', errorData);
                throw new Error(errorData.detail || 'Status update failed');
            }
            
            // Get the response data to confirm status was updated
            const data = await response.json();
            console.log('Status update response:', data);
            
            return data;
        } catch (error) {
            console.error('Status update error:', error);
            // Revert UI if server update failed
            fetchCurrentStatus();
            throw error;
        }
    }

    async function handleStatusChange() {
        const newStatus = statusSelect.value;
        
        // Don't allow changing to Available if in a call
        if (newStatus === 'Available' && activeCall) {
            alert('Cannot change status to Available while in a call');
            statusSelect.value = 'Busy';
            return;
        }
        
        await updateAgentStatus(newStatus);
    }

    async function fetchCurrentStatus() {
        try {
            // Use the /api/agents/me endpoint which has the agent's status
            const response = await fetch(`/api/agents/me`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (!response.ok) {
                throw new Error('Failed to get agent status');
            }
            
            const data = await response.json();
            statusSelect.value = data.status;
            
        } catch (error) {
            console.error('Get status error:', error);
            // Default to Available if can't fetch
            statusSelect.value = 'Available';
        }
    }

    async function loadCallHistory() {
        try {
            // Changed from /api/calls/history to /api/calls
            const response = await fetch('/api/calls', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (!response.ok) {
                throw new Error('Failed to load call history');
            }
            
            const data = await response.json();
            
            // Clear existing rows
            callLogBody.innerHTML = '';
            
            // Add calls to the table
            data.forEach(call => {
                const row = document.createElement('tr');
                
                const formattedDate = new Date(call.timestamp || call.start_time).toLocaleString();
                const duration = call.duration ? formatDuration(call.duration) : 'N/A';
                
                row.innerHTML = `
                    <td>${formattedDate}</td>
                    <td>${call.direction}</td>
                    <td>${call.caller_id || call.to_number || call.from_number}</td>
                    <td>${duration}</td>
                    <td>${call.status}</td>
                `;
                
                callLogBody.appendChild(row);
            });
            
        } catch (error) {
            console.error('Call history error:', error);
        }
    }

    function formatDuration(seconds) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = seconds % 60;
        return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
    }

    async function handleLogout() {
        try {
            // First update status to Offline
            console.log('Setting status to Offline before logout');
            try {
                await updateAgentStatus('Offline');
            } catch (statusError) {
                console.error('Failed to set status to Offline:', statusError);
                // Continue with logout regardless
            }
            
            // Call logout API
            console.log('Calling logout API');
            await fetch('/api/logout', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
        } catch (error) {
            console.error('Logout error:', error);
        } finally {
            // Always clear local storage and redirect
            localStorage.removeItem('token');
            localStorage.removeItem('agent');
            
            // Close WebSocket
            if (socket) {
                socket.close();
            }
            
            // Redirect to login
            window.location.href = '/login';
        }
    }

    // Function to force update the agent status regardless of current UI state
    async function forceStatusUpdate() {
        try {
            // Get current agent info to check status
            const response = await fetch('/api/agents/me', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (!response.ok) {
                throw new Error('Failed to get agent info');
            }
            
            const data = await response.json();
            console.log('Current agent status:', data.status);
            
            // If not available, force update to Available
            if (data.status !== 'Available') {
                await updateAgentStatus('Available');
                console.log('Forced agent status to Available');
            }
        } catch (error) {
            console.error('Error in force status update:', error);
        }
    }

    // Add event listener for page load to force status check
    window.addEventListener('load', function() {
        setTimeout(forceStatusUpdate, 1000);
    });

    // Track the current rooms to detect changes
    let currentRooms = [];

    async function loadInboundCalls() {
        try {
            const response = await fetch('/api/calls/active-rooms', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (!response.ok) {
                throw new Error('Failed to fetch inbound calls');
            }
            
            const data = await response.json();
            const rooms = data.rooms || [];
            
            // Save previous room names before updating
            const previousRooms = [...currentRooms];
            
            // Update current rooms
            currentRooms = rooms.map(room => room.room_name);
            
            // Find new rooms (rooms that weren't in the previous list)
            const newRooms = rooms.filter(room => 
                !previousRooms.includes(room.room_name)
            ).map(room => room.room_name);
            
            // Clear the inbound calls table
            inboundCallsBody.innerHTML = '';
            
            if (rooms.length === 0) {
                // Display a message if no rooms are available
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td colspan="5" style="text-align: center;">No active rooms available</td>
                `;
                inboundCallsBody.appendChild(row);
                return;
            }
            
            // Add each room to the table
            rooms.forEach(room => {
                const row = document.createElement('tr');
                row.dataset.roomName = room.room_name;
                
                // Add 'new' class if this is a newly added room
                if (newRooms.includes(room.room_name) && previousRooms.length > 0) {
                    row.classList.add('room-item', 'new');
                    
                    // Remove the 'new' class after animation completes
                    setTimeout(() => {
                        row.classList.remove('new');
                    }, 2000);
                } else {
                    row.classList.add('room-item');
                }
                
                // Format creation time if available
                let formattedTime = 'N/A';
                if (room.creation_time) {
                    try {
                        const date = new Date(room.creation_time);
                        formattedTime = date.toLocaleTimeString();
                    } catch (e) {
                        console.warn('Unable to format creation time:', e);
                    }
                }
                
                row.innerHTML = `
                    <td>${room.room_name}</td>
                    <td>${room.room_id || 'N/A'}</td>
                    <td>${room.status || 'Active'}</td>
                    <td>${room.participant_count || 0}</td>
                    <td><button class="join-call-btn" data-room="${room.room_name}">Join Call</button></td>
                `;
                
                inboundCallsBody.appendChild(row);
            });
            
            // Add event listeners to the join call buttons
            document.querySelectorAll('.join-call-btn').forEach(button => {
                button.addEventListener('click', handleJoinRoom);
            });
            
        } catch (error) {
            console.error('Error loading inbound calls:', error);
            
            // Display error message
            inboundCallsBody.innerHTML = `
                <tr>
                    <td colspan="5" style="text-align: center; color: red;">
                        Error loading inbound calls: ${error.message}
                    </td>
                </tr>
            `;
        }
    }
    
    function highlightNewRoom(roomName) {
        // First check if the room already exists in the current rooms
        if (currentRooms.includes(roomName)) {
            // If it exists, find the row and highlight it
            const existingRow = document.querySelector(`tr[data-room-name="${roomName}"]`);
            if (existingRow) {
                existingRow.classList.add('new');
                setTimeout(() => {
                    existingRow.classList.remove('new');
                }, 2000);
                return;
            }
        }
        
        // If we don't have the room, reload the entire list
        loadInboundCalls();
    }

    function removeDeletedRoom(roomName) {
        // Find the row with this room name
        const rowToRemove = document.querySelector(`tr[data-room-name="${roomName}"]`);
        if (rowToRemove) {
            // Add a fade-out effect
            rowToRemove.style.opacity = '0';
            rowToRemove.style.transform = 'translateX(20px)';
            
            // Remove after animation completes
            setTimeout(() => {
                rowToRemove.remove();
                
                // If no more rooms, show the "no rooms" message
                if (inboundCallsBody.querySelectorAll('tr').length === 0) {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td colspan="5" style="text-align: center;">No active rooms available</td>
                    `;
                    inboundCallsBody.appendChild(row);
                }
            }, 300);
            
            // Also remove from our tracked list
            const index = currentRooms.indexOf(roomName);
            if (index !== -1) {
                currentRooms.splice(index, 1);
            }
        } else {
            // If we can't find the row, reload the entire list
            loadInboundCalls();
        }
    }

    async function handleJoinRoom(event) {
        const roomName = event.target.dataset.room;
        
        if (!roomName) {
            return;
        }
        
        try {
            // Check microphone access first
            if (callHandler && callHandler.checkMicrophoneAccess) {
                const micStatus = await callHandler.checkMicrophoneAccess();
                if (!micStatus.supported) {
                    if (!confirm(`${micStatus.error}\n\nDo you want to continue without microphone access?`)) {
                        return;
                    }
                }
            }
            
            // Update status to Busy
            await updateAgentStatus('Busy');
            
            // Call API to join the room
            const response = await fetch('/api/calls/join-room', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ room_name: roomName })
            });
            
            if (!response.ok) {
                throw new Error('Failed to join room');
            }
            
            const data = await response.json();
            
            // Update UI to show active call
            callerId.textContent = `Room: ${roomName}`;
            activeCallPanel.classList.remove('hidden');
            
            // Start call timer
            startCallTimer();
            
            // Store call info
            activeCall = {
                id: data.call_id,
                room_name: roomName,
                direction: 'inbound'
            };
            
            // Use callHandler to connect to room
            if (callHandler) {
                try {
                    await callHandler.acceptIncomingCall(data.token);
                } catch (callError) {
                    console.error('Error in call setup:', callError);
                    alert(`Call connection error: ${callError.message}`);
                }
            }
            
            // Switch to the first tab to show the active call
            tabButtons[0].click();
            
        } catch (error) {
            console.error('Error joining room:', error);
            alert(`Failed to join room: ${error.message}`);
            
            // Revert status to Available
            updateAgentStatus('Available');
        }
    }
}); 