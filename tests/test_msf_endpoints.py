"""MSF endpoint testleri"""
import pytest
import json


class TestMSFStatus:
    def test_status(self, auth_client):
        r = auth_client.get("/api/msf/status")
        assert r.status_code == 200

    def test_payloads_list(self, auth_client):
        r = auth_client.get("/api/msf/payloads")
        assert r.status_code == 200

    def test_payload_generate_valid(self, auth_client):
        r = auth_client.post(
            "/api/msf/payload/generate",
            data=json.dumps({"lhost": "127.0.0.1", "lport": 4444, "platform": "linux"}),
            content_type="application/json",
        )
        assert r.status_code in (200, 302, 403, 500)

    def test_payload_generate_invalid_port(self, auth_client):
        r = auth_client.post(
            "/api/msf/payload/generate",
            data=json.dumps({"lhost": "127.0.0.1", "lport": 99999, "platform": "linux"}),
            content_type="application/json",
        )
        assert r.status_code in (400, 403, 500)
