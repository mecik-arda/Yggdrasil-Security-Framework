import json
import time
import threading
import re
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from tools_config import TOOLS_CONFIG
MAX_STEPS = 8
REDTEAM_MAX_STEPS = 15
SCOPE_WARNING_STEPS = 6
ACTIVE_SESSIONS = {}
ALLOWED_TOOLS = [
    "nmap", "nmap_stealth", "nmap_banner", "nmap_vuln", "nmap_tcp",
    "whois", "dnsenum", "dnsrecon", "dig", "nslookup",
    "subfinder", "assetfinder", "amass", "theharvester",
    "nikto", "wafw00f", "whatweb", "gobuster_dns",
    "nuclei", "searchsploit", "nmap_vulners",
    "sherlock", "traceroute", "dirb",
]
ESCALATION_TOOLS = [
    "hydra", "sqlmap", "commix", "wpscan", "wapiti",
    "fenrir", "erebus",
]
REDTEAM_TOOLS = [
    "sqlmap", "hydra", "commix", "nuclei", "searchsploit",
    "nmap_vuln", "nmap_vulners", "nikto", "dirb", "gobuster_dns",
    "wpscan", "wapiti",
]
def _get_tool_config(tool_key):
    return TOOLS_CONFIG.get(tool_key, {})
def _run_tool_direct(tool_key, target, extra_data=None):
    import subprocess
    config = _get_tool_config(tool_key)
    if not config:
        return f"Error: Unknown tool '{tool_key}'"
    tool_type = config.get("type")
    if tool_type == "cli":
        cmd_template = config.get("cmd", [])
        cmd = [arg.format(target=target) if "{target}" in arg else arg for arg in cmd_template]
        try:
            result = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=120).decode("utf-8", errors="replace")
            return result
        except subprocess.TimeoutExpired:
            return "TIMEOUT: Process took too long"
        except subprocess.CalledProcessError as e:
            return f"Execution Error:\n{e.output.decode('utf-8', errors='replace')}"
        except Exception as e:
            return f"System Error: {str(e)}"
    elif tool_type in ("custom_script", "custom_html"):
        from handlers import dispatch_handler
        handler_name = config.get("handler")
        if handler_name:
            try:
                return dispatch_handler(handler_name, target, extra_data or {})
            except Exception as e:
                return f"Handler Error: {str(e)}"
        return f"Error: No handler for '{tool_key}'"
    elif tool_type == "script":
        cmd_template = config.get("cmd", [])
        cmd = [arg.format(target=target) if "{target}" in arg else arg for arg in cmd_template]
        try:
            result = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=120).decode("utf-8", errors="replace")
            return result
        except Exception as e:
            return f"Execution Error: {str(e)}"
    return f"Error: Unsupported tool type '{tool_type}'"
def _odin_decide(session):
    from handlers.ai_engine import chat_completion, _check_ollama
    ok, models = _check_ollama()
    if not ok or not models:
        return _fallback_decide(session)
    model_names = [m["name"] for m in models]
    preferred = None
    for c in ["deepseek-r1:14b", "qwen2.5-coder:7b", "llama3.2:3b", "mistral:7b"]:
        base = c.split(":")[0]
        for m in model_names:
            if base in m:
                preferred = m
                break
        if preferred:
            break
    if not preferred:
        preferred = model_names[0]
    history_text = ""
    for i, step in enumerate(session["steps"]):
        history_text += f"\nStep {i+1}: Ran '{step['tool']}' on {step.get('target', session['target'])}\n"
        history_text += f"Result summary: {step.get('summary', 'No summary')[:300]}\n"
    available_tools = ALLOWED_TOOLS + (ESCALATION_TOOLS if len(session["steps"]) >= 2 else [])
    system = (
        "You are Odin, the master supervisor agent of the Yggdrasil Security Framework. "
        "You autonomously conduct penetration testing by deciding which security tools to run next. "
        "You always respond with ONLY a valid JSON object, no other text."
    )
    user = f"""Target: {session['target']}
Steps completed: {len(session['steps'])}/{MAX_STEPS}
{history_text}
Available tools: {', '.join(available_tools[:25])}
Decide the next action. Return JSON:
If you need to run another tool:
{{"action": "RUN", "tool": "tool_key", "target": "{session['target']}", "reasoning": "why this tool now"}}
If the mission is complete or you have enough information:
{{"action": "DONE", "summary": "Final summary of all findings and recommendations"}}"""
    try:
        result = chat_completion(preferred, [
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ])
        if result.get("status") == "success":
            content = result.get("response", "")
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                try:
                    return json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    pass
    except Exception:
        pass
    return _fallback_decide(session)
