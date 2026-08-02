"""
Yggdrasil Security Framework — Application Factory

Provides ``create_app()`` so tests, CLI tools, and deployments can build
independent Flask instances without running the module-level side-effects.
"""


def create_app(config_name='default'):
    """Build and return a fully-configured Flask application."""
    import os
    import secrets
    import json
    import logging
    import werkzeug.security

    from flask import Flask, render_template, request, session, jsonify
    from flask_cors import CORS
    from dotenv import load_dotenv

    load_dotenv()

    template_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates')
    static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static')
    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

    # -- Configuration ------------------------------------------------------
    app.config.from_object(_config_map.get(config_name, DefaultConfig))

    # Apply .env overrides
    app.secret_key = os.environ.get('SECRET_KEY') or _generate_and_save_secret('SECRET_KEY', 32)
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SECURE'] = app.config.get('SESSION_COOKIE_SECURE', True)
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')
    if not ADMIN_PASSWORD:
        raise RuntimeError(
            "ADMIN_PASSWORD environment variable is required. "
            "Set it in your .env file before starting the application."
        )
    app.config['ADMIN_PASSWORD_HASH'] = werkzeug.security.generate_password_hash(ADMIN_PASSWORD)

    CORS(app, resources={r"/api/*": {
        "origins": app.config.get('CORS_ORIGINS', ["http://localhost:5000", "http://127.0.0.1:5000", "https://localhost:5000"])
    }})

    # -- Translations -------------------------------------------------------
    translations = _load_translations()
    app.config['TRANSLATIONS'] = translations

    # -- CSRF & before_request ----------------------------------------------
    @app.before_request
    def before_request():
        app.jinja_env.globals.update(
            t=lambda key, **kw: _get_translation(translations, session.get('lang', 'en'), key, **kw),
            csrf_token=_generate_csrf_token
        )
        if request.method == "POST" and request.endpoint and not request.endpoint.startswith("auth."):
            if request.path in ('/api/beacon/register',) or request.path.startswith('/api/beacon/checkin/'):
                pass
            else:
                token = session.get('csrf_token')
                if not token or not secrets.compare_digest(token, request.headers.get('X-CSRFToken', '')):
                    if request.is_json or request.path.startswith('/api/'):
                        return jsonify({'status': 'error', 'message': 'CSRF token missing or incorrect.'}), 403
                    return "CSRF Error", 403

    # -- Extensions ---------------------------------------------------------
    from core.extensions import limiter
    if limiter:
        limiter.init_app(app)

    # -- Blueprints ---------------------------------------------------------
    _register_blueprints(app)

    # -- SocketIO -----------------------------------------------------------
    try:
        from routes.team_routes import team_bp, socketio as team_socketio, SOCKETIO_AVAILABLE
        if SOCKETIO_AVAILABLE and team_socketio:
            team_socketio.init_app(app)
            from core.logger import set_socketio_instance
            set_socketio_instance(team_socketio)

            def _heartbeat_callback(cpu, ram, ping_ms, ollama_online):
                try:
                    team_socketio.emit('heartbeat', {
                        'cpu': cpu, 'ram': ram, 'ping': ping_ms, 'ollama': ollama_online,
                    })
                except Exception:
                    from core.logger import get_logger
                    get_logger('app').debug('Heartbeat callback emit failed', exc_info=True)

            from core.monitor import set_tick_callback
            set_tick_callback(_heartbeat_callback)
    except ImportError:
        pass

    # -- Routes (app-level) ------------------------------------------------
    from core.auth import login_required

    @app.route('/')
    @login_required
    def home():
        from core.db import get_db_stats
        from tools_config import TOOLS_CONFIG
        stats = get_db_stats()
        lang = session.get('lang', 'en')
        js_translations = translations.get(lang, {})
        return render_template('index.html', stats=stats, tools=TOOLS_CONFIG,
                               js_translations=js_translations, current_lang=lang)

    @app.route('/settings')
    @login_required
    def settings():
        return render_template('settings.html')

    @app.route('/api/set_lang', methods=['POST'])
    def set_lang():
        data = request.json
        lang = data.get('lang')
        if lang in translations:
            session['lang'] = lang
            return jsonify({'status': 'success'})
        return jsonify({'status': 'error'})

    @app.route('/api/auth/status', methods=['GET'])
    def check_auth_status():
        return jsonify({'logged_in': session.get('logged_in', False)})

    # -- Error handlers -----------------------------------------------------
    @app.errorhandler(ValueError)
    def handle_value_error(e):
        if request.path.startswith('/api/') or request.is_json:
            return jsonify({'status': 'error', 'message': f'Invalid input: {str(e)}'}), 400
        return render_template('login.html'), 400

    @app.errorhandler(Exception)
    def handle_exception(e):
        from werkzeug.exceptions import HTTPException
        # HTTPException'leri kendi durum koduyla döndür (404 → 404, 403 → 403)
        if isinstance(e, HTTPException):
            if request.path.startswith('/api/') or request.is_json:
                return jsonify({'status': 'error', 'message': str(e)}), e.code
            return render_template('login.html'), e.code
        from core.logger import get_logger
        log = get_logger('flask')
        log.error(f'Unhandled exception: {e}', exc_info=True)
        if request.path.startswith('/api/') or request.is_json:
            return jsonify({'status': 'error', 'message': 'Internal server error'}), 500
        return render_template('login.html'), 500

    # -- Init services (lazy — call explicitly or via a dedicated method) ---
    app.extensions['_init_services'] = lambda: _init_services(app)
    app.extensions['_services_initialized'] = False

    return app


