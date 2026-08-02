"""
Yggdrasil Security Framework — Main entry point

Backward-compatible wrapper around the application factory.
Legacy code that does ``from app import app`` will continue to work.
"""
import os
import logging
import threading
import webbrowser

from yggapp import create_app, init_services

# ---------------------------------------------------------------------------
# Build the application via the factory
# ---------------------------------------------------------------------------
app = create_app()

# ---------------------------------------------------------------------------
# One-time service init (db, logging, monitor) — only when run directly
# ---------------------------------------------------------------------------
init_services(app)

# ---------------------------------------------------------------------------
# Main entry-point
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    from routes.team_routes import SOCKETIO_AVAILABLE, socketio as team_socketio

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
    # Default to localhost — user must explicitly set FLASK_HOST=0.0.0.0 for network exposure
    flask_host = os.environ.get('FLASK_HOST', '127.0.0.1')

    # SSL/TLS support — set SSL_CERT_FILE and SSL_KEY_FILE env vars to enable HTTPS
    ssl_context = None
    ssl_cert = os.environ.get('SSL_CERT_FILE')
    ssl_key = os.environ.get('SSL_KEY_FILE')
    if ssl_cert and ssl_key and os.path.exists(ssl_cert) and os.path.exists(ssl_key):
        ssl_context = (ssl_cert, ssl_key)
        print(f"[+] SSL/TLS enabled — HTTPS active")
        if flask_host in ('127.0.0.1', 'localhost'):
            app.config['SESSION_COOKIE_SECURE'] = False
    else:
        app.config['SESSION_COOKIE_SECURE'] = False

    flask_port = int(os.environ.get('FLASK_PORT', 5000))
    if SOCKETIO_AVAILABLE and team_socketio:
        print(f"[+] SocketIO active — WebSocket real-time mode enabled (host: {flask_host}:{flask_port})")
        team_socketio.run(app, host=flask_host, port=flask_port, debug=False, ssl_context=ssl_context, allow_unsafe_werkzeug=True)
    else:
        print(f"[!] SocketIO not available — falling back to polling mode (host: {flask_host}:{flask_port})")
        app.run(host=flask_host, port=flask_port, debug=False, threaded=True, ssl_context=ssl_context)
