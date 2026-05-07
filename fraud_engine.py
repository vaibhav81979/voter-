class FraudEngine:
    @staticmethod
    def calculate_risk_score(signals: dict) -> int:
        """
        Calculates risk based on weighted penalties:
        - Biometric duplicate: +50
        - Rapid voting: +30
        - Geolocation anomaly: +20
        - Device reuse: +15
        - Time patterns: +10
        """
        score = 0
        if signals.get("is_biometric_duplicate"): score += 50
        if signals.get("is_rapid_voting"): score += 30
        if signals.get("is_geo_anomaly"): score += 20
        if signals.get("is_device_reuse"): score += 15
        if signals.get("is_suspicious_time"): score += 10
        
        return score

    @staticmethod
    def should_block(score: int) -> bool:
        """Auto-block at score >= 50."""
        return score >= 50
