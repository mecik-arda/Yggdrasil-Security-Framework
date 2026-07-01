from flask import Blueprint, render_template, request, session, redirect, url_for, current_app
import os

auth_bp = Blueprint('auth', __name__)

from flask import current_app
from core.extensions import limiter

@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        # Rate limiting yapilacak
        if password == current_app.config['ADMIN_PASSWORD']:
            session['logged_in'] = True
            return redirect(url_for('home'))
        else:
            return render_template('login.html', error="Parola hatalı! (Incorrect password)")
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
