import subprocess
import platform
import os
from core.logger import get_logger

def run_command_safely(cmd, timeout=120, cwd=None, errors='replace', output_callback=None):
    if not isinstance(cmd, list):
        cmd = cmd.split()
    if cmd and cmd[0] == 'wsl.exe':
        try:
            idx = cmd.index('--')
            cmd.insert(idx + 1, 'stdbuf')
            cmd.insert(idx + 2, '-oL')
        except ValueError:
            pass
    elif platform.system() != 'Windows' and cmd and cmd[0] != 'stdbuf':
        cmd = ['stdbuf', '-oL'] + cmd
    env = os.environ.copy()
    env['PYTHONUNBUFFERED'] = '1'
    try:
        if output_callback:
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                cwd=cwd, env=env, universal_newlines=True, bufsize=1
            )
            output_lines = []
            for line in iter(process.stdout.readline, ''):
                if line:
                    line = line.rstrip('\n\r')
                    output_lines.append(line)
                    output_callback(line)
            process.wait(timeout=timeout)
            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, cmd, '\n'.join(output_lines).encode('utf-8'))
            return '\n'.join(output_lines)
        else:
            result = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=timeout, cwd=cwd, env=env).decode('utf-8', errors=errors)
            return result
    except subprocess.TimeoutExpired:
        get_logger('utils').warning(
            f'Command timed out: {" ".join(cmd)}',
            extra={'extra_data': {'cmd': ' '.join(cmd)}},
        )
        return "TIMEOUT: Process took too long"
    except subprocess.CalledProcessError as e:
        get_logger('utils').error(
            f'Command failed (exit {e.returncode}): {" ".join(cmd)}',
            extra={'extra_data': {'cmd': ' '.join(cmd), 'returncode': e.returncode}},
        )
        return f"Execution Error:\n{e.output.decode('utf-8', errors=errors) if isinstance(e.output, bytes) else e.output}"
    except Exception as e:
        get_logger('utils').error(
            f'Unexpected error running command: {e}',
            extra={'extra_data': {'cmd': " ".join(cmd)}},
        )
        return f"System Error: {str(e)}"
