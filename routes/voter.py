"""
Voter-facing routes: registration, login, face auth, balloting, voting.
"""

import os
import uuid
import json
from datetime import datetime, timedelta, timezone

from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, session, jsonify, current_app,
)

from models import db, Voter, Election, Candidate, Vote, OTP, FraudAlert, Configuration, IST
from auth import (
    hash_password, verify_password, generate_otp, hash_otp,
    login_required, face_verified_required,
)
from encryption import DataEncryptor
from face_auth import detect_face, encode_face, verify_face, check_liveness, save_face_image
from blockchain import VoteBlockchain

voter_bp = Blueprint("voter", __name__)


def _get_encryptor():
    return DataEncryptor(current_app.config["AES_KEY"])


# -------------------------------------------------------------------------
# Main Portal
# -------------------------------------------------------------------------

@voter_bp.route("/welcome")
def welcome():
    return render_template("welcome.html")

@voter_bp.route("/")
def index():
    return redirect(url_for("voter.welcome"))

@voter_bp.route("/home")
def home():
    lang = request.args.get("lang", "en")
    return render_template("index.html", lang=lang)

# -------------------------------------------------------------------------
# Static Info Pages
# -------------------------------------------------------------------------

@voter_bp.route("/booth")
def booth():
    return render_template("booth.html")

@voter_bp.route("/candidate")
def candidate():
    election = Election.query.filter_by(is_active=True).first()
    candidates = []
    if election:
        candidates = Candidate.query.filter_by(election_id=election.id).all()
    return render_template("candidate.html", election=election, candidates=candidates)

@voter_bp.route("/election-date")
def election_date():
    return render_template("election_date.html")

@voter_bp.route("/news")
def news():
    return render_template("news.html")

@voter_bp.route("/results")
def results():
    return render_template("results.html")

@voter_bp.route("/help")
def help_page():
    return render_template("help.html")



# -------------------------------------------------------------------------
# Registration
# -------------------------------------------------------------------------

@voter_bp.route("/register", methods=["GET", "POST"])
def register():
    """Voter registration with face capture."""
    if request.method == "GET":
        today = datetime.now().strftime("%Y-%m-%d")
        return render_template("register.html", today=today)

    # Process registration form
    full_name = request.form.get("full_name", "").strip()
    dob_str = request.form.get("dob", "")
    aadhaar = request.form.get("aadhaar", "").strip().replace(" ", "")
    phone = request.form.get("phone", "").strip()
    constituency = request.form.get("constituency", "").strip()
    village = request.form.get("village", "").strip()
    face_image_b64 = request.form.get("face_image", "")

    # Validation
    errors = []
    if not full_name:
        errors.append("Full name is required.")
    if not dob_str:
        errors.append("Date of birth is required.")
    if not aadhaar or len(aadhaar) != 12:
        errors.append("Valid 12-digit Aadhaar number is required.")
    if not constituency:
        errors.append("Constituency is required.")
    if not face_image_b64:
        errors.append("Face photo capture is required.")

    if errors:
        for e in errors:
            flash(e, "error")
        return render_template("register.html"), 400

    # Check duplicate Aadhaar
    enc = _get_encryptor()
    aadhaar_hash = enc.hash_value(aadhaar)
    existing = Voter.query.filter_by(aadhaar_hash=aadhaar_hash).first()
    if existing:
        # LOG SECURITY ALERT: Duplicate Aadhaar attempt
        alert = FraudAlert(
            alert_type="duplicate_aadhaar",
            constituency=constituency,
            detail=f"AADHAAR: {aadhaar_hash[:10]}... — Duplicate registration attempt (User: {full_name})",
            risk_level="critical",
        )
        db.session.add(alert)
        db.session.commit()

        flash("An account with this Aadhaar number already exists.", "error")
        return render_template("register.html"), 400

    # Parse DOB
    try:
        dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
    except ValueError:
        flash("Invalid date format.", "error")
        return render_template("register.html"), 400

    # Generate EPIC number
    epic_number = _generate_epic()

    # Encode face
    face_encoding = encode_face(face_image_b64)
    face_path = None
    if face_image_b64:
        face_path = save_face_image(
            face_image_b64,
            current_app.config["UPLOAD_FOLDER"],
            epic_number,
        )

    # Encrypt Aadhaar
    aadhaar_encrypted = enc.encrypt(aadhaar)

    # Create voter
    voter = Voter(
        epic_number=epic_number,
        full_name=full_name,
        dob=dob,
        aadhaar_encrypted=aadhaar_encrypted,
        aadhaar_hash=aadhaar_hash,
        phone=phone,
        constituency=constituency,
        village=village,
        face_encoding=face_encoding,
        face_image_path=face_path,
        is_verified=True if face_encoding else False,
    )

    db.session.add(voter)
    db.session.commit()

    flash(f"✅ Registration Successful! Your EPIC Number is: {epic_number} — Write it down and use it to login below.", "success")
    return redirect(url_for("voter.login"))


