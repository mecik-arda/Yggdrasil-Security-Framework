import subprocess
import shlex

def handle_hydra_bruteforce(target, data):
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

    # Target and protocol
    cmd.append(target)
    cmd.append(protocol)

    try:
        # Run hydra (timeout after 120 seconds to prevent hanging)
        result = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=120).decode('utf-8')
        return f">> EXECUTING HYDRA BRUTEFORCE:\n$ {' '.join(cmd)}\n\n{result}"
    except subprocess.TimeoutExpired:
        return f">> TIMEOUT: Hydra scan on {target} took too long (120s limit)."
    except subprocess.CalledProcessError as e:
        return f">> EXECUTION FAILED:\n$ {' '.join(cmd)}\n\n{e.output.decode('utf-8')}"
    except Exception as e:
        return f">> SYSTEM ERROR:\n{str(e)}"

