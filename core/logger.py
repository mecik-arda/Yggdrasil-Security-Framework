"""
Phase 3: Centralized Logging Module for Yggdrasil Security Framework.

Provides structured logging with three backends:
  1. SQLiteLogHandler  — writes to error_logs / system_events tables in stats.db
  2. SocketIOLogHandler — pushes log_entry events to the browser in real time
  3. RotatingFileHandler — writes to logs/yggdrasil.log (5 MB rotation, 3 backups)

Usage:
    from core.logger import get_logger
    log = get_logger(__name__)
    log.error("Something broke", extra={'tool': 'nmap', 'target': '10.0.0.1'})
"""

import logging
import logging.handlers
import os
import json
import sqlite3
import traceback as tb
import weakref
import threading
from datetime import datetime

# ---------------------------------------------------------------------------
# module-level state
# ---------------------------------------------------------------------------
_socketio_ref = None          # weakref to the Flask-SocketIO instance
_root_logger_initialized = False

# constants
MAX_ROWS_PER_TABLE = 5000
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'yggdrasil.log')

# ---------------------------------------------------------------------------
# custom handlers
# ---------------------------------------------------------------------------

class SQLiteLogHandler(logging.Handler):
    """Writes structured log records into stats.db (error_logs / system_events)."""

    def __init__(self, db_path='stats.db'):
        super().__init__()
        self.db_path = db_path
        self._lock = threading.Lock()
        self._conn = None
        self._log_count = 0

    def _get_conn(self):
        if self._conn is None:
            from core.db import get_connection
            self._conn = get_connection()
        return self._conn

    def emit(self, record: logging.LogRecord):
        _ensure_log_tables()
        try:
            msg = self.format(record)
            level = record.levelname.upper()
            module = record.name
            # extra fields (tool, target, traceback, extra_data)
            tool = getattr(record, 'tool', None)
            target = getattr(record, 'target', None)
            exc_text = None
            if record.exc_info and record.exc_info != (None, None, None):
                exc_text = ''.join(tb.format_exception(*record.exc_info))
            extra_data = getattr(record, 'extra_data', None)
            if extra_data and not isinstance(extra_data, str):
                extra_data = json.dumps(extra_data, default=str)

            with self._lock:
                conn = self._get_conn()
                c = conn.cursor()
                c.execute(
                    'INSERT INTO error_logs (level, module, tool, target, message, traceback, extra_data) '
                    'VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (level, module, tool, target, msg, exc_text, extra_data)
                )
                conn.commit()
                
                # Periodically prune old logs (e.g., every 500 logs)
                self._log_count += 1
                if self._log_count >= 500:
                    self._log_count = 0
                    _prune_old_logs_conn(conn)
        except Exception:
            self.handleError(record)


class SocketIOLogHandler(logging.Handler):
    """Pushes log_entry events to connected browsers via SocketIO.

    Holds a weak reference to the SocketIO instance so it degrades gracefully
    when SocketIO is unavailable (polling-mode fallback).
    """

    def __init__(self):
        super().__init__()
        self._lock = threading.Lock()

    @property
    def _socketio(self):
        """Resolve the weak reference (returns None if the object was garbage-collected)."""
        if _socketio_ref is None:
            return None
        return _socketio_ref()

    def emit(self, record: logging.LogRecord):
        sio = self._socketio
        if sio is None:
            return
        try:
            level = record.levelname.upper()
            module = record.name
            tool = getattr(record, 'tool', None)
            target = getattr(record, 'target', None)
            has_traceback = bool(record.exc_info and record.exc_info != (None, None, None))

            payload = {
                'id': getattr(record, 'log_id', 0),
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'level': level,
                'module': module,
                'tool': tool,
                'target': target,
                'message': self.format(record),
                'has_traceback': has_traceback,
            }
            with self._lock:
                sio.emit('log_entry', payload)
        except Exception:
            self.handleError(record)


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------

