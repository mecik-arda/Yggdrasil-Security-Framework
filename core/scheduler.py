"""Scan scheduling — cron-like scheduled task runner.

Schedules are stored in ``scans/schedules.json`` and executed by a
background thread that polls every ~30 seconds.
"""
import json
import os
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.logger import get_logger

SCHEDULE_FILE: str = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "scans",
    "schedules.json",
)

_schedules: Dict[str, Dict[str, Any]] = {}
_lock: threading.Lock = threading.Lock()
_runner: Optional[threading.Thread] = None
_stop_flag: threading.Event = threading.Event()


def _load_schedules() -> None:
    global _schedules
    try:
        os.makedirs(os.path.dirname(SCHEDULE_FILE), exist_ok=True)
        with open(SCHEDULE_FILE, "r", encoding="utf-8") as fh:
            _schedules = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        _schedules = {}


def _save_schedules() -> None:
    os.makedirs(os.path.dirname(SCHEDULE_FILE), exist_ok=True)
    with open(SCHEDULE_FILE, "w", encoding="utf-8") as fh:
        json.dump(_schedules, fh, indent=2)


def list_schedules() -> List[Dict[str, Any]]:
    with _lock:
        return [{"id": k, **v} for k, v in _schedules.items()]


def add_schedule(tool: str, target: str, interval_minutes: int) -> str:
    sid = f"sched_{int(time.time())}"
    with _lock:
        _schedules[sid] = {
            "tool": tool,
            "target": target,
            "interval_minutes": interval_minutes,
            "created_at": datetime.now().isoformat(),
            "last_run": None,
        }
        _save_schedules()
    return sid


def remove_schedule(sid: str) -> bool:
    with _lock:
        if sid not in _schedules:
            return False
        del _schedules[sid]
        _save_schedules()
    return True


def _run_scheduler_loop() -> None:
    log = get_logger("scheduler")
    while not _stop_flag.wait(timeout=30):
        with _lock:
            items = list(_schedules.items())
        for sid, cfg in items:
            last_run = cfg.get("last_run")
            interval = cfg.get("interval_minutes", 60)
            now = time.time()
            if last_run and (now - last_run < interval * 60):
                continue
            log.info(f"Running scheduled scan: {cfg['tool']} → {cfg['target']}")
            try:
                from core.tool_runner import execute_tool
                execute_tool(cfg["tool"], cfg["target"])
            except Exception as exc:
                log.error(f"Scheduled scan failed for {sid}: {exc}")
            with _lock:
                if sid in _schedules:
                    _schedules[sid]["last_run"] = time.time()
                    _save_schedules()


def start_scheduler() -> None:
    global _runner
    _stop_flag.clear()
    _load_schedules()
    if _runner and _runner.is_alive():
        return
    _runner = threading.Thread(target=_run_scheduler_loop, daemon=True, name="scan-scheduler")
    _runner.start()


def stop_scheduler() -> None:
    _stop_flag.set()