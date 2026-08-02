"""Centralized logging for the Yggdrasil Security Framework.

Provides:
    - init_logging()      — set up the root Yggdrasil logger with
                            rotating file + SQLite + optional SocketIO
                            handlers.
    - get_logger(name)    — convenience helper returning a child logger
                            under the 'yggdrasil' namespace.
    - emit_log_event()    — write a structured event to the system_events
                            table.
    - get_recent_errors() — query recent error_logs rows.
    - get_recent_events() — query recent system_events rows.
    - get_log_stats()     — summary counts.
    - clear_all_logs()    — truncate both log tables.

Log Rotation
------------
The rotating file handler is capped at 5 MB with 3 backups.  Old backups
are automatically rolled over so the log file never grows unbounded.
"""

import logging
import logging.handlers
import os
import sqlite3
import threading
import time
import weakref
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
LOG_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
LOG_FILE: str = os.path.join(LOG_DIR, "yggdrasil.log")

# Log rotation: 5 MB per file, keep 3 backups
MAX_LOG_BYTES: int = 5 * 1024 * 1024  # 5 MB
BACKUP_COUNT: int = 3

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------
_root_logger_initialized: bool = False
_socketio_ref: Optional[weakref.ref] = None
_emit_lock: threading.Lock = threading.Lock()
_sqlite_initialised: bool = False


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

def init_logging(app=None) -> None:
    """Create the root Yggdrasil logger with rotating file + SQLite handlers.

    Idempotent — subsequent calls are no-ops.
    """
    global _root_logger_initialized
    if _root_logger_initialized:
        return

    os.makedirs(LOG_DIR, exist_ok=True)

    root = logging.getLogger("yggdrasil")
    root.setLevel(logging.DEBUG)
    root.propagate = False

    # -- Rotating file handler (5 MB, 3 backups) ------------------------------
    try:
        fh = logging.handlers.RotatingFileHandler(
            LOG_FILE,
            maxBytes=MAX_LOG_BYTES,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        root.addHandler(fh)
    except Exception:
        pass  # best-effort

    # -- SQLite handler -------------------------------------------------------
    _ensure_log_tables()
    try:
        db_path = os.environ.get("YGG_STATS_DB", os.path.join(LOG_DIR, "stats.db"))
        sql_handler = SQLiteLogHandler(db_path=db_path)
        sql_handler.setLevel(logging.WARNING)
        root.addHandler(sql_handler)
    except Exception:
        pass

    _root_logger_initialized = True


# ---------------------------------------------------------------------------
# Logger access
# ---------------------------------------------------------------------------

def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the ``yggdrasil`` namespace."""
    if not name.startswith("yggdrasil."):
        name = f"yggdrasil.{name}"
    return logging.getLogger(name)


# ---------------------------------------------------------------------------
# SQLite helpers
# ---------------------------------------------------------------------------

def _get_db_connection(db_path: str = "") -> sqlite3.Connection:
    if not db_path:
        db_path = os.environ.get("YGG_STATS_DB", os.path.join(LOG_DIR, "stats.db"))
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_log_tables() -> None:
    global _sqlite_initialised
    if _sqlite_initialised:
        return
    conn = _get_db_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS error_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL,
                module TEXT NOT NULL,
                tool TEXT DEFAULT '',
                target TEXT DEFAULT '',
                message TEXT NOT NULL,
                traceback TEXT DEFAULT ''
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS system_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                source TEXT DEFAULT '',
                message TEXT NOT NULL,
                extra_data TEXT DEFAULT ''
            )
        """)
        conn.commit()
    finally:
        conn.close()
    _sqlite_initialised = True


def _prune_old_logs_conn(conn: sqlite3.Connection) -> None:
    """Keep at most 10 000 rows in each log table."""
    for table in ("error_logs", "system_events"):
        conn.execute(f"DELETE FROM {table} WHERE id NOT IN (SELECT id FROM {table} ORDER BY id DESC LIMIT 10000)")


# ---------------------------------------------------------------------------
# Event emission
# ---------------------------------------------------------------------------

