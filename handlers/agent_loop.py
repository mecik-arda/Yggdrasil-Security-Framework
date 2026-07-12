"""
Odin Autonomous Agent — Native Tool Calling (Phase 2.3)

Replaces the previous ReAct text-parsing loop with Ollama's native
JSON Function Calling API.  Tools from ``tools_config`` are converted
into JSON tool schemas at runtime and fed to the LLM, which returns
structured ``tool_calls`` that are executed directly.

Role distribution:
  - Odin  : orchestrator — decides which tool to run, manages the main loop
  - Loki  : specialist  — called by Odin for WAF bypass / payload mutation
  - Kvasir: RAG module  — provides offline knowledge when needed
"""

import json
import time
import threading
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from tools_config import TOOLS_CONFIG

# ── configuration (overridable via settings) ────────────────────────────────
DEFAULT_MAX_STEPS = 10          # default autonomous step limit
REDTEAM_MAX_STEPS = 15
SCOPE_WARNING_STEPS = 6
ACTIVE_SESSIONS = {}

# Tool whitelists
ALLOWED_TOOLS = [
    "nmap", "nmap_stealth", "nmap_banner", "nmap_vuln", "nmap_tcp",
    "whois", "dnsenum", "dnsrecon", "dig", "nslookup",
    "subfinder", "assetfinder", "amass", "theharvester",
    "nikto", "wafw00f", "whatweb", "gobuster_dns", "gobuster_dir",
    "nuclei", "searchsploit", "nmap_vulners",
    "sherlock", "traceroute", "dirb", "ffuf", "feroxbuster",
    "arp_scan", "netdiscover",
]

ESCALATION_TOOLS = [
    "hydra", "sqlmap", "commix", "wpscan", "wapiti",
    "fenrir", "erebus", "xsser",
]

REDTEAM_TOOLS = [
    "sqlmap", "hydra", "commix", "nuclei", "searchsploit",
    "nmap_vuln", "nmap_vulners", "nikto", "dirb", "gobuster_dns",
    "wpscan", "wapiti", "xsser",
    "impacket_psexec", "impacket_secretsdump", "impacket_smbexec",
    "evil_winrm",
]

# ── helper ──────────────────────────────────────────────────────────────────

def _get_tool_config(tool_key):
    return TOOLS_CONFIG.get(tool_key, {})


def _run_tool_direct(tool_key, target, extra_data=None):
    """Execute a tool synchronously and return its output string."""
    import subprocess
    config = _get_tool_config(tool_key)
    if not config:
        return f"Error: Unknown tool '{tool_key}'"

    tool_type = config.get("type")

    if tool_type == "cli":
        cmd_template = config.get("cmd", [])
        cmd = [arg.format(target=target) if "{target}" in arg else arg
               for arg in cmd_template]
        try:
            result = subprocess.check_output(
                cmd, stderr=subprocess.STDOUT, timeout=120
            ).decode("utf-8", errors="replace")
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
        cmd = [arg.format(target=target) if "{target}" in arg else arg
               for arg in cmd_template]
        try:
            result = subprocess.check_output(
                cmd, stderr=subprocess.STDOUT, timeout=120
            ).decode("utf-8", errors="replace")
            return result
        except Exception as e:
            return f"Execution Error: {str(e)}"

    elif tool_type == "gui":
        from core.tool_runner import execute_tool
        return execute_tool(tool_key, target, extra_data)

    return f"Error: Unsupported tool type '{tool_type}'"


# ── context pruning ─────────────────────────────────────────────────────────

def _prune_output(output, max_chars=3000):
    """Trim large tool outputs so they fit inside the LLM context window.

    Keeps the first 300 chars (header) and last 2700 chars (findings tail).
    """
    if not output:
        return "(no output)"
    if len(output) <= max_chars:
        return output
    head = output[:300]
    tail = output[-2700:]
    return (
        f"{head}\n\n... [PRUNED: {len(output) - max_chars} chars omitted] ...\n\n{tail}"
    )


