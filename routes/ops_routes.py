"""
Yggdrasil Ops Routes — Active Sessions, Network Topology, CVE Knowledge

Phase: Komuta Merkezi Genişletmesi
Provides backend API endpoints for the new operational command buttons.
"""
import json
import sqlite3
import re
import urllib.parse
import requests as _requests
from datetime import datetime
from flask import Blueprint, jsonify, request
from core.auth import login_required

ops_bp = Blueprint('ops_routes', __name__)


# ═══════════════════════════════════════════════════════════════════════════════
# GET /api/ops/sessions — Active C2 Sessions
# ═══════════════════════════════════════════════════════════════════════════════

@ops_bp.route('/api/ops/sessions', methods=['GET'])
@login_required
def get_active_sessions():
    """Return all active C2 (zombie) sessions from the database."""
    try:
        from core.db import get_connection
        conn = get_connection()
        c = conn.cursor()
        c.execute(
            'SELECT zombie_id, listener_port, remote_addr, os_type, connected_at, '
            'disconnected_at, commands_sent FROM c2_sessions '
            'WHERE disconnected_at IS NULL ORDER BY connected_at DESC'
        )
        rows = c.fetchall()
        conn.close()

        sessions = []
        for r in rows:
            sessions.append({
                'zombie_id': r[0],
                'listener_port': r[1],
                'remote_addr': r[2],
                'os_type': r[3],
                'connected_at': r[4],
                'disconnected_at': r[5],
                'commands_sent': r[6],
            })

        return jsonify({'status': 'success', 'sessions': sessions, 'count': len(sessions)})
    except Exception as e:
        from core.logger import get_logger
        get_logger('ops_routes').error(f'Database error in get_active_sessions: {e}', exc_info=True)
        return jsonify({'status': 'error', 'message': 'Internal server error'})


# ═══════════════════════════════════════════════════════════════════════════════
# GET /api/ops/topology — Network Topology Data (from scan_history)
# ═══════════════════════════════════════════════════════════════════════════════

@ops_bp.route('/api/ops/topology', methods=['GET'])
@login_required
def get_network_topology():
    """Parse scan_history table and build a node-edge graph for vis.js.

    Each scan result is parsed for:
      - Target IP/domain → becomes a 'target' node
      - Open ports → 'port' nodes, linked to their target
      - Subdomains → 'subdomain' nodes, linked to their target
      - Vulnerabilities → 'vulnerability' nodes
    """
    try:
        from core.db import get_connection
        conn = get_connection()
        c = conn.cursor()
        c.execute(
            'SELECT task_id, tool, target, output, status, timestamp '
            'FROM scan_history WHERE status != "RUNNING" '
            'ORDER BY timestamp DESC LIMIT 50'
        )
        rows = c.fetchall()
        conn.close()
    except Exception as e:
        from core.logger import get_logger
        get_logger('ops_routes').error(f'Database error in get_network_topology: {e}', exc_info=True)
        return jsonify({'status': 'error', 'message': 'Internal server error'})

    if not rows:
        return jsonify({'status': 'success', 'nodes': [], 'edges': [], 'message': 'No scan history found.'})

    nodes = {}   # id → {id, label, type, title}
    edges = []   # [{from, to}]

    for row in rows:
        task_id, tool, target, output, status, ts = row
        if not target:
            continue

        # Target node
        target_id = f'target_{target}'
        if target_id not in nodes:
            nodes[target_id] = {
                'id': target_id,
                'label': target,
                'type': 'target',
                'title': f'Target: {target}\nTool: {tool}\nTime: {ts}',
            }

        tool_key = (tool or '').lower()
        output_text = (output or '')

        # ── Nmap: extract open ports ──────────────────────────────────────
        if 'nmap' in tool_key:
            port_lines = re.findall(r'(\d+)/(tcp|udp)\s+open\s+(\S+)', output_text)
            for port, proto, service in port_lines:
                port_id = f'port_{target}_{port}_{proto}'
                if port_id not in nodes:
                    nodes[port_id] = {
                        'id': port_id,
                        'label': f'{port}/{proto}\n({service})',
                        'type': 'port',
                        'title': f'Port: {port}/{proto}\nService: {service}\nTarget: {target}',
                    }
                edges.append({'from': target_id, 'to': port_id})

        # ── Subfinder / Assetfinder / DNS tools: extract subdomains ───────
        if any(t in tool_key for t in ('subfinder', 'assetfinder', 'amass',
                                         'dnsenum', 'dnsrecon', 'fierce',
                                         'sublist3r', 'gobuster_dns')):
            # Heuristic: lines that look like subdomains
            sub_lines = re.findall(
                r'([a-zA-Z0-9][-a-zA-Z0-9]*\.' + re.escape(target) + r')',
                output_text
            )
            for sub in set(sub_lines):
                sub_id = f'subdomain_{sub}'
                if sub_id not in nodes:
                    nodes[sub_id] = {
                        'id': sub_id,
                        'label': sub,
                        'type': 'subdomain',
                        'title': f'Subdomain: {sub}\nDiscovered via: {tool}',
                    }
                edges.append({'from': target_id, 'to': sub_id})

        # ── Nuclei / Nikto / Vuln scanners: extract findings ──────────────
        if any(t in tool_key for t in ('nuclei', 'nikto', 'wapiti', 'wpscan',
                                         'nmap_vulners', 'nmap_vuln')):
            cve_matches = re.findall(r'CVE-\d{4}-\d{4,}', output_text, re.IGNORECASE)
            vuln_indicators = re.findall(
                r'(\[critical\]|\[high\]|\[medium\]).*', output_text, re.IGNORECASE
            )
            for cve_id in set(cve_matches):
                cve_node_id = f'vuln_{cve_id}'
                if cve_node_id not in nodes:
                    nodes[cve_node_id] = {
                        'id': cve_node_id,
                        'label': cve_id,
                        'type': 'vulnerability',
                        'title': f'CVE: {cve_id}\nFound by: {tool}\nTarget: {target}',
                    }
                edges.append({'from': target_id, 'to': cve_node_id})

            for v in set(vuln_indicators)[:5]:
                v_clean = v.strip()[:80]
                v_id = f'vuln_{v_clean}'
                if v_id not in nodes:
                    nodes[v_id] = {
                        'id': v_id,
                        'label': v_clean[:40],
                        'type': 'vulnerability',
                        'title': f'{v_clean}\nFound by: {tool}',
                    }
                edges.append({'from': target_id, 'to': v_id})

    return jsonify({
        'status': 'success',
        'nodes': list(nodes.values()),
        'edges': edges,
        'count': len(nodes),
    })


