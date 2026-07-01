from .utils import run_command_safely
def handle_subfinder(target, data):
    if data is None:
        data = {}
    threads = data.get('threads', '10')
    all_sources = data.get('all_sources', 'false') == 'true'
    cmd = ['subfinder', '-d', target]
    if threads:
        cmd.extend(['-t', str(threads)])
    if all_sources:
        cmd.append('-all')
    return run_command_safely(cmd, timeout=120)
