"""
Smart Notification System - Enhanced Edition
Production-ready intelligent notification management with learning and optimization.

Features:
1. Priority scoring with multi-factor analysis
2. User preference learning from interruptions
3. Time-of-day aware delivery
4. Interruption cost modeling with context awareness
5. Intelligent batching vs immediate alerts
6. Telegram integration with smart delivery
7. Focus time respect and do-not-disturb management
8. SQLite persistence with comprehensive analytics
"""

import sqlite3
import json
import time
import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from collections import defaultdict
import hashlib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class UrgencyLevel(Enum):
    """Notification urgency levels"""
    CRITICAL = 5
    HIGH = 4
    MEDIUM = 3
    LOW = 2
    MINIMAL = 1


class NotificationStatus(Enum):
    """Notification processing status"""
    PENDING = "pending"
    SENT = "sent"
    BATCHED = "batched"
    SUPPRESSED = "suppressed"
    DEFERRED = "deferred"
    FAILED = "failed"


@dataclass
class Notification:
    """Core notification structure"""
    id: Optional[int] = None
    title: str = ""
    message: str = ""
    urgency: UrgencyLevel = UrgencyLevel.MEDIUM
    category: str = ""
    timestamp: float = 0.0
    status: NotificationStatus = NotificationStatus.PENDING
    user_action: Optional[str] = None
    response_time: Optional[float] = None
    interruption_cost: float = 0.0
    priority_score: float = 0.0


