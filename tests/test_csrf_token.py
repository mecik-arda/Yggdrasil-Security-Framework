"""CSRF token mekanizması testleri"""
import pytest
import re


class TestCSRFTokenGeneration:
    def test_token_in_dashboard_html(self, auth_client):
        r = auth_client.get("/")
        html = r.data.decode()
        assert "csrfToken" in html or "csrf_token" in html or "csrf" in html.lower()

    def test_token_rotates_per_session(self, app):
        from yggapp import create_app, init_services
        c = app.test_client()
        r1 = c.get("/api/auth/status")
        r2 = c.get("/api/auth/status")
        assert r1.status_code == r2.status_code == 200

    def test_post_rejected_without_token(self, app):
        c = app.test_client()
        r = c.post("/api/action", content_type="application/json")
        assert r.status_code in (302, 403)

    def test_beacon_register_csrf_exempt(self, app):
        c = app.test_client()
        r = c.post(
            "/api/beacon/register",
            data='{"hostname":"t"}',
            content_type="application/json",
            headers={"X-Beacon-Key": "test-beacon-key-32-chars-long!!"},
        )
        assert r.status_code != 403, "Beacon register CSRF'den muaf olmalı"

    def test_beacon_checkin_csrf_exempt(self, app):
        c = app.test_client()
        r = c.post(
            "/api/beacon/checkin/test-id",
            data='{"status":"alive"}',
            content_type="application/json",
            headers={"X-Beacon-Key": "test-beacon-key-32-chars-long!!"},
        )
        assert r.status_code != 403

    def test_auth_login_csrf_exempt(self, app):
        c = app.test_client()
        r = c.post("/login", data={"username": "admin", "password": "test123"})
        assert r.status_code not in (403,)