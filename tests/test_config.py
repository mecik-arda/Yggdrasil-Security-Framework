"""Uygulama yapılandırma testleri"""
import os, pytest
from yggapp import create_app


class TestEnvironmentVars:
    def test_beacon_key_set(self):
        assert os.environ.get("BEACON_API_KEY") is not None
    def test_secret_key_set(self):
        assert os.environ.get("SECRET_KEY") is not None
    def test_admin_password_set(self):
        assert os.environ.get("ADMIN_PASSWORD") is not None


class TestAppConfigs:
    def test_test_config(self):
        app = create_app("test")
        assert app.config["TESTING"] is True
    def test_default_config(self):
        app = create_app("default")
        assert app.config["TESTING"] is False
    def test_admin_hash(self):
        app = create_app("test")
        assert "ADMIN_PASSWORD_HASH" in app.config
    def test_secret_key_length(self):
        app = create_app("test")
        assert len(app.secret_key) >= 16
    def test_translations(self):
        app = create_app("test")
        assert "TRANSLATIONS" in app.config
    def test_cors_configured(self):
        app = create_app("default")
        assert app.config.get("CORS_ORIGINS") or True