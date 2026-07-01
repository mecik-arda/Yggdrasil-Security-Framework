from flask import Blueprint, jsonify, request, session, send_file
from handlers.evasion_crafter import craft_evasive_payload, OUTPUT_DIR
import os

evasion_bp = Blueprint('evasion_routes', __name__)


def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            from flask import redirect, url_for
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


@evasion_bp.route('/api/evasion/craft', methods=['POST'])
@login_required
def api_craft_evasive():
    data = request.get_json()
    shellcode_hex = data.get('shellcode', '')
    language = data.get('language', 'python')
    method = data.get('method', 'aes')

    if not shellcode_hex:
        return jsonify({"status": "error", "message": "Shellcode (hex) required."})

    clean = shellcode_hex.replace("\\x", "").replace("0x", "").replace(" ", "").strip()
    if not clean or len(clean) < 4:
        return jsonify({"status": "error", "message": "Invalid shellcode. Provide raw hex bytes."})

    try:
        bytes.fromhex(clean)
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid hex shellcode."})

    result = craft_evasive_payload(clean, language, method)
    return jsonify(result)


@evasion_bp.route('/api/evasion/templates', methods=['GET'])
@login_required
def api_evasion_templates():
    return jsonify({
        "status": "success",
        "methods": ["aes", "xor", "polymorphic"],
        "languages": ["python", "c", "powershell", "csharp"],
        "description": {
            "aes": "AES-256-CBC encryption with loader stub",
            "xor": "Simple XOR-based encoding with decoder stub",
            "polymorphic": "Multi-layer compression + XOR + base64 stub"
        }
    })


@evasion_bp.route('/api/evasion/download', methods=['GET'])
@login_required
def api_evasion_download():
    filename = request.args.get('filename', '')
    if not filename or '..' in filename or '/' in filename or '\\' in filename:
        return jsonify({"status": "error", "message": "Invalid filename."}), 400

    filepath = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(filepath):
        return jsonify({"status": "error", "message": "File not found."}), 404

    return send_file(filepath, as_attachment=True, download_name=filename)