def _fallback_decide(session):
    steps = session["steps"]
    target = session["target"]
    step_count = len(steps)
    mode = session.get("mode", "recon")
    is_ip = any(c.isdigit() for c in target.replace(".", "")[:4]) and "." in target

    if mode == "redteam":
        return _redteam_decide(session, steps, target, step_count, is_ip)

    if step_count == 0:
        if is_ip:
            return {"action": "RUN", "tool": "nmap", "target": target,
                    "reasoning": "Starting with comprehensive Nmap scan to discover open ports and services."}
        else:
            return {"action": "RUN", "tool": "whois", "target": target,
                    "reasoning": "Starting with WHOIS to gather domain registration information."}
    if step_count == 1:
        if not is_ip:
            return {"action": "RUN", "tool": "subfinder", "target": target,
                    "reasoning": "Enumerating subdomains to map the attack surface."}
        output = steps[-1].get("output", "").lower()
        if any(p in output for p in ["80/tcp", "443/tcp", "8080/tcp", "http", "www"]):
            return {"action": "RUN", "tool": "nikto", "target": target,
                    "reasoning": "Web services detected. Running Nikto for web vulnerability scanning."}
        if "445/tcp" in output or "smb" in output:
            return {"action": "RUN", "tool": "nmap_vuln", "target": target,
                    "reasoning": "SMB port detected. Running vulnerability scan for known SMB exploits."}
        return {"action": "RUN", "tool": "nmap_vuln", "target": target,
                "reasoning": "Running targeted vulnerability scan based on discovered services."}
    if step_count == 2:
        output = steps[-1].get("output", "").lower()
        if any(p in output for p in ["80/tcp", "443/tcp", "http"]):
            return {"action": "RUN", "tool": "dirb", "target": target,
                    "reasoning": "Web service found. Running directory brute-force to discover hidden paths."}
        return {"action": "RUN", "tool": "nuclei", "target": target,
                "reasoning": "Running Nuclei templates for comprehensive vulnerability detection."}
    if step_count == 3:
        output = " ".join(s.get("output", "") for s in steps).lower()
        if "ssh" in output or "22/tcp" in output:
            return {"action": "RUN", "tool": "nmap_banner", "target": target,
                    "reasoning": "SSH detected. Grabbing detailed service banners for version fingerprinting."}
        return {"action": "DONE", "summary": (
            f"Completed {step_count+1} steps of automated reconnaissance on {target}. "
            "Review the findings in the terminal windows."
        )}
    if step_count >= 4:
        all_output = " ".join(s.get("output", "") for s in steps).lower()
        if "critical" in all_output or "vulnerability" in all_output:
            return {"action": "DONE", "summary": (
                f"Autonomous scan complete after {step_count+1} steps on {target}. "
                "Vulnerabilities detected."
            )}
    return {"action": "DONE", "summary": (
        f"Mission complete after {step_count+1} automated steps on {target}."
    )}


