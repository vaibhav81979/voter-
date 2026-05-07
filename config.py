import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Try to load .env file for stable keys
_env_file = os.path.join(BASE_DIR, ".env")
if os.path.exists(_env_file):
    with open(_env_file) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

# If no .env exists, generate stable keys and write them once
def _ensure_env():
    """Generate stable keys and persist them to .env so they survive restarts."""
    import secrets
    keys = {}
    needed = ["SECRET_KEY", "JWT_SECRET", "AES_KEY"]
    for k in needed:
        if not os.environ.get(k):
            keys[k] = secrets.token_hex(32) if k != "AES_KEY" else secrets.token_hex(16)
            os.environ[k] = keys[k]
    if keys:
        with open(_env_file, "a") as f:
            for k, v in keys.items():
                f.write(f"{k}={v}\n")

_ensure_env()


class Config:
    # Flask
    SECRET_KEY = os.environ.get("SECRET_KEY")

    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'evoting.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT
    JWT_SECRET = os.environ.get("JWT_SECRET")
    JWT_EXPIRY_HOURS = 2

    # AES Encryption — stable key required for Aadhaar decryption
    AES_KEY = os.environ.get("AES_KEY")

    # Rate Limiting
    RATELIMIT_DEFAULT = "200 per hour"
    RATELIMIT_STORAGE_URI = "memory://"

    # Uploads
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

    # OTP
    OTP_EXPIRY_MINUTES = 5

    # Session
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

