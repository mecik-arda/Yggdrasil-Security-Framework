"""
Tests for core.db — database initialisation and CRUD operations.
"""
import sqlite3 as real_sqlite3


from core.db import (
    init_db,
    get_db_stats,
    update_db_stats,
    log_scan_start,
    log_scan_end,
    init_c2_tables,
    log_c2_session,
    log_payload,
)


# ---------------------------------------------------------------------------
# init_db
# ---------------------------------------------------------------------------

class TestInitDb:
    def test_creates_tables(self, temp_db_path):
        init_db()
        conn = real_sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [r[0] for r in cursor.fetchall()]
        conn.close()
        assert 'stats' in tables
        assert 'scan_history' in tables

    def test_inserts_default_row(self, temp_db_path):
        init_db()
        conn = real_sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT total_scans, last_target, active_tool FROM stats WHERE id=1')
        row = cursor.fetchone()
        conn.close()
        assert row == (0, 'NONE', 'IDLE')

    def test_idempotent(self, temp_db_path):
        init_db()
        init_db()  # second call should not crash or duplicate
        conn = real_sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM stats')
        count = cursor.fetchone()[0]
        conn.close()
        assert count == 1


# ---------------------------------------------------------------------------
# get_db_stats / update_db_stats
# ---------------------------------------------------------------------------

class TestStats:
    def test_get_db_stats_returns_defaults_after_init(self):
        init_db()
        stats = get_db_stats()
        assert stats == {'total_scans': 0, 'last_target': 'NONE', 'active_tool': 'IDLE'}

    def test_update_and_get_stats(self):
        init_db()
        update_db_stats('192.168.1.1', 'NMAP')
        stats = get_db_stats()
        assert stats['total_scans'] == 1
        assert stats['last_target'] == '192.168.1.1'
        assert stats['active_tool'] == 'NMAP'

    def test_update_db_stats_increments_counter(self):
        init_db()
        update_db_stats('10.0.0.1', 'WHOIS')
        update_db_stats('10.0.0.2', 'DNSENUM')
        update_db_stats('10.0.0.3', 'NIKTO')
        stats = get_db_stats()
        # Other tests may also increment the counter (session-scoped DB)
        assert stats['total_scans'] >= 3
        assert stats['last_target'] == '10.0.0.3'
        assert stats['active_tool'] == 'NIKTO'


# ---------------------------------------------------------------------------
# scan_history
# ---------------------------------------------------------------------------

class TestScanHistory:
    def test_log_scan_start_creates_record(self, temp_db_path):
        init_db()
        log_scan_start('task-001', 'nmap', '10.0.0.1')
        conn = real_sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute(
            'SELECT task_id, tool, target, status, output FROM scan_history WHERE task_id=?',
            ('task-001',),
        )
        row = cursor.fetchone()
        conn.close()
        assert row is not None
        assert row[0] == 'task-001'
        assert row[1] == 'NMAP'
        assert row[2] == '10.0.0.1'
        assert row[3] == 'RUNNING'
        assert row[4] == ''

    def test_log_scan_start_replace(self, temp_db_path):
        """INSERT OR REPLACE should overwrite a duplicate task_id."""
        init_db()
        log_scan_start('task-dup', 'nmap', '10.0.0.1')
        log_scan_start('task-dup', 'whois', 'example.com')
        conn = real_sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM scan_history WHERE task_id=?', ('task-dup',))
        count = cursor.fetchone()[0]
        conn.close()
        assert count == 1

    def test_log_scan_end_updates_record(self, temp_db_path):
        init_db()
        log_scan_start('task-002', 'nmap', '10.0.0.1')
        log_scan_end('task-002', 'SUCCESS', 'scan output here')
        conn = real_sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute(
            'SELECT status, output FROM scan_history WHERE task_id=?', ('task-002',)
        )
        row = cursor.fetchone()
        conn.close()
        assert row[0] == 'SUCCESS'
        assert row[1] == 'scan output here'

    def test_log_scan_end_nonexistent_does_not_crash(self):
        init_db()
        # should not raise
        log_scan_end('nonexistent-task', 'SUCCESS', 'output')


# ---------------------------------------------------------------------------
# C2 tables
# ---------------------------------------------------------------------------

class TestC2Tables:
    def test_init_c2_tables_creates_tables(self, temp_db_path):
        init_c2_tables()
        conn = real_sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [r[0] for r in cursor.fetchall()]
        conn.close()
        assert 'c2_sessions' in tables
        assert 'payload_history' in tables
        assert 'attack_graph_nodes' in tables

    def test_log_c2_session(self, temp_db_path):
        init_c2_tables()
        log_c2_session('zombie-1', 4444, '192.168.1.100', 'linux')
        conn = real_sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute(
            'SELECT zombie_id, listener_port, remote_addr, os_type FROM c2_sessions'
        )
        row = cursor.fetchone()
        conn.close()
        assert row == ('zombie-1', 4444, '192.168.1.100', 'linux')

    def test_log_payload(self, temp_db_path):
        init_c2_tables()
        log_payload('meterpreter', 'windows', '10.0.0.1', 8080)
        conn = real_sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute(
            'SELECT payload_type, platform, lhost, lport FROM payload_history'
        )
        row = cursor.fetchone()
        conn.close()
        assert row == ('meterpreter', 'windows', '10.0.0.1', 8080)
