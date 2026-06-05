import subprocess

def handle_packet_injector(target, data):
    action = data.get('packet_action', 'sniff') if data else 'sniff'
    interface = data.get('interface', 'eth0') if data else 'eth0'
    protocol = data.get('protocol', 'tcp') if data else 'tcp'
    
    cmd = ['sudo', 'python3', 'Runes/packet-injector/main.py', '--action', action, '--interface', interface]
    
    if action == 'inject':
        if not target or target == 'none':
            return ">> ERROR: Target IP is strictly required for injection."
            
        cmd.extend(['--protocol', protocol])
        cmd.extend(['--dst-ip', str(target)])
        
        src_ip = data.get('src_ip')
        if src_ip: cmd.extend(['--src-ip', src_ip])
        
        src_mac = data.get('src_mac')
        if src_mac: cmd.extend(['--src-mac', src_mac])
        
        dst_mac = data.get('dst_mac')
        if dst_mac: cmd.extend(['--dst-mac', dst_mac])
        
        ttl = data.get('ttl')
        if ttl: cmd.extend(['--ttl', str(ttl)])
        
        if protocol == 'tcp':
            dst_port = data.get('dst_port')
            if dst_port: cmd.extend(['--dst-port', str(dst_port)])
            
            src_port = data.get('src_port')
            if src_port: cmd.extend(['--src-port', str(src_port)])
            
            seq = data.get('seq')
            if seq: cmd.extend(['--seq', str(seq)])
            
            ack_num = data.get('ack_num')
            if ack_num: cmd.extend(['--ack-num', str(ack_num)])
            
            window = data.get('window')
            if window: cmd.extend(['--window', str(window)])
            
            flags = data.get('flags')
            if flags:
                flag_list = [f.strip() for f in flags.split(',') if f.strip()]
                if flag_list:
                    cmd.append('--flags')
                    cmd.extend(flag_list)
                    
        elif protocol == 'arp':
            arp_op = data.get('arp_op')
            if arp_op: cmd.extend(['--arp-op', str(arp_op)])
        
        rate = data.get('rate')
        if rate: cmd.extend(['--rate', str(rate)])
        count = data.get('count')
        if count: cmd.extend(['--count', str(count)])
        duration = data.get('duration')
        if duration: cmd.extend(['--duration', str(duration)])
        burst = data.get('burst')
        if burst: cmd.extend(['--burst', str(burst)])
        
    try:
        return subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=120).decode('utf-8')
    except subprocess.TimeoutExpired:
        return "TIMEOUT: Process took too long"
    except subprocess.CalledProcessError as e:
        return f"Execution Error:\n{e.output.decode('utf-8')}"
    except Exception as e:
        return f"System Error: {str(e)}"
