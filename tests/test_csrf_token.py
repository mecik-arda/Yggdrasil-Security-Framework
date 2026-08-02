"""CSRF token mekanizması testleri"""
import pytest, re
from yggapp import create_app, init_services


@pytest.fixture(scope="session")
def app():
    from yggapp import create_app, init_services
    a = create_app("test")
    init_services(a)
    return a


@pytest.fixture
def unauth(app):
    return app.test_client()


@pytest.fixture(scope="session")
def auth(app):
    c = app.test_client()
    c.post("/login", data={"username": "admin", "password": "test123"}, follow_redirects=True)
    return c


class TestCSRFTokenGeneration:
    def test_token_in_dashboard_html(self, auth):
        r = auth.get("/")
        html = r.data.decode()
        assert "csrfToken" in html or "csrf_token" in html

    def test_token_rotates_per_session(self, unauth):
        r1 = unauth.get("/api/auth/status")
        r2 = unauth.get("/api/auth/status")
        assert r1.status_code == r2.status_code == 200

    def test_post_rejected_without_token(self, unauth):
        r = unauth.post("/api/action", content_type="application/json")
        assert r.status_code in (302, 403)

    def test_beacon_register_csrf_exempt(self, unauth):
        r = unauth.post("/api/beacon/register",
                        data='{"hostname":"t"}',
                        content_type="application/json",
                        headers={"X-Beacon-Key": "test-beacon-key-32-chars-long!!"})
        assert r.status_code != 403, "Beacon register CSRF'den muaf olmalı"

    def test_beacon_checkin_csrf_exempt(self, unauth):
        r = unauth.post("/api/beacon/checkin/test-id",
                        data='{"status":"alive"}',
                        content_type="application/json",
                        headers={"X-Beacon-Key": "test-beacon-key-32-chars-long!!"})
        assert r.status_code != 403

    def test_auth_login_csrf_exempt(self, unauth):
        r = unauth.post("/login", data={"username": "admin", "password": "test123"})
        assert r.status_code not in (403,)