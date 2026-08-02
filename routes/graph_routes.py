from flask import Blueprint, jsonify, request, session
from handlers.attack_graph import (
    get_graph_data, add_graph_node, remove_graph_node,
    reset_graph, auto_populate_from_scans
)

graph_bp = Blueprint('graph_routes', __name__)


from core import login_required, require_role


@graph_bp.route('/api/graph/data', methods=['GET'])
@login_required
def api_get_graph():
    session_id = session.get('session_id', 'default')
    return jsonify(get_graph_data(session_id))


@graph_bp.route('/api/graph/node/add', methods=['POST'])
@login_required
@require_role("admin", "analyst")
def api_add_node():
    data = request.get_json(silent=True) or {}
    label = data.get('label', '')
    node_type = data.get('node_type', 'ip')
    parent_id = data.get('parent_id', None)
    node_data = data.get('data', None)
    session_id = session.get('session_id', 'default')

    if not label:
        return jsonify({"status": "error", "message": "Label required."})

    result = add_graph_node(label, node_type, parent_id, node_data, session_id)
    return jsonify(result)


@graph_bp.route('/api/graph/node/remove', methods=['POST'])
@login_required
@require_role("admin", "analyst")
def api_remove_node():
    data = request.get_json(silent=True) or {}
    node_id = data.get('node_id', '')
    session_id = session.get('session_id', 'default')
    if not node_id:
        return jsonify({"status": "error", "message": "node_id required."})
    return jsonify(remove_graph_node(node_id, session_id))


@graph_bp.route('/api/graph/reset', methods=['POST'])
@login_required
@require_role("admin")
def api_reset_graph():
    data = request.get_json(silent=True) or {}
    session_id = session.get('session_id', 'default')
    return jsonify(reset_graph(session_id))


@graph_bp.route('/api/graph/auto', methods=['POST'])
@login_required
@require_role("admin", "analyst")
def api_auto_populate():
    data = request.get_json(silent=True) or {}
    target = data.get('target', '')
    session_id = session.get('session_id', 'default')
    if not target:
        return jsonify({"status": "error", "message": "Target required."})

    result = auto_populate_from_scans(target, session_id)
    return jsonify(result)