def init_services(app):
    """Initialize databases, logging, and monitoring. Call once per process."""
    if app.extensions.get('_services_initialized'):
        return
    from core.db import init_db, init_c2_tables
    from core.logger import init_logging
    from core.monitor import start_monitor

    with app.app_context():
        init_db()
        init_c2_tables()
        init_logging(app)
        start_monitor()

    app.extensions['_services_initialized'] = True


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

class DefaultConfig:
    DEBUG = False
    TESTING = False
    CORS_ORIGINS = ["http://localhost:5000", "http://127.0.0.1:5000", "https://localhost:5000"]


class TestConfig(DefaultConfig):
    TESTING = True
    DEBUG = True
    SESSION_COOKIE_SECURE = False


_config_map = {
    'default': DefaultConfig,
    'test': TestConfig,
}


def _generate_and_save_secret(key_name, length=16):
    import os
    import secrets
    secret = secrets.token_hex(length)
    try:
        from dotenv import set_key as _dotenv_set_key
        _dotenv_set_key('.env', key_name, secret)
    except Exception:
        pass
    return secret


def _save_admin_password_file(password):
    import os
    try:
        pw_file = 'admin_password_initial.txt'
        with open(pw_file, 'w') as f:
            f.write(password)
        os.chmod(pw_file, 0o600)
        print(f"\n[!] Initial admin password saved to {pw_file} — store it securely and delete this file.\n")
    except Exception:
        pass


def _load_translations():
    import os
    import json
    translations = {}
    lang_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'translations')
    if os.path.exists(lang_dir):
        for file in os.listdir(lang_dir):
            if file.endswith('.json'):
                lang_code = file.split('.')[0]
                with open(os.path.join(lang_dir, file), 'r', encoding='utf-8') as f:
                    translations[lang_code] = json.load(f)
    return translations


def _get_translation(translations, lang, key, **kwargs):
    text = translations.get(lang, {}).get(key, key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError:
            pass
    return text


def _generate_csrf_token():
    import secrets
    from flask import session
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(32)
    return session['csrf_token']


def _register_blueprints(app):
    # Her blueprint import'u bağımsız try/except ile korunuyor
    # Böylece tek bir eksik modül tüm uygulamayı çökertmez
    blueprints = []

    def _try_import(module_path, bp_name):
        try:
            mod = __import__(module_path, fromlist=[bp_name])
            bp = getattr(mod, bp_name)
            blueprints.append(bp)
        except Exception:
            pass  # Best-effort: eksik modül sessizce atlanır

    _try_import("routes.auth_routes", "auth_bp")
    _try_import("routes.api_routes", "api_bp")
    _try_import("routes.action_routes", "action_bp")
    _try_import("routes.wsl_routes", "api_wsl_bp")
    _try_import("routes.ai_routes", "ai_bp")
    _try_import("routes.rag_loki_routes", "rag_loki_bp")
    _try_import("routes.c2_routes", "c2_bp")
    _try_import("routes.msf_routes", "msf_bp")
    _try_import("routes.graph_routes", "graph_bp")
    _try_import("routes.beacon_routes", "beacon_bp")
    _try_import("routes.evasion_routes", "evasion_bp")
    _try_import("routes.log_routes", "log_bp")
    _try_import("routes.ops_routes", "ops_bp")
    _try_import("routes.team_routes", "team_bp")

    for bp in blueprints:
        try:
            app.register_blueprint(bp)
        except Exception:
            pass


def _init_services(app):
    init_services(app)
