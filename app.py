import os
import secrets
import json
import logging
from flask import Flask, render_template, request, session, jsonify, redirect, url_for
from flask_cors import CORS
from dotenv import load_dotenv
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from core.db import init_db
from core.monitor import start_monitor
from core.extensions import limiter

# Blueprints
from routes.auth_routes import auth_bp
from routes.api_routes import api_bp
from routes.action_routes import action_bp

# Initialize environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Initialize Limiter
limiter.init_app(app)

def generate_and_save_secret(key_name, length=16):
    """Generate a secret and append it to .env if missing"""
    secret = secrets.token_hex(length)
    try:
        with open('.env', 'a') as f:
            f.write(f"\n{key_name}={secret}\n")
    except Exception as e:
        print(f"[!] Warning: Could not save {key_name} to .env: {e}")
    return secret

# Secret Key Handling
app.secret_key = os.environ.get('SECRET_KEY')
if not app.secret_key:
    app.secret_key = generate_and_save_secret('SECRET_KEY', 32)
    print(f"\n[+] Generated and saved new SECRET_KEY to .env")

# Admin Password Handling
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')
if not ADMIN_PASSWORD:
    ADMIN_PASSWORD = generate_and_save_secret('ADMIN_PASSWORD', 8)
    print(f"\n[+] Generated and saved new ADMIN_PASSWORD to .env")
    print(f"[!] YOUR NEW ADMIN PASSWORD IS: {ADMIN_PASSWORD}\n")
    
app.config['ADMIN_PASSWORD'] = ADMIN_PASSWORD

# Apply limiter to auth_routes login manually since blueprint is already created
from routes.auth_routes import auth_bp

# Translations
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
        token = session.get('csrf_token')
        if not token or token != request.headers.get('X-CSRFToken'):
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'status': 'error', 'message': 'CSRF token missing or incorrect.'}), 403
            return "CSRF Error", 403

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

from routes.wsl_routes import api_wsl_bp
from routes.ai_routes import ai_bp
from routes.rag_loki_routes import rag_loki_bp

# Register Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(api_bp)
app.register_blueprint(action_bp)
app.register_blueprint(api_wsl_bp)
app.register_blueprint(ai_bp)
app.register_blueprint(rag_loki_bp)

# Main Application Routes
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

# Old AI routes moved to ai_routes.py

# Startup Initialization
with app.app_context():
    init_db()
    start_monitor()

if __name__ == '__main__':
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    print("""
    __   __                 _               _ _ 
    \ \ / /                | |             (_) |
     \ V /__ _  __ _   __ _| |__  __ _ _ __ _| |
      \ // _` |/ _` |/ _` | '_ \/ _` | '__| | |
      | | (_| | (_| | (_| | |_) | (_| | |  | | |
      \_/\__, |\__, |\__,_|_.__/ \__,_|_|  |_|_|
          __/ | __/ |                            
         |___/ |___/     Security Framework v2.0.0
    """)
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
