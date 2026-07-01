from app import create_app
from models import db, Admin
import bcrypt

app = create_app()
with app.app_context():
    admin = Admin.query.filter_by(username="admin").first()
    if admin:
        print(f"Admin found: {admin.username}")
        # Test password
        pwd = "admin123"
        match = bcrypt.checkpw(pwd.encode(), admin.password_hash.encode())
        print(f"Password 'admin123' match: {match}")
    else:
        print("Admin NOT found!")
