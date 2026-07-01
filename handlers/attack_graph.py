import sqlite3
import uuid
import os
import json

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "stats.db")
GRAPH_SESSION = "default"


def get_graph_data(session_id=None):
    sid = session_id or GRAPH_SESSION
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT node_id, node_type, label, parent_id, data, created_at FROM attack_graph_nodes WHERE session_id=? ORDER BY id ASC', (sid,))
    rows = c.fetchall()
    conn.close()

    parent_map = {r[0]: r[3] for r in rows}

    def compute_depth(node_id):
        d = 0
        seen = set()
        current = node_id
        while current and current not in seen and current in parent_map:
            seen.add(current)
            current = parent_map[current]
            if current:
                d += 1
        return d

    nodes = []
    for r in rows:
        node_id, node_type, label, parent_id, data_str, created_at = r
        data = {}
        try:
            if data_str:
                data = json.loads(data_str)
        except json.JSONDecodeError:
            pass

        nodes.append({
            "id": node_id,
            "node_type": node_type,
            "label": label,
            "parent_id": parent_id,
            "depth": compute_depth(node_id),
            "data": data,
            "created_at": created_at
        })

    return {"status": "success", "nodes": nodes, "session_id": sid}


def add_graph_node(label, node_type, parent_id=None, data=None, session_id=None):
    sid = session_id or GRAPH_SESSION
    node_id = str(uuid.uuid4())[:8]

    if parent_id:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM attack_graph_nodes WHERE node_id=?', (parent_id,))
        if c.fetchone()[0] == 0:
            conn.close()
            return {"status": "error", "message": f"Parent node '{parent_id}' not found."}
        conn.close()

    data_json = json.dumps(data) if data else "{}"

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute(
            'INSERT INTO attack_graph_nodes (session_id, node_id, node_type, label, parent_id, data) VALUES (?, ?, ?, ?, ?, ?)',
            (sid, node_id, node_type, label, parent_id, data_json)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return {"status": "error", "message": "Node ID conflict."}
    conn.close()

    return {"status": "success", "node_id": node_id, "label": label, "node_type": node_type}


def remove_graph_node(node_id, session_id=None):
    sid = session_id or GRAPH_SESSION
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM attack_graph_nodes WHERE node_id=? AND session_id=?', (node_id, sid))
    deleted = c.rowcount
    c.execute('UPDATE attack_graph_nodes SET parent_id=NULL WHERE parent_id=? AND session_id=?', (node_id, sid))
    conn.commit()
    conn.close()
    return {"status": "success", "deleted": deleted}


def reset_graph(session_id=None):
    sid = session_id or GRAPH_SESSION
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM attack_graph_nodes WHERE session_id=?', (sid,))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Attack graph reset."}


def auto_populate_from_scans(target, session_id=None):
    sid = session_id or GRAPH_SESSION
    root = add_graph_node(target, "target", parent_id=None, data={"type": "root_target"}, session_id=sid)
    if root["status"] != "success":
        return root

    root_id = root["node_id"]

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        'SELECT tool, output FROM scan_history WHERE target=? AND status=? ORDER BY id DESC LIMIT 15',
        (target, 'SUCCESS')
    )
    rows = c.fetchall()
    conn.close()

    found_ports = set()
    found_vulns = set()
    found_subdomains = set()

    for tool_name, output in rows:
        if not output:
            continue

        tool_lower = tool_name.lower()

        if any(t in tool_lower for t in ['nmap', 'port']):
            for line in output.split('\n'):
                if '/tcp' in line or '/udp' in line:
                    port_info = line.strip()[:80]
                    if port_info not in found_ports:
                        found_ports.add(port_info)
                        add_graph_node(port_info[:60], "port", parent_id=root_id, data={"raw": line.strip()[:200]}, session_id=sid)

        if any(t in tool_lower for t in ['subfinder', 'dns', 'subdomain', 'amass', 'knock']):
            for line in output.split('\n'):
                clean = line.strip()
                if clean and '.' in clean and not clean.startswith('[') and len(clean) < 200:
                    if clean not in found_subdomains:
                        found_subdomains.add(clean)
                        add_graph_node(clean[:60], "subdomain", parent_id=root_id, data={"raw": clean}, session_id=sid)

        if any(t in tool_lower for t in ['vuln', 'nuclei', 'nikto', 'wpscan', 'searchsploit']):
            for line in output.split('\n'):
                clean = line.strip()
                if clean and any(kw in clean.upper() for kw in ['CVE', 'VULN', 'CRITICAL', 'HIGH', 'MEDIUM']):
                    if clean not in found_vulns:
                        found_vulns.add(clean)
                        add_graph_node(clean[:80], "vuln", parent_id=root_id, data={"raw": clean}, session_id=sid)

    return {
        "status": "success",
        "root_id": root_id,
        "ports_found": len(found_ports),
        "subdomains_found": len(found_subdomains),
        "vulns_found": len(found_vulns)
    }
