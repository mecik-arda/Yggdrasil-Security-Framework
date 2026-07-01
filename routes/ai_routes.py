from flask import Blueprint, jsonify, request
from routes.action_routes import login_required
from handlers.ai_engine import (
    list_models, chat_completion, pull_model, remove_model, get_ai_profile_tiers,
    analyze_scan_output
)
from handlers.agent_loop import (
    start_agent, get_agent_status, stop_agent, list_agent_sessions
)
from handlers.valkyrie_reporter import (
    generate_report_from_agent, generate_report_from_terminals, markdown_to_html
)

ai_bp = Blueprint('ai_routes', __name__)

@ai_bp.route('/api/ai/status', methods=['GET'])
@login_required
def ai_status():
    """Check if Ollama is reachable and return installed models."""
    result = list_models()
    return jsonify(result)

@ai_bp.route('/api/ai/chat', methods=['POST'])
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

@ai_bp.route('/api/ai/models', methods=['GET'])
@login_required
def ai_models():
    """List installed Ollama models and available tiers."""
    installed = list_models()
    tiers = get_ai_profile_tiers()
    return jsonify({
        'installed': installed,
        'tiers': tiers
    })

@ai_bp.route('/api/ai/pull', methods=['POST'])
@login_required
def ai_pull():
    """Pull (download) a model from Ollama registry."""
    data = request.get_json()
    model = data.get('model', '')
    if not model:
        return jsonify({'status': 'error', 'message': 'Model adi gerekli.'})
    result = pull_model(model)
    return jsonify(result)

@ai_bp.route('/api/ai/remove', methods=['POST'])
@login_required
def ai_remove():
    """Remove an installed Ollama model."""
    data = request.get_json()
    model = data.get('model', '')
    if not model:
        return jsonify({'status': 'error', 'message': 'Model adi gerekli.'})
    result = remove_model(model)
    return jsonify(result)

@ai_bp.route('/api/ai/disk', methods=['GET'])
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

@ai_bp.route('/api/ai/tiers', methods=['GET'])
@login_required
def ai_tiers():
    """Return hardware tier recommendations."""
    return jsonify(get_ai_profile_tiers())

@ai_bp.route('/api/ai/report', methods=['POST'])
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

@ai_bp.route('/api/ai/report/html', methods=['POST'])
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

@ai_bp.route('/api/agent/start', methods=['POST'])
@login_required
def agent_start():
    """Start an autonomous ReAct agent session on a target."""
    data = request.get_json()
    target = data.get('target', '')
    if not target:
        return jsonify({'status': 'error', 'message': 'Target is required.'})
    result = start_agent(target)
    return jsonify(result)

@ai_bp.route('/api/agent/status', methods=['GET'])
@login_required
def agent_status():
    """Get the current status of an agent session."""
    session_id = request.args.get('session_id', '')
    if not session_id:
        return jsonify({'status': 'error', 'message': 'Session ID required.'})
    result = get_agent_status(session_id)
    return jsonify(result)

@ai_bp.route('/api/agent/stop', methods=['POST'])
@login_required
def agent_stop():
    """Force-stop a running agent session."""
    data = request.get_json()
    session_id = data.get('session_id', '')
    if not session_id:
        return jsonify({'status': 'error', 'message': 'Session ID required.'})
    result = stop_agent(session_id)
    return jsonify(result)

@ai_bp.route('/api/agent/sessions', methods=['GET'])
@login_required
def agent_sessions():
    """List all agent sessions."""
    return jsonify(list_agent_sessions())

@ai_bp.route('/api/ai/analyze', methods=['POST'])
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
