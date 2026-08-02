from flask import Blueprint, jsonify, request
from core import login_required, require_role
from core.validation import require_json_object
from handlers.rag_engine import (
    check_rag_status, index_knowledge_base, query_knowledge,
    fetch_gtfobins_live
)
from handlers.loki_engine import (
    mutate_payload, list_techniques, analyze_waf_response
)

rag_loki_bp = Blueprint('rag_loki_routes', __name__)

@rag_loki_bp.route('/api/rag/status', methods=['GET'])
@login_required
def rag_status():
    """Check RAG engine status (ChromaDB, Ollama, collections)."""
    return jsonify(check_rag_status())

@rag_loki_bp.route('/api/rag/index', methods=['POST'])
@login_required
@require_role("admin")
def rag_index():
    """Index built-in knowledge base into ChromaDB."""
    result = index_knowledge_base()
    return jsonify(result)

@rag_loki_bp.route('/api/rag/fetch', methods=['POST'])
@login_required
@require_role("admin")
def rag_fetch():
    """Fetch latest GTFOBins data from GitHub."""
    result = fetch_gtfobins_live()
    return jsonify(result)

@rag_loki_bp.route('/api/rag/query', methods=['POST'])
@login_required
@require_role("admin", "analyst")
def rag_query():
    """Query the RAG knowledge base."""
    data = require_json_object(request)
    query = data.get('query', '')
    collections = data.get('collections', None)
    top_k = data.get('top_k', 5)
    if not query or not query.strip():
        return jsonify({'status': 'error', 'message': 'Sorgu metni gerekli.'})
    result = query_knowledge(query.strip(), collections, top_k)
    return jsonify(result)

@rag_loki_bp.route('/api/loki/mutate', methods=['POST'])
@login_required
@require_role("admin")
def loki_mutate():
    """Mutate a payload using selected WAF evasion techniques."""
    data = require_json_object(request)
    payload = data.get('payload', '')
    techniques = data.get('techniques', None)
    count = data.get('count', 5)
    result = mutate_payload(payload, techniques, count)
    return jsonify(result)

@rag_loki_bp.route('/api/loki/techniques', methods=['GET'])
@login_required
def loki_techniques():
    """List all available mutation techniques."""
    return jsonify(list_techniques())

@rag_loki_bp.route('/api/loki/analyze', methods=['POST'])
@login_required
@require_role("admin")
def loki_analyze_waf():
    """Analyze a WAF block response and suggest bypass strategies."""
    data = require_json_object(request)
    status_code = data.get('status_code', 403)
    response_body = data.get('response_body', '')
    result = analyze_waf_response(status_code, response_body)
    return jsonify(result)