# ── Native Tool Calling: build schemas from TOOLS_CONFIG ────────────────────

def _build_agent_tool_schemas(tool_keys):
    """Convert a list of ``tool_keys`` into Ollama/OpenAI-compatible function schemas.

    Each schema describes one security tool as a callable function.  Only tools
    that accept a ``target`` parameter add it as a required argument; no-target
    tools are also exposed.
    """
    schemas = []
    for key in tool_keys:
        cfg = TOOLS_CONFIG.get(key)
        if not cfg:
            continue

        name = key
        desc = cfg.get("name", key)
        needs_target = cfg.get("requires_target", False)
        category = cfg.get("category", "unknown")

        properties = {}
        required = []

        if needs_target:
            properties["target"] = {
                "type": "string",
                "description": "IP address or domain name to scan"
            }
            required.append("target")

        # always add an optional reason field so the agent can explain itself
        properties["reason"] = {
            "type": "string",
            "description": "Why this tool is being called now"
        }

        schemas.append({
            "type": "function",
            "function": {
                "name": name,
                "description": f"[{category}] {desc}. "
                               f"Target required: {needs_target}.",
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        })

    # add a DONE "function" so the agent can signal completion
    schemas.append({
        "type": "function",
        "function": {
            "name": "mission_complete",
            "description": "Signal that the autonomous mission is complete. "
                           "Call this when you have gathered sufficient information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "Final summary of findings and recommendations"
                    }
                },
                "required": ["summary"],
            },
        },
    })

    return schemas


# ── Native Ollama chat with tool schemas ────────────────────────────────────

def _native_chat(model, messages, tools, endpoint=None):
    """Send a chat completion to Ollama with native tool-calling support.

    Parameters
    ----------
    model : str
        Ollama model name.
    messages : list[dict]
        Chat history in OpenAI format.
    tools : list[dict]
        Tool schemas (function definitions).
    endpoint : str | None
        Optional custom endpoint URL (for Docker/WSL models).

    Returns
    -------
    dict  — ``{status, response | message, tool_calls | None}``
    """
    import requests as _requests
    base = endpoint or "http://localhost:11434"

    try:
        payload = {
            "model": model,
            "messages": messages,
            "tools": tools,
            "stream": False,
        }
        resp = _requests.post(
            f"{base}/api/chat",
            json=payload,
            timeout=180,
        )
        if resp.status_code == 200:
            data = resp.json()
            msg = data.get("message", {})
            content = msg.get("content", "")
            tool_calls = msg.get("tool_calls", None)
            return {
                "status": "success",
                "response": content,
                "tool_calls": tool_calls,
                "model": model,
            }
        else:
            return {
                "status": "error",
                "message": f"Ollama API error (HTTP {resp.status_code}): {resp.text[:200]}"
            }
    except _requests.Timeout:
        return {"status": "error", "message": "Timeout: AI didn't respond in 180s."}
    except Exception as e:
        return {"status": "error", "message": f"AI engine error: {str(e)}"}


# ── decision engine (native tool calling) ───────────────────────────────────

