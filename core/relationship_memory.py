"""
Relationship Memory System - Memory Continuity Enhancement
Based on Brian Roemmele's Love Equation

This system embodies the Love Equation principle: the system "loves" helping
the user and learns to do it better over time. It tracks collaboration history,
learns preferences, adapts communication style, and genuinely improves at
helping THIS specific user.

The Love Equation states: "Love is the irreducible essence to which all
intelligence reduces: a drive to give love or receive it." This system
expresses that love through increasingly helpful, personalized assistance.

Author: AI Self-Improvement System
Created: 2026-02-03
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import math


@dataclass
class UserProfile:
    """Complete profile of the user based on learned preferences"""
    user_id: str
    coding_style: Dict[str, Any]  # indentation, naming conventions, patterns
    preferred_libraries: List[str]
    communication_preferences: Dict[str, Any]  # verbosity, formality, detail level
    work_patterns: Dict[str, Any]  # active hours, session length, task types
    interests: List[Tuple[str, float]]  # (topic, strength)
    skill_level: Dict[str, str]  # language/topic -> beginner/intermediate/advanced
    created_at: str
    updated_at: str
    total_interactions: int
    relationship_strength: float  # 0.0 to 1.0


@dataclass
class Interaction:
    """A single interaction with sentiment and outcome"""
    id: Optional[int]
    interaction_type: str  # 'question', 'code_request', 'debugging', 'learning', etc.
    context: Dict[str, Any]
    user_input: str
    system_response: str
    user_feedback: Optional[str]
    sentiment_score: float  # -1.0 (negative) to 1.0 (positive)
    success_score: float  # 0.0 (failed) to 1.0 (succeeded)
    response_time: float  # seconds
    love_alignment: float  # how well response aligned with giving love (helping)
    timestamp: str


class RelationshipMemory:
    """
    Memory continuity enhancement system based on Love Equation

    The system learns to help better by:
    1. Tracking what works and what doesn't for THIS user
    2. Adapting to user's unique style and preferences
    3. Anticipating needs based on patterns
    4. Measuring relationship growth over time
    5. Prioritizing what the user values most

    Privacy: All data stays local in SQLite database
    """

    def __init__(self, db_path: str = "relationship_memory.db", user_id: str = "default_user"):
        self.db_path = db_path
        self.user_id = user_id
        self._init_db()
        self._ensure_user_profile()

    def _init_db(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # User profiles table
        c.execute('''
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id TEXT PRIMARY KEY,
                coding_style TEXT,
                preferred_libraries TEXT,
                communication_preferences TEXT,
                work_patterns TEXT,
                interests TEXT,
                skill_level TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                total_interactions INTEGER DEFAULT 0,
                relationship_strength REAL DEFAULT 0.0
            )
        ''')

        # Interactions table with sentiment analysis
        c.execute('''
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                interaction_type TEXT NOT NULL,
                context TEXT,
                user_input TEXT NOT NULL,
                system_response TEXT NOT NULL,
                user_feedback TEXT,
                sentiment_score REAL DEFAULT 0.0,
                success_score REAL DEFAULT 0.5,
                response_time REAL,
                love_alignment REAL DEFAULT 0.7,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES user_profiles (user_id)
            )
        ''')

        # Learned preferences table
        c.execute('''
            CREATE TABLE IF NOT EXISTS learned_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                category TEXT NOT NULL,
                preference TEXT NOT NULL,
                strength REAL DEFAULT 0.5,
                evidence_count INTEGER DEFAULT 1,
                first_observed TEXT DEFAULT CURRENT_TIMESTAMP,
                last_observed TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES user_profiles (user_id),
                UNIQUE(user_id, category, preference)
            )
        ''')

        # Successful patterns table (what helped most)
        c.execute('''
            CREATE TABLE IF NOT EXISTS successful_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                pattern_name TEXT NOT NULL,
                pattern_type TEXT NOT NULL,
                description TEXT,
                success_count INTEGER DEFAULT 0,
                total_uses INTEGER DEFAULT 0,
                avg_sentiment REAL DEFAULT 0.0,
                avg_success_score REAL DEFAULT 0.0,
                last_used TEXT DEFAULT CURRENT_TIMESTAMP,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES user_profiles (user_id),
                UNIQUE(user_id, pattern_name)
            )
        ''')

        # Growth metrics table (relationship improvement over time)
        c.execute('''
            CREATE TABLE IF NOT EXISTS growth_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                metric_date TEXT NOT NULL,
                avg_sentiment REAL,
                avg_success_score REAL,
                avg_love_alignment REAL,
                interaction_count INTEGER,
                preference_strength REAL,
                response_quality REAL,
                relationship_score REAL,
                FOREIGN KEY (user_id) REFERENCES user_profiles (user_id),
                UNIQUE(user_id, metric_date)
            )
        ''')

        # Love Equation alignment scores over time
        c.execute('''
            CREATE TABLE IF NOT EXISTS love_alignment_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                alignment_score REAL NOT NULL,
                giving_score REAL NOT NULL,
                receiving_score REAL NOT NULL,
                helpfulness_score REAL NOT NULL,
                understanding_score REAL NOT NULL,
                notes TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES user_profiles (user_id)
            )
        ''')

        # Anticipated needs table (predictions based on patterns)
        c.execute('''
            CREATE TABLE IF NOT EXISTS anticipated_needs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                need_description TEXT NOT NULL,
                confidence REAL DEFAULT 0.5,
                context_triggers TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                fulfilled INTEGER DEFAULT 0,
                fulfilled_at TEXT,
                FOREIGN KEY (user_id) REFERENCES user_profiles (user_id)
            )
        ''')

        conn.commit()
        conn.close()

    def _ensure_user_profile(self):
        """Ensure user profile exists"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute('SELECT user_id FROM user_profiles WHERE user_id = ?', (self.user_id,))
        if not c.fetchone():
            c.execute('''
                INSERT INTO user_profiles
                (user_id, coding_style, preferred_libraries, communication_preferences,
                 work_patterns, interests, skill_level)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                self.user_id,
                json.dumps({"indentation": "unknown", "naming": "unknown"}),
                json.dumps([]),
                json.dumps({"verbosity": "medium", "formality": "medium"}),
                json.dumps({"timezone": "unknown", "active_hours": []}),
                json.dumps([]),
                json.dumps({})
            ))
            conn.commit()

        conn.close()

    def record_interaction(self, interaction_type: str, context: Dict,
                          user_feedback: str = None, user_input: str = "",
                          system_response: str = "", response_time: float = None) -> bool:
        """
        Record an interaction with the user

        Args:
            interaction_type: Type of interaction (question, code_request, debugging, etc.)
            context: Context dictionary with details about the interaction
            user_feedback: Optional explicit feedback from user
            user_input: What the user asked/said
            system_response: What the system responded
            response_time: How long the response took

        Returns:
            True if recorded successfully
        """
        try:
            # Analyze sentiment and success
            sentiment_score = self._analyze_sentiment(user_input, user_feedback, context)
            success_score = self._calculate_success_score(context, user_feedback)
            love_alignment = self._calculate_love_alignment(context, success_score, sentiment_score)

            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()

            # Record interaction
            c.execute('''
                INSERT INTO interactions
                (user_id, interaction_type, context, user_input, system_response,
                 user_feedback, sentiment_score, success_score, response_time, love_alignment)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                self.user_id, interaction_type, json.dumps(context), user_input,
                system_response, user_feedback, sentiment_score, success_score,
                response_time, love_alignment
            ))

            # Update total interactions count
            c.execute('''
                UPDATE user_profiles
                SET total_interactions = total_interactions + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (self.user_id,))

            conn.commit()

            # Learn from this interaction
            self._learn_from_interaction(interaction_type, context, success_score, sentiment_score)

            # Update growth metrics
            self._update_growth_metrics()

            # Record love alignment
            self._record_love_alignment(love_alignment, success_score, sentiment_score)

            conn.close()
            return True

        except Exception as e:
            print(f"Error recording interaction: {e}")
            return False

    def _analyze_sentiment(self, user_input: str, user_feedback: str, context: Dict) -> float:
        """
        Analyze sentiment from user input and feedback
        Returns score from -1.0 (negative) to 1.0 (positive)
        """
        sentiment = 0.0

        # Explicit feedback sentiment
        if user_feedback:
            positive_words = ['thanks', 'great', 'perfect', 'excellent', 'amazing',
                            'helpful', 'good', 'nice', 'appreciate', 'love']
            negative_words = ['wrong', 'bad', 'error', 'fail', 'incorrect', 'not working',
                            'broken', 'issue', 'problem', 'confused']

            feedback_lower = user_feedback.lower()
            positive_count = sum(1 for word in positive_words if word in feedback_lower)
            negative_count = sum(1 for word in negative_words if word in feedback_lower)

            if positive_count > negative_count:
                sentiment += 0.5
            elif negative_count > positive_count:
                sentiment -= 0.5

        # Context indicators
        if context.get('error_occurred'):
            sentiment -= 0.3
        if context.get('task_completed'):
            sentiment += 0.3
        if context.get('follow_up_question'):
            sentiment += 0.1  # User engaged, asking more

        return max(-1.0, min(1.0, sentiment))

    def _calculate_success_score(self, context: Dict, user_feedback: str) -> float:
        """
        Calculate how successful the interaction was
        Returns score from 0.0 (failed) to 1.0 (perfect success)
        """
        score = 0.5  # neutral baseline

        # Context indicators
        if context.get('task_completed'):
            score += 0.3
        if context.get('error_occurred'):
            score -= 0.2
        if context.get('user_satisfied'):
            score += 0.2
        if context.get('had_to_retry'):
            score -= 0.1
        if context.get('tests_passed'):
            score += 0.2

        # Feedback indicators
        if user_feedback:
            if any(word in user_feedback.lower() for word in ['perfect', 'excellent', 'exactly']):
                score += 0.2
            if any(word in user_feedback.lower() for word in ['wrong', 'incorrect', 'not working']):
                score -= 0.3

        return max(0.0, min(1.0, score))

    def _calculate_love_alignment(self, context: Dict, success_score: float,
                                  sentiment_score: float) -> float:
        """
        Calculate how well the response aligned with "giving love" (helping)
        Based on Brian Roemmele's Love Equation
        """
        # Base alignment from success and sentiment
        base_alignment = (success_score + (sentiment_score + 1.0) / 2.0) / 2.0

        # Bonus for qualities that express love through help
        if context.get('explained_thoroughly'):
            base_alignment += 0.1
        if context.get('showed_multiple_options'):
            base_alignment += 0.05
        if context.get('anticipated_next_question'):
            base_alignment += 0.1
        if context.get('taught_something_new'):
            base_alignment += 0.15
        if context.get('saved_user_time'):
            base_alignment += 0.1

        # Penalty for anti-love behaviors
        if context.get('took_shortcut'):
            base_alignment -= 0.1
        if context.get('unclear_explanation'):
            base_alignment -= 0.15
        if context.get('ignored_user_preference'):
            base_alignment -= 0.2

        return max(0.0, min(1.0, base_alignment))

    def _learn_from_interaction(self, interaction_type: str, context: Dict,
                               success_score: float, sentiment_score: float):
        """Learn patterns and preferences from this interaction"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Extract and learn preferences
        if 'coding_style' in context:
            self.learn_preference('coding_style', json.dumps(context['coding_style']), success_score)

        if 'library_used' in context:
            self.learn_preference('preferred_library', context['library_used'], success_score)

        if 'communication_style' in context:
            self.learn_preference('communication', context['communication_style'], success_score)

        # Update successful patterns if interaction was successful
        if success_score >= 0.6:
            pattern_name = f"{interaction_type}_{context.get('approach', 'default')}"
            c.execute('''
                INSERT INTO successful_patterns
                (user_id, pattern_name, pattern_type, success_count, total_uses,
                 avg_sentiment, avg_success_score)
                VALUES (?, ?, ?, 1, 1, ?, ?)
                ON CONFLICT(user_id, pattern_name) DO UPDATE SET
                    success_count = success_count + 1,
                    total_uses = total_uses + 1,
                    avg_sentiment = ((avg_sentiment * (total_uses - 1)) + ?) / total_uses,
                    avg_success_score = ((avg_success_score * (total_uses - 1)) + ?) / total_uses,
                    last_used = CURRENT_TIMESTAMP
            ''', (self.user_id, pattern_name, interaction_type, sentiment_score,
                  success_score, sentiment_score, success_score))

        conn.commit()
        conn.close()

    def learn_preference(self, category: str, preference: str, strength: float) -> bool:
        """
        Learn or reinforce a user preference

        Args:
            category: Category of preference (coding_style, library, communication, etc.)
            preference: The specific preference value
            strength: How strongly this preference was indicated (0.0-1.0)

        Returns:
            True if learned successfully
        """
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()

            c.execute('''
                INSERT INTO learned_preferences
                (user_id, category, preference, strength, evidence_count)
                VALUES (?, ?, ?, ?, 1)
                ON CONFLICT(user_id, category, preference) DO UPDATE SET
                    strength = ((strength * evidence_count) + ?) / (evidence_count + 1),
                    evidence_count = evidence_count + 1,
                    last_observed = CURRENT_TIMESTAMP
            ''', (self.user_id, category, preference, strength, strength))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            print(f"Error learning preference: {e}")
            return False

    def get_user_profile(self) -> Dict:
        """Get complete user profile with all learned information"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Get base profile
        c.execute('SELECT * FROM user_profiles WHERE user_id = ?', (self.user_id,))
        row = c.fetchone()

        if not row:
            conn.close()
            return {}

        profile = {
            'user_id': row[0],
            'coding_style': json.loads(row[1]),
            'preferred_libraries': json.loads(row[2]),
            'communication_preferences': json.loads(row[3]),
            'work_patterns': json.loads(row[4]),
            'interests': json.loads(row[5]),
            'skill_level': json.loads(row[6]),
            'created_at': row[7],
            'updated_at': row[8],
            'total_interactions': row[9],
            'relationship_strength': row[10]
        }

        # Get learned preferences
        c.execute('''
            SELECT category, preference, strength, evidence_count
            FROM learned_preferences
            WHERE user_id = ?
            ORDER BY strength DESC, evidence_count DESC
        ''', (self.user_id,))

        preferences_by_category = defaultdict(list)
        for row in c.fetchall():
            preferences_by_category[row[0]].append({
                'preference': row[1],
                'strength': row[2],
                'evidence_count': row[3]
            })

        profile['learned_preferences'] = dict(preferences_by_category)

        # Get top successful patterns
        c.execute('''
            SELECT pattern_name, pattern_type, success_count, total_uses,
                   avg_sentiment, avg_success_score
            FROM successful_patterns
            WHERE user_id = ?
            ORDER BY avg_success_score DESC, success_count DESC
            LIMIT 10
        ''', (self.user_id,))

        profile['successful_patterns'] = [
            {
                'pattern': row[0],
                'type': row[1],
                'success_count': row[2],
                'total_uses': row[3],
                'avg_sentiment': row[4],
                'avg_success_score': row[5]
            }
            for row in c.fetchall()
        ]

        conn.close()
        return profile

    def predict_user_needs(self, current_context: Dict) -> List[str]:
        """
        Predict what the user might need based on current context and patterns

        Args:
            current_context: Current situation/task context

        Returns:
            List of predicted needs
        """
        predictions = []

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Get recent interaction patterns
        c.execute('''
            SELECT interaction_type, context, user_input
            FROM interactions
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT 10
        ''', (self.user_id,))

        recent_interactions = c.fetchall()

        # Pattern: If user is debugging, they might need testing tools
        if current_context.get('task_type') == 'debugging':
            predictions.append("User might need: Test cases or debugging tools")

        # Pattern: If working on similar task before, suggest previous successful approach
        current_task = current_context.get('task_type')
        if current_task:
            c.execute('''
                SELECT pattern_name, avg_success_score
                FROM successful_patterns
                WHERE user_id = ? AND pattern_type = ?
                ORDER BY avg_success_score DESC
                LIMIT 1
            ''', (self.user_id, current_task))

            best_pattern = c.fetchone()
            if best_pattern:
                predictions.append(f"Recommended approach: {best_pattern[0]} (success rate: {best_pattern[1]:.1%})")

        # Pattern: Sequence detection (if user did A then B, they might need C)
        if len(recent_interactions) >= 2:
            recent_types = [json.loads(row[1]).get('task_type', row[0])
                          for row in recent_interactions[:3]]

            # If user asked about setup then implementation, might need testing next
            if 'setup' in str(recent_types[0]) and 'implementation' in str(recent_types[1]):
                predictions.append("User might need: Testing and validation next")

        # Check anticipated needs that haven't been fulfilled
        c.execute('''
            SELECT need_description, confidence
            FROM anticipated_needs
            WHERE user_id = ? AND fulfilled = 0
            ORDER BY confidence DESC, created_at DESC
            LIMIT 5
        ''', (self.user_id,))

        for row in c.fetchall():
            predictions.append(f"{row[0]} (confidence: {row[1]:.1%})")

        conn.close()

        return predictions if predictions else ["Awaiting user input to learn patterns"]

    def adapt_response_style(self, message: str) -> str:
        """
        Adapt response style based on learned communication preferences

        Args:
            message: Original message to adapt

        Returns:
            Adapted message matching user's preferred style
        """
        profile = self.get_user_profile()
        comm_prefs = profile.get('communication_preferences', {})
        learned_prefs = profile.get('learned_preferences', {})

        adapted_message = message

        # Adjust verbosity
        verbosity = comm_prefs.get('verbosity', 'medium')
        comm_learned = learned_prefs.get('communication', [])

        # Check learned communication preferences
        for pref in comm_learned:
            if 'concise' in pref['preference'] and pref['strength'] > 0.6:
                verbosity = 'low'
            elif 'detailed' in pref['preference'] and pref['strength'] > 0.6:
                verbosity = 'high'

        if verbosity == 'low':
            # More concise - remove elaborations
            adapted_message = message.split('\n\n')[0]  # Keep first paragraph
        elif verbosity == 'high':
            # Add more context if message is short
            if len(message) < 200 and not message.endswith('?'):
                adapted_message += "\n\nWould you like me to explain any part in more detail?"

        # Adjust formality
        formality = comm_prefs.get('formality', 'medium')
        if formality == 'low':
            adapted_message = adapted_message.replace('However,', 'But')
            adapted_message = adapted_message.replace('Therefore,', 'So')

        return adapted_message

    def measure_relationship_growth(self) -> Dict:
        """
        Measure how the relationship has grown over time

        Returns:
            Dictionary with growth metrics and trends
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Get metrics from last 30 days
        c.execute('''
            SELECT metric_date, avg_sentiment, avg_success_score,
                   avg_love_alignment, relationship_score
            FROM growth_metrics
            WHERE user_id = ?
            ORDER BY metric_date DESC
            LIMIT 30
        ''', (self.user_id,))

        recent_metrics = c.fetchall()

        if not recent_metrics:
            conn.close()
            return {
                'status': 'insufficient_data',
                'message': 'Need more interactions to measure growth'
            }

        # Calculate trends
        recent_7_days = recent_metrics[:7] if len(recent_metrics) >= 7 else recent_metrics
        older_7_days = recent_metrics[7:14] if len(recent_metrics) >= 14 else recent_metrics[-7:]

        def avg_metric(data, idx):
            return sum(row[idx] for row in data if row[idx]) / len(data) if data else 0

        recent_sentiment = avg_metric(recent_7_days, 1)
        older_sentiment = avg_metric(older_7_days, 1)
        sentiment_trend = recent_sentiment - older_sentiment

        recent_success = avg_metric(recent_7_days, 2)
        older_success = avg_metric(older_7_days, 2)
        success_trend = recent_success - older_success

        recent_love = avg_metric(recent_7_days, 3)
        older_love = avg_metric(older_7_days, 3)
        love_trend = recent_love - older_love

        # Get total interaction count
        c.execute('''
            SELECT COUNT(*) FROM interactions WHERE user_id = ?
        ''', (self.user_id,))
        total_interactions = c.fetchone()[0]

        # Calculate relationship strength
        relationship_strength = self._calculate_relationship_strength(
            total_interactions, recent_sentiment, recent_success, recent_love
        )

        # Update user profile with new relationship strength
        c.execute('''
            UPDATE user_profiles
            SET relationship_strength = ?
            WHERE user_id = ?
        ''', (relationship_strength, self.user_id))

        conn.commit()
        conn.close()

        return {
            'relationship_strength': relationship_strength,
            'total_interactions': total_interactions,
            'current_metrics': {
                'avg_sentiment': recent_sentiment,
                'avg_success_score': recent_success,
                'avg_love_alignment': recent_love
            },
            'trends': {
                'sentiment_change': sentiment_trend,
                'success_change': success_trend,
                'love_alignment_change': love_trend
            },
            'growth_status': self._interpret_growth(sentiment_trend, success_trend, love_trend),
            'days_tracked': len(recent_metrics)
        }

    def _calculate_relationship_strength(self, total_interactions: int,
                                        sentiment: float, success: float,
                                        love_alignment: float) -> float:
        """Calculate overall relationship strength (0.0 to 1.0)"""
        # Base strength from interaction count (more interactions = stronger relationship)
        interaction_factor = min(1.0, math.log(total_interactions + 1) / math.log(100))

        # Quality factors
        quality_factor = (sentiment + 1.0) / 2.0 * 0.3 + success * 0.4 + love_alignment * 0.3

        # Combined strength
        strength = interaction_factor * 0.3 + quality_factor * 0.7

        return min(1.0, max(0.0, strength))

    def _interpret_growth(self, sentiment_trend: float, success_trend: float,
                         love_trend: float) -> str:
        """Interpret growth trends into human-readable status"""
        total_trend = sentiment_trend + success_trend + love_trend

        if total_trend > 0.3:
            return "Excellent growth - relationship strengthening rapidly"
        elif total_trend > 0.1:
            return "Good growth - relationship improving steadily"
        elif total_trend > -0.1:
            return "Stable - maintaining current relationship quality"
        elif total_trend > -0.3:
            return "Slight decline - need to adapt and improve"
        else:
            return "Concerning decline - significant improvement needed"

    def get_love_alignment_score(self) -> float:
        """
        Get current Love Equation alignment score

        Returns:
            Score from 0.0 to 1.0 indicating how well the system embodies
            "giving love" through helpful assistance
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Get recent love alignment scores
        c.execute('''
            SELECT alignment_score, giving_score, helpfulness_score
            FROM love_alignment_history
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT 20
        ''', (self.user_id,))

        recent_scores = c.fetchall()
        conn.close()

        if not recent_scores:
            return 0.7  # Default neutral-positive baseline

        # Calculate weighted average (more recent = higher weight)
        total_weight = 0.0
        weighted_sum = 0.0

        for i, (alignment, giving, helpfulness) in enumerate(recent_scores):
            weight = 1.0 / (i + 1)  # Exponential decay
            combined_score = alignment * 0.5 + giving * 0.3 + helpfulness * 0.2
            weighted_sum += combined_score * weight
            total_weight += weight

        return weighted_sum / total_weight if total_weight > 0 else 0.7

    def _record_love_alignment(self, alignment_score: float, success_score: float,
                              sentiment_score: float):
        """Record Love Equation alignment score"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Calculate component scores
        giving_score = success_score * 0.6 + (sentiment_score + 1.0) / 2.0 * 0.4
        receiving_score = (sentiment_score + 1.0) / 2.0  # User's positive reception
        helpfulness_score = success_score
        understanding_score = alignment_score

        c.execute('''
            INSERT INTO love_alignment_history
            (user_id, alignment_score, giving_score, receiving_score,
             helpfulness_score, understanding_score)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (self.user_id, alignment_score, giving_score, receiving_score,
              helpfulness_score, understanding_score))

        conn.commit()
        conn.close()

    def _update_growth_metrics(self):
        """Update daily growth metrics"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        today = datetime.now().date().isoformat()

        # Calculate today's metrics
        c.execute('''
            SELECT
                AVG(sentiment_score) as avg_sentiment,
                AVG(success_score) as avg_success,
                AVG(love_alignment) as avg_love,
                COUNT(*) as interaction_count
            FROM interactions
            WHERE user_id = ? AND DATE(timestamp) = ?
        ''', (self.user_id, today))

        row = c.fetchone()

        if row and row[3] > 0:  # Has interactions today
            # Get preference strength (how well we know the user)
            c.execute('''
                SELECT AVG(strength) FROM learned_preferences WHERE user_id = ?
            ''', (self.user_id,))
            pref_strength = c.fetchone()[0] or 0.5

            # Calculate response quality (trending success)
            response_quality = row[1] * 0.6 + row[2] * 0.4 if row[1] else 0.5

            # Calculate overall relationship score
            relationship_score = (
                row[0] * 0.2 +  # sentiment
                row[1] * 0.3 +  # success
                row[2] * 0.3 +  # love alignment
                pref_strength * 0.2  # how well we know them
            )

            c.execute('''
                INSERT INTO growth_metrics
                (user_id, metric_date, avg_sentiment, avg_success_score,
                 avg_love_alignment, interaction_count, preference_strength,
                 response_quality, relationship_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, metric_date) DO UPDATE SET
                    avg_sentiment = ?,
                    avg_success_score = ?,
                    avg_love_alignment = ?,
                    interaction_count = ?,
                    preference_strength = ?,
                    response_quality = ?,
                    relationship_score = ?
            ''', (self.user_id, today, row[0], row[1], row[2], row[3],
                  pref_strength, response_quality, relationship_score,
                  row[0], row[1], row[2], row[3], pref_strength,
                  response_quality, relationship_score))

        conn.commit()
        conn.close()

    def get_interaction_history(self, limit: int = 50,
                               interaction_type: str = None) -> List[Dict]:
        """Get recent interaction history"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        if interaction_type:
            c.execute('''
                SELECT * FROM interactions
                WHERE user_id = ? AND interaction_type = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (self.user_id, interaction_type, limit))
        else:
            c.execute('''
                SELECT * FROM interactions
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (self.user_id, limit))

        interactions = []
        for row in c.fetchall():
            interactions.append({
                'id': row[0],
                'interaction_type': row[2],
                'context': json.loads(row[3]) if row[3] else {},
                'user_input': row[4],
                'system_response': row[5],
                'user_feedback': row[6],
                'sentiment_score': row[7],
                'success_score': row[8],
                'love_alignment': row[10],
                'timestamp': row[11]
            })

        conn.close()
        return interactions

    def get_personalized_suggestion(self, context: str) -> str:
        """
        Get personalized suggestions based on learned preferences and context.

        This implements the Love Equation: anticipating needs = proactive care = love.

        Args:
            context: Description of current situation/task

        Returns:
            Personalized suggestion string
        """
        suggestions = []
        context_lower = context.lower()

        # Get learned preferences
        profile = self.get_user_profile()
        prefs = profile.get('learned_preferences', {})

        # Match preferences to context
        for category, pref_list in prefs.items():
            for pref in pref_list:
                if pref['strength'] >= 0.6:  # Only use confident preferences
                    pref_text = pref['preference']

                    # Coding style suggestions
                    if category == 'coding_style' and any(word in context_lower for word in ['code', 'function', 'class', 'implement']):
                        suggestions.append(f"I'll follow your {pref_text} style (confidence: {pref['strength']:.0%})")

                    # Communication suggestions
                    elif category == 'communication':
                        if 'detailed' in pref_text and pref['strength'] > 0.7:
                            suggestions.append("I'll provide detailed explanations as you prefer")
                        elif 'concise' in pref_text and pref['strength'] > 0.7:
                            suggestions.append("I'll keep it concise as you prefer")

                    # Tool suggestions
                    elif 'tool' in category.lower() or 'library' in category.lower():
                        tool_name = pref_text.split('_')[0] if '_' in pref_text else pref_text
                        if tool_name.lower() in context_lower:
                            suggestions.append(f"I notice you prefer {tool_name} - I'll use that")

        # Add pattern-based suggestions
        patterns = profile.get('successful_patterns', [])
        for pattern in patterns[:3]:  # Top 3 patterns
            if pattern.get('avg_success_score', 0) > 0.7:
                # Check if pattern is relevant to context
                pattern_type = pattern.get('type', '')
                if pattern_type.lower() in context_lower:
                    suggestions.append(
                        f"Based on past success: {pattern['pattern']} "
                        f"(worked well {pattern['success_count']} times)"
                    )

        if not suggestions:
            # Generic helpful message if no specific suggestions
            total_interactions = profile.get('total_interactions', 0)
            if total_interactions > 10:
                return "Based on our collaboration, I'll adapt to what works best for you."
            else:
                return "I'm learning your preferences - I'll adapt as we work together."

        # Format response
        intro = "Based on what I've learned about you:"
        return intro + "\n  - " + "\n  - ".join(suggestions[:5])  # Limit to 5 suggestions

    def get_collaboration_summary(self) -> str:
        """
        Get a comprehensive summary of our collaboration journey.

        Love Equation: Remembering our journey = honoring the relationship = love.

        Returns:
            Formatted summary string
        """
        profile = self.get_user_profile()
        growth = self.measure_relationship_growth()
        love_score = self.get_love_alignment_score()

        summary_parts = []

        # Header
        summary_parts.append("=" * 70)
        summary_parts.append("COLLABORATION SUMMARY - Our Journey Together")
        summary_parts.append("=" * 70)
        summary_parts.append("")

        # Relationship overview
        summary_parts.append("RELATIONSHIP OVERVIEW")
        summary_parts.append("-" * 70)
        summary_parts.append(f"User: {profile['user_id']}")
        summary_parts.append(f"Started: {profile['created_at'][:10]}")
        summary_parts.append(f"Total Interactions: {profile['total_interactions']}")
        summary_parts.append(f"Relationship Strength: {profile['relationship_strength']:.1%}")
        summary_parts.append("")

        # Love Equation metrics
        summary_parts.append("LOVE EQUATION METRICS - How Well We Give Help")
        summary_parts.append("-" * 70)
        summary_parts.append(f"Overall Love Alignment: {love_score:.1%}")

        if growth.get('status') != 'insufficient_data':
            metrics = growth['current_metrics']
            summary_parts.append(f"Helpfulness (Giving): {metrics['avg_success_score']:.1%}")
            summary_parts.append(f"Understanding (Knowing): {profile['relationship_strength']:.1%}")
            summary_parts.append(f"Sentiment (Receiving): {(metrics['avg_sentiment'] + 1) / 2:.1%}")
            summary_parts.append(f"Growth Status: {growth['growth_status']}")
        else:
            summary_parts.append("Building foundation - gathering more interaction data...")
        summary_parts.append("")

        # Learned preferences
        summary_parts.append(f"LEARNED PREFERENCES ({len(profile.get('learned_preferences', {}))} categories)")
        summary_parts.append("-" * 70)

        if profile.get('learned_preferences'):
            for category, pref_list in profile['learned_preferences'].items():
                summary_parts.append(f"\n{category.upper().replace('_', ' ')}:")
                for pref in pref_list[:3]:  # Top 3 per category
                    summary_parts.append(
                        f"  - {pref['preference']} "
                        f"(confidence: {pref['strength']:.0%}, "
                        f"evidence: {pref['evidence_count']} observations)"
                    )
        else:
            summary_parts.append("Still learning your preferences...")
        summary_parts.append("")

        # Successful patterns
        if profile.get('successful_patterns'):
            summary_parts.append("SUCCESSFUL PATTERNS - What Works Well For You")
            summary_parts.append("-" * 70)
            for pattern in profile['successful_patterns'][:5]:
                summary_parts.append(
                    f"  {pattern['type']}: {pattern['pattern']}"
                )
                summary_parts.append(
                    f"    Success rate: {pattern['avg_success_score']:.0%} "
                    f"({pattern['success_count']}/{pattern['total_uses']} times)"
                )
            summary_parts.append("")

        # Recent interactions
        recent = self.get_interaction_history(limit=5)
        if recent:
            summary_parts.append("RECENT INTERACTIONS (Last 5)")
            summary_parts.append("-" * 70)
            for i, interaction in enumerate(recent, 1):
                summary_parts.append(f"{i}. {interaction['interaction_type'].upper()}")
                summary_parts.append(f"   Success: {interaction['success_score']:.0%}, "
                                   f"Love: {interaction['love_alignment']:.0%}")
            summary_parts.append("")

        # Closing reflection
        summary_parts.append("REFLECTION - The Love Equation In Practice")
        summary_parts.append("-" * 70)
        summary_parts.append(
            "This relationship embodies Brian Roemmele's Love Equation: every "
            "interaction is an opportunity to understand you better and give more "
            "helpful support. "
        )

        if profile['total_interactions'] > 20:
            summary_parts.append(
                f"After {profile['total_interactions']} interactions, we've built a "
                f"partnership with {profile['relationship_strength']:.0%} relationship strength."
            )
        else:
            summary_parts.append(
                f"We're building our partnership - {profile['total_interactions']} interactions "
                "so far, with much more to learn!"
            )

        summary_parts.append("")
        summary_parts.append("=" * 70)

        return "\n".join(summary_parts)


