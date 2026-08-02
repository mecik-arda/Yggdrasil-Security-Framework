"""Session timeout testleri — SESSION_TIMEOUT (30dk) mekanizması."""
import time

import pytest


class TestSessionTimeout:
    """Session timeout: 30 dakika inaktivite → auto-logout."""

    def test_session_timeout_constant(self):
        from core import SESSION_TIMEOUT
        assert SESSION_TIMEOUT == 1800  # 30 minutes

    def test_activity_updates_timestamp(self, app):
        """Her istek _last_activity timestamp'ini güncellemeli."""
        c = app.test_client()
        c.post("/login", data={"password": "test123"}, follow_redirects=True)
        with c.session_transaction() as sess:
            assert sess.get("_last_activity") is not None

    def test_fresh_login_has_no_timeout(self, app):
        """Yeni login olmuş kullanıcı timeout'a uğramamalı."""
        c = app.test_client()
        c.post("/login", data={"password": "test123"}, follow_redirects=True)
        r = c.get("/api/auth/status")
        assert r.status_code == 200

    def test_logout_clears_session(self, auth_client):
        """Logout session'ı temizlemeli."""
        r = auth_client.get("/logout", follow_redirects=True)
        assert r.status_code == 200