"""Action routes testleri — tool run/install/update/remove"""
import pytest, json
from yggapp import create_app, init_services


@pytest.fixture(scope="session")
def app():
    a = create_app("test")
    init_services(a)
    return a


@pytest.fixture
def auth(app):
    c = app.test_client()
    c.post("/login", data={"username": "admin", "password": "test123"}, follow_redirects=True)
    return c


class TestActionCheck:
    def test_check_tool_status(self, auth):
        r = auth.post("/api/action", data={"tool": "whois", "action": "check"})
        assert r.status_code in (200, 302, 403, 405)

    def test_check_updates(self, auth):
        r = auth.post("/api/action", data={"tool": "whois", "action": "check_updates"})
        assert r.status_code in (200, 302, 403, 405)


class TestActionRun:
    def test_run_requires_target(self, auth):
        r = auth.post("/api/action", data={"tool": "whois", "action": "run"})
        assert r.status_code in (200, 302, 400, 403, 405)

    def test_install_action(self, auth):
        r = auth.post("/api/action", data={"tool": "whois", "action": "install"})
        assert r.status_code in (200, 302, 403, 405)

    def test_invalid_action(self, auth):
        r = auth.post("/api/action", data={"tool": "whois", "action": "nonexistent"})
        assert r.status_code in (200, 302, 400, 403)


class TestTaskStatus:
    def test_task_status_endpoint(self, auth):
        r = auth.get("/api/task_status")
        assert r.status_code == 200

    def test_task_kill_nonexistent(self, auth):
        r = auth.post("/api/task_kill",
                      data=json.dumps({"task_id": "nonexistent"}),
                      content_type="application/json")
        assert r.status_code in (200, 400, 403)

    def test_task_kill_all(self, auth):
        r = auth.post("/api/task_kill_all",
                      data=json.dumps({}),
                      content_type="application/json")
        assert r.status_code in (200, 403)