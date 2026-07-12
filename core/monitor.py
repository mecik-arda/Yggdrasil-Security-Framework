import threading
import time
import psutil
import socket

# Global State Variables
CURRENT_CPU = 0.0
PING_MS = None
OLLAMA_ONLINE = False
CPU_PERCENT = 0.0
RAM_PERCENT = 0.0

# Optional callback called after each monitor tick: callback(cpu, ram, ping, ollama)
_on_tick = None


def _system_monitor():
    global CURRENT_CPU, PING_MS, OLLAMA_ONLINE, CPU_PERCENT, RAM_PERCENT
    psutil.cpu_percent(interval=None)  # Initialize

    while True:
        # 1. Update CPU
        CPU_PERCENT = psutil.cpu_percent(interval=None)
        CURRENT_CPU = CPU_PERCENT

        # 2. Update RAM
        RAM_PERCENT = psutil.virtual_memory().percent

        # 3. Update Ping (Fast network check)
        try:
            s_time = time.time()
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            s.connect(("8.8.8.8", 53))
            s.close()
            PING_MS = int((time.time() - s_time) * 1000)
        except Exception:
            PING_MS = None

        # 4. Update Ollama Status
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.1)
            s.connect(("127.0.0.1", 11434))
            s.close()
            OLLAMA_ONLINE = True
        except Exception:
            OLLAMA_ONLINE = False

        # 5. Notify optional callback (used by SocketIO heartbeat)
        if _on_tick:
            try:
                _on_tick(CURRENT_CPU, RAM_PERCENT, PING_MS, OLLAMA_ONLINE)
            except Exception:
                pass

        # Sleep before next update
        time.sleep(2)


def set_tick_callback(callback):
    """Register a function to call after each monitor cycle.
    Signature: callback(cpu: float, ram: float, ping: int|None, ollama: bool)
    """
    global _on_tick
    _on_tick = callback


def start_monitor():
    thread = threading.Thread(target=_system_monitor, daemon=True)
    thread.start()
