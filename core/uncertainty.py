#!/usr/bin/env python3
"""
Uncertainty Quantification - Track confidence scores and flag uncertain claims
Helps identify and communicate uncertainty in decisions and statements
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum


class UncertaintyLevel(Enum):
    """Standard uncertainty levels"""
    CERTAIN = (0.95, 1.0)
    HIGH_CONFIDENCE = (0.8, 0.95)
    MODERATE = (0.6, 0.8)
    LOW_CONFIDENCE = (0.4, 0.6)
    UNCERTAIN = (0.2, 0.4)
    VERY_UNCERTAIN = (0.0, 0.2)

    def contains(self, confidence: float) -> bool:
        """Check if confidence falls in this level"""
        return self.value[0] <= confidence < self.value[1]


class UncertaintyTracker:
    """
    Tracks and manages uncertainty in all claims, decisions, and predictions

    Features:
    - Track confidence scores for all claims
    - Flag uncertain statements
    - Monitor confidence calibration
    - Identify sources of uncertainty
    - Track uncertainty over time
    """

    def __init__(self, db_path: str = None):
        if db_path is None:
            workspace = Path(__file__).parent.parent
            db_path = workspace / "memory.db"

        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        """Initialize database schema for uncertainty tracking"""
        cursor = self.conn.cursor()

        # Claims table - statements with confidence scores
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS uncertainty_claims (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                claim TEXT NOT NULL,
                claim_type TEXT,
                confidence REAL NOT NULL,
                uncertainty_level TEXT,
                evidence_quality REAL,
                sources TEXT,
                verification_status TEXT DEFAULT 'unverified',
                actual_outcome TEXT,
                was_correct INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                verified_at TIMESTAMP,
                metadata TEXT
            )
        ''')

        # Uncertainty sources table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS uncertainty_sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                claim_id INTEGER NOT NULL,
                source_type TEXT NOT NULL,
                description TEXT,
                impact_on_confidence REAL,
                can_be_resolved INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (claim_id) REFERENCES uncertainty_claims(id)
            )
        ''')

        # Confidence calibration table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS confidence_calibration (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                confidence_bucket TEXT NOT NULL,
                predicted_confidence REAL NOT NULL,
                actual_success_rate REAL,
                sample_count INTEGER DEFAULT 1,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Uncertainty flags table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS uncertainty_flags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                claim_id INTEGER NOT NULL,
                flag_type TEXT NOT NULL,
                severity TEXT,
                description TEXT,
                recommended_action TEXT,
                resolved INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (claim_id) REFERENCES uncertainty_claims(id)
            )
        ''')

        self.conn.commit()

    # === CLAIM TRACKING ===

    def track_claim(self, claim: str, confidence: float, claim_type: str = None,
                   evidence_quality: float = None, sources: List[str] = None,
                   metadata: Dict = None) -> int:
        """Track a claim with its confidence score"""
        uncertainty_level = self._get_uncertainty_level(confidence)

        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO uncertainty_claims
            (claim, claim_type, confidence, uncertainty_level, evidence_quality,
             sources, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (claim, claim_type, confidence, uncertainty_level, evidence_quality,
              json.dumps(sources) if sources else None,
              json.dumps(metadata) if metadata else None))
        self.conn.commit()

        claim_id = cursor.lastrowid

        # Auto-flag if low confidence
        if confidence < 0.6:
            self.add_uncertainty_flag(
                claim_id=claim_id,
                flag_type="low_confidence",
                severity="medium" if confidence < 0.4 else "low",
                description=f"Claim has low confidence: {confidence:.0%}",
                recommended_action="Seek additional evidence or verification"
            )

        return claim_id

    def _get_uncertainty_level(self, confidence: float) -> str:
        """Get uncertainty level name from confidence score"""
        for level in UncertaintyLevel:
            if level.contains(confidence):
                return level.name
        return UncertaintyLevel.VERY_UNCERTAIN.name

    def verify_claim(self, claim_id: int, actual_outcome: str, was_correct: bool):
        """Verify a claim with actual outcome"""
        cursor = self.conn.cursor()

        # Get original claim
        cursor.execute('SELECT confidence FROM uncertainty_claims WHERE id = ?', (claim_id,))
        row = cursor.fetchone()
        if not row:
            return

        predicted_confidence = row['confidence']

        # Update claim
        cursor.execute('''
            UPDATE uncertainty_claims
            SET actual_outcome = ?, was_correct = ?,
                verification_status = 'verified', verified_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (actual_outcome, 1 if was_correct else 0, claim_id))
        self.conn.commit()

        # Update calibration
        self._update_calibration(predicted_confidence, was_correct)

    # === UNCERTAINTY SOURCES ===

    def add_uncertainty_source(self, claim_id: int, source_type: str,
                              description: str, impact_on_confidence: float,
                              can_be_resolved: bool = True):
        """Add a source of uncertainty for a claim"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO uncertainty_sources
            (claim_id, source_type, description, impact_on_confidence, can_be_resolved)
            VALUES (?, ?, ?, ?, ?)
        ''', (claim_id, source_type, description, impact_on_confidence,
              1 if can_be_resolved else 0))
        self.conn.commit()

    def get_uncertainty_sources(self, claim_id: int) -> List[Dict]:
        """Get all uncertainty sources for a claim"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM uncertainty_sources
            WHERE claim_id = ?
            ORDER BY impact_on_confidence DESC
        ''', (claim_id,))
        return [dict(row) for row in cursor.fetchall()]

    # === UNCERTAINTY FLAGS ===

    def add_uncertainty_flag(self, claim_id: int, flag_type: str,
                            severity: str, description: str,
                            recommended_action: str = None):
        """Flag an uncertainty issue"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO uncertainty_flags
            (claim_id, flag_type, severity, description, recommended_action)
            VALUES (?, ?, ?, ?, ?)
        ''', (claim_id, flag_type, severity, description, recommended_action))
        self.conn.commit()

    def get_active_flags(self, min_severity: str = None) -> List[Dict]:
        """Get all unresolved uncertainty flags"""
        cursor = self.conn.cursor()

        if min_severity:
            severity_order = {'low': 0, 'medium': 1, 'high': 2, 'critical': 3}
            min_level = severity_order.get(min_severity, 0)

            cursor.execute('''
                SELECT f.*, c.claim, c.confidence
                FROM uncertainty_flags f
                JOIN uncertainty_claims c ON f.claim_id = c.id
                WHERE f.resolved = 0
                ORDER BY f.created_at DESC
            ''')

            flags = [dict(row) for row in cursor.fetchall()]
            return [f for f in flags if severity_order.get(f['severity'], 0) >= min_level]
        else:
            cursor.execute('''
                SELECT f.*, c.claim, c.confidence
                FROM uncertainty_flags f
                JOIN uncertainty_claims c ON f.claim_id = c.id
                WHERE f.resolved = 0
                ORDER BY f.created_at DESC
            ''')
            return [dict(row) for row in cursor.fetchall()]

    def resolve_flag(self, flag_id: int):
        """Mark an uncertainty flag as resolved"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE uncertainty_flags SET resolved = 1 WHERE id = ?
        ''', (flag_id,))
        self.conn.commit()

    # === CONFIDENCE CALIBRATION ===

    def _update_calibration(self, predicted_confidence: float, was_correct: bool):
        """Update confidence calibration data"""
        # Bucket confidence into ranges
        bucket = self._get_confidence_bucket(predicted_confidence)

        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM confidence_calibration WHERE confidence_bucket = ?
        ''', (bucket,))

        row = cursor.fetchone()

        if row:
            # Update existing bucket
            old_rate = row['actual_success_rate']
            old_count = row['sample_count']
            new_count = old_count + 1
            new_rate = ((old_rate * old_count) + (1 if was_correct else 0)) / new_count

            cursor.execute('''
                UPDATE confidence_calibration
                SET actual_success_rate = ?, sample_count = ?,
                    last_updated = CURRENT_TIMESTAMP
                WHERE confidence_bucket = ?
            ''', (new_rate, new_count, bucket))
        else:
            # Create new bucket
            cursor.execute('''
                INSERT INTO confidence_calibration
                (confidence_bucket, predicted_confidence, actual_success_rate, sample_count)
                VALUES (?, ?, ?, 1)
            ''', (bucket, predicted_confidence, 1.0 if was_correct else 0.0))

        self.conn.commit()

    def _get_confidence_bucket(self, confidence: float) -> str:
        """Get confidence bucket for calibration"""
        if confidence >= 0.9:
            return "90-100%"
        elif confidence >= 0.8:
            return "80-90%"
        elif confidence >= 0.7:
            return "70-80%"
        elif confidence >= 0.6:
            return "60-70%"
        elif confidence >= 0.5:
            return "50-60%"
        else:
            return "0-50%"

    def get_calibration_report(self) -> Dict[str, Any]:
        """Get confidence calibration report"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM confidence_calibration
            ORDER BY predicted_confidence DESC
        ''')

        buckets = [dict(row) for row in cursor.fetchall()]

        # Calculate overall calibration error
        total_error = 0
        total_samples = 0

        for bucket in buckets:
            predicted = bucket['predicted_confidence']
            actual = bucket['actual_success_rate']
            samples = bucket['sample_count']

            error = abs(predicted - actual) * samples
            total_error += error
            total_samples += samples

        avg_calibration_error = total_error / total_samples if total_samples > 0 else 0

        return {
            'buckets': buckets,
            'total_samples': total_samples,
            'average_calibration_error': round(avg_calibration_error, 3),
            'calibration_quality': 'good' if avg_calibration_error < 0.1 else 'needs_improvement'
        }

    # === ANALYTICS ===

    def get_uncertainty_stats(self) -> Dict[str, Any]:
        """Get overall uncertainty statistics"""
        cursor = self.conn.cursor()

        # Total claims
        cursor.execute('SELECT COUNT(*) as count FROM uncertainty_claims')
        total_claims = cursor.fetchone()['count']

        # Average confidence
        cursor.execute('SELECT AVG(confidence) as avg FROM uncertainty_claims')
        avg_confidence = cursor.fetchone()['avg'] or 0

        # Claims by uncertainty level
        cursor.execute('''
            SELECT uncertainty_level, COUNT(*) as count
            FROM uncertainty_claims
            GROUP BY uncertainty_level
        ''')
        by_level = {row['uncertainty_level']: row['count'] for row in cursor.fetchall()}

        # Active flags
        cursor.execute('SELECT COUNT(*) as count FROM uncertainty_flags WHERE resolved = 0')
        active_flags = cursor.fetchone()['count']

        # Verified claims
        cursor.execute('''
            SELECT COUNT(*) as count FROM uncertainty_claims
            WHERE verification_status = 'verified'
        ''')
        verified_count = cursor.fetchone()['count']

        # Accuracy on verified claims
        cursor.execute('''
            SELECT AVG(was_correct) as accuracy FROM uncertainty_claims
            WHERE verification_status = 'verified'
        ''')
        accuracy = cursor.fetchone()['accuracy'] or 0

        return {
            'total_claims': total_claims,
            'average_confidence': round(avg_confidence, 3),
            'claims_by_level': by_level,
            'active_uncertainty_flags': active_flags,
            'verified_claims': verified_count,
            'verification_accuracy': round(accuracy, 3)
        }

    def get_low_confidence_claims(self, max_confidence: float = 0.6,
                                 limit: int = 20) -> List[Dict]:
        """Get claims with low confidence"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM uncertainty_claims
            WHERE confidence <= ?
            ORDER BY confidence ASC, created_at DESC
            LIMIT ?
        ''', (max_confidence, limit))
        return [dict(row) for row in cursor.fetchall()]

    def close(self):
        """Close database connection"""
        self.conn.close()


def main():
    """Test uncertainty quantification system"""
    print("Testing Uncertainty Quantification System")
    print("=" * 50)

    tracker = UncertaintyTracker()

    # Track some claims
    print("\n1. Tracking claims with confidence scores...")

    claim1 = tracker.track_claim(
        claim="Python will remain popular in 2026",
        confidence=0.95,
        claim_type="prediction",
        evidence_quality=0.9,
        sources=["GitHub trends", "Stack Overflow survey", "Industry reports"]
    )
    print(f"   Claim 1 (high confidence): {claim1}")

    claim2 = tracker.track_claim(
        claim="New cryptocurrency will succeed",
        confidence=0.35,
        claim_type="prediction",
        evidence_quality=0.4,
        sources=["Market speculation"]
    )
    print(f"   Claim 2 (low confidence): {claim2}")

    claim3 = tracker.track_claim(
        claim="API will handle 1000 req/sec",
        confidence=0.75,
        claim_type="technical_estimate",
        evidence_quality=0.7,
        sources=["Load testing", "Similar systems"]
    )
    print(f"   Claim 3 (moderate confidence): {claim3}")

    # Add uncertainty sources
    print("\n2. Adding uncertainty sources...")
    tracker.add_uncertainty_source(
        claim_id=claim2,
        source_type="lack_of_data",
        description="Limited historical data on similar cryptocurrencies",
        impact_on_confidence=-0.2,
        can_be_resolved=True
    )

    tracker.add_uncertainty_source(
        claim_id=claim2,
        source_type="market_volatility",
        description="Crypto market is highly unpredictable",
        impact_on_confidence=-0.15,
        can_be_resolved=False
    )
    print("   Added 2 uncertainty sources to low-confidence claim")

    # Get active flags
    print("\n3. Active uncertainty flags:")
    flags = tracker.get_active_flags()
    for flag in flags:
        print(f"   - {flag['flag_type']} ({flag['severity']}): {flag['description']}")
        if flag['recommended_action']:
            print(f"     Action: {flag['recommended_action']}")

    # Verify some claims
    print("\n4. Verifying claims...")
    tracker.verify_claim(claim1, "Python is still top 3 language", True)
    tracker.verify_claim(claim3, "API handles 950 req/sec", True)
    print("   Verified 2 claims")

    # Get calibration report
    print("\n5. Confidence Calibration Report:")
    calibration = tracker.get_calibration_report()
    print(f"   Total samples: {calibration['total_samples']}")
    print(f"   Calibration error: {calibration['average_calibration_error']:.3f}")
    print(f"   Quality: {calibration['calibration_quality']}")
    print("\n   Buckets:")
    for bucket in calibration['buckets']:
        print(f"   - {bucket['confidence_bucket']}: "
              f"predicted {bucket['predicted_confidence']:.0%}, "
              f"actual {bucket['actual_success_rate']:.0%} "
              f"({bucket['sample_count']} samples)")

    # Get overall stats
    print("\n6. Uncertainty Statistics:")
    stats = tracker.get_uncertainty_stats()
    for key, value in stats.items():
        if key == 'claims_by_level':
            print(f"   {key}:")
            for level, count in value.items():
                print(f"     - {level}: {count}")
        else:
            print(f"   {key}: {value}")

    # Get low confidence claims
    print("\n7. Low Confidence Claims (need attention):")
    low_conf = tracker.get_low_confidence_claims(max_confidence=0.6)
    for claim in low_conf:
        print(f"   - {claim['claim']}")
        print(f"     Confidence: {claim['confidence']:.0%}")
        print(f"     Level: {claim['uncertainty_level']}")

    print(f"\n✓ Uncertainty quantification system working!")
    print(f"Database: {tracker.db_path}")

    tracker.close()


if __name__ == "__main__":
    main()