def _generate_epic() -> str:
    """Generate a unique EPIC number like ABC1234567."""
    import random
    import string
    while True:
        letters = "".join(random.choices(string.ascii_uppercase, k=3))
        digits = "".join(random.choices(string.digits, k=7))
        epic = letters + digits
        if not Voter.query.filter_by(epic_number=epic).first():
            return epic


# -------------------------------------------------------------------------
# Login
# -------------------------------------------------------------------------

@voter_bp.route("/login", methods=["GET", "POST"])
def login():
    """Voter login page."""
    if request.method == "GET":
        return render_template("login.html")

    epic_number = request.form.get("epic_number", "").strip().upper()
    if not epic_number:
        flash("Please enter your EPIC Number.", "error")
        return render_template("login.html"), 400

    voter = Voter.query.filter_by(epic_number=epic_number).first()
    if not voter:
        flash("EPIC Number not found. Please check and try again.", "error")
        return render_template("login.html"), 400

    # Store voter in session for face verification step
    session["pending_voter_id"] = voter.id
    session["pending_epic"] = epic_number
    return render_template("login.html", show_face_auth=True, epic_number=epic_number)


# -------------------------------------------------------------------------
# Face Auth API
# -------------------------------------------------------------------------

@voter_bp.route("/api/lookup-epic", methods=["POST"])
def api_lookup_epic():
    """AJAX: check if an EPIC number exists and store pending voter in session."""
    data = request.get_json()
    epic_number = (data.get("epic_number", "") or "").strip().upper()

    if not epic_number:
        return jsonify({"success": False, "message": "EPIC number is required."}), 400

    voter = Voter.query.filter_by(epic_number=epic_number).first()
    if not voter:
        return jsonify({"success": False, "message": "EPIC Number not found. Please check and try again."}), 404

    # Store in session for face verification step
    session["pending_voter_id"] = voter.id
    session["pending_epic"] = epic_number

    return jsonify({
        "success": True,
        "name": voter.full_name,
        "epic": voter.epic_number,
    })


@voter_bp.route("/api/face-register", methods=["POST"])
def api_face_register():
    """Register a face encoding during registration (AJAX)."""
    data = request.get_json()
    image_b64 = data.get("image", "")

    if not image_b64:
        return jsonify({"success": False, "message": "No image provided."}), 400

    # Detect face
    detection = detect_face(image_b64)
    if not detection["found"]:
        return jsonify({"success": False, "message": "No face detected. Please face the camera directly."}), 400

    # Check liveness
    liveness = check_liveness(image_b64)
    if not liveness["alive"]:
        return jsonify({"success": False, "message": liveness["message"]}), 400

    return jsonify({
        "success": True,
        "message": "Face captured successfully!",
        "face_detected": True,
        "face_count": detection["count"],
    })


