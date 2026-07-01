from .utils import run_command_safely
def handle_packet_injector(target, data):
    action = data.get('packet_action', 'sniff') if data else 'sniff'
    interface = data.get('interface', 'eth0') if data else 'eth0'
    protocol = data.get('protocol', 'tcp') if data else 'tcp'
    cmd = ['sudo', 'python3', 'Runes/packet-injector/main.py', '--action', action, '--interface', interface]
    if action == 'inject':
        if not target or target == 'none':
            return ">> ERROR: Target IP is strictly required for injection."
        cmd.extend(['--protocol', protocol, '--dst-ip', str(target)])
        general_args = {
            'src_ip': '--src-ip',
            'src_mac': '--src-mac',
            'dst_mac': '--dst-mac',
            'ttl': '--ttl',
            'rate': '--rate',
            'count': '--count',
            'duration': '--duration',
            'burst': '--burst'
        }
        for key, arg_flag in general_args.items():
            val = data.get(key)
            if val:
                cmd.extend([arg_flag, str(val)])
        if protocol == 'tcp':
            tcp_args = {
                'dst_port': '--dst-port',
                'src_port': '--src-port',
                'seq': '--seq',
                'ack_num': '--ack-num',
                'window': '--window'
            }
            for key, arg_flag in tcp_args.items():
                val = data.get(key)
                if val:
                    cmd.extend([arg_flag, str(val)])
            flags = data.get('flags')
            if flags:
                flag_list = [f.strip() for f in flags.split(',') if f.strip()]
                if flag_list:
                    cmd.append('--flags')
                    cmd.extend(flag_list)
        elif protocol == 'arp':
            arp_op = data.get('arp_op')
            if arp_op: cmd.extend(['--arp-op', str(arp_op)])
    return run_command_safely(cmd, timeout=120)
