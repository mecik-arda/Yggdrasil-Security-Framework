"""
Shared pytest fixtures for Yggdrasil Security Framework tests.
"""
import sys
import types
import sqlite3 as real_sqlite3

import pytest


# ---------------------------------------------------------------------------
# Session-scoped: prevent heavy handler imports
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def _mock_handlers_module():
    """Mock the entire handlers package so core modules can be imported
    without pulling in 25+ handler modules, Flask, etc."""
    if 'handlers' not in sys.modules:
        pkg = types.ModuleType('handlers')
        pkg.__path__ = []  # make it look like a package

        def _dispatch_handler(handler_name, target, data):
            return f"[mocked dispatch] handler={handler_name} target={target}"

        pkg.dispatch_handler = _dispatch_handler
        sys.modules['handlers'] = pkg

    yield
    # keep mock in sys.modules for the entire session


# ---------------------------------------------------------------------------
# Database fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_db_path(tmp_path):
    """Return path to a temporary, isolated SQLite database."""
    return str(tmp_path / "test_stats.db")


@pytest.fixture(autouse=True)
def _mock_db_connect(mocker, temp_db_path):
    """
    Redirect all ``sqlite3.connect('stats.db')`` calls inside ``core.db``
    to the temporary database so tests never touch the real file.
    """
    original_connect = real_sqlite3.connect

    def _mocked_connect(database, *args, **kwargs):
        if database == 'stats.db' or (isinstance(database, str) and database.endswith('stats.db')):
            database = temp_db_path
        return original_connect(database, *args, **kwargs)

    mocker.patch('core.db.sqlite3.connect', side_effect=_mocked_connect)


# ---------------------------------------------------------------------------
# Platform / OS helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_platform_linux(mocker):
    """Make ``platform.system()`` return 'Linux'."""
    mocker.patch('platform.system', return_value='Linux')
    mocker.patch('core.tool_runner.platform.system', return_value='Linux')
    mocker.patch('core.system_manager.platform.system', return_value='Linux')


@pytest.fixture
def mock_platform_windows(mocker):
    """Make ``platform.system()`` return 'Windows'."""
    mocker.patch('platform.system', return_value='Windows')
    mocker.patch('core.tool_runner.platform.system', return_value='Windows')
    mocker.patch('core.system_manager.platform.system', return_value='Windows')


# ---------------------------------------------------------------------------
# Subprocess helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_subprocess(mocker):
    """Return a bundle of mocks for subprocess.Popen and check_output."""
    mock_popen = mocker.MagicMock()
    mock_process = mocker.MagicMock()
    mock_process.communicate.return_value = (b"mocked output", b"")
    mock_process.returncode = 0
    mock_popen.return_value = mock_process

    mock_check_output = mocker.MagicMock(return_value=b"mocked output")

    mocker.patch('subprocess.Popen', mock_popen)
    mocker.patch('subprocess.check_output', mock_check_output)
    mocker.patch('subprocess.check_call')

    return {
        'popen': mock_popen,
        'process': mock_process,
        'check_output': mock_check_output,
    }


# ---------------------------------------------------------------------------
# psutil helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_psutil(mocker):
    """Mock psutil.Process so task-manager tests never touch real processes."""
    mock_process_class = mocker.MagicMock()
    mock_process_instance = mocker.MagicMock()
    mock_process_instance.pid = 99999
    mock_process_instance.children.return_value = []
    mock_process_class.return_value = mock_process_instance

    mocker.patch('psutil.Process', mock_process_class)

    return {
        'Process': mock_process_class,
        'instance': mock_process_instance,
    }


# ---------------------------------------------------------------------------
# Task-manager state reset
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_task_manager():
    """Re-create the task-manager singleton so tests are isolated."""
    from core.task_manager import _TaskManager, _manager as old_mgr
    import core.task_manager as tm
    try:
        old_mgr._executor.shutdown(wait=False)
    except Exception:
        pass
    new_mgr = _TaskManager()
    tm._manager = new_mgr
    yield
    try:
        new_mgr._executor.shutdown(wait=False)
    except Exception:
        pass
    tm._manager = old_mgr
