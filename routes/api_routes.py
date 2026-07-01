from flask import Blueprint, jsonify, request, session
from core.task_manager import get_async_tasks, kill_task, kill_all_tasks
from core.db import log_scan_end
import psutil

api_bp = Blueprint('api', __name__)

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            from flask import redirect, url_for
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@api_bp.route('/api/task_status', methods=['GET'])
@login_required
def get_task_status():
    task_id = request.args.get('task_id')
    task = get_async_tasks().get(task_id)
    if not task:
        return jsonify({'status': 'error', 'message': 'Task not found'})
    
    # process objesini serialize etmemek icin copy alalim
    ret_task = {k: v for k, v in task.items() if k != 'process'}
    return jsonify(ret_task)

@api_bp.route('/api/task_kill', methods=['POST'])
@login_required
def api_kill_task():
    task_id = request.form.get('task_id')
    success, result = kill_task(task_id)
    if success:
        task = get_async_tasks().get(task_id)
        if task:
            log_scan_end(task_id, 'ABORTED', task.get('output', '[!] PROCESS ABORTED BY USER.'))
        return jsonify({'status': 'success', 'killed': result})
    return jsonify({'status': 'error', 'message': result})

@api_bp.route('/api/task_kill_all', methods=['POST'])
@login_required
def api_kill_all_tasks():
    total_killed = kill_all_tasks()
    return jsonify({'status': 'success', 'killed': total_killed})

@api_bp.route('/api/system_resources', methods=['GET'])
@login_required
def system_resources():
    import core.monitor as monitor
    cpu = monitor.CURRENT_CPU
    ram = psutil.virtual_memory().percent
    
    active_scans = []
    for task_id, task in list(get_async_tasks().items()):
        if task.get('status') == 'running' and task.get('action') == 'run':
            process = task.get('process')
            pids = [process.pid] if process else []
            active_scans.append({
                'task_id': task_id,
                'tool': task.get('tool'),
                'target': task.get('target'),
                'pids': pids
            })
            
    return jsonify({
        'cpu': cpu,
        'ram': ram,
        'ping': monitor.PING_MS,
        'ollama': monitor.OLLAMA_ONLINE,
        'active_scans': active_scans
    })

@api_bp.route('/api/history', methods=['GET'])
@login_required
def get_history():
    try:
        import sqlite3
        conn = sqlite3.connect('stats.db')
        c = conn.cursor()
        c.execute('SELECT id, timestamp, tool, target, status, output FROM scan_history ORDER BY id DESC LIMIT 30')
        rows = c.fetchall()
        conn.close()
        
        history = []
        for r in rows:
            history.append({
                'id': r[0],
                'timestamp': r[1],
                'tool': r[2],
                'target': r[3],
                'status': r[4],
                'output': r[5]
            })
        return jsonify(history)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@api_bp.route('/api/history/clear', methods=['POST'])
@login_required
def clear_history():
    try:
        import sqlite3
        conn = sqlite3.connect('stats.db')
        c = conn.cursor()
        c.execute('DELETE FROM scan_history')
        conn.commit()
        conn.close()
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@api_bp.route('/api/tools', methods=['GET'])
@login_required
def get_tools():
    from tools_config import TOOLS_CONFIG
    frontend_config = {}
    for key, val in TOOLS_CONFIG.items():
        frontend_config[key] = {
            'name': val.get('name'),
            'category': val.get('category'),
            'requires_target': val.get('requires_target'),
            'has_modal': val.get('has_modal', False)
        }
    return jsonify(frontend_config)

@api_bp.route('/api/stats', methods=['GET'])
@login_required
def get_stats():
    from core.db import get_db_stats
    return jsonify(get_db_stats())
