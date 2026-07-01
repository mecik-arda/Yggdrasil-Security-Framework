from .utils import run_command_safely
import os
import platform
def handle_fenrir_cracker(target, data):
    if data is None:
        data = {}
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
    if not os.path.isfile(target):
        cmd.extend(["--hash", target, "--no-tui"])
    else:
        cmd.extend(["-H", target, "--no-tui"])
    return run_command_safely(cmd, timeout=300)
