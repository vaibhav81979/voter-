"""
Authentication helpers: password hashing, JWT tokens, OTP generation.
"""

import random
import string
import hashlib
from datetime import datetime, timedelta, timezone
from functools import wraps

import bcrypt
import jwt
from flask import request, jsonify, session, redirect, url_for, flash


# ---------------------------------------------------------------------------
# Password Hashing
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against a bcrypt hash."""
    return bcrypt.checkpw(password.encode(), hashed.encode())


# ---------------------------------------------------------------------------
# JWT Tokens
# ---------------------------------------------------------------------------

def generate_token(user_id: int, role: str, secret: str, expiry_hours: int = 2) -> str:
    """Generate a JWT token for authenticated sessions."""
    payload = {
        "user_id": user_id,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=expiry_hours),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_token(token: str, secret: str) -> dict | None:
    """Decode and validate a JWT token. Returns payload or None."""
    try:
        return jwt.decode(token, secret, algorithms=["HS256"])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


# ---------------------------------------------------------------------------
# OTP
# ---------------------------------------------------------------------------

def generate_otp(length: int = 6) -> str:
    """Generate a random numeric OTP."""
    return "".join(random.choices(string.digits, k=length))


def hash_otp(otp: str) -> str:
    """Hash OTP for secure storage."""
    return hashlib.sha256(otp.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Decorators
# ---------------------------------------------------------------------------

def login_required(f):
    """Decorator that checks for a valid voter session."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "voter_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("voter.login"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Decorator that checks for a valid admin session."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "admin_id" not in session:
            flash("Admin access required.", "warning")
            return redirect(url_for("admin.admin_login"))
        return f(*args, **kwargs)
    return decorated


def face_verified_required(f):
    """Decorator that checks if the voter has completed face verification."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("face_verified"):
            flash("Face verification required before voting.", "warning")
            return redirect(url_for("voter.login"))
        return f(*args, **kwargs)
    return decorated
