import threading
import time
import psutil
import socket

# Global State Variables
CURRENT_CPU = 0.0
PING_MS = None
OLLAMA_ONLINE = False

def _system_monitor():
    global CURRENT_CPU, PING_MS, OLLAMA_ONLINE
    psutil.cpu_percent(interval=None) # Initialize
    
    while True:
        # 1. Update CPU
        CURRENT_CPU = psutil.cpu_percent(interval=None)
        
        # 2. Update Ping (Fast network check)
        try:
            s_time = time.time()
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5) # FIXED: Using instance timeout instead of setdefaulttimeout
            s.connect(("8.8.8.8", 53))
            s.close()
            PING_MS = int((time.time() - s_time) * 1000)
        except Exception:
            PING_MS = None
            
        # 3. Update Ollama Status
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            s.connect(("127.0.0.1", 11434))
            s.close()
            OLLAMA_ONLINE = True
        except Exception:
            OLLAMA_ONLINE = False
            
        # Sleep before next update
        time.sleep(2)

def start_monitor():
    thread = threading.Thread(target=_system_monitor, daemon=True)
    thread.start()
