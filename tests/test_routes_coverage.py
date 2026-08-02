"""Tüm route'ların varlığını ve auth gereksinimini kontrol eder"""
import pytest
from yggapp import create_app, init_services


@pytest.fixture(scope="session")
def app():
    a = create_app("test")
    init_services(a)
    return a


def _get_routes(app):
    return [(r.rule, r.methods) for r in app.url_map.iter_rules()]


class TestRouteCoverage:
    def test_core_routes_exist(self, app):
        rules = {r[0] for r in _get_routes(app)}
        required = [
            "/",
            "/settings",
            "/login",
            "/logout",
            "/api/auth/status",
            "/api/set_lang",
            "/api/stats",
            "/api/action",
            "/api/task_status",
            "/api/task_kill",
            "/api/task_kill_all",
        ]
        for path in required:
            assert path in rules, f"Route {path} not registered"

    def test_beacon_routes_exist(self, app):
        rules = {r[0] for r in _get_routes(app)}
        beacon_routes = [
            "/api/beacon/register",
            "/api/beacon/list",
            "/api/beacon/detail",
            "/api/beacon/remove",
            "/api/beacon/task",
            "/api/beacon/generate",
        ]
        for path in beacon_routes:
            assert path in rules, f"Beacon route {path} not registered"

    def test_c2_routes_exist(self, app):
        rules = {r[0] for r in _get_routes(app)}
        c2_routes = [
            "/api/c2/listeners",
            "/api/c2/listener/start",
            "/api/c2/listener/stop",
            "/api/c2/listener/stop_all",
            "/api/c2/zombies",
            "/api/c2/zombie/output",
            "/api/c2/zombie/command",
            "/api/c2/zombie/disconnect",
            "/api/c2/payload/generate",
        ]
        for path in c2_routes:
            assert path in rules, f"C2 route {path} not registered"

    def test_msf_routes_exist(self, app):
        rules = {r[0] for r in _get_routes(app)}
        msf_routes = [
            "/api/msf/status",
            "/api/msf/payloads",
            "/api/msf/payload/generate",
        ]
        for path in msf_routes:
            assert path in rules, f"MSF route {path} not registered"

    def test_log_routes_exist(self, app):
        rules = {r[0] for r in _get_routes(app)}
        log_routes = [
            "/api/logs/errors",
            "/api/logs/events",
            "/api/logs/stats",
            "/api/logs/clear",
        ]
        for path in log_routes:
            assert path in rules, f"Log route {path} not registered"

    def test_graph_routes_exist(self, app):
        rules = {r[0] for r in _get_routes(app)}
        graph_routes = ["/api/graph/data", "/api/graph/node/add"]
        for path in graph_routes:
            assert path in rules, f"Graph route {path} not registered"

    def test_evasion_routes_exist(self, app):
        rules = {r[0] for r in _get_routes(app)}
        evasion_routes = ["/api/evasion/craft"]
        for path in evasion_routes:
            assert path in rules, f"Evasion route {path} not registered"


class TestAuthRequirements:
    def test_dashboard_requires_login(self, app):
        c = app.test_client()
        r = c.get("/")
        assert r.status_code == 302

    def test_settings_requires_login(self, app):
        c = app.test_client()
        r = c.get("/settings")
        assert r.status_code == 302

    def test_api_action_requires_csrf(self, app):
        c = app.test_client()
        r = c.post("/api/action", content_type="application/json")
        assert r.status_code in (302, 403)

    def test_c2_listeners_requires_login(self, app):
        c = app.test_client()
        r = c.get("/api/c2/listeners")
        assert r.status_code == 302

    def test_beacon_list_requires_login(self, app):
        c = app.test_client()
        r = c.get("/api/beacon/list")
        assert r.status_code == 302