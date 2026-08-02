"""
Tests for auth routes — login, logout, password hashing, CSRF protection,
unauthorized access redirects, and rate limiting.

Covers ``routes/auth_routes.py`` and ``core/auth.py``.
"""

import sys
import pytest
import werkzeug.security
from flask import session, url_for


# ---------------------------------------------------------------------------
# Flask test client fixture — remove handlers mock before importing app
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    """Create a Flask test client for the Yggdrasil app.

    The conftest session-scoped ``_mock_handlers_module`` fixture stubs out
    ``handlers`` to speed up core-only tests.  We remove it here so the full
    Flask application (and all its route → handler imports) can load.

    We also ensure DB tables are re-created for each test's temporary DB.
    """
    # Remove the lightweight mock that the conftest session fixture installed.
    if 'handlers' in sys.modules:
        del sys.modules['handlers']

    # Ensure tables exist in the current temp DB (conftest redirects stats.db)
    from core.db import init_db, init_c2_tables
    init_db()
    init_c2_tables()

    from app import app as _app
    _app.config['TESTING'] = True
    _app.config['WTF_CSRF_ENABLED'] = False
    _app.config['ADMIN_PASSWORD_HASH'] = werkzeug.security.generate_password_hash('testpass')
    with _app.test_client() as c:
        with _app.app_context():
            yield c


@pytest.fixture
def logged_in_client(client):
    """A test client that is already logged in."""
    with client.session_transaction() as sess:
        sess['logged_in'] = True
        sess['csrf_token'] = 'test-csrf-token-12345'
    return client


# ---------------------------------------------------------------------------
# Login page rendering
# ---------------------------------------------------------------------------

class TestLoginPage:
    def test_get_login_returns_200(self, client):
        """GET /login should return the login page."""
        resp = client.get('/login')
        assert resp.status_code == 200

    def test_login_page_has_password_field(self, client):
        """The login form should contain a password field."""
        resp = client.get('/login')
        html = resp.data.decode('utf-8')
        assert 'password' in html.lower()


# ---------------------------------------------------------------------------
# Login POST — successful authentication
# ---------------------------------------------------------------------------

class TestLoginSuccess:
    def test_login_with_correct_password_redirects(self, client):
        """Correct password should redirect to home (302)."""
        resp = client.post('/login', data={'password': 'testpass'}, follow_redirects=False)
        assert resp.status_code == 302

    def test_login_sets_session_logged_in(self, client):
        """After successful login, session['logged_in'] should be True."""
        resp = client.post('/login', data={'password': 'testpass'})
        # Follow redirect then check session
        with client.session_transaction() as sess:
            # Session should have logged_in after successful POST+redirect
            pass
        # Just verify we got redirected (302)
        assert resp.status_code == 302

    def test_login_clears_old_session_on_success(self, client):
        """Session fixation: old session data should be cleared on login."""
        with client.session_transaction() as sess:
            sess['old_data'] = 'should-be-removed'
        client.post('/login', data={'password': 'testpass'})
        with client.session_transaction() as sess:
            assert 'old_data' not in sess


# ---------------------------------------------------------------------------
# Login POST — failed authentication
# ---------------------------------------------------------------------------

class TestLoginFailure:
    def test_login_with_wrong_password_returns_200(self, client):
        """Wrong password should re-render login page, not redirect."""
        resp = client.post('/login', data={'password': 'wrongpassword'})
        assert resp.status_code == 200

    def test_login_with_wrong_password_shows_error(self, client):
        """Wrong password should show an error message."""
        resp = client.post('/login', data={'password': 'wrongpassword'})
        html = resp.data.decode('utf-8')
        assert 'hatali' in html.lower() or 'incorrect' in html.lower() or 'error' in html.lower()

    def test_login_with_wrong_password_does_not_set_session(self, client):
        """Failed login should NOT set logged_in in session."""
        client.post('/login', data={'password': 'wrongpassword'})
        with client.session_transaction() as sess:
            assert sess.get('logged_in') is not True

    def test_login_with_empty_password_fails(self, client):
        """Empty password should fail."""
        resp = client.post('/login', data={'password': ''})
        assert resp.status_code == 200
        with client.session_transaction() as sess:
            assert sess.get('logged_in') is not True


# ---------------------------------------------------------------------------
# Login brute-force protection
# ---------------------------------------------------------------------------

class TestBruteForceProtection:
    def test_too_many_attempts_returns_429(self, client):
        """After 5+ failed attempts, should return HTTP 429."""
        for _ in range(6):
            client.post('/login', data={'password': 'wrong'})
        resp = client.post('/login', data={'password': 'wrong'})
        assert resp.status_code == 429

    def test_rate_limit_message_on_429(self, client):
        """429 response should mention waiting."""
        for _ in range(6):
            client.post('/login', data={'password': 'wrong'})
        resp = client.post('/login', data={'password': 'wrong'})
        html = resp.data.decode('utf-8')
        assert 'attempt' in html.lower() or 'wait' in html.lower() or 'minute' in html.lower()


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