class FocusTimeManager:
    """Manages user focus time and do-not-disturb windows"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False, timeout=10.0)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.cursor = self.conn.cursor()
        self._create_tables()

    def _create_tables(self):
        """Create focus time management tables"""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS focus_sessions (
                id INTEGER PRIMARY KEY,
                start_time REAL NOT NULL,
                end_time REAL,
                category TEXT,
                description TEXT,
                created_at REAL
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS dnd_schedule (
                id INTEGER PRIMARY KEY,
                day_of_week INTEGER,
                start_hour REAL,
                end_hour REAL,
                description TEXT,
                active BOOLEAN DEFAULT 1
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS learned_quiet_times (
                id INTEGER PRIMARY KEY,
                hour_of_day INTEGER,
                day_of_week INTEGER,
                quiet_probability REAL,
                samples_count INTEGER,
                updated_at REAL
            )
        """)

        self.conn.commit()

    def start_focus_session(self, category: str = "work",
                           duration_minutes: int = 60,
                           description: str = "") -> int:
        """Start a focus session"""
        try:
            now = time.time()
            end_time = now + (duration_minutes * 60)
            self.cursor.execute("""
                INSERT INTO focus_sessions
                (start_time, end_time, category, description, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (now, end_time, category, description, now))
            self.conn.commit()
            logger.info(f"Started focus session: {category} for {duration_minutes}min")
            return self.cursor.lastrowid
        except Exception as e:
            logger.error(f"Error starting focus session: {e}")
            return -1

    def end_focus_session(self, session_id: int) -> bool:
        """End a focus session"""
        try:
            self.cursor.execute("""
                UPDATE focus_sessions SET end_time = ? WHERE id = ?
            """, (time.time(), session_id))
            self.conn.commit()
            logger.info(f"Ended focus session: {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error ending focus session: {e}")
            return False

    def is_in_focus_mode(self) -> bool:
        """Check if currently in active focus session"""
        try:
            now = time.time()
            self.cursor.execute("""
                SELECT id FROM focus_sessions
                WHERE start_time <= ? AND (end_time > ? OR end_time IS NULL)
            """, (now, now))
            return self.cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Error checking focus mode: {e}")
            return False

    def set_dnd_schedule(self, day_of_week: int, start_hour: float,
                        end_hour: float, description: str = ""):
        """Set do-not-disturb schedule for a day"""
        try:
            self.cursor.execute("""
                INSERT OR REPLACE INTO dnd_schedule
                (day_of_week, start_hour, end_hour, description, active)
                VALUES (?, ?, ?, ?, 1)
            """, (day_of_week, start_hour, end_hour, description))
            self.conn.commit()
            logger.info(f"Set DND schedule for day {day_of_week}: {start_hour}-{end_hour}")
        except Exception as e:
            logger.error(f"Error setting DND schedule: {e}")

    def should_respect_dnd(self, hour: float, day_of_week: int) -> bool:
        """Check if currently in do-not-disturb window"""
        try:
            self.cursor.execute("""
                SELECT id FROM dnd_schedule
                WHERE day_of_week = ? AND start_hour <= ? AND end_hour > ?
                AND active = 1
            """, (day_of_week, hour, hour))
            return self.cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Error checking DND: {e}")
            return False

    def learn_quiet_time(self, hour: int, day_of_week: int, is_quiet: bool):
        """Learn when user is typically quiet"""
        try:
            self.cursor.execute("""
                SELECT quiet_probability, samples_count FROM learned_quiet_times
                WHERE hour_of_day = ? AND day_of_week = ?
            """, (hour, day_of_week))

            result = self.cursor.fetchone()
            if result:
                old_prob, count = result
                new_prob = (old_prob * count + (1.0 if is_quiet else 0.0)) / (count + 1)
                self.cursor.execute("""
                    UPDATE learned_quiet_times
                    SET quiet_probability = ?, samples_count = ?, updated_at = ?
                    WHERE hour_of_day = ? AND day_of_week = ?
                """, (new_prob, count + 1, time.time(), hour, day_of_week))
            else:
                self.cursor.execute("""
                    INSERT INTO learned_quiet_times
                    (hour_of_day, day_of_week, quiet_probability, samples_count, updated_at)
                    VALUES (?, ?, ?, 1, ?)
                """, (hour, day_of_week, 1.0 if is_quiet else 0.0, time.time()))

            self.conn.commit()
        except Exception as e:
            logger.error(f"Error learning quiet time: {e}")

    def get_quiet_probability(self, hour: int, day_of_week: int) -> float:
        """Get probability user is in quiet mode at this time"""
        try:
            self.cursor.execute("""
                SELECT quiet_probability FROM learned_quiet_times
                WHERE hour_of_day = ? AND day_of_week = ?
            """, (hour, day_of_week))

            result = self.cursor.fetchone()
            return result[0] if result else 0.3
        except Exception as e:
            logger.error(f"Error getting quiet probability: {e}")
            return 0.3


class PriorityScorer:
    """Intelligent priority scoring for notifications"""

    def __init__(self):
        self.weights = {
            "urgency": 0.40,
            "recency": 0.20,
            "user_satisfaction": 0.20,
            "category_frequency": 0.10,
            "user_engagement": 0.10
        }

    def calculate_score(self, notification: Notification,
                       satisfaction_history: List[float],
                       category_frequency: int,
                       user_engagement_rate: float) -> float:
        """Calculate comprehensive priority score"""
        score = 0.0

        # Urgency component
        urgency_score = notification.urgency.value / 5.0
        score += urgency_score * self.weights["urgency"]

        # Recency component
        age_minutes = (time.time() - notification.timestamp) / 60
        recency_score = max(0, 1.0 - (age_minutes / 60.0))
        score += recency_score * self.weights["recency"]

        # User satisfaction history
        if satisfaction_history:
            avg_satisfaction = sum(satisfaction_history) / len(satisfaction_history)
            satisfaction_score = min(1.0, avg_satisfaction / 10.0)
            score += satisfaction_score * self.weights["user_satisfaction"]

        # Category frequency (how often this category appears)
        freq_score = min(1.0, category_frequency / 20.0)
        score += freq_score * self.weights["category_frequency"]

        # User engagement rate
        engagement_score = min(1.0, user_engagement_rate)
        score += engagement_score * self.weights["user_engagement"]

        return round(score, 3)


class InterruptionCostModel:
    """Models the cost of interrupting user"""

    def __init__(self):
        self.base_costs = {
            UrgencyLevel.CRITICAL: 0.1,
            UrgencyLevel.HIGH: 0.3,
            UrgencyLevel.MEDIUM: 0.6,
            UrgencyLevel.LOW: 0.8,
            UrgencyLevel.MINIMAL: 0.95
        }

    def calculate_cost(self, urgency: UrgencyLevel, hour: int,
                      day_of_week: int, context: Dict) -> float:
        """Calculate interruption cost with time awareness"""
        base_cost = self.base_costs[urgency]

        # Time-of-day factor
        time_factor = self._calculate_time_factor(hour)

        # Context factors
        context_factor = 1.0
        if context.get("in_meeting"):
            context_factor *= 0.3
        if context.get("focused_mode"):
            context_factor *= 0.5
        if context.get("in_deep_work"):
            context_factor *= 0.4

        # Notification fatigue
        recent_count = context.get("recent_notification_count", 0)
        fatigue_factor = max(0.1, 1.0 - (recent_count * 0.08))

        # Day-of-week factor
        weekend_factor = 0.6 if day_of_week >= 5 else 1.0

        total_cost = (base_cost * time_factor * context_factor *
                     fatigue_factor * weekend_factor)

        return round(min(1.0, total_cost), 3)

    def _calculate_time_factor(self, hour: int) -> float:
        """Calculate time-of-day interruption cost factor"""
        if 9 <= hour < 17:  # Work hours
            return 1.0
        elif 22 <= hour or hour < 7:  # Sleep hours
            return 0.15
        elif 7 <= hour < 9 or 17 <= hour < 22:  # Off-peak
            return 0.6
        else:
            return 0.8


class UserPreferenceEngine:
    """Learns and adapts to user notification preferences"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False, timeout=10.0)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.cursor = self.conn.cursor()
        self._create_tables()

    def _create_tables(self):
        """Create preference learning tables"""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                id INTEGER PRIMARY KEY,
                category TEXT UNIQUE,
                preferred_window_start REAL,
                preferred_window_end REAL,
                max_daily_notifications INTEGER,
                batch_preferred BOOLEAN,
                engagement_score REAL,
                updated_at REAL
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS interaction_history (
                id INTEGER PRIMARY KEY,
                category TEXT,
                action TEXT,
                satisfaction_rating REAL,
                response_time_ms INTEGER,
                timestamp REAL
            )
        """)

        self.conn.commit()

    def record_interaction(self, category: str, action: str,
                          satisfaction: float, response_time_ms: int = 0):
        """Record user interaction"""
        try:
            self.cursor.execute("""
                INSERT INTO interaction_history
                (category, action, satisfaction_rating, response_time_ms, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (category, action, satisfaction, response_time_ms, time.time()))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error recording interaction: {e}")

    def learn_preference(self, category: str, **kwargs):
        """Learn user preference for category"""
        try:
            self.cursor.execute("""
                INSERT OR REPLACE INTO user_preferences
                (category, preferred_window_start, preferred_window_end,
                 max_daily_notifications, batch_preferred, engagement_score, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                category,
                kwargs.get("preferred_window_start", 9.0),
                kwargs.get("preferred_window_end", 17.0),
                kwargs.get("max_daily_notifications", 10),
                kwargs.get("batch_preferred", True),
                kwargs.get("engagement_score", 0.5),
                time.time()
            ))
            self.conn.commit()
            logger.info(f"Learned preference for {category}")
        except Exception as e:
            logger.error(f"Error learning preference: {e}")

    def get_preference(self, category: str) -> Dict:
        """Get learned preference for category"""
        try:
            self.cursor.execute("""
                SELECT preferred_window_start, preferred_window_end,
                       max_daily_notifications, batch_preferred, engagement_score
                FROM user_preferences WHERE category = ?
            """, (category,))

            result = self.cursor.fetchone()
            if result:
                return {
                    "window_start": result[0],
                    "window_end": result[1],
                    "max_daily": result[2],
                    "batch_preferred": result[3],
                    "engagement_score": result[4]
                }
            return None
        except Exception as e:
            logger.error(f"Error getting preference: {e}")
            return None

    def get_satisfaction_history(self, category: str, limit: int = 20) -> List[float]:
        """Get satisfaction history for category"""
        try:
            self.cursor.execute("""
                SELECT satisfaction_rating FROM interaction_history
                WHERE category = ? ORDER BY timestamp DESC LIMIT ?
            """, (category, limit))

            return [row[0] for row in self.cursor.fetchall() if row[0] is not None]
        except Exception as e:
            logger.error(f"Error getting satisfaction history: {e}")
            return []


class NotificationBatcher:
    """Intelligent batching of notifications"""

    def __init__(self, db_path: str, batch_window: int = 1800):
        self.db_path = db_path
        self.batch_window = batch_window
        self.conn = sqlite3.connect(db_path, check_same_thread=False, timeout=10.0)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.cursor = self.conn.cursor()
        self._create_tables()

    def _create_tables(self):
        """Create batching tables"""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS notification_batches (
                id INTEGER PRIMARY KEY,
                batch_key TEXT UNIQUE,
                category TEXT,
                batch_hash TEXT,
                created_at REAL,
                sent_at REAL,
                notification_count INTEGER
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS batched_notifications (
                id INTEGER PRIMARY KEY,
                batch_id INTEGER,
                notification_id INTEGER,
                FOREIGN KEY (batch_id) REFERENCES notification_batches(id)
            )
        """)

        self.conn.commit()

    def should_batch(self, urgency: UrgencyLevel) -> bool:
        """Determine if notification should be batched"""
        return urgency.value <= UrgencyLevel.LOW.value

    def add_to_batch(self, notif_id: int, category: str, batch_key: str) -> bool:
        """Add notification to batch"""
        try:
            now = time.time()

            self.cursor.execute("""
                INSERT OR IGNORE INTO notification_batches
                (batch_key, category, created_at, notification_count)
                VALUES (?, ?, ?, 0)
            """, (batch_key, category, now))

            self.cursor.execute("""
                SELECT id FROM notification_batches WHERE batch_key = ?
            """, (batch_key,))

            result = self.cursor.fetchone()
            if not result:
                self.cursor.execute("""
                    INSERT INTO notification_batches
                    (batch_key, category, created_at, notification_count)
                    VALUES (?, ?, ?, 0)
                """, (batch_key, category, now))
                self.conn.commit()
                batch_id = self.cursor.lastrowid
            else:
                batch_id = result[0]

            self.cursor.execute("""
                INSERT INTO batched_notifications (batch_id, notification_id)
                VALUES (?, ?)
            """, (batch_id, notif_id))

            self.cursor.execute("""
                UPDATE notification_batches
                SET notification_count = notification_count + 1
                WHERE id = ?
            """, (batch_id,))

            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error batching notification: {e}")
            return False

    def get_ready_batches(self) -> List[Tuple]:
        """Get batches ready to send"""
        try:
            cutoff_time = time.time() - self.batch_window
            self.cursor.execute("""
                SELECT id, batch_key, category, notification_count
                FROM notification_batches
                WHERE sent_at IS NULL AND created_at < ?
            """, (cutoff_time,))

            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting ready batches: {e}")
            return []

    def mark_batch_sent(self, batch_id: int) -> bool:
        """Mark batch as sent"""
        try:
            self.cursor.execute("""
                UPDATE notification_batches
                SET sent_at = ? WHERE id = ?
            """, (time.time(), batch_id))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error marking batch sent: {e}")
            return False


class TelegramNotifier:
    """Telegram integration for notifications"""

    def __init__(self, bot_token: Optional[str] = None,
                 chat_id: Optional[str] = None):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = "https://api.telegram.org/bot"

    def send_notification(self, notification: Notification) -> bool:
        """Send notification via Telegram"""
        if not self.bot_token or not self.chat_id:
            logger.debug("Telegram not configured, skipping send")
            return False

        try:
            message = f"""
*{notification.urgency.name}*: {notification.title}

{notification.message}

_Category: {notification.category}_
_Time: {datetime.fromtimestamp(notification.timestamp).strftime('%H:%M:%S')}_
            """.strip()

            url = f"{self.api_url}{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }

            response = requests.post(url, json=payload, timeout=5)
            if response.status_code == 200:
                logger.info(f"Telegram sent: {notification.title}")
                return True
            else:
                logger.error(f"Telegram failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Telegram error: {e}")
            return False

    def send_batch_summary(self, category: str, count: int) -> bool:
        """Send batch summary"""
        if not self.bot_token or not self.chat_id:
            return False

        try:
            message = f"📦 {count} notifications from {category}"
            url = f"{self.api_url}{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }

            response = requests.post(url, json=payload, timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Batch summary error: {e}")
            return False


class SmartNotificationSystem:
    """Main production-ready smart notification orchestrator"""

    def __init__(self, db_path: str = "smart_notifications.db",
                 telegram_bot_token: Optional[str] = None,
                 telegram_chat_id: Optional[str] = None):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False, timeout=10.0)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.cursor = self.conn.cursor()

        # Initialize components
        self.preference_engine = UserPreferenceEngine(db_path)
        self.focus_manager = FocusTimeManager(db_path)
        self.priority_scorer = PriorityScorer()
        self.interruption_model = InterruptionCostModel()
        self.batcher = NotificationBatcher(db_path)
        self.telegram = TelegramNotifier(telegram_bot_token, telegram_chat_id)

        self._create_tables()

    def _create_tables(self):
        """Create core notification tables"""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                message TEXT,
                urgency TEXT NOT NULL,
                category TEXT,
                timestamp REAL NOT NULL,
                status TEXT DEFAULT 'pending',
                user_action TEXT,
                response_time_ms INTEGER,
                interruption_cost REAL,
                priority_score REAL,
                deferred_until REAL
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS category_analytics (
                id INTEGER PRIMARY KEY,
                category TEXT UNIQUE,
                notification_count INTEGER DEFAULT 0,
                total_satisfaction REAL DEFAULT 0,
                avg_satisfaction REAL DEFAULT 0,
                last_updated REAL
            )
        """)

        self.conn.commit()

    def classify_urgency(self, title: str, message: str,
                        category: str) -> UrgencyLevel:
        """Classify notification urgency"""
        critical_keywords = ["critical", "emergency", "urgent", "alert", "error", "failure"]
        high_keywords = ["warning", "important", "issue", "problem", "failed"]
        low_keywords = ["info", "update", "reminder", "note"]

        text = f"{title} {message}".lower()

        if any(kw in text for kw in critical_keywords):
            return UrgencyLevel.CRITICAL
        elif any(kw in text for kw in high_keywords):
            return UrgencyLevel.HIGH
        elif any(kw in text for kw in low_keywords):
            return UrgencyLevel.LOW

        return UrgencyLevel.MEDIUM

    def should_defer(self, notification: Notification,
                    user_context: Dict) -> Tuple[bool, Optional[float]]:
        """Determine if notification should be deferred"""
        now = datetime.now()
        hour = now.hour
        day_of_week = now.weekday()

        # Check focus mode
        if self.focus_manager.is_in_focus_mode():
            if notification.urgency.value <= UrgencyLevel.MEDIUM.value:
                defer_until = time.time() + 1800  # 30 minutes
                return True, defer_until

        # Check DND schedule
        if self.focus_manager.should_respect_dnd(hour, day_of_week):
            if notification.urgency != UrgencyLevel.CRITICAL:
                defer_until = time.time() + 3600  # 1 hour
                return True, defer_until

        # Check learned quiet times
        quiet_prob = self.focus_manager.get_quiet_probability(hour, day_of_week)
        if quiet_prob > 0.7 and notification.urgency.value <= UrgencyLevel.MEDIUM.value:
            defer_until = time.time() + 1800
            return True, defer_until

        return False, None

    def enqueue_notification(self, title: str, message: str,
                            category: str = "general",
                            urgency: Optional[UrgencyLevel] = None,
                            user_context: Optional[Dict] = None) -> int:
        """Enqueue notification for processing"""
        if urgency is None:
            urgency = self.classify_urgency(title, message, category)

        if user_context is None:
            user_context = {}

        notification = Notification(
            title=title,
            message=message,
            urgency=urgency,
            category=category,
            timestamp=time.time()
        )

        # Check if should defer
        should_defer, defer_until = self.should_defer(notification, user_context)

        try:
            now = time.time()
            hour = datetime.now().hour
            day_of_week = datetime.now().weekday()

            # Calculate interruption cost
            cost = self.interruption_model.calculate_cost(
                urgency, hour, day_of_week, user_context
            )

            # Determine status
            if should_defer:
                status = NotificationStatus.DEFERRED.value
            else:
                status = NotificationStatus.PENDING.value

            self.cursor.execute("""
                INSERT INTO notifications
                (title, message, urgency, category, timestamp, status,
                 interruption_cost, deferred_until)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (title, message, urgency.name, category, now, status,
                  cost, defer_until if should_defer else None))

            self.conn.commit()
            notification.id = self.cursor.lastrowid

            self._update_category_analytics(category)

            logger.info(f"Enqueued: {title} (ID: {notification.id}, Status: {status})")
            return notification.id

        except Exception as e:
            logger.error(f"Error enqueuing notification: {e}")
            return -1

    def _update_category_analytics(self, category: str):
        """Update category analytics"""
        try:
            self.cursor.execute("""
                INSERT OR IGNORE INTO category_analytics
                (category, notification_count, last_updated)
                VALUES (?, 0, ?)
            """, (category, time.time()))

            self.cursor.execute("""
                UPDATE category_analytics
                SET notification_count = notification_count + 1,
                    last_updated = ?
                WHERE category = ?
            """, (time.time(), category))

            self.conn.commit()
        except Exception as e:
            logger.error(f"Error updating analytics: {e}")

    def process_notifications(self) -> Dict:
        """Process pending and deferred notifications"""
        try:
            now = time.time()

            # Process deferred notifications that are ready
            self.cursor.execute("""
                UPDATE notifications
                SET status = ?
                WHERE status = ? AND deferred_until <= ?
            """, (NotificationStatus.PENDING.value, NotificationStatus.DEFERRED.value, now))

            self.conn.commit()

            # Get pending notifications
            self.cursor.execute("""
                SELECT id, title, message, urgency, category, timestamp
                FROM notifications WHERE status = ?
                ORDER BY urgency DESC, timestamp ASC
            """, (NotificationStatus.PENDING.value,))

            pending = self.cursor.fetchall()
            sent_count = 0
            batched_count = 0

            for row in pending:
                notif_id, title, message, urgency_str, category, ts = row
                urgency = UrgencyLevel[urgency_str]

                notification = Notification(
                    id=notif_id,
                    title=title,
                    message=message,
                    urgency=urgency,
                    category=category,
                    timestamp=ts
                )

                # Calculate priority
                satisfaction = self.preference_engine.get_satisfaction_history(category)
                self.cursor.execute("""
                    SELECT notification_count FROM category_analytics
                    WHERE category = ?
                """, (category,))
                freq_result = self.cursor.fetchone()
                frequency = freq_result[0] if freq_result else 0

                priority_score = self.priority_scorer.calculate_score(
                    notification, satisfaction, frequency, 0.7
                )

                # Decide: batch or send
                if self.batcher.should_batch(urgency):
                    batch_key = f"{category}_{int(now / 3600)}"
                    self.batcher.add_to_batch(notif_id, category, batch_key)

                    self.cursor.execute("""
                        UPDATE notifications
                        SET status = ?, priority_score = ?
                        WHERE id = ?
                    """, (NotificationStatus.BATCHED.value, priority_score, notif_id))

                    batched_count += 1
                else:
                    # Send immediately
                    self.telegram.send_notification(notification)

                    self.cursor.execute("""
                        UPDATE notifications
                        SET status = ?, priority_score = ?
                        WHERE id = ?
                    """, (NotificationStatus.SENT.value, priority_score, notif_id))

                    sent_count += 1

            self.conn.commit()

            # Process ready batches
            batches = self.batcher.get_ready_batches()
            batch_sent = 0
            for batch_id, batch_key, category, count in batches:
                if self.telegram.send_batch_summary(category, count):
                    self.batcher.mark_batch_sent(batch_id)
                    batch_sent += 1

            return {
                "sent": sent_count,
                "batched": batched_count,
                "batch_sent": batch_sent,
                "total": sent_count + batched_count
            }

        except Exception as e:
            logger.error(f"Error processing notifications: {e}")
            return {"error": str(e)}

    def record_user_interaction(self, notif_id: int, action: str,
                               satisfaction: float, response_time_ms: int = 0):
        """Record user interaction with notification"""
        try:
            self.cursor.execute("""
                UPDATE notifications
                SET user_action = ?, response_time_ms = ?
                WHERE id = ?
            """, (action, response_time_ms, notif_id))

            self.cursor.execute("""
                SELECT category FROM notifications WHERE id = ?
            """, (notif_id,))

            result = self.cursor.fetchone()
            if result:
                category = result[0]
                self.preference_engine.record_interaction(
                    category, action, satisfaction, response_time_ms
                )

                # Update category analytics
                self.cursor.execute("""
                    UPDATE category_analytics
                    SET total_satisfaction = total_satisfaction + ?,
                        avg_satisfaction = total_satisfaction / notification_count
                    WHERE category = ?
                """, (satisfaction, category))

            self.conn.commit()
            logger.info(f"Recorded interaction for notification {notif_id}")
        except Exception as e:
            logger.error(f"Error recording interaction: {e}")

    def get_system_stats(self) -> Dict:
        """Get comprehensive system statistics"""
        try:
            self.cursor.execute("""
                SELECT status, COUNT(*) FROM notifications GROUP BY status
            """)
            status_stats = dict(self.cursor.fetchall())

            self.cursor.execute("""
                SELECT urgency, COUNT(*) FROM notifications GROUP BY urgency
            """)
            urgency_stats = dict(self.cursor.fetchall())

            self.cursor.execute("""
                SELECT AVG(priority_score), MAX(priority_score), MIN(priority_score)
                FROM notifications WHERE priority_score IS NOT NULL
            """)
            score_stats = self.cursor.fetchone()

            self.cursor.execute("""
                SELECT category, notification_count, avg_satisfaction
                FROM category_analytics ORDER BY notification_count DESC
            """)
            category_stats = self.cursor.fetchall()

            return {
                "by_status": status_stats,
                "by_urgency": urgency_stats,
                "priority_scores": {
                    "avg": round(score_stats[0], 3) if score_stats[0] else None,
                    "max": round(score_stats[1], 3) if score_stats[1] else None,
                    "min": round(score_stats[2], 3) if score_stats[2] else None
                },
                "top_categories": category_stats[:5]
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}

    def close(self):
        """Close database connection"""
        try:
            self.conn.close()
            logger.info("Database closed")
        except Exception as e:
            logger.error(f"Error closing database: {e}")


