"""
Admin routes: dashboard, voter management, fraud alerts.
"""

from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, session, jsonify,
)

from models import db, Admin, Voter, Election, Candidate, Vote, FraudAlert
from auth import hash_password, verify_password, admin_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# -------------------------------------------------------------------------
# Admin Login
# -------------------------------------------------------------------------

@admin_bp.route("/login", methods=["GET", "POST"])
def admin_login():
    """Admin login page."""
    if request.method == "GET":
        return render_template("admin/login.html")

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    if not username or not password:
        flash("Username and password are required.", "error")
        return render_template("admin/login.html"), 400

    admin = Admin.query.filter_by(username=username).first()
    if not admin or not verify_password(password, admin.password_hash):
        flash("Invalid credentials.", "error")
        return render_template("admin/login.html"), 401

    session["admin_id"] = admin.id
    session["admin_name"] = admin.name
    session["admin_role"] = admin.role
    flash(f"Welcome, {admin.name}!", "success")
    return redirect(url_for("admin.dashboard"))


# -------------------------------------------------------------------------
# Dashboard
# -------------------------------------------------------------------------

@admin_bp.route("/dashboard")
@admin_required
def dashboard():
    """Admin dashboard with election stats."""
    # Sync candidate vote counts from real votes table
    from sqlalchemy import func
    vote_counts = db.session.query(
        Vote.candidate_id, func.count(Vote.id).label('cnt')
    ).group_by(Vote.candidate_id).all()
    count_map = {r.candidate_id: r.cnt for r in vote_counts}

    # Update cached votes_count to match real data
    all_candidates_sync = Candidate.query.all()
    for c in all_candidates_sync:
        c.votes_count = count_map.get(c.id, 0)
    db.session.commit()

    stats = _get_dashboard_stats()
    fraud_alerts = FraudAlert.query.order_by(
        FraudAlert.timestamp.desc()
    ).limit(10).all()

    # Get candidate performance sorted by real vote count
    election = Election.query.filter_by(is_active=True).first()
    candidates = []
    if election:
        candidates = Candidate.query.filter_by(
            election_id=election.id,
        ).order_by(Candidate.votes_count.desc()).all()

    return render_template(
        "admin/dashboard.html",
        stats=stats,
        fraud_alerts=fraud_alerts,
        candidates=candidates,
        election=election,
    )


def _get_dashboard_stats():
    """Compute dashboard statistics."""
    total_voters = Voter.query.count()
    total_votes = Vote.query.count()
    verified_voters = Voter.query.filter_by(is_verified=True).count()
    turnout = round((total_votes / total_voters * 100), 1) if total_voters > 0 else 0
    unresolved_alerts = FraudAlert.query.filter_by(is_resolved=False).count()

    return {
        "total_voters": total_voters,
        "total_votes": total_votes,
        "verified_voters": verified_voters,
        "turnout": turnout,
        "unresolved_alerts": unresolved_alerts,
    }


# -------------------------------------------------------------------------
# Voter Management
# -------------------------------------------------------------------------

@admin_bp.route("/voters")
@admin_required
def voters():
    """Voter list with verification status."""
    page = request.args.get("page", 1, type=int)
    search = request.args.get("search", "").strip()

    query = Voter.query
    if search:
        query = query.filter(
            (Voter.epic_number.ilike(f"%{search}%")) |
            (Voter.full_name.ilike(f"%{search}%")) |
            (Voter.constituency.ilike(f"%{search}%"))
        )

    pagination = query.order_by(Voter.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False,
    )

    return render_template(
        "admin/voters.html",
        voters=pagination.items,
        pagination=pagination,
        search=search,
    )


@admin_bp.route("/api/verify-voter/<int:voter_id>", methods=["POST"])
@admin_required
def verify_voter(voter_id):
    """Verify a voter."""
    voter = db.session.get(Voter, voter_id)
    if not voter:
        return jsonify({"success": False, "message": "Voter not found."}), 404

    voter.is_verified = True
    db.session.commit()
    return jsonify({"success": True, "message": f"Voter {voter.epic_number} verified."})


@admin_bp.route("/api/bulk-verify", methods=["POST"])
@admin_required
def bulk_verify():
    """Bulk verify selected voters."""
    data = request.get_json()
    voter_ids = data.get("voter_ids", [])

    if not voter_ids:
        return jsonify({"success": False, "message": "No voters selected."}), 400

    count = 0
    for vid in voter_ids:
        voter = db.session.get(Voter, vid)
        if voter and not voter.is_verified:
            voter.is_verified = True
            count += 1

    db.session.commit()
    return jsonify({"success": True, "message": f"{count} voters verified."})


# -------------------------------------------------------------------------
# Fraud Alerts
# -------------------------------------------------------------------------

@admin_bp.route("/fraud-alerts")
@admin_required
def fraud_alerts():
    """Fraud alert listing."""
    alerts = FraudAlert.query.order_by(
        FraudAlert.is_resolved.asc(),
        FraudAlert.timestamp.desc(),
    ).all()
    
    critical_count = FraudAlert.query.filter_by(risk_level='critical', is_resolved=False).count()
    high_risk_count = FraudAlert.query.filter_by(risk_level='high', is_resolved=False).count()
    total_unresolved = FraudAlert.query.filter_by(is_resolved=False).count()

    return render_template(
        "admin/fraud_alerts.html", 
        alerts=alerts,
        critical_count=critical_count,
        high_risk_count=high_risk_count,
        total_unresolved=total_unresolved
    )