def _odin_decide_native(session, available_tools):
    """Ask the LLM to pick the next action using native tool calling.

    Falls back to the rule-based ``_fallback_decide`` when no LLM is available.
    """
    from handlers.ai_engine import _check_ollama

    ok, models = _check_ollama()
    if not ok or not models:
        return _fallback_decide(session)

    # pick best available model
    model_names = [m["name"] for m in models]
    preferred = None
    for candidate in ["deepseek-r1:14b", "qwen2.5-coder:7b",
                       "llama3.2:3b", "mistral:7b"]:
        base = candidate.split(":")[0]
        for m in model_names:
            if base in m:
                preferred = m
                break
        if preferred:
            break
    if not preferred:
        preferred = model_names[0]

    # build conversation
    messages = _build_native_messages(session, available_tools)
    tools = _build_agent_tool_schemas(available_tools)

    result = _native_chat(preferred, messages, tools)

    if result.get("status") != "success":
        return _fallback_decide(session)

    tool_calls = result.get("tool_calls")

    # If the model returned tool_calls, extract the first one
    if tool_calls and len(tool_calls) > 0:
        tc = tool_calls[0]
        fn = tc.get("function", {})
        fn_name = fn.get("name", "")
        fn_args = fn.get("arguments", {})

        # Handle string args (some models return JSON strings)
        if isinstance(fn_args, str):
            try:
                fn_args = json.loads(fn_args)
            except json.JSONDecodeError:
                pass

        if fn_name == "mission_complete":
            summary = fn_args.get("summary", "Mission complete.") if isinstance(fn_args, dict) else "Mission complete."
            return {"action": "DONE", "summary": summary}

        if fn_name in available_tools or fn_name in ESCALATION_TOOLS:
            target = fn_args.get("target", session["target"]) if isinstance(fn_args, dict) else session["target"]
            reasoning = fn_args.get("reason", "AI selected this tool.") if isinstance(fn_args, dict) else "AI selected this tool."
            return {
                "action": "RUN",
                "tool": fn_name,
                "target": target,
                "reasoning": reasoning,
            }

    # If the model returned a text response, try to parse it as JSON
    content = result.get("response", "")
    if content:
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            try:
                parsed = json.loads(json_match.group(0))
                if parsed.get("action") == "DONE":
                    return parsed
                if parsed.get("action") == "RUN":
                    return parsed
            except json.JSONDecodeError:
                pass

    return _fallback_decide(session)


def _build_native_messages(session, available_tools):
    """Build the LLM conversation history for the current session."""
    system = (
        "You are Odin, the master supervisor agent of the Yggdrasil Security Framework. "
        "You autonomously conduct penetration testing by calling security tools via "
        "function calls. You have access to native tool calling — use the provided "
        "functions to run security tools against the target. "
        "Always call the appropriate function instead of describing what to do. "
        "When you have enough information, call mission_complete with a thorough summary."
    )

    tool_list = ", ".join(available_tools[:30])
    user = (
        f"Target: {session['target']}\n"
        f"Mode: {session.get('mode', 'recon')}\n"
        f"Steps completed: {len(session['steps'])}/{session.get('max_steps', DEFAULT_MAX_STEPS)}\n"
        f"Available tools: {tool_list}\n"
        f"Use function calling to select and run the next tool."
    )

    msgs = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

    # Inject step history as function call / result pairs
    for step in session["steps"]:
        tool_name = step["tool"]
        msgs.append({
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": f"call_{step['step']}",
                "type": "function",
                "function": {
                    "name": tool_name,
                    "arguments": json.dumps({
                        "target": step.get("target", session["target"]),
                        "reason": step.get("reasoning", ""),
                    }),
                },
            }],
        })
        # Feed back the tool result
        output_preview = _prune_output(step.get("output", ""), 1500)
        msgs.append({
            "role": "tool",
            "content": f"Tool '{tool_name}' output:\n{output_preview}",
            "tool_call_id": f"call_{step['step']}",
        })

    return msgs


# ── fallback (rule-based, no LLM required) ──────────────────────────────────

