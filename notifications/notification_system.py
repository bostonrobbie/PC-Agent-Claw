"""
Smart Notification System
A production-ready notification system that learns user preferences,
manages priority, and optimizes notification timing.
"""

import sqlite3
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import requests
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class UrgencyLevel(Enum):
    """Urgency classification levels"""
    CRITICAL = 5
    HIGH = 4
    MEDIUM = 3
    LOW = 2
    MINIMAL = 1


class NotificationStatus(Enum):
    """Notification status tracking"""
    PENDING = "pending"
    SENT = "sent"
    BATCHED = "batched"
    SUPPRESSED = "suppressed"
    FAILED = "failed"


@dataclass
class Notification:
    """Core notification data structure"""
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


class InterruptionCostModel:
    """Models the cost of interrupting user based on context"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._initialize_cost_model()

    def _initialize_cost_model(self):
        """Initialize default interruption costs"""
        self.base_costs = {
            UrgencyLevel.CRITICAL: 0.1,  # Low cost - must interrupt
            UrgencyLevel.HIGH: 0.3,
            UrgencyLevel.MEDIUM: 0.6,
            UrgencyLevel.LOW: 0.8,
            UrgencyLevel.MINIMAL: 0.95  # High cost - suppress if possible
        }

    def calculate_cost(self, urgency: UrgencyLevel, hour: int,
                       user_context: Dict) -> float:
        """Calculate interruption cost based on multiple factors"""
        base_cost = self.base_costs[urgency]

        # Time-of-day adjustment
        if 9 <= hour < 17:  # Work hours
            time_factor = 1.0
        elif 22 <= hour or hour < 7:  # Sleep hours
            time_factor = 0.5 if urgency == UrgencyLevel.CRITICAL else 0.2
        else:
            time_factor = 0.7

        # User activity context
        activity_factor = 1.0
        if user_context.get("in_meeting"):
            activity_factor = 0.3
        elif user_context.get("focused_mode"):
            activity_factor = 0.5

        # Notification fatigue - suppress if too many recent
        recent_count = user_context.get("recent_notification_count", 0)
        fatigue_factor = max(0.1, 1.0 - (recent_count * 0.1))

        return base_cost * time_factor * activity_factor * fatigue_factor


class UserPreferenceLearn:
    """Learns and adapts user preferences over time"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._create_tables()

    def _create_tables(self):
        """Create preference learning tables"""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                id INTEGER PRIMARY KEY,
                category TEXT UNIQUE,
                preferred_time_window TEXT,
                max_daily_notifications INTEGER,
                batch_similar BOOLEAN,
                do_not_disturb_hours TEXT,
                created_at REAL,
                updated_at REAL
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS preference_history (
                id INTEGER PRIMARY KEY,
                category TEXT,
                action TEXT,
                timestamp REAL,
                user_satisfaction REAL
            )
        """)

        self.conn.commit()

    def record_interaction(self, category: str, action: str,
                          satisfaction: float):
        """Record user interaction with notifications"""
        try:
            self.cursor.execute("""
                INSERT INTO preference_history
                (category, action, timestamp, user_satisfaction)
                VALUES (?, ?, ?, ?)
            """, (category, action, time.time(), satisfaction))
            self.conn.commit()
            logger.info(f"Recorded interaction: {category} - {action}")
        except Exception as e:
            logger.error(f"Error recording interaction: {e}")

    def get_category_preference(self, category: str) -> Dict:
        """Get learned preferences for a category"""
        try:
            self.cursor.execute("""
                SELECT preferred_time_window, max_daily_notifications,
                       batch_similar, do_not_disturb_hours
                FROM user_preferences WHERE category = ?
            """, (category,))

            result = self.cursor.fetchone()
            if result:
                return {
                    "preferred_time_window": result[0],
                    "max_daily_notifications": result[1],
                    "batch_similar": result[2],
                    "do_not_disturb_hours": result[3]
                }
            return None
        except Exception as e:
            logger.error(f"Error getting preference: {e}")
            return None

    def learn_preference(self, category: str, **kwargs):
        """Learn and update user preference"""
        try:
            now = time.time()
            self.cursor.execute("""
                INSERT OR REPLACE INTO user_preferences
                (category, preferred_time_window, max_daily_notifications,
                 batch_similar, do_not_disturb_hours, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                category,
                kwargs.get("preferred_time_window", "09:00-17:00"),
                kwargs.get("max_daily_notifications", 10),
                kwargs.get("batch_similar", True),
                kwargs.get("do_not_disturb_hours", "22:00-07:00"),
                now,
                now
            ))
            self.conn.commit()
            logger.info(f"Learned preference for {category}")
        except Exception as e:
            logger.error(f"Error learning preference: {e}")


