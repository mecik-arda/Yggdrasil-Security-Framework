from .utils import run_command_safely
import subprocess
import os
def handle_muninn_scan(target, data):
    if not target or target.lower() == 'none':
        return ">> ERROR: Target domain/IP is required for Muninn Scanner."
    cmd = ['go', 'run', './cmd/subenum/main.go', '-d', str(target)]
    if data:
        if data.get('all') == 'true':
            cmd.append('--all')
        if data.get('nuclei') == 'true':
            cmd.append('--nuclei')
        if data.get('nmap') == 'true':
            cmd.append('--nmap')
        if data.get('monitor') == 'true':
            cmd.append('--monitor')
    cwd_path = os.path.join('Runes', 'muninn-scanner')
    try:
        subprocess.check_output(['go', 'mod', 'tidy'], cwd=cwd_path, stderr=subprocess.STDOUT)
    except Exception:
        pass  # Non-fatal; proceed with scan
    return run_command_safely(cmd, timeout=600, cwd=cwd_path)