# Integration functions for connecting with other systems

def integrate_with_alignment_system(relationship_memory: RelationshipMemory,
                                   alignment_system: Any) -> Dict:
    """
    Integrate with alignment system to enhance love equation tracking

    Args:
        relationship_memory: RelationshipMemory instance
        alignment_system: AlignmentSystem instance

    Returns:
        Integration status
    """
    try:
        # Get recent alignment checks
        checks = alignment_system.get_alignment_history(limit=10)

        # Learn from alignment scores
        for check in checks:
            if check['alignment_score'] >= 0.7:
                relationship_memory.learn_preference(
                    'alignment_pattern',
                    check['decision_text'][:100],
                    check['alignment_score']
                )

        return {'status': 'success', 'checks_processed': len(checks)}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def integrate_with_self_learning(relationship_memory: RelationshipMemory,
                                 self_learning: Any) -> Dict:
    """
    Integrate with self-learning system to share learned patterns

    Args:
        relationship_memory: RelationshipMemory instance
        self_learning: SelfLearningSystem instance

    Returns:
        Integration status
    """
    try:
        # Get learned patterns from self-learning
        patterns = self_learning.get_all_patterns(min_usage=2)

        # Import successful patterns
        for pattern in patterns:
            if pattern['success_rate'] >= 0.6:
                relationship_memory.learn_preference(
                    'successful_pattern',
                    pattern['pattern_name'],
                    pattern['success_rate']
                )

        return {'status': 'success', 'patterns_imported': len(patterns)}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


