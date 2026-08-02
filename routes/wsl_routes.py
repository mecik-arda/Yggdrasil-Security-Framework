from flask import Blueprint, jsonify, request
from core.system_manager import check_tool_status_detail
from core.tool_runner import get_preferred_wsl, get_wsl_distros
from tools_config import TOOLS_CONFIG
import concurrent.futures
import platform
import json

api_wsl_bp = Blueprint('api_wsl', __name__)
from core import login_required, require_role
from core.validation import require_json_object

WSL_CONFIG_FILE = 'wsl_config.json'

@api_wsl_bp.route('/api/wsl/distros', methods=['GET'])
@login_required
def api_wsl_distros():
    distros = get_wsl_distros()
    preferred = get_preferred_wsl()
    return jsonify({'distros': distros, 'preferred': preferred})

@api_wsl_bp.route('/api/wsl/config', methods=['POST'])
@login_required
@require_role("admin")
def api_wsl_config():
    distro = require_json_object(request).get('distro')
    if distro in get_wsl_distros() or not distro:
        with open(WSL_CONFIG_FILE, 'w') as f:
            json.dump({'wsl_distro': distro}, f)
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error', 'message': 'Invalid distro'})

@api_wsl_bp.route('/api/dependencies', methods=['GET'])
@login_required
def check_dependencies():
    deps = []
    current_os = platform.system()
    def process_tool(item):
        key, val = item
        supported = val.get('supported_os', [])
        is_supported = True
        is_wsl = False
        if current_os.lower() not in supported:
            is_supported = False
            if current_os == 'Windows' and 'linux' in supported:
                is_supported = True
                is_wsl = True
        status_detail = check_tool_status_detail(key)
        return {
            'tool_key': key,
            'name': val.get('name', key),
            'installed': status_detail != 'missing',
            'installed_platform': status_detail,
            'supported': is_supported,
            'is_wsl': is_wsl
        }
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        results = executor.map(process_tool, TOOLS_CONFIG.items())
    for r in results:
        if r:
            deps.append(r)
    return jsonify(deps)
