import subprocess
import os

def handle_gobuster_dns(target, data):
    threads = data.get('threads', '10')
    wordlist = data.get('wordlist', '')

    cmd = ['gobuster', 'dns', '-d', target]

    if threads:
        cmd.extend(['-t', str(threads)])
        
    if wordlist and os.path.exists(wordlist):
        cmd.extend(['-w', wordlist])
    else:
        # Provide a warning if no wordlist is supplied, as gobuster requires it
        return f">> VALIDATION ERROR: Gobuster DNS mode requires a valid wordlist. The provided wordlist path '{wordlist}' is empty or invalid."

    try:
        result = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=120).decode('utf-8', errors='replace')
        return f">> EXECUTING GOBUSTER (DNS):\n$ {' '.join(cmd)}\n\n{result}"
    except subprocess.TimeoutExpired:
        return f">> TIMEOUT: Gobuster scan on {target} took too long (120s limit)."
    except subprocess.CalledProcessError as e:
        return f">> EXECUTION FAILED:\n$ {' '.join(cmd)}\n\n{e.output.decode('utf-8', errors='replace')}"
    except Exception as e:
        return f">> SYSTEM ERROR:\n{str(e)}"
