from .utils import run_command_safely
def handle_hydra_bruteforce(target, data, output_callback=None):
    if data is None:
        data = {}
    protocol = data.get('protocol', 'ssh')
    port = data.get('port', '')
    threads = data.get('threads', '4')
    user_type = data.get('user_type', 'single') # 'single' or 'list'
    user_val = data.get('user_val', 'admin')
    pass_type = data.get('pass_type', 'single') # 'single' or 'list'
    pass_val = data.get('pass_val', 'admin')
    verbose = data.get('verbose', 'false') == 'true'
    cmd = ['hydra']
    if user_type == 'list':
        cmd.extend(['-L', user_val])
    else:
        cmd.extend(['-l', user_val])
    if pass_type == 'list':
        cmd.extend(['-P', pass_val])
    else:
        cmd.extend(['-p', pass_val])
    if port:
        cmd.extend(['-s', str(port)])
    if threads:
        cmd.extend(['-t', str(threads)])
    if verbose:
        cmd.append('-V')
    cmd.append(target)
    cmd.append(protocol)
    return run_command_safely(cmd, timeout=120, output_callback=output_callback)