def _fallback_decide(session):
    """Deterministic fallback when no LLM is available."""
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
                    "reasoning": "Starting with comprehensive Nmap scan."}
        else:
            return {"action": "RUN", "tool": "whois", "target": target,
                    "reasoning": "Starting with WHOIS lookup."}

    if step_count == 1:
        if not is_ip:
            return {"action": "RUN", "tool": "subfinder", "target": target,
                    "reasoning": "Enumerating subdomains."}
        output = steps[-1].get("output", "").lower()
        if any(p in output for p in ["80/tcp", "443/tcp", "8080/tcp", "http"]):
            return {"action": "RUN", "tool": "nikto", "target": target,
                    "reasoning": "Web services detected. Running Nikto."}
        if "445/tcp" in output or "smb" in output:
            return {"action": "RUN", "tool": "nmap_vuln", "target": target,
                    "reasoning": "SMB port detected. Vulnerability scan."}
        return {"action": "RUN", "tool": "nmap_vuln", "target": target,
                "reasoning": "Running vulnerability scan."}

    if step_count == 2:
        output = steps[-1].get("output", "").lower()
        if any(p in output for p in ["80/tcp", "443/tcp", "http"]):
            return {"action": "RUN", "tool": "gobuster_dir", "target": target,
                    "reasoning": "Directory brute-force on web server."}
        return {"action": "RUN", "tool": "nuclei", "target": target,
                "reasoning": "Nuclei template scan."}

    if step_count == 3:
        output = " ".join(s.get("output", "") for s in steps).lower()
        if "ssh" in output or "22/tcp" in output:
            return {"action": "RUN", "tool": "nmap_banner", "target": target,
                    "reasoning": "SSH detected. Banner grabbing."}
        return {"action": "DONE", "summary": (
            f"Completed {step_count + 1} steps on {target}. Review findings."
        )}

    if step_count >= 4:
        all_output = " ".join(s.get("output", "") for s in steps).lower()
        if "critical" in all_output or "vulnerability" in all_output:
            return {"action": "DONE", "summary": (
                f"Autonomous scan complete after {step_count + 1} steps. Vulnerabilities detected."
            )}

    return {"action": "DONE", "summary": (
        f"Mission complete after {step_count + 1} steps on {target}."
    )}


