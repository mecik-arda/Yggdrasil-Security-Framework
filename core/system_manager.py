import os
import shutil
import platform
import subprocess
import shlex
import threading
import concurrent.futures
from tools_config import TOOLS_CONFIG
from core.tool_runner import get_preferred_wsl

def get_pkg_name(cmd):
    parts = shlex.split(cmd)
    if 'apt-get' in parts:
        return parts[-1] if not parts[-1].startswith('-') else parts[-2]
    elif 'winget' in parts:
        return parts[-1]
    elif 'pip' in parts:
        return parts[-1]
    elif 'go' in parts:
        return parts[-1]
    return None

def rm_error(func, path, exc_info):
    import stat
    os.chmod(path, stat.S_IWRITE)
    func(path)

def install_tool_system(tool_key):
    config = TOOLS_CONFIG.get(tool_key, {})
    current_os = platform.system()
    
    is_wsl = False
    wsl_distro = None
    if current_os == "Windows":
        cmd = config.get('install_windows')
        if not cmd:
            cmd = config.get('install_linux')
            wsl_distro = get_preferred_wsl()
            if cmd and wsl_distro:
                is_wsl = True
            else:
                cmd = None
    else:
        cmd = config.get('install_linux')
        
    if not cmd:
        return False, "Installation command cannot be inferred for this OS."
        
    install_cmd = shlex.split(cmd)
    if is_wsl:
        if install_cmd[0] == 'sudo':
            install_cmd = install_cmd[1:]
        install_cmd = ['wsl.exe', '-d', wsl_distro, '-u', 'root', '--'] + install_cmd
        
    try:
        # Run apt-get update if needed
        if 'apt-get install' in cmd:
            update_cmd = ['sudo', 'apt-get', 'update']
            if is_wsl:
                update_cmd = ['wsl.exe', '-d', wsl_distro, '-u', 'root', '--', 'apt-get', 'update']
            subprocess.check_output(update_cmd, stderr=subprocess.STDOUT)
            
        output = subprocess.check_output(install_cmd, stderr=subprocess.STDOUT).decode('utf-8', errors='replace')
        return True, f"Installation output:\n{output}"
    except subprocess.CalledProcessError as e:
        return False, f"Installation failed:\n{e.output.decode('utf-8', errors='replace')}"
    except Exception as e:
        return False, f"Error: {str(e)}"

def remove_tool_system(tool_key):
    config = TOOLS_CONFIG.get(tool_key, {})
    current_os = platform.system()
    
    check_type = config.get('check_type', 'default')
    check_path = config.get('check_path', '')
    if check_type == 'runes_repo' and check_path.startswith('Runes/'):
        repo_name = check_path.split('/')[1]
        repo_path = os.path.join('Runes', repo_name)
        if os.path.exists(repo_path):
            try:
                shutil.rmtree(repo_path, onerror=rm_error)
                return True, f"Successfully removed {repo_name} repository."
            except Exception as e:
                return False, f"Failed to delete {repo_name}: {str(e)}"
        return False, f"Repository {repo_name} not found."
        
    is_wsl = False
    wsl_distro = None
    if current_os == "Windows":
        cmd = config.get('install_windows')
        if not cmd:
            cmd = config.get('install_linux')
            wsl_distro = get_preferred_wsl()
            if cmd and wsl_distro:
                is_wsl = True
    else:
        cmd = config.get('install_linux')
        
    if not cmd:
        return False, "Uninstallation command cannot be inferred (Install command missing)."
        
    pkg = get_pkg_name(cmd)
    if not pkg:
        return False, "Could not determine package name for removal."
        
    remove_cmd = []
    if 'apt-get' in cmd:
        remove_cmd = ['sudo', 'apt-get', 'remove', '-y', pkg]
    elif 'winget' in cmd:
        remove_cmd = ['winget', 'uninstall', pkg]
    elif 'pip' in cmd:
        remove_cmd = ['pip', 'uninstall', '-y', pkg]
    else:
        return False, f"Automated removal not supported for this installation type: {cmd}"
        
    if is_wsl:
        if remove_cmd[0] == 'sudo':
            remove_cmd = remove_cmd[1:]
        remove_cmd = ['wsl.exe', '-d', wsl_distro, '-u', 'root', '--'] + remove_cmd
        
    try:
        output = subprocess.check_output(remove_cmd, stderr=subprocess.STDOUT).decode('utf-8', errors='replace')
        return True, f"Removal output:\n{output}"
    except subprocess.CalledProcessError as e:
        return False, f"Removal failed:\n{e.output.decode('utf-8', errors='replace')}"
    except Exception as e:
        return False, f"Error: {str(e)}"