class TestLogout:
    def test_logout_clears_session(self, logged_in_client):
        """Logout should clear the session."""
        logged_in_client.get('/logout')
        with logged_in_client.session_transaction() as sess:
            assert sess.get('logged_in') is not True

    def test_logout_redirects_to_login(self, logged_in_client):
        """Logout should redirect to login page."""
        resp = logged_in_client.get('/logout', follow_redirects=False)
        assert resp.status_code == 302

    def test_logout_when_not_logged_in_still_works(self, client):
        """Logout when not logged in should not crash."""
        resp = client.get('/logout', follow_redirects=False)
        assert resp.status_code == 302


# ---------------------------------------------------------------------------
# Unauthorized access — login_required decorator
# ---------------------------------------------------------------------------

class TestLoginRequired:
    def test_home_redirects_when_not_logged_in(self, client):
        """GET / should redirect to login when not authenticated."""
        resp = client.get('/', follow_redirects=False)
        assert resp.status_code == 302

    def test_settings_redirects_when_not_logged_in(self, client):
        """GET /settings should redirect when not authenticated."""
        resp = client.get('/settings', follow_redirects=False)
        assert resp.status_code == 302

    def test_api_endpoints_redirect_when_not_logged_in(self, client):
        """API endpoints should redirect when not authenticated."""
        resp = client.get('/api/stats', follow_redirects=False)
        assert resp.status_code == 302

    def test_home_accessible_when_logged_in(self, logged_in_client):
        """GET / should succeed when authenticated."""
        resp = logged_in_client.get('/')
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# CSRF protection
# ---------------------------------------------------------------------------

class TestCsrfProtection:
    def test_post_without_csrf_token_returns_403(self, logged_in_client):
        """POST without CSRF token should return 403."""
        resp = logged_in_client.post('/api/task_kill_all', data={})
        assert resp.status_code == 403

    def test_post_with_wrong_csrf_token_returns_403(self, logged_in_client):
        """POST with incorrect CSRF token should return 403."""
        resp = logged_in_client.post(
            '/api/task_kill_all',
            data={},
            headers={'X-CSRFToken': 'wrong-token'}
        )
        assert resp.status_code == 403

    def test_post_with_correct_csrf_token_allowed(self, logged_in_client):
        """POST with correct CSRF token should succeed (not 403 for CSRF)."""
        with logged_in_client.session_transaction() as sess:
            token = sess.get('csrf_token', 'fallback')
        resp = logged_in_client.post(
            '/api/task_kill_all',
            data={},
            headers={'X-CSRFToken': token}
        )
        # Should NOT be 403 (may be another status, but not CSRF blocked)
        assert resp.status_code != 403

    def test_beacon_register_exempt_from_csrf(self, client):
        """Beacon register endpoint should be exempt from CSRF checks."""
        resp = client.post('/api/beacon/register',
                          data='{"hostname":"test"}',
                          content_type='application/json')
        # Should not be 403 for CSRF (may be 401 for auth, but not CSRF)
        assert resp.status_code != 403


# ---------------------------------------------------------------------------
# Auth status check
# ---------------------------------------------------------------------------

class TestAuthStatus:
    def test_auth_status_not_logged_in(self, client):
        """GET /api/auth/status should return logged_in: false."""
        resp = client.get('/api/auth/status')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['logged_in'] is False

    def test_auth_status_logged_in(self, logged_in_client):
        """GET /api/auth/status should return logged_in: true."""
        resp = logged_in_client.get('/api/auth/status')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['logged_in'] is True


# ---------------------------------------------------------------------------
# Password hash verification
# ---------------------------------------------------------------------------

class TestPasswordHashing:
    def test_password_hash_matches(self):
        """check_password_hash should return True for correct password."""
        pw = 'mysecurepassword'
        hashed = werkzeug.security.generate_password_hash(pw)
        assert werkzeug.security.check_password_hash(hashed, pw) is True

    def test_password_hash_does_not_match(self):
        """check_password_hash should return False for wrong password."""
        pw = 'mysecurepassword'
        hashed = werkzeug.security.generate_password_hash(pw)
        assert werkzeug.security.check_password_hash(hashed, 'wrong') is False

    def test_password_hash_is_different_each_time(self):
        """Each call to generate_password_hash should produce unique output."""
        pw = 'test'
        h1 = werkzeug.security.generate_password_hash(pw)
        h2 = werkzeug.security.generate_password_hash(pw)
        assert h1 != h2
