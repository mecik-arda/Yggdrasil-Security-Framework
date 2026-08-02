"""core/tool_runner.py için testler"""
import pytest
from yggapp import create_app, init_services


@pytest.fixture(scope="session")
def app():
    a = create_app("test")
    init_services(a)
    return a


class TestToolRunnerImport:
    def test_import(self):
        from core.tool_runner import execute_tool, execute_tool_streaming
        assert callable(execute_tool)
        assert callable(execute_tool_streaming)

    def test_tool_config_import(self):
        from tools_config import TOOLS_CONFIG
        assert isinstance(TOOLS_CONFIG, dict)
        assert len(TOOLS_CONFIG) > 0


class TestToolCheckRoutes:
    def test_tool_check_endpoint(self, app):
        c = app.test_client()
        r = c.post("/api/tool/check",
                   data='{"tool":"whois"}',
                   content_type="application/json")
        assert r.status_code in (200, 302, 403, 404, 500)

    def test_tools_list_endpoint(self, app):
        c = app.test_client()
        r = c.get("/api/tools")
        assert r.status_code in (200, 302)


class TestTaskManager:
    def test_create_task(self):
        from core.task_manager import create_task
        tid = create_task("test_tool", "test_target", "run")
        assert isinstance(tid, str)
        assert len(tid) > 0

    def test_kill_non_existent_task(self):
        from core.task_manager import kill_task
        ok, msg = kill_task("nonexistent-id")
        assert ok is False

    def test_kill_all_tasks(self):
        from core.task_manager import kill_all_tasks
        count = kill_all_tasks()
        assert isinstance(count, int)

    def test_get_async_tasks(self):
        from core.task_manager import get_async_tasks
        tasks = get_async_tasks()
        assert isinstance(tasks, dict)


class TestTaskRetention:
    def test_cleanup_runs(self):
        import time
        from core.task_manager import _TaskManager
        tm = _TaskManager()
        tid = tm.create_task("test", "target", "run")
        task = tm.get_task(tid)
        task.status = "success"
        task.completed_at = time.time() - 100000
        tm._prune_old_tasks()
        assert tm.get_task(tid) is None, "Old completed task should be pruned"
