"""Rate limiting testleri — Flask-Limiter entegrasyonu."""
import os

import pytest


class TestRateLimiting:
    """Flask-Limiter zaten core/extensions.py'de yapılandırılmış."""

    def test_limiter_import(self):
        from core.extensions import limiter
        # limiter None is OK locally (may not have flask-limiter installed)
        # CI'da requirements.txt'den yüklendiği için mevcut olmalı
        if os.environ.get("CI") == "true":
            assert limiter is not None
        else:
            # localde flask-limiter yoksa import None döner — kabul edilebilir
            pass

    def test_api_endpoints_accessible(self, app):
        """Rate limit altında API endpoint'leri erişilebilir olmalı."""
        c = app.test_client()
        r = c.get("/api/auth/status")
        assert r.status_code == 200

    def test_multiple_requests_within_limit(self, app):
        """10 ardışık istek başarılı olmalı (200/dk limit altında)."""
        c = app.test_client()
        for _ in range(10):
            r = c.get("/api/auth/status")
            assert r.status_code == 200


class TestRateLimitLogin:
    """Login rate limiting zaten routes/auth_routes.py'de IP bazlı."""

    def test_login_endpoint_works(self, app):
        c = app.test_client()
        r = c.get("/login")
        assert r.status_code == 200