def _redteam_decide(session, steps, target, step_count, is_ip):
    REDTEAM_STEPS = REDTEAM_MAX_STEPS

    if step_count == 0:
        if is_ip:
            return {"action": "RUN", "tool": "nmap_tcp", "target": target,
                    "reasoning": "[REDTEAM] Full TCP port scan to map entire attack surface."}

    if step_count == 1:
        output = steps[-1].get("output", "").lower()
        web_ports = [p for p in ["80/tcp", "443/tcp", "8080/tcp", "8443/tcp", "3000/tcp", "5000/tcp", "8000/tcp", "8888/tcp"] if p in output]
        if web_ports:
            session["discovered"] = session.get("discovered", {})
            session["discovered"]["web_ports"] = web_ports
        return {"action": "RUN", "tool": "nmap_vuln", "target": target,
                "reasoning": "[REDTEAM] Vulnerability scan on all discovered services."}

    if step_count == 2:
        output = " ".join(s.get("output", "") for s in steps).lower()
        has_web = any(p in output for p in ["80/tcp", "443/tcp", "8080/tcp", "http"])
        if has_web:
            session["discovered"] = session.get("discovered", {})
            session["discovered"]["has_web"] = True
            return {"action": "RUN", "tool": "nikto", "target": target,
                    "reasoning": "[REDTEAM] Web server detected. Running Nikto for web vulns."}
        return {"action": "RUN", "tool": "nuclei", "target": target,
                "reasoning": "[REDTEAM] Running Nuclei for comprehensive CVE detection."}

    if step_count == 3:
        has_web = session.get("discovered", {}).get("has_web", False)
        if has_web:
            return {"action": "RUN", "tool": "gobuster_dns", "target": target,
                    "reasoning": "[REDTEAM] DNS brute-force for hidden subdomains."}
        return {"action": "RUN", "tool": "nuclei", "target": target,
                "reasoning": "[REDTEAM] Running Nuclei templates."}

    if step_count == 4:
        has_web = session.get("discovered", {}).get("has_web", False)
        if has_web:
            return {"action": "RUN", "tool": "dirb", "target": target,
                    "reasoning": "[REDTEAM] Directory enumeration on web server."}
        return {"action": "RUN", "tool": "searchsploit", "target": target,
                "reasoning": "[REDTEAM] Searching Exploit-DB for known exploits."}

    if step_count == 5:
        output = " ".join(s.get("output", "") for s in steps).lower()
        has_web = session.get("discovered", {}).get("has_web", False)
        has_sql = any(kw in output for kw in ["sql", "mysql", "postgresql", "mariadb", "oracle", "mssql", "3306/tcp", "1433/tcp", "5432/tcp"])
        has_ssh = "22/tcp" in output or "ssh" in output
        has_smb = "445/tcp" in output or "smb" in output

        if has_sql and has_web:
            session["discovered"]["has_sql"] = True
            return {"action": "RUN", "tool": "sqlmap", "target": target,
                    "reasoning": "[REDTEAM] SQL service and web detected. Launching SQLMap for SQLi."}

        if has_ssh:
            session["discovered"]["has_ssh"] = True

        if has_smb:
            session["discovered"]["has_smb"] = True

        return {"action": "RUN", "tool": "nuclei", "target": target,
                "reasoning": "[REDTEAM] Additional Nuclei scan with all templates."}

    if step_count in (6, 7):
        has_ssh = session.get("discovered", {}).get("has_ssh", False)
        has_smb = session.get("discovered", {}).get("has_smb", False)
        has_sql = session.get("discovered", {}).get("has_sql", False)

        if has_sql and step_count == 6:
            return {"action": "RUN", "tool": "sqlmap", "target": target,
                    "reasoning": "[REDTEAM] Deep SQLMap scan with --dbs enumeration."}

        if has_ssh and step_count == 6:
            session["discovered"]["hydra_on_ssh"] = True
            return {"action": "RUN", "tool": "hydra", "target": target,
                    "reasoning": "[REDTEAM] Initiating Hydra brute-force on SSH."}

        if has_smb and step_count == 7:
            return {"action": "RUN", "tool": "nmap_vuln", "target": target,
                    "reasoning": "[REDTEAM] Deep SMB vulnerability scan for EternalBlue and related exploits."}

        return {"action": "RUN", "tool": "nuclei", "target": target,
                "reasoning": "[REDTEAM] Running comprehensive vulnerability assessment."}

    if step_count >= 8:
        all_output = " ".join(s.get("output", "") for s in steps).lower()
        vuln_indicators = ["critical", "cve-", "exploit", "vulnerable", "sql injection", "xss", "rce", "lfi", "bypass"]
        found_vulns = [v for v in vuln_indicators if v in all_output]

        if found_vulns:
            session["discovered"] = session.get("discovered", {})
            session["discovered"]["confirmed_vulns"] = found_vulns
            if step_count < REDTEAM_STEPS - 2:
                return {"action": "RUN", "tool": "searchsploit", "target": target,
                        "reasoning": f"[REDTEAM] Found: {', '.join(found_vulns[:3])}. Searching for exploit code."}

        if step_count < REDTEAM_STEPS - 2:
            return {"action": "RUN", "tool": "nuclei", "target": target,
                    "reasoning": "[REDTEAM] Continuing deep scan for additional vulnerabilities."}

    return {"action": "DONE", "summary": (
        f"[REDTEAM] Autonomous operation complete on {target}. "
        f"Ran {step_count+1} steps. "
        + ("Vulnerabilities found: " + ", ".join(session.get("discovered", {}).get("confirmed_vulns", [])) + ". "
           if session.get("discovered", {}).get("confirmed_vulns") else "No critical vulnerabilities confirmed. ")
        + "Review all terminal outputs and attack graph for details."
    )}
