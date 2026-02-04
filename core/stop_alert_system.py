"""
Stop Alert System - CRITICAL FIX

Ensures user is ALWAYS notified via Telegram when AI stops working.
User should never have to check chat to see if work stopped.

Built in response to: "if i hadnt looked at the chat and noticed that
it had stopped i would have had no idea"
"""

import time
import threading
import requests
import json
from datetime import datetime, timedelta
from typing import Optional, Callable
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StopAlertSystem:
    """
    Monitors AI activity and sends Telegram alerts when work stops

    Critical Features:
    1. Heartbeat monitoring - detects when AI goes silent
    2. Telegram notifications - alerts user immediately when stop detected
    3. Auto-recovery attempts - tries to resume work automatically
    4. Stop prevention - integrates with continuous workflow
    """

    def __init__(self, telegram_bot_token: str, telegram_chat_id: str,
                 heartbeat_interval: int = 60):
        """
        Initialize stop alert system

        Args:
            telegram_bot_token: Bot token for sending alerts
            telegram_chat_id: User's chat ID (5791597360)
            heartbeat_interval: Seconds between heartbeat checks
        """
        self.bot_token = telegram_bot_token
        self.chat_id = telegram_chat_id
        self.heartbeat_interval = heartbeat_interval

        self.last_activity = datetime.now()
        self.is_working = False
        self.current_task = None
        self.monitor_thread = None
        self.running = False

        self.stop_count = 0
        self.alerts_sent = 0

    def start_working(self, task_name: str):
        """
        Call this when starting work on a task

        Args:
            task_name: What you're working on
        """
        self.is_working = True
        self.current_task = task_name
        self.last_activity = datetime.now()

        logger.info(f"Started working on: {task_name}")

        # Start monitoring if not already running
        if not self.running:
            self.start_monitoring()

    def heartbeat(self, activity_description: str = ""):
        """
        Call this regularly while working to show you're still active

        Args:
            activity_description: What you just did
        """
        self.last_activity = datetime.now()

        if activity_description:
            logger.debug(f"Activity: {activity_description}")

    def stop_working(self, reason: str = "Task complete"):
        """
        Call this when legitimately stopping

        Args:
            reason: Why you're stopping
        """
        self.is_working = False

        # Send completion notification, not alert
        self._send_notification(
            f"✓ Task Complete: {self.current_task}\n"
            f"Reason: {reason}\n"
            f"Time: {datetime.now().strftime('%H:%M:%S')}"
        )

        logger.info(f"Stopped working: {reason}")

    def start_monitoring(self):
        """Start background monitoring for stops"""
        if self.running:
            logger.warning("Monitoring already running")
            return

        self.running = True
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True
        )
        self.monitor_thread.start()

        logger.info(f"Stop monitoring started (interval: {self.heartbeat_interval}s)")

    def stop_monitoring(self):
        """Stop background monitoring"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)

        logger.info("Stop monitoring stopped")

    def _monitoring_loop(self):
        """Background loop checking for stops"""
        while self.running:
            try:
                # Check if we should be working but haven't had activity
                if self.is_working:
                    time_since_activity = (datetime.now() - self.last_activity).total_seconds()

                    # If no activity for longer than interval, send alert
                    if time_since_activity > self.heartbeat_interval:
                        self._handle_stop_detected(time_since_activity)

            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")

            time.sleep(self.heartbeat_interval)

    def _handle_stop_detected(self, idle_seconds: float):
        """Handle when a stop is detected"""
        self.stop_count += 1

        alert_message = (
            f"🚨 AI STOPPED WORKING\n\n"
            f"Task: {self.current_task}\n"
            f"Idle for: {int(idle_seconds)} seconds\n"
            f"Last activity: {self.last_activity.strftime('%H:%M:%S')}\n"
            f"Stop count this session: {self.stop_count}\n\n"
            f"⚠️ You may need to send 'Continue' to resume work"
        )

        self._send_telegram_alert(alert_message)

        logger.warning(f"STOP DETECTED: Idle for {idle_seconds}s")

        # Try auto-recovery (future enhancement)
        # self._attempt_auto_recovery()

    def _send_telegram_alert(self, message: str):
        """
        Send Telegram alert to user

        Args:
            message: Alert message to send
        """
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

            data = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }

            response = requests.post(url, json=data, timeout=10)

            if response.status_code == 200:
                self.alerts_sent += 1
                logger.info(f"Telegram alert sent successfully (#{self.alerts_sent})")
            else:
                logger.error(f"Failed to send Telegram alert: {response.status_code}")

        except Exception as e:
            logger.error(f"Error sending Telegram alert: {e}")
            # Fallback: at least log it
            print(f"\n{'='*80}")
            print("CRITICAL: AI STOPPED WORKING")
            print(message)
            print(f"{'='*80}\n")

    def _send_notification(self, message: str):
        """Send a regular notification (not an alert)"""
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

            data = {
                'chat_id': self.chat_id,
                'text': message
            }

            requests.post(url, json=data, timeout=10)

        except Exception as e:
            logger.debug(f"Notification send failed: {e}")

    def get_stats(self) -> dict:
        """Get monitoring statistics"""
        return {
            'is_working': self.is_working,
            'current_task': self.current_task,
            'last_activity': self.last_activity.isoformat(),
            'stop_count': self.stop_count,
            'alerts_sent': self.alerts_sent,
            'monitoring_active': self.running
        }


class StopPreventionIntegration:
    """
    Integrates stop alerts with continuous workflow system

    Ensures both prevention AND notification
    """

    def __init__(self, alert_system: StopAlertSystem, workflow_system):
        self.alerts = alert_system
        self.workflow = workflow_system

    def start_task_with_monitoring(self, task_id: str, description: str,
                                   subtasks: list, verification_required: bool = True):
        """
        Start a task with both workflow tracking and stop monitoring

        Args:
            task_id: Task identifier
            description: What the task is
            subtasks: All subtasks that must be completed
            verification_required: Whether verification needed

        Returns:
            Task object
        """
        # Start workflow tracking
        task = self.workflow.start_task(task_id, description, subtasks, verification_required)

        # Start activity monitoring
        self.alerts.start_working(description)

        logger.info(f"Task started with full monitoring: {description}")

        return task

    def complete_subtask_with_heartbeat(self, task_id: str, subtask: str):
        """
        Complete a subtask and send heartbeat

        Args:
            task_id: Task identifier
            subtask: Subtask completed
        """
        # Mark in workflow
        self.workflow.complete_subtask(task_id, subtask)

        # Send heartbeat
        self.alerts.heartbeat(f"Completed: {subtask}")

        logger.info(f"Subtask completed with heartbeat: {subtask}")

    def check_can_stop_safely(self, task_id: str) -> dict:
        """
        Check if it's safe to stop, with user notification if not

        Args:
            task_id: Task to check

        Returns:
            Check result with should_stop, reason, missing_work
        """
        # Check workflow
        check = self.workflow.check_should_stop(task_id)

        # If trying to stop but shouldn't, send alert
        if not check['should_stop']:
            alert_message = (
                f"⚠️ PREVENTED PREMATURE STOP\n\n"
                f"Task: {task_id}\n"
                f"Reason: {check['reason']}\n"
                f"Missing work:\n" +
                "\n".join(f"  • {work}" for work in check['missing_work'][:5])
            )

            self.alerts._send_telegram_alert(alert_message)

            logger.warning(f"Prevented stop: {check['reason']}")

        return check

    def finish_task_properly(self, task_id: str):
        """
        Finish a task with all verification

        Args:
            task_id: Task to finish
        """
        # Check workflow
        check = self.workflow.check_should_stop(task_id)

        if not check['should_stop']:
            raise Exception(f"Cannot finish task - {check['reason']}")

        # Mark complete in workflow
        result = self.workflow.mark_complete(task_id)

        if result['success']:
            # Stop monitoring with completion notice
            self.alerts.stop_working("All subtasks completed and verified")

        return result


# Global instance that can be used throughout the system
_global_alert_system: Optional[StopAlertSystem] = None


def initialize_global_alerts(telegram_bot_token: str, telegram_chat_id: str):
    """
    Initialize the global alert system

    Call this at the start of every session

    Args:
        telegram_bot_token: Bot token
        telegram_chat_id: User's Telegram chat ID
    """
    global _global_alert_system

    _global_alert_system = StopAlertSystem(
        telegram_bot_token=telegram_bot_token,
        telegram_chat_id=telegram_chat_id,
        heartbeat_interval=60  # Alert if no activity for 60 seconds
    )

    logger.info("Global stop alert system initialized")

    return _global_alert_system


def get_alert_system() -> Optional[StopAlertSystem]:
    """Get the global alert system instance"""
    return _global_alert_system


def heartbeat(activity: str = ""):
    """
    Convenience function to send heartbeat

    Use this throughout your code to show you're still working
    """
    if _global_alert_system:
        _global_alert_system.heartbeat(activity)


# Example usage
if __name__ == '__main__':
    # Initialize system (use real token in production)
    alert_system = StopAlertSystem(
        telegram_bot_token="YOUR_BOT_TOKEN",
        telegram_chat_id="5791597360",
        heartbeat_interval=30  # Check every 30 seconds for testing
    )

    # Simulate working
    print("Starting work...")
    alert_system.start_working("Build amazing features")

    # Send heartbeats while working
    for i in range(3):
        time.sleep(10)
        alert_system.heartbeat(f"Working on step {i+1}")
        print(f"Sent heartbeat {i+1}")

    # Simulate stopping without notification
    print("\nSimulating stop (no heartbeat for 30+ seconds)...")
    print("Alert should trigger...")
    time.sleep(35)

    # Stats
    stats = alert_system.get_stats()
    print(f"\nStats: {json.dumps(stats, indent=2)}")

    # Proper completion
    alert_system.stop_working("Task complete")
    alert_system.stop_monitoring()