def emit_log_event(
    event_type: str,
    message: str,
    source: str = "",
    extra_data: Optional[Dict[str, Any]] = None,
) -> None:
    """Write a structured event to the system_events table."""
    import json as _json
    _ensure_log_tables()
    conn = _get_db_connection()
    try:
        conn.execute(
            "INSERT INTO system_events (timestamp, event_type, source, message, extra_data) VALUES (?, ?, ?, ?, ?)",
            (datetime.now(timezone.utc).isoformat(), event_type, source, message,
             _json.dumps(extra_data) if extra_data else ""),
        )
        conn.commit()
        _prune_old_logs_conn(conn)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

def get_recent_errors(limit: int = 50, level: str = "") -> List[Dict[str, Any]]:
    _ensure_log_tables()
    conn = _get_db_connection()
    try:
        if level:
            rows = conn.execute(
                "SELECT * FROM error_logs WHERE level = ? ORDER BY id DESC LIMIT ?",
                (level.upper(), int(limit)),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM error_logs ORDER BY id DESC LIMIT ?",
                (int(limit),),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_recent_events(limit: int = 50, event_type: str = "") -> List[Dict[str, Any]]:
    _ensure_log_tables()
    conn = _get_db_connection()
    try:
        if event_type:
            rows = conn.execute(
                "SELECT * FROM system_events WHERE event_type = ? ORDER BY id DESC LIMIT ?",
                (event_type, int(limit)),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM system_events ORDER BY id DESC LIMIT ?",
                (int(limit),),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_log_stats() -> Dict[str, int]:
    _ensure_log_tables()
    conn = _get_db_connection()
    try:
        now = datetime.now(timezone.utc)
        today = now.strftime("%Y-%m-%d")
        total_errors = conn.execute("SELECT COUNT(*) FROM error_logs").fetchone()[0]
        total_events = conn.execute("SELECT COUNT(*) FROM system_events").fetchone()[0]
        errors_today = conn.execute(
            "SELECT COUNT(*) FROM error_logs WHERE timestamp LIKE ?", (f"{today}%",)
        ).fetchone()[0]
        warnings_today = conn.execute(
            "SELECT COUNT(*) FROM error_logs WHERE level = 'WARNING' AND timestamp LIKE ?",
            (f"{today}%",),
        ).fetchone()[0]
        return {
            "errors_today": errors_today,
            "warnings_today": warnings_today,
            "total_errors": total_errors,
            "total_events": total_events,
        }
    finally:
        conn.close()


def clear_all_logs() -> None:
    _ensure_log_tables()
    conn = _get_db_connection()
    try:
        conn.execute("DELETE FROM error_logs")
        conn.execute("DELETE FROM system_events")
        conn.commit()
    finally:
        conn.close()


def _prune_old_logs(db_path: str) -> None:
    """Public entry point used by test_log_pruning."""
    conn = _get_db_connection(db_path)
    try:
        _prune_old_logs_conn(conn)
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# SocketIO integration
# ---------------------------------------------------------------------------

def set_socketio_instance(sio: Any) -> None:
    global _socketio_ref
    if sio is None:
        _socketio_ref = None
    else:
        _socketio_ref = weakref.ref(sio)


class SocketIOLogHandler(logging.Handler):
    """Log handler that emits log records to SocketIO clients."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            ref = _socketio_ref
            if ref is None:
                return
            sio = ref()
            if sio is None:
                return
            sio.emit("log_entry", {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": record.levelname,
                "module": record.name,
                "message": self.format(record),
            })
        except Exception:
            pass


class SQLiteLogHandler(logging.Handler):
    """Log handler that writes ERROR+ records to the error_logs table."""

    def __init__(self, db_path: str = "") -> None:
        super().__init__()
        self._db_path = db_path or os.environ.get("YGG_STATS_DB", os.path.join(LOG_DIR, "stats.db"))

    def emit(self, record: logging.LogRecord) -> None:
        _ensure_log_tables()
        try:
            conn = _get_db_connection(self._db_path)
            try:
                conn.execute(
                    "INSERT INTO error_logs (timestamp, level, module, tool, target, message) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        datetime.now(timezone.utc).isoformat(),
                        record.levelname,
                        record.name,
                        getattr(record, "tool", ""),
                        getattr(record, "target", ""),
                        self.format(record),
                    ),
                )
                conn.commit()
                _prune_old_logs_conn(conn)
            finally:
                conn.close()
        except Exception:
            pass