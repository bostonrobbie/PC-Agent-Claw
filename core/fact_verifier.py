#!/usr/bin/env python3
"""
Fact Verification System - Verify facts before stating, cross-reference with databases
Ensures accuracy and reliability of information
"""

import sqlite3
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum


class VerificationStatus(Enum):
    """Fact verification status"""
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    DISPUTED = "disputed"
    FALSE = "false"
    PENDING = "pending"


class ConfidenceLevel(Enum):
    """Confidence in fact verification"""
    VERY_HIGH = 0.95
    HIGH = 0.80
    MEDIUM = 0.60
    LOW = 0.40
    VERY_LOW = 0.20


class FactVerifier:
    """
    Fact verification system with cross-referencing

    Features:
    - Track and verify factual claims
    - Cross-reference with multiple sources
    - Maintain fact database
    - Track verification history
    - Flag contradictory claims
    - Source credibility scoring
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
        """Initialize database schema for fact verification"""
        cursor = self.conn.cursor()

        # Facts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fact_id TEXT UNIQUE NOT NULL,
                claim TEXT NOT NULL,
                category TEXT,
                verification_status TEXT DEFAULT 'unverified',
                confidence REAL DEFAULT 0.5,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_verified TIMESTAMP,
                verification_count INTEGER DEFAULT 0,
                metadata TEXT
            )
        ''')

        # Sources table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fact_sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT UNIQUE NOT NULL,
                source_name TEXT NOT NULL,
                source_type TEXT,
                credibility_score REAL DEFAULT 0.5,
                total_facts INTEGER DEFAULT 0,
                verified_facts INTEGER DEFAULT 0,
                disputed_facts INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        ''')

        # Verifications table (fact-source relationship)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fact_verifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fact_id TEXT NOT NULL,
                source_id TEXT NOT NULL,
                verification_status TEXT NOT NULL,
                confidence REAL,
                evidence TEXT,
                verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                FOREIGN KEY (fact_id) REFERENCES facts(fact_id),
                FOREIGN KEY (source_id) REFERENCES fact_sources(source_id)
            )
        ''')

        # Contradictions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fact_contradictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fact_id_1 TEXT NOT NULL,
                fact_id_2 TEXT NOT NULL,
                contradiction_type TEXT,
                severity TEXT,
                description TEXT,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved INTEGER DEFAULT 0,
                FOREIGN KEY (fact_id_1) REFERENCES facts(fact_id),
                FOREIGN KEY (fact_id_2) REFERENCES facts(fact_id)
            )
        ''')

        # Verification history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS verification_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fact_id TEXT NOT NULL,
                previous_status TEXT,
                new_status TEXT,
                previous_confidence REAL,
                new_confidence REAL,
                reason TEXT,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (fact_id) REFERENCES facts(fact_id)
            )
        ''')

        self.conn.commit()

    # === FACT MANAGEMENT ===

    def add_fact(self, claim: str, category: str = None,
                initial_status: VerificationStatus = VerificationStatus.UNVERIFIED,
                metadata: Dict = None) -> str:
        """Add a new fact to the database"""
        fact_id = self._generate_fact_id(claim)

        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO facts
            (fact_id, claim, category, verification_status, metadata)
            VALUES (?, ?, ?, ?, ?)
        ''', (fact_id, claim, category, initial_status.value,
              json.dumps(metadata) if metadata else None))
        self.conn.commit()

        return fact_id

    def _generate_fact_id(self, claim: str) -> str:
        """Generate unique ID for a fact"""
        return hashlib.sha256(claim.encode()).hexdigest()[:16]

    def get_fact(self, fact_id: str) -> Optional[Dict]:
        """Get fact details"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM facts WHERE fact_id = ?', (fact_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def search_facts(self, query: str, category: str = None,
                    min_confidence: float = 0.0) -> List[Dict]:
        """Search for facts matching query"""
        cursor = self.conn.cursor()

        if category:
            cursor.execute('''
                SELECT * FROM facts
                WHERE (claim LIKE ? OR category = ?)
                AND confidence >= ?
                ORDER BY confidence DESC, last_verified DESC
            ''', (f'%{query}%', category, min_confidence))
        else:
            cursor.execute('''
                SELECT * FROM facts
                WHERE claim LIKE ? AND confidence >= ?
                ORDER BY confidence DESC, last_verified DESC
            ''', (f'%{query}%', min_confidence))

        return [dict(row) for row in cursor.fetchall()]

    # === SOURCE MANAGEMENT ===

    def add_source(self, source_name: str, source_type: str,
                  credibility_score: float = 0.5, metadata: Dict = None) -> str:
        """Add a fact source"""
        source_id = hashlib.md5(source_name.encode()).hexdigest()[:12]

        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO fact_sources
            (source_id, source_name, source_type, credibility_score, metadata)
            VALUES (?, ?, ?, ?, ?)
        ''', (source_id, source_name, source_type, credibility_score,
              json.dumps(metadata) if metadata else None))
        self.conn.commit()

        return source_id

    def get_source(self, source_id: str) -> Optional[Dict]:
        """Get source details"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM fact_sources WHERE source_id = ?', (source_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def update_source_credibility(self, source_id: str, new_score: float):
        """Update source credibility score"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE fact_sources
            SET credibility_score = ?
            WHERE source_id = ?
        ''', (new_score, source_id))
        self.conn.commit()

    # === VERIFICATION ===

    def verify_fact(self, fact_id: str, source_id: str,
                   status: VerificationStatus, confidence: float,
                   evidence: str = None, notes: str = None):
        """Verify a fact with a source"""
        cursor = self.conn.cursor()

        # Add verification record
        cursor.execute('''
            INSERT INTO fact_verifications
            (fact_id, source_id, verification_status, confidence, evidence, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (fact_id, source_id, status.value, confidence, evidence, notes))

        # Update fact status
        self._update_fact_status(fact_id)

        # Update source statistics
        cursor.execute('''
            UPDATE fact_sources
            SET total_facts = total_facts + 1,
                verified_facts = verified_facts + CASE WHEN ? = 'verified' THEN 1 ELSE 0 END,
                disputed_facts = disputed_facts + CASE WHEN ? IN ('disputed', 'false') THEN 1 ELSE 0 END
            WHERE source_id = ?
        ''', (status.value, status.value, source_id))

        self.conn.commit()

    def _update_fact_status(self, fact_id: str):
        """Update fact status based on all verifications"""
        cursor = self.conn.cursor()

        # Get all verifications for this fact
        cursor.execute('''
            SELECT v.verification_status, v.confidence, s.credibility_score
            FROM fact_verifications v
            JOIN fact_sources s ON v.source_id = s.source_id
            WHERE v.fact_id = ?
        ''', (fact_id,))

        verifications = cursor.fetchall()

        if not verifications:
            return

        # Calculate weighted average confidence
        total_weight = 0
        weighted_confidence = 0
        status_votes = {}

        for ver in verifications:
            weight = ver['confidence'] * ver['credibility_score']
            total_weight += weight
            weighted_confidence += ver['confidence'] * weight

            status = ver['verification_status']
            status_votes[status] = status_votes.get(status, 0) + weight

        # Determine overall status (majority vote weighted by credibility)
        if status_votes:
            overall_status = max(status_votes.items(), key=lambda x: x[1])[0]
        else:
            overall_status = VerificationStatus.UNVERIFIED.value

        # Calculate average confidence
        avg_confidence = weighted_confidence / total_weight if total_weight > 0 else 0.5

        # Get current fact state
        cursor.execute('SELECT verification_status, confidence FROM facts WHERE fact_id = ?', (fact_id,))
        current = cursor.fetchone()

        # Log history if changed
        if current and (current['verification_status'] != overall_status or
                       abs(current['confidence'] - avg_confidence) > 0.01):
            cursor.execute('''
                INSERT INTO verification_history
                (fact_id, previous_status, new_status, previous_confidence, new_confidence, reason)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (fact_id, current['verification_status'], overall_status,
                  current['confidence'], avg_confidence, 'Updated based on new verifications'))

        # Update fact
        cursor.execute('''
            UPDATE facts
            SET verification_status = ?,
                confidence = ?,
                last_verified = CURRENT_TIMESTAMP,
                verification_count = verification_count + 1
            WHERE fact_id = ?
        ''', (overall_status, avg_confidence, fact_id))

        self.conn.commit()

    def cross_reference(self, fact_id: str, min_sources: int = 2) -> Dict[str, Any]:
        """Cross-reference a fact across multiple sources"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT v.*, s.source_name, s.credibility_score
            FROM fact_verifications v
            JOIN fact_sources s ON v.source_id = s.source_id
            WHERE v.fact_id = ?
            ORDER BY s.credibility_score DESC
        ''', (fact_id,))

        verifications = [dict(row) for row in cursor.fetchall()]
        source_count = len(verifications)

        # Analyze agreement
        statuses = [v['verification_status'] for v in verifications]
        agreement = all(s == statuses[0] for s in statuses) if statuses else False

        return {
            'fact_id': fact_id,
            'source_count': source_count,
            'meets_threshold': source_count >= min_sources,
            'agreement': agreement,
            'verifications': verifications,
            'recommendation': 'reliable' if (source_count >= min_sources and agreement) else 'needs_more_verification'
        }

    # === CONTRADICTION DETECTION ===

    def detect_contradiction(self, fact_id_1: str, fact_id_2: str,
                           contradiction_type: str = None,
                           severity: str = "medium",
                           description: str = None):
        """Flag a contradiction between two facts"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO fact_contradictions
            (fact_id_1, fact_id_2, contradiction_type, severity, description)
            VALUES (?, ?, ?, ?, ?)
        ''', (fact_id_1, fact_id_2, contradiction_type, severity, description))
        self.conn.commit()

    def get_contradictions(self, fact_id: str = None, unresolved_only: bool = True) -> List[Dict]:
        """Get contradictions for a fact or all contradictions"""
        cursor = self.conn.cursor()

        if fact_id:
            cursor.execute('''
                SELECT c.*, f1.claim as claim_1, f2.claim as claim_2
                FROM fact_contradictions c
                JOIN facts f1 ON c.fact_id_1 = f1.fact_id
                JOIN facts f2 ON c.fact_id_2 = f2.fact_id
                WHERE (c.fact_id_1 = ? OR c.fact_id_2 = ?)
                AND (? = 0 OR c.resolved = 0)
                ORDER BY c.detected_at DESC
            ''', (fact_id, fact_id, 1 if unresolved_only else 0))
        else:
            cursor.execute('''
                SELECT c.*, f1.claim as claim_1, f2.claim as claim_2
                FROM fact_contradictions c
                JOIN facts f1 ON c.fact_id_1 = f1.fact_id
                JOIN facts f2 ON c.fact_id_2 = f2.fact_id
                WHERE (? = 0 OR c.resolved = 0)
                ORDER BY c.detected_at DESC
            ''', (1 if unresolved_only else 0,))

        return [dict(row) for row in cursor.fetchall()]

    # === ANALYTICS ===

    def get_verification_stats(self) -> Dict[str, Any]:
        """Get overall verification statistics"""
        cursor = self.conn.cursor()

        # Total facts
        cursor.execute('SELECT COUNT(*) as count FROM facts')
        total_facts = cursor.fetchone()['count']

        # By status
        cursor.execute('''
            SELECT verification_status, COUNT(*) as count
            FROM facts
            GROUP BY verification_status
        ''')
        by_status = {row['verification_status']: row['count'] for row in cursor.fetchall()}

        # Average confidence
        cursor.execute('SELECT AVG(confidence) as avg FROM facts WHERE verification_status = "verified"')
        avg_confidence = cursor.fetchone()['avg'] or 0

        # Total sources
        cursor.execute('SELECT COUNT(*) as count FROM fact_sources')
        total_sources = cursor.fetchone()['count']

        # Average source credibility
        cursor.execute('SELECT AVG(credibility_score) as avg FROM fact_sources')
        avg_credibility = cursor.fetchone()['avg'] or 0

        # Contradictions
        cursor.execute('SELECT COUNT(*) as count FROM fact_contradictions WHERE resolved = 0')
        unresolved_contradictions = cursor.fetchone()['count']

        return {
            'total_facts': total_facts,
            'facts_by_status': by_status,
            'average_confidence': round(avg_confidence, 3),
            'total_sources': total_sources,
            'average_source_credibility': round(avg_credibility, 3),
            'unresolved_contradictions': unresolved_contradictions
        }

    def get_most_reliable_facts(self, limit: int = 10) -> List[Dict]:
        """Get most reliable facts (high confidence, verified)"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM facts
            WHERE verification_status = 'verified'
            ORDER BY confidence DESC, verification_count DESC
            LIMIT ?
        ''', (limit,))
        return [dict(row) for row in cursor.fetchall()]

    def close(self):
        """Close database connection"""
        self.conn.close()