# ============================================================================
# PRODUCTION TEST CODE
# ============================================================================

def run_production_tests():
    """Comprehensive production test suite"""

    print("\n" + "="*80)
    print("SMART NOTIFICATION SYSTEM - PRODUCTION TEST SUITE")
    print("="*80 + "\n")

    db_path = "smart_notifications_test.db"
    telegram_chat_id = "5791597360"

    sns = SmartNotificationSystem(db_path, telegram_chat_id=telegram_chat_id)

    try:
        # Test 1: Urgency Classification
        print("[TEST 1] Urgency Classification")
        print("-" * 80)

        test_cases = [
            ("CRITICAL Database Failure", "Prod database is down", "database", UrgencyLevel.CRITICAL),
            ("Warning: High Memory", "Memory usage above 90%", "system", UrgencyLevel.HIGH),
            ("Reminder: Team Meeting", "Meeting starts in 10 minutes", "calendar", UrgencyLevel.LOW),
            ("Daily Summary", "Your digest is ready", "digest", UrgencyLevel.LOW),
        ]

        for title, msg, cat, expected_urgency in test_cases:
            classified = sns.classify_urgency(title, msg, cat)
            status = "[PASS]" if classified == expected_urgency else "[FAIL]"
            print(f"{status} '{title}' -> {classified.name} (expected {expected_urgency.name})")

        # Test 2: Enqueue Various Notifications
        print("\n[TEST 2] Enqueue Notifications with Various Urgencies")
        print("-" * 80)

        notifications = [
            ("System Error", "Database connection failed", "database", UrgencyLevel.CRITICAL),
            ("Build Warning", "Test coverage 75%", "build", UrgencyLevel.HIGH),
            ("Daily Digest", "Your notifications summary", "digest", UrgencyLevel.LOW),
            ("New Feature", "Feature X is available", "product", UrgencyLevel.MEDIUM),
        ]

        notif_ids = []
        for title, msg, cat, urg in notifications:
            notif_id = sns.enqueue_notification(
                title, msg, cat, urg,
                {"in_meeting": False, "focused_mode": False, "recent_notification_count": 0}
            )
            notif_ids.append(notif_id)
            print(f"[OK] Enqueued '{title}' (ID: {notif_id}, Urgency: {urg.name})")

        # Test 3: Focus Time Management
        print("\n[TEST 3] Focus Time Management")
        print("-" * 80)

        session_id = sns.focus_manager.start_focus_session("deep_work", 60, "Code review")
        print(f"[OK] Started focus session {session_id}")

        in_focus = sns.focus_manager.is_in_focus_mode()
        print(f"[OK] In focus mode: {in_focus}")

        sns.focus_manager.end_focus_session(session_id)
        print(f"[OK] Ended focus session {session_id}")

        # Test 4: DND Schedule
        print("\n[TEST 4] Do-Not-Disturb Schedule")
        print("-" * 80)

        sns.focus_manager.set_dnd_schedule(0, 22.0, 7.0, "Night sleep")
        sns.focus_manager.set_dnd_schedule(1, 22.0, 7.0, "Night sleep")
        print("[OK] Set DND schedule: 22:00-07:00")

        # Test 5: Preference Learning
        print("\n[TEST 5] User Preference Learning")
        print("-" * 80)

        sns.preference_engine.learn_preference(
            "database",
            preferred_window_start=8.0,
            preferred_window_end=18.0,
            max_daily_notifications=20,
            batch_preferred=True,
            engagement_score=0.8
        )
        print("[OK] Learned preference for 'database' category")

        pref = sns.preference_engine.get_preference("database")
        if pref:
            print(f"  - Window: {pref['window_start']:.1f}-{pref['window_end']:.1f}")
            print(f"  - Batch preferred: {pref['batch_preferred']}")
            print(f"  - Engagement: {pref['engagement_score']}")

        # Test 6: Interruption Cost Modeling
        print("\n[TEST 6] Interruption Cost Modeling")
        print("-" * 80)

        contexts = [
            (9, 0, {"in_meeting": False, "focused_mode": False, "recent_notification_count": 0}),
            (14, 0, {"in_meeting": True, "focused_mode": False, "recent_notification_count": 0}),
            (23, 0, {"in_meeting": False, "focused_mode": True, "recent_notification_count": 5}),
            (6, 0, {"in_meeting": False, "focused_mode": False, "recent_notification_count": 0}),
        ]

        time_labels = {9: "Work Hours", 14: "In Meeting", 23: "Late Night", 6: "Early Morning"}

        for hour, day, context in contexts:
            cost = sns.interruption_model.calculate_cost(
                UrgencyLevel.MEDIUM, hour, day, context
            )
            print(f"[OK] {time_labels[hour]}: Interruption cost = {cost:.3f}")

        # Test 7: Priority Scoring
        print("\n[TEST 7] Priority Scoring")
        print("-" * 80)

        notif = Notification(
            title="Test Notification",
            message="Testing priority scoring",
            urgency=UrgencyLevel.HIGH,
            timestamp=time.time(),
            category="test"
        )

        satisfaction = [8.5, 8.0, 7.5, 8.2]
        score = sns.priority_scorer.calculate_score(notif, satisfaction, 5, 0.75)
        print(f"[OK] Priority score for HIGH urgency: {score:.3f}")

        # Test 8: Process Notifications
        print("\n[TEST 8] Process Notifications")
        print("-" * 80)

        result = sns.process_notifications()
        print(f"[OK] Processing results:")
        print(f"  - Sent immediately: {result.get('sent', 0)}")
        print(f"  - Batched: {result.get('batched', 0)}")
        print(f"  - Batch sent: {result.get('batch_sent', 0)}")
        print(f"  - Total processed: {result.get('total', 0)}")

        # Test 9: Record User Interactions
        print("\n[TEST 9] Record User Interactions")
        print("-" * 80)

        if notif_ids:
            sns.record_user_interaction(notif_ids[0], "dismissed", 6.5, 2000)
            sns.record_user_interaction(notif_ids[1], "opened", 8.5, 5000)
            print("[OK] Recorded user interactions")

        # Test 10: System Statistics
        print("\n[TEST 10] System Statistics")
        print("-" * 80)

        stats = sns.get_system_stats()
        print(f"[OK] Statistics:")
        print(f"  - By status: {stats.get('by_status', {})}")
        print(f"  - By urgency: {stats.get('by_urgency', {})}")
        scores = stats.get('priority_scores', {})
        print(f"  - Priority scores (avg/max/min): {scores.get('avg')}/{scores.get('max')}/{scores.get('min')}")

        # Test 11: Batching Decision Logic
        print("\n[TEST 11] Batching Decision Logic")
        print("-" * 80)

        should_batch_low = sns.batcher.should_batch(UrgencyLevel.LOW)
        should_batch_critical = sns.batcher.should_batch(UrgencyLevel.CRITICAL)
        print(f"[OK] Should batch LOW urgency: {should_batch_low}")
        print(f"[OK] Should batch CRITICAL urgency: {should_batch_critical}")

        # Test 12: Quiet Time Learning
        print("\n[TEST 12] Quiet Time Learning")
        print("-" * 80)

        for _ in range(5):
            sns.focus_manager.learn_quiet_time(14, 0, True)  # Monday 2PM
        for _ in range(2):
            sns.focus_manager.learn_quiet_time(14, 0, False)

        quiet_prob = sns.focus_manager.get_quiet_probability(14, 0)
        print(f"[OK] Quiet probability for Monday 2PM: {quiet_prob:.3f}")

        print("\n" + "="*80)
        print("ALL PRODUCTION TESTS COMPLETED SUCCESSFULLY")
        print("="*80 + "\n")

    finally:
        sns.close()
        import os
        try:
            time.sleep(0.5)
            if os.path.exists(db_path):
                os.remove(db_path)
                print(f"Cleaned up test database: {db_path}")
        except Exception as e:
            print(f"Note: Could not clean up test database: {e}")


if __name__ == "__main__":
    run_production_tests()
