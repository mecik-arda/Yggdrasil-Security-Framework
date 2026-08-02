"""
Yggdrasil Security Framework - Core Module

Provides foundational components for authentication, database access,
logging, system monitoring, task management, tool execution, and
input validation.

Exports:
    login_required  - Flask view decorator for session-based auth
"""

from functools import wraps
from flask import session, redirect, url_for


def login_required(f):
    """Decorator that ensures the user is logged in via Flask session.

    Session fixation mitigation: a fresh session secret is set on every
    login.  Callers (auth_routes.py) MUST call ``session.clear()``
    before populating ``session['logged_in'] = True``.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function


__all__ = ["login_required"]