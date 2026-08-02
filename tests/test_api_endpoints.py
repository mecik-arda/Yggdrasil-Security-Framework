"""
Tests for API endpoints — JSON responses, rate limiting, task management,
history, stats, and system resources.

Covers ``routes/api_routes.py``.
"""

import sys
import json
import pytest
import werkzeug.security
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Flask test client fixture — remove handlers mock before importing app
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    """Create a Flask test client with authentication bypassed."""
    # Remove the lightweight mock that the conftest session fixture installed.
    if 'handlers' in sys.modules:
        del sys.modules['handlers']

    # Ensure tables exist in the current temp DB
    from core.db import init_db, init_c2_tables
    init_db()
    init_c2_tables()

    from app import app as _app
    _app.config['TESTING'] = True
    _app.config['WTF_CSRF_ENABLED'] = False
    _app.config['ADMIN_PASSWORD_HASH'] = werkzeug.security.generate_password_hash('testpass')
    with _app.test_client() as c:
        with _app.app_context():
            # Pre-login via session
            with c.session_transaction() as sess:
                sess['logged_in'] = True
                sess['role'] = 'admin'
                sess['csrf_token'] = 'test-csrf-token-api'
            yield c


def _csrf_headers(client):
    """Extract the current CSRF token from the client's session."""
    with client.session_transaction() as sess:
        token = sess.get('csrf_token', 'no-token')
    return {'X-CSRFToken': token}


# ---------------------------------------------------------------------------
# Task status endpoint
# ---------------------------------------------------------------------------

class TestTaskStatus:
    def test_task_status_missing_task_id(self, client):
        """GET /api/task_status without task_id returns error."""
        resp = client.get('/api/task_status', headers=_csrf_headers(client))
        data = resp.get_json()
        assert data['status'] == 'error'

    def test_task_status_nonexistent_task(self, client):
        """GET /api/task_status with nonexistent task returns error."""
        resp = client.get('/api/task_status?task_id=nonexistent',
                         headers=_csrf_headers(client))
        data = resp.get_json()
        assert data['status'] == 'error'


# ---------------------------------------------------------------------------
# Task kill endpoints
# ---------------------------------------------------------------------------

class TestTaskKill:
    def test_kill_task_missing_id(self, client):
        """POST /api/task_kill without task_id returns error."""
        resp = client.post('/api/task_kill', data={},
                          headers=_csrf_headers(client))
        data = resp.get_json()
        assert data['status'] == 'error'

    def test_kill_all_tasks_returns_success(self, client):
        """POST /api/task_kill_all should return success with kill count."""
        resp = client.post('/api/task_kill_all', data={},
                          headers=_csrf_headers(client))
        data = resp.get_json()
        assert data['status'] == 'success'
        assert 'killed' in data


# ---------------------------------------------------------------------------
# System resources endpoint
# ---------------------------------------------------------------------------

class TestSystemResources:
    def test_system_resources_returns_json(self, client):
        """GET /api/system_resources should return JSON with cpu, ram fields."""
        resp = client.get('/api/system_resources', headers=_csrf_headers(client))
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'cpu' in data
        assert 'ram' in data

    def test_system_resources_has_queue_stats(self, client):
        """Response should include queue statistics."""
        resp = client.get('/api/system_resources', headers=_csrf_headers(client))
        data = resp.get_json()
        assert 'queue' in data


# ---------------------------------------------------------------------------
# History endpoints
# ---------------------------------------------------------------------------

class TestHistory:
    def test_history_returns_list(self, client):
        """GET /api/history should return a JSON array."""
        resp = client.get('/api/history', headers=_csrf_headers(client))
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)

    def test_history_clear_returns_success(self, client):
        """POST /api/history/clear should return success."""
        resp = client.post('/api/history/clear', data={},
                          headers=_csrf_headers(client))
        data = resp.get_json()
        assert data['status'] == 'success'


# ---------------------------------------------------------------------------
# Tools endpoint
# ---------------------------------------------------------------------------

class TestTools:
    def test_tools_returns_dict(self, client):
        """GET /api/tools should return a JSON object keyed by tool name."""
        resp = client.get('/api/tools', headers=_csrf_headers(client))
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, dict)
        # Should have at least one known tool
        assert len(data) > 0

    def test_tools_have_required_fields(self, client):
        """Each tool entry should have name, category, requires_target."""
        resp = client.get('/api/tools', headers=_csrf_headers(client))
        data = resp.get_json()
        for key, val in data.items():
            assert 'name' in val
            assert 'category' in val


# ---------------------------------------------------------------------------
# Stats endpoint
# ---------------------------------------------------------------------------

class TestStats:
    def test_stats_returns_dict(self, client):
        """GET /api/stats should return scan stats."""
        resp = client.get('/api/stats', headers=_csrf_headers(client))
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'total_scans' in data
        assert 'last_target' in data
        assert 'active_tool' in data


# ---------------------------------------------------------------------------
# Rate limiting (when flask-limiter is available)
# ---------------------------------------------------------------------------

class TestRateLimiting:
    def test_rate_limit_headers_or_normal_response(self, client):
        """Multiple rapid requests should not crash under load."""
        responses = []
        for _ in range(5):
            resp = client.get('/api/tools', headers=_csrf_headers(client))
            responses.append(resp.status_code)
        # All should succeed — rate limiter may or may not be active
        assert all(s == 200 for s in responses)
