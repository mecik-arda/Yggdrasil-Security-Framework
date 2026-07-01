import subprocess
import platform
import shlex
import json
import os
from tools_config import TOOLS_CONFIG
from handlers import dispatch_handler

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
        try:
            current_os = platform.system()
            cwd = config.get('cwd', '.')
            log_path = config.get('log_file', 'launcher.log')
            log_file = open(log_path, "w")
            
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
            return f"GUI Launch Error: {str(e)}"
            
    elif tool_type in ['cli', 'script']:
        cmd_template = config.get('cmd', [])
        cmd = [arg.format(target=target) if '{target}' in arg else arg for arg in cmd_template]
        
        current_os = platform.system()
        supported = config.get('supported_os', [])
        
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
            return "TIMEOUT: Process took too long"
        except Exception as e:
            return f"System Error: {str(e)}"
            
    elif tool_type in ['custom_html', 'custom_script']:
        handler_name = config.get('handler')
        return dispatch_handler(handler_name, target, data)
        
    return "Unsupported tool type"