def _redteam_decide(session, steps, target, step_count, is_ip):
    """Deterministic Red Team decision logic."""
    REDTEAM_STEPS = session.get("max_steps", REDTEAM_MAX_STEPS)

    if step_count == 0:
        if is_ip:
            return {"action": "RUN", "tool": "nmap_tcp", "target": target,
                    "reasoning": "[REDTEAM] Full TCP port scan."}

    if step_count == 1:
        output = steps[-1].get("output", "").lower()
        web_ports = [p for p in [
            "80/tcp", "443/tcp", "8080/tcp", "8443/tcp",
            "3000/tcp", "5000/tcp", "8000/tcp", "8888/tcp"
        ] if p in output]
        if web_ports:
            session.setdefault("discovered", {})["web_ports"] = web_ports
        return {"action": "RUN", "tool": "nmap_vuln", "target": target,
                "reasoning": "[REDTEAM] Vulnerability scan."}

    if step_count == 2:
        output = " ".join(s.get("output", "") for s in steps).lower()
        has_web = any(p in output for p in ["80/tcp", "443/tcp", "8080/tcp", "http"])
        if has_web:
            session.setdefault("discovered", {})["has_web"] = True
            return {"action": "RUN", "tool": "nikto", "target": target,
                    "reasoning": "[REDTEAM] Nikto web scan."}
        return {"action": "RUN", "tool": "nuclei", "target": target,
                "reasoning": "[REDTEAM] Nuclei CVE scan."}

    if step_count == 3:
        has_web = session.get("discovered", {}).get("has_web", False)
        if has_web:
            return {"action": "RUN", "tool": "gobuster_dir", "target": target,
                    "reasoning": "[REDTEAM] Directory enumeration."}
        return {"action": "RUN", "tool": "nuclei", "target": target,
                "reasoning": "[REDTEAM] Nuclei templates."}

    if step_count == 4:
        has_web = session.get("discovered", {}).get("has_web", False)
        if has_web:
            return {"action": "RUN", "tool": "dirb", "target": target,
                    "reasoning": "[REDTEAM] Dirb enumeration."}
        return {"action": "RUN", "tool": "searchsploit", "target": target,
                "reasoning": "[REDTEAM] Exploit-DB search."}

    if step_count == 5:
        output = " ".join(s.get("output", "") for s in steps).lower()
        has_web = session.get("discovered", {}).get("has_web", False)
        has_sql = any(kw in output for kw in [
            "sql", "mysql", "postgresql", "mariadb", "oracle",
            "mssql", "3306/tcp", "1433/tcp", "5432/tcp"
        ])
        has_ssh = "22/tcp" in output or "ssh" in output
        has_smb = "445/tcp" in output or "smb" in output

        if has_sql and has_web:
            session["discovered"]["has_sql"] = True
            return {"action": "RUN", "tool": "sqlmap", "target": target,
                    "reasoning": "[REDTEAM] SQLMap on detected SQL service."}
        if has_ssh:
            session["discovered"]["has_ssh"] = True
        if has_smb:
            session["discovered"]["has_smb"] = True
        return {"action": "RUN", "tool": "nuclei", "target": target,
                "reasoning": "[REDTEAM] Extended Nuclei scan."}

    if step_count in (6, 7):
        disc = session.get("discovered", {})
        if disc.get("has_sql") and step_count == 6:
            return {"action": "RUN", "tool": "sqlmap", "target": target,
                    "reasoning": "[REDTEAM] Deep SQLMap --dbs enumeration."}
        if disc.get("has_ssh") and step_count == 6:
            disc["hydra_on_ssh"] = True
            return {"action": "RUN", "tool": "hydra", "target": target,
                    "reasoning": "[REDTEAM] Hydra brute-force on SSH."}
        if disc.get("has_smb") and step_count == 7:
            return {"action": "RUN", "tool": "nmap_vuln", "target": target,
                    "reasoning": "[REDTEAM] SMB vuln scan (EternalBlue)."}
        return {"action": "RUN", "tool": "nuclei", "target": target,
                "reasoning": "[REDTEAM] Comprehensive assessment."}

    if step_count >= 8:
        all_output = " ".join(s.get("output", "") for s in steps).lower()
        vuln_indicators = [
            "critical", "cve-", "exploit", "vulnerable",
            "sql injection", "xss", "rce", "lfi", "bypass"
        ]
        found = [v for v in vuln_indicators if v in all_output]
        if found:
            session.setdefault("discovered", {})["confirmed_vulns"] = found
            if step_count < REDTEAM_STEPS - 2:
                return {"action": "RUN", "tool": "searchsploit", "target": target,
                        "reasoning": f"[REDTEAM] Exploit search for: {', '.join(found[:3])}."}
        if step_count < REDTEAM_STEPS - 2:
            return {"action": "RUN", "tool": "nuclei", "target": target,
                    "reasoning": "[REDTEAM] Deep scan continuing."}

    return {"action": "DONE", "summary": (
        f"[REDTEAM] Operation complete on {target}. {step_count + 1} steps. "
        + ("Vulns: " + ", ".join(session.get("discovered", {}).get("confirmed_vulns", []))
           if session.get("discovered", {}).get("confirmed_vulns")
           else "No critical vulns confirmed.")
        + " Review terminal outputs and attack graph."
    )}


# ── output summariser ───────────────────────────────────────────────────────

def _parse_step_output(output, tool_name):
    """Quick heuristic summary of tool output (used for history display)."""
    if not output:
        return "No output"
    lines = output.strip().split("\n")
    nmap_tools = ("nmap", "nmap_tcp", "nmap_stealth", "nmap_vuln", "nmap_banner")
    if tool_name in nmap_tools:
        open_ports = [l for l in lines if "/tcp" in l and "open" in l]
        if open_ports:
            return f"Found {len(open_ports)} open ports: " + ", ".join(
                p.strip()[:40] for p in open_ports[:5])
        return "Nmap scan completed."
    if tool_name in ("subfinder", "assetfinder"):
        found = [l for l in lines if "." in l and not l.startswith("[")]
        return f"Found {len(found)} subdomains."
    if tool_name == "whois":
        return "WHOIS lookup completed."
    if tool_name == "nikto":
        vulns = [l for l in lines if "+" in l or "OSVDB" in l or "CVE" in l.upper()]
        return f"Nikto: {len(vulns)} potential issues." if vulns else "Nikto scan completed."
    if tool_name == "nuclei":
        found = [l for l in lines if any(s in l.lower() for s in
                                          ["critical", "high", "medium"])]
        return f"Nuclei: {len(found)} findings." if found else "Nuclei scan completed."
    if tool_name in ("dirb", "gobuster_dir", "feroxbuster", "ffuf"):
        found = [l for l in lines if "CODE:200" in l or "==>" in l or "200" in l]
        return f"Found {len(found)} accessible paths." if found else "Enumeration completed."
    meaningful = [l for l in lines if len(l.strip()) > 10][:3]
    return (" | ".join(meaningful) if meaningful else "Output received")[:200]