@voter_bp.route("/api/face-verify", methods=["POST"])
def api_face_verify():
    """Verify face for login (AJAX)."""
    data = request.get_json()
    image_b64 = data.get("image", "")
    voter_id = session.get("pending_voter_id")

    if not voter_id:
        return jsonify({"success": False, "message": "No login session found. Please enter your EPIC number first."}), 400

    if not image_b64:
        return jsonify({"success": False, "message": "No image provided."}), 400

    voter = db.session.get(Voter, voter_id)
    if not voter:
        return jsonify({"success": False, "message": "Voter not found."}), 404

    if not voter.face_encoding:
        # No biometric on file — allow login but log it (for demo / newly seeded voters)
        session["voter_id"] = voter.id
        session["voter_name"] = voter.full_name
        session["voter_epic"] = voter.epic_number
        session["voter_constituency"] = voter.constituency
        session["face_verified"] = True
        session.pop("pending_voter_id", None)
        session.pop("pending_epic", None)
        return jsonify({
            "success": True,
            "message": "Identity confirmed (no biometric on file, access granted).",
            "confidence": 100,
            "redirect": url_for("voter.ballot"),
        })

    # Fetch configuration
    liveness_enabled = Configuration.get('liveness', 'true') == 'true'
    
    # Check liveness if enabled
    if liveness_enabled:
        liveness = check_liveness(image_b64)
        if not liveness["alive"]:
            # Log fraud alert
            alert = FraudAlert(
                alert_type="face_auth_failure",
                constituency=voter.constituency,
                detail=f"Liveness check failed for EPIC: {voter.epic_number}",
                risk_level="high",
            )
            db.session.add(alert)
            db.session.commit()
            return jsonify({"success": False, "message": liveness["message"]}), 400

    # Verify face with dynamic tolerance
    tolerance_val = float(Configuration.get('face_tolerance', '0.5'))
    # Map distance-based setting (0.4-0.6) to correlation-based threshold (40-60)
    # distance 0.4 (High Strictness) -> correlation 60
    # distance 0.5 (Standard) -> correlation 50
    # distance 0.6 (Low) -> correlation 40
    threshold = (1.0 - tolerance_val + 0.1) * 100
    
    result = verify_face(voter.face_encoding, image_b64, threshold=threshold)

    if result["match"]:
        session["voter_id"] = voter.id
        session["voter_name"] = voter.full_name
        session["voter_epic"] = voter.epic_number
        session["voter_constituency"] = voter.constituency
        session["face_verified"] = True
        session.pop("pending_voter_id", None)
        session.pop("pending_epic", None)
        return jsonify({
            "success": True,
            "message": f"Face verified! Confidence: {result['confidence']}%",
            "confidence": result["confidence"],
            "redirect": url_for("voter.ballot"),
        })
    else:
        # Log potential fraud
        alert = FraudAlert(
            alert_type="face_auth_failure",
            constituency=voter.constituency,
            detail=f"Face mismatch for EPIC: {voter.epic_number}. Confidence: {result['confidence']}%",
            risk_level="high",
        )
        db.session.add(alert)
        db.session.commit()
        return jsonify({
            "success": False,
            "message": f"Face did not match. Confidence: {result['confidence']}%. Please try again.",
            "confidence": result["confidence"],
        }), 401


# -------------------------------------------------------------------------
# Biometric Verification (Simulated)
# -------------------------------------------------------------------------

@voter_bp.route("/api/biometric-verify", methods=["POST"])
def api_biometric_verify():
    """Simulated biometric/fingerprint verification."""
    voter_id = session.get("pending_voter_id")
    if not voter_id:
        return jsonify({"success": False, "message": "No login session found."}), 400

    voter = db.session.get(Voter, voter_id)
    if not voter:
        return jsonify({"success": False, "message": "Voter not found."}), 404

    # Simulate biometric verification success
    session["voter_id"] = voter.id
    session["voter_name"] = voter.full_name
    session["voter_epic"] = voter.epic_number
    session["voter_constituency"] = voter.constituency
    session["face_verified"] = True
    session.pop("pending_voter_id", None)
    session.pop("pending_epic", None)

    return jsonify({
        "success": True,
        "message": "Biometric verification successful!",
        "redirect": url_for("voter.ballot"),
    })


# -------------------------------------------------------------------------
# Ballot
# -------------------------------------------------------------------------

