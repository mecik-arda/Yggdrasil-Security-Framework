"""
Odin's Eye AI — Local Ollama Engine
Handles all communication with locally running Ollama instance.
Models are NOT downloaded automatically; user triggers via UI Package Manager.
"""
import requests
import subprocess
import platform
import json
import re
OLLAMA_BASE = "http://localhost:11434"
REQUEST_TIMEOUT = 120  # seconds for chat generation
def _check_ollama():
    """Check if Ollama is running and accessible. Returns (bool, list_of_models)."""
    try:
        resp = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=5)
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            return True, models
        return False, []
    except requests.ConnectionError:
        return False, []
    except Exception:
        return False, []
def list_models():
    """Return all locally installed Ollama models."""
    ok, models = _check_ollama()
    if not ok:
        return {
            "status": "error",
            "message": "Ollama servisi calismiyor. Terminalde 'ollama serve' ile baslatin."
        }
    return {
        "status": "success",
        "models": [{"name": m["name"], "size": m.get("size", 0)} for m in models]
    }
def chat_completion(model, messages, stream=False):
    """
    Send chat completion to local Ollama.
    Args:
        model: str — model name (e.g. 'qwen2.5-coder:7b')
        messages: list[dict] — [{"role": "user", "content": "..."}]
        stream: bool — reserved for future streaming support
    Returns:
        dict with status and response/error message
    """
    ok, _ = _check_ollama()
    if not ok:
        return {
            "status": "error",
            "message": "Ollama servisi calismiyor. Terminalde 'ollama serve' komutuyla baslatin."
        }
    try:
        payload = {
            "model": model,
            "messages": messages,
            "stream": False
        }
        resp = requests.post(
            f"{OLLAMA_BASE}/api/chat",
            json=payload,
            timeout=REQUEST_TIMEOUT
        )
        if resp.status_code == 200:
            data = resp.json()
            content = data.get("message", {}).get("content", "")
            return {"status": "success", "response": content}
        else:
            return {
                "status": "error",
                "message": f"Ollama API hatasi (HTTP {resp.status_code}): {resp.text[:200]}"
            }
    except requests.Timeout:
        return {"status": "error", "message": "Timeout: AI yaniti 120 saniyede gelmedi."}
    except Exception as e:
        return {"status": "error", "message": f"AI Engine hatasi: {str(e)}"}
def pull_model(model_name):
    """
    Launch model pull in a separate terminal window (non-blocking).
    Does NOT download automatically — user must trigger explicitly.
    """
    if not model_name or not re.match(r'^[a-zA-Z0-9\.\-\:]+$', model_name):
        return {"status": "error", "message": "Gecersiz model adi formatı tespit edildi. (Guvenlik Ihlali)"}
    ok, _ = _check_ollama()
    if not ok:
        return {
            "status": "error",
            "message": "Ollama servisi calismiyor. Once Ollama'yi baslatin."
        }
    try:
        if platform.system() == "Windows":
            subprocess.Popen(
                f'start "Odin Model Pull - {model_name}" cmd /k "ollama pull {model_name}"',
                shell=True
            )
        else:
            subprocess.Popen(
                ["x-terminal-emulator", "-e", f"bash -c 'ollama pull {model_name}; read -p \"Done. Press enter...\"'"]
            )
        return {
            "status": "success",
            "message": f"'{model_name}' indirme islemi yeni terminalde baslatildi."
        }
    except Exception as e:
        return {"status": "error", "message": f"Pull baslatilamadi: {str(e)}"}
