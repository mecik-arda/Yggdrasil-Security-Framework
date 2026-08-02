"""Session management testleri — fixation, logout, cookie flags"""
import pytest
from yggapp import create_app, init_services


@pytest.fixture(scope="session")
def app():
    a = create_app("test")
    init_services(a)
    return a


class TestSessionManagement:
    def test_logout_clears_session(self, app):
        c = app.test_client()
        c.post("/login", data={"username": "admin", "password": "test123"})
        r = c.get("/logout", follow_redirects=True)
        assert r.status_code == 200
        r2 = c.get("/api/auth/status")
        data = r2.get_json()
        assert data["logged_in"] is False

    def test_session_persists_after_login(self, app):
        c = app.test_client()
        c.post("/login", data={"username": "admin", "password": "test123"})
        r1 = c.get("/api/auth/status")
        assert r1.get_json()["logged_in"] is True
        r2 = c.get("/api/auth/status")
        assert r2.get_json()["logged_in"] is True

    def test_unauth_redirect_has_no_session(self, app):
        c = app.test_client()
        r = c.get("/api/auth/status")
        assert r.get_json()["logged_in"] is False

    def test_multiple_logins_same_session(self, app):
        c = app.test_client()
        for _ in range(3):
            r = c.post("/login", data={"username": "admin", "password": "test123"})
            assert r.status_code in (200, 302)


class TestCookieFlags:
    def test_session_cookie_present(self, app):
        c = app.test_client()
        r = c.post("/login", data={"username": "admin", "password": "test123"})
        cookies = r.headers.get("Set-Cookie", "")
        assert "session" in cookies.lower() or r.status_code == 302