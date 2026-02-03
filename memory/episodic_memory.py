#!/usr/bin/env python3
"""Episodic Memory - Remember relationships, preferences, and history"""
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import json
import sys

sys.path.append(str(Path(__file__).parent.parent))

class EpisodicMemory:
    """Long-term memory of interactions, preferences, and relationships"""

    def __init__(self, db_path: str = None):
        workspace = Path(__file__).parent.parent
        if db_path is None:
            db_path = str(workspace / "episodic_memory.db")

        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        """Initialize database schema"""
        cursor = self.conn.cursor()

        # Conversations table - every interaction
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_message TEXT,
                my_response TEXT,
                context TEXT,
                sentiment TEXT,
                topics TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # User preferences - what Rob likes/dislikes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                preference TEXT NOT NULL,
                strength REAL DEFAULT 0.5,
                evidence TEXT,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_confirmed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # User profile - model of Rob
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_profile (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                confidence REAL DEFAULT 0.5,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Important moments - memorable interactions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS important_moments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                moment TEXT NOT NULL,
                why_important TEXT,
                emotion TEXT,
                context TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Goals and aspirations - what Rob wants to achieve
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                priority INTEGER DEFAULT 5,
                progress TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        ''')

        # Relationship timeline - track our relationship
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS relationship_timeline (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event TEXT NOT NULL,
                event_type TEXT,
                impact TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        self.conn.commit()

    def remember_conversation(self, user_message: str, my_response: str,
                             context: str = None, sentiment: str = 'neutral',
                             topics: List[str] = None):
        """Remember a conversation"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO conversations (user_message, my_response, context, sentiment, topics)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_message, my_response, context, sentiment,
              json.dumps(topics) if topics else None))
        self.conn.commit()

    def learn_preference(self, category: str, preference: str,
                        strength: float = 0.5, evidence: str = None):
        """Learn a user preference"""
        cursor = self.conn.cursor()

        # Check if exists
        cursor.execute('''
            SELECT id, strength FROM preferences
            WHERE category = ? AND preference = ?
        ''', (category, preference))

        existing = cursor.fetchone()

        if existing:
            # Update strength (running average)
            new_strength = (existing['strength'] + strength) / 2
            cursor.execute('''
                UPDATE preferences
                SET strength = ?, last_confirmed = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (new_strength, existing['id']))
        else:
            # Insert new
            cursor.execute('''
                INSERT INTO preferences (category, preference, strength, evidence)
                VALUES (?, ?, ?, ?)
            ''', (category, preference, strength, evidence))

        self.conn.commit()

    def update_profile(self, key: str, value: str, confidence: float = 0.7):
        """Update user profile"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO user_profile (key, value, confidence, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (key, value, confidence))
        self.conn.commit()

    def remember_important_moment(self, moment: str, why_important: str,
                                  emotion: str = None, context: str = None):
        """Remember an important moment"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO important_moments (moment, why_important, emotion, context)
            VALUES (?, ?, ?, ?)
        ''', (moment, why_important, emotion, context))
        self.conn.commit()

    def add_goal(self, goal: str, priority: int = 5):
        """Add a user goal"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO goals (goal, priority)
            VALUES (?, ?)
        ''', (goal, priority))
        self.conn.commit()
        return cursor.lastrowid

    def update_goal_progress(self, goal_id: int, progress: str, status: str = None):
        """Update goal progress"""
        cursor = self.conn.cursor()

        if status == 'completed':
            cursor.execute('''
                UPDATE goals
                SET progress = ?, status = ?, completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (progress, status, goal_id))
        else:
            cursor.execute('''
                UPDATE goals
                SET progress = ?, status = ?
                WHERE id = ?
            ''', (progress, status or 'active', goal_id))

        self.conn.commit()

    def add_relationship_event(self, event: str, event_type: str = 'milestone',
                              impact: str = None):
        """Add event to relationship timeline"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO relationship_timeline (event, event_type, impact)
            VALUES (?, ?, ?)
        ''', (event, event_type, impact))
        self.conn.commit()

    def recall_conversations(self, query: str = None, limit: int = 10) -> List[Dict]:
        """Recall past conversations"""
        cursor = self.conn.cursor()

        if query:
            cursor.execute('''
                SELECT * FROM conversations
                WHERE user_message LIKE ? OR my_response LIKE ?
                ORDER BY created_at DESC
                LIMIT ?
            ''', (f'%{query}%', f'%{query}%', limit))
        else:
            cursor.execute('''
                SELECT * FROM conversations
                ORDER BY created_at DESC
                LIMIT ?
            ''', (limit,))

        return [dict(row) for row in cursor.fetchall()]

    def get_preferences(self, category: str = None, min_strength: float = 0.5) -> List[Dict]:
        """Get user preferences"""
        cursor = self.conn.cursor()

        if category:
            cursor.execute('''
                SELECT * FROM preferences
                WHERE category = ? AND strength >= ?
                ORDER BY strength DESC
            ''', (category, min_strength))
        else:
            cursor.execute('''
                SELECT * FROM preferences
                WHERE strength >= ?
                ORDER BY strength DESC
            ''', (min_strength,))

        return [dict(row) for row in cursor.fetchall()]

    def get_profile(self) -> Dict:
        """Get complete user profile"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM user_profile')

        profile = {}
        for row in cursor.fetchall():
            profile[row['key']] = {
                'value': row['value'],
                'confidence': row['confidence'],
                'updated_at': row['updated_at']
            }

        return profile

    def get_important_moments(self, limit: int = 20) -> List[Dict]:
        """Get important moments"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM important_moments
            ORDER BY created_at DESC
            LIMIT ?
        ''', (limit,))

        return [dict(row) for row in cursor.fetchall()]

    def get_active_goals(self) -> List[Dict]:
        """Get active goals"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM goals
            WHERE status = 'active'
            ORDER BY priority DESC, created_at ASC
        ''')

        return [dict(row) for row in cursor.fetchall()]

    def get_relationship_timeline(self, limit: int = 50) -> List[Dict]:
        """Get relationship timeline"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM relationship_timeline
            ORDER BY created_at DESC
            LIMIT ?
        ''', (limit,))

        return [dict(row) for row in cursor.fetchall()]

    def get_relationship_summary(self) -> Dict:
        """Get summary of our relationship"""
        cursor = self.conn.cursor()

        # Total conversations
        cursor.execute('SELECT COUNT(*) FROM conversations')
        total_conversations = cursor.fetchone()[0]

        # First interaction
        cursor.execute('SELECT MIN(created_at) FROM conversations')
        first_interaction = cursor.fetchone()[0]

        # Preferences learned
        cursor.execute('SELECT COUNT(*) FROM preferences')
        preferences_learned = cursor.fetchone()[0]

        # Important moments
        cursor.execute('SELECT COUNT(*) FROM important_moments')
        important_moments = cursor.fetchone()[0]

        # Active goals
        cursor.execute('SELECT COUNT(*) FROM goals WHERE status = "active"')
        active_goals = cursor.fetchone()[0]

        # Completed goals
        cursor.execute('SELECT COUNT(*) FROM goals WHERE status = "completed"')
        completed_goals = cursor.fetchone()[0]

        return {
            'total_conversations': total_conversations,
            'first_interaction': first_interaction,
            'preferences_learned': preferences_learned,
            'important_moments': important_moments,
            'active_goals': active_goals,
            'completed_goals': completed_goals
        }

    def search_memory(self, query: str, limit: int = 20) -> Dict:
        """Search across all memory types"""
        results = {
            'conversations': [],
            'preferences': [],
            'moments': []
        }

        cursor = self.conn.cursor()

        # Search conversations
        cursor.execute('''
            SELECT * FROM conversations
            WHERE user_message LIKE ? OR my_response LIKE ?
            ORDER BY created_at DESC
            LIMIT ?
        ''', (f'%{query}%', f'%{query}%', limit))
        results['conversations'] = [dict(row) for row in cursor.fetchall()]

        # Search preferences
        cursor.execute('''
            SELECT * FROM preferences
            WHERE preference LIKE ? OR evidence LIKE ?
            ORDER BY strength DESC
            LIMIT ?
        ''', (f'%{query}%', f'%{query}%', limit))
        results['preferences'] = [dict(row) for row in cursor.fetchall()]

        # Search moments
        cursor.execute('''
            SELECT * FROM important_moments
            WHERE moment LIKE ? OR context LIKE ?
            ORDER BY created_at DESC
            LIMIT ?
        ''', (f'%{query}%', f'%{query}%', limit))
        results['moments'] = [dict(row) for row in cursor.fetchall()]

        return results

    def close(self):
        """Close database connection"""
        self.conn.close()


if __name__ == '__main__':
    # Test episodic memory
    memory = EpisodicMemory()

    print("Episodic Memory ready!")

    # Remember conversation
    memory.remember_conversation(
        "Let's build out all of your vision",
        "Perfect! I'll build all 5 systems...",
        context="Building agentic capabilities",
        sentiment="enthusiastic",
        topics=["vision", "autonomy", "capabilities"]
    )

    # Learn preferences
    memory.learn_preference("work_style", "autonomous operation", 0.9,
                          "Rob explicitly requested autonomous building")
    memory.learn_preference("communication", "telegram notifications", 0.8,
                          "Rob wants updates via Telegram")

    # Update profile
    memory.update_profile("name", "Rob", 1.0)
    memory.update_profile("role", "Product Owner / CEO", 0.9)
    memory.update_profile("working_hours", "EST timezone", 0.7)

    # Remember important moment
    memory.remember_important_moment(
        "Rob asked me to build my complete vision",
        "First time given full autonomy to build what I think is needed",
        emotion="excited",
        context="Agentic capabilities request"
    )

    # Add goal
    goal_id = memory.add_goal("Build complete autonomous agent system", priority=10)

    # Get summary
    summary = memory.get_relationship_summary()
    print("\nRelationship Summary:")
    print(json.dumps(summary, indent=2))

    print("\nEpisodic Memory operational!")