def update_tool_system(tool_key):
    config = TOOLS_CONFIG.get(tool_key, {})
    current_os = platform.system()
    check_path = config.get('check_path', '')
    check_type = config.get('check_type', 'default')
    
    if check_type == 'runes_repo':
        repo_name = check_path.split('/')[1]
        repo_path = os.path.join('Runes', repo_name)
        if os.path.exists(repo_path):
            try:
                subprocess.check_output(["git", "pull"], cwd=repo_path, stderr=subprocess.STDOUT)
                if tool_key == 'fenrir':
                    if current_os == 'Windows':
                        build_dir = os.path.join(repo_path, 'build')
                        if not os.path.exists(build_dir): os.makedirs(build_dir)
                        subprocess.check_output(["cmake", ".."], cwd=build_dir, stderr=subprocess.STDOUT)
                        subprocess.check_output(["cmake", "--build", ".", "--config", "Release"], cwd=build_dir, stderr=subprocess.STDOUT)
                    else:
                        subprocess.check_output(["make"], cwd=repo_path, stderr=subprocess.STDOUT)
                return True, f"Successfully updated {repo_name} from git repository."
            except subprocess.CalledProcessError as e:
                return False, f"Update failed for {repo_name}:\n{e.output.decode('utf-8', errors='replace')}"
            except Exception as e:
                return False, f"Update error for {repo_name}: {str(e)}"
        return False, f"Repository {repo_name} not found."
        
    is_wsl = False
    wsl_distro = None
    if current_os == "Windows":
        cmd = config.get('install_windows')
        if not cmd:
            cmd = config.get('install_linux')
            wsl_distro = get_preferred_wsl()
            if cmd and wsl_distro:
                is_wsl = True
    else:
        cmd = config.get('install_linux')
        
    if not cmd:
        return False, "Update command cannot be inferred."
        
    pkg = get_pkg_name(cmd)
    if not pkg:
        return False, "Could not determine package name for update."
        
    update_cmd = []
    if 'apt-get' in cmd:
        update_cmd = ['sudo', 'apt-get', '--only-upgrade', 'install', '-y', pkg]
    elif 'winget' in cmd:
        update_cmd = ['winget', 'upgrade', pkg]
    elif 'pip' in cmd:
        update_cmd = ['pip', 'install', '--upgrade', pkg]
    elif 'go' in cmd and 'install' in cmd:
        update_cmd = shlex.split(cmd) 
    else:
        return False, f"Automated update not supported for this installation type: {cmd}"
        
    if is_wsl:
        if update_cmd[0] == 'sudo':
            update_cmd = update_cmd[1:]
        update_cmd = ['wsl.exe', '-d', wsl_distro, '-u', 'root', '--'] + update_cmd
        
    try:
        output = subprocess.check_output(update_cmd, stderr=subprocess.STDOUT).decode('utf-8', errors='replace')
        return True, f"Update output:\n{output}"
    except subprocess.CalledProcessError as e:
        return False, f"Update failed:\n{e.output.decode('utf-8', errors='replace')}"
    except Exception as e:
        return False, f"Error: {str(e)}"

def check_runes_updates():
    runes_dir = "Runes"
    if not os.path.exists(runes_dir):
        return []
    def check_repo(item):
        repo_path = os.path.join(runes_dir, item)
        if os.path.isdir(repo_path) and os.path.exists(os.path.join(repo_path, ".git")):
            try:
                subprocess.check_output(["git", "fetch"], cwd=repo_path, stderr=subprocess.STDOUT)
                status = subprocess.check_output(["git", "status", "-uno"], cwd=repo_path, stderr=subprocess.STDOUT).decode("utf-8")
                if "Your branch is behind" in status or "git pull" in status:
                    return item
            except Exception:
                pass
        return None
    items = os.listdir(runes_dir)
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(check_repo, item) for item in items]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())
    return [r for r in results if r]

