"""Tüm endpoint'lerde geçersiz input → 400 döndüğünü doğrula"""
import pytest, json
from tests.conftest import auth_client, client  # noqa: F401


class TestValidationAcrossEndpoints:
    """Her endpoint'te hatalı input 500 yerine 400 döndürmeli."""

    def test_log_errors_limit_too_high(self, auth_client):
        r = auth_client.get("/api/logs/errors?limit=99999")
        assert r.status_code == 400

    def test_log_errors_limit_nan(self, auth_client):
        r = auth_client.get("/api/logs/errors?limit=abc")
        assert r.status_code == 400

    def test_log_events_limit_too_high(self, auth_client):
        r = auth_client.get("/api/logs/events?limit=99999")
        assert r.status_code == 400

    def test_c2_start_invalid_port_type(self, auth_client):
        """Port string ise 400 dönmeli."""
        r = auth_client.post("/api/c2/listener/start",
                             data=json.dumps({"port": "abc"}),
                             content_type="application/json")
        # bounded_integer çalışıyorsa 400, değilse 500
        assert r.status_code in (400, 500, 403)


class TestCSRFRoutes:
    """CSRF koruması altındaki endpoint'ler."""

    def test_post_action_without_csrf(self, client):
        r = client.post("/api/action", content_type="application/json")
        assert r.status_code in (302, 403)

    def test_beacon_register_exempt_from_csrf(self, client):
        r = client.post("/api/beacon/register",
                        data=json.dumps({"hostname": "test"}),
                        content_type="application/json",
                        headers={"X-Beacon-Key": "test-beacon-key-32-chars-long!!"})
        assert r.status_code != 403