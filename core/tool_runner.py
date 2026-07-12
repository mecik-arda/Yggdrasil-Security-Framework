import subprocess
import platform
import shlex
import json
import os
import shutil
from tools_config import TOOLS_CONFIG
from handlers import dispatch_handler
from core.logger import get_logger

WSL_CONFIG_FILE = 'wsl_config.json'

def get_wsl_distros():
    if platform.system() != 'Windows':
        return []
    try:
        output = subprocess.check_output(['wsl.exe', '--list', '--quiet'], stderr=subprocess.STDOUT)
        decoded = output.decode('utf-16le', errors='ignore').strip()
        return [d.strip() for d in decoded.split('\n') if d.strip()]
    except Exception:
        pass
    return []

def get_preferred_wsl():
    if os.path.exists(WSL_CONFIG_FILE):
        try:
            with open(WSL_CONFIG_FILE, 'r') as f:
                data = json.load(f)
                distro = data.get('wsl_distro')
                if distro in get_wsl_distros():
                    return distro
        except Exception:
            pass
    distros = get_wsl_distros()
    return distros[0] if distros else None

def execute_tool(tool_key, target, data=None, task_id=None):
    config = TOOLS_CONFIG.get(tool_key)
    if not config:
        return "Tool definition not found"

    tool_type = config.get('type')

    if tool_type == 'gui':
        current_os = platform.system()
        cwd = config.get('cwd', '.')
        log_path = config.get('log_file', 'launcher.log')
        try:
            # FIX: Use with-statement to ensure log file handle is closed
            with open(log_path, "w") as log_file:
                if current_os == 'Windows':
                    cmd_str = config.get('cmd_windows')
                    # Use cmd.exe /c start to avoid direct shell=True with raw string
                    cmd_list = ['cmd.exe', '/c', cmd_str]
                    process = subprocess.Popen(cmd_list, shell=False, cwd=cwd, stdout=log_file, stderr=log_file)
                else:
                    cmd_str = config.get('cmd_linux')
                    # Split the linux command
                    cmd_list = shlex.split(cmd_str)
                    process = subprocess.Popen(cmd_list, shell=False, cwd=cwd, stdout=log_file, stderr=log_file)

            # Note: GUI processes run independently, so we just return success
            return f">> INITIATING GUI TOOL ({current_os.upper()} MODE)...\n>> PLEASE CHECK YOUR TASKBAR FOR THE NEW WINDOW."
        except Exception as e:
            get_logger('tool_runner').error(
                f'GUI launch failed: {tool_key} - {e}',
                extra={'tool': tool_key},
            )
            # FIX: Return generic message to avoid information disclosure
            return f"GUI Launch Error: Could not launch {tool_key}. Check logs for details."

    elif tool_type in ['cli', 'script']:
        cmd_template = config.get('cmd', [])
        cmd = [arg.format(target=target) if '{target}' in arg else arg for arg in cmd_template]

        current_os = platform.system()
        supported = config.get('supported_os', [])
        is_windows_supported = ('windows' in supported) if supported else True

        if current_os == 'Windows' and is_windows_supported and cmd:
            if shutil.which(cmd[0]) is None:
                if os.path.exists(os.path.join('venv', 'Scripts', f"{cmd[0]}.exe")):
                    cmd[0] = os.path.join('venv', 'Scripts', f"{cmd[0]}.exe")
                elif cmd[0] == 'tshark' and os.path.exists(r"C:\Program Files\Wireshark\tshark.exe"):
                    cmd[0] = r"C:\Program Files\Wireshark\tshark.exe"

        if current_os.lower() not in supported and current_os == 'Windows':
            wsl_distro = get_preferred_wsl()
            if wsl_distro:
                cmd = ['wsl.exe', '-d', wsl_distro, '-u', 'root', '--'] + cmd

        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            if task_id:
                from core.task_manager import set_task_process
                set_task_process(task_id, process)

            output, _ = process.communicate(timeout=120)
            return output.decode('utf-8', errors='replace')
        except subprocess.TimeoutExpired:
            process.kill()
            get_logger('tool_runner').warning(
                f'Tool timed out: {tool_key}',
                extra={'tool': tool_key, 'target': target or 'NONE'},
            )
            return "TIMEOUT: Process took too long"
        except Exception as e:
            get_logger('tool_runner').error(
                f'Tool execution failed: {tool_key} - {e}',
                extra={'tool': tool_key, 'target': target or 'NONE'},
            )
            # FIX: Return generic message to avoid information disclosure
            return f"System Error: Tool execution failed. Check logs for details."

    elif tool_type in ['custom_html', 'custom_script']:
        handler_name = config.get('handler')
        return dispatch_handler(handler_name, target, data)

    return "Unsupported tool type"


