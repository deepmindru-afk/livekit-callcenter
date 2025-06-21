// Auto-Assignment Manager
class AutoAssignmentManager {
  constructor() {
    this.isActive = false;
    this.currentInvitation = null;
    this.countdownTimer = null;
    this.statusUpdateInterval = null;

    this.initializeUI();
    this.bindEvents();
  }

  initializeUI() {
    // Get UI elements
    this.elements = {
      toggleBtn: document.getElementById("toggleAutoAssignmentBtn"),
      statusIndicator: document.getElementById("autoAssignmentStatus"),
      statusState: document.getElementById("autoAssignmentState"),
      modal: document.getElementById("callInvitationModal"),
      acceptBtn: document.getElementById("acceptInvitationBtn"),
      rejectBtn: document.getElementById("rejectInvitationBtn"),
      callerId: document.getElementById("invitationCallerId"),
      roomName: document.getElementById("invitationRoomName"),
      countdown: document.getElementById("invitationCountdown"),
      statusPanel: document.getElementById("autoAssignmentPanel"),
      closeStatusPanel: document.getElementById("closeStatusPanelBtn"),
      serviceStatus: document.getElementById("serviceStatus"),
      pendingCount: document.getElementById("pendingCount"),
      lastUpdate: document.getElementById("lastUpdate"),
      pendingAssignments: document.getElementById("pendingAssignments"),
    };

    // // Check if all elements were found
    // const missingElements = Object.entries(this.elements)
    //   .filter(([key, element]) => !element)
    //   .map(([key]) => key);

    // if (missingElements.length > 0) {
    //   console.error("Missing auto-assignment UI elements:", missingElements);
    //   this.showNotification(
    //     "Auto-assignment UI elements missing: " + missingElements.join(", "),
    //     "error"
    //   );
    // } else {
    //   console.log("All auto-assignment UI elements found successfully");
    // }

    // Initialize status
    this.updateUI();
    this.updateDebugPanel();
  }

  updateDebugPanel() {
    const managerStatus = document.getElementById("debugManagerStatus");
    const webSocketStatus = document.getElementById("debugWebSocket");

    if (managerStatus) {
      managerStatus.textContent = "Initialized";
    }

    if (webSocketStatus && window.socket) {
      webSocketStatus.textContent =
        window.socket.readyState === WebSocket.OPEN
          ? "Connected"
          : "Disconnected";
    }
  }

