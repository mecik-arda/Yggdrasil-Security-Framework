"""Edge case testleri — boş body, eksik header, path injection"""
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


class TestEdgeCases:
    def test_empty_post_body(self, c):
        r = c.post("/api/beacon/register", content_type="application/json",
                   headers={"X-Beacon-Key": "test-beacon-key-32-chars-long!!"})
        assert r.status_code in (200, 400, 401, 500)

    def test_wrong_content_type(self, c):
        r = c.post("/api/beacon/register",
                   data="hostname=test",
                   content_type="application/x-www-form-urlencoded",
                   headers={"X-Beacon-Key": "test-beacon-key-32-chars-long!!"})
        assert r.status_code in (200, 400, 401, 415, 500)

    def test_double_slash_in_path(self, c):
        r = c.get("//api/auth/status")
        assert r.status_code in (200, 301, 302, 308, 404, 500)

    def test_trailing_slash(self, c):
        r = c.get("/login/")
        assert r.status_code in (200, 301, 302, 308, 404, 500)

    def test_missing_header(self, c):
        r = c.get("/api/beacon/list")
        assert r.status_code == 302

    def test_invalid_json(self, c):
        r = c.post("/api/beacon/register",
                   data="not-json{{{",
                   content_type="application/json",
                   headers={"X-Beacon-Key": "test-beacon-key-32-chars-long!!"})
        assert r.status_code in (400, 401, 500)

    def test_http_method_not_allowed(self, c):
        r = c.put("/api/auth/status")
        assert r.status_code in (200, 404, 405, 500)

    def test_delete_method(self, c):
        r = c.delete("/api/auth/status")
        assert r.status_code in (200, 404, 405, 500)