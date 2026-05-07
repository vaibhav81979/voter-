"""
National E-Voting Portal — One-Click Launcher
Run with:  python run.py
"""

from app import create_app, socketio
from models import db


def main():
    app = create_app()

    with app.app_context():
        # Create tables if they don't exist yet
        db.create_all()

        # Auto-seed demo data (safe — checks before inserting)
        try:
            from init_db import init_database
            init_database()
        except Exception as e:
            # init_database creates its own app context; just ensure tables exist
            print(f"[INFO] Seeding skipped (already done or error: {e})")

    print("\n" + "=" * 55)
    print("  [READY] National E-Voting Portal is RUNNING!")
    print("=" * 55)
    print("  URL        : http://localhost:8080")
    print("  Admin      : http://localhost:8080/admin/login")
    print("  Admin creds: admin / admin123")
    print("  Demo voter : EPIC = ABC1234567")
    print("=" * 55 + "\n")

    socketio.run(app, debug=True, host="0.0.0.0", port=8080, use_reloader=False, allow_unsafe_werkzeug=True)


if __name__ == "__main__":
    main()
