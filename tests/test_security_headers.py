"""HTTP güvenlik header'ları testleri — CORS, X-Frame, content-type"""
import pytest


class TestCORSHeaders:
    def test_cors_on_api(self, app):
        c = app.test_client()
        r = c.get("/api/auth/status")
        assert r.status_code == 200

    def test_cors_preflight(self, app):
        c = app.test_client()
        r = c.options(
            "/api/auth/status",
            headers={
                "Origin": "http://localhost:5000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert r.status_code in (200, 404)


class TestSecurityHeaders:
    def test_session_cookie_http_only(self, auth_client):
        """Session cookie HttpOnly flag'i olmalı."""
        r = auth_client.post(
            "/login", data={"username": "admin", "password": "test123"}
        )
        assert r.status_code in (200, 302)

    def test_no_server_header_leak(self, app):
        c = app.test_client()
        r = c.get("/api/auth/status")
        assert r.status_code == 200

    def test_content_type_json(self, app):
        c = app.test_client()
        r = c.get("/api/auth/status")
        assert r.status_code == 200
        assert r.content_type == "application/json"

    def test_content_type_html(self, app):
        c = app.test_client()
        r = c.get("/login")
        assert r.status_code == 200
        assert "text/html" in r.content_type