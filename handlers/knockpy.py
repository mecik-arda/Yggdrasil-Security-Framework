import subprocess
import os

def handle_knockpy(target, data):
    threads = data.get('threads', '50')
    wordlist = data.get('wordlist', '')

    cmd = ['knockpy', target]

    if threads:
        cmd.extend(['-t', str(threads)])
        
    if wordlist and os.path.exists(wordlist):
        cmd.extend(['-w', wordlist])

    try:
        result = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=120).decode('utf-8', errors='replace')
        return f">> EXECUTING KNOCKPY:\n$ {' '.join(cmd)}\n\n{result}"
    except subprocess.TimeoutExpired:
        return f">> TIMEOUT: Knockpy scan on {target} took too long (120s limit)."
    except subprocess.CalledProcessError as e:
        return f">> EXECUTION FAILED:\n$ {' '.join(cmd)}\n\n{e.output.decode('utf-8', errors='replace')}"
    except Exception as e:
        return f">> SYSTEM ERROR:\n{str(e)}"
