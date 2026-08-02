"""routes/log_routes.py için testler — auth_client fixture ile"""
import pytest
from tests.conftest import auth_client, client, app  # noqa: F401


class TestLogErrorRoutes:
    def test_get_errors_default(self, auth_client):
        r = auth_client.get("/api/logs/errors")
        assert r.status_code == 200
        data = r.get_json()
        assert data["status"] == "success"

    def test_get_errors_with_limit(self, auth_client):
        r = auth_client.get("/api/logs/errors?limit=10")
        assert r.status_code == 200

    def test_limit_too_high_returns_400(self, auth_client):
        r = auth_client.get("/api/logs/errors?limit=99999")
        assert r.status_code == 400

    def test_limit_not_a_number_returns_400(self, auth_client):
        r = auth_client.get("/api/logs/errors?limit=abc")
        assert r.status_code == 400

    def test_limit_negative_returns_400(self, auth_client):
        r = auth_client.get("/api/logs/errors?limit=-1")
        assert r.status_code == 400

    def test_error_with_level_filter(self, auth_client):
        r = auth_client.get("/api/logs/errors?level=ERROR")
        assert r.status_code == 200

    def test_require_login(self, client):
        r = client.get("/api/logs/errors")
        assert r.status_code == 302


class TestLogEventRoutes:
    def test_get_events(self, auth_client):
        r = auth_client.get("/api/logs/events")
        assert r.status_code == 200

    def test_get_events_limit_400(self, auth_client):
        r = auth_client.get("/api/logs/events?limit=99999")
        assert r.status_code == 400


class TestLogStatsRoutes:
    def test_get_stats(self, auth_client):
        r = auth_client.get("/api/logs/stats")
        assert r.status_code == 200
        data = r.get_json()
        assert data["status"] == "success"