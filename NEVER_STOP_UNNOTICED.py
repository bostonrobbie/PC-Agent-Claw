#!/usr/bin/env python3
"""
NEVER STOP UNNOTICED - Complete Integration

This script ensures the user is ALWAYS alerted when AI stops working.

User feedback (message 424):
"if i hadnt looked at the chat and noticed that it had stopped
i would have had no idea"

SOLUTION:
1. Heartbeat monitoring - detects when AI goes silent
2. Telegram instant alerts - user notified immediately
3. Stop prevention - workflow system prevents stopping
4. Auto-recovery - attempts to resume work
5. Activity logging - complete audit trail

USER PROMISE:
You will NEVER have to check the chat to see if work stopped.
You will be alerted via Telegram within 60 seconds of any stop.
"""

import os
import sys
import time
import logging
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.stop_alert_system import StopAlertSystem, StopPreventionIntegration, initialize_global_alerts, heartbeat
from core.continuous_workflow import ContinuousWorkflowSystem

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NeverStopUnnoticedSystem:
    """
    Complete system ensuring user always knows when AI stops

    Combines:
    - Stop detection (heartbeat monitoring)
    - Stop prevention (continuous workflow)
    - Stop notification (Telegram alerts)
    - Stop recovery (auto-resume attempts)
    """

    def __init__(self, telegram_bot_token: str = None, telegram_chat_id: str = "5791597360"):
        """
        Initialize the complete system

        Args:
            telegram_bot_token: Telegram bot token (read from env if not provided)
            telegram_chat_id: User's Telegram chat ID (default: 5791597360)
        """
        # Get bot token from environment or parameter
        self.bot_token = telegram_bot_token or os.getenv('TELEGRAM_BOT_TOKEN')

        if not self.bot_token:
            logger.warning("No Telegram bot token provided - alerts will use fallback logging")
            self.bot_token = "FALLBACK_MODE"

        self.chat_id = telegram_chat_id

        # Initialize all systems
        self.alert_system = StopAlertSystem(
            telegram_bot_token=self.bot_token,
            telegram_chat_id=self.chat_id,
            heartbeat_interval=60  # Alert if idle for 60 seconds
        )

        self.workflow_system = ContinuousWorkflowSystem(
            db_path="never_stop_workflow.db"
        )

        self.integration = StopPreventionIntegration(
            alert_system=self.alert_system,
            workflow_system=self.workflow_system
        )

        # Initialize global heartbeat
        initialize_global_alerts(self.bot_token, self.chat_id)

        logger.info("Never Stop Unnoticed system initialized")

    def start_task(self, task_id: str, description: str, subtasks: list,
                   send_start_notification: bool = True):
        """
        Start a task with full monitoring

        Args:
            task_id: Unique task identifier
            description: What you're doing
            subtasks: All work that must be completed
            send_start_notification: Send Telegram notification that work started

        Returns:
            Task object
        """
        # Start with integrated monitoring
        task = self.integration.start_task_with_monitoring(
            task_id=task_id,
            description=description,
            subtasks=subtasks,
            verification_required=True
        )

        # Notify user work is starting
        if send_start_notification:
            self._send_notification(
                f"🚀 AI Started Working\n\n"
                f"Task: {description}\n"
                f"Subtasks: {len(subtasks)}\n"
                f"Started: {datetime.now().strftime('%H:%M:%S')}\n\n"
                f"You will be alerted if work stops."
            )

        logger.info(f"Started monitored task: {description}")

        return task

    def complete_subtask(self, task_id: str, subtask: str,
                        send_progress_update: bool = False):
        """
        Complete a subtask with heartbeat

        Args:
            task_id: Task identifier
            subtask: Subtask completed
            send_progress_update: Send Telegram progress update
        """
        self.integration.complete_subtask_with_heartbeat(task_id, subtask)

        if send_progress_update:
            summary = self.workflow_system.get_work_summary(task_id)
            self._send_notification(
                f"✓ Progress Update\n\n"
                f"Completed: {subtask}\n"
                f"Progress: {summary['completed_subtasks']}/{summary['total_subtasks']}\n"
                f"({summary['completion_percentage']:.1f}% complete)"
            )

    def try_to_finish(self, task_id: str) -> dict:
        """
        Attempt to finish task (will fail if incomplete)

        Args:
            task_id: Task to finish

        Returns:
            Result dict with success, message, missing_work
        """
        # Check if we can stop
        check = self.integration.check_can_stop_safely(task_id)

        if not check['should_stop']:
            # System already sent alert, just return
            return {
                'success': False,
                'message': check['reason'],
                'missing_work': check['missing_work']
            }

        # OK to finish
        result = self.integration.finish_task_properly(task_id)

        # Send completion notification
        self._send_notification(
            f"✅ TASK COMPLETE\n\n"
            f"Task: {task_id}\n"
            f"Completed: {datetime.now().strftime('%H:%M:%S')}\n"
            f"Status: All subtasks verified"
        )

        return result

    def get_status(self) -> dict:
        """Get current system status"""
        alert_stats = self.alert_system.get_stats()
        stop_prevention_stats = self.workflow_system.get_stop_prevention_stats()

        return {
            'monitoring_active': alert_stats['monitoring_active'],
            'is_working': alert_stats['is_working'],
            'current_task': alert_stats['current_task'],
            'stops_detected': alert_stats['stop_count'],
            'alerts_sent': alert_stats['alerts_sent'],
            'stops_prevented': stop_prevention_stats['total_stops_prevented'],
            'last_activity': alert_stats['last_activity']
        }

    def _send_notification(self, message: str):
        """Send notification via Telegram"""
        self.alert_system._send_notification(message)