def _parse_step_output(output, tool_name):
    if not output:
        return "No output"
    lines = output.strip().split("\n")
    if tool_name in ("nmap", "nmap_tcp", "nmap_stealth", "nmap_vuln"):
        open_ports = [l for l in lines if "/tcp" in l and "open" in l]
        if open_ports:
            return f"Found {len(open_ports)} open ports: " + ", ".join(p.strip()[:40] for p in open_ports[:5])
        return "Nmap scan completed. Check output for details."
    if tool_name == "subfinder":
        found = [l for l in lines if "." in l and not l.startswith("[")]
        return f"Found {len(found)} subdomains."
    if tool_name == "whois":
        return "WHOIS lookup completed."
    if tool_name == "nikto":
        vulns = [l for l in lines if "+" in l or "OSVDB" in l or "CVE" in l.upper()]
        return f"Nikto found {len(vulns)} potential issues." if vulns else "Nikto scan completed."
    if tool_name == "nuclei":
        found = [l for l in lines if "critical" in l.lower() or "high" in l.lower() or "medium" in l.lower()]
        return f"Nuclei found {len(found)} potential vulnerabilities." if found else "Nuclei scan completed."
    if tool_name == "dirb":
        found = [l for l in lines if "CODE:200" in l or "==>" in l]
        return f"Dirb found {len(found)} accessible paths." if found else "Dirb scan completed."
    meaningful = [l for l in lines if len(l.strip()) > 10][:3]
    summary = " | ".join(meaningful) if meaningful else "Output received"
    return summary[:200]
def run_agent_loop(session_id, target, mode="recon"):
    max_steps = REDTEAM_MAX_STEPS if mode == "redteam" else MAX_STEPS
    session = {
        "id": session_id,
        "target": target,
        "status": "running",
        "mode": mode,
        "steps": [],
        "started_at": time.time(),
        "final_summary": "",
        "discovered": {}
    }
    ACTIVE_SESSIONS[session_id] = session
    allowed = ALLOWED_TOOLS + (REDTEAM_TOOLS if mode == "redteam" else []) + ESCALATION_TOOLS
    try:
        while len(session["steps"]) < max_steps:
            if session.get("status") != "running":
                return
            session["current_phase"] = "thinking"
            decision = _odin_decide(session)
            if decision.get("action") == "DONE":
                session["status"] = "completed"
                session["final_summary"] = decision.get("summary", "Mission complete.")
                session["current_phase"] = "done"
                _auto_populate_graph(target, session)
                return
            if decision.get("action") != "RUN":
                session["status"] = "completed"
                session["final_summary"] = "Agent stopped: No valid action decided."
                session["current_phase"] = "done"
                return
            tool_key = decision.get("tool", "")
            reasoning = decision.get("reasoning", "")
            if tool_key not in allowed and tool_key not in ESCALATION_TOOLS:
                session["steps"].append({
                    "step": len(session["steps"]) + 1,
                    "tool": tool_key,
                    "target": target,
                    "reasoning": reasoning,
                    "status": "blocked",
                    "summary": f"Tool '{tool_key}' is not in autonomous whitelist."
                })
                continue
            session["current_phase"] = "executing"
            session["current_tool"] = tool_key
            session["current_step"] = len(session["steps"]) + 1
            step = {
                "step": len(session["steps"]) + 1,
                "tool": tool_key,
                "target": target,
                "reasoning": reasoning,
                "status": "running"
            }
            session["steps"].append(step)
            try:
                output = _run_tool_direct(tool_key, target)
                step["status"] = "completed"
                step["output"] = output[:5000]
            except Exception as e:
                step["status"] = "error"
                step["output"] = f"Error: {str(e)}"
            session["current_phase"] = "observing"
            step["summary"] = _parse_step_output(step.get("output", ""), tool_key)
            scope_limit = max_steps - 2
            if len(session["steps"]) >= scope_limit:
                session["scope_warning"] = (
                    f"Approaching safety limit ({max_steps} steps). "
                    "Agent will complete soon."
                )
        session["status"] = "completed"
        session["final_summary"] = (
            f"Maximum steps ({max_steps}) reached for autonomous scan on {target}. "
            "Review all terminal outputs for findings."
        )
        session["current_phase"] = "done"
        _auto_populate_graph(target, session)
    except Exception as e:
        session["status"] = "error"
        session["final_summary"] = f"Agent error: {str(e)}"
        session["current_phase"] = "error"