@admin_bp.route("/api/resolve-alert/<int:alert_id>", methods=["POST"])
@admin_required
def resolve_alert(alert_id):
    """Mark a fraud alert as resolved."""
    alert = db.session.get(FraudAlert, alert_id)
    if not alert:
        return jsonify({"success": False, "message": "Alert not found."}), 404

    alert.is_resolved = True
    db.session.commit()
    return jsonify({"success": True, "message": "Alert resolved."})


# -------------------------------------------------------------------------
# Admin API for dashboard data
# -------------------------------------------------------------------------

@admin_bp.route("/api/stats")
@admin_required
def api_stats():
    """Dashboard statistics JSON."""
    stats = _get_dashboard_stats()
    return jsonify(stats)


@admin_bp.route("/api/election-results")
@admin_required
def api_election_results():
    """Election results data."""
    election = Election.query.filter_by(is_active=True).first()
    if not election:
        return jsonify({"candidates": []})

    candidates = Candidate.query.filter_by(
        election_id=election.id,
    ).order_by(Candidate.votes_count.desc()).all()

    total_votes = sum(c.votes_count or 0 for c in candidates)

    return jsonify({
        "election": election.name,
        "total_votes": total_votes,
        "candidates": [
            {
                "id": c.id,
                "name": c.name,
                "party": c.party,
                "party_short": c.party_short,
                "constituency": c.constituency,
                "votes": c.votes_count or 0,
                "percentage": round(
                    (c.votes_count or 0) / total_votes * 100, 1
                ) if total_votes > 0 else 0,
            }
            for c in candidates
        ],
    })


# -------------------------------------------------------------------------
# Settings
# -------------------------------------------------------------------------

@admin_bp.route("/settings")
@admin_required
def settings():
    """System configuration and settings."""
    # Assuming stats isn't strictly required for sidebar on settings, or we fetch it:
    stats = _get_dashboard_stats()
    return render_template("admin/settings.html", stats=stats)


@admin_bp.route("/save-settings", methods=["POST"])
@admin_required
def save_settings():
    """Handle saving system settings."""
    # In a real system, these would be saved to a Configuration table or env variables.
    flash("System configuration successfully updated.", "success")
    return redirect(url_for("admin.settings"))


# -------------------------------------------------------------------------
# Candidate Management
# -------------------------------------------------------------------------

@admin_bp.route("/candidates")
@admin_required
def manage_candidates():
    """List all candidates for admin editing."""
    candidates = Candidate.query.all()
    stats = _get_dashboard_stats()
    return render_template("admin/candidates.html", candidates=candidates, stats=stats)


@admin_bp.route("/candidates/add", methods=["POST"])
@admin_required
def add_candidate():
    name = request.form.get("name")
    party = request.form.get("party")
    party_short = request.form.get("party_short")
    constituency = request.form.get("constituency")
    details = request.form.get("details", "")
    election_id = request.form.get("election_id", 1)  # Defaulting to 1 for simplicity
    
    if name and party and constituency:
        c = Candidate(
            name=name,
            party=party,
            party_short=party_short,
            constituency=constituency,
            details=details,
            election_id=election_id,
            votes_count=0
        )
        db.session.add(c)
        db.session.commit()
        flash(f"Candidate {name} added successfully.", "success")
    else:
        flash("Please fill in all required fields.", "error")
        
    return redirect(url_for("admin.manage_candidates"))


@admin_bp.route("/candidates/edit/<int:c_id>", methods=["POST"])
@admin_required
def edit_candidate(c_id):
    c = db.session.get(Candidate, c_id)
    if not c:
        flash("Candidate not found.", "error")
        return redirect(url_for("admin.manage_candidates"))
        
    c.name = request.form.get("name", c.name)
    c.party = request.form.get("party", c.party)
    c.party_short = request.form.get("party_short", c.party_short)
    c.constituency = request.form.get("constituency", c.constituency)
    c.details = request.form.get("details", c.details)
    
    db.session.commit()
    flash(f"Candidate {c.name} updated successfully.", "success")
    return redirect(url_for("admin.manage_candidates"))


@admin_bp.route("/candidates/delete/<int:c_id>", methods=["POST"])
@admin_required
def delete_candidate(c_id):
    c = db.session.get(Candidate, c_id)
    if not c:
        flash("Candidate not found.", "error")
    else:
        db.session.delete(c)
        db.session.commit()
        flash("Candidate removed successfully.", "success")
        
    return redirect(url_for("admin.manage_candidates"))


# -------------------------------------------------------------------------
# Admin Logout
# -------------------------------------------------------------------------

@admin_bp.route("/logout")
def admin_logout():
    """Clear admin session."""
    session.pop("admin_id", None)
    session.pop("admin_name", None)
    session.pop("admin_role", None)
    flash("Admin logged out.", "info")
    return redirect(url_for("admin.admin_login"))