# ═══════════════════════════════════════════════════════════════════════════════
# GET /api/ops/cve — CVE Knowledge Search (NIST NVD API)
# ═══════════════════════════════════════════════════════════════════════════════

@ops_bp.route('/api/ops/cve', methods=['GET'])
@login_required
def search_cve_knowledge():
    """Search CVE details via the NIST NVD API (or Circl.lu as fallback).

    Query param: ``q`` — CVE ID (e.g. "CVE-2024-1234") or keyword.
    """
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'status': 'error', 'message': 'No search query provided.'})

    results = []

    # Try NIST NVD API first
    try:
        if query.upper().startswith('CVE-'):
            cve_id = query.upper()
            url = f'https://services.nvd.nist.gov/rest/json/cves/2.0?cveId={cve_id}'
        else:
            encoded_query = urllib.parse.quote(query)
            url = f'https://services.nvd.nist.gov/rest/json/cves/2.0?keywordSearch={encoded_query}&resultsPerPage=10'

        resp = _requests.get(url, timeout=15, headers={
            'User-Agent': 'Yggdrasil-Security-Framework/2.1',
        })

        if resp.status_code == 200:
            data = resp.json()
            vulns = data.get('vulnerabilities', [])
            for v in vulns:
                cve = v.get('cve', {})
                cve_id = cve.get('id', '')
                desc_list = cve.get('descriptions', [])
                desc = next(
                    (d['value'] for d in desc_list if d.get('lang') == 'en'),
                    (desc_list[0]['value'] if desc_list else 'No description')
                )

                # CVSS score
                metrics = cve.get('metrics', {})
                cvss_v3 = metrics.get('cvssMetricV31', metrics.get('cvssMetricV30', []))
                cvss_score = None
                severity = None
                if cvss_v3:
                    cvss_data = cvss_v3[0].get('cvssData', {})
                    cvss_score = cvss_data.get('baseScore')
                    severity = cvss_data.get('baseSeverity')

                published = cve.get('published', '')

                results.append({
                    'id': cve_id,
                    'description': desc[:500],
                    'cvss': cvss_score,
                    'severity': severity or 'N/A',
                    'published': published[:10] if published else 'Unknown',
                    'url': f'https://nvd.nist.gov/vuln/detail/{cve_id}',
                })
    except Exception:
        pass  # Fallback below

    # Fallback: Circl.lu API
    if not results and query.upper().startswith('CVE-'):
        try:
            cve_id = query.upper()
            url = f'https://cve.circl.lu/api/cve/{cve_id}'
            resp = _requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data and 'id' in data:
                    cvss_val = None
                    cvss_data = data.get('cvss', {})
                    if isinstance(cvss_data, dict):
                        cvss_val = cvss_data.get('score')
                    elif isinstance(cvss_data, (int, float)):
                        cvss_val = cvss_data

                    severity = None
                    if cvss_val is not None:
                        if cvss_val >= 9.0:
                            severity = 'CRITICAL'
                        elif cvss_val >= 7.0:
                            severity = 'HIGH'
                        elif cvss_val >= 4.0:
                            severity = 'MEDIUM'
                        else:
                            severity = 'LOW'

                    results.append({
                        'id': data.get('id', cve_id),
                        'description': (data.get('summary') or 'No description')[:500],
                        'cvss': cvss_val,
                        'severity': severity or 'N/A',
                        'published': (data.get('Published') or '')[:10],
                        'url': f'https://nvd.nist.gov/vuln/detail/{cve_id}',
                    })
        except Exception:
            pass

    if not results:
        return jsonify({
            'status': 'success',
            'results': [],
            'message': f'No CVE results found for "{query}".',
        })

    return jsonify({'status': 'success', 'results': results})