def init_logging(app=None, db_path='stats.db'):
    """One-time setup. Creates all handlers, configures the root Yggdrasil logger.

    Must be called once during app startup (inside an app-context if using Flask).
    """
    global _root_logger_initialized

    if _root_logger_initialized:
        return

    # ensure log directory exists
    os.makedirs(LOG_DIR, exist_ok=True)

    # root logger for our namespace
    root = logging.getLogger('yggdrasil')
    root.setLevel(logging.DEBUG)
    root.propagate = False  # don't bubble to the Python root logger

    # -- handler 1: rotating file (5 MB, 3 backups) --
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        '[%(asctime)s] %(levelname)-8s %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    ))
    root.addHandler(file_handler)

    # -- handler 2: SQLite --
    sqlite_handler = SQLiteLogHandler(db_path=db_path)
    sqlite_handler.setLevel(logging.WARNING)  # WARNING+ go to DB
    sqlite_handler.setFormatter(logging.Formatter('%(message)s'))
    root.addHandler(sqlite_handler)

    # -- handler 3: SocketIO real-time push --
    sio_handler = SocketIOLogHandler()
    sio_handler.setLevel(logging.WARNING)
    sio_handler.setFormatter(logging.Formatter('%(message)s'))
    root.addHandler(sio_handler)

    _root_logger_initialized = True

    # prune old rows on startup
    _prune_old_logs(db_path)


