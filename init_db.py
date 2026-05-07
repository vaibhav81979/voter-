"""
Database initialization script.
Creates tables and seeds demo data for testing.
"""

from datetime import datetime, timezone, timedelta
from app import create_app
from models import db, Voter, Admin, Election, Candidate, FraudAlert
from auth import hash_password
from encryption import DataEncryptor


def init_database():
    app = create_app()

    with app.app_context():
        # Create all tables
        db.create_all()
        print("[OK] Database tables created.")

        enc = DataEncryptor(app.config["AES_KEY"])

        # ---- Seed Admin ----
        if not Admin.query.filter_by(username="admin").first():
            admin = Admin(
                username="admin",
                password_hash=hash_password("admin123"),
                name="Amit Sharma",
                role="chief",
            )
            db.session.add(admin)
            print("[OK] Admin account created: admin / admin123")

        # ---- Seed Election ----
        if not Election.query.first():
            election = Election(
                name="General Election to the Lok Sabha 2024",
                description="Phase 4 of 7 — Nation-wide electronic voting",
                start_date=datetime(2024, 5, 1, tzinfo=timezone.utc),
                end_date=datetime(2024, 6, 30, tzinfo=timezone.utc),
                is_active=True,
            )
            db.session.add(election)
            db.session.flush()  # Get the election ID

            # ---- Seed Candidates ----
            candidates = [
                Candidate(
                    name="Rajesh Kumar Jha",
                    party="Bharatiya Janata Party",
                    party_short="BJP",
                    symbol_icon="local_fire_department",
                    constituency="New Delhi",
                    election_id=election.id,
                    votes_count=1452109,
                ),
                Candidate(
                    name="Sanjay Kumar Singh",
                    party="Indian National Congress",
                    party_short="INC",
                    symbol_icon="pan_tool",
                    constituency="New Delhi",
                    election_id=election.id,
                    votes_count=1207078,
                ),
                Candidate(
                    name="Priya Agarwal",
                    party="Aam Aadmi Party",
                    party_short="AAP",
                    symbol_icon="cleaning_services",
                    constituency="New Delhi",
                    election_id=election.id,
                    votes_count=892301,
                ),
                Candidate(
                    name="Vikram Patel",
                    party="Bahujan Samaj Party",
                    party_short="BSP",
                    symbol_icon="pets",
                    constituency="New Delhi",
                    election_id=election.id,
                    votes_count=293300,
                ),
                Candidate(
                    name="Meena Devi",
                    party="Independent",
                    party_short="IND",
                    symbol_icon="emoji_objects",
                    constituency="New Delhi",
                    election_id=election.id,
                    votes_count=145021,
                ),
                Candidate(
                    name="NOTA",
                    party="None of the Above",
                    party_short="NOTA",
                    symbol_icon="block",
                    constituency="New Delhi",
                    election_id=election.id,
                    votes_count=0,
                ),
            ]
            db.session.add_all(candidates)
            print(f"[OK] {len(candidates)} candidates seeded.")

        # ---- Seed Sample Voter ----
        if not Voter.query.filter_by(epic_number="ABC1234567").first():
            voter = Voter(
                epic_number="ABC1234567",
                full_name="Rahul Sharma",
                dob=datetime(1990, 5, 15).date(),
                aadhaar_encrypted=enc.encrypt("123456789012"),
                aadhaar_hash=enc.hash_value("123456789012"),
                phone="9876543210",
                constituency="New Delhi",
                village="Connaught Place",
                is_verified=True,
            )
            db.session.add(voter)
            print("[OK] Sample voter created: EPIC=ABC1234567")

        # ---- Seed Fraud Alerts ----
        if not FraudAlert.query.first():
            alerts = [
                FraudAlert(
                    alert_type="duplicate_epic",
                    constituency="Lucknow East",
                    detail="EPIC: ABC1234567 — Duplicate registration attempt detected",
                    risk_level="critical",
                ),
                FraudAlert(
                    alert_type="face_auth_failure",
                    constituency="Varanasi Cantt.",
                    detail="Device: VVPAT-0822 — Multiple failed face authentication attempts",
                    risk_level="high",
                ),
                FraudAlert(
                    alert_type="duplicate_epic",
                    constituency="Amethi",
                    detail="EPIC: XYZ7890123 — Same Aadhaar linked to multiple EPICs",
                    risk_level="critical",
                ),
            ]
            db.session.add_all(alerts)
            print(f"[OK] {len(alerts)} fraud alerts seeded.")

        db.session.commit()
        print("\n[DONE] Database initialized successfully!")
        print("=" * 50)
        print("Demo Credentials:")
        print("  Admin:  admin / admin123")
        print("  Voter:  EPIC = ABC1234567")
        print("=" * 50)


if __name__ == "__main__":
    init_database()
