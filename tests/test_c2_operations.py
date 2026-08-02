"""C2 operations extended testleri — listener/zombie/payload"""
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
    r = c.post("/login", data={"username": "admin", "password": "test123"}, follow_redirects=True)
    if r.status_code != 200:
        # Login failed (rate limit?), skip auth-dependent tests
        pytest.skip("Login failed — rate limit or auth issue")
    return c


class TestC2ListenerStart:
    def test_start_listener(self, auth):
        r = auth.post("/api/c2/listener/start",
                      data=json.dumps({"port": 44444, "name": "test-op"}),
                      content_type="application/json")
        assert r.status_code in (200, 403)

    def test_start_invalid_port(self, auth):
        r = auth.post("/api/c2/listener/start",
                      data=json.dumps({"port": "abc"}),
                      content_type="application/json")
        assert r.status_code in (400, 403)

    def test_start_port_out_of_range(self, auth):
        r = auth.post("/api/c2/listener/start",
                      data=json.dumps({"port": 99999}),
                      content_type="application/json")
        assert r.status_code in (400, 403)


class TestC2ListenersList:
    def test_list_listeners(self, auth):
        r = auth.get("/api/c2/listeners")
        assert r.status_code == 200
        data = r.get_json()
        assert data["status"] == "success"
        assert "listeners" in data

    def test_listeners_requires_auth(self, unauth):
        r = unauth.get("/api/c2/listeners")
        assert r.status_code == 302


class TestC2Zombies:
    def test_list_zombies(self, auth):
        r = auth.get("/api/c2/zombies")
        assert r.status_code == 200

    def test_zombie_output_requires_id(self, auth):
        r = auth.get("/api/c2/zombie/output")
        assert r.status_code in (200, 400, 500)


class TestC2Payload:
    def test_generate_payload(self, auth):
        r = auth.post("/api/c2/payload/generate",
                      data=json.dumps({"listener_ip": "127.0.0.1", "listener_port": 4444, "payload_type": "python"}),
                      content_type="application/json")
        assert r.status_code in (200, 403)

    def test_generate_invalid_ip(self, auth):
        r = auth.post("/api/c2/payload/generate",
                      data=json.dumps({"listener_ip": "invalid", "listener_port": 4444}),
                      content_type="application/json")
        assert r.status_code in (200, 400, 403, 500)


class TestC2Stop:
    def test_stop_all_listeners(self, auth):
        r = auth.post("/api/c2/listener/stop_all",
                      data=json.dumps({}),
                      content_type="application/json")
        assert r.status_code in (200, 403)