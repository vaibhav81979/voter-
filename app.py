"""
National E-Voting Portal – Flask Application Entry Point
"""

import os
from flask import Flask
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import Config
from models import db
from flask_socketio import SocketIO
from threading import Lock

socketio = SocketIO(cors_allowed_origins="*")
thread = None
thread_lock = Lock()

def background_analytics_thread(app):
    """Push real-time turnout analytics every 5 seconds [cite: 48, 62]"""
    with app.app_context():
        from models import Voter, Vote
        while True:
            socketio.sleep(5)
            try:
                total_voters = Voter.query.count()
                total_votes = Vote.query.count()
                turnout = round((total_votes / total_voters * 100), 1) if total_voters > 0 else 0
                
                socketio.emit('analytics_update', {
                    'total_voters': total_voters,
                    'total_votes': total_votes,
                    'turnout': turnout
                }, namespace='/admin')
            except Exception as e:
                pass


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure directories exist
    os.makedirs(app.config.get("UPLOAD_FOLDER", "uploads"), exist_ok=True)
    os.makedirs(os.path.join(app.instance_path), exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    socketio.init_app(app)

    csrf = CSRFProtect(app)

    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=[app.config.get("RATELIMIT_DEFAULT", "100 per hour")],
        storage_uri=app.config.get("RATELIMIT_STORAGE_URI", "memory://"),
    )

    # Exempt API endpoints from CSRF (they use JSON)
    from routes.voter import voter_bp
    from routes.admin import admin_bp

    csrf.exempt(voter_bp)
    csrf.exempt(admin_bp)

    app.register_blueprint(voter_bp)
    app.register_blueprint(admin_bp)

    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return """
        <div style="text-align:center;padding:80px;font-family:sans-serif;">
            <h1 style="color:#ff9933;font-size:48px;">404</h1>
            <p>Page not found.</p>
            <a href="/" style="color:#ff9933;">Return to Home</a>
        </div>
        """, 404

    @app.errorhandler(500)
    def server_error(e):
        return """
        <div style="text-align:center;padding:80px;font-family:sans-serif;">
            <h1 style="color:#ff9933;font-size:48px;">500</h1>
            <p>Internal server error. Please try again later.</p>
            <a href="/" style="color:#ff9933;">Return to Home</a>
        </div>
        """, 500

    @socketio.on('connect', namespace='/admin')
    def admin_connect():
        global thread
        with thread_lock:
            if thread is None:
                thread = socketio.start_background_task(background_analytics_thread, app._get_current_object())

    return app


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        db.create_all()
    # Use socketio.run instead of app.run
    socketio.run(app, debug=True, host="0.0.0.0", port=8080, allow_unsafe_werkzeug=True)
