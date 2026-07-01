"""
Tests for core.task_manager — async task lifecycle management.
"""
import uuid


from core.task_manager import (
    ASYNC_TASKS,
    create_task,
    set_task_process,
    kill_task,
    kill_all_tasks,
)


class TestCreateTask:
    def test_returns_uuid_string(self):
        task_id = create_task('nmap', '10.0.0.1', 'scan')
        assert isinstance(task_id, str)
        uuid.UUID(task_id)  # raises ValueError if not a valid UUID

    def test_adds_entry_to_async_tasks(self):
        task_id = create_task('nmap', '10.0.0.1', 'scan')
        assert task_id in ASYNC_TASKS
        assert ASYNC_TASKS[task_id]['status'] == 'running'
        assert ASYNC_TASKS[task_id]['tool'] == 'nmap'
        assert ASYNC_TASKS[task_id]['target'] == '10.0.0.1'
        assert ASYNC_TASKS[task_id]['action'] == 'scan'
        assert ASYNC_TASKS[task_id]['process'] is None

    def test_unique_ids(self):
        id1 = create_task('a', 'b', 'c')
        id2 = create_task('a', 'b', 'c')
        assert id1 != id2


class TestSetTaskProcess:
    def test_sets_process_on_existing_task(self):
        task_id = create_task('nmap', 'target', 'scan')
        mock_proc = object()
        set_task_process(task_id, mock_proc)
        assert ASYNC_TASKS[task_id]['process'] is mock_proc

    def test_does_not_crash_on_unknown_task(self):
        set_task_process('nonexistent', object())  # should not raise


class TestKillTask:
    def test_not_found(self):
        ok, msg = kill_task('nonexistent-id')
        assert ok is False
        assert 'not found' in msg.lower()

    def test_kill_task_with_process(self, mock_psutil):
        task_id = create_task('nmap', '10.0.0.1', 'scan')
        mock_proc = object()
        set_task_process(task_id, mock_proc)
        task_before = ASYNC_TASKS[task_id]
        task_before['process'] = mock_psutil['instance']

        ok, killed = kill_task(task_id)
        assert ok is True
        assert killed >= 1
        assert ASYNC_TASKS[task_id]['status'] == 'error'
        assert 'ABORTED' in ASYNC_TASKS[task_id]['output']

    def test_kill_task_sets_message_when_no_output(self, mock_psutil):
        task_id = create_task('whois', 'example.com', 'scan')
        task = ASYNC_TASKS[task_id]
        task['process'] = mock_psutil['instance']

        ok, _ = kill_task(task_id)
        assert ok is True
        assert ASYNC_TASKS[task_id]['output'] == '[!] PROCESS ABORTED BY USER.'


class TestKillAllTasks:
    def test_kills_all_running_tasks(self, mock_psutil):
        tid1 = create_task('nmap', 'a', 'x')
        tid2 = create_task('whois', 'b', 'y')
        ASYNC_TASKS[tid1]['process'] = mock_psutil['instance']
        ASYNC_TASKS[tid2]['process'] = mock_psutil['instance']

        total = kill_all_tasks()
        assert total == 2
        assert ASYNC_TASKS[tid1]['status'] == 'error'
        assert ASYNC_TASKS[tid2]['status'] == 'error'

    def test_skips_already_finished_tasks(self, mock_psutil):
        tid1 = create_task('nmap', 'a', 'x')
        ASYNC_TASKS[tid1]['process'] = mock_psutil['instance']
        ASYNC_TASKS[tid1]['status'] = 'success'  # already done

        total = kill_all_tasks()
        assert total == 0  # no running tasks to kill
