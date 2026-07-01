from flask import Blueprint, jsonify, request, session
from handlers.team_server import (
    register_user, remove_user, get_user_list,
    add_team_message, get_team_messages,
    register_event_handler, broadcast_event
)
import json

team_bp = Blueprint('team_routes', __name__)

try:
    from flask_socketio import SocketIO, emit
    socketio = SocketIO(cors_allowed_origins="*", async_mode="threading")
    SOCKETIO_AVAILABLE = True
except ImportError:
    socketio = None
    SOCKETIO_AVAILABLE = False


def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            from flask import redirect, url_for
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


@team_bp.route('/api/team/users', methods=['GET'])
@login_required
def api_team_users():
    return jsonify({"status": "success", "users": get_user_list()})


@team_bp.route('/api/team/messages', methods=['GET'])
@login_required
def api_team_messages():
    since = request.args.get('since', 0, type=float)
    return jsonify({"status": "success", "messages": get_team_messages(since)})


@team_bp.route('/api/team/message', methods=['POST'])
@login_required
def api_team_message_post():
    data = request.get_json()
    message = data.get('message', '')
    if not message:
        return jsonify({"status": "error", "message": "Message required."})

    username = session.get('username', 'operator')
    result = add_team_message(username, message)
    return jsonify(result)


@team_bp.route('/api/team/broadcast', methods=['POST'])
@login_required
def api_team_broadcast():
    data = request.get_json()
    event = data.get('event', '')
    payload = data.get('data', {})
    if not event:
        return jsonify({"status": "error", "message": "Event name required."})

    broadcast_event(event, payload)
    return jsonify({"status": "success"})


@team_bp.route('/api/team/status', methods=['GET'])
@login_required
def api_team_status():
    return jsonify({
        "status": "success",
        "websocket_available": SOCKETIO_AVAILABLE,
        "users_online": len(get_user_list()),
        "team_mode": True
    })


if SOCKETIO_AVAILABLE:
    @socketio.on('connect')
    def handle_connect():
        username = session.get('username', 'operator')
        register_user(request.sid, username)
        emit('connected', {'username': username})


    @socketio.on('disconnect')
    def handle_disconnect():
        remove_user(request.sid)


    @socketio.on('team_message')
    def handle_team_message(data):
        message = data.get('message', '')
        if message:
            username = session.get('username', 'operator')
            add_team_message(request.sid, message)
            emit('team_message', {'username': username, 'message': message, 'time': __import__('time').time()}, broadcast=True)


    @socketio.on('subscribe')
    def handle_subscribe(data):
        data.get('channel', 'all')
        handler_id = str(id(request.sid))
        register_event_handler(handler_id, lambda payload: emit('event', json.loads(payload)) if isinstance(payload, str) else emit('event', payload))
