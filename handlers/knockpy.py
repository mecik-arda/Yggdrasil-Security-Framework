from .utils import run_command_safely
import os
def handle_knockpy(target, data, output_callback=None):
    if data is None:
        data = {}
    threads = data.get('threads', '50')
    wordlist = data.get('wordlist', '')
    cmd = ['knockpy', target]
    if threads:
        cmd.extend(['-t', str(threads)])
    if wordlist and os.path.exists(wordlist):
        cmd.extend(['-w', wordlist])
    return run_command_safely(cmd, timeout=120, output_callback=output_callback)
