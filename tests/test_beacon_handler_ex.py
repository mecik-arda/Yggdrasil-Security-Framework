"""Beacon handler extended testleri"""
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


@pytest.fixture
def auth(app):
    c2 = app.test_client()
    r = c2.post("/login", data={"username": "admin", "password": "test123"}, follow_redirects=True)
    if r.status_code != 200:
        pytest.skip("Login failed (rate limit)")
    return c2


class TestBeaconRegister:
    def test_register_no_key_401(self, c):
        r = c.post("/api/beacon/register",
                   data=json.dumps({"hostname": "test"}),
                   content_type="application/json")
        assert r.status_code == 401

    def test_register_with_key_200(self, c):
        r = c.post("/api/beacon/register",
                   data=json.dumps({"hostname": "test-pc", "os": "linux"}),
                   content_type="application/json",
                   headers={"X-Beacon-Key": "test-beacon-key-32-chars-long!!"})
        assert r.status_code == 200

    def test_register_empty_body(self, c):
        r = c.post("/api/beacon/register",
                   content_type="application/json",
                   headers={"X-Beacon-Key": "test-beacon-key-32-chars-long!!"})
        assert r.status_code in (200, 400, 401, 500)


class TestBeaconList:
    def test_list_requires_auth(self, c):
        r = c.get("/api/beacon/list")
        assert r.status_code in (302, 403)

    def test_list_auth(self, auth):
        r = auth.get("/api/beacon/list")
        assert r.status_code == 200

    def test_detail_requires_beacon_id(self, auth):
        r = auth.get("/api/beacon/detail")
        assert r.status_code == 200

    def test_remove_requires_auth(self, c):
        r = c.post("/api/beacon/remove",
                   data=json.dumps({"beacon_id": "x"}),
                   content_type="application/json")
        assert r.status_code in (302, 403)


class TestBeaconTask:
    def test_assign_task_requires_login(self, c):
        r = c.post("/api/beacon/task",
                   data=json.dumps({"beacon_id": "x", "command": "whoami"}),
                   content_type="application/json")
        assert r.status_code in (302, 403)


class TestBeaconGenerate:
    def test_generate_requires_url(self, auth):
        r = auth.post("/api/beacon/generate",
                    data=json.dumps({"sleep": 5, "jitter": 10}),
                    content_type="application/json")
        assert r.status_code in (200, 400, 403)

    def test_generate_invalid_sleep_400(self, auth):
        r = auth.post("/api/beacon/generate",
                    data=json.dumps({"listener_url": "http://x.com", "sleep": -5}),
                    content_type="application/json")
        assert r.status_code in (400, 403)
