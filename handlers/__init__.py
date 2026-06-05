from .packet_injector import handle_packet_injector
from .erebus_scanner import handle_erebus_scan
from .adv_syn import handle_adv_syn_scan
from .custom_html import handle_generate_dorks, handle_wayback
from .mimir_scanner import handle_mimir_scanner

# Map handler string names to actual Python functions
HANDLER_MAP = {
    'packet_injector': handle_packet_injector,
    'erebus_scan': handle_erebus_scan,
    'adv_syn_scan': handle_adv_syn_scan,
    'generate_dorks': handle_generate_dorks,
    'wayback': handle_wayback,
    'mimir_scanner': handle_mimir_scanner
}

def dispatch_handler(handler_name, target, data):
    handler_func = HANDLER_MAP.get(handler_name)
    if handler_func:
        return handler_func(target, data)
    else:
        return f"Error: Handler '{handler_name}' is not mapped or does not exist."