# Example usage showing the complete workflow
def example_usage():
    """
    Example showing how to use the system

    This ensures user is ALWAYS notified of stops
    """
    print("="*80)
    print("NEVER STOP UNNOTICED - Example Usage")
    print("="*80)

    # Initialize system
    # In production, set TELEGRAM_BOT_TOKEN environment variable
    system = NeverStopUnnoticedSystem()

    # Start a task
    task = system.start_task(
        task_id='example_task',
        description='Build 5 advanced AI systems',
        subtasks=[
            'Build self-improvement loop',
            'Build capability synergy',
            'Build real-world testing',
            'Build Telegram integration',
            'Build relationship memory',
            'Test all systems',
            'Verify everything',
            'Commit to GitHub'
        ],
        send_start_notification=True
    )

    print(f"\n✓ Task started: {task.description}")
    print(f"  Subtasks: {len(task.subtasks)}")
    print(f"  Monitoring: ACTIVE")
    print(f"  Telegram alerts: ENABLED")

    # Simulate working through subtasks
    print("\nSimulating work...")
    for i, subtask in enumerate(task.subtasks[:3], 1):
        time.sleep(2)  # Simulate work
        system.complete_subtask('example_task', subtask)
        print(f"  [{i}/8] {subtask} ✓")

        # Send heartbeat
        heartbeat(f"Completed {subtask}")

    # Try to finish early - should be PREVENTED
    print("\n⚠️ Attempting to finish with 5/8 subtasks incomplete...")
    result = system.try_to_finish('example_task')

    if not result['success']:
        print(f"  ✓ STOP PREVENTED: {result['message']}")
        print(f"  Missing work:")
        for work in result['missing_work']:
            print(f"    - {work}")
        print(f"  ✓ USER ALERTED via Telegram")

    # Complete remaining subtasks
    print("\nCompleting remaining work...")
    for i, subtask in enumerate(task.subtasks[3:], 4):
        time.sleep(1)
        system.complete_subtask('example_task', subtask)
        print(f"  [{i}/8] {subtask} ✓")
        heartbeat(f"Completed {subtask}")

    # Verify and finish
    print("\nVerifying all work...")
    system.workflow_system.verify_task('example_task', True, "All tests passed")
    heartbeat("Verification complete")

    # Now finish should succeed
    print("\nFinishing task...")
    result = system.try_to_finish('example_task')

    if result['success']:
        print(f"  ✓ TASK COMPLETE")
        print(f"  ✓ USER NOTIFIED via Telegram")

    # Show stats
    print("\n" + "="*80)
    print("SYSTEM STATISTICS")
    print("="*80)
    stats = system.get_status()
    print(f"Stops detected: {stats['stops_detected']}")
    print(f"Stops prevented: {stats['stops_prevented']}")
    print(f"Alerts sent: {stats['alerts_sent']}")
    print(f"Monitoring active: {stats['monitoring_active']}")

    print("\n" + "="*80)
    print("RESULT: User was kept informed throughout entire process")
    print("NEVER had to check chat to see if work stopped")
    print("="*80)


if __name__ == '__main__':
    # Set bot token from environment
    # export TELEGRAM_BOT_TOKEN="your_token_here"

    example_usage()
