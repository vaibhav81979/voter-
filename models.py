"""
SQLAlchemy database models for the National E-Voting Portal.
"""

from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Voter(db.Model):
    __tablename__ = "voters"

    id = db.Column(db.Integer, primary_key=True)
    epic_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(200), nullable=False)
    dob = db.Column(db.Date, nullable=False)
    aadhaar_encrypted = db.Column(db.Text, nullable=False)       # AES encrypted
    aadhaar_hash = db.Column(db.String(64), nullable=False, index=True)  # SHA-256 for lookup
    phone = db.Column(db.String(15))
    constituency = db.Column(db.String(100), nullable=False)
    village = db.Column(db.String(100))
    face_encoding = db.Column(db.LargeBinary)                    # Stored face data
    face_image_path = db.Column(db.String(300))
    is_verified = db.Column(db.Boolean, default=False)
    has_voted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Voter {self.epic_number}>"


class Admin(db.Model):
    __tablename__ = "admins"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(30), default="officer")  # officer, chief
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class Election(db.Model):
    __tablename__ = "elections"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    candidates = db.relationship("Candidate", backref="election", lazy=True)


class Candidate(db.Model):
    __tablename__ = "candidates"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    party = db.Column(db.String(100), nullable=False)
    party_short = db.Column(db.String(20))
    symbol_icon = db.Column(db.String(50))           # Material icon name
    constituency = db.Column(db.String(100), nullable=False)
    election_id = db.Column(db.Integer, db.ForeignKey("elections.id"), nullable=False)
    votes_count = db.Column(db.Integer, default=0)
    details = db.Column(db.Text)


class Vote(db.Model):
    __tablename__ = "votes"

    id = db.Column(db.Integer, primary_key=True)
    voter_hash = db.Column(db.String(64), nullable=False)        # Hashed voter reference
    candidate_id = db.Column(db.Integer, nullable=False)
    encrypted_ballot = db.Column(db.Text, nullable=False)        # AES encrypted ballot data
    transaction_id = db.Column(db.String(50), unique=True, nullable=False)
    
    # Blockchain linkage fields
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    previous_hash = db.Column(db.String(64), nullable=False, default="GENESIS")
    nonce = db.Column(db.Integer, nullable=False, default=0)
    hash = db.Column(db.String(64), unique=True, nullable=False, default="GENESIS_HASH")
    
    constituency = db.Column(db.String(100))


class OTP(db.Model):
    __tablename__ = "otps"

    id = db.Column(db.Integer, primary_key=True)
    identifier = db.Column(db.String(100), nullable=False)       # Phone or EPIC
    otp_hash = db.Column(db.String(64), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class FraudAlert(db.Model):
    __tablename__ = "fraud_alerts"

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    alert_type = db.Column(db.String(50), nullable=False)        # duplicate_epic, face_auth_failure, etc.
    constituency = db.Column(db.String(100))
    detail = db.Column(db.Text)
    risk_level = db.Column(db.String(20), default="medium")      # low, medium, high, critical
    is_resolved = db.Column(db.Boolean, default=False)
