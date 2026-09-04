from flask import Flask, render_template
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
from models import db, User, Session

app = Flask(__name__)
app.config['SECRET_KEY'] = 'change-this-secret'

# IMPORTANT: replace 'yourpassword' below with the root password you set in MySQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:root@localhost/livementor'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()
    print("Database tables created successfully!")

CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

rooms = {}

@socketio.on('join')
def on_join(data):
    room = data['room']
    join_room(room)
    rooms.setdefault(room, set()).add(data['sid_name'])
    emit('user-joined', {'sid': data['sid_name']}, room=room, include_self=False)

@socketio.on('signal')
def on_signal(data):
    emit('signal', data, room=data['room'], include_self=False)

@socketio.on('leave')
def on_leave(data):
    room = data['room']
    leave_room(room)
    emit('user-left', {'sid': data['sid_name']}, room=room)

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)