"""
Odin Autonomous Agent — ReAct (Reasoning + Acting) Loop
Odin plans strategy, executes Yggdrasil tools, parses output via Heimdall,
and iterates until the mission is complete or safety limits are reached.
Runs in a background thread. Frontend polls /api/agent/status for live updates.
"""
import json
import time
import threading
import re
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from tools_config import TOOLS_CONFIG
MAX_STEPS = 8
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
def _get_tool_config(tool_key):
    """Get tool config from TOOLS_CONFIG with safe default."""
    return TOOLS_CONFIG.get(tool_key, {})
def _run_tool_direct(tool_key, target, extra_data=None):
    """
    Execute a Yggdrasil tool directly (synchronous, for agent use).
    Uses the same execution path as app.py's execute_tool.
    """
    import subprocess
    import platform
    import shlex
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
    """
    Ask Odin (LLM) to decide the next action based on current state.
    Falls back to rule-based decisions if Ollama is unavailable.
    """
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
    """Rule-based fallback when Ollama is unavailable."""
    steps = session["steps"]
    target = session["target"]
    step_count = len(steps)
    is_ip = any(c.isdigit() for c in target.replace(".", "")[:4]) and "." in target
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
            "Review the findings in the terminal windows. "
            "Recommend manual verification of discovered services and potential exploitation of identified vulnerabilities."
        )}
    if step_count >= 4:
        all_output = " ".join(s.get("output", "") for s in steps).lower()
        if "critical" in all_output or "vulnerability" in all_output:
            return {"action": "DONE", "summary": (
                f"Autonomous scan complete after {step_count+1} steps on {target}. "
                "Vulnerabilities detected — review terminal output and consider exploitation phase."
            )}
    return {"action": "DONE", "summary": (
        f"Mission complete after {step_count+1} automated steps on {target}. "
        "All scan results are available in the terminal windows for manual review."
    )}
def _parse_step_output(output, tool_name):
    """Try to get a quick summary of tool output (lightweight, no LLM needed)."""
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
def run_agent_loop(session_id, target):
    """
    Main ReAct loop. Runs in background thread.
    Thought → Action → Observation → Thought → ...
    """
    session = {
        "id": session_id,
        "target": target,
        "status": "running",
        "steps": [],
        "started_at": time.time(),
        "final_summary": ""
    }
    ACTIVE_SESSIONS[session_id] = session
    try:
        while len(session["steps"]) < MAX_STEPS:
            if session.get("status") != "running":
                return
            session["current_phase"] = "thinking"
            decision = _odin_decide(session)
            if decision.get("action") == "DONE":
                session["status"] = "completed"
                session["final_summary"] = decision.get("summary", "Mission complete.")
                session["current_phase"] = "done"
                return
            if decision.get("action") != "RUN":
                session["status"] = "completed"
                session["final_summary"] = "Agent stopped: No valid action decided."
                session["current_phase"] = "done"
                return
            tool_key = decision.get("tool", "")
            reasoning = decision.get("reasoning", "")
            if tool_key not in ALLOWED_TOOLS and tool_key not in ESCALATION_TOOLS:
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
                step["output"] = output[:5000]  # Keep storage manageable
            except Exception as e:
                step["status"] = "error"
                step["output"] = f"Error: {str(e)}"
            session["current_phase"] = "observing"
            step["summary"] = _parse_step_output(step.get("output", ""), tool_key)
            if len(session["steps"]) >= SCOPE_WARNING_STEPS:
                session["scope_warning"] = (
                    f"Approaching safety limit ({MAX_STEPS} steps). "
                    "Agent will complete soon."
                )
        session["status"] = "completed"
        session["final_summary"] = (
            f"Maximum steps ({MAX_STEPS}) reached for autonomous scan on {target}. "
            "Review all terminal outputs for findings."
        )
        session["current_phase"] = "done"
    except Exception as e:
        session["status"] = "error"
        session["final_summary"] = f"Agent error: {str(e)}"
        session["current_phase"] = "error"
def start_agent(target):
    """Start an autonomous agent session. Returns session_id."""
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
    thread = threading.Thread(
        target=run_agent_loop,
        args=(session_id, target),
        daemon=True
    )
    thread.start()
    return {
        "status": "success",
        "session_id": session_id,
        "message": f"Autonomous agent started on {target}. Max {MAX_STEPS} steps.",
        "max_steps": MAX_STEPS
    }
def get_agent_status(session_id):
    """Get current state of an agent session."""
    session = ACTIVE_SESSIONS.get(session_id)
    if not session:
        return {"status": "error", "message": "Session not found."}
    return {
        "status": "success",
        "session": {
            "id": session["id"],
            "target": session["target"],
            "status": session["status"],
            "current_phase": session.get("current_phase", ""),
            "current_tool": session.get("current_tool", ""),
            "current_step": session.get("current_step", 0),
            "total_steps": len(session.get("steps", [])),
            "max_steps": MAX_STEPS,
            "final_summary": session.get("final_summary", ""),
            "scope_warning": session.get("scope_warning", ""),
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
    """Force-stop a running agent session."""
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
    """List all agent sessions (active and completed)."""
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
