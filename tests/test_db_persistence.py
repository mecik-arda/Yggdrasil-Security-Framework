"""core/db.py SQLite persistence testleri"""
import pytest, time
from yggapp import create_app, init_services


@pytest.fixture(scope="session")
def app():
    a = create_app("test")
    init_services(a)
    return a


class TestDBConnection:
    def test_get_connection(self):
        from core.db import get_connection
        conn = get_connection()
        assert conn is not None
        conn.close()

    def test_wal_mode(self):
        from core.db import get_connection
        conn = get_connection()
        cursor = conn.execute("PRAGMA journal_mode")
        mode = cursor.fetchone()[0]
        assert mode.lower() == "wal"
        conn.close()

    def test_stats_table_exists(self):
        from core.db import get_connection
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='stats'")
        assert c.fetchone() is not None
        conn.close()

    def test_scan_history_table_exists(self):
        from core.db import get_connection
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scan_history'")
        assert c.fetchone() is not None
        conn.close()

    def test_c2_sessions_table_exists(self):
        from core.db import get_connection
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='c2_sessions'")
        assert c.fetchone() is not None
        conn.close()


class TestDBOperations:
    def test_get_db_stats(self):
        from core.db import get_db_stats
        stats = get_db_stats()
        assert "total_scans" in stats
        assert "last_target" in stats
        assert isinstance(stats["total_scans"], int)

    def test_update_db_stats(self, app):
        from core.db import update_db_stats, get_db_stats
        before = get_db_stats()["total_scans"]
        update_db_stats("test-target", "TEST_TOOL")
        after = get_db_stats()["total_scans"]
        assert after >= before

    def test_log_scan_start_end(self, app):
        from core.db import log_scan_start, log_scan_end
        tid = f"test-{int(time.time())}"
        log_scan_start(tid, "TEST_TOOL", "test-target")
        log_scan_end(tid, "SUCCESS", "test output")


class TestC2Tables:
    def test_init_c2_tables(self):
        from core.db import init_c2_tables
        init_c2_tables()  # idempotent olmalı

    def test_log_c2_session(self):
        from core.db import log_c2_session
        log_c2_session("test-zombie", 4444, "192.168.1.1:12345", "Linux")