def _auto_populate_graph(target, session):
    try:
        from handlers.attack_graph import auto_populate_from_scans
        mode = session.get("mode", "recon")
        sid = "redteam_" + session.get("id", "anon") if mode == "redteam" else "recon_" + session.get("id", "anon")
        auto_populate_from_scans(target, sid)
    except Exception:
        pass


def start_agent(target, mode="recon"):
    import uuid
    session_id = str(uuid.uuid4())[:8]
    if not target or len(target.strip()) < 2:
        return {"status": "error", "message": "Valid target required."}
    target = target.strip()
    for sid, s in list(ACTIVE_SESSIONS.items()):
        if s.get("status") == "running" and s.get("target") == target:
            return {
                "status": "error",
                "message": f"An autonomous scan is already running on {target} (Session: {sid})."
            }
    import re as _re
    if not _re.match(r'^[\w\.\-\:\@]+$', target):
        return {"status": "error", "message": "Invalid target format. Banned characters detected."}

    if mode == "redteam":
        from handlers.attack_graph import add_graph_node
        add_graph_node(target, "target", parent_id=None, data={"type": "redteam_root"}, session_id="redteam_" + session_id)

    max_steps = REDTEAM_MAX_STEPS if mode == "redteam" else MAX_STEPS
    thread = threading.Thread(
        target=run_agent_loop,
        args=(session_id, target, mode),
        daemon=True
    )
    thread.start()
    return {
        "status": "success",
        "session_id": session_id,
        "message": f"Autonomous agent started on {target}. Max {max_steps} steps. Mode: {mode}.",
        "max_steps": max_steps,
        "mode": mode
    }
def get_agent_status(session_id):
    session = ACTIVE_SESSIONS.get(session_id)
    if not session:
        return {"status": "error", "message": "Session not found."}
    mode = session.get("mode", "recon")
    return {
        "status": "success",
        "session": {
            "id": session["id"],
            "target": session["target"],
            "status": session["status"],
            "mode": mode,
            "current_phase": session.get("current_phase", ""),
            "current_tool": session.get("current_tool", ""),
            "current_step": session.get("current_step", 0),
            "total_steps": len(session.get("steps", [])),
            "max_steps": REDTEAM_MAX_STEPS if mode == "redteam" else MAX_STEPS,
            "final_summary": session.get("final_summary", ""),
            "scope_warning": session.get("scope_warning", ""),
            "discovered": session.get("discovered", {}),
            "steps": [
                {
                    "step": s["step"],
                    "tool": s["tool"],
                    "target": s.get("target", ""),
                    "reasoning": s.get("reasoning", ""),
                    "status": s["status"],
                    "summary": s.get("summary", "")
                }
                for s in session.get("steps", [])
            ]
        }
    }
def stop_agent(session_id):
    session = ACTIVE_SESSIONS.get(session_id)
    if not session:
        return {"status": "error", "message": "Session not found."}
    if session.get("status") != "running":
        return {"status": "error", "message": "Session is not running."}
    session["status"] = "stopped"
    session["final_summary"] = "Agent stopped by user."
    session["current_phase"] = "stopped"
    return {"status": "success", "message": f"Session {session_id} stopped."}
def list_agent_sessions():
    return {
        "status": "success",
        "sessions": [
            {
                "id": s["id"],
                "target": s["target"],
                "status": s["status"],
                "steps": len(s.get("steps", [])),
                "started_at": s.get("started_at", 0)
            }
            for s in ACTIVE_SESSIONS.values()
        ]
    }
