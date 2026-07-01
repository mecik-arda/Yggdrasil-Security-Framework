from flask import Blueprint, jsonify, request
from core.task_manager import create_task, get_async_tasks
from core.db import log_scan_start, update_db_stats, log_scan_end
from core.system_manager import sanitize_target, validate_target, check_tool_status, check_runes_updates, apply_runes_updates, install_tool_system, update_tool_system, remove_tool_system
from core.tool_runner import execute_tool
from tools_config import TOOLS_CONFIG
import threading

action_bp = Blueprint('action', __name__)

def login_required(f):
    from functools import wraps
    from flask import session, redirect, url_for
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def run_async_task(task_id, tool, target, data, action):
    tasks = get_async_tasks()
    
    if action == 'run':
        log_scan_start(task_id, tool, target if target else 'SYSTEM')
        
    try:
        if action == 'run':
            target_val = target if target else 'NONE'
            update_db_stats(target_val, tool.upper())
            config = TOOLS_CONFIG.get(tool)
            if config and config.get('type') == 'custom_html':
                output = execute_tool(tool, target, data, task_id=task_id)
                type_val = 'html' if tool in ['google_dorks'] else 'text'
            else:
                output = execute_tool(tool, target, data, task_id=task_id)
                type_val = 'text'
                
            tasks[task_id]['status'] = 'success'
            tasks[task_id]['output'] = output
            tasks[task_id]['type'] = type_val
            log_scan_end(task_id, 'SUCCESS', output)
            
        elif action == 'install':
            success, msg = install_tool_system(tool)
            tasks[task_id]['status'] = 'success' if success else 'error'
            tasks[task_id]['message'] = msg
            
        elif action == 'update':
            success, msg = update_tool_system(tool)
            tasks[task_id]['status'] = 'success' if success else 'error'
            tasks[task_id]['message'] = msg
            
        elif action == 'remove':
            success, msg = remove_tool_system(tool)
            tasks[task_id]['status'] = 'success' if success else 'error'
            tasks[task_id]['message'] = msg
            
    except Exception as e:
        tasks[task_id]['status'] = 'error'
        tasks[task_id]['message'] = str(e)
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
        task_id = create_task(tool, target, action)
        thread = threading.Thread(target=run_async_task, args=(task_id, tool, target, data, action))
        thread.daemon = True
        thread.start()
        return jsonify({'status': 'pending', 'task_id': task_id})
        
    return jsonify({'status': 'error', 'message': 'Invalid action'})
