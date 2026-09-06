const socket = io("http://localhost:5000");
const room = localStorage.getItem('roomCode') || "session-101";
const myId = Math.random().toString(36).substring(2, 8);

let localStream;
let peerConnection;
let isCaller = false;
let mediaRecorder;
let recordedChunks = [];

const config = {
  iceServers: [{ urls: "stun:stun.l.google.com:19302" }]
};

const localVideo = document.getElementById("localVideo");
const remoteVideo = document.getElementById("remoteVideo");

document.getElementById("startBtn").onclick = startCall;
document.getElementById("hangupBtn").onclick = hangUp;

socket.emit("join", { room, sid_name: myId });

// If someone else joins after me, I become the caller and initiate the offer
socket.on("user-joined", async () => {
  if (localStream) {
    isCaller = true;
    await createOffer();
  }
});

async function startCall() {
  localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
  localVideo.srcObject = localStream;
  
   // Start recording audio for later transcription
  recordedChunks = [];
  const audioOnlyStream = new MediaStream(localStream.getAudioTracks());
  let recorderOptions = { mimeType: 'audio/webm;codecs=opus' };
  if (!MediaRecorder.isTypeSupported(recorderOptions.mimeType)) {
    recorderOptions = {};
  }
  mediaRecorder = new MediaRecorder(audioOnlyStream, recorderOptions);
  mediaRecorder.ondataavailable = (event) => {
    if (event.data.size > 0) recordedChunks.push(event.data);
  };
  mediaRecorder.start();


  peerConnection = new RTCPeerConnection(config);
  localStream.getTracks().forEach(track => peerConnection.addTrack(track, localStream));

  peerConnection.ontrack = (event) => {
    remoteVideo.srcObject = event.streams[0];
  };

  peerConnection.onicecandidate = (event) => {
    if (event.candidate) {
      socket.emit("signal", { room, type: "ice", candidate: event.candidate });
    }
  };
}

async function createOffer() {
  const offer = await peerConnection.createOffer();
  await peerConnection.setLocalDescription(offer);
  socket.emit("signal", { room, type: "offer", offer });
}

socket.on("signal", async (data) => {
  if (data.type === "offer" && !isCaller) {
    if (!peerConnection) await startCall();
    await peerConnection.setRemoteDescription(new RTCSessionDescription(data.offer));
    const answer = await peerConnection.createAnswer();
    await peerConnection.setLocalDescription(answer);
    socket.emit("signal", { room, type: "answer", answer });
  }
  if (data.type === "answer" && isCaller) {
    if (peerConnection.signalingState !== "stable") {
      await peerConnection.setRemoteDescription(new RTCSessionDescription(data.answer));
    }
  }
  if (data.type === "ice" && peerConnection) {
    try {
      await peerConnection.addIceCandidate(new RTCIceCandidate(data.candidate));
    } catch (e) {
      console.error("Error adding ICE candidate", e);
    }
  }
});


function hangUp() {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop();
    mediaRecorder.onstop = () => {
      const audioBlob = new Blob(recordedChunks, { type: 'audio/webm' });
      uploadRecording(audioBlob);
    };
  }
  if (peerConnection) {
    peerConnection.close();
    peerConnection = null;
  }
  if (localStream) {
    localStream.getTracks().forEach(track => track.stop());
  }
  localVideo.srcObject = null;
  remoteVideo.srcObject = null;
  isCaller = false;
  socket.emit("leave", { room, sid_name: myId });
}


async function uploadRecording(audioBlob) {
  const formData = new FormData();
  formData.append('audio', audioBlob, 'session-recording.webm');
  formData.append('room', room);

  try {
    const response = await fetch('http://127.0.0.1:5000/upload-recording', {
      method: 'POST',
      body: formData
    });
    const data = await response.json();
    console.log('Recording uploaded:', data);
    alert('Session recording saved! Processing summary...');
  } catch (err) {
    console.error('Failed to upload recording:', err);
  }
}