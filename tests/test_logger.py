"""
Tests for Centralized Logging Module — log initialization,
SQLite log handler, SocketIO log handler, rotating file handler,
log query helpers, stats, and cleanup.

Covers ``core/logger.py``.
"""

import os
import logging
import sqlite3 as real_sqlite3
import pytest
from unittest.mock import patch, MagicMock, PropertyMock


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_logger_state():
    """Reset logger module state before each test."""
    import core.logger as log_mod
    log_mod._root_logger_initialized = False
    log_mod._socketio_ref = None
    # Remove our handlers from the root logger
    root = logging.getLogger('yggdrasil')
    root.handlers.clear()
    root.propagate = True
    yield
    root.handlers.clear()
    root.propagate = True


# ---------------------------------------------------------------------------
# init_logging
# ---------------------------------------------------------------------------

class TestInitLogging:
    def test_init_logging_creates_handlers(self, tmp_path):
        """After init_logging, the yggdrasil logger should have handlers."""
        from core.logger import init_logging
        log_dir = tmp_path / 'logs'
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / 'yggdrasil.log'

        with patch('core.logger.LOG_DIR', str(log_dir)):
            with patch('core.logger.LOG_FILE', str(log_file)):
                init_logging()

        root = logging.getLogger('yggdrasil')
        assert len(root.handlers) >= 1  # At least the file handler

    def test_init_logging_idempotent(self, tmp_path):
        """Calling init_logging twice should not duplicate handlers."""
        from core.logger import init_logging
        log_dir = tmp_path / 'logs'
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / 'yggdrasil.log'

        with patch('core.logger.LOG_DIR', str(log_dir)):
            with patch('core.logger.LOG_FILE', str(log_file)):
                init_logging()
                handler_count = len(logging.getLogger('yggdrasil').handlers)
                init_logging()
                assert len(logging.getLogger('yggdrasil').handlers) == handler_count

    def test_init_logging_creates_log_directory(self, tmp_path):
        """Should create logs directory if it doesn't exist."""
        from core.logger import init_logging
        log_dir = tmp_path / 'new_logs'
        log_file = log_dir / 'yggdrasil.log'

        with patch('core.logger.LOG_DIR', str(log_dir)):
            with patch('core.logger.LOG_FILE', str(log_file)):
                init_logging()
        assert os.path.isdir(str(log_dir))


# ---------------------------------------------------------------------------
# get_logger
# ---------------------------------------------------------------------------

class TestGetLogger:
    def test_get_logger_returns_logger(self):
        """get_logger should return a logging.Logger instance."""
        from core.logger import get_logger
        log = get_logger('test_module')
        assert isinstance(log, logging.Logger)

    def test_get_logger_prepends_namespace(self):
        """Logger name should be prefixed with 'yggdrasil.'."""
        from core.logger import get_logger
        log = get_logger('my_tool')
        assert log.name == 'yggdrasil.my_tool'

    def test_get_logger_already_prefixed(self):
        """If name already has the prefix, should not double it."""
        from core.logger import get_logger
        log = get_logger('yggdrasil.already.prefixed')
        assert log.name == 'yggdrasil.already.prefixed'


# ---------------------------------------------------------------------------
# emit_log_event
# ---------------------------------------------------------------------------

class TestEmitLogEvent:
    def test_emit_log_event_writes_to_db(self, temp_db_path):
        """emit_log_event should insert into system_events table."""
        from core.logger import emit_log_event, _ensure_log_tables
        _ensure_log_tables()

        emit_log_event('test_event', 'Test message from unit test', source='pytest')

        conn = real_sqlite3.connect(temp_db_path)
        c = conn.cursor()
        c.execute('SELECT event_type, source, message FROM system_events')
        row = c.fetchone()
        conn.close()
        assert row is not None
        assert row[0] == 'test_event'
        assert row[1] == 'pytest'
        assert 'Test message' in row[2]

    def test_emit_log_event_with_extra_data(self, temp_db_path):
        """Extra data should be stored as JSON."""
        from core.logger import emit_log_event, _ensure_log_tables
        _ensure_log_tables()

        emit_log_event('data_event', 'Message with data', source='test',
                       extra_data={'key': 'value', 'count': 42})

        conn = real_sqlite3.connect(temp_db_path)
        c = conn.cursor()
        c.execute('SELECT extra_data FROM system_events WHERE event_type=?', ('data_event',))
        row = c.fetchone()
        conn.close()
        assert row is not None
        assert 'key' in row[0]
        assert 'value' in row[0]


