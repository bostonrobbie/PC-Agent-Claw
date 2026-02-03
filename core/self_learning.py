#!/usr/bin/env python3
"""
Self-Learning System - Track interactions, learn from mistakes, adapt over time
Learns from all interactions and improves behavior based on outcomes
"""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import defaultdict


class SelfLearningSystem:
    """
    Self-learning system that tracks all interactions and adapts behavior

    Features:
    - Tracks all interactions and their outcomes
    - Learns from mistakes and successes
    - Adapts behavior based on historical performance
    - Identifies patterns in successful/failed approaches
    - Provides recommendations based on learned patterns
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
        """Initialize database schema for self-learning"""
        cursor = self.conn.cursor()

        # Interactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                interaction_type TEXT NOT NULL,
                context TEXT,
                action_taken TEXT NOT NULL,
                outcome TEXT NOT NULL,
                success INTEGER DEFAULT 0,
                confidence REAL DEFAULT 0.5,
                duration_seconds REAL,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        ''')

        # Patterns table - learned behavioral patterns
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learned_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_name TEXT UNIQUE NOT NULL,
                pattern_type TEXT,
                conditions TEXT,
                recommended_action TEXT,
                success_rate REAL DEFAULT 0.0,
                usage_count INTEGER DEFAULT 0,
                last_used TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Mistakes table - track and learn from errors
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mistakes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mistake_type TEXT NOT NULL,
                description TEXT NOT NULL,
                context TEXT,
                lesson_learned TEXT,
                prevention_strategy TEXT,
                occurrence_count INTEGER DEFAULT 1,
                last_occurred TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Adaptations table - behavioral changes made
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS adaptations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                adaptation_name TEXT NOT NULL,
                reason TEXT,
                old_behavior TEXT,
                new_behavior TEXT,
                effectiveness_score REAL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        self.conn.commit()

    # === INTERACTION TRACKING ===

    def log_interaction(self, interaction_type: str, action_taken: str,
                       outcome: str, success: bool, context: str = None,
                       confidence: float = 0.5, duration_seconds: float = None,
                       error_message: str = None, metadata: Dict = None):
        """Log an interaction and its outcome"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO interactions
            (interaction_type, context, action_taken, outcome, success,
             confidence, duration_seconds, error_message, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (interaction_type, context, action_taken, outcome,
              1 if success else 0, confidence, duration_seconds,
              error_message, json.dumps(metadata) if metadata else None))
        self.conn.commit()

        # Analyze and update patterns
        self._update_patterns(interaction_type, action_taken, success, context)

    def _update_patterns(self, interaction_type: str, action_taken: str,
                        success: bool, context: str):
        """Update learned patterns based on interaction outcome"""
        pattern_name = f"{interaction_type}::{action_taken}"

        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM learned_patterns WHERE pattern_name = ?
        ''', (pattern_name,))

        pattern = cursor.fetchone()

        if pattern:
            # Update existing pattern
            old_success_rate = pattern['success_rate']
            usage_count = pattern['usage_count'] + 1
            new_success_rate = ((old_success_rate * pattern['usage_count']) +
                               (1 if success else 0)) / usage_count

            cursor.execute('''
                UPDATE learned_patterns
                SET success_rate = ?, usage_count = ?, last_used = CURRENT_TIMESTAMP
                WHERE pattern_name = ?
            ''', (new_success_rate, usage_count, pattern_name))
        else:
            # Create new pattern
            cursor.execute('''
                INSERT INTO learned_patterns
                (pattern_name, pattern_type, conditions, recommended_action,
                 success_rate, usage_count, last_used)
                VALUES (?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
            ''', (pattern_name, interaction_type, context, action_taken,
                  1.0 if success else 0.0))

        self.conn.commit()

    # === MISTAKE TRACKING ===

    def log_mistake(self, mistake_type: str, description: str,
                   context: str = None, lesson_learned: str = None,
                   prevention_strategy: str = None):
        """Log a mistake and learn from it"""
        cursor = self.conn.cursor()

        # Check if this mistake exists
        cursor.execute('''
            SELECT * FROM mistakes
            WHERE mistake_type = ? AND description = ?
        ''', (mistake_type, description))

        existing = cursor.fetchone()

        if existing:
            # Update existing mistake
            cursor.execute('''
                UPDATE mistakes
                SET occurrence_count = occurrence_count + 1,
                    last_occurred = CURRENT_TIMESTAMP,
                    lesson_learned = COALESCE(?, lesson_learned),
                    prevention_strategy = COALESCE(?, prevention_strategy)
                WHERE id = ?
            ''', (lesson_learned, prevention_strategy, existing['id']))
        else:
            # Create new mistake entry
            cursor.execute('''
                INSERT INTO mistakes
                (mistake_type, description, context, lesson_learned, prevention_strategy)
                VALUES (?, ?, ?, ?, ?)
            ''', (mistake_type, description, context, lesson_learned, prevention_strategy))

        self.conn.commit()

    def get_similar_mistakes(self, mistake_type: str, limit: int = 5) -> List[Dict]:
        """Get similar past mistakes to avoid repeating them"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM mistakes
            WHERE mistake_type = ?
            ORDER BY occurrence_count DESC, last_occurred DESC
            LIMIT ?
        ''', (mistake_type, limit))
        return [dict(row) for row in cursor.fetchall()]

    # === PATTERN RECOGNITION ===

    def get_best_action(self, interaction_type: str, min_confidence: float = 0.6) -> Optional[Dict]:
        """Get the best recommended action based on learned patterns"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM learned_patterns
            WHERE pattern_type = ? AND success_rate >= ?
            ORDER BY success_rate DESC, usage_count DESC
            LIMIT 1
        ''', (interaction_type, min_confidence))

        row = cursor.fetchone()
        return dict(row) if row else None

    def get_all_patterns(self, min_usage: int = 3) -> List[Dict]:
        """Get all learned patterns with sufficient data"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM learned_patterns
            WHERE usage_count >= ?
            ORDER BY success_rate DESC
        ''', (min_usage,))
        return [dict(row) for row in cursor.fetchall()]

    # === ADAPTATION ===

    def apply_adaptation(self, adaptation_name: str, reason: str,
                        old_behavior: str, new_behavior: str,
                        effectiveness_score: float = None):
        """Log a behavioral adaptation"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO adaptations
            (adaptation_name, reason, old_behavior, new_behavior, effectiveness_score)
            VALUES (?, ?, ?, ?, ?)
        ''', (adaptation_name, reason, old_behavior, new_behavior, effectiveness_score))
        self.conn.commit()

    def get_recent_adaptations(self, days: int = 30, limit: int = 20) -> List[Dict]:
        """Get recent behavioral adaptations"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM adaptations
            WHERE applied_at >= datetime('now', '-' || ? || ' days')
            ORDER BY applied_at DESC
            LIMIT ?
        ''', (days, limit))
        return [dict(row) for row in cursor.fetchall()]

    # === ANALYTICS ===

    def get_learning_stats(self) -> Dict[str, Any]:
        """Get overall learning statistics"""
        cursor = self.conn.cursor()

        # Total interactions
        cursor.execute('SELECT COUNT(*) as count FROM interactions')
        total_interactions = cursor.fetchone()['count']

        # Success rate
        cursor.execute('''
            SELECT AVG(success) as success_rate FROM interactions
            WHERE created_at >= datetime('now', '-7 days')
        ''')
        recent_success_rate = cursor.fetchone()['success_rate'] or 0

        # Learned patterns
        cursor.execute('SELECT COUNT(*) as count FROM learned_patterns WHERE usage_count >= 3')
        stable_patterns = cursor.fetchone()['count']

        # Unique mistakes
        cursor.execute('SELECT COUNT(*) as count FROM mistakes')
        unique_mistakes = cursor.fetchone()['count']

        # Total mistake occurrences
        cursor.execute('SELECT SUM(occurrence_count) as total FROM mistakes')
        total_mistakes = cursor.fetchone()['total'] or 0

        # Adaptations
        cursor.execute('SELECT COUNT(*) as count FROM adaptations')
        total_adaptations = cursor.fetchone()['count']

        return {
            'total_interactions': total_interactions,
            'recent_success_rate': round(recent_success_rate, 3),
            'stable_patterns': stable_patterns,
            'unique_mistakes': unique_mistakes,
            'total_mistake_occurrences': total_mistakes,
            'adaptations_applied': total_adaptations,
            'learning_quality': self._calculate_learning_quality()
        }

    def _calculate_learning_quality(self) -> float:
        """Calculate overall learning quality score (0-1)"""
        cursor = self.conn.cursor()

        # Get success rates over time windows
        cursor.execute('''
            SELECT AVG(success) as rate FROM interactions
            WHERE created_at >= datetime('now', '-1 days')
        ''')
        recent_rate = cursor.fetchone()['rate'] or 0.5

        cursor.execute('''
            SELECT AVG(success) as rate FROM interactions
            WHERE created_at >= datetime('now', '-7 days')
            AND created_at < datetime('now', '-1 days')
        ''')
        older_rate = cursor.fetchone()['rate'] or 0.5

        # Improvement = positive change over time
        improvement = max(0, recent_rate - older_rate)

        # Quality = base success rate + improvement bonus
        quality = min(1.0, recent_rate + (improvement * 0.5))

        return round(quality, 3)

    def get_interaction_history(self, interaction_type: str = None,
                               days: int = 7, limit: int = 100) -> List[Dict]:
        """Get interaction history for analysis"""
        cursor = self.conn.cursor()

        if interaction_type:
            cursor.execute('''
                SELECT * FROM interactions
                WHERE interaction_type = ?
                AND created_at >= datetime('now', '-' || ? || ' days')
                ORDER BY created_at DESC
                LIMIT ?
            ''', (interaction_type, days, limit))
        else:
            cursor.execute('''
                SELECT * FROM interactions
                WHERE created_at >= datetime('now', '-' || ? || ' days')
                ORDER BY created_at DESC
                LIMIT ?
            ''', (days, limit))

        return [dict(row) for row in cursor.fetchall()]

    def close(self):
        """Close database connection"""
        self.conn.close()


def main():
    """Test self-learning system"""
    print("Testing Self-Learning System")
    print("=" * 50)

    system = SelfLearningSystem()

    # Simulate some interactions
    print("\n1. Logging interactions...")
    system.log_interaction(
        interaction_type="code_generation",
        action_taken="use_async_await",
        outcome="successful_execution",
        success=True,
        context="web_scraping_task",
        confidence=0.8,
        duration_seconds=2.5
    )

    system.log_interaction(
        interaction_type="code_generation",
        action_taken="use_threading",
        outcome="race_condition_error",
        success=False,
        context="web_scraping_task",
        confidence=0.6,
        error_message="Thread safety issue"
    )

    system.log_interaction(
        interaction_type="code_generation",
        action_taken="use_async_await",
        outcome="successful_execution",
        success=True,
        context="api_calls",
        confidence=0.9
    )

    print("   Logged 3 interactions")

    # Log a mistake
    print("\n2. Logging a mistake...")
    system.log_mistake(
        mistake_type="concurrency_error",
        description="Used threading without proper locks",
        context="web_scraping_task",
        lesson_learned="Always use async/await for I/O-bound tasks",
        prevention_strategy="Default to asyncio for concurrent I/O operations"
    )
    print("   Logged mistake with lesson learned")

    # Get best action recommendation
    print("\n3. Getting best action recommendation...")
    best_action = system.get_best_action("code_generation")
    if best_action:
        print(f"   Recommended: {best_action['recommended_action']}")
        print(f"   Success rate: {best_action['success_rate']:.1%}")
        print(f"   Usage count: {best_action['usage_count']}")

    # Apply adaptation
    print("\n4. Applying behavioral adaptation...")
    system.apply_adaptation(
        adaptation_name="prefer_async_over_threading",
        reason="Higher success rate and fewer race conditions",
        old_behavior="Use threading for concurrent operations",
        new_behavior="Use asyncio for I/O-bound concurrent operations",
        effectiveness_score=0.85
    )
    print("   Adaptation applied")

    # Get learning statistics
    print("\n5. Learning Statistics:")
    stats = system.get_learning_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")

    # Get all learned patterns
    print("\n6. Learned Patterns:")
    patterns = system.get_all_patterns(min_usage=1)
    for pattern in patterns:
        print(f"   - {pattern['pattern_name']}")
        print(f"     Success rate: {pattern['success_rate']:.1%}, Uses: {pattern['usage_count']}")

    print(f"\n✓ Self-learning system working!")
    print(f"Database: {system.db_path}")

    system.close()


if __name__ == "__main__":
    main()
