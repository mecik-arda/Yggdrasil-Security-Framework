import os
import subprocess
import shutil
import json
import platform
import threading
import html
import re
import sqlite3
import shlex
import socket
import ipaddress
import secrets
import concurrent.futures
import uuid
import psutil
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory
from flask_cors import CORS

# Monkey-patch subprocess.Popen to track spawned processes per thread
original_popen = subprocess.Popen
ACTIVE_PROCESSES = {}

class TrackedPopen(original_popen):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        thread_id = threading.get_ident()
        if thread_id not in ACTIVE_PROCESSES:
            ACTIVE_PROCESSES[thread_id] = []
        ACTIVE_PROCESSES[thread_id].append(self)

subprocess.Popen = TrackedPopen
from flask_cors import CORS
from handlers import dispatch_handler
from handlers.ai_engine import (
    list_models, chat_completion, pull_model, remove_model, get_ai_profile_tiers,
    analyze_scan_output
)
from handlers.rag_engine import (
    check_rag_status, index_knowledge_base, query_knowledge,
    fetch_gtfobins_live
)
from handlers.agent_loop import (
    start_agent, get_agent_status, stop_agent, list_agent_sessions
)
from handlers.valkyrie_reporter import (
    generate_report, generate_report_from_agent, generate_report_from_terminals,
    markdown_to_html
)
from handlers.loki_engine import (
    mutate_payload, list_techniques, analyze_waf_response
)
from dotenv import load_dotenv
import sqlite3
import shlex
import socket
import ipaddress
import secrets
import concurrent.futures
load_dotenv()
import time

CURRENT_CPU = 0.0
def _cpu_monitor():
    global CURRENT_CPU
    psutil.cpu_percent(interval=None)
    while True:
        time.sleep(1)
        CURRENT_CPU = psutil.cpu_percent(interval=None)

_cpu_thread = threading.Thread(target=_cpu_monitor, daemon=True)
_cpu_thread.start()

app = Flask(__name__)
def load_translations():
    translations = {}
    lang_dir = os.path.join(os.path.dirname(__file__), 'translations')
    if os.path.exists(lang_dir):
        for file in os.listdir(lang_dir):
            if file.endswith('.json'):
                lang_code = file.split('.')[0]
                with open(os.path.join(lang_dir, file), 'r', encoding='utf-8') as f:
                    translations[lang_code] = json.load(f)
    return translations