def main():
    """Test fact verification system"""
    print("Testing Fact Verification System")
    print("=" * 50)

    verifier = FactVerifier()

    # Add sources
    print("\n1. Adding fact sources...")
    wiki = verifier.add_source("Wikipedia", "encyclopedia", credibility_score=0.85)
    news1 = verifier.add_source("Reuters", "news", credibility_score=0.90)
    news2 = verifier.add_source("Random Blog", "blog", credibility_score=0.40)
    print(f"   Added 3 sources")

    # Add facts
    print("\n2. Adding facts...")
    fact1 = verifier.add_fact(
        "Python was created by Guido van Rossum",
        category="programming"
    )
    fact2 = verifier.add_fact(
        "Python was released in 1991",
        category="programming"
    )
    fact3 = verifier.add_fact(
        "AI will replace all programmers by 2025",
        category="prediction"
    )
    print(f"   Added 3 facts")

    # Verify facts with different sources
    print("\n3. Verifying facts...")
    verifier.verify_fact(
        fact1, wiki,
        VerificationStatus.VERIFIED,
        confidence=0.95,
        evidence="Official Python documentation"
    )

    verifier.verify_fact(
        fact1, news1,
        VerificationStatus.VERIFIED,
        confidence=0.90,
        evidence="Historical records"
    )

    verifier.verify_fact(
        fact2, wiki,
        VerificationStatus.VERIFIED,
        confidence=0.95
    )

    verifier.verify_fact(
        fact3, news2,
        VerificationStatus.DISPUTED,
        confidence=0.30,
        evidence="Speculative opinion piece"
    )
    print("   Verified facts with multiple sources")

    # Cross-reference
    print("\n4. Cross-referencing fact...")
    cross_ref = verifier.cross_reference(fact1, min_sources=2)
    print(f"   Fact: {fact1}")
    print(f"   Sources: {cross_ref['source_count']}")
    print(f"   Agreement: {cross_ref['agreement']}")
    print(f"   Recommendation: {cross_ref['recommendation']}")

    # Detect contradiction
    print("\n5. Detecting contradictions...")
    fact4 = verifier.add_fact(
        "Python was created in 1995",  # Wrong date
        category="programming"
    )
    verifier.detect_contradiction(
        fact2, fact4,
        contradiction_type="date_conflict",
        severity="high",
        description="Conflicting release dates for Python"
    )
    print("   Flagged contradiction between facts")

    # Get contradictions
    contradictions = verifier.get_contradictions(unresolved_only=True)
    for c in contradictions:
        print(f"\n   Contradiction ({c['severity']}):")
        print(f"   - Claim 1: {c['claim_1']}")
        print(f"   - Claim 2: {c['claim_2']}")
        print(f"   - Description: {c['description']}")

    # Search facts
    print("\n6. Searching for Python facts...")
    results = verifier.search_facts("Python", min_confidence=0.7)
    for fact in results:
        print(f"   - {fact['claim']}")
        print(f"     Status: {fact['verification_status']}, Confidence: {fact['confidence']:.0%}")

    # Get verification stats
    print("\n7. Verification Statistics:")
    stats = verifier.get_verification_stats()
    for key, value in stats.items():
        if key == 'facts_by_status':
            print(f"   {key}:")
            for status, count in value.items():
                print(f"     - {status}: {count}")
        else:
            print(f"   {key}: {value}")

    # Most reliable facts
    print("\n8. Most Reliable Facts:")
    reliable = verifier.get_most_reliable_facts(limit=5)
    for fact in reliable:
        print(f"   - {fact['claim']}")
        print(f"     Confidence: {fact['confidence']:.0%}, Verifications: {fact['verification_count']}")

    print(f"\n✓ Fact verification system working!")
    print(f"Database: {verifier.db_path}")

    verifier.close()


if __name__ == "__main__":
    main()
