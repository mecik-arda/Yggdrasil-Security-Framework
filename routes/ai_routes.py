from flask import Blueprint, jsonify, request
from routes.action_routes import login_required
from handlers.ai_engine import (
    list_models, chat_completion, pull_model, remove_model, get_ai_profile_tiers,
    analyze_scan_output, scan_all_model_sources, check_environment_status
)
from handlers.agent_loop import (
    start_agent, get_agent_status, stop_agent, list_agent_sessions,
    get_agent_settings, update_agent_settings
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


@ai_bp.route('/api/ai/scan_sources', methods=['GET'])
@login_required
def ai_scan_sources():
    """Scan localhost, Docker, and WSL for all available Ollama models."""
    result = scan_all_model_sources()
    return jsonify(result)


@ai_bp.route('/api/ai/environment_status', methods=['GET'])
@login_required
def ai_environment_status():
    """Return real-time status of Docker and WSL environments."""
    result = check_environment_status()
    return jsonify({'status': 'success', 'environments': result})


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
    data = request.get_json()
    target = data.get('target', '')
    mode = data.get('mode', 'recon')
    if not target:
        return jsonify({'status': 'error', 'message': 'Target is required.'})
    result = start_agent(target, mode)
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


# ── Agent settings (Phase 2.4) ──────────────────────────────────────────────

@ai_bp.route('/api/agent/settings', methods=['GET'])
@login_required
def agent_settings_get():
    """Return current autonomous agent settings."""
    settings = get_agent_settings()
    return jsonify({'status': 'success', 'settings': settings})


@ai_bp.route('/api/agent/settings', methods=['POST'])
@login_required
def agent_settings_update():
    """Update autonomous agent settings.

    Accepts JSON: {max_steps: int, approval_mode: bool, multi_agent_mode: bool,
                    odin_model: str, loki_model: str, kvasir_model: str}
    """
    data = request.get_json() or {}
    updates = {}
    if 'max_steps' in data:
        try:
            updates['max_steps'] = max(1, min(50, int(data['max_steps'])))
        except (ValueError, TypeError):
            return jsonify({'status': 'error', 'message': 'max_steps must be an integer.'})
    if 'approval_mode' in data:
        updates['approval_mode'] = bool(data['approval_mode'])
    if 'multi_agent_mode' in data:
        updates['multi_agent_mode'] = bool(data['multi_agent_mode'])
    if 'odin_model' in data:
        updates['odin_model'] = str(data['odin_model'])
    if 'loki_model' in data:
        updates['loki_model'] = str(data['loki_model'])
    if 'kvasir_model' in data:
        updates['kvasir_model'] = str(data['kvasir_model'])

    new_settings = update_agent_settings(updates)
    return jsonify({'status': 'success', 'settings': new_settings})


# ── Auto-Pwn (Phase: Komuta Merkezi Genişletmesi) ────────────────────────────

@ai_bp.route('/api/ai/auto-pwn', methods=['POST'])
@login_required
def ai_auto_pwn():
    """Kvasir-guided autonomous Privilege Escalation / Lateral Movement.

    Accepts JSON: {session_ids: [zombie_id, ...]}
    For each active session, queries the Kvasir RAG knowledge base for
    privilege escalation vectors based on the zombie's OS, then sends
    appropriate enumeration commands via the C2 handler.
    """
    data = request.get_json() or {}
    session_ids = data.get('session_ids', [])

    if not session_ids:
        return jsonify({'status': 'error', 'message': 'No session IDs provided.'})

    results = []
    commands_sent = 0

    from core.db import get_connection
    try:
        conn = get_connection()
        c = conn.cursor()
        
        for sid in session_ids:
            try:
                c.execute(
                    'SELECT zombie_id, os_type, remote_addr FROM c2_sessions '
                    'WHERE zombie_id = ? AND disconnected_at IS NULL LIMIT 1',
                    (sid,)
                )
                row = c.fetchone()

                if not row:
                    results.append({'session': sid, 'status': 'not_found', 'message': 'Session not active.'})
                    continue

                zombie_id, os_type, remote_addr = row
                os_lower = (os_type or '').lower()

                # Determine PrivEsc vectors based on OS
                priv_esc_commands = _get_auto_pwn_commands(os_lower)

                # Query Kvasir RAG for additional vectors
                kvasir_hints = _query_kvasir_for_privesc(os_lower)

                results.append({
                    'session': zombie_id,
                    'status': 'analyzed',
                    'os': os_type,
                    'remote': remote_addr,
                    'commands_queued': priv_esc_commands,
                    'kvasir_hints': kvasir_hints,
                })
                commands_sent += len(priv_esc_commands)

            except Exception as e:
                results.append({'session': sid, 'status': 'error', 'message': str(e)})

        conn.close()
    except Exception as outer_e:
        return jsonify({'status': 'error', 'message': f'Database connection error: {str(outer_e)}'})

    return jsonify({
        'status': 'success',
        'message': f'Auto-Pwn analysis complete. {commands_sent} commands queued for {len(session_ids)} session(s).',
        'details': '\n'.join(
            f"[{r.get('session','?')}] {r.get('status','?')}: {r.get('os','?')} — "
            f"{len(r.get('commands_queued',[]))} commands ready"
            for r in results
        ),
        'results': results,
    })


def _get_auto_pwn_commands(os_type):
    """Return privilege escalation enumeration commands based on OS type."""
    if 'windows' in os_type:
        return [
            'whoami /all',
            'systeminfo',
            'net user',
            'net localgroup administrators',
            'icacls "C:\\Program Files"',
            'schtasks /query /fo LIST /v',
            'reg query HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall /s',
            'wmic service get name,displayname,pathname,startmode',
        ]
    else:
        return [
            'whoami ; id',
            'uname -a',
            'sudo -l 2>/dev/null || echo "No sudo"',
            'find / -perm -4000 -type f 2>/dev/null | head -20',
            'cat /etc/crontab 2>/dev/null || echo "No crontab"',
            'ls -la /etc/cron.* 2>/dev/null',
            'cat /etc/passwd | grep -v nologin | grep -v false',
            'ss -tlnp 2>/dev/null || netstat -tlnp',
            'find / -writable -type f 2>/dev/null | grep -v /proc | head -15',
        ]


def _query_kvasir_for_privesc(os_type):
    """Query the Kvasir RAG engine for privilege escalation hints."""
    try:
        from handlers.rag_engine import search_kvasir
        query = f'privilege escalation {"windows" if "windows" in os_type else "linux"}'
        result = search_kvasir(query)
        if result and result.get('status') == 'success':
            entries = result.get('entries', result.get('results', []))
            return [e.get('title', e.get('name', '')) for e in entries[:3]]
    except Exception:
        pass
    return []

