#!/usr/bin/env python3
"""Learning Tracker (#22) - Track what the system learns over time"""
import sqlite3
from pathlib import Path
from typing import Dict, List
from datetime import datetime
import json
import sys

sys.path.append(str(Path(__file__).parent.parent))

class LearningTracker:
    """Track system learning and improvements"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            workspace = Path(__file__).parent.parent
            db_path = str(workspace / "learning.db")

        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        """Initialize database schema"""
        cursor = self.conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                lesson TEXT NOT NULL,
                context TEXT,
                confidence REAL DEFAULT 0.5,
                evidence TEXT,
                applied_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learning_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                learning_id INTEGER NOT NULL,
                situation TEXT,
                outcome TEXT,
                success BOOLEAN,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (learning_id) REFERENCES learnings (id)
            )
        ''')

        self.conn.commit()

    def add_learning(self, category: str, lesson: str, context: str = None,
                    confidence: float = 0.5, evidence: str = None) -> int:
        """Add a new learning"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO learnings (category, lesson, context, confidence, evidence)
            VALUES (?, ?, ?, ?, ?)
        ''', (category, lesson, context, confidence, evidence))
        self.conn.commit()
        return cursor.lastrowid

    def apply_learning(self, learning_id: int, situation: str, outcome: str, success: bool):
        """Record application of a learning"""
        cursor = self.conn.cursor()

        # Add application record
        cursor.execute('''
            INSERT INTO learning_applications (learning_id, situation, outcome, success)
            VALUES (?, ?, ?, ?)
        ''', (learning_id, situation, outcome, success))

        # Update learning stats
        if success:
            cursor.execute('''
                UPDATE learnings
                SET applied_count = applied_count + 1,
                    success_count = success_count + 1,
                    confidence = MIN(1.0, confidence + 0.05),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (learning_id,))
        else:
            cursor.execute('''
                UPDATE learnings
                SET applied_count = applied_count + 1,
                    confidence = MAX(0.0, confidence - 0.05),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (learning_id,))

        self.conn.commit()

    def get_learnings(self, category: str = None, min_confidence: float = 0.0,
                     limit: int = 100) -> List[Dict]:
        """Get learnings with optional filters"""
        cursor = self.conn.cursor()

        if category:
            cursor.execute('''
                SELECT * FROM learnings
                WHERE category = ? AND confidence >= ?
                ORDER BY confidence DESC, updated_at DESC
                LIMIT ?
            ''', (category, min_confidence, limit))
        else:
            cursor.execute('''
                SELECT * FROM learnings
                WHERE confidence >= ?
                ORDER BY confidence DESC, updated_at DESC
                LIMIT ?
            ''', (min_confidence, limit))

        return [dict(row) for row in cursor.fetchall()]

    def get_top_learnings(self, limit: int = 10) -> List[Dict]:
        """Get highest confidence learnings"""
        cursor = self.conn.cursor()

        cursor.execute('''
            SELECT * FROM learnings
            WHERE applied_count > 0
            ORDER BY confidence DESC, success_count DESC
            LIMIT ?
        ''', (limit,))

        return [dict(row) for row in cursor.fetchall()]

    def get_learning_statistics(self) -> Dict:
        """Get overall learning statistics"""
        cursor = self.conn.cursor()

        cursor.execute('''
            SELECT
                COUNT(*) as total_learnings,
                AVG(confidence) as avg_confidence,
                SUM(applied_count) as total_applications,
                SUM(success_count) as total_successes
            FROM learnings
        ''')

        stats = dict(cursor.fetchone())

        # Calculate success rate
        if stats['total_applications'] and stats['total_applications'] > 0:
            stats['success_rate'] = (stats['total_successes'] / stats['total_applications']) * 100
        else:
            stats['success_rate'] = 0

        # Get learnings by category
        cursor.execute('''
            SELECT category, COUNT(*) as count
            FROM learnings
            GROUP BY category
            ORDER BY count DESC
        ''')

        stats['by_category'] = {row['category']: row['count'] for row in cursor.fetchall()}

        return stats

    def get_learning_applications(self, learning_id: int) -> List[Dict]:
        """Get application history for a learning"""
        cursor = self.conn.cursor()

        cursor.execute('''
            SELECT * FROM learning_applications
            WHERE learning_id = ?
            ORDER BY created_at DESC
        ''', (learning_id,))

        return [dict(row) for row in cursor.fetchall()]

    def search_learnings(self, query: str) -> List[Dict]:
        """Search learnings by text"""
        cursor = self.conn.cursor()

        cursor.execute('''
            SELECT * FROM learnings
            WHERE lesson LIKE ? OR context LIKE ?
            ORDER BY confidence DESC
        ''', (f'%{query}%', f'%{query}%'))

        return [dict(row) for row in cursor.fetchall()]

    def close(self):
        """Close database connection"""
        self.conn.close()


if __name__ == '__main__':
    # Test the system
    tracker = LearningTracker()

    print("Learning Tracker ready!")

    # Add some learnings
    print("\nAdding sample learnings...")

    learning1 = tracker.add_learning(
        "Trading",
        "Opening range breakouts work better during high volatility",
        context="Backtested 3 months of data",
        confidence=0.75,
        evidence="Win rate: 58% in high vol vs 45% in low vol"
    )

    learning2 = tracker.add_learning(
        "Risk Management",
        "Position size should decrease as daily loss increases",
        context="Risk management analysis",
        confidence=0.85,
        evidence="Reduces drawdown by 40%"
    )

    learning3 = tracker.add_learning(
        "Market Timing",
        "NYC session has highest win rate for momentum strategies",
        context="Session analysis",
        confidence=0.70,
        evidence="65% win rate NYC vs 48% Asian"
    )

    # Apply learnings
    print("\nApplying learnings...")
    tracker.apply_learning(learning1, "NQ breakout in high vol", "Won $150", success=True)
    tracker.apply_learning(learning1, "ES breakout in high vol", "Won $200", success=True)
    tracker.apply_learning(learning2, "Reduced size after -$500 day", "Protected capital", success=True)

    # Get statistics
    print("\nLearning Statistics:")
    stats = tracker.get_learning_statistics()
    print(json.dumps(stats, indent=2))

    # Get top learnings
    print("\nTop Learnings:")
    top = tracker.get_top_learnings(limit=5)
    for learning in top:
        print(f"\n  [{learning['category']}] {learning['lesson']}")
        print(f"    Confidence: {learning['confidence']:.2f}")
        print(f"    Applied: {learning['applied_count']}, Successes: {learning['success_count']}")

    tracker.close()