# ---------------------------------------------------------------------------
# get_recent_errors / get_recent_events
# ---------------------------------------------------------------------------

class TestQueryLogs:
    def test_get_recent_errors_empty(self):
        """Empty table should return empty list."""
        from core.logger import get_recent_errors, _ensure_log_tables
        _ensure_log_tables()
        result = get_recent_errors()
        assert isinstance(result, list)

    def test_get_recent_events_empty(self):
        """Empty events table should return empty list."""
        from core.logger import get_recent_events, _ensure_log_tables
        _ensure_log_tables()
        result = get_recent_events()
        assert isinstance(result, list)

    def test_get_recent_errors_with_limit(self):
        """Should respect the limit parameter."""
        from core.logger import get_recent_errors, _ensure_log_tables
        _ensure_log_tables()
        result = get_recent_errors(limit=5)
        assert len(result) <= 5

    def test_get_recent_errors_filter_by_level(self, temp_db_path):
        """Should filter by log level."""
        from core.logger import get_recent_errors, emit_log_event, _ensure_log_tables
        _ensure_log_tables()

        # Insert some test data directly
        conn = real_sqlite3.connect(temp_db_path)
        c = conn.cursor()
        c.execute(
            "INSERT INTO error_logs (level, module, message) VALUES (?, ?, ?)",
            ('ERROR', 'test_mod', 'Test error message')
        )
        c.execute(
            "INSERT INTO error_logs (level, module, message) VALUES (?, ?, ?)",
            ('WARNING', 'test_mod', 'Test warning message')
        )
        conn.commit()
        conn.close()

        errors = get_recent_errors(level='ERROR')
        for err in errors:
            assert err['level'] == 'ERROR'

    def test_get_recent_events_filter_by_type(self, temp_db_path):
        """Should filter by event type."""
        from core.logger import get_recent_events, _ensure_log_tables
        _ensure_log_tables()

        # Insert test events
        conn = real_sqlite3.connect(temp_db_path)
        c = conn.cursor()
        c.execute(
            "INSERT INTO system_events (event_type, source, message) VALUES (?, ?, ?)",
            ('scan_start', 'nmap', 'Started scan')
        )
        c.execute(
            "INSERT INTO system_events (event_type, source, message) VALUES (?, ?, ?)",
            ('scan_end', 'nmap', 'Ended scan')
        )
        conn.commit()
        conn.close()

        events = get_recent_events(event_type='scan_start')
        for evt in events:
            assert evt['event_type'] == 'scan_start'


# ---------------------------------------------------------------------------
# get_log_stats
# ---------------------------------------------------------------------------

class TestGetLogStats:
    def test_get_log_stats_returns_dict(self):
        """get_log_stats should return summary stats as dict."""
        from core.logger import get_log_stats, _ensure_log_tables
        _ensure_log_tables()
        stats = get_log_stats()
        assert isinstance(stats, dict)
        assert 'errors_today' in stats
        assert 'warnings_today' in stats
        assert 'total_errors' in stats
        assert 'total_events' in stats

    def test_get_log_stats_values_are_integers(self):
        """All count values should be integers."""
        from core.logger import get_log_stats, _ensure_log_tables
        _ensure_log_tables()
        stats = get_log_stats()
        for key in ['errors_today', 'warnings_today', 'total_errors', 'total_events']:
            assert isinstance(stats[key], int)


# ---------------------------------------------------------------------------
# clear_all_logs
# ---------------------------------------------------------------------------

class TestClearAllLogs:
    def test_clear_all_logs(self, temp_db_path):
        """clear_all_logs should delete all log entries."""
        from core.logger import clear_all_logs, emit_log_event, _ensure_log_tables
        _ensure_log_tables()

        emit_log_event('event1', 'Message 1')
        emit_log_event('event2', 'Message 2')

        clear_all_logs()

        conn = real_sqlite3.connect(temp_db_path)
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM system_events')
        count = c.fetchone()[0]
        c.execute('SELECT COUNT(*) FROM error_logs')
        err_count = c.fetchone()[0]
        conn.close()
        assert count == 0
        assert err_count == 0


# ---------------------------------------------------------------------------
# set_socketio_instance
# ---------------------------------------------------------------------------

