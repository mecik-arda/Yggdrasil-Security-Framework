"""Pytest fixtures — tüm testler için ortak session yönetimi."""
import os
import pytest
import json
import re

# Ensure env vars override .env file values
os.environ["BEACON_API_KEY"] = "test-beacon-key-32-chars-long!!"
os.environ["SECRET_KEY"] = "test-secret-key-32-chars-long!!"
os.environ["ADMIN_PASSWORD"] = "test123"

# Ensure project root is on path
_src = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _src not in __import__("sys").path:
    __import__("sys").path.insert(0, _src)


@pytest.fixture(scope="session")
def app():
    """Fresh Flask app — no services, no DB (session-scoped)."""
    from yggapp import create_app, init_services
    a = create_app("test")
    init_services(a)
    return a


@pytest.fixture
def client(app):
    """Test client with NO login (unauth)."""
    return app.test_client()


@pytest.fixture(scope="session")
def auth_client(app):
    """Test client with admin login + CSRF token (session-scoped, tek login)."""
    from yggapp import init_services
    init_services(app)

    c = app.test_client()
    r = c.post("/login", data={"username": "admin", "password": "test123"},
               follow_redirects=True)
    assert r.status_code == 200, f"Login failed: {r.status_code}"

    # Extract CSRF token from HTML
    html = r.data.decode()
    m = re.search(r'"csrf_token"\s*,\s*"([^"]+)"', html)
    csrf_token = m.group(1) if m else None

    # Attach CSRF token to client for auto-injection
    c._csrf_token = csrf_token
    return c


def auth_post(client, path, data=None):
    """Helper: POST with CSRF token and session cookie."""
    headers = {}
    if getattr(client, '_csrf_token', None):
        headers["X-CSRFToken"] = client._csrf_token
    return client.post(
        path,
        data=json.dumps(data) if data else None,
        content_type="application/json",
        headers=headers,
    )


@pytest.fixture
def temp_db_path(tmp_path_factory):
    """Temporary SQLite database path for core module tests."""
    db_dir = tmp_path_factory.mktemp("db")
    db_path = db_dir / "test_stats.db"
    # Redirect core.db's DB_PATH to temp file
    import core.db as db_mod
    original = getattr(db_mod, "DB_PATH", None)
    db_mod.DB_PATH = str(db_path)
    # Ensure tables are fresh
    db_mod.init_db()
    db_mod.init_c2_tables()
    yield str(db_path)
    if original is not None:
        db_mod.DB_PATH = original
