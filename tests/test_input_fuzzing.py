"""Input fuzzing testleri — SQL injection, XSS, null byte, uzun input"""
import pytest, json
from yggapp import create_app, init_services


@pytest.fixture(scope="session")
def app():
    a = create_app("test")
    init_services(a)
    return a


@pytest.fixture
def c(app):
    return app.test_client()


class TestSQLInjection:
    def test_sql_injection_in_query_param(self, c):
        r = c.get("/api/logs/errors?limit=1%27%20OR%201=1--")
        assert r.status_code != 500  # crash olmamalı

    def test_sqli_in_beacon_register(self, c):
        r = c.post("/api/beacon/register",
                   data=json.dumps({"hostname": "'; DROP TABLE users;--"}),
                   content_type="application/json",
                   headers={"X-Beacon-Key": "test-beacon-key-32-chars-long!!"})
        assert r.status_code in (200, 400, 401)

    def test_sqli_in_login(self, c):
        r = c.post("/login", data={"username": "admin'--", "password": "x"})
        assert r.status_code in (200, 302, 429)


class TestXSSPayloads:
    def test_xss_in_target_param(self, c):
        r = c.get("/api/logs/errors?tool=<script>alert(1)</script>")
        assert r.status_code != 500

    def test_xss_in_json_body(self, c):
        r = c.post("/api/beacon/register",
                   data=json.dumps({"hostname": "<img src=x onerror=alert(1)>"}),
                   content_type="application/json",
                   headers={"X-Beacon-Key": "test-beacon-key-32-chars-long!!"})
        assert r.status_code in (200, 400, 401)


class TestEdgeInputs:
    def test_null_byte(self, c):
        r = c.get("/api/logs/errors?tool=test\x00null")
        assert r.status_code != 500

    def test_very_long_input(self, c):
        long_str = "A" * 10000
        r = c.post("/api/beacon/register",
                   data=json.dumps({"hostname": long_str}),
                   content_type="application/json",
                   headers={"X-Beacon-Key": "test-beacon-key-32-chars-long!!"})
        assert r.status_code in (200, 400, 401, 413, 500)

    def test_unicode_input(self, c):
        r = c.get("/api/logs/errors?tool=テスト")
        assert r.status_code != 500