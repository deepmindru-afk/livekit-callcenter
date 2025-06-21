// Livekit Integration Handler
// This file manages WebRTC connections using the Livekit SDK

(function () {
  // Initialize Livekit variables
  let room;
  let localParticipant;
  let localTrackPublication;
  let remoteAudioElement = document.getElementById("remoteAudio");

  // Add a createDummyAudioTrack function to the LivekitClient global
  // This will create a silent audio track as a fallback
  if (window.LivekitClient && !LivekitClient.createDummyAudioTrack) {
    LivekitClient.createDummyAudioTrack = function () {
      // Create an audio context
      const audioContext = new (window.AudioContext ||
        window.webkitAudioContext)();

      // Create an oscillator that generates silence
      const oscillator = audioContext.createOscillator();
      const destination = audioContext.createMediaStreamDestination();
      oscillator.connect(destination);

      // Start the oscillator but with 0 gain (silent)
      const gainNode = audioContext.createGain();
      gainNode.gain.value = 0;
      oscillator.connect(gainNode);
      gainNode.connect(destination);
      oscillator.start();

      // Create a track from the media stream
      const track = destination.stream.getAudioTracks()[0];

      return new LivekitClient.LocalAudioTrack(track, {
        name: "silent_fallback",
      });
    };
  }

  // Handler functions exposed to main.js
  const callHandler = {
    // Check if microphone access is available (optional pre-check)
    checkMicrophoneAccess: async function () {
      try {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
          console.warn("Browser does not support getUserMedia API");
          return {
            supported: false,
            error: "Your browser does not support microphone access",
          };
        }

        // Try to access the microphone
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: true,
        });

        // Stop all tracks to release the microphone
        stream.getTracks().forEach((track) => track.stop());

        return { supported: true };
      } catch (error) {
        console.error("Microphone access error:", error);

        let errorMessage = "Could not access microphone";
        if (
          error.name === "NotAllowedError" ||
          error.name === "PermissionDeniedError"
        ) {
          errorMessage =
            "Microphone access denied. Please allow microphone access in your browser settings.";
        } else if (
          error.name === "NotFoundError" ||
          error.name === "DevicesNotFoundError"
        ) {
          errorMessage =
            "No microphone found. Please connect a microphone and try again.";
        }

        return {
          supported: false,
          error: errorMessage,
        };
      }
    },

    // Start a new outbound call
    startOutboundCall: async function (token, phoneNumber, roomName) {
      try {
        // Connect to Livekit room directly using the token
        await connectToRoom(token);

        // Publish local audio track
        await publishLocalAudio();

        // Create SIP invite for the phone number
        await createSIPInvite(phoneNumber, roomName);

        console.log(`Outbound call to ${phoneNumber} initiated`);
      } catch (error) {
        console.error("Error starting outbound call:", error);
        throw error;
      }
    },

    // Accept an incoming call
    acceptIncomingCall: async function (token) {
      try {
        // Connect to Livekit room
        await connectToRoom(token);

        // Publish local audio track
        await publishLocalAudio();

        console.log("Incoming call accepted");
      } catch (error) {
        console.error("Error accepting incoming call:", error);
        throw error;
      }
    },

    // Toggle mute state
    toggleMute: function (muted) {
      if (!localParticipant || !localTrackPublication) {
        console.warn("Cannot toggle mute: no active call");
        return;
      }

      if (muted) {
        localTrackPublication.mute();
        console.log("Microphone muted");
      } else {
        localTrackPublication.unmute();
        console.log("Microphone unmuted");
      }
    },

    // End the current call
    endCall: function () {
      if (room) {
        room.disconnect();
        console.log("Call ended, room disconnected");
      }

      // Clear references
      room = null;
      localParticipant = null;
      localTrackPublication = null;
    },
  };

  // Connect to a Livekit room using the provided token
  async function connectToRoom(token) {
    if (!token) {
      throw new Error("No token provided for Livekit connection");
    }

    // Decode token to check details and log them for debugging
    try {
      const tokenParts = token.split(".");
      if (tokenParts.length === 3) {
        const payloadBase64 = tokenParts[1];
        const payload = JSON.parse(atob(payloadBase64));
        console.log("Token payload:", payload);
        console.log("Token video grant:", payload.video);
      }
    } catch (e) {
      console.error("Failed to decode token:", e);
    }

    try {
      // Initialize room instance
      room = new LivekitClient.Room({
        // Optional room configuration
        adaptiveStream: true,
        dynacast: true,
        stopLocalTrackOnUnpublish: true,
      });

      // Set up event listeners for room events
      setupRoomEventListeners();

      // Get the LiveKit server URL from configuration
      // This should be set in your HTML or configuration
      let livekitServerUrl = window.livekitServerUrl;

      // If not configured, try to determine it from token or use fallback
      if (!livekitServerUrl) {
        // Try to extract from API URL pattern
        const apiUrl = window.location.origin;

        // Check if we're on localhost for development
        if (apiUrl.includes("localhost") || apiUrl.includes("127.0.0.1")) {
          livekitServerUrl = "ws://localhost:7880";
        } else {
          // Production fallback (should be configured properly)
          livekitServerUrl = "wss://livekit.your-domain.com";
        }

        // livekitServerUrl = 'wss://livekit-server-staging.tsengineering.io';

        console.log("Using fallback LiveKit server URL:", livekitServerUrl);
      }

      console.log("Connecting to LiveKit server at:", livekitServerUrl);

      // Connect to Livekit room
      await room.connect(livekitServerUrl, token, {
        // Additional connection options for debugging
        autoSubscribe: true,
        // rtcConfig: {
        //     iceServers: [
        //         { urls: 'stun:stun.l.google.com:19302' },
        //         { urls: 'stun:stun1.l.google.com:19302' }
        //     ]
        // }
      });

      // Get local participant reference
      localParticipant = room.localParticipant;

      console.log("Connected to Livekit room:", room.name);
    } catch (error) {
      console.error("Failed to connect to Livekit room:", error);
      console.error("Connection error details:", error.message);
      console.error("Error stack:", error.stack);

      // Check if it's a network error
      if (
        error.message.includes("Failed to fetch") ||
        error.message.includes("NetworkError") ||
        error.message.includes("connection") ||
        error.message.includes("signal")
      ) {
        console.error(
          "Network error detected. Please check your LiveKit server URL and ensure it is accessible."
        );
      }

      throw error;
    }
  }

  // Create SIP invite to call a phone number
  async function createSIPInvite(phoneNumber, roomName) {
    if (!phoneNumber || !roomName) {
      throw new Error("Phone number and room name are required for SIP invite");
    }

    try {
      // Get the participant identity
      const participantIdentity = localParticipant
        ? localParticipant.identity
        : `caller_${Date.now()}`;

      // Create a SIP participant to connect to the phone number
      const response = await fetch("/api/sip/create-participant", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("token")}`, // Assuming token is stored in localStorage
        },
        body: JSON.stringify({
          phoneNumber: phoneNumber,
          roomName: roomName,
          participantIdentity: participantIdentity,
          participantName: `SIP Call to ${phoneNumber}`,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(
          `Failed to create SIP participant: ${
            errorData.detail || response.statusText
          }`
        );
      }

      const sipParticipant = await response.json();
      console.log("SIP participant created:", sipParticipant);

      // Store SIP participant info for future reference
      window.activeSIPParticipant = sipParticipant;

      return sipParticipant;
    } catch (error) {
      console.error("Failed to create SIP invite:", error);
      throw error;
    }
  }

  // Publish local audio track to the room
  async function publishLocalAudio() {
    if (!room || !localParticipant) {
      throw new Error("No active room connection");
    }

    try {
      // Check if browser supports getUserMedia
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        console.error("Browser does not support getUserMedia API");

        // Connect without audio as a fallback
        console.log("Connecting without audio as a fallback");

        // Still allow the call to continue without audio input
        return;
      }

      // Request mic permissions and create local audio track
      try {
        console.log("Requesting microphone access...");

        // First check direct access to device
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
            // Try to ensure we get good audio levels
            channelCount: 1,
            sampleRate: 48000,
            sampleSize: 16,
          },
        });

        // Check if the stream has active audio tracks
        const audioTracks = stream.getAudioTracks();

        if (audioTracks.length === 0) {
          console.error("No audio tracks available in the media stream");
          throw new Error("No audio tracks available");
        }

        console.log("Microphone access granted:", audioTracks[0].label);
        console.log("Microphone settings:", audioTracks[0].getSettings());

        // Check if the track is actually getting audio
        const audioTrack = audioTracks[0];

        // Create audio track through LiveKit with the existing track
        console.log("Creating LiveKit audio track from microphone");
        const microphoneTrack = new LivekitClient.LocalAudioTrack(audioTrack, {
          name: "microphone",
        });

        // Publish track to room
        console.log("Publishing microphone track to room");
        localTrackPublication = await localParticipant.publishTrack(
          microphoneTrack
        );

        console.log("Local audio track published");

        // Add volume meter to verify audio is working
        setupAudioLevelMonitoring(microphoneTrack);
      } catch (micError) {
        console.error("Failed to access microphone:", micError);
        console.log("Continuing call without audio input");

        // Create a silent audio track as fallback
        if (LivekitClient.createDummyAudioTrack) {
          try {
            console.log("Creating silent audio track as fallback");
            const silentTrack = LivekitClient.createDummyAudioTrack();
            localTrackPublication = await localParticipant.publishTrack(
              silentTrack
            );
            console.log("Silent audio track published");
          } catch (fallbackError) {
            console.error("Failed to create fallback audio:", fallbackError);
          }
        }
      }
    } catch (error) {
      console.error("Failed to publish local audio track:", error);

      // Don't throw - allow call to continue without audio
      console.log("Continuing call without publishing audio");
    }
  }

  // Monitor audio levels to ensure microphone is working
  function setupAudioLevelMonitoring(audioTrack) {
    if (!audioTrack) return;

    try {
      // Create an audio context
      const audioContext = new (window.AudioContext ||
        window.webkitAudioContext)();

      // We need to get the media stream track from the LiveKit track
      const mediaStreamTrack = audioTrack.mediaStreamTrack;
      if (!mediaStreamTrack) {
        console.error("No media stream track available for monitoring");
        return;
      }

      // Create a MediaStream with the track
      const stream = new MediaStream([mediaStreamTrack]);

      // Create a source node from the stream
      const source = audioContext.createMediaStreamSource(stream);

      // Create an analyser node
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      const bufferLength = analyser.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);

      // Connect the source to the analyser
      source.connect(analyser);

      let silenceCounter = 0;
      const silenceThreshold = 5; // Number of consecutive silent samples before warning

      // Check audio levels periodically
      const interval = setInterval(() => {
        if (
          !audioTrack.isEnabled ||
          !audioTrack.mediaStreamTrack ||
          audioTrack.mediaStreamTrack.readyState !== "live"
        ) {
          console.log("Audio track no longer active, stopping monitoring");
          clearInterval(interval);
          return;
        }

        // Get frequency data
        analyser.getByteFrequencyData(dataArray);

        // Calculate average audio level
        let sum = 0;
        for (let i = 0; i < bufferLength; i++) {
          sum += dataArray[i];
        }
        const average = sum / bufferLength;

        // Update the debug panel with mic level if it exists
        const micLevelElement = document.getElementById("micLevel");
        if (micLevelElement) {
          micLevelElement.textContent = Math.round(average);
        }

        // Log audio level periodically (but not too often to avoid console spam)
        if (average > 5 || silenceCounter % 5 === 0) {
          console.log(`Current microphone audio level: ${Math.round(average)}`);
        }

        // Check for silence (very low audio levels)
        if (average < 5) {
          silenceCounter++;
          if (silenceCounter >= silenceThreshold) {
            console.warn(
              `Microphone might not be capturing audio - ${silenceCounter} consecutive silent samples detected`
            );

            // Show a notification to the user after extended silence
            if (
              silenceCounter === silenceThreshold ||
              silenceCounter % 10 === 0
            ) {
              // Optional: Notify user about potential microphone issue
              const event = new CustomEvent("audioIssueDetected", {
                detail: {
                  type: "silence",
                  message: "Microphone not detecting audio",
                },
              });
              window.dispatchEvent(event);
            }
          }
        } else {
          // Reset counter when audio is detected
          if (silenceCounter > 0) {
            console.log("Audio detected after silence");
            silenceCounter = 0;

            // Update debug panel
            const audioStatusElement = document.getElementById("audioStatus");
            if (audioStatusElement) {
              audioStatusElement.textContent = "Audio detected";
            }
          }
        }
      }, 1000);

      // Store the interval ID to clean up later
      audioTrack._monitoringInterval = interval;
    } catch (error) {
      console.error("Error setting up audio monitoring:", error);
      // Don't block the call if monitoring fails
    }
  }

  // Set up event listeners for room events
  function setupRoomEventListeners() {
    if (!room) return;

    // Room connection state change
    room.on(LivekitClient.RoomEvent.ConnectionStateChanged, (state) => {
      console.log("Room connection state changed:", state);
    });

    // Remote participant connected
    room.on(LivekitClient.RoomEvent.ParticipantConnected, (participant) => {
      console.log("Remote participant connected:", participant.identity);

      // Log detailed info about the participant
      console.log("Participant details:", {
        sid: participant.sid,
        identity: participant.identity,
        name: participant.name,
        metadata: participant.metadata,
      });
    });

    // Remote participant disconnected
    room.on(LivekitClient.RoomEvent.ParticipantDisconnected, (participant) => {
      console.log("Remote participant disconnected:", participant.identity);

      // If this was the PSTN participant, we should end the call
      if (
        participant.identity.startsWith("pstn_") ||
        participant.identity.startsWith("caller_")
      ) {
        console.log("PSTN/Caller participant disconnected - ending call");
        callHandler.endCall();

        // Dispatch event for main.js to handle UI updates
        console.log(
          "Dispatching callEnded event due to participant disconnect"
        );
        window.dispatchEvent(
          new CustomEvent("callEnded", {
            detail: {
              reason: "remoteHangup",
              participant: participant.identity,
            },
          })
        );
      }
    });

    // Track published - when remote participant publishes a track
    room.on(
      LivekitClient.RoomEvent.TrackPublished,
      (publication, participant) => {
        console.log(
          "Track published by participant:",
          participant.identity,
          "track kind:",
          publication.kind
        );

        // Automatically subscribe to track if it's not already subscribed
        if (!publication.isSubscribed) {
          console.log(
            `Subscribing to ${publication.kind} track from ${participant.identity}`
          );
          publication.setSubscribed(true);
        }
      }
    );

    // Track subscribed - when we receive audio from remote participant
    room.on(
      LivekitClient.RoomEvent.TrackSubscribed,
      (track, publication, participant) => {
        console.log(
          "Subscribed to track:",
          track.kind,
          "from participant:",
          participant.identity
        );

        if (track.kind === "audio") {
          // Check if the audio element exists
          if (!remoteAudioElement) {
            console.error("Remote audio element not found, creating one");
            remoteAudioElement = document.createElement("audio");
            remoteAudioElement.id = "remoteAudio";
            remoteAudioElement.autoplay = true;
            document.body.appendChild(remoteAudioElement);
          }

          // Attach remote audio to audio element
          try {
            console.log("Attaching remote audio track to audio element");
            track.attach(remoteAudioElement);

            // Set volume to maximum
            remoteAudioElement.volume = 1.0;

            // Try to automatically play audio
            remoteAudioElement
              .play()
              .then(() =>
                console.log("Remote audio playback started successfully")
              )
              .catch((error) => {
                console.error("Error playing remote audio:", error);

                // If autoplay failed, show a UI element to let user manually start audio
                alert("Please click OK to enable audio for this call");
                remoteAudioElement
                  .play()
                  .then(() =>
                    console.log(
                      "Remote audio playback started after user interaction"
                    )
                  )
                  .catch((e) =>
                    console.error(
                      "Still failed to play audio after user interaction:",
                      e
                    )
                  );
              });

            console.log("Remote audio attached to element");
          } catch (attachError) {
            console.error("Error attaching remote audio:", attachError);
          }

          // Setup audio level monitoring for remote audio
          if (track.audioLevel) {
            console.log(`Initial remote audio level: ${track.audioLevel}`);
          }

          // Monitor for audio changes
          track.on("audioLevelChanged", (level) => {
            if (level > 0.01) {
              // Only log when there's meaningful audio
              console.log(`Remote audio level: ${level.toFixed(3)}`);
            }
          });
        }
      }
    );

    // Track unsubscribed - when remote audio track is removed
    room.on(
      LivekitClient.RoomEvent.TrackUnsubscribed,
      (track, publication, participant) => {
        console.log(
          "Unsubscribed from track:",
          track.kind,
          "from participant:",
          participant.identity
        );

        if (track.kind === "audio") {
          track.detach();
        }
      }
    );

    // Room disconnected
    room.on(LivekitClient.RoomEvent.Disconnected, (reason) => {
      console.log("Disconnected from room, reason:", reason);

      // Clean up any audio elements
      if (remoteAudioElement) {
        console.log("Cleaning up remote audio element");
        const tracks = remoteAudioElement.srcObject?.getTracks() || [];
        tracks.forEach((track) => track.stop());
        remoteAudioElement.srcObject = null;
      }

      // Clear resources
      room = null;
      localParticipant = null;
      localTrackPublication = null;

      // Dispatch event for main.js to handle UI updates
      console.log(
        "Dispatching callEnded event due to room disconnect, reason:",
        reason
      );
      window.dispatchEvent(
        new CustomEvent("callEnded", {
          detail: { reason: "roomDisconnected", livekitReason: reason },
        })
      );
    });
  }

  // Listen for call ended events from the server
  window.addEventListener("callEnded", (event) => {
    if (room) {
      callHandler.endCall();
    }
  });

  // Expose callHandler to window
  window.callHandler = callHandler;
})();
