import eventlet
eventlet.monkey_patch()

from app import create_app, socketio
from models import db

app = create_app()

# Ensure DB tables exist
with app.app_context():
    db.create_all()
    try:
        from init_db import init_database
        init_database()
    except Exception as e:
        print(f"[INFO] DB seeding skipped: {e}")

# Expose the underlying Flask app as 'application' (WSGI convention)
application = app
