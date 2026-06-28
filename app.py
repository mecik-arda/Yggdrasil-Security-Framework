import os
import subprocess
import shutil
import json
import platform
import threading
import html
import re
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from handlers import dispatch_handler
from dotenv import load_dotenv
import sqlite3
import shlex
import socket
import ipaddress
import secrets
import concurrent.futures

load_dotenv()

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
    # Allows IPv4, IPv6, Domains, and none
    if not target or target.lower() == 'none':
        return True
    pattern = r'^[\w\.\-\:]+$'
    if not re.match(pattern, target):
        return False
        
    # We do NOT block private IPs here because Yggdrasil is a network 
    # scanning framework meant to target local subnets and localhost.
    return True

def init_db():
    conn = sqlite3.connect('stats.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS stats
                 (id INTEGER PRIMARY KEY, total_scans INTEGER, last_target TEXT, active_tool TEXT)''')
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

from tools_config import TOOLS_CONFIG

def check_tool_status(tool_key):
    config = TOOLS_CONFIG.get(tool_key, {})
    if not config:
        return False
        
    if tool_key == 'fenrir':
        exe = '.exe' if platform.system() == 'Windows' else ''
        path1 = os.path.join('Runes', 'fenrir-hash-cracker', 'build', f'fenrir{exe}')
        path2 = os.path.join('Runes', 'fenrir-hash-cracker', 'build', 'Release', f'fenrir{exe}')
        has_git = os.path.exists(os.path.join('Runes', 'fenrir-hash-cracker', '.git'))
        return has_git and (os.path.exists(path1) or os.path.exists(path2))
        
    tool_bin = config.get('bin')
    if not tool_bin:
        check_path = config.get('check_path')
        if check_path:
            if check_path.startswith('Runes/'):
                repo_path = os.path.join('Runes', check_path.split('/')[1])
                if not os.path.exists(os.path.join(repo_path, '.git')):
                    return False
            return os.path.exists(check_path)
        return True
    return shutil.which(tool_bin) is not None

def install_tool_system(tool_key):
    config = TOOLS_CONFIG.get(tool_key, {})
    current_os = platform.system()
    
    if current_os == "Windows":
        cmd = config.get('install_windows')
    else:
        cmd = config.get('install_linux')
        
    if not cmd:
        supported = config.get('supported_os', [])
        if current_os.lower() not in supported:
            return False, f"Not natively supported on {current_os}. Manual installation (or WSL) required."
        return False, "Installation command not defined for this OS."

    try:
        cmd_list = shlex.split(cmd)
        output = subprocess.check_output(cmd_list, stderr=subprocess.STDOUT).decode('utf-8')
        return True, f"Installation output:\n{output}"
    except subprocess.CalledProcessError as e:
        return False, f"Installation failed:\n{e.output.decode('utf-8')}"
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
    if check_path.startswith('Runes/') or tool_key == 'fenrir':
        repo_name = 'fenrir-hash-cracker' if tool_key == 'fenrir' else check_path.split('/')[1]
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
        
    cmd = config.get('install_windows') if current_os == "Windows" else config.get('install_linux')
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
        
    try:
        output = subprocess.check_output(remove_cmd, stderr=subprocess.STDOUT).decode('utf-8')
        return True, f"Removal output:\n{output}"
    except subprocess.CalledProcessError as e:
        return False, f"Removal failed:\n{e.output.decode('utf-8')}"
    except Exception as e:
        return False, f"Error: {str(e)}"

def update_tool_system(tool_key):
    config = TOOLS_CONFIG.get(tool_key, {})
    current_os = platform.system()
    
    check_path = config.get('check_path', '')
    if check_path.startswith('Runes/') or tool_key == 'fenrir':
        repo_name = 'fenrir-hash-cracker' if tool_key == 'fenrir' else check_path.split('/')[1]
        repo_path = os.path.join('Runes', repo_name)
        if os.path.exists(os.path.join(repo_path, '.git')):
            try:
                output = subprocess.check_output(['git', 'pull'], cwd=repo_path, stderr=subprocess.STDOUT).decode('utf-8')
                
                if tool_key == 'fenrir':
                    if current_os == 'Windows':
                        subprocess.check_call(['cmake', '..'], cwd=os.path.join(repo_path, 'build'))
                        subprocess.check_call(['cmake', '--build', '.', '--config', 'Release'], cwd=os.path.join(repo_path, 'build'))
                    else:
                        subprocess.check_call(['cmake', '..'], cwd=os.path.join(repo_path, 'build'))
                        subprocess.check_call(['make'], cwd=os.path.join(repo_path, 'build'))
                    output += "\nRecompiled Fenrir successfully."
                    
                return True, f"Update output:\n{output}"
            except subprocess.CalledProcessError as e:
                return False, f"Update failed:\n{e.output.decode('utf-8') if e.output else str(e)}"
        return False, f"Repository {repo_name} not found or not a git repository."

    cmd = config.get('install_windows') if current_os == "Windows" else config.get('install_linux')
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
        
    try:
        output = subprocess.check_output(update_cmd, stderr=subprocess.STDOUT).decode('utf-8')
        return True, f"Update output:\n{output}"
    except subprocess.CalledProcessError as e:
        return False, f"Update failed:\n{e.output.decode('utf-8')}"
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
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(check_repo, items)
        
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
        try:
            result = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=120).decode('utf-8')
            return result
        except subprocess.TimeoutExpired:
            return "TIMEOUT: Process took too long"
        except subprocess.CalledProcessError as e:
            return f"Execution Error:\n{e.output.decode('utf-8')}"
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
    for key, val in TOOLS_CONFIG.items():
        if val.get('bin') or val.get('install_linux') or val.get('install_windows'):
            supported_os = val.get('supported_os', [])
            is_supported = current_os in supported_os if supported_os else True
            deps.append({
                'tool_key': key,
                'name': val.get('name', key),
                'installed': check_tool_status(key),
                'supported': is_supported
            })
    return jsonify(deps)

@app.route('/api/action', methods=['POST'])
@login_required
def handle_action():
    data = request.form
    tool = data.get('tool')
    target = data.get('target')
    action = data.get('action')

    # Validate target for SSRF/Argument Injection protection
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

    elif action == 'install':
        success, msg = install_tool_system(tool)
        return jsonify({'status': 'success' if success else 'error', 'message': msg})

    elif action == 'update':
        success, msg = update_tool_system(tool)
        return jsonify({'status': 'success' if success else 'error', 'message': msg})

    elif action == 'remove':
        success, msg = remove_tool_system(tool)
        return jsonify({'status': 'success' if success else 'error', 'message': msg})

    elif action == 'run':
        target_val = target if target else 'NONE'
        update_db_stats(target_val, tool.upper())
        
        config = TOOLS_CONFIG.get(tool)
        if config and config.get('type') == 'custom_html':
            output = execute_tool(tool, target, data)
            return jsonify({'status': 'success', 'output': output, 'type': 'html' if tool in ['google_dorks'] else 'text'})
            
        output = execute_tool(tool, target, data)
        return jsonify({'status': 'success', 'output': output, 'type': 'text'})

    return jsonify({'status': 'error', 'message': 'Invalid action'})

if __name__ == '__main__':
    # Listen on localhost by default for security, can be overridden with environment variables if desired
    host = os.environ.get('HOST', '127.0.0.1')
    app.run(host=host, port=5000, debug=False)
