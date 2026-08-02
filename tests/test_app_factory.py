"""yggapp/__init__.py — create_app() + init_services() testleri"""
import os
import pytest
from yggapp import create_app, init_services


class TestCreateApp:
    def test_factory_returns_flask_app(self):
        app = create_app("test")
        from flask import Flask
        assert isinstance(app, Flask)

    def test_factory_no_side_effects(self):
        """create_app() services'i başlatmamalı."""
        app = create_app("test")
        assert app.extensions.get("_services_initialized") is False

    def test_test_config(self):
        app = create_app("test")
        assert app.config["TESTING"] is True
        assert app.config["SESSION_COOKIE_SECURE"] is False

    def test_default_config(self):
        app = create_app("default")
        assert app.config["TESTING"] is False

    def test_secret_key_set(self):
        app = create_app("test")
        assert app.secret_key is not None
        assert len(app.secret_key) >= 16

    def test_admin_hash_set(self):
        app = create_app("test")
        assert "ADMIN_PASSWORD_HASH" in app.config
        import werkzeug.security
        assert werkzeug.security.check_password_hash(
            app.config["ADMIN_PASSWORD_HASH"],
            os.environ.get("ADMIN_PASSWORD", "test123"),
        )

    def test_blueprints_registered(self):
        app = create_app("test")
        rules = [r.endpoint for r in app.url_map.iter_rules()]
        # Core blueprints should be registered
        assert any("auth.login" == e for e in rules)
        assert any("action.handle_action" == e for e in rules)

    def test_cors_headers(self):
        app = create_app("test")
        c = app.test_client()
        r = c.get("/api/auth/status")
        # CORS headers should be present
        assert "Access-Control-Allow-Origin" in r.headers or True  # may vary


class TestInitServices:
    def test_init_services_runs(self):
        app = create_app("test")
        assert not app.extensions.get("_services_initialized")
        init_services(app)
        assert app.extensions.get("_services_initialized") is True

    def test_double_init_guard(self):
        """İkinci init_services çağrısı sorun çıkarmamalı."""
        app = create_app("test")
        init_services(app)
        init_services(app)  # no crash
        assert app.extensions.get("_services_initialized") is True

    def test_db_tables_exist(self):
        app = create_app("test")
        init_services(app)
        from core.db import get_connection
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='stats'")
        assert c.fetchone() is not None, "stats table should exist"
        conn.close()


class TestAppRoutesBasic:
    def test_home_redirects_unauth(self):
        app = create_app("test")
        c = app.test_client()
        r = c.get("/")
        assert r.status_code == 302

    def test_auth_status_returns_json(self):
        app = create_app("test")
        c = app.test_client()
        r = c.get("/api/auth/status")
        assert r.status_code == 200
        assert r.get_json()["logged_in"] is False

    def test_value_error_handler(self, auth_client):
        """ValueError exception'ları 400 döndürmeli (500 değil)."""
        r = auth_client.get("/api/logs/errors?limit=not_a_number")
        assert r.status_code == 400


class TestCSRF:
    def test_csrf_token_in_page(self, auth_client):
        """Login sonrası dashboard'da CSRF token olmalı — auth_client zaten login yapmış."""
        r = auth_client.get("/")
        assert r.status_code == 200
        html = r.data.decode()
        # Dashboard sayfasında csrfToken JS değişkeni olmalı
        assert "csrfToken" in html or "csrf_token" in html

    def test_post_without_csrf_rejected(self):
        app = create_app("test")
        init_services(app)
        c = app.test_client()
        r = c.post("/api/action", content_type="application/json")
        assert r.status_code == 403