class TestSocketIOIntegration:
    def test_set_socketio_instance_stores_weakref(self):
        """set_socketio_instance should store a weak reference."""
        import core.logger as log_mod
        mock_sio = MagicMock()
        log_mod.set_socketio_instance(mock_sio)
        # Should not crash — stored reference via global
        assert log_mod._socketio_ref is not None

    def test_set_socketio_instance_none(self):
        """Passing None should clear the reference."""
        import core.logger as log_mod
        log_mod.set_socketio_instance(None)
        assert log_mod._socketio_ref is None

    def test_socketio_handler_emit_does_not_crash_when_no_socketio(self, tmp_path):
        """SocketIOLogHandler.emit should not crash when no SocketIO is set."""
        from core.logger import SocketIOLogHandler, set_socketio_instance
        set_socketio_instance(None)

        handler = SocketIOLogHandler()
        record = logging.LogRecord(
            name='test', level=logging.WARNING, pathname='', lineno=0,
            msg='Test log message', args=(), exc_info=None
        )
        # Should not raise
        handler.emit(record)


# ---------------------------------------------------------------------------
# SQLiteLogHandler
# ---------------------------------------------------------------------------

class TestSQLiteLogHandler:
    def test_sqlite_handler_writes_to_db(self, temp_db_path):
        """SQLiteLogHandler.emit should write to error_logs table."""
        from core.logger import SQLiteLogHandler, _ensure_log_tables
        _ensure_log_tables()

        with patch('core.logger._ensure_log_tables'):
            handler = SQLiteLogHandler(db_path=temp_db_path)
            handler.setFormatter(logging.Formatter('%(message)s'))

            record = logging.LogRecord(
                name='yggdrasil.test', level=logging.ERROR,
                pathname='test.py', lineno=42, msg='Test error',
                args=(), exc_info=None
            )
            record.tool = 'nmap'
            record.target = '10.0.0.1'

            handler.emit(record)

            conn = real_sqlite3.connect(temp_db_path)
            c = conn.cursor()
            c.execute(
                'SELECT level, module, tool, target, message FROM error_logs'
            )
            row = c.fetchone()
            conn.close()
            assert row is not None
            assert row[0] == 'ERROR'
            assert row[1] == 'yggdrasil.test'
            assert row[2] == 'nmap'
            assert row[3] == '10.0.0.1'
            assert 'Test error' in row[4]

    def test_sqlite_handler_with_exception(self):
        """Records with exception info should be handled gracefully."""
        from core.logger import SQLiteLogHandler, _ensure_log_tables
        _ensure_log_tables()
        import sys

        handler = SQLiteLogHandler()
        handler.setFormatter(logging.Formatter('%(message)s'))

        try:
            raise ValueError('deliberate test exception')
        except ValueError:
            record = logging.LogRecord(
                name='test', level=logging.ERROR, pathname='', lineno=0,
                msg='Error with exception', args=(), exc_info=sys.exc_info()
            )

        with patch('core.logger._ensure_log_tables'):
            with patch('core.logger._prune_old_logs_conn'):
                handler.emit(record)
        # If we got here without exception, the handler handled it correctly


# ---------------------------------------------------------------------------
# Log pruning
# ---------------------------------------------------------------------------

class TestLogPruning:
    def test_prune_does_not_crash(self):
        """_prune_old_logs should not crash even on empty DB."""
        from core.logger import _prune_old_logs
        _prune_old_logs('stats.db')


# ---------------------------------------------------------------------------
# RotatingFileHandler — log rotation
# ---------------------------------------------------------------------------

class TestRotatingFileHandler:
    def test_file_handler_configured_in_init(self, tmp_path):
        """init_logging should add a RotatingFileHandler."""
        from core.logger import init_logging
        log_dir = tmp_path / 'logs'
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / 'yggdrasil.log'

        with patch('core.logger.LOG_DIR', str(log_dir)):
            with patch('core.logger.LOG_FILE', str(log_file)):
                init_logging()

        root = logging.getLogger('yggdrasil')
        file_handlers = [
            h for h in root.handlers
            if isinstance(h, logging.handlers.RotatingFileHandler)
        ]
        assert len(file_handlers) >= 1

    def test_file_handler_max_bytes_and_backup_count(self, tmp_path):
        """RotatingFileHandler should be 5MB with 3 backups."""
        from core.logger import init_logging
        log_dir = tmp_path / 'logs'
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / 'yggdrasil.log'

        with patch('core.logger.LOG_DIR', str(log_dir)):
            with patch('core.logger.LOG_FILE', str(log_file)):
                init_logging()

        root = logging.getLogger('yggdrasil')
        for h in root.handlers:
            if isinstance(h, logging.handlers.RotatingFileHandler):
                assert h.maxBytes == 5 * 1024 * 1024
                assert h.backupCount == 3
