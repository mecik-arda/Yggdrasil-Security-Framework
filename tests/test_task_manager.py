"""
Tests for core.task_manager — ThreadPoolExecutor-based async task management.
"""
import uuid

import pytest

from core.task_manager import (
    create_task,
    set_task_process,
    kill_task,
    kill_all_tasks,
    get_async_tasks,
    get_task_manager,
)


# ---------------------------------------------------------------------------
# Helpers: reset the singleton between tests
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_task_manager():
    """Re-create the internal singleton so tests are isolated."""
    from core.task_manager import _TaskManager, _manager
    # Save old executor reference to shut it down later (best-effort)
    old = _manager
    try:
        old._executor.shutdown(wait=False)
    except Exception:
        pass
    # Replace module-level singleton
    import core.task_manager as tm
    new_mgr = _TaskManager()
    tm._manager = new_mgr
    yield
    try:
        new_mgr._executor.shutdown(wait=False)
    except Exception:
        pass
    tm._manager = old


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCreateTask:
    def test_returns_uuid_string(self):
        task_id = create_task('nmap', '10.0.0.1', 'scan')
        assert isinstance(task_id, str)
        uuid.UUID(task_id)

    def test_task_appears_in_all_dicts(self):
        task_id = create_task('nmap', '10.0.0.1', 'scan')
        tasks = get_async_tasks()
        assert task_id in tasks
        assert tasks[task_id]['tool'] == 'nmap'
        assert tasks[task_id]['target'] == '10.0.0.1'

    def test_unique_ids(self):
        id1 = create_task('a', 'b', 'c')
        id2 = create_task('a', 'b', 'c')
        assert id1 != id2

    def test_initial_status_is_pending(self):
        task_id = create_task('whois', 'x', 'y')
        mgr = get_task_manager()
        task = mgr.get_task(task_id)
        assert task.status == 'pending'


class TestSetTaskProcess:
    def test_sets_process_on_existing_task(self):
        task_id = create_task('nmap', 'target', 'scan')
        mock_proc = object()
        set_task_process(task_id, mock_proc)
        mgr = get_task_manager()
        assert mgr.get_task(task_id).process is mock_proc

    def test_does_not_crash_on_unknown_task(self):
        set_task_process('nonexistent', object())


class TestSubmitAndExecute:
    def test_submit_runs_task(self):
        """Verify a submitted function executes and updates task state."""
        results = []

        def _work():
            results.append('done')

        task_id = create_task('test', 'x', 'run')
        mgr = get_task_manager()
        mgr.submit(task_id, _work)
        # Wait for the task to finish (pool is synchronous enough for this)
        import time
        deadline = time.time() + 5
        while time.time() < deadline:
            task = mgr.get_task(task_id)
            if task and task.status in ('success', 'error'):
                break
            time.sleep(0.05)
        assert results == ['done']


class TestKillTask:
    def test_not_found(self):
        ok, msg = kill_task('nonexistent-id')
        assert ok is False
        assert 'not found' in msg.lower()

    def test_kill_task_with_process(self, mock_psutil):
        task_id = create_task('nmap', '10.0.0.1', 'scan')
        set_task_process(task_id, mock_psutil['instance'])
        ok, killed = kill_task(task_id)
        assert ok is True
        assert killed >= 1
        task = get_task_manager().get_task(task_id)
        assert task.status == 'error'
        assert 'ABORTED' in task.output

    def test_kill_task_sets_message_when_no_output(self, mock_psutil):
        task_id = create_task('whois', 'example.com', 'scan')
        set_task_process(task_id, mock_psutil['instance'])
        ok, _ = kill_task(task_id)
        assert ok is True
        task = get_task_manager().get_task(task_id)
        assert task.output == '[!] PROCESS ABORTED BY USER.'


class TestKillAllTasks:
    def test_kills_all_running_tasks(self, mock_psutil):
        tid1 = create_task('nmap', 'a', 'x')
        tid2 = create_task('whois', 'b', 'y')
        set_task_process(tid1, mock_psutil['instance'])
        set_task_process(tid2, mock_psutil['instance'])
        total = kill_all_tasks()
        assert total == 2
        mgr = get_task_manager()
        assert mgr.get_task(tid1).status == 'error'
        assert mgr.get_task(tid2).status == 'error'

    def test_skips_finished_tasks(self, mock_psutil):
        tid1 = create_task('nmap', 'a', 'x')
        set_task_process(tid1, mock_psutil['instance'])
        # Mark as success (simulating completion)
        get_task_manager().get_task(tid1).status = 'success'
        total = kill_all_tasks()
        assert total == 0


class TestGetStats:
    def test_initial_stats(self):
        mgr = get_task_manager()
        stats = mgr.get_stats()
        assert stats['active'] == 0
        assert stats['queued'] == 0
        assert stats['max_workers'] == 5

    def test_active_after_submit(self):
        mgr = get_task_manager()
        import time
        started = []
        def _slow():
            started.append(1)
            time.sleep(0.5)
        task_id = create_task('test', 'x', 'run')
        mgr.submit(task_id, _slow)
        time.sleep(0.05)
        stats = mgr.get_stats()
        assert stats['active'] >= 1
