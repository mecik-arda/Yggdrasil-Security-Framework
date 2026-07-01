import subprocess
def run_command_safely(cmd, timeout=120, cwd=None, errors='replace'):
    try:
        result = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=timeout, cwd=cwd).decode('utf-8', errors=errors)
        return result
    except subprocess.TimeoutExpired:
        return "TIMEOUT: Process took too long"
    except subprocess.CalledProcessError as e:
        return f"Execution Error:\n{e.output.decode('utf-8', errors=errors)}"
    except Exception as e:
        return f"System Error: {str(e)}"
