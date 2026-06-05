import os
import subprocess
import shutil
import json
import platform
import threading
import html
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

stats_lock = threading.Lock()

SCAN_STATS = {
    'total_scans': 0,
    'last_target': 'NONE',
    'active_tool': 'IDLE'
}

TOOLS_CONFIG = {
    'nmap': {'name': 'Nmap (Full Scan)', 'category': 'active_scanning', 'requires_target': True, 'type': 'cli', 'bin': 'nmap', 'install_linux': 'sudo apt-get install nmap -y', 'install_windows': 'winget install Insecure.Nmap', 'supported_os': ['linux', 'windows'], 'cmd': ['nmap', '-sV', '-F', '--version-light', '{target}']},
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
    'update_modules': {'name': 'Sync All Runes (Update)', 'category': 'system_ops', 'requires_target': False, 'type': 'custom_html', 'handler': 'update_modules'}
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
        # Use shell=True to support commands with pipes or '&&' if any.
        output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode('utf-8')
        return True, f"Installation output:\n{output}"
    except subprocess.CalledProcessError as e:
        return False, f"Installation failed:\n{e.output.decode('utf-8')}"
    except Exception as e:
        return False, f"Error: {str(e)}"

def generate_dorks(target):
    target_escaped = html.escape(target)
    dorks = [
        f"site:{target_escaped}",
        f"site:{target_escaped} inurl:admin",
        f"site:{target_escaped} inurl:login",
        f"site:{target_escaped} intitle:index of",
        f"site:{target_escaped} filetype:pdf",
        f"site:{target_escaped} filetype:sql",
        f"site:{target_escaped} inurl:wp-config.bak",
        f"site:{target_escaped} intext:'sql syntax near'",
        f"site:{target_escaped} inurl:dashboard"
    ]
    html_out = "<div style='display:flex; flex-wrap:wrap; gap:10px;'>"
    for d in dorks:
        url = f"https://www.google.com/search?q={d.replace(' ', '+')}"
        html_out += f"<a href='{url}' target='_blank' style='background:#333; padding:10px; color:#88c0d0; text-decoration:none; border:1px solid #4c566a;'>{d}</a>"
    html_out += "</div>"
    return html_out

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

def apply_runes_updates():
    runes_dir = "Runes"
    output_html = "<div style='font-family: monospace;'>"
    output_html += "<h3>[ ᛊ ] RUNE SYNC (UPDATE APPLIED)</h3>"
    
    if not os.path.exists(runes_dir):
        return "Runes directory not found."

    for item in os.listdir(runes_dir):
        repo_path = os.path.join(runes_dir, item)
        if os.path.isdir(repo_path) and os.path.exists(os.path.join(repo_path, ".git")):
            try:
                status = subprocess.check_output(["git", "status", "-uno"], cwd=repo_path, stderr=subprocess.STDOUT).decode("utf-8")
                if "Your branch is behind" in status or "git pull" in status:
                    output_html += f"<p style='color: var(--highlight-color);'>Applying updates for <b>{item}</b>...</p>"
                    pull_output = subprocess.check_output(["git", "pull"], cwd=repo_path, stderr=subprocess.STDOUT).decode("utf-8")
                    output_html += f"<pre style='background: #222; padding: 10px; border: 1px solid #444; color: #fff;'>{pull_output}</pre>"
                    
                    if "Network-Sniffer-Scanner-Java" in item:
                        output_html += "<p style='color: #88c0d0;'>Recompiling Java Sniffer with Maven...</p>"
                        mvn_cmd = "mvn.cmd" if platform.system() == "Windows" else "mvn"
                        mvn_output = subprocess.check_output([mvn_cmd, "clean", "install"], cwd=repo_path, stderr=subprocess.STDOUT).decode("utf-8")
                        if "BUILD SUCCESS" in mvn_output:
                            output_html += "<p style='color: #a3be8c;'>Compilation Successful.</p>"
                        else:
                            output_html += "<p style='color: #bf616a;'>Compilation Failed. Check logs.</p>"
            except Exception as e:
                output_html += f"<p style='color: #bf616a;'>Error updating {item}: {str(e)}</p>"
                
    output_html += "<br><p style='color: #a3be8c;'>Update process complete.</p></div>"
    return output_html

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

    elif tool_type == 'custom_html':
        handler_name = config.get('handler')
        if handler_name == 'generate_dorks':
            return generate_dorks(target)
        elif handler_name == 'wayback':
            return f"Wayback Machine Link: https://web.archive.org/web/*/{target}"

    elif tool_type == 'custom_script':
        handler_name = config.get('handler')
        if handler_name == 'adv_syn_scan':
            syn_mode = data.get('syn_mode', 'auto') if data else 'auto'
            if syn_mode == 'auto':
                max_port = data.get('max_port', '1000') if data else '1000'
                cmd = ["bash", "Runes/Advanced-SYN-Scanner/auto_scan.sh", str(target), str(max_port)]
            else:
                source_ip = data.get('source_ip', '') if data else ''
                start_port = data.get('start_port', '1') if data else '1'
                end_port = data.get('end_port', '1000') if data else '1000'
                cmd = ["sudo", "Runes/Advanced-SYN-Scanner/syn_scanner", "-s", source_ip, "-t", target, "-p", start_port, "-e", end_port]
            
            try:
                result = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=120).decode('utf-8')
                return result
            except subprocess.TimeoutExpired:
                return "TIMEOUT: Process took too long"
            except subprocess.CalledProcessError as e:
                return f"Execution Error:\n{e.output.decode('utf-8')}"
            except Exception as e:
                return f"System Error: {str(e)}"

    return "Unsupported tool type"

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/tools', methods=['GET'])
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
def get_stats():
    return jsonify(SCAN_STATS)

@app.route('/api/dependencies', methods=['GET'])
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
def handle_action():
    data = request.form
    tool = data.get('tool')
    target = data.get('target')
    action = data.get('action')

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
        with stats_lock:
            SCAN_STATS['total_scans'] += 1
            SCAN_STATS['last_target'] = target if target else 'NONE'
            SCAN_STATS['active_tool'] = tool.upper()
        
        config = TOOLS_CONFIG.get(tool)
        if config and config.get('type') == 'custom_html':
            output = execute_tool(tool, target, data)
            return jsonify({'status': 'success', 'output': output, 'type': 'html' if tool in ['google_dorks'] else 'text'})
            
        output = execute_tool(tool, target, data)
        return jsonify({'status': 'success', 'output': output, 'type': 'text'})

    return jsonify({'status': 'error', 'message': 'Invalid action'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
