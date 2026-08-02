"""
Yggdrasil Security Framework - Core Module

Provides foundational components for authentication, database access,
logging, system monitoring, task management, tool execution, and
input validation.

Exports:
    login_required  - Flask view decorator for session-based auth
    csrf_protect    - Flask view decorator for CSRF token validation
    generate_csrf_token - Generate a CSRF token for the session
"""

import secrets
from functools import wraps
from flask import session, redirect, url_for, request, abort, current_app, jsonify


# ---------------------------------------------------------------------------
# Role-Based Access Control
# ---------------------------------------------------------------------------

# Available roles, ordered from least to most privileged.
ROLES = ["readonly", "analyst", "admin"]

# Default role assigned on first login.
DEFAULT_ROLE = "admin"


def require_role(*allowed_roles: str):
    """Decorator that restricts access to users with one of the given roles.

    Must be stacked **below** ``@login_required``::

        @app.route("/api/sensitive")
        @login_required
        @require_role("admin")
        def sensitive():
            ...

    If the user's ``session["role"]`` is not in *allowed_roles* they receive
    a 403 JSON response.
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user_role = session.get("role", "")
            if user_role not in allowed_roles:
                return jsonify({
                    "status": "error",
                    "message": f"Role '{user_role}' not permitted. Required: {', '.join(allowed_roles)}.",
                }), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

import time as _time

# Session timeout: 30 minutes of inactivity logs the user out.
SESSION_TIMEOUT: int = 1800  # seconds


def login_required(f):
    """Decorator that ensures the user is logged in via Flask session.

    Session fixation mitigation: a fresh session secret is set on every
    login.  Callers (auth_routes.py) MUST call ``session.clear()``
    before populating ``session['logged_in'] = True``.

    Session timeout: if ``SESSION_TIMEOUT`` seconds have elapsed since the
    last activity (stored in ``session['_last_activity']``), the session is
    cleared and the user is redirected to login.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("auth.login"))

        last_activity = session.get("_last_activity")
        if last_activity and (_time.time() - last_activity > SESSION_TIMEOUT):
            session.clear()
            return redirect(url_for("auth.login"))

        session["_last_activity"] = _time.time()
        return f(*args, **kwargs)
    return decorated_function


# ---------------------------------------------------------------------------
# CSRF Protection
# ---------------------------------------------------------------------------

# Beacon register and checkin are machine-to-machine endpoints.
# They authenticate via X-Beacon-Key header, not cookie-based sessions,
# so CSRF is irrelevant for them.
CSRF_EXEMPT_PREFIXES = [
    "/api/beacon/register",
    "/api/beacon/checkin",
    "/api/beacon/task",
    "/api/beacon/output",
]


def _is_csrf_exempt():
    """Return True if the current request path is CSRF-exempt."""
    path = request.path.rstrip("/")
    for prefix in CSRF_EXEMPT_PREFIXES:
        if path.startswith(prefix):
            return True
    return False


def generate_csrf_token() -> str:
    """Generate a new CSRF token and store it in the session.

    Returns:
        The generated token string (32 hex chars).
    """
    token = secrets.token_hex(16)
    session["csrf_token"] = token
    return token


def csrf_protect(f):
    """Decorator that enforces CSRF token validation on state-changing requests.

    - GET / HEAD / OPTIONS are always allowed (safe methods).
    - POST / PUT / PATCH / DELETE require a valid CSRF token.
    - The token must be sent as ``X-CSRFToken`` header or ``csrf_token``
      form field, and must match ``session['csrf_token']``.
    - Beacon endpoints are automatically exempt.

    Usage::

        @app.route("/api/action", methods=["POST"])
        @login_required
        @csrf_protect
        def handle_action():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return f(*args, **kwargs)

        if _is_csrf_exempt():
            return f(*args, **kwargs)

        session_token = session.get("csrf_token")
        if not session_token:
            # No token in session → generate one so the frontend can pick it up
            generate_csrf_token()
            abort(403, description="CSRF token missing — refresh the page and try again.")

        # Check header first, then form field
        client_token = request.headers.get("X-CSRFToken") or request.form.get("csrf_token")
        if not client_token or not secrets.compare_digest(session_token, client_token):
            abort(403, description="CSRF token invalid or missing.")

        return f(*args, **kwargs)
    return decorated_function


__all__ = ["login_required", "csrf_protect", "generate_csrf_token"]