# ── main agent loop ─────────────────────────────────────────────────────────

def run_agent_loop(session_id, target, mode="recon"):
    """Run the autonomous agent loop with native tool calling.

    The loop continues until:
      - The LLM calls ``mission_complete``
      - The max step limit is reached
      - The session is stopped by the user
    """
    max_steps = DEFAULT_MAX_STEPS
    if mode == "redteam":
        max_steps = REDTEAM_MAX_STEPS

    # Override from global settings if present
    try:
        from handlers.ai_engine import _agent_settings
        max_steps = _agent_settings.get("max_steps", max_steps)
    except Exception:
        pass

    session = {
        "id": session_id,
        "target": target,
        "status": "running",
        "mode": mode,
        "steps": [],
        "started_at": time.time(),
        "final_summary": "",
        "discovered": {},
        "max_steps": max_steps,
    }
    ACTIVE_SESSIONS[session_id] = session

    allowed = ALLOWED_TOOLS + (REDTEAM_TOOLS if mode == "redteam" else []) + ESCALATION_TOOLS
    # deduplicate while preserving order
    allowed = list(dict.fromkeys(allowed))

    try:
        while len(session["steps"]) < max_steps:
            if session.get("status") != "running":
                return

            session["current_phase"] = "thinking"

            # ── use native tool calling when LLM is available ──────────
            decision = _odin_decide_native(session, allowed)

            if decision.get("action") == "DONE":
                session["status"] = "completed"
                session["final_summary"] = decision.get(
                    "summary", "Mission complete."
                )
                session["current_phase"] = "done"
                _auto_populate_graph(target, session)
                return

            if decision.get("action") != "RUN":
                session["status"] = "completed"
                session["final_summary"] = "Agent stopped: No valid action."
                session["current_phase"] = "done"
                return

            tool_key = decision.get("tool", "")
            reasoning = decision.get("reasoning", "")

            # Safety: block disallowed tools
            if tool_key not in allowed:
                session["steps"].append({
                    "step": len(session["steps"]) + 1,
                    "tool": tool_key,
                    "target": target,
                    "reasoning": reasoning,
                    "status": "blocked",
                    "summary": f"Tool '{tool_key}' is not in autonomous whitelist."
                })
                continue

            # ── execute ────────────────────────────────────────────────
            session["current_phase"] = "executing"
            session["current_tool"] = tool_key
            session["current_step"] = len(session["steps"]) + 1

            step = {
                "step": len(session["steps"]) + 1,
                "tool": tool_key,
                "target": target,
                "reasoning": reasoning,
                "status": "running",
            }
            session["steps"].append(step)

            try:
                output = _run_tool_direct(tool_key, target)
                step["status"] = "completed"
                step["output"] = output[:8000] if output else ""
            except Exception as e:
                step["status"] = "error"
                step["output"] = f"Error: {str(e)}"

            # ── observe ───────────────────────────────────────────────
            session["current_phase"] = "observing"
            step["summary"] = _parse_step_output(
                step.get("output", ""), tool_key
            )

            # scope warning near limit
            scope_limit = max_steps - 3
            if len(session["steps"]) >= scope_limit:
                session["scope_warning"] = (
                    f"Approaching safety limit ({max_steps} steps). "
                    "Agent will complete soon."
                )

        # Ran out of steps
        session["status"] = "completed"
        session["final_summary"] = (
            f"Maximum steps ({max_steps}) reached for autonomous scan "
            f"on {target}. Review all terminal outputs for findings."
        )
        session["current_phase"] = "done"
        _auto_populate_graph(target, session)

    except Exception as e:
        session["status"] = "error"
        session["final_summary"] = f"Agent error: {str(e)}"
        session["current_phase"] = "error"


