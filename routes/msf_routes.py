from flask import Blueprint, jsonify, request, session, send_file
from handlers.msf_handler import (
    get_payload_list, generate_payload, get_msf_rpc_status,
    list_generated_payloads
)
import os

msf_bp = Blueprint('msf_routes', __name__)


from core.auth import login_required
from core.validation import bounded_integer


@msf_bp.route('/api/msf/status', methods=['GET'])
@login_required
def api_msf_status():
    return jsonify(get_msf_rpc_status())


@msf_bp.route('/api/msf/payloads', methods=['GET'])
@login_required
def api_payload_list():
    platform = request.args.get('platform', None)
    return jsonify(get_payload_list(platform))


@msf_bp.route('/api/msf/payload/generate', methods=['POST'])
@login_required
def api_generate_payload():
    data = request.get_json()
    platform = data.get('platform', 'linux')
    lhost = data.get('lhost', '')
    lport = bounded_integer(data.get('lport', 4444), 'lport', minimum=1, maximum=65535, default=4444)
    payload_type = data.get('payload_type', None)
    encoder = data.get('encoder', 'none')
    iterations = bounded_integer(data.get('iterations', 0), 'iterations', minimum=0, maximum=100, default=0)
    arch = data.get('arch', None)
    output_format = data.get('output_format', 'exe')

    if not lhost:
        return jsonify({"status": "error", "message": "LHOST required."})

    result = generate_payload(platform, lhost, lport, payload_type, encoder, iterations, arch, output_format)
    return jsonify(result)


@msf_bp.route('/api/msf/payload/download', methods=['GET'])
@login_required
def api_download_payload():
    filename = request.args.get('filename', '')
    if not filename or '..' in filename or '/' in filename or '\\' in filename:
        return jsonify({"status": "error", "message": "Invalid filename."}), 400

    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "generated_payloads")
    filepath = os.path.join(output_dir, filename)

    if not os.path.exists(filepath):
        return jsonify({"status": "error", "message": "File not found."}), 404

    return send_file(filepath, as_attachment=True, download_name=filename)


@msf_bp.route('/api/msf/payloads/list', methods=['GET'])
@login_required
def api_list_payloads():
    return jsonify(list_generated_payloads())


MSF_ALLOWED_PREFIXES = [
    "use ", "set ", "setg ", "run", "exploit", "back", "exit",
    "sessions", "search ", "info ", "show ", "hosts", "services", "vulns",
    "db_nmap ", "db_status", "workspace ", "jobs", "route ", "load ", "unload ",
    "handler ", "grep ", "irb", "spool ", "resource ", "makerc ",
]

def _validate_msf_command(command):
    cmd_clean = command.strip()
    if not cmd_clean:
        return False
    if len(cmd_clean) > 300:
        return False
    if any(ch in cmd_clean for ch in [";", "&&", "||", "`", "$(", "${", "../", "..\\"]):
        return False
    for prefix in MSF_ALLOWED_PREFIXES:
        if cmd_clean.lower().startswith(prefix.lower()):
            return True
    return False


@msf_bp.route('/api/msf/execute', methods=['POST'])
@login_required
def api_msf_execute():
    data = request.get_json()
    command = data.get('command', '')
    if not command:
        return jsonify({"status": "error", "message": "Command required."})

    if not _validate_msf_command(command):
        return jsonify({"status": "error", "message": "Command blocked by security policy."})

    import subprocess
    try:
        result = subprocess.run(
            ["msfconsole", "-q", "-x", command + "; exit"],
            capture_output=True, text=True, timeout=30
        )
        return jsonify({
            "status": "success",
            "output": result.stdout[:5000],
            "stderr": result.stderr[:1000]
        })
    except subprocess.TimeoutExpired:
        return jsonify({"status": "error", "message": "Command timed out."})
    except FileNotFoundError:
        return jsonify({"status": "error", "message": "msfconsole not found."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@msf_bp.route('/api/msf/sessions', methods=['GET'])
@login_required
def api_msf_sessions():
    return jsonify({"status": "success", "sessions": [], "message": "MSF RPC not connected. Use msfrpcd for live sessions."})
