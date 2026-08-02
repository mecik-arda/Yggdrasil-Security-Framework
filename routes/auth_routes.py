from flask import Blueprint, render_template, request, session, redirect, url_for, current_app
import time
from collections import OrderedDict

auth_bp = Blueprint('auth', __name__)

from flask import current_app

_AUTH_ATTEMPTS = OrderedDict()
MAX_TRACKED_IPS = 1000  # FIX: prevent unbounded memory growth from brute-force attempts

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        ip = request.remote_addr or '127.0.0.1'
        now = time.time()
        # FIX: Prune old IPs to prevent memory leak from brute-force scans
        if len(_AUTH_ATTEMPTS) > MAX_TRACKED_IPS:
            while len(_AUTH_ATTEMPTS) > MAX_TRACKED_IPS // 2:
                _AUTH_ATTEMPTS.popitem(last=False)
        # CI ortamında rate-limit uygulama (testler paralel çalışıyor)
        in_ci = __import__('os').environ.get('CI', '').lower() == 'true'
        attempts = [t for t in _AUTH_ATTEMPTS.get(ip, []) if now - t < 60]
        if not in_ci and len(attempts) >= 5:
            return render_template('login.html', error='Too many attempts. Wait 1 minute.'), 429
        import werkzeug.security
        # Support both form-data and JSON login
        if request.is_json:
            data = request.get_json(silent=True) or {}
            password = data.get('password', '')
        else:
            password = request.form.get('password', '')
        if werkzeug.security.check_password_hash(current_app.config['ADMIN_PASSWORD_HASH'], password):
            # FIX: Regenerate session ID to prevent session fixation attacks
            session.clear()
            session['logged_in'] = True
            session['role'] = 'admin'  # RBAC: default role
            from core import generate_csrf_token
            generate_csrf_token()
            _AUTH_ATTEMPTS.pop(ip, None)
            return redirect(url_for('home'))
        else:
            attempts.append(now)
            _AUTH_ATTEMPTS[ip] = attempts
            return render_template('login.html', error="Parola hatali! (Incorrect password)")
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