def execute_tool_streaming(tool_key, target, output_callback, data=None, task_id=None):
    """Like ``execute_tool`` but calls ``output_callback(line_text)`` for each output line.

    The callback receives decoded UTF-8 strings (without trailing newline).
    Returns the full output as a single string (same return convention as ``execute_tool``).
    """
    config = TOOLS_CONFIG.get(tool_key)
    if not config:
        output_callback("Tool definition not found")
        return "Tool definition not found"

    tool_type = config.get('type')

    # For non-CLI types, just run the blocking version and split output
    if tool_type == 'gui':
        result = execute_tool(tool_key, target, data, task_id)
        for line in result.split('\n'):
            output_callback(line)
        return result

    if tool_type in ['custom_html', 'custom_script']:
        handler_name = config.get('handler')
        called = [False]
        def wrapped_callback(line):
            called[0] = True
            output_callback(line)
        result = dispatch_handler(handler_name, target, data, output_callback=wrapped_callback)
        if not called[0] and result:
            for line in str(result).split('\n'):
                output_callback(line)
        return result

    if tool_type not in ['cli', 'script']:
        output_callback("Unsupported tool type")
        return "Unsupported tool type"

    # -- CLI / script: read stdout line by line ----------------------------
    cmd_template = config.get('cmd', [])
    cmd = [arg.format(target=target) if '{target}' in arg else arg for arg in cmd_template]

    current_os = platform.system()
    supported = config.get('supported_os', [])
    is_windows_supported = ('windows' in supported) if supported else True

    if current_os == 'Windows' and is_windows_supported and cmd:
        import shutil
        if shutil.which(cmd[0]) is None:
            if os.path.exists(os.path.join('venv', 'Scripts', f"{cmd[0]}.exe")):
                cmd[0] = os.path.join('venv', 'Scripts', f"{cmd[0]}.exe")
            elif cmd[0] == 'tshark' and os.path.exists(r"C:\Program Files\Wireshark\tshark.exe"):
                cmd[0] = r"C:\Program Files\Wireshark\tshark.exe"

    wsl_booting = False
    if current_os.lower() not in supported and current_os == 'Windows':
        wsl_distro = get_preferred_wsl()
        if wsl_distro:
            wsl_booting = True
            cmd = ['wsl.exe', '-d', wsl_distro, '-u', 'root', '--', 'stdbuf', '-oL'] + cmd
    elif current_os != 'Windows' and cmd and cmd[0] != 'stdbuf':
        cmd = ['stdbuf', '-oL'] + cmd

    env = os.environ.copy()
    env['PYTHONUNBUFFERED'] = '1'

    try:
        if wsl_booting:
            output_callback(f"[!] Target OS requires Linux. Booting WSL ({wsl_distro})...")
            output_callback("[!] Please wait, this may take a moment.")
        else:
            output_callback(f"[*] Initializing {tool_key}... Please wait, some tools take time to generate output.")

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True,
            env=env
        )
        if task_id:
            from core.task_manager import set_task_process
            set_task_process(task_id, process)

        output_lines = []
        for line in iter(process.stdout.readline, ''):
            if line:
                line = line.rstrip('\n\r')
                output_lines.append(line)
                output_callback(line)

        process.wait(timeout=120)
        return '\n'.join(output_lines)

    except subprocess.TimeoutExpired:
        process.kill()
        get_logger('tool_runner').warning(
            f'Tool timed out (streaming): {tool_key}',
            extra={'tool': tool_key, 'target': target or 'NONE'},
        )
        output_callback("TIMEOUT: Process took too long")
        return "TIMEOUT: Process took too long"
    except Exception as e:
        get_logger('tool_runner').error(
            f'Tool execution failed (streaming): {tool_key} - {e}',
            extra={'tool': tool_key, 'target': target or 'NONE'},
        )
        msg = "System Error: Tool execution failed. Check logs for details."
        output_callback(msg)
        return msg