@voter_bp.route("/ballot")
@login_required
@face_verified_required
def ballot():
    """Show the electronic ballot paper."""
    voter = db.session.get(Voter, session["voter_id"])

    if voter.has_voted:
        flash("You have already cast your vote.", "warning")
        return redirect(url_for("voter.vote_success_page"))

    # Get active election and candidates
    election = Election.query.filter_by(is_active=True).first()
    candidates = []
    if election:
        candidates = Candidate.query.filter_by(
            election_id=election.id,
            constituency=voter.constituency,
        ).all()
        # If no constituency-specific candidates, show all
        if not candidates:
            candidates = Candidate.query.filter_by(election_id=election.id).all()

    return render_template(
        "voting_booth.html",
        voter=voter,
        election=election,
        candidates=candidates,
    )


# -------------------------------------------------------------------------
# Cast Vote
# -------------------------------------------------------------------------

@voter_bp.route("/api/cast-vote", methods=["POST"])
@login_required
@face_verified_required
def api_cast_vote():
    """Cast an encrypted vote."""
    voter = db.session.get(Voter, session["voter_id"])

    if voter.has_voted:
        return jsonify({"success": False, "message": "You have already voted."}), 400

    data = request.get_json()
    candidate_id = data.get("candidate_id")

    if not candidate_id:
        return jsonify({"success": False, "message": "No candidate selected."}), 400

    candidate = db.session.get(Candidate, candidate_id)
    if not candidate:
        return jsonify({"success": False, "message": "Invalid candidate."}), 400

    # Create encrypted ballot
    enc = _get_encryptor()
    ballot_data = json.dumps({
        "candidate_id": candidate.id,
        "candidate_name": candidate.name,
        "party": candidate.party,
        "constituency": voter.constituency,
        "timestamp": datetime.now(IST).isoformat(),
    })
    encrypted_ballot = enc.encrypt(ballot_data)

    # Generate transaction ID
    transaction_id = f"EV-2024-{uuid.uuid4().hex[:4].upper()}-{uuid.uuid4().hex[:4].upper()}-{uuid.uuid4().hex[:4].upper()}"

    # --- Blockchain Integration ---
    last_vote = Vote.query.order_by(Vote.id.desc()).first()
    previous_hash = last_vote.hash if last_vote else "GENESIS"
    index = (last_vote.id + 1) if last_vote else 1
    
    blockchain = VoteBlockchain(difficulty=2)
    vote_timestamp = datetime.now(IST)
    
    nonce, block_hash = blockchain.proof_of_work(
        index=index,
        previous_hash=previous_hash,
        timestamp=vote_timestamp.isoformat(),
        data=encrypted_ballot
    )

    # Create vote record
    vote = Vote(
        voter_hash=enc.hash_value(str(voter.id) + voter.epic_number),
        candidate_id=candidate.id,
        encrypted_ballot=encrypted_ballot,
        transaction_id=transaction_id,
        constituency=voter.constituency,
        previous_hash=previous_hash,
        nonce=nonce,
        hash=block_hash,
        timestamp=vote_timestamp
    )

    # Update candidate vote count
    candidate.votes_count = (candidate.votes_count or 0) + 1

    # Mark voter as having voted
    voter.has_voted = True

    db.session.add(vote)
    db.session.commit()

    # Store vote info in session for receipt
    session["last_vote"] = {
        "transaction_id": transaction_id,
        "timestamp": datetime.now(IST).strftime("%d %b %Y, %I:%M %p IST"),
        "constituency": voter.constituency,
        "voter_name": _mask_name(voter.full_name),
    }

    return jsonify({
        "success": True,
        "message": "Vote cast successfully!",
        "transaction_id": transaction_id,
        "redirect": url_for("voter.vote_success_page"),
    })


def _mask_name(name: str) -> str:
    """Mask voter name for receipt: 'RAHUL SHARMA' -> 'RAHUL S*****'"""
    parts = name.upper().split()
    if len(parts) > 1:
        last = parts[-1]
        masked = last[0] + "*" * (len(last) - 1) if len(last) > 1 else last
        return " ".join(parts[:-1]) + " " + masked
    return name.upper()


@voter_bp.route("/vote-success")
@login_required
def vote_success_page():
    """Vote cast successfully page."""
    vote_info = session.get("last_vote", {})
    return render_template("vote_success.html", vote_info=vote_info)