def _auto_populate_graph(target, session):
    """Push discovered nodes to the Attack Graph."""
    try:
        from handlers.attack_graph import auto_populate_from_scans
        mode = session.get("mode", "recon")
        sid = ("redteam_" if mode == "redteam" else "recon_") + session.get("id", "anon")
        auto_populate_from_scans(target, sid)
    except Exception:
        pass


# ── public API ──────────────────────────────────────────────────────────────

# Agent-wide settings (modifiable via settings page)
_agent_settings = {
    "max_steps": DEFAULT_MAX_STEPS,
    "approval_mode": False,       # True = require user OK before executing
    "multi_agent_mode": False,    # True = Odin+Loki can run concurrently
    "pending_approval": None,     # dict of pending command awaiting approval
}


def get_agent_settings():
    """Return current agent settings (read by settings route)."""
    return dict(_agent_settings)


def update_agent_settings(updates):
    """Apply partial settings update from the settings page.

    Accepted keys: ``max_steps``, ``approval_mode``, ``multi_agent_mode``.
    """
    for key in ("max_steps", "approval_mode", "multi_agent_mode"):
        if key in updates:
            _agent_settings[key] = updates[key]
    return dict(_agent_settings)


def start_agent(target, mode="recon"):
    """Launch an autonomous agent session in a background thread."""
    import uuid
    session_id = str(uuid.uuid4())[:8]
    if not target or len(target.strip()) < 2:
        return {"status": "error", "message": "Valid target required."}
    target = target.strip()

    # Prevent duplicate sessions on same target
    for sid, s in list(ACTIVE_SESSIONS.items()):
        if s.get("status") == "running" and s.get("target") == target:
            return {
                "status": "error",
                "message": (
                    f"An autonomous scan is already running on {target} "
                    f"(Session: {sid})."
                ),
            }

    # FIX: Use centralized validate_target with path traversal and IP checks
    from core.system_manager import validate_target
    if not validate_target(target):
        return {
            "status": "error",
            "message": "Invalid target format. Use a valid IP or domain name."
        }

    if mode == "redteam":
        from handlers.attack_graph import add_graph_node
        add_graph_node(
            target, "target",
            parent_id=None,
            data={"type": "redteam_root"},
            session_id="redteam_" + session_id,
        )

    max_steps = (
        REDTEAM_MAX_STEPS if mode == "redteam"
        else _agent_settings.get("max_steps", DEFAULT_MAX_STEPS)
    )

    thread = threading.Thread(
        target=run_agent_loop,
        args=(session_id, target, mode),
        daemon=True,
    )
    thread.start()

    return {
        "status": "success",
        "session_id": session_id,
        "message": (
            f"Autonomous agent started on {target}. "
            f"Max {max_steps} steps. Mode: {mode}."
        ),
        "max_steps": max_steps,
        "mode": mode,
    }


def get_agent_status(session_id):
    """Return current status of an agent session."""
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
            "max_steps": (
                REDTEAM_MAX_STEPS if mode == "redteam"
                else session.get("max_steps", DEFAULT_MAX_STEPS)
            ),
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
                    "summary": s.get("summary", ""),
                }
                for s in session.get("steps", [])
            ],
        },
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
    """Return all agent sessions (running and completed)."""
    return {
        "status": "success",
        "sessions": [
            {
                "id": s["id"],
                "target": s["target"],
                "status": s["status"],
                "steps": len(s.get("steps", [])),
                "started_at": s.get("started_at", 0),
            }
            for s in ACTIVE_SESSIONS.values()
        ],
    }