  bindEvents() {
    // Toggle auto-assignment
    // this.elements.toggleBtn.addEventListener("click", () => {
    //   this.toggleAutoAssignment();
    // });

    // Call invitation responses
    this.elements.acceptBtn.addEventListener("click", () => {
      this.respondToInvitation(true);
    });

    this.elements.rejectBtn.addEventListener("click", () => {
      this.respondToInvitation(false, "user_declined");
    });

    // // Status panel
    // this.elements.statusIndicator.addEventListener("click", () => {
    //   this.showStatusPanel();
    // });

    // this.elements.closeStatusPanel.addEventListener("click", () => {
    //   this.hideStatusPanel();
    // });

    // Modal overlay click to close
    this.elements.modal.addEventListener("click", (event) => {
      if (event.target === this.elements.modal) {
        this.respondToInvitation(false, "timeout");
      }
    });

    // Keyboard shortcuts
    document.addEventListener("keydown", (event) => {
      if (this.currentInvitation) {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          this.respondToInvitation(true);
        } else if (event.key === "Escape") {
          event.preventDefault();
          this.respondToInvitation(false, "user_declined");
        }
      }
    });
  }

  async toggleAutoAssignment() {
    try {
      if (this.isActive) {
        await this.stopAutoAssignment();
      } else {
        await this.startAutoAssignment();
      }
    } catch (error) {
      console.error("Error toggling auto-assignment:", error);
      this.showNotification(
        "Failed to toggle auto-assignment: " + error.message,
        "error"
      );
    }
  }

  async startAutoAssignment() {
    const token = localStorage.getItem("token");

    const response = await fetch("/api/auto-assignment/start", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    });

    if (response.ok) {
      this.isActive = true;
      this.updateUI();
      this.startStatusUpdates();
      this.showNotification("Auto-assignment started successfully", "success");
    } else {
      const error = await response.text();
      throw new Error(error);
    }
  }

  async stopAutoAssignment() {
    const token = localStorage.getItem("token");

    const response = await fetch("/api/auto-assignment/stop", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    });

    if (response.ok) {
      this.isActive = false;
      this.updateUI();
      this.stopStatusUpdates();
      this.showNotification("Auto-assignment stopped", "info");
    } else {
      const error = await response.text();
      throw new Error(error);
    }
  }

  async getStatus() {
    try {
      const token = localStorage.getItem("token");

      const response = await fetch("/api/auto-assignment/status", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const status = await response.json();
        this.updateStatusDisplay(status);
        return status;
      }
    } catch (error) {
      console.error("Error getting auto-assignment status:", error);
    }
  }

  startStatusUpdates() {
    // Update status every 10 seconds
    this.statusUpdateInterval = setInterval(() => {
      this.getStatus();
    }, 10000);
  }

  stopStatusUpdates() {
    if (this.statusUpdateInterval) {
      clearInterval(this.statusUpdateInterval);
      this.statusUpdateInterval = null;
    }
  }

  updateUI() {
    console.log("Updating auto-assignment UI");
    // Update toggle button
    // this.elements.toggleBtn.textContent = this.isActive ? "Stop" : "Start";
    // this.elements.toggleBtn.className = this.isActive
    //   ? "btn-danger btn-small"
    //   : "btn-secondary btn-small";

    // Update status indicator
    // this.elements.statusState.textContent = this.isActive ? "Active" : "Off";
    // this.elements.statusIndicator.className = this.isActive
    //   ? "status-indicator active"
    //   : "status-indicator inactive";
  }

  updateStatusDisplay(status) {
    this.elements.serviceStatus.textContent = status.is_monitoring
      ? "Running"
      : "Stopped";
    this.elements.pendingCount.textContent = Object.keys(
      status.pending_assignments || {}
    ).length;
    this.elements.lastUpdate.textContent = new Date().toLocaleTimeString();

    // Update pending assignments display
    this.updatePendingAssignments(status.pending_assignments || {});
  }

  updatePendingAssignments(assignments) {
    const container = this.elements.pendingAssignments;
    container.innerHTML = "";

    const assignmentCount = Object.keys(assignments).length;

    if (assignmentCount === 0) {
      container.innerHTML =
        '<div class="pending-assignment-item">No pending assignments</div>';
      return;
    }

    Object.entries(assignments).forEach(([roomName, assignment]) => {
      const item = document.createElement("div");
      item.className = "pending-assignment-item";
      item.innerHTML = `
                <div><strong>Room:</strong> ${roomName}</div>
                <div><strong>Caller:</strong> ${assignment.caller_id}</div>
                <div><strong>Agents:</strong> ${
                  assignment.available_agents?.length || 0
                }</div>
                <div><strong>Current:</strong> ${
                  assignment.current_agent_index + 1
                }/${assignment.available_agents?.length || 0}</div>
            `;
      container.appendChild(item);
    });
  }

  showCallInvitation(invitation) {
    console.log("Showing call invitation modal for:", invitation);

    if (!this.elements.modal) {
      console.error("Call invitation modal element not found!");
      this.showNotification(
        "Cannot show call invitation - modal not found",
        "error"
      );
      return;
    }

    // Store current invitation
    this.currentInvitation = invitation;

    // Update invitation display
    if (this.elements.callerId) {
      this.elements.callerId.textContent = invitation.caller_id || "Unknown";
    }
    if (this.elements.roomName) {
      this.elements.roomName.textContent = invitation.room_name || "Unknown";
    }

    // Reset countdown
    let timeLeft = invitation.timeout || 30;
    if (this.elements.countdown) {
      this.elements.countdown.textContent = timeLeft;
    }

    // Show modal
    console.log("Removing hidden class from modal");
    this.elements.modal.classList.remove("hidden");
    this.elements.modal.style.display = "flex"; // Force display

    console.log("Modal should now be visible");

    // Start countdown timer
    this.countdownTimer = setInterval(() => {
      timeLeft--;
      if (this.elements.countdown) {
        this.elements.countdown.textContent = timeLeft;
      }

      if (timeLeft <= 0) {
        console.log("Invitation timeout reached");
        this.respondToInvitation(false, "timeout");
      }
    }, 1000);

    // Play notification sound
    this.playNotificationSound();

    // Show additional notification
    this.showNotification(
      `📞 Incoming call from ${invitation.caller_id || "Unknown"}`,
      "info"
    );
  }

  hideCallInvitation() {
    this.elements.modal.classList.add("hidden");
    this.currentInvitation = null;

    if (this.countdownTimer) {
      clearInterval(this.countdownTimer);
      this.countdownTimer = null;
    }
  }

  async respondToInvitation(accepted, reason = "") {
    if (!this.currentInvitation) {
      console.warn("No current invitation to respond to");
      return;
    }

    // Store invitation data before hiding (to avoid race condition)
    const invitationData = {
      room_name: this.currentInvitation.room_name,
      call_id: this.currentInvitation.call_id,
      caller_id: this.currentInvitation.caller_id,
    };

    try {
      const token = localStorage.getItem("token");

      // Send response via API
      const response = await fetch("/api/auto-assignment/respond", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          room_name: invitationData.room_name,
          accepted: accepted,
          reason: reason,
        }),
      });

      if (response.ok) {
        // Also send via WebSocket for immediate response
        if (window.socket && window.socket.readyState === WebSocket.OPEN) {
          window.socket.send(
            JSON.stringify({
              type: "call_invitation_response",
              room_name: invitationData.room_name,
              accepted: accepted,
              reason: reason,
            })
          );
        }

        this.hideCallInvitation();

        if (accepted) {
          this.showNotification(
            `Call from ${invitationData.caller_id} accepted successfully!`,
            "success"
          );

          // Auto-join the agent to the room
          await this.autoJoinRoom(invitationData);
        } else {
          this.showNotification("Call invitation declined", "info");
        }
      } else {
        const error = await response.text();
        throw new Error(error);
      }
    } catch (error) {
      console.error("Error responding to invitation:", error);
      this.showNotification(
        "Failed to respond to invitation: " + error.message,
        "error"
      );
      // Hide invitation even on error to prevent stuck state
      this.hideCallInvitation();
    }
  }

  showStatusPanel() {
    this.elements.statusPanel.classList.remove("hidden");
    this.getStatus(); // Refresh status when showing panel
  }

  hideStatusPanel() {
    this.elements.statusPanel.classList.add("hidden");
  }

  playNotificationSound() {
    // Try to play the ringtone or create a beep sound
    const ringtone = document.getElementById("ringtone");
    if (ringtone) {
      ringtone.play().catch((err) => {
        console.warn("Could not play notification sound:", err);
        // Fallback to browser beep
        this.playBeep();
      });
    } else {
      this.playBeep();
    }
  }

  playBeep() {
    // Create a simple beep sound using Web Audio API
    try {
      const audioContext = new (window.AudioContext ||
        window.webkitAudioContext)();
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();

      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);

      oscillator.frequency.setValueAtTime(800, audioContext.currentTime);
      gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(
        0.01,
        audioContext.currentTime + 0.5
      );

      oscillator.start(audioContext.currentTime);
      oscillator.stop(audioContext.currentTime + 0.5);
    } catch (error) {
      console.warn("Could not create beep sound:", error);
    }
  }

  showNotification(message, type = "info") {
    // Create a simple notification
    const notification = document.createElement("div");
    notification.className = `notification notification-${type}`;
    notification.textContent = message;

    notification.style.cssText = `
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: ${
              type === "error"
                ? "#dc3545"
                : type === "success"
                ? "#28a745"
                : "#007bff"
            };
            color: white;
            padding: 12px 24px;
            border-radius: 4px;
            z-index: 2000;
            animation: slideDown 0.3s ease-in-out;
        `;

    document.body.appendChild(notification);

    // Remove notification after 3 seconds
    setTimeout(() => {
      notification.style.animation = "slideUp 0.3s ease-in-out";
      setTimeout(() => {
        if (notification.parentNode) {
          notification.parentNode.removeChild(notification);
        }
      }, 300);
    }, 3000);
  }

  async autoJoinRoom(invitationData) {
    try {
      console.log(`Auto-joining room: ${invitationData.room_name}`);

      // Check microphone access first
      const callHandler = window.callHandler;
      if (callHandler && callHandler.checkMicrophoneAccess) {
        const micStatus = await callHandler.checkMicrophoneAccess();
        if (!micStatus.supported) {
          console.warn("Microphone issue:", micStatus.error);
          // Continue anyway - user already accepted the call
        }
      }

      // Update agent status to Busy (should already be done by server, but ensure it's set)
      const token = localStorage.getItem("token");

      // Call API to join the room
      const response = await fetch("/api/calls/join-room", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          room_name: invitationData.room_name,
          call_id: invitationData.call_id,
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Failed to join room: ${errorText}`);
      }

      const data = await response.json();

      // Update UI to show active call
      const callerId = document.getElementById("callerId");
      const activeCallPanel = document.getElementById("activeCall");

      if (callerId) {
        callerId.textContent =
          invitationData.caller_id || `Room: ${invitationData.room_name}`;
      }

      if (activeCallPanel) {
        activeCallPanel.classList.remove("hidden");
      }

      // Start call timer
      if (window.startCallTimer) {
        window.startCallTimer();
      }

      // Store call info globally
      const callInfo = {
        id: data.call_id || invitationData.call_id,
        room_name: invitationData.room_name,
        direction: "inbound",
        caller_id: invitationData.caller_id,
      };

      if (window.setActiveCall) {
        window.setActiveCall(callInfo);
      } else {
        window.activeCall = callInfo;
      }

      // Use callHandler to connect to room
      if (callHandler) {
        try {
          console.log("Connecting to LiveKit room with token...");
          await callHandler.acceptIncomingCall(data.token);
          console.log("Successfully connected to LiveKit room");
        } catch (callError) {
          console.error("Error in LiveKit connection:", callError);
          this.showNotification(
            `Call connection error: ${callError.message}`,
            "error"
          );
        }
      } else {
        console.warn(
          "CallHandler not available - audio connection may not work"
        );
      }

      // Switch to the outbound calls tab to show the active call
      const firstTabBtn = document.querySelector(
        '.tab-btn[data-tab="outbound-tab"]'
      );
      if (firstTabBtn) {
        firstTabBtn.click();
      }

      this.showNotification(
        `Successfully joined call with ${invitationData.caller_id}`,
        "success"
      );
    } catch (error) {
      console.error("Error auto-joining room:", error);
      this.showNotification(`Failed to join call: ${error.message}`, "error");

      // Revert agent status to Available on error
      try {
        const token = localStorage.getItem("token");
        await fetch("/api/agents/status", {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ status: "Available" }),
        });
      } catch (statusError) {
        console.error("Error reverting agent status:", statusError);
      }
    }
  }

  // Test function for debugging
  testCallInvitation() {
    console.log("Testing call invitation display...");
    const testInvitation = {
      type: "call_invitation",
      room_name: "inbound-test-" + Date.now(),
      caller_id: "+1234567890",
      call_id: 123,
      timestamp: new Date().toISOString(),
      timeout: 30,
    };
    this.showCallInvitation(testInvitation);
  }

  // Handle WebSocket messages for auto-assignment
  handleWebSocketMessage(data) {
    console.log("Auto-assignment manager handling message:", data);

    // Update debug panel
    const debugLastMessage = document.getElementById("debugLastMessage");
    if (debugLastMessage) {
      debugLastMessage.textContent = `${
        data.type
      } at ${new Date().toLocaleTimeString()}`;
    }

    switch (data.type) {
      case "call_invitation":
        console.log("Processing call invitation:", data);
        this.showCallInvitation(data);
        break;

      case "call_assigned":
        console.log("Processing call assignment:", data);
        this.hideCallInvitation();
        this.showNotification("Call successfully assigned to you!", "success");
        break;

      case "call_ended":
        console.log("Processing call ended:", data);
        this.handleCallEnded(data);
        break;

      default:
        // Let other handlers deal with other message types
        console.log(
          "Auto-assignment manager ignoring message type:",
          data.type
        );
        break;
    }
  }

  handleCallEnded(data) {
    // Clean up any auto-assignment related state when call ends
    console.log("Auto-assignment: Call ended, cleaning up...");

    // Clear any pending invitations
    if (this.currentInvitation) {
      this.hideCallInvitation();
    }

    // Show notification if this was an auto-assigned call
    if (data && data.room_name && data.room_name.startsWith("inbound-")) {
      this.showNotification("Auto-assigned call ended", "info");
    }
  }
}

// Global instance
window.autoAssignmentManager = null;

// Initialize when DOM is ready and make sure all elements exist
function initializeAutoAssignment() {
  // Check if all required elements exist
  // const requiredElements = [
  //   "toggleAutoAssignmentBtn",
  //   "autoAssignmentStatus",
  //   "autoAssignmentState",
  //   "callInvitationModal",
  //   "acceptInvitationBtn",
  //   "rejectInvitationBtn",
  // ];

  // const allElementsExist = requiredElements.every((id) =>
  //   document.getElementById(id)
  // );

  // if (allElementsExist) {
  console.log("Initializing auto-assignment manager...");
  window.autoAssignmentManager = new AutoAssignmentManager();
  // } else {
  //   console.warn("Auto-assignment elements not found, retrying in 1 second...");
  //   setTimeout(initializeAutoAssignment, 1000);
  // }
}

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", initializeAutoAssignment);

// Also initialize when main.js has loaded (fallback)
window.addEventListener("load", () => {
  if (!window.autoAssignmentManager) {
    initializeAutoAssignment();
  }
});

// CSS for notifications (add to head if not in CSS file)
const notificationStyles = `
@keyframes slideDown {
    from {
        transform: translateX(-50%) translateY(-100%);
        opacity: 0;
    }
    to {
        transform: translateX(-50%) translateY(0);
        opacity: 1;
    }
}

@keyframes slideUp {
    from {
        transform: translateX(-50%) translateY(0);
        opacity: 1;
    }
    to {
        transform: translateX(-50%) translateY(-100%);
        opacity: 0;
    }
}
`;

// Add notification styles to head
const styleSheet = document.createElement("style");
styleSheet.textContent = notificationStyles;
document.head.appendChild(styleSheet);

// Expose test function globally for debugging
window.testAutoAssignment = function () {
  if (window.autoAssignmentManager) {
    window.autoAssignmentManager.testCallInvitation();
  } else {
    console.error("Auto-assignment manager not initialized");
    alert("Auto-assignment manager not initialized. Check console for errors.");
  }
};
