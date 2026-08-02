"""
C2 Repository — Hybrid in-memory + SQLite persistence for listeners and zombies.

Provides a transparent persistence layer that mirrors ``LISTENERS`` and
``ZOMBIES`` dicts in SQLite, without breaking the existing in-memory API.
"""
import time
import json
import threading
from core.db import get_connection


# -- Listeners --------------------------------------------------------------

def persist_listener(listener_id: str, data: dict):
    """Insert or update a C2 listener record in the database."""
    try:
        conn = get_connection()
        try:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS c2_listeners_persist
                   (listener_id TEXT PRIMARY KEY,
                    name TEXT, port INTEGER, bind_addr TEXT,
                    status TEXT, auth_enabled INTEGER,
                    api_key TEXT, started_at REAL,
                    total_connections INTEGER DEFAULT 0,
                    updated_at REAL)"""
            )
            conn.execute(
                """INSERT OR REPLACE INTO c2_listeners_persist
                   (listener_id, name, port, bind_addr, status, auth_enabled,
                    api_key, started_at, total_connections, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    listener_id,
                    str(data.get('name', '')),
                    int(data.get('port', 0)),
                    str(data.get('bind_addr', '0.0.0.0')),
                    str(data.get('status', 'unknown')),
                    1 if data.get('auth_enabled') else 0,
                    str(data.get('api_key', '')),
                    float(data.get('started_at', time.time())),
                    int(data.get('total_connections', 0)),
                    time.time(),
                ),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception:
        pass  # Best-effort persistence — never break the in-memory path


def load_all_listeners():
    """Return a dict of persisted listener records keyed by listener_id."""
    records = {}
    try:
        conn = get_connection()
        try:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS c2_listeners_persist
                   (listener_id TEXT PRIMARY KEY,
                    name TEXT, port INTEGER, bind_addr TEXT,
                    status TEXT, auth_enabled INTEGER,
                    api_key TEXT, started_at REAL,
                    total_connections INTEGER DEFAULT 0,
                    updated_at REAL)"""
            )
            rows = conn.execute(
                "SELECT listener_id, name, port, bind_addr, status, auth_enabled, api_key, started_at, total_connections FROM c2_listeners_persist"
            ).fetchall()
            for row in rows:
                records[row[0]] = {
                    'name': row[1],
                    'port': row[2],
                    'bind_addr': row[3],
                    'status': row[4],
                    'auth_enabled': bool(row[5]),
                    'api_key': row[6],
                    'started_at': row[7],
                    'total_connections': row[8],
                }
        finally:
            conn.close()
    except Exception:
        pass
    return records


def delete_listener(listener_id: str):
    """Remove a persisted listener record."""
    try:
        conn = get_connection()
        try:
            conn.execute("DELETE FROM c2_listeners_persist WHERE listener_id = ?", (listener_id,))
            conn.commit()
        finally:
            conn.close()
    except Exception:
        pass


# -- Zombies / Sessions -----------------------------------------------------

def persist_zombie(zombie_id: str, data: dict):
    """Log a new C2 zombie session in the database."""
    try:
        conn = get_connection()
        try:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS c2_zombies_persist
                   (zombie_id TEXT PRIMARY KEY,
                    listener_id TEXT,
                    addr TEXT,
                    hostname TEXT,
                    os_type TEXT,
                    connected_at REAL,
                    last_seen REAL,
                    status TEXT,
                    updated_at REAL)"""
            )
            conn.execute(
                """INSERT OR REPLACE INTO c2_zombies_persist
                   (zombie_id, listener_id, addr, hostname, os_type,
                    connected_at, last_seen, status, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    zombie_id,
                    str(data.get('listener_id', '')),
                    str(data.get('addr', '')),
                    str(data.get('hostname', 'Unknown')),
                    str(data.get('os_type', 'Unknown')),
                    float(data.get('connected_at', time.time())),
                    float(data.get('last_seen', time.time())),
                    str(data.get('status', 'connected')),
                    time.time(),
                ),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception:
        pass


def update_zombie_status(zombie_id: str, status: str):
    """Update the status of a persisted zombie."""
    try:
        conn = get_connection()
        try:
            conn.execute(
                "UPDATE c2_zombies_persist SET status = ?, last_seen = ?, updated_at = ? WHERE zombie_id = ?",
                (status, time.time(), time.time(), zombie_id),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception:
        pass


def load_all_zombies():
    """Return a dict of persisted zombie records keyed by zombie_id."""
    records = {}
    try:
        conn = get_connection()
        try:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS c2_zombies_persist
                   (zombie_id TEXT PRIMARY KEY,
                    listener_id TEXT,
                    addr TEXT,
                    hostname TEXT,
                    os_type TEXT,
                    connected_at REAL,
                    last_seen REAL,
                    status TEXT,
                    updated_at REAL)"""
            )
            rows = conn.execute(
                "SELECT zombie_id, listener_id, addr, hostname, os_type, connected_at, last_seen, status FROM c2_zombies_persist"
            ).fetchall()
            for row in rows:
                records[row[0]] = {
                    'listener_id': row[1],
                    'addr': row[2],
                    'hostname': row[3],
                    'os_type': row[4],
                    'connected_at': row[5],
                    'last_seen': row[6],
                    'status': row[7],
                }
        finally:
            conn.close()
    except Exception:
        pass
    return records