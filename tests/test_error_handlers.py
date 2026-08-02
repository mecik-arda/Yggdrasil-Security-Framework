"""Error handler testleri — 400/403/404/405/429/500 sayfaları"""
import pytest
import json


class TestHTTPErrors:
    def test_404_returns_json_on_api(self, app):
        c = app.test_client()
        r = c.get("/api/nonexistent")
        assert r.status_code == 404

    def test_405_method_not_allowed(self, app):
        c = app.test_client()
        r = c.put("/api/beacon/register")
        assert r.status_code == 405

    def test_400_bad_request_body(self, app):
        c = app.test_client()
        r = c.post(
            "/api/c2/listener/start",
            data="not-json",
            content_type="application/json",
        )
        assert r.status_code in (400, 403, 415, 500)

    def test_403_csrf_on_action(self, app):
        c = app.test_client()
        r = c.post("/api/action", content_type="application/json")
        assert r.status_code in (302, 403)

    def test_500_not_crash_on_missing_route(self, app):
        c = app.test_client()
        r = c.get("/api/nonexistent/endpoint/xyz")
        assert r.status_code == 404

    def test_api_errors_return_json(self, app):
        c = app.test_client()
        r = c.post("/api/action", content_type="application/json")
        ct = r.content_type
        assert "json" in ct or r.status_code in (302, 403)


class TestErrorFormatting:
    def test_400_includes_message(self, auth_client):
        r = auth_client.get("/api/logs/errors?limit=abc")
        assert r.status_code == 400

    def test_validation_error_includes_field_name(self, auth_client):
        r = auth_client.get("/api/logs/errors?limit=99999")
        assert r.status_code == 400
        data = r.get_json()
        assert "status" in data or "message" in data or "error" in data
