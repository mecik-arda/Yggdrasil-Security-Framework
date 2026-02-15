import os
import subprocess
import shutil
import json
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

SCAN_STATS = {
    'total_scans': 0,
    'last_target': 'NONE',
    'active_tool': 'IDLE'
}

TOOLS_CONFIG = {
    'nmap': {'bin': 'nmap', 'install': 'sudo apt-get install nmap -y'},
    'whois': {'bin': 'whois', 'install': 'sudo apt-get install whois -y'},
    'dnsenum': {'bin': 'dnsenum', 'install': 'sudo apt-get install dnsenum -y'},
    'sublist3r': {'bin': 'sublist3r', 'install': 'sudo apt-get install sublist3r -y'},
    'theharvester': {'bin': 'theHarvester', 'install': 'sudo apt-get install theharvester -y'},
    'wafw00f': {'bin': 'wafw00f', 'install': 'sudo apt-get install wafw00f -y'},
    'dnsrecon': {'bin': 'dnsrecon', 'install': 'sudo apt-get install dnsrecon -y'},
    'dig': {'bin': 'dig', 'install': 'sudo apt-get install dnsutils -y'},
    'searchsploit': {'bin': 'searchsploit', 'install': 'sudo apt-get install exploitdb -y'},
    'tshark': {'bin': 'tshark', 'install': 'sudo apt-get install tshark -y'},
    'nikto': {'bin': 'nikto', 'install': 'sudo apt-get install nikto -y'},
    'wpscan': {'bin': 'wpscan', 'install': 'sudo apt-get install wpscan -y'},
    'amass': {'bin': 'amass', 'install': 'sudo apt-get install amass -y'},
    'sherlock': {'bin': 'sherlock', 'install': 'sudo apt-get install sherlock -y'},
    'sqlmap': {'bin': 'sqlmap', 'install': 'sudo apt-get install sqlmap -y'},
    'commix': {'bin': 'commix', 'install': 'sudo apt-get install commix -y'}
}

def check_tool_status(tool_key):
    if tool_key in ['google_dorks', 'wayback', 'dnsdumpster']:
        return True
    tool_bin = TOOLS_CONFIG.get(tool_key, {}).get('bin')
    if tool_bin:
        return shutil.which(tool_bin) is not None
    return False

def install_tool_system(tool_key):
    if tool_key not in TOOLS_CONFIG:
        return False, "Tool definition not found"
    cmd = TOOLS_CONFIG[tool_key]['install']
    try:
        subprocess.check_call(cmd.split())
        return True, "Installation successful"
    except subprocess.CalledProcessError:
        return False, "Installation failed"

def generate_dorks(target):
    dorks = [
        f"site:{target}",
        f"site:{target} inurl:admin",
        f"site:{target} inurl:login",
        f"site:{target} intitle:index of",
        f"site:{target} filetype:pdf",
        f"site:{target} filetype:sql",
        f"site:{target} inurl:wp-config.bak",
        f"site:{target} intext:'sql syntax near'",
        f"site:{target} inurl:dashboard"
    ]
    html = "<div style='display:flex; flex-wrap:wrap; gap:10px;'>"
    for d in dorks:
        url = f"https://www.google.com/search?q={d.replace(' ', '+')}"
        html += f"<a href='{url}' target='_blank' style='background:#333; padding:10px; color:#88c0d0; text-decoration:none; border:1px solid #4c566a;'>{d}</a>"
    html += "</div>"
    return html

def execute_tool(tool, target):
    cmd = []
    
    if tool == 'nmap':
        cmd = ["nmap", "-sV", "-F", "--version-light", target]
    elif tool == 'whois':
        cmd = ["whois", target]
    elif tool == 'dnsenum':
        cmd = ["dnsenum", "--noreverse", target]
    elif tool == 'sublist3r':
        cmd = ["sublist3r", "-d", target]
    elif tool == 'theharvester':
        cmd = ["theHarvester", "-d", target, "-l", "100", "-b", "all"]
    elif tool == 'wafw00f':
        cmd = ["wafw00f", target]
    elif tool == 'dnsrecon':
        cmd = ["dnsrecon", "-d", target]
    elif tool == 'dig':
        cmd = ["dig", "ANY", target]
    elif tool == 'searchsploit':
        cmd = ["searchsploit", target]
    elif tool == 'tshark':
        cmd = ["tshark", "-c", "5", "-i", "any"]
    elif tool == 'nikto':
        cmd = ["nikto", "-h", target, "-Tuning", "1"]
    elif tool == 'wpscan':
        cmd = ["wpscan", "--url", target, "--enumerate", "p", "--random-user-agent"]
    elif tool == 'amass':
        cmd = ["amass", "enum", "-d", target, "-passive"]
    elif tool == 'sherlock':
        cmd = ["sherlock", target, "--timeout", "5"]
    elif tool == 'sqlmap':
        cmd = ["sqlmap", "-u", target, "--batch", "--banner"]
    elif tool == 'commix':
        cmd = ["commix", "--url", target, "--batch"]

    try:
        if not cmd: return "Command not defined"
        result = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=120).decode('utf-8')
        return result
    except subprocess.TimeoutExpired:
        return "TIMEOUT: Process took too long"
    except subprocess.CalledProcessError as e:
        return f"Execution Error:\n{e.output.decode('utf-8')}"
    except Exception as e:
        return f"System Error: {str(e)}"

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/stats', methods=['GET'])
def get_stats():
    return jsonify(SCAN_STATS)

@app.route('/api/action', methods=['POST'])
def handle_action():
    data = request.form
    tool = data.get('tool')
    target = data.get('target')
    action = data.get('action')

    if action == 'check':
        exists = check_tool_status(tool)
        return jsonify({'status': 'installed' if exists else 'missing'})

    elif action == 'install':
        success, msg = install_tool_system(tool)
        return jsonify({'status': 'success' if success else 'error', 'message': msg})

    elif action == 'run':
        SCAN_STATS['total_scans'] += 1
        SCAN_STATS['last_target'] = target
        SCAN_STATS['active_tool'] = tool.upper()
        
        if tool == 'google_dorks':
            return jsonify({'status': 'success', 'output': generate_dorks(target), 'type': 'html'})
        elif tool == 'wayback':
            return jsonify({'status': 'success', 'output': f"Wayback Machine Link: https://web.archive.org/web/*/{target}", 'type': 'text'})
        
        output = execute_tool(tool, target)
        return jsonify({'status': 'success', 'output': output, 'type': 'text'})

    return jsonify({'status': 'error', 'message': 'Invalid action'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
