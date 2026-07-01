from flask import Blueprint, render_template, request, session, redirect, url_for, current_app
import time

auth_bp = Blueprint('auth', __name__)

from flask import current_app

_AUTH_ATTEMPTS = {}

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        ip = request.remote_addr or '127.0.0.1'
        now = time.time()
        attempts = [t for t in _AUTH_ATTEMPTS.get(ip, []) if now - t < 60]
        if len(attempts) >= 5:
            return render_template('login.html', error='Too many attempts. Wait 1 minute.'), 429
        password = request.form.get('password')
        if password == current_app.config['ADMIN_PASSWORD']:
            session['logged_in'] = True
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
