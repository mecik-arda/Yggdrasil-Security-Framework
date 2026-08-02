"""Phase 3: Log Dashboard API — query and manage centralized logs."""
from flask import Blueprint, jsonify, request
from core import login_required, require_role
from core.logger import get_recent_errors, get_recent_events, get_log_stats, clear_all_logs
from core.validation import bounded_integer

log_bp = Blueprint('log_routes', __name__)


@log_bp.route('/api/logs/errors', methods=['GET'])
@login_required
def api_get_errors():
    """GET /api/logs/errors?level=ERROR&tool=nmap&limit=50&since=2026-07-01T00:00:00"""
    level = request.args.get('level')
    tool = request.args.get('tool')
    limit = request.args.get('limit', 100)
    since = request.args.get('since')
    if since:
        try:
            from datetime import datetime
            datetime.fromisoformat(since.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            since = None

    limit = bounded_integer(limit, 'limit', minimum=1, maximum=500, default=100)
    errors = get_recent_errors(limit=limit, level=level, tool=tool, since=since)
    return jsonify({'status': 'success', 'errors': errors, 'count': len(errors)})


@log_bp.route('/api/logs/events', methods=['GET'])
@login_required
def api_get_events():
    """GET /api/logs/events?event_type=task_killed&limit=50&since=2026-07-01T00:00:00"""
    event_type = request.args.get('event_type')
    limit = request.args.get('limit', 100)
    since = request.args.get('since')
    if since:
        try:
            from datetime import datetime
            datetime.fromisoformat(since.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            since = None

    limit = bounded_integer(limit, 'limit', minimum=1, maximum=500, default=100)
    events = get_recent_events(limit=limit, event_type=event_type, since=since)
    return jsonify({'status': 'success', 'events': events, 'count': len(events)})


@log_bp.route('/api/logs/stats', methods=['GET'])
@login_required
def api_get_stats():
    """GET /api/logs/stats — summary counts for the dashboard badge row."""
    stats = get_log_stats()
    return jsonify({'status': 'success', 'stats': stats})


@log_bp.route('/api/logs/clear', methods=['POST'])
@login_required
@require_role("admin")
def api_clear_logs():
    """POST /api/logs/clear — delete all log entries."""
    clear_all_logs()
    return jsonify({'status': 'success', 'message': 'All logs cleared.'})