TRANSLATIONS = load_translations()
def get_translation(key, **kwargs):
    lang = session.get('lang', 'en')
    text = TRANSLATIONS.get(lang, {}).get(key, key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError:
            pass
    return text
def generate_csrf_token():
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(32)
    return session['csrf_token']
@app.before_request
def before_request():
    app.jinja_env.globals.update(t=get_translation, csrf_token=generate_csrf_token)
    if request.method == "POST" and request.endpoint != "login":
        token = session.get('csrf_token')
        if not token or token != request.headers.get('X-CSRFToken'):
            from flask import jsonify
            return jsonify({'status': 'error', 'message': 'CSRF token missing or incorrect.'}), 403
app.secret_key = os.environ.get('SECRET_KEY')
if not app.secret_key:
    app.secret_key = secrets.token_hex(16)
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')
if not ADMIN_PASSWORD:
    ADMIN_PASSWORD = secrets.token_hex(8)
    print(f"\n[!] WARNING: ADMIN_PASSWORD not set in .env!")
    print(f"[!] A temporary password has been generated for this session: {ADMIN_PASSWORD}\n")
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function
def is_private_ip(ip_str):
    try:
        ip = ipaddress.ip_address(ip_str)
        return ip.is_private or ip.is_loopback
    except ValueError:
        return False
def validate_target(target):
    if not target:
        return True
    pattern = r'^[\w\.\-\:\@]+$'
    if not re.match(pattern, target):
        return False
    return True
def init_db():
    conn = sqlite3.connect('stats.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS stats
                 (id INTEGER PRIMARY KEY, total_scans INTEGER, last_target TEXT, active_tool TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS scan_history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT UNIQUE, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, tool TEXT, target TEXT, status TEXT, output TEXT)''')
    c.execute('SELECT COUNT(*) FROM stats')
    if c.fetchone()[0] == 0:
        c.execute('INSERT INTO stats (total_scans, last_target, active_tool) VALUES (0, "NONE", "IDLE")')
    conn.commit()
    conn.close()
init_db()
def get_db_stats():
    conn = sqlite3.connect('stats.db')
    c = conn.cursor()
    c.execute('SELECT total_scans, last_target, active_tool FROM stats WHERE id=1')
    row = c.fetchone()
    conn.close()
    return {'total_scans': row[0], 'last_target': row[1], 'active_tool': row[2]}
def update_db_stats(target, tool):
    conn = sqlite3.connect('stats.db')
    c = conn.cursor()
    c.execute('UPDATE stats SET total_scans = total_scans + 1, last_target = ?, active_tool = ? WHERE id=1', (target, tool))
    conn.commit()
    conn.close()

def log_scan_start(task_id, tool, target):
    try:
        conn = sqlite3.connect('stats.db')
        c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO scan_history (task_id, tool, target, status, output) VALUES (?, ?, ?, ?, ?)',
                  (task_id, tool.upper(), target, 'RUNNING', ''))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error logging scan start: {e}")

def log_scan_end(task_id, status, output):
    try:
        conn = sqlite3.connect('stats.db')
        c = conn.cursor()
        c.execute('UPDATE scan_history SET status = ?, output = ? WHERE task_id = ?',
                  (status, output, task_id))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error logging scan end: {e}")

WSL_CONFIG_FILE = 'wsl_config.json'
def get_wsl_distros():
    if platform.system() != 'Windows':
        return []
    try:
        output = subprocess.check_output(['wsl.exe', '--list', '--quiet'], stderr=subprocess.STDOUT)
        decoded = output.decode('utf-16le', errors='ignore').strip()
        return [d.strip() for d in decoded.split('\n') if d.strip()]
    except Exception:
        pass
    return []
def get_preferred_wsl():
    if os.path.exists(WSL_CONFIG_FILE):
        try:
            with open(WSL_CONFIG_FILE, 'r') as f:
                data = json.load(f)
                distro = data.get('wsl_distro')
                if distro in get_wsl_distros():
                    return distro
        except Exception:
            pass
    distros = get_wsl_distros()
    return distros[0] if distros else None
from tools_config import TOOLS_CONFIG
def check_tool_status(tool_key):
    config = TOOLS_CONFIG.get(tool_key, {})
    if not config:
        return False
    check_type = config.get('check_type')
    if check_type == 'runes_repo':
        check_path = config.get('check_path', '')
        if check_path.startswith('Runes/'):
            repo_name = check_path.split('/')[1]
            repo_path = os.path.join('Runes', repo_name)
            if not os.path.exists(os.path.join(repo_path, '.git')):
                return False
        binaries = config.get('check_binaries', [])
        if binaries:
            exe = '.exe' if platform.system() == 'Windows' else ''
            resolved = [b.format(exe=exe) for b in binaries]
            if not any(os.path.exists(b) for b in resolved):
                return False
        return True
    tool_bin = config.get('bin')
    if not tool_bin:
        check_path = config.get('check_path')
        if check_path:
            return os.path.exists(check_path)
        return True
    if shutil.which(tool_bin) is not None:
        return True
    if platform.system() == 'Windows':
        wsl = get_preferred_wsl()
        if wsl:
            try:
                subprocess.check_output(['wsl.exe', '-d', wsl, '-u', 'root', '-e', 'which', tool_bin], stderr=subprocess.DEVNULL)
                return True
            except Exception:
                pass
    return False
def install_tool_system(tool_key):
    config = TOOLS_CONFIG.get(tool_key, {})
    current_os = platform.system()
    is_wsl = False
    wsl_distro = None
    if current_os == "Windows":
        cmd = config.get('install_windows')
        if not cmd:
            cmd = config.get('install_linux')
            wsl_distro = get_preferred_wsl()
            if cmd and wsl_distro:
                is_wsl = True
    else:
        cmd = config.get('install_linux')
    if not cmd:
        supported = config.get('supported_os', [])
        if current_os.lower() not in supported:
            return False, f"Not natively supported on {current_os}. Manual installation (or WSL) required."
        return False, "Installation command not defined for this OS."
    try:
        cmd_list = shlex.split(cmd)
        if is_wsl:
            if cmd_list[0] == 'sudo':
                cmd_list = cmd_list[1:]
            cmd_list = ['wsl.exe', '-d', wsl_distro, '-u', 'root', '--'] + cmd_list
        output = subprocess.check_output(cmd_list, stderr=subprocess.STDOUT).decode('utf-8', errors='replace')
        return True, f"Installation output:\n{output}"
    except subprocess.CalledProcessError as e:
        return False, f"Installation failed:\n{e.output.decode('utf-8', errors='replace')}"
    except Exception as e:
        return False, f"Error: {str(e)}"
def get_pkg_name(cmd_str):
    parts = shlex.split(cmd_str)
    if 'apt-get' in parts or 'apt' in parts:
        return parts[parts.index('install') + 1] if 'install' in parts else parts[-1]
    if 'winget' in parts:
        return parts[parts.index('install') + 1] if 'install' in parts else parts[-1]
    if 'pip' in parts:
        return parts[parts.index('install') + 1] if 'install' in parts else parts[-1]
    if 'go' in parts and 'install' in parts:
        return parts[-1]
    return ""
def remove_tool_system(tool_key):
    config = TOOLS_CONFIG.get(tool_key, {})
    current_os = platform.system()
    check_path = config.get('check_path', '')
    check_type = config.get('check_type', 'default')
    if check_type == 'runes_repo':
        repo_name = check_path.split('/')[1]
        repo_path = os.path.join('Runes', repo_name)
        if os.path.exists(repo_path):
            try:
                def rm_error(func, path, exc_info):
                    os.chmod(path, 0o777)
                    func(path)
                shutil.rmtree(repo_path, onerror=rm_error)
                return True, f"Successfully removed {repo_name} repository."
            except Exception as e:
                return False, f"Failed to delete {repo_name}: {str(e)}"
        return False, f"Repository {repo_name} not found."
    is_wsl = False
    wsl_distro = None
    if current_os == "Windows":
        cmd = config.get('install_windows')
        if not cmd:
            cmd = config.get('install_linux')
            wsl_distro = get_preferred_wsl()
            if cmd and wsl_distro:
                is_wsl = True
    else:
        cmd = config.get('install_linux')
    if not cmd:
        return False, "Uninstallation command cannot be inferred (Install command missing)."
    pkg = get_pkg_name(cmd)
    if not pkg:
        return False, "Could not determine package name for removal."
    remove_cmd = []
    if 'apt-get' in cmd:
        remove_cmd = ['sudo', 'apt-get', 'remove', '-y', pkg]
    elif 'winget' in cmd:
        remove_cmd = ['winget', 'uninstall', pkg]
    elif 'pip' in cmd:
        remove_cmd = ['pip', 'uninstall', '-y', pkg]
    else:
        return False, f"Automated removal not supported for this installation type: {cmd}"
    if is_wsl:
        if remove_cmd[0] == 'sudo':
            remove_cmd = remove_cmd[1:]
        remove_cmd = ['wsl.exe', '-d', wsl_distro, '-u', 'root', '--'] + remove_cmd
    try:
        output = subprocess.check_output(remove_cmd, stderr=subprocess.STDOUT).decode('utf-8', errors='replace')
        return True, f"Removal output:\n{output}"
    except subprocess.CalledProcessError as e:
        return False, f"Removal failed:\n{e.output.decode('utf-8', errors='replace')}"
    except Exception as e:
        return False, f"Error: {str(e)}"
def update_tool_system(tool_key):
    config = TOOLS_CONFIG.get(tool_key, {})
    current_os = platform.system()
    check_path = config.get('check_path', '')
    check_type = config.get('check_type', 'default')
    if check_type == 'runes_repo':
        repo_name = check_path.split('/')[1]
        repo_path = os.path.join('Runes', repo_name)
        if os.path.exists(repo_path):
            try:
                subprocess.check_output(["git", "pull"], cwd=repo_path, stderr=subprocess.STDOUT)
                if tool_key == 'fenrir':
                    if current_os == 'Windows':
                        build_dir = os.path.join(repo_path, 'build')
                        if not os.path.exists(build_dir): os.makedirs(build_dir)
                        subprocess.check_output(["cmake", ".."], cwd=build_dir, stderr=subprocess.STDOUT)
                        subprocess.check_output(["cmake", "--build", ".", "--config", "Release"], cwd=build_dir, stderr=subprocess.STDOUT)
                    else:
                        subprocess.check_output(["make"], cwd=repo_path, stderr=subprocess.STDOUT)
                return True, f"Successfully updated {repo_name} from git repository."
            except subprocess.CalledProcessError as e:
                return False, f"Update failed for {repo_name}:\n{e.output.decode('utf-8', errors='replace')}"
            except Exception as e:
                return False, f"Update error for {repo_name}: {str(e)}"
        return False, f"Repository {repo_name} not found."
    is_wsl = False
    wsl_distro = None
    if current_os == "Windows":
        cmd = config.get('install_windows')
        if not cmd:
            cmd = config.get('install_linux')
            wsl_distro = get_preferred_wsl()
            if cmd and wsl_distro:
                is_wsl = True
    else:
        cmd = config.get('install_linux')
    if not cmd:
        return False, "Update command cannot be inferred."
    pkg = get_pkg_name(cmd)
    if not pkg:
        return False, "Could not determine package name for update."
    update_cmd = []
    if 'apt-get' in cmd:
        update_cmd = ['sudo', 'apt-get', '--only-upgrade', 'install', '-y', pkg]
    elif 'winget' in cmd:
        update_cmd = ['winget', 'upgrade', pkg]
    elif 'pip' in cmd:
        update_cmd = ['pip', 'install', '--upgrade', pkg]
    elif 'go' in cmd and 'install' in cmd:
        update_cmd = shlex.split(cmd) 
    else:
        return False, f"Automated update not supported for this installation type: {cmd}"
    if is_wsl:
        if update_cmd[0] == 'sudo':
            update_cmd = update_cmd[1:]
        update_cmd = ['wsl.exe', '-d', wsl_distro, '-u', 'root', '--'] + update_cmd
    try:
        output = subprocess.check_output(update_cmd, stderr=subprocess.STDOUT).decode('utf-8', errors='replace')
        return True, f"Update output:\n{output}"
    except subprocess.CalledProcessError as e:
        return False, f"Update failed:\n{e.output.decode('utf-8', errors='replace')}"
    except Exception as e:
        return False, f"Error: {str(e)}"
def check_runes_updates():
    runes_dir = "Runes"
    if not os.path.exists(runes_dir):
        return []
    def check_repo(item):
        repo_path = os.path.join(runes_dir, item)
        if os.path.isdir(repo_path) and os.path.exists(os.path.join(repo_path, ".git")):
            try:
                subprocess.check_output(["git", "fetch"], cwd=repo_path, stderr=subprocess.STDOUT)
                status = subprocess.check_output(["git", "status", "-uno"], cwd=repo_path, stderr=subprocess.STDOUT).decode("utf-8")
                if "Your branch is behind" in status or "git pull" in status:
                    return item
            except Exception:
                pass
        return None
    items = os.listdir(runes_dir)
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(check_repo, item) for item in items]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())
    return [r for r in results if r]
def background_update(runes_dir):
    for item in os.listdir(runes_dir):
        repo_path = os.path.join(runes_dir, item)
        if os.path.isdir(repo_path) and os.path.exists(os.path.join(repo_path, ".git")):
            try:
                status = subprocess.check_output(["git", "status", "-uno"], cwd=repo_path, stderr=subprocess.STDOUT).decode("utf-8")
                if "Your branch is behind" in status or "git pull" in status:
                    subprocess.check_output(["git", "pull"], cwd=repo_path, stderr=subprocess.STDOUT)
                    if "Network-Sniffer-Scanner-Java" in item:
                        mvn_cmd = "mvn.cmd" if platform.system() == "Windows" else "mvn"
                        subprocess.check_output([mvn_cmd, "clean", "install"], cwd=repo_path, stderr=subprocess.STDOUT)
            except Exception:
                pass
def apply_runes_updates():
    runes_dir = "Runes"
    if not os.path.exists(runes_dir):
        return "<p>Runes directory not found.</p>"
    thread = threading.Thread(target=background_update, args=(runes_dir,))
    thread.daemon = True
    thread.start()
    return "<div style='font-family: monospace;'><p style='color: #a3be8c;'>Updates started in the background. Tools will be synced shortly.</p></div>"
def execute_tool(tool_key, target, data=None):
    config = TOOLS_CONFIG.get(tool_key)
    if not config:
        return "Tool definition not found"
    tool_type = config.get('type')
    if tool_type == 'gui':
        try:
            current_os = platform.system()
            cmd_str = config.get('cmd_windows') if current_os == 'Windows' else config.get('cmd_linux')
            cwd = config.get('cwd', '.')
            log_path = config.get('log_file', 'launcher.log')
            log_file = open(log_path, "w")
            subprocess.Popen(cmd_str, shell=True, cwd=cwd, stdout=log_file, stderr=log_file)
            return f">> INITIATING GUI TOOL ({current_os.upper()} MODE)...\n>> PLEASE CHECK YOUR TASKBAR FOR THE NEW WINDOW."
        except Exception as e:
            return f"GUI Launch Error: {str(e)}"
    elif tool_type in ['cli', 'script']:
        cmd_template = config.get('cmd', [])
        cmd = [arg.format(target=target) if '{target}' in arg else arg for arg in cmd_template]
        current_os = platform.system()
        supported = config.get('supported_os', [])
        if current_os.lower() not in supported and current_os == 'Windows':
            wsl_distro = get_preferred_wsl()
            if wsl_distro:
                cmd = ['wsl.exe', '-d', wsl_distro, '-u', 'root', '--'] + cmd
        try:
            result = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=120).decode('utf-8', errors='replace')
            return result
        except subprocess.TimeoutExpired:
            return "TIMEOUT: Process took too long"
        except subprocess.CalledProcessError as e:
            return f"Execution Error:\n{e.output.decode('utf-8', errors='replace')}"
        except Exception as e:
            return f"System Error: {str(e)}"
    elif tool_type in ['custom_html', 'custom_script']:
        handler_name = config.get('handler')
        return dispatch_handler(handler_name, target, data)
    return "Unsupported tool type"
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('home'))
        else:
            return render_template('login.html', error="Parola hatalı! (Incorrect password)")
    return render_template('login.html')
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))
@app.route('/')
@login_required
def home():
    lang = session.get('lang', 'en')
    js_translations = TRANSLATIONS.get(lang, {})
    return render_template('index.html', js_translations=js_translations, current_lang=lang)
@app.route('/api/set_lang', methods=['POST'])
def set_lang():
    lang = request.json.get('lang', 'en')
    session['lang'] = lang
    return jsonify({'status': 'success', 'lang': lang})
@app.route('/api/tools', methods=['GET'])
@login_required
def get_tools():
    frontend_config = {}
    for key, val in TOOLS_CONFIG.items():
        frontend_config[key] = {
            'name': val.get('name'),
            'category': val.get('category'),
            'requires_target': val.get('requires_target'),
            'has_modal': val.get('has_modal', False)
        }
    return jsonify(frontend_config)
@app.route('/api/stats', methods=['GET'])
@login_required
def get_stats():
    return jsonify(get_db_stats())
@app.route('/api/dependencies', methods=['GET'])
@login_required
def get_dependencies():
    current_os = platform.system().lower()
    deps = []
    def process_tool(item):
        key, val = item
        if val.get('bin') or val.get('install_linux') or val.get('install_windows'):
            supported_os = val.get('supported_os', [])
            is_supported = current_os in supported_os if supported_os else True
            wsl_distro = get_preferred_wsl()
            is_wsl = False
            if not is_supported and current_os == 'windows' and wsl_distro and val.get('install_linux'):
                is_supported = True
                is_wsl = True
            return {
                'tool_key': key,
                'name': val.get('name', key),
                'installed': check_tool_status(key),
                'supported': is_supported,
                'is_wsl': is_wsl
            }
        return None
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        results = executor.map(process_tool, TOOLS_CONFIG.items())
    for r in results:
        if r:
            deps.append(r)
    return jsonify(deps)
@app.route('/api/wsl/distros', methods=['GET'])
@login_required
def api_wsl_distros():
    distros = get_wsl_distros()
    preferred = get_preferred_wsl()
    return jsonify({'distros': distros, 'preferred': preferred})
@app.route('/api/wsl/config', methods=['POST'])
@login_required
def api_wsl_config():
    distro = request.json.get('distro')
    if distro in get_wsl_distros() or not distro:
        with open(WSL_CONFIG_FILE, 'w') as f:
            json.dump({'wsl_distro': distro}, f)
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error', 'message': 'Invalid distro'})
import uuid
ASYNC_TASKS = {}
def run_async_task(task_id, tool, target, data, action):
    thread_id = threading.get_ident()
    ASYNC_TASKS[task_id]['thread_id'] = thread_id
    if action == 'run':
        log_scan_start(task_id, tool, target if target else 'SYSTEM')
    try:
        if action == 'run':
            target_val = target if target else 'NONE'
            update_db_stats(target_val, tool.upper())
            config = TOOLS_CONFIG.get(tool)
            if config and config.get('type') == 'custom_html':
                output = execute_tool(tool, target, data)
                type_val = 'html' if tool in ['google_dorks'] else 'text'
            else:
                output = execute_tool(tool, target, data)
                type_val = 'text'
            ASYNC_TASKS[task_id] = {'status': 'success', 'output': output, 'type': type_val}
            log_scan_end(task_id, 'SUCCESS', output)
        elif action == 'install':
            success, msg = install_tool_system(tool)
            ASYNC_TASKS[task_id] = {'status': 'success' if success else 'error', 'message': msg}
        elif action == 'update':
            success, msg = update_tool_system(tool)
            ASYNC_TASKS[task_id] = {'status': 'success' if success else 'error', 'message': msg}
        elif action == 'remove':
            success, msg = remove_tool_system(tool)
            ASYNC_TASKS[task_id] = {'status': 'success' if success else 'error', 'message': msg}
    except Exception as e:
        ASYNC_TASKS[task_id] = {'status': 'error', 'message': str(e)}
        if action == 'run':
            log_scan_end(task_id, 'ERROR', str(e))
    finally:
        if thread_id in ACTIVE_PROCESSES:
            del ACTIVE_PROCESSES[thread_id]
@app.route('/api/task_status', methods=['GET'])
@login_required
def get_task_status():
    task_id = request.args.get('task_id')
    task = ASYNC_TASKS.get(task_id)
    if not task:
        return jsonify({'status': 'error', 'message': 'Task not found'})
    return jsonify(task)

@app.route('/api/task_kill', methods=['POST'])
@login_required
def kill_task():
    task_id = request.form.get('task_id')
    task = ASYNC_TASKS.get(task_id)
    if not task:
        return jsonify({'status': 'error', 'message': 'Task not found'})
    
    thread_id = task.get('thread_id')
    processes = ACTIVE_PROCESSES.get(thread_id, [])
    
    killed = 0
    for p in processes:
        try:
            parent = psutil.Process(p.pid)
            for child in parent.children(recursive=True):
                try:
                    child.kill()
                except psutil.NoSuchProcess:
                    pass
            parent.kill()
            killed += 1
        except psutil.NoSuchProcess:
            pass
        except Exception as e:
            print(f"Error killing process {p.pid}: {e}")
            
    task['status'] = 'error'
    task['message'] = 'Task aborted by user.'
    if 'output' in task:
        task['output'] += "\n\n[!] PROCESS ABORTED BY USER."
    else:
        task['output'] = "[!] PROCESS ABORTED BY USER."
    
    log_scan_end(task_id, 'ABORTED', task['output'])
    return jsonify({'status': 'success', 'killed': killed})

@app.route('/api/task_kill_all', methods=['POST'])
@login_required
def task_kill_all():
    total_killed = 0
    for task_id, task in list(ASYNC_TASKS.items()):
        if task.get('status') == 'running':
            thread_id = task.get('thread_id')
            processes = ACTIVE_PROCESSES.get(thread_id, [])
            for p in processes:
                try:
                    parent = psutil.Process(p.pid)
                    for child in parent.children(recursive=True):
                        try:
                            child.kill()
                        except psutil.NoSuchProcess:
                            pass
                    parent.kill()
                    total_killed += 1
                except psutil.NoSuchProcess:
                    pass
                except Exception:
                    pass
            
            task['status'] = 'error'
            task['message'] = 'Aborted by Global Kill Switch.'
            if 'output' in task:
                task['output'] += "\n\n[!] PROCESS ABORTED BY GLOBAL KILL SWITCH."
            else:
                task['output'] = "[!] PROCESS ABORTED BY GLOBAL KILL SWITCH."
            
            log_scan_end(task_id, 'ABORTED', task['output'])
            
    return jsonify({'status': 'success', 'killed': total_killed})
@app.route('/api/action', methods=['POST'])
@login_required
def handle_action():
    data = request.form
    tool = data.get('tool')
    target = data.get('target')
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
        task_id = str(uuid.uuid4())
        ASYNC_TASKS[task_id] = {'status': 'running', 'tool': tool, 'target': target, 'action': action}
        thread = threading.Thread(target=run_async_task, args=(task_id, tool, target, data, action))
        thread.daemon = True
        thread.start()
        return jsonify({'status': 'pending', 'task_id': task_id})
    return jsonify({'status': 'error', 'message': 'Invalid action'})

@app.route('/api/system_resources', methods=['GET'])
@login_required
def system_resources():
    cpu = CURRENT_CPU
    ram = psutil.virtual_memory().percent
    
    # Fast network ping check
    ping_ms = None
    import time
    try:
        s_time = time.time()
        # Connect to a public DNS server
        socket.setdefaulttimeout(0.5)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("8.8.8.8", 53))
        s.close()
        ping_ms = int((time.time() - s_time) * 1000)
    except Exception:
        pass

    # Fast Ollama status check
    ollama_online = False
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("127.0.0.1", 11434))
        s.close()
        ollama_online = True
    except Exception:
        pass
    
    active_scans = []
    for task_id, task in list(ASYNC_TASKS.items()):
        if task.get('status') == 'running' and task.get('action') == 'run':
            thread_id = task.get('thread_id')
            pids = [p.pid for p in ACTIVE_PROCESSES.get(thread_id, [])]
            active_scans.append({
                'task_id': task_id,
                'tool': task.get('tool'),
                'target': task.get('target'),
                'pids': pids
            })
            
    return jsonify({
        'cpu': cpu,
        'ram': ram,
        'ping': ping_ms,
        'ollama': ollama_online,
        'active_scans': active_scans
    })

@app.route('/api/history', methods=['GET'])
@login_required
def get_history():
    try:
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

@app.route('/api/history/clear', methods=['POST'])
@login_required
def clear_history():
    try:
        conn = sqlite3.connect('stats.db')
        c = conn.cursor()
        c.execute('DELETE FROM scan_history')
        conn.commit()
        conn.close()
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})
@app.route('/api/ai/status', methods=['GET'])
@login_required
def ai_status():
    """Check if Ollama is reachable and return installed models."""
    result = list_models()
    return jsonify(result)
@app.route('/api/ai/chat', methods=['POST'])
@login_required
def ai_chat():
    """Send chat completion to local Ollama model."""
    data = request.get_json()
    model = data.get('model', 'qwen2.5-coder:7b')
    messages = data.get('messages', [])
    if not messages:
        return jsonify({'status': 'error', 'message': 'Mesaj gonderilmedi.'})
    result = chat_completion(model, messages)
    return jsonify(result)
@app.route('/api/ai/models', methods=['GET'])
@login_required
def ai_models():
    """List installed Ollama models and available tiers."""
    installed = list_models()
    tiers = get_ai_profile_tiers()
    return jsonify({
        'installed': installed,
        'tiers': tiers
    })
@app.route('/api/ai/pull', methods=['POST'])
@login_required
def ai_pull():
    """Pull (download) a model from Ollama registry."""
    data = request.get_json()
    model = data.get('model', '')
    if not model:
        return jsonify({'status': 'error', 'message': 'Model adi gerekli.'})
    result = pull_model(model)
    return jsonify(result)
@app.route('/api/ai/remove', methods=['POST'])
@login_required
def ai_remove():
    """Remove an installed Ollama model."""
    data = request.get_json()
    model = data.get('model', '')
    if not model:
        return jsonify({'status': 'error', 'message': 'Model adi gerekli.'})
    result = remove_model(model)
    return jsonify(result)
@app.route('/api/ai/disk', methods=['GET'])
@login_required
def ai_disk_usage():
    """Return Ollama model disk usage."""
    result = list_models()
    if result.get("status") != "success":
        return jsonify({"status": "error", "message": "Cannot retrieve model data."})
    models = result.get("models", [])
    total_bytes = sum(m.get("size", 0) for m in models)
    total_gb = total_bytes / (1024 ** 3)
    return jsonify({
        "status": "success",
        "total_models": len(models),
        "total_size_bytes": total_bytes,
        "total_size_gb": round(total_gb, 2),
        "models": [{"name": m["name"], "size_bytes": m.get("size", 0),
                     "size_gb": round(m.get("size", 0) / (1024 ** 3), 2)} for m in models]
    })
@app.route('/api/ai/tiers', methods=['GET'])
@login_required
def ai_tiers():
    """Return hardware tier recommendations."""
    return jsonify(get_ai_profile_tiers())
@app.route('/api/rag/status', methods=['GET'])
@login_required
def rag_status():
    """Check RAG engine status (ChromaDB, Ollama, collections)."""
    return jsonify(check_rag_status())
@app.route('/api/rag/index', methods=['POST'])
@login_required
def rag_index():
    """Index built-in knowledge base into ChromaDB."""
    result = index_knowledge_base()
    return jsonify(result)
@app.route('/api/rag/fetch', methods=['POST'])
@login_required
def rag_fetch():
    """Fetch latest GTFOBins data from GitHub."""
    result = fetch_gtfobins_live()
    return jsonify(result)
@app.route('/api/rag/query', methods=['POST'])
@login_required
def rag_query():
    """Query the RAG knowledge base."""
    data = request.get_json()
    query = data.get('query', '')
    collections = data.get('collections', None)
    top_k = data.get('top_k', 5)
    if not query or not query.strip():
        return jsonify({'status': 'error', 'message': 'Sorgu metni gerekli.'})
    result = query_knowledge(query.strip(), collections, top_k)
    return jsonify(result)
@app.route('/api/loki/mutate', methods=['POST'])
@login_required
def loki_mutate():
    """Mutate a payload using selected WAF evasion techniques."""
    data = request.get_json()
    payload = data.get('payload', '')
    techniques = data.get('techniques', None)
    count = data.get('count', 5)
    result = mutate_payload(payload, techniques, count)
    return jsonify(result)
@app.route('/api/loki/techniques', methods=['GET'])
@login_required
def loki_techniques():
    """List all available mutation techniques."""
    return jsonify(list_techniques())
@app.route('/api/loki/analyze', methods=['POST'])
@login_required
def loki_analyze_waf():
    """Analyze a WAF block response and suggest bypass strategies."""
    data = request.get_json()
    status_code = data.get('status_code', 403)
    response_body = data.get('response_body', '')
    result = analyze_waf_response(status_code, response_body)
    return jsonify(result)
@app.route('/api/ai/report', methods=['POST'])
@login_required
def ai_report():
    """
    Generate a security assessment report.
    Accepts JSON:
      - source: 'terminals' or 'agent_session'
      - terminals: [{tool, target, output, analysis}]
      - session_id: str (if source='agent_session')
    """
    data = request.get_json()
    source = data.get('source', 'terminals')
    if source == 'agent_session':
        session_id = data.get('session_id', '')
        if not session_id:
            return jsonify({'status': 'error', 'message': 'Session ID required.'})
        status = get_agent_status(session_id)
        if status.get('status') != 'success':
            return jsonify({'status': 'error', 'message': 'Agent session not found.'})
        report = generate_report_from_agent(status['session'])
    else:
        terminals = data.get('terminals', [])
        if not terminals:
            return jsonify({'status': 'error', 'message': 'No terminal data provided.'})
        report = generate_report_from_terminals(terminals)
    return jsonify({'status': 'success', 'report': report})
@app.route('/api/ai/report/html', methods=['POST'])
@login_required
def ai_report_html():
    """Generate report as standalone HTML (for print-to-PDF)."""
    data = request.get_json()
    source = data.get('source', 'terminals')
    if source == 'agent_session':
        session_id = data.get('session_id', '')
        status = get_agent_status(session_id)
        if status.get('status') != 'success':
            return jsonify({'status': 'error', 'message': 'Agent session not found.'})
        md_report = generate_report_from_agent(status['session'])
    else:
        terminals = data.get('terminals', [])
        if not terminals:
            return jsonify({'status': 'error', 'message': 'No terminal data provided.'})
        md_report = generate_report_from_terminals(terminals)
    html_report = markdown_to_html(md_report)
    return html_report, 200, {'Content-Type': 'text/html; charset=utf-8'}
@app.route('/api/agent/start', methods=['POST'])
@login_required
def agent_start():
    """Start an autonomous ReAct agent session on a target."""
    data = request.get_json()
    target = data.get('target', '')
    if not target:
        return jsonify({'status': 'error', 'message': 'Target is required.'})
    result = start_agent(target)
    return jsonify(result)
@app.route('/api/agent/status', methods=['GET'])
@login_required
def agent_status():
    """Get the current status of an agent session."""
    session_id = request.args.get('session_id', '')
    if not session_id:
        return jsonify({'status': 'error', 'message': 'Session ID required.'})
    result = get_agent_status(session_id)
    return jsonify(result)
@app.route('/api/agent/stop', methods=['POST'])
@login_required
def agent_stop():
    """Force-stop a running agent session."""
    data = request.get_json()
    session_id = data.get('session_id', '')
    if not session_id:
        return jsonify({'status': 'error', 'message': 'Session ID required.'})
    result = stop_agent(session_id)
    return jsonify(result)
@app.route('/api/agent/sessions', methods=['GET'])
@login_required
def agent_sessions():
    """List all agent sessions."""
    return jsonify(list_agent_sessions())
@app.route('/api/ai/analyze', methods=['POST'])
@login_required
def ai_analyze():
    """
    Heimdall Agent: Analyze raw tool output and return structured findings.
    Accepts JSON: {output, tool_name, target}
    """
    data = request.get_json()
    output = data.get('output', '')
    tool_name = data.get('tool_name', 'unknown')
    target = data.get('target', '')
    if not output or not output.strip():
        return jsonify({'status': 'error', 'message': 'Analiz icin cikti gerekli.'})
    result = analyze_scan_output(output, tool_name, target)
    return jsonify(result)
if __name__ == '__main__':
    host = os.environ.get('HOST', '127.0.0.1')
    app.run(host=host, port=5000, debug=False)
