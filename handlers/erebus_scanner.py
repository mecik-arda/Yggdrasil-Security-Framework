from .utils import run_command_safely


def handle_erebus_scan(target, data):
    if not target or target == 'none':
        return ">> ERROR: Target IP/Domain is required for Erebus Scanner."

    ports = data.get('ports', '1-1024') if data else '1-1024'
    if not ports or not ports.strip():
        ports = '1-1024'

    cmd = ['cargo', 'run', '--manifest-path', 'Runes/erebus-scanner/Cargo.toml', '--', '-t', str(target), '-p', str(ports)]

    if data:
        if data.get('banner') == 'true':
            cmd.append('--banner')
        if data.get('randomize') == 'true':
            cmd.append('--randomize')
        if data.get('adaptive') == 'true':
            cmd.append('--adaptive')
        proxy = data.get('proxy')
        if proxy and proxy.strip():
            cmd.extend(['--proxy', str(proxy).strip()])

    return run_command_safely(cmd, timeout=180)
