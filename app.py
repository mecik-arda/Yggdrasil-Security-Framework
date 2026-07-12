import os
import secrets
import json
import logging
import threading
import webbrowser
from flask import Flask, render_template, request, session, jsonify, redirect, url_for
from flask_cors import CORS
from dotenv import load_dotenv
from core.db import init_db, init_c2_tables
from core.monitor import start_monitor
from core.logger import init_logging, set_socketio_instance, get_logger

from routes.auth_routes import auth_bp
from routes.api_routes import api_bp
from routes.action_routes import action_bp

load_dotenv()

app = Flask(__name__)
# Restrict CORS to specific origins (e.g., localhost/127.0.0.1 for local dev, adjust as needed for production)
CORS(app, resources={r"/api/*": {"origins": ["http://localhost:5000", "http://127.0.0.1:5000", "https://localhost:5000"]}})

# Secure Session Cookies
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=True, # Requires HTTPS
    SESSION_COOKIE_SAMESITE='Lax',
)

def generate_and_save_secret(key_name, length=16):
    """Generate a cryptographically secure secret and persist it to .env.

    Uses ``dotenv.set_key`` to avoid duplicate lines that accumulate with
    repeated ``'a'`` (append) writes.
    """
    secret = secrets.token_hex(length)
    try:
        from dotenv import set_key as _dotenv_set_key
        _dotenv_set_key('.env', key_name, secret)
    except Exception as e:
        print(f"[!] Warning: Could not save {key_name} to .env: {e}")
    return secret

app.secret_key = os.environ.get('SECRET_KEY')
if not app.secret_key:
    app.secret_key = generate_and_save_secret('SECRET_KEY', 32)
    print(f"\n[+] Generated and saved new SECRET_KEY to .env")

import werkzeug.security

ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')
if not ADMIN_PASSWORD:
    ADMIN_PASSWORD = generate_and_save_secret('ADMIN_PASSWORD', 12)
    # FIX: Never print the password to stdout — write to a secure file instead
    try:
        pw_file = 'admin_password_initial.txt'
        with open(pw_file, 'w') as f:
            f.write(ADMIN_PASSWORD)
        os.chmod(pw_file, 0o600)
        print(f"\n[+] Generated and saved new ADMIN_PASSWORD to .env")
        print(f"[!] Initial admin password saved to {pw_file} — store it securely and delete this file.\n")
    except Exception as e:
        print(f"\n[+] Generated and saved new ADMIN_PASSWORD to .env (could not write file: {e})\n")

# Store the hash of the password, not the plaintext
app.config['ADMIN_PASSWORD_HASH'] = werkzeug.security.generate_password_hash(ADMIN_PASSWORD)

def load_translations():
    translations = {}
    lang_dir = os.path.join(os.path.dirname(__file__), 'translations')
    if os.path.exists(lang_dir):
        for file in os.listdir(lang_dir):
            if file.endswith('.json'):
                lang_code = file.split('.')[0]
                with open(os.path.join(lang_dir, file), 'r', encoding='utf-8') as f:
                    translations[lang_code] = json.load(f)
    return translations

TRANSLATIONS = load_translations()

