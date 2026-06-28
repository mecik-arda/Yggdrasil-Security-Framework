from .packet_injector import handle_packet_injector
from .erebus_scanner import handle_erebus_scan
from .adv_syn import handle_adv_syn_scan
from .custom_html import handle_generate_dorks, handle_wayback
from .mimir_scanner import handle_mimir_scanner
from .bifrost import handle_bifrost_gateway
from .hydra import handle_hydra_bruteforce
from .subfinder import handle_subfinder
from .knockpy import handle_knockpy
from .gobuster_dns import handle_gobuster_dns
from .fenrir import handle_fenrir_cracker

# Map handler string names to actual Python functions
HANDLER_MAP = {
    'packet_injector': handle_packet_injector,
    'erebus_scan': handle_erebus_scan,
    'adv_syn_scan': handle_adv_syn_scan,
    'generate_dorks': handle_generate_dorks,
    'wayback': handle_wayback,
    'mimir_scanner': handle_mimir_scanner,
    'bifrost_gateway': handle_bifrost_gateway,
    'hydra_bruteforce': handle_hydra_bruteforce,
    'subfinder': handle_subfinder,
    'knockpy': handle_knockpy,
    'gobuster_dns': handle_gobuster_dns,
    'fenrir_cracker': handle_fenrir_cracker
}

def dispatch_handler(handler_name, target, data):
    handler_func = HANDLER_MAP.get(handler_name)
    if handler_func:
        return handler_func(target, data)
    else:
        return f"Error: Handler '{handler_name}' is not mapped or does not exist."
