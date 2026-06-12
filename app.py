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

load_dotenv()

app = Flask(__name__)

app.secret_key = os.environ.get('SECRET_KEY')
if not app.secret_key:
    import secrets
    app.secret_key = secrets.token_hex(16)

ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')
if not ADMIN_PASSWORD:
    print("WARNING: ADMIN_PASSWORD not set in .env! Using fallback for dev. Do NOT use in production.")
    ADMIN_PASSWORD = "yggdrasil2026"

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
        
    # SSRF Protection
    try:
        resolved_ip = socket.gethostbyname(target)
        if is_private_ip(resolved_ip):
            return False
    except socket.gaierror:
        pass
        
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

TOOLS_CONFIG = {
    'nmap': {'name': 'Nmap (Full Scan)', 'category': 'active_scanning', 'requires_target': True, 'type': 'cli', 'bin': 'nmap', 'install_linux': 'sudo apt-get install nmap -y', 'install_windows': 'winget install Insecure.Nmap', 'supported_os': ['linux', 'windows'], 'cmd': ['nmap', '-sV', '-F', '--version-light', '{target}']},
    'erebus': {'name': 'Erebus Scanner (Rust)', 'category': 'erebus_scanner', 'requires_target': True, 'type': 'custom_script', 'handler': 'erebus_scan', 'has_modal': True, 'bin': 'cargo', 'install_linux': 'sudo apt-get install cargo -y', 'install_windows': 'winget install Rustlang.Rustup', 'supported_os': ['linux', 'windows']},
    'whois': {'name': 'WHOIS Lookup', 'category': 'passive_recon', 'requires_target': True, 'type': 'cli', 'bin': 'whois', 'install_linux': 'sudo apt-get install whois -y', 'install_windows': 'winget install Microsoft.Sysinternals.WhoIs', 'supported_os': ['linux', 'windows'], 'cmd': ['whois', '{target}']},
    'dnsenum': {'name': 'DNS Enum', 'category': 'dns_subdomain', 'requires_target': True, 'type': 'cli', 'bin': 'dnsenum', 'install_linux': 'sudo apt-get install dnsenum -y', 'install_windows': '', 'supported_os': ['linux'], 'cmd': ['dnsenum', '--noreverse', '{target}']},
    'sublist3r': {'name': 'Sublist3r', 'category': 'dns_subdomain', 'requires_target': True, 'type': 'cli', 'bin': 'sublist3r', 'install_linux': 'sudo apt-get install sublist3r -y', 'install_windows': 'pip install sublist3r', 'supported_os': ['linux', 'windows'], 'cmd': ['sublist3r', '-d', '{target}']},
    'theharvester': {'name': 'The Harvester', 'category': 'passive_recon', 'requires_target': True, 'type': 'cli', 'bin': 'theHarvester', 'install_linux': 'sudo apt-get install theharvester -y', 'install_windows': 'pip install theHarvester', 'supported_os': ['linux', 'windows'], 'cmd': ['theHarvester', '-d', '{target}', '-l', '100', '-b', 'all']},
    'wafw00f': {'name': 'WAF Detection', 'category': 'active_scanning', 'requires_target': True, 'type': 'cli', 'bin': 'wafw00f', 'install_linux': 'sudo apt-get install wafw00f -y', 'install_windows': 'pip install wafw00f', 'supported_os': ['linux', 'windows'], 'cmd': ['wafw00f', '{target}']},
    'dnsrecon': {'name': 'DNS Recon', 'category': 'dns_subdomain', 'requires_target': True, 'type': 'cli', 'bin': 'dnsrecon', 'install_linux': 'sudo apt-get install dnsrecon -y', 'install_windows': 'pip install dnsrecon', 'supported_os': ['linux', 'windows'], 'cmd': ['dnsrecon', '-d', '{target}']},
    'dig': {'name': 'Dig (DNS Utils)', 'category': 'dns_subdomain', 'requires_target': True, 'type': 'cli', 'bin': 'dig', 'install_linux': 'sudo apt-get install dnsutils -y', 'install_windows': 'winget install ISC.BIND', 'supported_os': ['linux', 'windows'], 'cmd': ['dig', 'ANY', '{target}']},
    'searchsploit': {'name': 'Exploit-DB Search', 'category': 'vulnerability', 'requires_target': True, 'type': 'cli', 'bin': 'searchsploit', 'install_linux': 'sudo apt-get install exploitdb -y', 'install_windows': '', 'supported_os': ['linux'], 'cmd': ['searchsploit', '{target}']},
    'wireshark': {'name': 'Packet Sniffer', 'category': 'active_scanning', 'requires_target': True, 'type': 'cli', 'bin': 'tshark', 'install_linux': 'sudo apt-get install tshark -y', 'install_windows': 'winget install WiresharkFoundation.Wireshark', 'supported_os': ['linux', 'windows'], 'cmd': ['tshark', '-c', '5', '-i', 'any']},
    'nikto': {'name': 'Nikto Web Scan', 'category': 'active_scanning', 'requires_target': True, 'type': 'cli', 'bin': 'nikto', 'install_linux': 'sudo apt-get install nikto -y', 'install_windows': '', 'supported_os': ['linux'], 'cmd': ['nikto', '-h', '{target}', '-Tuning', '1']},
    'wpscan': {'name': 'WPScan (WordPress)', 'category': 'active_scanning', 'requires_target': True, 'type': 'cli', 'bin': 'wpscan', 'install_linux': 'sudo apt-get install wpscan -y', 'install_windows': '', 'supported_os': ['linux'], 'cmd': ['wpscan', '--url', '{target}', '--enumerate', 'p', '--random-user-agent']},
    'amass': {'name': 'Amass Enumeration', 'category': 'passive_recon', 'requires_target': True, 'type': 'cli', 'bin': 'amass', 'install_linux': 'sudo apt-get install amass -y', 'install_windows': 'winget install OWASP.Amass', 'supported_os': ['linux', 'windows'], 'cmd': ['amass', 'enum', '-d', '{target}', '-passive']},
    'sherlock': {'name': 'Sherlock (Username)', 'category': 'passive_recon', 'requires_target': True, 'type': 'cli', 'bin': 'sherlock', 'install_linux': 'sudo apt-get install sherlock -y', 'install_windows': 'pip install sherlock', 'supported_os': ['linux', 'windows'], 'cmd': ['sherlock', '{target}', '--timeout', '5']},
    'sqlmap': {'name': 'Sqlmap (SQLi)', 'category': 'vulnerability', 'requires_target': True, 'type': 'cli', 'bin': 'sqlmap', 'install_linux': 'sudo apt-get install sqlmap -y', 'install_windows': 'pip install sqlmap', 'supported_os': ['linux', 'windows'], 'cmd': ['sqlmap', '-u', '{target}', '--batch', '--banner']},
    'commix': {'name': 'Commix (Injection)', 'category': 'vulnerability', 'requires_target': True, 'type': 'cli', 'bin': 'commix', 'install_linux': 'sudo apt-get install commix -y', 'install_windows': 'pip install commix', 'supported_os': ['linux', 'windows'], 'cmd': ['commix', '--url', '{target}', '--batch']},
    'google_dorks': {'name': 'Google Dorks Tree', 'category': 'passive_recon', 'requires_target': True, 'type': 'custom_html', 'handler': 'generate_dorks'},
    'wayback': {'name': 'Wayback Machine', 'category': 'passive_recon', 'requires_target': True, 'type': 'custom_html', 'handler': 'wayback'},
    'mac_degistir': {'name': 'MAC Değiştir', 'category': 'kali_ghost', 'requires_target': False, 'type': 'script', 'supported_os': ['linux'], 'cmd': ['bash', 'Runes/mac_degistir.sh']},
    'sorgula': {'name': 'Kimlik Sorgula', 'category': 'kali_ghost', 'requires_target': False, 'type': 'script', 'supported_os': ['linux'], 'cmd': ['bash', 'Runes/sorgula.sh']},
    'yeni_ip': {'name': 'Yeni IP (Tor)', 'category': 'kali_ghost', 'requires_target': False, 'type': 'script', 'supported_os': ['linux'], 'cmd': ['bash', 'Runes/yeni_ip.sh']},
    'adv_syn_scan': {'name': 'Advanced SYN Scan', 'category': 'adv_syn', 'requires_target': True, 'type': 'custom_script', 'handler': 'adv_syn_scan', 'has_modal': True, 'supported_os': ['linux']},
    'java_sniffer': {'name': 'Launch GUI Sniffer', 'category': 'java_sniffer', 'requires_target': False, 'type': 'gui', 'cwd': 'Runes/Network-Sniffer-Scanner-Java', 'cmd_windows': 'mvn javafx:run', 'cmd_linux': 'sudo mvn javafx:run', 'log_file': 'Runes/Network-Sniffer-Scanner-Java/launcher.log', 'install_linux': 'sudo apt-get install maven -y', 'install_windows': 'winget install Apache.Maven', 'supported_os': ['linux', 'windows']},
    'update_modules': {'name': 'Sync All Runes (Update)', 'category': 'system_ops', 'requires_target': False, 'type': 'custom_html', 'handler': 'update_modules'},
    'snoopdork': {'name': 'Launch SnoopDork OSINT', 'category': 'snoopdork', 'requires_target': False, 'type': 'gui', 'cwd': 'Runes/SnoopDork_V3', 'cmd_windows': 'start SnoopDork_V3.html', 'cmd_linux': 'xdg-open SnoopDork_V3.html', 'supported_os': ['linux', 'windows']},
    'packet_injector': {'name': 'Packet Injector (Craft & Inject)', 'category': 'packet_injector', 'requires_target': True, 'type': 'custom_script', 'handler': 'packet_injector', 'has_modal': True, 'supported_os': ['linux']},
    'mimir_scanner': {'name': 'Mimir Scanner (Real-time)', 'category': 'mimir_scanner', 'requires_target': False, 'type': 'custom_script', 'handler': 'mimir_scanner', 'supported_os': ['linux', 'windows']},
    'bifrost_gateway': {'name': 'Bifrost Security Gateway', 'category': 'bifrost_gateway', 'requires_target': False, 'type': 'custom_script', 'handler': 'bifrost_gateway', 'install_linux': 'sudo apt-get install maven -y', 'install_windows': 'winget install Apache.Maven', 'supported_os': ['linux', 'windows']}
}

def check_tool_status(tool_key):
    config = TOOLS_CONFIG.get(tool_key, {})
    if not config:
        return False
    tool_bin = config.get('bin')
    if not tool_bin:
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

def check_runes_updates():
    runes_dir = "Runes"
    updates = []
    if not os.path.exists(runes_dir):
        return updates
    for item in os.listdir(runes_dir):
        repo_path = os.path.join(runes_dir, item)
        if os.path.isdir(repo_path) and os.path.exists(os.path.join(repo_path, ".git")):
            try:
                subprocess.check_output(["git", "fetch"], cwd=repo_path, stderr=subprocess.STDOUT)
                status = subprocess.check_output(["git", "status", "-uno"], cwd=repo_path, stderr=subprocess.STDOUT).decode("utf-8")
                if "Your branch is behind" in status or "git pull" in status:
                    updates.append(item)
            except Exception:
                pass
    return updates

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
    return render_template('index.html')

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
