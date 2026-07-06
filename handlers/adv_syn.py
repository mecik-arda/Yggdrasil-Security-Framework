from .utils import run_command_safely
def handle_adv_syn_scan(target, data, output_callback=None):
    syn_mode = data.get('syn_mode', 'auto') if data else 'auto'
    if syn_mode == 'auto':
        if not target or target == 'none':
            return ">> ERROR: Target IP is required for Automated SYN Scan."
        max_port = data.get('max_port', '1000') if data else '1000'
        cmd = ["bash", "Runes/Advanced-SYN-Scanner/auto_scan.sh", str(target), str(max_port)]
    else:
        manual_target = data.get('target', target) # Might override base target
        if not manual_target or manual_target == 'none':
            return ">> ERROR: Target IP is required for Manual SYN Scan."
        source_ip = data.get('source_ip', '') if data else ''
        start_port = data.get('start_port', '1') if data else '1'
        end_port = data.get('end_port', '1000') if data else '1000'
        cmd = ["sudo", "Runes/Advanced-SYN-Scanner/syn_scanner"]
        if source_ip:
            cmd.extend(["-s", str(source_ip)])
        cmd.extend(["-t", str(manual_target), "-p", str(start_port), "-e", str(end_port)])
    return run_command_safely(cmd, timeout=120, output_callback=output_callback)