def remove_model(model_name):
    """Remove an installed Ollama model to free disk space."""
    if not model_name or not re.match(r'^[a-zA-Z0-9\.\-\:]+$', model_name):
        return {"status": "error", "message": "Gecersiz model adi formatı tespit edildi. (Guvenlik Ihlali)"}
    try:
        result = subprocess.check_output(
            ["ollama", "rm", model_name],
            stderr=subprocess.STDOUT,
            timeout=30
        ).decode("utf-8", errors="replace")
        return {"status": "success", "message": result.strip()}
    except subprocess.CalledProcessError as e:
        return {
            "status": "error",
            "message": f"Model silinemedi:\n{e.output.decode('utf-8', errors='replace')}"
        }
    except FileNotFoundError:
        return {
            "status": "error",
            "message": "Ollama CLI bulunamadi. Ollama kurulu oldugundan emin olun."
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
def analyze_scan_output(output, tool_name, target="unknown"):
    """
    Heimdall Agent: Parse raw scan output and extract structured findings.
    Sends tool output to the local Ollama model with a parsing prompt
    asking for JSON-structured results including open ports, banners,
    vulnerabilities, and recommended next steps.
    Args:
        output: str — raw terminal output from a security tool
        tool_name: str — name of the tool (e.g. 'nmap', 'hydra')
        target: str — scan target for context
    Returns:
        dict with structured analysis or error
    """
    ok, models = _check_ollama()
    if not ok:
        return {
            "status": "error",
            "message": "Ollama servisi calismiyor. Analiz yapilamadi."
        }
    max_chars = 8000
    truncated = output[-max_chars:] if len(output) > max_chars else output
    if len(output) > max_chars:
        truncated = "[...output truncated...]\n" + truncated
    model_names = [m["name"] for m in models]
    preferred = None
    for candidate in ["qwen2.5-coder:7b", "deepseek-r1:14b", "mistral:7b",
                       "llama3.2:3b", "qwen2.5-coder:1.5b"]:
        base = candidate.split(":")[0]
        for m in model_names:
            if base in m or candidate in m:
                preferred = m
                break
        if preferred:
            break
    if not preferred and model_names:
        preferred = model_names[0]
    if not preferred:
        return {
            "status": "error",
            "message": "No AI model available for analysis. Pull a model first."
        }
    system_prompt = (
        "You are Heimdall, an automated reconnaissance parsing agent for a "
        "penetration testing framework called Yggdrasil. Your job is to analyze "
        "raw tool output and return ONLY a valid JSON object."
    )
    user_prompt = f"""Analyze the following output from the security tool '{tool_name}' that was run against target '{target}'.
Return a JSON object with this exact structure:
{{
  "summary": "One-sentence summary of findings",
  "findings": [
    {{ "type": "port|service|vulnerability|credential|path|info",
       "detail": "specific finding detail",
       "severity": "critical|high|medium|low|info"
    }}
  ],
  "recommendations": [
    {{ "action": "specific next step to take",
       "tool": "recommended Yggdrasil tool name or external tool",
       "reason": "why this step is recommended"
    }}
  ],
  "stats": {{
    "open_ports": 0,
    "services_found": 0,
    "vulnerabilities_found": 0
  }}
}}
--- RAW TOOL OUTPUT ---
{truncated}
--- END OUTPUT ---
Return ONLY the JSON object, no other text."""
    try:
        payload = {
            "model": preferred,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False
        }
        resp = requests.post(
            f"{OLLAMA_BASE}/api/chat",
            json=payload,
            timeout=REQUEST_TIMEOUT
        )
        if resp.status_code == 200:
            data = resp.json()
            content = data.get("message", {}).get("content", "")
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                try:
                    parsed = json.loads(json_match.group(0))
                    return {
                        "status": "success",
                        "model": preferred,
                        "analysis": parsed
                    }
                except json.JSONDecodeError:
                    pass
            return {
                "status": "success",
                "model": preferred,
                "analysis": {
                    "summary": content.strip()[:300],
                    "findings": [],
                    "recommendations": [],
                    "stats": {}
                },
                "raw": True
            }
        else:
            return {
                "status": "error",
                "message": f"Ollama API hatasi (HTTP {resp.status_code})"
            }
    except requests.Timeout:
        return {"status": "error", "message": "Timeout: Analiz 120 saniyede tamamlanamadi."}
    except Exception as e:
        return {"status": "error", "message": f"Analysis hatasi: {str(e)}"}
def get_ai_profile_tiers():
    """Return available hardware profile tiers with recommended models."""
    return {
        "tiers": [
            {
                "id": "tier1",
                "name": "Tier 1: Minimum (CPU)",
                "description": "Dusuk RAM, CPU execution. Temel analizler icin uygun.",
                "ram": "16 GB",
                "gpu": "N/A (CPU)",
                "models": ["llama3.2:3b", "qwen2.5-coder:7b"],
                "speed": "10-15 tokens/sec"
            },
            {
                "id": "tier2",
                "name": "Tier 2: Recommended (GPU)",
                "description": "Oyun/gelistirici PC'si. Hizli AI yanitlari.",
                "ram": "32 GB",
                "gpu": "12-16 GB VRAM (RTX 3060/4060Ti/4070)",
                "models": ["deepseek-r1:14b", "qwen2.5-coder:7b"],
                "speed": "40-70 tokens/sec"
            },
            {
                "id": "tier3",
                "name": "Tier 3: Enterprise (Heavy GPU)",
                "description": "Yuksek RAM ve VRAM. Maksimum AI zekasi.",
                "ram": "64 GB+",
                "gpu": "24 GB+ VRAM (RTX 3090/4090)",
                "models": ["deepseek-r1:70b", "qwen2.5-coder:32b"],
                "speed": "80+ tokens/sec"
            }
        ]
    }
