import time
import json
import threading

TEAM_USERS = {}
TEAM_MESSAGES = []
TEAM_MAX_MESSAGES = 200
TEAM_LOCK = threading.Lock()

EVENT_HANDLERS = {}


def register_user(sid, username):
    with TEAM_LOCK:
        TEAM_USERS[sid] = {
            "username": username,
            "joined_at": time.time(),
            "last_seen": time.time(),
            "active": True
        }
    broadcast_event("user_joined", {"username": username, "total_users": len(TEAM_USERS)})
    return {"status": "success", "users": get_user_list()}


def remove_user(sid):
    with TEAM_LOCK:
        user = TEAM_USERS.pop(sid, None)
        if user:
            broadcast_event("user_left", {"username": user["username"], "total_users": len(TEAM_USERS)})


def get_user_list():
    with TEAM_LOCK:
        return [{"username": u["username"], "active": u["active"], "joined_at": u["joined_at"]} for u in TEAM_USERS.values()]


def add_team_message(sid, message):
    with TEAM_LOCK:
        user = TEAM_USERS.get(sid, {"username": "unknown"})
        msg = {
            "username": user["username"],
            "message": message[:500],
            "time": time.time()
        }
        TEAM_MESSAGES.append(msg)
        if len(TEAM_MESSAGES) > TEAM_MAX_MESSAGES:
            TEAM_MESSAGES.pop(0)
    broadcast_event("team_message", msg)
    return {"status": "success"}


def get_team_messages(since=0):
    with TEAM_LOCK:
        if since == 0:
            return TEAM_MESSAGES[-50:]
        return [m for m in TEAM_MESSAGES if m["time"] > since]


def broadcast_event(event_name, data):
    payload = json.dumps({"event": event_name, "data": data, "time": time.time()})
    with TEAM_LOCK:
        for handler in list(EVENT_HANDLERS.values()):
            try:
                handler(payload)
            except Exception:
                pass


def register_event_handler(handler_id, handler_func):
    with TEAM_LOCK:
        EVENT_HANDLERS[handler_id] = handler_func


def unregister_event_handler(handler_id):
    with TEAM_LOCK:
        EVENT_HANDLERS.pop(handler_id, None)


def notify_scan_start(tool, target):
    broadcast_event("scan_started", {"tool": tool, "target": target})


def notify_scan_complete(tool, target, status):
    broadcast_event("scan_completed", {"tool": tool, "target": target, "status": status})


def notify_zombie_connected(zombie_id, addr, os_type):
    broadcast_event("zombie_connected", {"zombie_id": zombie_id, "addr": addr, "os_type": os_type})


def notify_zombie_disconnected(zombie_id, addr):
    broadcast_event("zombie_disconnected", {"zombie_id": zombie_id, "addr": addr})


def notify_beacon_checkin(beacon_id, hostname):
    broadcast_event("beacon_checkin", {"beacon_id": beacon_id, "hostname": hostname})


def notify_graph_update(node_id, label, node_type):
    broadcast_event("graph_updated", {"node_id": node_id, "label": label, "node_type": node_type})
