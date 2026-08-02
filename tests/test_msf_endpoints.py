"""MSF endpoint testleri"""
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


class TestMSFStatus:
    def test_status(self, auth):
        r = auth.get("/api/msf/status")
        assert r.status_code == 200

    def test_payloads_list(self, auth):
        r = auth.get("/api/msf/payloads")
        assert r.status_code == 200

    def test_payload_generate_valid(self, auth):
        r = auth.post("/api/msf/payload/generate",
                      data=json.dumps({"lhost": "127.0.0.1", "lport": 4444, "platform": "linux"}),
                      content_type="application/json")
        assert r.status_code in (200, 403, 500)

    def test_payload_generate_invalid_port(self, auth):
        r = auth.post("/api/msf/payload/generate",
                      data=json.dumps({"lhost": "127.0.0.1", "lport": "abc"}),
                      content_type="application/json")
        assert r.status_code in (400, 403)
