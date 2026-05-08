
from app import create_app
from models import db, FraudAlert

def update_existing_logs():
    app = create_app()
    with app.app_context():
        # Find all duplicate_aadhaar alerts that are still 'high'
        alerts = FraudAlert.query.filter_by(alert_type='duplicate_aadhaar', risk_level='high').all()
        
        count = 0
        for alert in alerts:
            alert.risk_level = 'critical'
            # Update detail to the new format if it doesn't already look like it
            if "AADHAAR:" not in alert.detail:
                alert.detail = f"AADHAAR: [EXISTING] — {alert.detail}"
            count += 1
            
        db.session.commit()
        print(f"Successfully updated {count} security log entries to CRITICAL.")

if __name__ == "__main__":
    update_existing_logs()
