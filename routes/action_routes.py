from flask import Blueprint, jsonify, request
from core.task_manager import create_task, get_async_tasks, get_task_manager
from core.db import log_scan_start, update_db_stats, log_scan_end
from core.system_manager import sanitize_target, validate_target, check_tool_status, check_runes_updates, apply_runes_updates, install_tool_system, update_tool_system, remove_tool_system
from core.tool_runner import execute_tool, execute_tool_streaming
from core.logger import get_logger
from tools_config import TOOLS_CONFIG

try:
    from routes.team_routes import socketio, SOCKETIO_AVAILABLE
except ImportError:
    socketio = None
    SOCKETIO_AVAILABLE = False

action_bp = Blueprint('action', __name__)


from core.auth import login_required


def _emit_event(event_name, data):
    """Emit a SocketIO event if available."""
    try:
        if SOCKETIO_AVAILABLE and socketio:
            socketio.emit(event_name, data)
    except Exception as e:
        get_logger('action_routes').warning(
            f'SocketIO emit failed for event {event_name}',
            extra={'tool': data.get('tool'), 'target': data.get('target')},
        )


def _emit_stats_update():
    """Trigger stats push on db change."""
    try:
        if SOCKETIO_AVAILABLE and socketio:
            from core.db import get_db_stats
            socketio.emit('stats_update', get_db_stats())
    except Exception as e:
        get_logger('action_routes').warning('SocketIO stats_update emit failed')


def _notify_team(event_name, tool, target, status=None):
    """Forward event to team_server notification system."""
    try:
        from handlers.team_server import (
            notify_scan_start, notify_scan_complete,
        )
        if event_name == 'scan_started':
            notify_scan_start(tool, target)
        elif event_name == 'scan_completed':
            notify_scan_complete(tool, target, status or 'UNKNOWN')
    except Exception as e:
        get_logger('action_routes').warning(
            f'Team notify failed for {event_name}',
            extra={'tool': tool, 'target': target},
        )


def run_async_task(task_id, tool, target, data, action):
    manager = get_task_manager()
    task_obj = manager.get_task(task_id)

    if action == 'run':
        log_scan_start(task_id, tool, target if target else 'SYSTEM')
        _emit_event('scan_start', {
            'task_id': task_id, 'tool': tool, 'target': target or 'SYSTEM',
        })
        _notify_team('scan_started', tool, target)

    try:
        if action == 'run':
            target_val = target if target else 'NONE'
            update_db_stats(target_val, tool.upper())
            _emit_stats_update()
            config = TOOLS_CONFIG.get(tool)

            def _on_output(line):
                _emit_event('scan_output', {
                    'task_id': task_id, 'tool': tool, 'line': line,
                })

            if config and config.get('type') == 'custom_html':
                output = execute_tool(tool, target, data, task_id=task_id)
                type_val = 'html'
                trusted = True  # custom_html handlers are considered trusted (static templates)
                # Do NOT emit HTML line by line as that triggers text escaping in frontend.
                # Instead, we skip scan_output and let scan_complete deliver the full HTML.
            else:
                output = execute_tool_streaming(tool, target, _on_output, data, task_id=task_id)
                type_val = 'text'
                trusted = False

            if task_obj:
                task_obj.status = 'success'
                task_obj.output = output
                task_obj.type = type_val
            log_scan_end(task_id, 'SUCCESS', output)
            _emit_event('scan_complete', {
                'task_id': task_id, 'tool': tool, 'output': output, 'type': type_val, 'trusted_source': trusted,
            })
            _notify_team('scan_completed', tool, target, 'SUCCESS')

        elif action == 'install':
            success, msg = install_tool_system(tool)
            if task_obj:
                task_obj.status = 'success' if success else 'error'
                task_obj.message = msg

        elif action == 'update':
            success, msg = update_tool_system(tool)
            if task_obj:
                task_obj.status = 'success' if success else 'error'
                task_obj.message = msg

        elif action == 'remove':
            success, msg = remove_tool_system(tool)
            if task_obj:
                task_obj.status = 'success' if success else 'error'
                task_obj.message = msg

    except Exception as e:
        get_logger('action_routes').error(
            f'Task execution failed: {e}',
            extra={'tool': tool, 'target': target or 'NONE', 'task_id': task_id},
            exc_info=True,
        )
        if task_obj:
            task_obj.status = 'error'
            task_obj.message = str(e)
        _emit_event('scan_error', {
            'task_id': task_id, 'tool': tool, 'error': str(e),
        })
        if action == 'run':
            log_scan_end(task_id, 'ERROR', str(e))


@action_bp.route('/api/action', methods=['POST'])
@login_required
def handle_action():
    data = request.form
    tool = data.get('tool')
    target = data.get('target')
    if target:
        target = sanitize_target(target)
    action = data.get('action')

    if not validate_target(target):
        return jsonify({'status': 'error', 'message': '>> INVALID TARGET. BANNED CHARACTERS DETECTED.'})

    if action == 'check':
        exists = check_tool_status(tool)
        return jsonify({'status': 'installed' if exists else 'missing'})
    elif action == 'check_updates':
        updates = check_runes_updates()
        return jsonify({'status': 'success', 'updates': updates})
    elif action == 'apply_updates':
        output = apply_runes_updates()
        return jsonify({'status': 'success', 'output': output, 'type': 'html'})
    elif action in ['run', 'install', 'update', 'remove']:
        client_task_id = data.get('task_id')
        task_id = create_task(tool, target, action, client_task_id=client_task_id)
        get_task_manager().submit(task_id, run_async_task, task_id, tool, target, data, action)
        return jsonify({'status': 'pending', 'task_id': task_id})

    return jsonify({'status': 'error', 'message': 'Invalid action'})
