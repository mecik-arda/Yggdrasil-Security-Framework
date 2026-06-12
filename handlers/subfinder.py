import subprocess

def handle_subfinder(target, data):
    threads = data.get('threads', '10')
    all_sources = data.get('all_sources', 'false') == 'true'

    cmd = ['subfinder', '-d', target]

    if threads:
        cmd.extend(['-t', str(threads)])
        
    if all_sources:
        cmd.append('-all')

    try:
        result = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=120).decode('utf-8', errors='replace')
        return f">> EXECUTING SUBFINDER:\n$ {' '.join(cmd)}\n\n{result}"
    except subprocess.TimeoutExpired:
        return f">> TIMEOUT: Subfinder scan on {target} took too long (120s limit)."
    except subprocess.CalledProcessError as e:
        return f">> EXECUTION FAILED:\n$ {' '.join(cmd)}\n\n{e.output.decode('utf-8', errors='replace')}"
    except Exception as e:
        return f">> SYSTEM ERROR:\n{str(e)}"
