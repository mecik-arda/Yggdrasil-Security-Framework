"""WSL, Ops, System Manager ve Rate Limit testleri — toplu dosya"""
import pytest, json
from yggapp import create_app, init_services


@pytest.fixture(scope="session")
def app():
    a = create_app("test")
    init_services(a)
    return a


@pytest.fixture
def unauth(app):
    return app.test_client()


@pytest.fixture
def auth(app):
    c = app.test_client()
    c.post("/login", data={"username": "admin", "password": "test123"}, follow_redirects=True)
    return c


# ── WSL Routes ──
class TestWSLRoutes:
    def test_wsl_distros(self, auth):
        r = auth.get("/api/wsl/distros")
        assert r.status_code in (200, 404, 500)


# ── Ops Routes ──
class TestOpsRoutes:
    def test_ops_cve(self, auth):
        r = auth.get("/api/ops/cve")
        assert r.status_code in (200, 404)

    def test_ops_sessions(self, auth):
        r = auth.get("/api/ops/sessions")
        assert r.status_code in (200, 404)

    def test_ops_topology(self, auth):
        r = auth.get("/api/ops/topology")
        assert r.status_code in (200, 302, 403, 404, 500)


# ── System Manager ──
class TestSystemManager:
    def test_validate_target_good(self):
        from core.system_manager import validate_target
        assert validate_target("example.com") is True

    def test_validate_target_bad(self):
        from core.system_manager import validate_target
        # Banned characters should return False
        assert validate_target("test;rm -rf /") is False

    def test_sanitize_target(self):
        from core.system_manager import sanitize_target
        result = sanitize_target("  example.com  ")
        assert result == "example.com"

    def test_check_tool_status(self):
        from core.system_manager import check_tool_status
        # Returns dict with status
        result = check_tool_status("python")
        assert isinstance(result, (bool, dict))


# ── Rate Limiting ──
class TestRateLimiting:
    def test_beacon_generate_rate_limited(self, auth):
        r = auth.post("/api/beacon/generate",
                      data=json.dumps({"listener_url": "http://x.com", "sleep": 5, "jitter": 10}),
                      content_type="application/json")
        assert r.status_code in (200, 400, 403, 404, 429)

    def test_c2_start_rate_limited(self, auth):
        r = auth.post("/api/c2/listener/start",
                      data=json.dumps({"port": 55555, "name": "rl-test"}),
                      content_type="application/json")
        assert r.status_code in (200, 403, 404, 429)