class PriorityScorer:
    """Scores notifications based on multiple factors"""

    def __init__(self):
        self.weights = {
            "urgency": 0.35,
            "recency": 0.25,
            "user_history": 0.20,
            "category_trend": 0.20
        }

    def calculate_score(self, notification: Notification,
                       user_history: List[float],
                       category_trend: float) -> float:
        """Calculate priority score for notification"""
        score = 0.0

        # Urgency component (0-1)
        urgency_score = notification.urgency.value / 5.0
        score += urgency_score * self.weights["urgency"]

        # Recency component (0-1)
        age_seconds = time.time() - notification.timestamp
        recency_score = max(0, 1.0 - (age_seconds / 3600.0))
        score += recency_score * self.weights["recency"]

        # User history component (0-1)
        if user_history:
            avg_user_history = sum(user_history) / len(user_history)
            history_score = min(1.0, avg_user_history / 10.0)
            score += history_score * self.weights["user_history"]

        # Category trend component (0-1)
        trend_score = min(1.0, category_trend / 10.0)
        score += trend_score * self.weights["category_trend"]

        return round(score, 3)


class BatchingEngine:
    """Handles batching of low-priority notifications"""

    def __init__(self, db_path: str, batch_window: int = 3600):
        """
        Initialize batching engine

        Args:
            db_path: Path to SQLite database
            batch_window: Time window in seconds to batch notifications
        """
        self.db_path = db_path
        self.batch_window = batch_window
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._create_tables()

    def _create_tables(self):
        """Create batching tables"""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS notification_batches (
                id INTEGER PRIMARY KEY,
                batch_key TEXT UNIQUE,
                category TEXT,
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

    def should_batch(self, notification: Notification) -> bool:
        """Determine if notification should be batched"""
        return notification.urgency.value <= UrgencyLevel.LOW.value

    def add_to_batch(self, notification: Notification, batch_key: str):
        """Add notification to batch"""
        try:
            now = time.time()

            # Get or create batch
            self.cursor.execute("""
                INSERT OR IGNORE INTO notification_batches
                (batch_key, category, created_at, notification_count)
                VALUES (?, ?, ?, 0)
            """, (batch_key, notification.category, now))

            self.cursor.execute("""
                SELECT id FROM notification_batches WHERE batch_key = ?
            """, (batch_key,))

            batch_id = self.cursor.fetchone()[0]

            # Add notification to batch
            self.cursor.execute("""
                INSERT INTO batched_notifications (batch_id, notification_id)
                VALUES (?, ?)
            """, (batch_id, notification.id))

            self.cursor.execute("""
                UPDATE notification_batches
                SET notification_count = notification_count + 1
                WHERE id = ?
            """, (batch_id,))

            self.conn.commit()
            logger.info(f"Added notification to batch: {batch_key}")
        except Exception as e:
            logger.error(f"Error adding to batch: {e}")

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

    def mark_batch_sent(self, batch_id: int):
        """Mark batch as sent"""
        try:
            self.cursor.execute("""
                UPDATE notification_batches
                SET sent_at = ? WHERE id = ?
            """, (time.time(), batch_id))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error marking batch sent: {e}")


class TelegramNotifier:
    """Handles Telegram notifications"""

    def __init__(self, bot_token: Optional[str] = None,
                 chat_id: Optional[str] = None):
        """
        Initialize Telegram notifier

        Args:
            bot_token: Telegram bot token
            chat_id: Chat ID for notifications
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = "https://api.telegram.org/bot"

    def send_notification(self, notification: Notification) -> bool:
        """Send notification via Telegram"""
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram not configured")
            return False

        try:
            message = f"""
*{notification.urgency.name}*: {notification.title}

{notification.message}

_Category: {notification.category}_
_Time: {datetime.fromtimestamp(notification.timestamp).strftime('%Y-%m-%d %H:%M:%S')}_
            """.strip()

            url = f"{self.api_url}{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }

            response = requests.post(url, json=payload, timeout=5)
            if response.status_code == 200:
                logger.info(f"Telegram notification sent: {notification.title}")
                return True
            else:
                logger.error(f"Telegram error: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error sending Telegram notification: {e}")
            return False

    def send_batch_summary(self, batch_summary: str) -> bool:
        """Send batch summary via Telegram"""
        if not self.bot_token or not self.chat_id:
            return False

        try:
            url = f"{self.api_url}{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": f"📦 *Batch Summary*\n\n{batch_summary}",
                "parse_mode": "Markdown"
            }

            response = requests.post(url, json=payload, timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error sending batch summary: {e}")
            return False


class NotificationSystem:
    """Main Smart Notification System orchestrator"""

    def __init__(self, db_path: str = "notification_system.db",
                 telegram_bot_token: Optional[str] = None,
                 telegram_chat_id: Optional[str] = None):
        """
        Initialize notification system

        Args:
            db_path: Path to SQLite database
            telegram_bot_token: Optional Telegram bot token
            telegram_chat_id: Optional Telegram chat ID
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()

        # Initialize components
        self.preference_learner = UserPreferenceLearn(db_path)
        self.batching_engine = BatchingEngine(db_path)
        self.priority_scorer = PriorityScorer()
        self.interruption_model = InterruptionCostModel(db_path)
        self.telegram = TelegramNotifier(telegram_bot_token, telegram_chat_id)

        self._create_tables()

    def _create_tables(self):
        """Create main notification tables"""
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
                response_time REAL,
                interruption_cost REAL,
                priority_score REAL
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS category_trends (
                id INTEGER PRIMARY KEY,
                category TEXT UNIQUE,
                notification_count INTEGER DEFAULT 0,
                last_updated REAL
            )
        """)

        self.conn.commit()

    def classify_urgency(self, keywords: List[str],
                        category: str) -> UrgencyLevel:
        """Classify notification urgency based on keywords"""
        critical_keywords = ["critical", "emergency", "urgent", "alert", "error"]
        high_keywords = ["warning", "important", "issue", "problem"]
        low_keywords = ["info", "update", "reminder"]

        text = " ".join(keywords).lower()

        if any(keyword in text for keyword in critical_keywords):
            return UrgencyLevel.CRITICAL
        elif any(keyword in text for keyword in high_keywords):
            return UrgencyLevel.HIGH
        elif any(keyword in text for keyword in low_keywords):
            return UrgencyLevel.LOW

        return UrgencyLevel.MEDIUM

    def should_suppress(self, notification: Notification,
                       user_context: Dict) -> bool:
        """Determine if notification should be suppressed"""
        hour = datetime.now().hour
        cost = self.interruption_model.calculate_cost(
            notification.urgency, hour, user_context
        )

        # Suppress if cost exceeds threshold (unless critical)
        if cost > 0.7 and notification.urgency != UrgencyLevel.CRITICAL:
            logger.info(f"Suppressing notification due to high interruption cost: {cost}")
            return True

        return False

    def enqueue_notification(self, title: str, message: str,
                            category: str = "general",
                            urgency: Optional[UrgencyLevel] = None,
                            user_context: Optional[Dict] = None) -> int:
        """
        Enqueue notification for processing

        Args:
            title: Notification title
            message: Notification message
            category: Notification category
            urgency: Urgency level (auto-classified if None)
            user_context: Dict with user context info

        Returns:
            Notification ID
        """
        if urgency is None:
            urgency = self.classify_urgency([title, message], category)

        if user_context is None:
            user_context = {}

        notification = Notification(
            title=title,
            message=message,
            urgency=urgency,
            category=category,
            timestamp=time.time(),
            status=NotificationStatus.PENDING
        )

        # Check if should suppress
        if self.should_suppress(notification, user_context):
            notification.status = NotificationStatus.SUPPRESSED
            status = "suppressed"
        else:
            status = "pending"

        # Store notification
        try:
            self.cursor.execute("""
                INSERT INTO notifications
                (title, message, urgency, category, timestamp, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (notification.title, notification.message,
                  notification.urgency.name, notification.category,
                  notification.timestamp, status))

            self.conn.commit()
            notification.id = self.cursor.lastrowid

            # Update category trend
            self._update_category_trend(category)

            logger.info(f"Enqueued notification: {title} (ID: {notification.id})")
            return notification.id
        except Exception as e:
            logger.error(f"Error enqueuing notification: {e}")
            return -1

    def _update_category_trend(self, category: str):
        """Update category trend count"""
        try:
            now = time.time()
            self.cursor.execute("""
                INSERT OR IGNORE INTO category_trends
                (category, notification_count, last_updated)
                VALUES (?, 0, ?)
            """, (category, now))

            self.cursor.execute("""
                UPDATE category_trends
                SET notification_count = notification_count + 1,
                    last_updated = ?
                WHERE category = ?
            """, (now, category))

            self.conn.commit()
        except Exception as e:
            logger.error(f"Error updating category trend: {e}")

    def process_notifications(self) -> Dict:
        """Process pending notifications"""
        try:
            self.cursor.execute("""
                SELECT id, title, message, urgency, category, timestamp
                FROM notifications WHERE status = 'pending'
                ORDER BY
                    CASE urgency
                        WHEN 'CRITICAL' THEN 1
                        WHEN 'HIGH' THEN 2
                        WHEN 'MEDIUM' THEN 3
                        WHEN 'LOW' THEN 4
                        WHEN 'MINIMAL' THEN 5
                    END,
                    timestamp DESC
            """)

            pending = self.cursor.fetchall()
            sent_count = 0
            batched_count = 0

            for row in pending:
                notification_id, title, message, urgency_str, category, ts = row
                urgency = UrgencyLevel[urgency_str]

                notification = Notification(
                    id=notification_id,
                    title=title,
                    message=message,
                    urgency=urgency,
                    category=category,
                    timestamp=ts,
                    status=NotificationStatus.PENDING
                )

                # Calculate priority
                user_history = self._get_user_history(category)
                trend = self._get_category_trend(category)
                priority_score = self.priority_scorer.calculate_score(
                    notification, user_history, trend
                )

                # Decide: send immediately or batch
                if self.batching_engine.should_batch(notification):
                    batch_key = f"{category}_{int(time.time() / 3600)}"
                    self.batching_engine.add_to_batch(notification, batch_key)

                    self.cursor.execute("""
                        UPDATE notifications
                        SET status = ?, priority_score = ?
                        WHERE id = ?
                    """, (NotificationStatus.BATCHED.value, priority_score, notification_id))

                    batched_count += 1
                else:
                    # Send immediately
                    self.telegram.send_notification(notification)

                    self.cursor.execute("""
                        UPDATE notifications
                        SET status = ?, priority_score = ?
                        WHERE id = ?
                    """, (NotificationStatus.SENT.value, priority_score, notification_id))

                    sent_count += 1

            self.conn.commit()

            # Process ready batches
            batches = self.batching_engine.get_ready_batches()
            batch_sent = self._process_batches(batches)

            return {
                "sent": sent_count,
                "batched": batched_count,
                "batch_sent": batch_sent,
                "total_processed": sent_count + batched_count
            }
        except Exception as e:
            logger.error(f"Error processing notifications: {e}")
            return {"error": str(e)}

    def _process_batches(self, batches: List[Tuple]) -> int:
        """Process and send ready batches"""
        sent_count = 0
        for batch_id, batch_key, category, notif_count in batches:
            summary = f"Category: {category}\nNotifications: {notif_count}"
            if self.telegram.send_batch_summary(summary):
                self.batching_engine.mark_batch_sent(batch_id)
                sent_count += 1

        return sent_count

    def _get_user_history(self, category: str, limit: int = 10) -> List[float]:
        """Get user satisfaction history for category"""
        try:
            self.cursor.execute("""
                SELECT user_satisfaction FROM preference_history
                WHERE category = ? ORDER BY timestamp DESC LIMIT ?
            """, (category, limit))

            results = self.cursor.fetchall()
            return [row[0] for row in results if row[0] is not None]
        except Exception as e:
            logger.error(f"Error getting user history: {e}")
            return []

    def _get_category_trend(self, category: str) -> float:
        """Get recent trend for category"""
        try:
            self.cursor.execute("""
                SELECT notification_count FROM category_trends
                WHERE category = ?
            """, (category,))

            result = self.cursor.fetchone()
            return result[0] if result else 0.0
        except Exception as e:
            logger.error(f"Error getting category trend: {e}")
            return 0.0

    def record_user_action(self, notification_id: int, action: str,
                          satisfaction: float):
        """Record user action on notification"""
        try:
            response_time = time.time()
            self.cursor.execute("""
                UPDATE notifications
                SET user_action = ?, response_time = ?
                WHERE id = ?
            """, (action, response_time, notification_id))

            # Get category for preference learning
            self.cursor.execute("""
                SELECT category FROM notifications WHERE id = ?
            """, (notification_id,))

            result = self.cursor.fetchone()
            if result:
                category = result[0]
                self.preference_learner.record_interaction(
                    category, action, satisfaction
                )

            self.conn.commit()
            logger.info(f"Recorded action for notification {notification_id}")
        except Exception as e:
            logger.error(f"Error recording user action: {e}")

    def get_stats(self) -> Dict:
        """Get notification system statistics"""
        try:
            self.cursor.execute("""
                SELECT status, COUNT(*) FROM notifications GROUP BY status
            """)

            stats = dict(self.cursor.fetchall())

            self.cursor.execute("""
                SELECT urgency, COUNT(*) FROM notifications GROUP BY urgency
            """)

            urgency_dist = dict(self.cursor.fetchall())

            self.cursor.execute("""
                SELECT AVG(priority_score), MAX(priority_score), MIN(priority_score)
                FROM notifications WHERE priority_score IS NOT NULL
            """)

            score_stats = self.cursor.fetchone()

            return {
                "by_status": stats,
                "by_urgency": urgency_dist,
                "avg_priority_score": round(score_stats[0], 3) if score_stats[0] else None,
                "max_priority_score": round(score_stats[1], 3) if score_stats[1] else None,
                "min_priority_score": round(score_stats[2], 3) if score_stats[2] else None
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}

    def close(self):
        """Close database connection"""
        try:
            self.conn.close()
            logger.info("Database connection closed")
        except Exception as e:
            logger.error(f"Error closing connection: {e}")


# ============================================================================
# PRODUCTION TEST CODE
# ============================================================================

def run_comprehensive_test():
    """Comprehensive test suite for notification system"""

    print("\n" + "="*70)
    print("SMART NOTIFICATION SYSTEM - COMPREHENSIVE TEST SUITE")
    print("="*70 + "\n")

    # Initialize system
    db_path = "test_notification_system.db"
    ns = NotificationSystem(db_path)

    try:
        # Test 1: Urgency Classification
        print("[TEST 1] Urgency Classification")
        print("-" * 70)

        test_cases = [
            (["CRITICAL system failure", "Emergency alert"], "system", UrgencyLevel.CRITICAL),
            (["Warning: High memory usage"], "monitoring", UrgencyLevel.HIGH),
            (["Reminder: Meeting in 10 mins"], "calendar", UrgencyLevel.LOW),
            (["Daily digest update"], "digest", UrgencyLevel.MINIMAL),
        ]

        for keywords, category, expected in test_cases:
            urgency = ns.classify_urgency(keywords, category)
            status = "[PASS]" if urgency == expected else "[FAIL]"
            print(f"{status} {' '.join(keywords[:2])} -> {urgency.name} (expected {expected.name})")

        # Test 2: Enqueue Notifications with Various Urgencies
        print("\n[TEST 2] Enqueue Notifications")
        print("-" * 70)

        notifications = [
            ("System Critical", "Database connection failed", "database", UrgencyLevel.CRITICAL),
            ("Build Warning", "Test coverage below threshold", "build", UrgencyLevel.HIGH),
            ("Daily Summary", "Your daily tasks summary", "digest", UrgencyLevel.LOW),
            ("Info Update", "New feature available", "product", UrgencyLevel.MEDIUM),
        ]

        notif_ids = []
        for title, message, category, urgency in notifications:
            notif_id = ns.enqueue_notification(
                title, message, category, urgency,
                {"in_meeting": False, "focused_mode": False}
            )
            notif_ids.append(notif_id)
            print(f"[OK] Enqueued: {title} (ID: {notif_id}, Urgency: {urgency.name})")

        # Test 3: Preference Learning
        print("\n[TEST 3] User Preference Learning")
        print("-" * 70)

        ns.preference_learner.learn_preference(
            "database",
            preferred_time_window="08:00-18:00",
            max_daily_notifications=20,
            batch_similar=True,
            do_not_disturb_hours="22:00-07:00"
        )
        print("[OK] Learned preference for 'database' category")

        pref = ns.preference_learner.get_category_preference("database")
        print(f"  - Preferred window: {pref['preferred_time_window']}")
        print(f"  - Max daily: {pref['max_daily_notifications']}")
        print(f"  - Batch similar: {pref['batch_similar']}")
        print(f"  - DND hours: {pref['do_not_disturb_hours']}")

        # Test 4: Interruption Cost Calculation
        print("\n[TEST 4] Interruption Cost Modeling")
        print("-" * 70)

        contexts = [
            (9, {"in_meeting": False, "focused_mode": False, "recent_notification_count": 0}),
            (14, {"in_meeting": True, "focused_mode": False, "recent_notification_count": 0}),
            (23, {"in_meeting": False, "focused_mode": True, "recent_notification_count": 5}),
            (6, {"in_meeting": False, "focused_mode": False, "recent_notification_count": 0}),
        ]

        time_names = {9: "Work Hours", 14: "Meeting", 23: "Late Night", 6: "Early Morning"}

        for hour, context in contexts:
            cost = ns.interruption_model.calculate_cost(
                UrgencyLevel.MEDIUM, hour, context
            )
            print(f"[OK] {time_names[hour]}: Interruption cost = {cost:.3f}")

        # Test 5: Priority Scoring
        print("\n[TEST 5] Priority Scoring")
        print("-" * 70)

        notif = Notification(
            id=1,
            title="Test",
            message="Test message",
            urgency=UrgencyLevel.HIGH,
            timestamp=time.time(),
            category="test"
        )

        user_history = [8.0, 7.5, 8.2, 7.8]
        category_trend = 5.0

        score = ns.priority_scorer.calculate_score(notif, user_history, category_trend)
        print(f"[OK] Priority score for HIGH urgency notification: {score:.3f}")

        # Test 6: Process Notifications
        print("\n[TEST 6] Process Notifications")
        print("-" * 70)

        result = ns.process_notifications()
        print(f"[OK] Processed notifications:")
        print(f"  - Sent immediately: {result['sent']}")
        print(f"  - Batched: {result['batched']}")
        print(f"  - Batches sent: {result['batch_sent']}")
        print(f"  - Total processed: {result['total_processed']}")

        # Test 7: Record User Actions
        print("\n[TEST 7] Record User Actions & Learning")
        print("-" * 70)

        if notif_ids:
            ns.record_user_action(notif_ids[0], "dismissed", 7.0)
            ns.record_user_action(notif_ids[1], "opened", 8.5)
            print(f"[OK] Recorded user actions for notifications")

        # Test 8: Notification Suppression
        print("\n[TEST 8] Notification Suppression (High Interruption Cost)")
        print("-" * 70)

        suppressed_id = ns.enqueue_notification(
            "Low Priority Update",
            "Minor system information",
            "system",
            UrgencyLevel.LOW,
            {"in_meeting": True, "focused_mode": True, "recent_notification_count": 8}
        )
        print(f"[OK] Enqueued low-priority notification during high-cost time: {suppressed_id}")

        # Test 9: Statistics
        print("\n[TEST 9] System Statistics")
        print("-" * 70)

        stats = ns.get_stats()
        print(f"[OK] Statistics:")
        print(f"  - By status: {stats['by_status']}")
        print(f"  - By urgency: {stats['by_urgency']}")
        print(f"  - Avg priority score: {stats['avg_priority_score']}")
        print(f"  - Max priority score: {stats['max_priority_score']}")

        # Test 10: Batching Engine
        print("\n[TEST 10] Batching Engine")
        print("-" * 70)

        low_notif = Notification(
            id=99,
            title="Batch Test",
            message="This should be batched",
            urgency=UrgencyLevel.LOW,
            category="batch_test",
            timestamp=time.time()
        )

        should_batch = ns.batching_engine.should_batch(low_notif)
        print(f"[OK] Should batch LOW urgency notification: {should_batch}")

        critical_notif = Notification(
            id=100,
            title="Critical Test",
            message="This should not be batched",
            urgency=UrgencyLevel.CRITICAL,
            category="critical_test",
            timestamp=time.time()
        )

        should_batch = ns.batching_engine.should_batch(critical_notif)
        print(f"[OK] Should batch CRITICAL urgency notification: {should_batch}")

        print("\n" + "="*70)
        print("ALL TESTS COMPLETED SUCCESSFULLY")
        print("="*70 + "\n")

    finally:
        ns.close()
        # Cleanup
        import os
        import time as time_module
        try:
            time_module.sleep(0.5)  # Give time to release locks
            if os.path.exists(db_path):
                os.remove(db_path)
                print(f"Cleaned up test database: {db_path}")
        except Exception as e:
            print(f"Note: Could not clean up test database: {e}")


if __name__ == "__main__":
    run_comprehensive_test()
