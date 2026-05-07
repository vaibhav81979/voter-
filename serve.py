from waitress import serve
from app import create_app
from models import db
import os

def start_server():
    app = create_app()
    
    with app.app_context():
        # Ensure database is ready
        db.create_all()
        try:
            from init_db import init_database
            init_database()
        except Exception:
            pass

    print("\n" + "=" * 55)
    print("  [OK] PRODUCTION SERVER (WAITRESS) IS STARTING")
    print("=" * 55)
    print("  URL        : http://localhost:8080")
    print("  Admin      : http://localhost:8080/admin/login")
    print("  Mode       : Production / Stable")
    print("=" * 55 + "\n")

    # Serve the app using waitress on port 8080
    serve(app, host='0.0.0.0', port=8080, threads=6)

if __name__ == "__main__":
    start_server()
