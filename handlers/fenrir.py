import subprocess
import os
import platform

def handle_fenrir_cracker(target, data):
    hash_mode = data.get('fenrir_hash_mode', 'md5')
    attack_mode = data.get('fenrir_attack_mode', 'dict')
    wordlist = data.get('fenrir_wordlist', '')
    
    exe = '.exe' if platform.system() == 'Windows' else ''
    fenrir_bin = os.path.join('Runes', 'fenrir-hash-cracker', 'build', f'fenrir{exe}')
    if not os.path.exists(fenrir_bin):
        fenrir_bin = os.path.join('Runes', 'fenrir-hash-cracker', 'build', 'Release', f'fenrir{exe}')

    if not os.path.exists(fenrir_bin):
        return ">> ERROR: FENRIR BINARY NOT FOUND. PLEASE INSTALL/UPDATE THE MODULE."

    cmd = [fenrir_bin, "-m", hash_mode, "-a", attack_mode]
    
    if wordlist:
        cmd.extend(["-w", wordlist])
        
    cmd.extend(["-H", target, "--no-tui"])

    try:
        result = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=300).decode('utf-8', errors='replace')
        return result
    except subprocess.TimeoutExpired:
        return ">> ERROR: TIMEOUT EXPIRED (5 MINUTES MAX)."
    except subprocess.CalledProcessError as e:
        return f">> EXECUTION ERROR:\n{e.output.decode('utf-8', errors='replace')}"
    except Exception as e:
        return f">> SYSTEM ERROR: {str(e)}"