def background_update(runes_dir):
    for item in os.listdir(runes_dir):
        repo_path = os.path.join(runes_dir, item)
        if os.path.isdir(repo_path) and os.path.exists(os.path.join(repo_path, ".git")):
            try:
                status = subprocess.check_output(["git", "status", "-uno"], cwd=repo_path, stderr=subprocess.STDOUT).decode("utf-8")
                if "Your branch is behind" in status or "git pull" in status:
                    subprocess.check_output(["git", "pull"], cwd=repo_path, stderr=subprocess.STDOUT)
                    if "Network-Sniffer-Scanner-Java" in item:
                        mvn_cmd = "mvn.cmd" if platform.system() == "Windows" else "mvn"
                        subprocess.check_output([mvn_cmd, "clean", "install"], cwd=repo_path, stderr=subprocess.STDOUT)
            except Exception:
                pass

def apply_runes_updates():
    runes_dir = "Runes"
    if not os.path.exists(runes_dir):
        return "<p>Runes directory not found.</p>"
    thread = threading.Thread(target=background_update, args=(runes_dir,))
    thread.daemon = True
    thread.start()
    return "<div style='font-family: monospace;'><p style='color: #a3be8c;'>Updates started in the background. Tools will be synced shortly.</p></div>"

def check_tool_status_detail(tool_key):
    config = TOOLS_CONFIG.get(tool_key, {})
    if not config:
        return 'missing'
    current_os = platform.system()
    check_type = config.get('check_type')
    
    if check_type == 'runes_repo':
        check_path = config.get('check_path', '')
        if check_path.startswith('Runes/'):
            repo_name = check_path.split('/')[1]
            repo_path = os.path.join('Runes', repo_name)
            if not os.path.exists(os.path.join(repo_path, '.git')):
                return 'missing'
        binaries = config.get('check_binaries', [])
        if binaries:
            exe = '.exe' if current_os == 'Windows' else ''
            resolved = [b.format(exe=exe) for b in binaries]
            if not any(os.path.exists(b) for b in resolved):
                return 'missing'
        return 'windows' if current_os == 'Windows' else 'linux'
        
    tool_bin = config.get('bin')
    if not tool_bin:
        check_path = config.get('check_path')
        if check_path:
            return 'windows' if os.path.exists(check_path) else 'missing'
        return 'windows' if current_os == 'Windows' else 'linux'
        
    supported = config.get('supported_os', [])
    is_windows_supported = ('windows' in supported) if supported else True
    
    if current_os == 'Windows':
        if is_windows_supported:
            if shutil.which(tool_bin) is not None:
                return 'windows'
            venv_bin = os.path.join('venv', 'Scripts', f"{tool_bin}.exe")
            if os.path.exists(venv_bin):
                return 'windows'
            if tool_bin == 'tshark' and os.path.exists(r"C:\Program Files\Wireshark\tshark.exe"):
                return 'windows'
                
        wsl_distro = get_preferred_wsl()
        if wsl_distro:
            try:
                res = subprocess.run(['wsl.exe', '-d', wsl_distro, '-u', 'root', '--', 'which', tool_bin], capture_output=True, text=True)
                if res.returncode == 0 and res.stdout.strip():
                    return 'wsl'
            except:
                pass
        return 'missing'
    else:
        if shutil.which(tool_bin) is not None:
            return 'linux'
        return 'missing'

def check_tool_status(tool_key):
    return check_tool_status_detail(tool_key) != 'missing'

import re

def sanitize_target(target):
    if not target:
        return target
    if target.startswith("http://") or target.startswith("https://"):
        target = target.split("://", 1)[1]
    if "/" in target:
        target = target.split("/", 1)[0]
    target = target.split(":")[0] if ":" in target and not target.count(":") > 1 else target
    return target

def validate_target(target):
    if not target:
        return True
    target = sanitize_target(target)
    pattern = r'^[\w\.\-]+(:\d+)?$'
    if not re.match(pattern, target):
        return False
    return True
