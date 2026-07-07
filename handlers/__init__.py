from .packet_injector import handle_packet_injector
from .erebus_scanner import handle_erebus_scan
from .adv_syn import handle_adv_syn_scan
from .custom_html import handle_generate_dorks, handle_wayback, handle_update_modules, handle_odin_ai, handle_loki_ai
from .mimir_scanner import handle_mimir_scanner
from .bifrost import handle_bifrost_gateway
from .hydra import handle_hydra_bruteforce
from .subfinder import handle_subfinder
from .knockpy import handle_knockpy
from .gobuster_dns import handle_gobuster_dns
from .fenrir import handle_fenrir_cracker
from .muninn_scanner import handle_muninn_scan
from .sleipnir_scanner import handle_sleipnir_scan
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
    'fenrir_cracker': handle_fenrir_cracker,
    'muninn_scan': handle_muninn_scan,
    'sleipnir_scan': handle_sleipnir_scan,
    'update_modules': handle_update_modules,
    'odin_ai': handle_odin_ai,
    'loki_ai': handle_loki_ai
}
def dispatch_handler(handler_name, target, data, output_callback=None):
    handler_func = HANDLER_MAP.get(handler_name)
    if handler_func:
        return handler_func(target, data, output_callback=output_callback)
    else:
        return f"Error: Handler '{handler_name}' is not mapped or does not exist."
