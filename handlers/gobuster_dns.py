from .utils import run_command_safely
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
        return f">> VALIDATION ERROR: Gobuster DNS mode requires a valid wordlist. The provided wordlist path '{wordlist}' is empty or invalid."
    return run_command_safely(cmd, timeout=120)
