#!/usr/bin/env python3
"""
Proactive Agent System - Autonomous monitoring and suggestion engine

This system proactively:
- Detects opportunities
- Monitors for issues
- Suggests improvements
- Generates autonomous goals
- Runs 24/7 monitoring loops
- Sends Telegram notifications
"""

import sqlite3
import json
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import traceback


class OpportunityType(Enum):
    """Types of opportunities that can be detected"""
    OPTIMIZATION = "optimization"
    COST_REDUCTION = "cost_reduction"
    REVENUE_INCREASE = "revenue_increase"
    AUTOMATION = "automation"
    LEARNING = "learning"
    IMPROVEMENT = "improvement"


class IssueSeverity(Enum):
    """Severity levels for detected issues"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class ProactiveAgent:
    """
    Autonomous agent that proactively monitors and suggests improvements

    Features:
    - Opportunity detection across multiple domains
    - Issue monitoring with severity classification
    - Improvement suggestions with impact estimates
    - Autonomous goal generation
    - 24/7 monitoring loop
    - Telegram notifications for important findings
    - Persistent memory integration
    """

    def __init__(self, db_path: str = None, notification_threshold: float = 0.7):
        if db_path is None:
            workspace = Path(__file__).parent.parent
            db_path = workspace / "memory.db"

        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

        # Configuration
        self.notification_threshold = notification_threshold
        self.monitoring_active = False
        self.monitoring_thread = None

        # Load Telegram notifier
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from telegram_notifier import TelegramNotifier
            self.notifier = TelegramNotifier()
        except Exception as e:
            print(f"[WARNING] Could not load Telegram notifier: {e}")
            self.notifier = None

        # Load persistent memory
        try:
            from core.persistent_memory import PersistentMemory
            self.memory = PersistentMemory(db_path=db_path)
        except Exception as e:
            print(f"[WARNING] Could not load persistent memory: {e}")
            self.memory = None

        # Monitoring rules
        self.monitoring_rules = []
        self._register_default_rules()

    def _init_db(self):
        """Initialize database schema"""
        cursor = self.conn.cursor()

        # Opportunities detected
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS opportunities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                opportunity_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                potential_impact REAL,
                confidence REAL,
                effort_estimate_hours REAL,
                status TEXT DEFAULT 'new',
                notified INTEGER DEFAULT 0,
                acted_on INTEGER DEFAULT 0,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        ''')

        # Issues detected
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                issue_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                severity INTEGER,
                status TEXT DEFAULT 'open',
                notified INTEGER DEFAULT 0,
                resolved_at TIMESTAMP,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolution TEXT,
                metadata TEXT
            )
        ''')

        # Improvement suggestions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                rationale TEXT,
                expected_benefit TEXT,
                implementation_steps TEXT,
                priority INTEGER DEFAULT 2,
                status TEXT DEFAULT 'pending',
                notified INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        ''')

        # Autonomous goals
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS autonomous_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_name TEXT NOT NULL,
                description TEXT,
                reasoning TEXT,
                success_criteria TEXT,
                priority INTEGER DEFAULT 2,
                status TEXT DEFAULT 'proposed',
                progress REAL DEFAULT 0,
                notified INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                metadata TEXT
            )
        ''')

        # Monitoring log
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS monitoring_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                monitor_type TEXT NOT NULL,
                event TEXT,
                details TEXT,
                severity INTEGER DEFAULT 1,
                action_taken TEXT,
                logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Notification history
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notification_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                notification_type TEXT NOT NULL,
                title TEXT,
                message TEXT,
                priority TEXT,
                sent_successfully INTEGER,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        self.conn.commit()

    # === OPPORTUNITY DETECTION ===

    def detect_opportunity(self, opportunity_type: OpportunityType, title: str,
                          description: str, potential_impact: float,
                          confidence: float = 0.5, effort_estimate_hours: float = None,
                          metadata: Dict = None, notify: bool = True) -> int:
        """Detect and log an opportunity"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO opportunities
            (opportunity_type, title, description, potential_impact, confidence,
             effort_estimate_hours, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (opportunity_type.value, title, description, potential_impact,
              confidence, effort_estimate_hours,
              json.dumps(metadata) if metadata else None))
        self.conn.commit()
        opp_id = cursor.lastrowid

        # Log to monitoring
        self._log_monitoring(
            monitor_type="opportunity_detection",
            event=f"Detected: {title}",
            details=f"Impact: {potential_impact:.0%}, Confidence: {confidence:.0%}",
            severity=2 if potential_impact > 0.5 else 1
        )

        # Notify if significant
        if notify and potential_impact >= self.notification_threshold and self.notifier:
            self._notify_opportunity(opp_id)

        return opp_id

    def _notify_opportunity(self, opp_id: int):
        """Send notification about an opportunity"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM opportunities WHERE id = ?', (opp_id,))
        opp = dict(cursor.fetchone())

        message = f"*Opportunity Detected*\n\n"
        message += f"*{opp['title']}*\n\n"
        message += f"{opp['description']}\n\n"
        message += f"Impact: {opp['potential_impact']:.0%}\n"
        message += f"Confidence: {opp['confidence']:.0%}"

        if opp['effort_estimate_hours']:
            message += f"\nEffort: ~{opp['effort_estimate_hours']} hours"

        try:
            success = self.notifier.send_message(message, priority="info")
            cursor.execute('''
                UPDATE opportunities SET notified = 1 WHERE id = ?
            ''', (opp_id,))
            self.conn.commit()

            # Log notification
            self._log_notification(
                notification_type="opportunity",
                title=opp['title'],
                message=message,
                priority="info",
                sent_successfully=success
            )
        except Exception as e:
            print(f"[ERROR] Could not send notification: {e}")

    def get_opportunities(self, status: str = None, min_impact: float = 0,
                         limit: int = 50) -> List[Dict]:
        """Get detected opportunities"""
        cursor = self.conn.cursor()

        if status:
            cursor.execute('''
                SELECT * FROM opportunities
                WHERE status = ? AND potential_impact >= ?
                ORDER BY potential_impact DESC, detected_at DESC
                LIMIT ?
            ''', (status, min_impact, limit))
        else:
            cursor.execute('''
                SELECT * FROM opportunities
                WHERE potential_impact >= ?
                ORDER BY potential_impact DESC, detected_at DESC
                LIMIT ?
            ''', (min_impact, limit))

        return [dict(row) for row in cursor.fetchall()]

    def act_on_opportunity(self, opp_id: int, action_taken: str):
        """Mark opportunity as acted upon"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE opportunities
            SET status = 'acted_on', acted_on = 1
            WHERE id = ?
        ''', (opp_id,))
        self.conn.commit()

        self._log_monitoring(
            monitor_type="opportunity_action",
            event=f"Acted on opportunity {opp_id}",
            details=action_taken,
            action_taken=action_taken
        )

    # === ISSUE MONITORING ===

    def detect_issue(self, issue_type: str, title: str, description: str,
                    severity: IssueSeverity, metadata: Dict = None,
                    notify: bool = True) -> int:
        """Detect and log an issue"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO issues
            (issue_type, title, description, severity, metadata)
            VALUES (?, ?, ?, ?, ?)
        ''', (issue_type, title, description, severity.value,
              json.dumps(metadata) if metadata else None))
        self.conn.commit()
        issue_id = cursor.lastrowid

        # Log to monitoring
        self._log_monitoring(
            monitor_type="issue_detection",
            event=f"Issue detected: {title}",
            details=description,
            severity=severity.value
        )

        # Notify if high severity
        if notify and severity.value >= IssueSeverity.HIGH.value and self.notifier:
            self._notify_issue(issue_id)

        return issue_id

    def _notify_issue(self, issue_id: int):
        """Send notification about an issue"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM issues WHERE id = ?', (issue_id,))
        issue = dict(cursor.fetchone())

        severity_emoji = {
            1: "ℹ️",
            2: "⚠️",
            3: "🚨",
            4: "🔥"
        }

        message = f"{severity_emoji.get(issue['severity'], '⚠️')} *Issue Detected*\n\n"
        message += f"*{issue['title']}*\n\n"
        message += f"{issue['description']}\n\n"
        message += f"Severity: {IssueSeverity(issue['severity']).name}"

        priority_map = {1: "info", 2: "normal", 3: "urgent", 4: "urgent"}
        priority = priority_map.get(issue['severity'], "normal")

        try:
            success = self.notifier.send_message(message, priority=priority)
            cursor.execute('''
                UPDATE issues SET notified = 1 WHERE id = ?
            ''', (issue_id,))
            self.conn.commit()

            # Log notification
            self._log_notification(
                notification_type="issue",
                title=issue['title'],
                message=message,
                priority=priority,
                sent_successfully=success
            )
        except Exception as e:
            print(f"[ERROR] Could not send notification: {e}")

    def resolve_issue(self, issue_id: int, resolution: str):
        """Mark issue as resolved"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE issues
            SET status = 'resolved', resolved_at = CURRENT_TIMESTAMP,
                resolution = ?
            WHERE id = ?
        ''', (resolution, issue_id))
        self.conn.commit()

        self._log_monitoring(
            monitor_type="issue_resolution",
            event=f"Resolved issue {issue_id}",
            details=resolution,
            action_taken=resolution
        )

    def get_issues(self, status: str = "open", min_severity: int = 1,
                  limit: int = 50) -> List[Dict]:
        """Get detected issues"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM issues
            WHERE status = ? AND severity >= ?
            ORDER BY severity DESC, detected_at DESC
            LIMIT ?
        ''', (status, min_severity, limit))
        return [dict(row) for row in cursor.fetchall()]

    # === IMPROVEMENT SUGGESTIONS ===

    def suggest_improvement(self, category: str, title: str, description: str,
                          rationale: str, expected_benefit: str,
                          implementation_steps: List[str], priority: int = 2,
                          metadata: Dict = None, notify: bool = True) -> int:
        """Generate an improvement suggestion"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO suggestions
            (category, title, description, rationale, expected_benefit,
             implementation_steps, priority, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (category, title, description, rationale, expected_benefit,
              json.dumps(implementation_steps), priority,
              json.dumps(metadata) if metadata else None))
        self.conn.commit()
        suggestion_id = cursor.lastrowid

        # Log to monitoring
        self._log_monitoring(
            monitor_type="improvement_suggestion",
            event=f"Suggested: {title}",
            details=description,
            severity=priority
        )

        # Notify if high priority
        if notify and priority >= 3 and self.notifier:
            self._notify_suggestion(suggestion_id)

        return suggestion_id

    def _notify_suggestion(self, suggestion_id: int):
        """Send notification about a suggestion"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM suggestions WHERE id = ?', (suggestion_id,))
        suggestion = dict(cursor.fetchone())

        message = f"💡 *Improvement Suggestion*\n\n"
        message += f"*{suggestion['title']}*\n\n"
        message += f"{suggestion['description']}\n\n"
        message += f"*Rationale:* {suggestion['rationale']}\n\n"
        message += f"*Expected Benefit:* {suggestion['expected_benefit']}"

        priority_map = {1: "info", 2: "normal", 3: "urgent"}
        priority = priority_map.get(suggestion['priority'], "normal")

        try:
            success = self.notifier.send_message(message, priority=priority)
            cursor.execute('''
                UPDATE suggestions SET notified = 1 WHERE id = ?
            ''', (suggestion_id,))
            self.conn.commit()

            # Log notification
            self._log_notification(
                notification_type="suggestion",
                title=suggestion['title'],
                message=message,
                priority=priority,
                sent_successfully=success
            )
        except Exception as e:
            print(f"[ERROR] Could not send notification: {e}")

    def get_suggestions(self, status: str = "pending", category: str = None,
                       limit: int = 50) -> List[Dict]:
        """Get improvement suggestions"""
        cursor = self.conn.cursor()

        if category:
            cursor.execute('''
                SELECT * FROM suggestions
                WHERE status = ? AND category = ?
                ORDER BY priority DESC, created_at DESC
                LIMIT ?
            ''', (status, category, limit))
        else:
            cursor.execute('''
                SELECT * FROM suggestions
                WHERE status = ?
                ORDER BY priority DESC, created_at DESC
                LIMIT ?
            ''', (status, limit))

        return [dict(row) for row in cursor.fetchall()]

    # === AUTONOMOUS GOAL GENERATION ===

    def generate_goal(self, goal_name: str, description: str, reasoning: str,
                     success_criteria: List[str], priority: int = 2,
                     metadata: Dict = None, notify: bool = True) -> int:
        """Autonomously generate a new goal"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO autonomous_goals
            (goal_name, description, reasoning, success_criteria, priority, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (goal_name, description, reasoning, json.dumps(success_criteria),
              priority, json.dumps(metadata) if metadata else None))
        self.conn.commit()
        goal_id = cursor.lastrowid

        # Log to monitoring
        self._log_monitoring(
            monitor_type="goal_generation",
            event=f"Generated goal: {goal_name}",
            details=reasoning,
            severity=priority
        )

        # Notify if high priority
        if notify and priority >= 3 and self.notifier:
            self._notify_goal(goal_id)

        return goal_id

    def _notify_goal(self, goal_id: int):
        """Send notification about a new goal"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM autonomous_goals WHERE id = ?', (goal_id,))
        goal = dict(cursor.fetchone())

        message = f"🎯 *New Autonomous Goal*\n\n"
        message += f"*{goal['goal_name']}*\n\n"
        message += f"{goal['description']}\n\n"
        message += f"*Reasoning:* {goal['reasoning']}\n\n"

        criteria = json.loads(goal['success_criteria'])
        message += f"*Success Criteria:*\n"
        for i, criterion in enumerate(criteria, 1):
            message += f"{i}. {criterion}\n"

        priority_map = {1: "info", 2: "normal", 3: "urgent"}
        priority = priority_map.get(goal['priority'], "normal")

        try:
            success = self.notifier.send_message(message, priority=priority)
            cursor.execute('''
                UPDATE autonomous_goals SET notified = 1 WHERE id = ?
            ''', (goal_id,))
            self.conn.commit()

            # Log notification
            self._log_notification(
                notification_type="goal",
                title=goal['goal_name'],
                message=message,
                priority=priority,
                sent_successfully=success
            )
        except Exception as e:
            print(f"[ERROR] Could not send notification: {e}")

    def update_goal_progress(self, goal_id: int, progress: float, status: str = None):
        """Update goal progress"""
        cursor = self.conn.cursor()

        if status:
            cursor.execute('''
                UPDATE autonomous_goals
                SET progress = ?, status = ?
                WHERE id = ?
            ''', (progress, status, goal_id))
        else:
            cursor.execute('''
                UPDATE autonomous_goals SET progress = ? WHERE id = ?
            ''', (progress, goal_id))

        self.conn.commit()

    def get_goals(self, status: str = "proposed", limit: int = 50) -> List[Dict]:
        """Get autonomous goals"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM autonomous_goals
            WHERE status = ?
            ORDER BY priority DESC, created_at DESC
            LIMIT ?
        ''', (status, limit))
        return [dict(row) for row in cursor.fetchall()]

    # === MONITORING RULES ===

    def _register_default_rules(self):
        """Register default monitoring rules"""
        # Example rule: Check for failed tasks
        self.add_monitoring_rule(
            name="failed_tasks",
            check_function=self._check_failed_tasks,
            interval_seconds=300  # Check every 5 minutes
        )

        # Example rule: Check for stale opportunities
        self.add_monitoring_rule(
            name="stale_opportunities",
            check_function=self._check_stale_opportunities,
            interval_seconds=3600  # Check every hour
        )

    def add_monitoring_rule(self, name: str, check_function: Callable,
                           interval_seconds: int = 300):
        """Add a monitoring rule"""
        self.monitoring_rules.append({
            'name': name,
            'function': check_function,
            'interval': interval_seconds,
            'last_check': 0
        })

    def _check_failed_tasks(self):
        """Check for failed tasks in memory"""
        if not self.memory:
            return

        try:
            # Get failed tasks from today
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) as count FROM tasks
                WHERE status = 'failed'
                  AND DATE(updated_at) = DATE('now')
            ''')
            result = cursor.fetchone()
            if result and result['count'] > 0:
                self.detect_issue(
                    issue_type="task_failure",
                    title=f"{result['count']} tasks failed today",
                    description="Multiple task failures detected. Investigation recommended.",
                    severity=IssueSeverity.MEDIUM,
                    notify=True
                )
        except Exception as e:
            print(f"[WARNING] Failed to check failed tasks: {e}")

    def _check_stale_opportunities(self):
        """Check for opportunities not acted upon"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) as count FROM opportunities
                WHERE status = 'new'
                  AND acted_on = 0
                  AND detected_at < datetime('now', '-7 days')
            ''')
            result = cursor.fetchone()
            if result and result['count'] > 0:
                self.suggest_improvement(
                    category="process",
                    title="Review stale opportunities",
                    description=f"{result['count']} opportunities detected over a week ago have not been acted upon",
                    rationale="Acting on opportunities in a timely manner maximizes value",
                    expected_benefit="Better opportunity capture rate",
                    implementation_steps=[
                        "Review opportunities list",
                        "Prioritize top opportunities",
                        "Create action plans"
                    ],
                    priority=2,
                    notify=False  # Don't spam
                )
        except Exception as e:
            print(f"[WARNING] Failed to check stale opportunities: {e}")

    # === 24/7 MONITORING LOOP ===

    def start_monitoring(self, interval_seconds: int = 60):
        """Start continuous monitoring loop"""
        if self.monitoring_active:
            print("[WARNING] Monitoring already active")
            return

        self.monitoring_active = True

        def monitoring_loop():
            print("[PROACTIVE AGENT] Monitoring started")
            self._log_monitoring(
                monitor_type="system",
                event="Monitoring started",
                details=f"Interval: {interval_seconds}s"
            )

            while self.monitoring_active:
                try:
                    # Run monitoring rules
                    current_time = time.time()
                    for rule in self.monitoring_rules:
                        if current_time - rule['last_check'] >= rule['interval']:
                            try:
                                rule['function']()
                                rule['last_check'] = current_time
                            except Exception as e:
                                print(f"[ERROR] Monitoring rule '{rule['name']}' failed: {e}")

                    # Sleep until next check
                    time.sleep(interval_seconds)

                except Exception as e:
                    print(f"[ERROR] Monitoring loop error: {e}")
                    traceback.print_exc()
                    time.sleep(interval_seconds)

            print("[PROACTIVE AGENT] Monitoring stopped")
            self._log_monitoring(
                monitor_type="system",
                event="Monitoring stopped",
                details="Monitoring loop terminated"
            )

        self.monitoring_thread = threading.Thread(target=monitoring_loop, daemon=True)
        self.monitoring_thread.start()

    def stop_monitoring(self):
        """Stop monitoring loop"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)

    # === LOGGING ===

    def _log_monitoring(self, monitor_type: str, event: str, details: str = None,
                       severity: int = 1, action_taken: str = None):
        """Log monitoring event"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO monitoring_log
            (monitor_type, event, details, severity, action_taken)
            VALUES (?, ?, ?, ?, ?)
        ''', (monitor_type, event, details, severity, action_taken))
        self.conn.commit()

    def _log_notification(self, notification_type: str, title: str, message: str,
                         priority: str, sent_successfully: bool):
        """Log notification sent"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO notification_history
            (notification_type, title, message, priority, sent_successfully)
            VALUES (?, ?, ?, ?, ?)
        ''', (notification_type, title, message, priority, 1 if sent_successfully else 0))
        self.conn.commit()

    def get_monitoring_log(self, limit: int = 100) -> List[Dict]:
        """Get recent monitoring log"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM monitoring_log
            ORDER BY logged_at DESC
            LIMIT ?
        ''', (limit,))
        return [dict(row) for row in cursor.fetchall()]

    def get_stats(self) -> Dict:
        """Get agent statistics"""
        cursor = self.conn.cursor()

        # Opportunities
        cursor.execute('SELECT COUNT(*) as count FROM opportunities WHERE status = "new"')
        new_opps = cursor.fetchone()['count']

        # Issues
        cursor.execute('SELECT COUNT(*) as count FROM issues WHERE status = "open"')
        open_issues = cursor.fetchone()['count']

        # Suggestions
        cursor.execute('SELECT COUNT(*) as count FROM suggestions WHERE status = "pending"')
        pending_suggestions = cursor.fetchone()['count']

        # Goals
        cursor.execute('SELECT COUNT(*) as count FROM autonomous_goals WHERE status IN ("proposed", "active")')
        active_goals = cursor.fetchone()['count']

        # Notifications
        cursor.execute('SELECT COUNT(*) as count FROM notification_history WHERE DATE(sent_at) = DATE("now")')
        notifications_today = cursor.fetchone()['count']

        return {
            'new_opportunities': new_opps,
            'open_issues': open_issues,
            'pending_suggestions': pending_suggestions,
            'active_goals': active_goals,
            'notifications_today': notifications_today,
            'monitoring_active': self.monitoring_active
        }

    def close(self):
        """Close agent and cleanup"""
        self.stop_monitoring()
        self.conn.close()


# === TEST CODE ===

def main():
    """Test proactive agent system"""
    print("Testing Proactive Agent System")
    print("=" * 70)

    agent = ProactiveAgent(notification_threshold=0.6)

    try:
        # Test opportunity detection
        print("\n1. Detecting opportunities...")
        opp_id = agent.detect_opportunity(
            opportunity_type=OpportunityType.OPTIMIZATION,
            title="Optimize database queries",
            description="Several queries are scanning full tables. Adding indexes could improve performance by 10x.",
            potential_impact=0.75,
            confidence=0.85,
            effort_estimate_hours=4,
            notify=False  # Don't spam during test
        )
        print(f"   Opportunity {opp_id} detected")

        opp_id2 = agent.detect_opportunity(
            opportunity_type=OpportunityType.AUTOMATION,
            title="Automate daily report generation",
            description="Daily reports are generated manually. Automation could save 30 minutes daily.",
            potential_impact=0.65,
            confidence=0.9,
            effort_estimate_hours=8,
            notify=False
        )
        print(f"   Opportunity {opp_id2} detected")

        # Get opportunities
        opportunities = agent.get_opportunities(min_impact=0.5)
        print(f"   Total opportunities: {len(opportunities)}")

        # Test issue detection
        print("\n2. Detecting issues...")
        issue_id = agent.detect_issue(
            issue_type="performance",
            title="API response time degraded",
            description="Average API response time increased from 200ms to 800ms over the past hour",
            severity=IssueSeverity.HIGH,
            notify=False
        )
        print(f"   Issue {issue_id} detected")

        # Get issues
        issues = agent.get_issues(status="open")
        print(f"   Open issues: {len(issues)}")

        # Test improvement suggestions
        print("\n3. Generating improvement suggestions...")
        suggestion_id = agent.suggest_improvement(
            category="code_quality",
            title="Implement comprehensive logging",
            description="Add structured logging to all API endpoints for better debugging",
            rationale="Current logging is inconsistent and makes troubleshooting difficult",
            expected_benefit="Faster debugging and issue resolution",
            implementation_steps=[
                "Choose logging framework (e.g., structlog)",
                "Define logging standards",
                "Add logging to all endpoints",
                "Set up log aggregation"
            ],
            priority=2,
            notify=False
        )
        print(f"   Suggestion {suggestion_id} generated")

        # Get suggestions
        suggestions = agent.get_suggestions()
        print(f"   Pending suggestions: {len(suggestions)}")

        # Test autonomous goal generation
        print("\n4. Generating autonomous goals...")
        goal_id = agent.generate_goal(
            goal_name="Achieve 99.9% uptime",
            description="Improve system reliability to achieve three-nines uptime",
            reasoning="Current uptime is 98.5%. Customer satisfaction and revenue depend on reliability.",
            success_criteria=[
                "Uptime > 99.9% for 30 consecutive days",
                "Zero critical incidents",
                "Average response time < 300ms"
            ],
            priority=3,
            notify=False
        )
        print(f"   Goal {goal_id} generated")

        # Update goal progress
        agent.update_goal_progress(goal_id, progress=0.25, status="active")
        print(f"   Goal {goal_id} progress updated to 25%")

        # Get goals
        goals = agent.get_goals(status="active")
        print(f"   Active goals: {len(goals)}")

        # Test monitoring
        print("\n5. Testing monitoring system...")
        print("   Starting monitoring loop (will run for 5 seconds)...")
        agent.start_monitoring(interval_seconds=2)
        time.sleep(5)
        agent.stop_monitoring()
        print("   Monitoring stopped")

        # Get monitoring log
        log = agent.get_monitoring_log(limit=10)
        print(f"   Monitoring log entries: {len(log)}")

        # Get statistics
        print("\n6. Agent Statistics:")
        stats = agent.get_stats()
        for key, value in stats.items():
            print(f"   {key}: {value}")

        # Demonstrate acting on opportunity
        print("\n7. Acting on opportunity...")
        agent.act_on_opportunity(opp_id, "Created task to add database indexes")
        print(f"   Opportunity {opp_id} marked as acted on")

        # Demonstrate resolving issue
        print("\n8. Resolving issue...")
        agent.resolve_issue(issue_id, "Identified slow query and optimized it")
        print(f"   Issue {issue_id} marked as resolved")

        print(f"\n✓ Proactive Agent System working!")
        print(f"Database: {agent.db_path}")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        traceback.print_exc()
    finally:
        agent.close()


if __name__ == "__main__":
    main()
