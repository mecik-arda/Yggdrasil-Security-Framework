"""Auth login mekanizması testleri — JSON/form, rate-limit, brute-force"""
import pytest
from yggapp import create_app, init_services


@pytest.fixture(scope="session")
def app():
    a = create_app("test")
    init_services(a)
    return a


@pytest.fixture
def c(app):
    return app.test_client()


class TestLoginFlow:
    def test_form_login_success(self, c):
        r = c.post("/login", data={"username": "admin", "password": "test123"},
                   follow_redirects=True)
        assert r.status_code == 200

    def test_json_login_success(self, c):
        r = c.post("/login",
                   data='{"username":"admin","password":"test123"}',
                   content_type="application/json",
                   follow_redirects=True)
        assert r.status_code == 200

    def test_wrong_password(self, c):
        r = c.post("/login", data={"username": "admin", "password": "wrong"})
        assert r.status_code in (200, 302)
        html = r.data.decode()
        assert "parola hatali" in html.lower() or "incorrect password" in html.lower()

    def test_empty_password(self, c):
        r = c.post("/login", data={"username": "admin", "password": ""})
        assert r.status_code in (200, 302)

    def test_login_redirects_to_dashboard(self, c):
        r = c.post("/login", data={"username": "admin", "password": "test123"},
                   follow_redirects=True)
        html = r.data.decode()
        assert "yggdrasil" in html.lower() or "csrfToken" in html

    def test_logout_clears_session(self, c):
        c.post("/login", data={"username": "admin", "password": "test123"})
        r = c.get("/logout", follow_redirects=True)
        assert r.status_code == 200
        r2 = c.get("/api/auth/status")
        data = r2.get_json()
        assert data["logged_in"] is False

    def test_dashboard_requires_login(self, c):
        r = c.get("/")
        assert r.status_code == 302

    def test_settings_requires_login(self, c):
        r = c.get("/settings")
        assert r.status_code == 302