from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
from models import db, User, Session
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

db_password = os.getenv('DB_PASSWORD')
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://root:{db_password}@localhost/livementor'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()
    print("Database tables created successfully!")

CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    role = data.get('role')
    password = data.get('password')

    if not all([name, email, role, password]):
        return jsonify({'error': 'All fields are required'}), 400

    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({'error': 'Email already registered'}), 400

    new_user = User(name=name, email=email, role=role)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'Signup successful', 'user_id': new_user.id}), 201


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid email or password'}), 401

    return jsonify({
        'message': 'Login successful',
        'user_id': user.id,
        'name': user.name,
        'role': user.role
    }), 200


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