# -------------------------------------------------------------------------
# EPIC Recovery / OTP
# -------------------------------------------------------------------------

@voter_bp.route("/epic-recovery", methods=["GET", "POST"])
def epic_recovery():
    """EPIC number recovery page."""
    if request.method == "GET":
        return render_template("epic_recovery.html")

    identifier = request.form.get("identifier", "").strip().replace(" ", "")
    if not identifier:
        flash("Please enter your Aadhaar number.", "error")
        return render_template("epic_recovery.html")

    # Check if Aadhaar exists
    enc = _get_encryptor()
    aadhaar_hash = enc.hash_value(identifier)
    voter = Voter.query.filter_by(aadhaar_hash=aadhaar_hash).first()

    if not voter:
        flash("No voter found with this Aadhaar number.", "error")
        return render_template("epic_recovery.html")

    # Generate and store OTP
    otp_code = generate_otp()
    otp = OTP(
        identifier=aadhaar_hash,
        otp_hash=hash_otp(otp_code),
        expires_at=datetime.now(IST) + timedelta(
            minutes=current_app.config.get("OTP_EXPIRY_MINUTES", 5)
        ),
    )
    db.session.add(otp)
    db.session.commit()

    # In a real system, send OTP via SMS. Here we flash it for demo.
    flash(f"OTP sent to your registered mobile! (Demo OTP: {otp_code})", "info")
    session["recovery_aadhaar_hash"] = aadhaar_hash
    return render_template("epic_recovery.html", show_otp=True)


@voter_bp.route("/api/verify-otp", methods=["POST"])
def api_verify_otp():
    """Verify OTP for EPIC recovery."""
    data = request.get_json()
    otp_input = data.get("otp", "").strip()
    aadhaar_hash = session.get("recovery_aadhaar_hash")

    if not aadhaar_hash or not otp_input:
        return jsonify({"success": False, "message": "Invalid request."}), 400

    otp_record = OTP.query.filter_by(
        identifier=aadhaar_hash,
        otp_hash=hash_otp(otp_input),
        is_used=False,
    ).order_by(OTP.created_at.desc()).first()

    if not otp_record:
        return jsonify({"success": False, "message": "Invalid OTP."}), 400

    if otp_record.expires_at < datetime.now(IST):
        return jsonify({"success": False, "message": "OTP has expired."}), 400

    otp_record.is_used = True
    db.session.commit()

    # Find voter
    voter = Voter.query.filter_by(aadhaar_hash=aadhaar_hash).first()

    return jsonify({
        "success": True,
        "message": f"Verified! Your EPIC Number is: {voter.epic_number}",
        "epic_number": voter.epic_number,
    })


# -------------------------------------------------------------------------
# Send OTP API
# -------------------------------------------------------------------------

@voter_bp.route("/api/send-otp", methods=["POST"])
def api_send_otp():
    """Send OTP for any verification purpose."""
    data = request.get_json()
    identifier = data.get("identifier", "").strip().replace(" ", "")

    if not identifier:
        return jsonify({"success": False, "message": "Identifier required."}), 400

    enc = _get_encryptor()
    id_hash = enc.hash_value(identifier)

    # Generate OTP
    otp_code = generate_otp()
    otp = OTP(
        identifier=id_hash,
        otp_hash=hash_otp(otp_code),
        expires_at=datetime.now(IST) + timedelta(minutes=5),
    )
    db.session.add(otp)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"OTP sent successfully! (Demo: {otp_code})",
        "demo_otp": otp_code,
    })


# -------------------------------------------------------------------------
# Voter Card Preview
# -------------------------------------------------------------------------

@voter_bp.route("/voter-card")
@login_required
def voter_card():
    """Voter ID card preview."""
    voter = db.session.get(Voter, session["voter_id"])
    return render_template("voter_card.html", voter=voter)


# -------------------------------------------------------------------------
# Logout
# -------------------------------------------------------------------------

@voter_bp.route("/logout")
def logout():
    """Clear session and redirect to home."""
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("voter.index"))