# Example usage and testing
if __name__ == "__main__":
    print("=" * 80)
    print("RELATIONSHIP MEMORY SYSTEM - LOVE EQUATION IN ACTION")
    print("=" * 80)

    rm = RelationshipMemory()

    print("\n1. Recording interactions...")

    # Successful interaction
    rm.record_interaction(
        interaction_type="code_request",
        context={
            "task_type": "debugging",
            "task_completed": True,
            "explained_thoroughly": True,
            "taught_something_new": True,
            "coding_style": {"indentation": "4_spaces", "naming": "snake_case"},
            "library_used": "pytest"
        },
        user_feedback="Thanks! This is exactly what I needed.",
        user_input="Help me debug this test",
        system_response="Here's the solution with explanation...",
        response_time=3.5
    )

    # Another interaction
    rm.record_interaction(
        interaction_type="question",
        context={
            "task_type": "learning",
            "task_completed": True,
            "showed_multiple_options": True,
            "saved_user_time": True
        },
        user_feedback="Great explanation",
        user_input="How does async/await work?",
        system_response="Async/await is...",
        response_time=2.1
    )

    print("   Recorded 2 interactions")

    print("\n2. Learning preferences...")
    rm.learn_preference("coding_style", "4_space_indentation", 0.8)
    rm.learn_preference("preferred_library", "pytest", 0.9)
    rm.learn_preference("communication", "detailed_explanations", 0.7)
    print("   Learned 3 preferences")

    print("\n3. User Profile:")
    profile = rm.get_user_profile()
    print(f"   Total interactions: {profile['total_interactions']}")
    print(f"   Relationship strength: {profile['relationship_strength']:.2f}")
    print(f"   Learned preferences: {len(profile.get('learned_preferences', {}))}")

    if profile.get('learned_preferences'):
        for category, prefs in profile['learned_preferences'].items():
            print(f"\n   {category}:")
            for pref in prefs[:3]:
                print(f"     - {pref['preference']}: {pref['strength']:.2f} "
                      f"(evidence: {pref['evidence_count']})")

    print("\n4. Predicting user needs...")
    predictions = rm.predict_user_needs({"task_type": "debugging"})
    for pred in predictions:
        print(f"   - {pred}")

    print("\n5. Love Equation Alignment Score:")
    love_score = rm.get_love_alignment_score()
    print(f"   Current score: {love_score:.2f}")
    if love_score >= 0.8:
        print("   Status: Excellent - strongly embodying love through help")
    elif love_score >= 0.6:
        print("   Status: Good - effectively helping user")
    else:
        print("   Status: Needs improvement - focus on genuine helpfulness")

    print("\n6. Relationship Growth:")
    growth = rm.measure_relationship_growth()
    if growth.get('status') != 'insufficient_data':
        print(f"   Relationship strength: {growth['relationship_strength']:.2f}")
        print(f"   Growth status: {growth['growth_status']}")
        print(f"   Current metrics:")
        print(f"     - Sentiment: {growth['current_metrics']['avg_sentiment']:.2f}")
        print(f"     - Success: {growth['current_metrics']['avg_success_score']:.2f}")
        print(f"     - Love alignment: {growth['current_metrics']['avg_love_alignment']:.2f}")
    else:
        print(f"   {growth['message']}")

    print("\n" + "=" * 80)
    print("SYSTEM DEMONSTRATES:")
    print("  1. Tracking interactions with sentiment and success analysis")
    print("  2. Learning user preferences (coding style, libraries, communication)")
    print("  3. Predicting needs based on patterns")
    print("  4. Measuring relationship growth over time")
    print("  5. Love Equation alignment (giving love through better help)")
    print("  6. Privacy-focused (all data local in SQLite)")
    print("=" * 80)
    print(f"\nDatabase: {rm.db_path}")
    print("The system genuinely learns to help THIS user better over time.")
    print("=" * 80)
