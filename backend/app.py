from flask import Flask, render_template
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS

app = Flask(__name__)
app.config['SECRET_KEY'] = 'change-this-secret'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Track who is in which room
rooms = {}

@socketio.on('join')
def on_join(data):
    room = data['room']
    join_room(room)
    rooms.setdefault(room, set()).add(data['sid_name'])
    emit('user-joined', {'sid': data['sid_name']}, room=room, include_self=False)

@socketio.on('signal')
def on_signal(data):
    # Relay WebRTC offer/answer/ICE candidates to the other peer in the room
    emit('signal', data, room=data['room'], include_self=False)

@socketio.on('leave')
def on_leave(data):
    room = data['room']
    leave_room(room)
    emit('user-left', {'sid': data['sid_name']}, room=room)

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)