def get_translation(key, **kwargs):
    lang = session.get('lang', 'en')
    text = TRANSLATIONS.get(lang, {}).get(key, key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError:
            pass
    return text

def generate_csrf_token():
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(32)
    return session['csrf_token']

@app.before_request
def before_request():
    app.jinja_env.globals.update(t=get_translation, csrf_token=generate_csrf_token)
    if request.method == "POST" and request.endpoint and not request.endpoint.startswith("auth."):
        # FIX: Beacon register/checkin use API key auth (X-Beacon-Key), not session cookies.
        # They must be exempt from CSRF since implants can't send CSRF tokens.
        if request.path in ('/api/beacon/register',) or request.path.startswith('/api/beacon/checkin/'):
            pass  # Skip CSRF — validated by X-Beacon-Key header in beacon_routes.py
        else:
            token = session.get('csrf_token')
            if not token or not secrets.compare_digest(token, request.headers.get('X-CSRFToken') or ''):
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({'status': 'error', 'message': 'CSRF token missing or incorrect.'}), 403
                return "CSRF Error", 403

from core.auth import login_required

# FIX: API rate limiting to prevent DoS/brute-force on sensitive endpoints
try:
    from core.extensions import limiter
    if limiter:
        limiter.init_app(app)
        LIMITER_AVAILABLE = True
    else:
        LIMITER_AVAILABLE = False
except ImportError:
    limiter = None
    LIMITER_AVAILABLE = False

from routes.wsl_routes import api_wsl_bp
from routes.ai_routes import ai_bp
from routes.rag_loki_routes import rag_loki_bp
from routes.c2_routes import c2_bp
from routes.msf_routes import msf_bp
from routes.graph_routes import graph_bp
from routes.beacon_routes import beacon_bp
from routes.evasion_routes import evasion_bp
from routes.team_routes import team_bp, socketio as team_socketio, SOCKETIO_AVAILABLE
from routes.log_routes import log_bp
from routes.ops_routes import ops_bp

app.register_blueprint(auth_bp)
app.register_blueprint(api_bp)
app.register_blueprint(action_bp)
app.register_blueprint(api_wsl_bp)
app.register_blueprint(ai_bp)
app.register_blueprint(rag_loki_bp)
app.register_blueprint(c2_bp)
app.register_blueprint(msf_bp)
app.register_blueprint(graph_bp)
app.register_blueprint(beacon_bp)
app.register_blueprint(evasion_bp)
app.register_blueprint(team_bp)
app.register_blueprint(log_bp)
app.register_blueprint(ops_bp)

if SOCKETIO_AVAILABLE and team_socketio:
    team_socketio.init_app(app)
    set_socketio_instance(team_socketio)

    # Wire up monitor → SocketIO heartbeat
    def _heartbeat_callback(cpu, ram, ping_ms, ollama_online):
        try:
            team_socketio.emit('heartbeat', {
                'cpu': cpu,
                'ram': ram,
                'ping': ping_ms,
                'ollama': ollama_online,
            })
        except Exception:
            get_logger('app').debug('Heartbeat callback emit failed', exc_info=True)

    from core.monitor import set_tick_callback
    set_tick_callback(_heartbeat_callback)



@app.route('/')
@login_required
def home():
    from core.db import get_db_stats
    stats = get_db_stats()
    from tools_config import TOOLS_CONFIG
    lang = session.get('lang', 'en')
    js_translations = TRANSLATIONS.get(lang, {})
    return render_template('index.html', stats=stats, tools=TOOLS_CONFIG, js_translations=js_translations, current_lang=lang)

@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html')

@app.route('/api/set_lang', methods=['POST'])
def set_lang():
    data = request.json
    lang = data.get('lang')
    if lang in TRANSLATIONS:
        session['lang'] = lang
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error'})

@app.route('/api/auth/status', methods=['GET'])
def check_auth_status():
    is_logged_in = session.get('logged_in', False)
    return jsonify({'logged_in': is_logged_in})

with app.app_context():
    init_db()
    init_c2_tables()
    init_logging(app)
    start_monitor()


@app.errorhandler(Exception)
def handle_exception(e):
    """Global Flask error handler — logs all unhandled exceptions."""
    log = get_logger('flask')
    log.error(f'Unhandled exception: {e}', exc_info=True)
    if request.path.startswith('/api/') or request.is_json:
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500
    return render_template('login.html'), 500

if __name__ == '__main__':
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    print(r"""
    __   __                 _               _ _
    \ \ / /                | |             (_) |
     \ V /__ _  __ _   __ _| |__  __ _ _ __ _| |
      \ // _` |/ _` |/ _` | '_ \/ _` | '__| | |
      | | (_| | (_| | (_| | |_) | (_| | |  | | |
      \_/\__, |\__, |\__,_|_.__/ \__,_|_|  |_|_|
          __/ | __/ |
         |___/ |___/     Security Framework v2.1.0
    """)
    threading.Timer(1.5, lambda: webbrowser.open_new("http://127.0.0.1:5000")).start()
    # FIX: Default to localhost — user must explicitly set FLASK_HOST=0.0.0.0 for network exposure
    flask_host = os.environ.get('FLASK_HOST', '127.0.0.1')

    # SSL/TLS support — set SSL_CERT_FILE and SSL_KEY_FILE env vars to enable HTTPS
    ssl_context = None
    ssl_cert = os.environ.get('SSL_CERT_FILE')
    ssl_key = os.environ.get('SSL_KEY_FILE')
    if ssl_cert and ssl_key and os.path.exists(ssl_cert) and os.path.exists(ssl_key):
        ssl_context = (ssl_cert, ssl_key)
        print(f"[+] SSL/TLS enabled — HTTPS active")
        # Downgrade secure cookie requirement if using self-signed cert locally
        if flask_host in ('127.0.0.1', 'localhost'):
            app.config['SESSION_COOKIE_SECURE'] = False
    else:
        # Disable secure cookie for plain HTTP (browsers reject Secure cookies over HTTP)
        app.config['SESSION_COOKIE_SECURE'] = False

    if SOCKETIO_AVAILABLE and team_socketio:
        print(f"[+] SocketIO active — WebSocket real-time mode enabled (host: {flask_host})")
        team_socketio.run(app, host=flask_host, port=5000, debug=False, ssl_context=ssl_context, allow_unsafe_werkzeug=True)
    else:
        print(f"[!] SocketIO not available — falling back to polling mode (host: {flask_host})")
        app.run(host=flask_host, port=5000, debug=False, threaded=True, ssl_context=ssl_context)