def set_socketio_instance(sio):
    """Store a weak reference to the Flask-SocketIO instance.

    Called from app.py after team_socketio.init_app(app).
    """
    global _socketio_ref
    if sio is not None:
        _socketio_ref = weakref.ref(sio)
    else:
        _socketio_ref = None


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the 'yggdrasil' namespace.

    Usage:
        log = get_logger(__name__)
        log.error("something broke", extra={'tool': 'nmap', 'target': '10.0.0.1'})
    """
    if not name.startswith('yggdrasil.'):
        name = f'yggdrasil.{name}'
    return logging.getLogger(name)


def emit_log_event(event_type: str, message: str, source: str = None, extra_data: dict = None):
    """Programmatic system-event entry (for non-logger call-sites)."""
    _ensure_log_tables()
    from core.db import get_connection
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        'INSERT INTO system_events (event_type, source, message, extra_data) VALUES (?, ?, ?, ?)',
        (event_type, source, message, json.dumps(extra_data) if extra_data else None)
    )
    conn.commit()
    conn.close()


def get_recent_errors(limit=100, level=None, tool=None, since=None):
    """Query the error_logs table. Returns list of dicts (newest first)."""
    _ensure_log_tables()
    from core.db import get_connection
    conn = get_connection()
    c = conn.cursor()
    query = 'SELECT id, timestamp, level, module, tool, target, message, traceback, extra_data FROM error_logs WHERE 1=1'
    params = []
    if level:
        query += ' AND level = ?'
        params.append(level.upper())
    if tool:
        query += ' AND tool = ?'
        params.append(tool)
    if since:
        query += ' AND timestamp >= ?'
        params.append(since)
    query += ' ORDER BY timestamp DESC LIMIT ?'
    params.append(int(limit))
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return [
        {
            'id': r[0], 'timestamp': r[1], 'level': r[2], 'module': r[3],
            'tool': r[4], 'target': r[5], 'message': r[6],
            'traceback': r[7], 'extra_data': r[8],
        }
        for r in rows
    ]


def get_recent_events(limit=100, event_type=None, since=None):
    """Query the system_events table. Returns list of dicts (newest first)."""
    _ensure_log_tables()
    from core.db import get_connection
    conn = get_connection()
    c = conn.cursor()
    query = 'SELECT id, timestamp, event_type, source, message, extra_data FROM system_events WHERE 1=1'
    params = []
    if event_type:
        query += ' AND event_type = ?'
        params.append(event_type)
    if since:
        query += ' AND timestamp >= ?'
        params.append(since)
    query += ' ORDER BY timestamp DESC LIMIT ?'
    params.append(int(limit))
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return [
        {
            'id': r[0], 'timestamp': r[1], 'event_type': r[2],
            'source': r[3], 'message': r[4], 'extra_data': r[5],
        }
        for r in rows
    ]


def get_log_stats():
    """Return summary stats for the dashboard badge row."""
    _ensure_log_tables()
    from core.db import get_connection
    conn = get_connection()
    c = conn.cursor()
    today = datetime.utcnow().strftime('%Y-%m-%d')
    c.execute("SELECT COUNT(*) FROM error_logs WHERE level='ERROR' AND timestamp >= ?", (today,))
    errors_today = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM error_logs WHERE level='WARNING' AND timestamp >= ?", (today,))
    warnings_today = c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT tool) FROM error_logs WHERE tool IS NOT NULL AND timestamp >= ?", (today,))
    unique_tools = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM error_logs WHERE level='CRITICAL' AND timestamp >= ?", (today,))
    critical_today = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM error_logs")
    total_errors = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM system_events")
    total_events = c.fetchone()[0]
    c.execute("SELECT message, timestamp FROM error_logs WHERE level IN ('ERROR','CRITICAL') ORDER BY timestamp DESC LIMIT 1")
    last_error = c.fetchone()
    conn.close()
    return {
        'errors_today': errors_today,
        'warnings_today': warnings_today,
        'unique_tools_errored': unique_tools,
        'critical_today': critical_today,
        'total_errors': total_errors,
        'total_events': total_events,
        'last_error': {'message': last_error[0], 'timestamp': last_error[1]} if last_error else None,
    }


def clear_all_logs():
    """Delete all entries from both log tables."""
    _ensure_log_tables()
    from core.db import get_connection
    conn = get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM error_logs')
    c.execute('DELETE FROM system_events')
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# internal helpers
# ---------------------------------------------------------------------------

def _ensure_log_tables():
    """Create log tables if they don't exist (idempotent, safe to call anytime)."""
    try:
        from core.db import get_connection
        conn = get_connection()
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS error_logs
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                      level TEXT NOT NULL,
                      module TEXT,
                      tool TEXT,
                      target TEXT,
                      message TEXT NOT NULL,
                      traceback TEXT,
                      extra_data TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS system_events
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                      event_type TEXT NOT NULL,
                      source TEXT,
                      message TEXT NOT NULL,
                      extra_data TEXT)''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_error_logs_timestamp ON error_logs(timestamp DESC)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_error_logs_level ON error_logs(level)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_system_events_timestamp ON system_events(timestamp DESC)')
        conn.commit()
        conn.close()
    except Exception:
        pass


def _prune_old_logs_conn(conn):
    """Helper to prune logs using an existing connection."""
    try:
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM error_logs')
        count = c.fetchone()[0]
        if count > MAX_ROWS_PER_TABLE:
            c.execute(
                'DELETE FROM error_logs WHERE id NOT IN '
                '(SELECT id FROM error_logs ORDER BY timestamp DESC LIMIT ?)',
                (MAX_ROWS_PER_TABLE,)
            )
        c.execute('SELECT COUNT(*) FROM system_events')
        count = c.fetchone()[0]
        if count > MAX_ROWS_PER_TABLE:
            c.execute(
                'DELETE FROM system_events WHERE id NOT IN '
                '(SELECT id FROM system_events ORDER BY timestamp DESC LIMIT ?)',
                (MAX_ROWS_PER_TABLE,)
            )
        conn.commit()
    except Exception:
        pass


def _prune_old_logs(db_path):
    """Keep only the newest MAX_ROWS_PER_TABLE rows in each table."""
    try:
        from core.db import get_connection
        conn = get_connection()
        _prune_old_logs_conn(conn)
        conn.close()
    except Exception:
        pass  # best-effort; never crash startup on log pruning
