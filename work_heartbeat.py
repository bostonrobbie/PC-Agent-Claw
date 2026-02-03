#!/usr/bin/env python3
"""
Work Heartbeat System - Keep Rob updated on continuous progress
Prevents the "work for a few minutes then stop" problem
"""

import time
import threading
from datetime import datetime, timedelta
from task_status_notifier import TaskStatusNotifier

class WorkHeartbeat:
    """Monitor work progress and send periodic updates"""

    def __init__(self):
        self.notifier = TaskStatusNotifier()
        self.current_task = None
        self.task_start_time = None
        self.last_update_time = None
        self.is_working = False
        self.heartbeat_interval = 900  # 15 minutes in seconds
        self.blocker_threshold = 300   # 5 minutes - notify if stuck

    def start_task(self, task_name):
        """Start tracking a new task"""
        self.current_task = task_name
        self.task_start_time = datetime.now()
        self.last_update_time = datetime.now()
        self.is_working = True

        # Notify task started
        self.notifier.task_started(task_name)

    def complete_task(self, next_task=None):
        """Mark current task as complete"""
        if self.current_task:
            self.notifier.task_completed(self.current_task, next_task)
            self.current_task = None
            self.is_working = False

    def send_progress_update(self, progress_pct, details=None):
        """Send a progress update for long-running tasks"""
        if self.current_task:
            self.notifier.progress_update(self.current_task, progress_pct, details)
            self.last_update_time = datetime.now()

    def mark_blocked(self, blocker_reason):
        """Mark current task as blocked"""
        if self.current_task:
            self.notifier.blocked(self.current_task, blocker_reason)
            self.is_working = False

    def take_break(self, reason="All tasks completed"):
        """Notify that taking a break"""
        self.notifier.taking_break(reason)
        self.is_working = False

    def check_if_stale(self):
        """Check if we haven't sent update in too long"""
        if not self.is_working:
            return False

        time_since_update = (datetime.now() - self.last_update_time).total_seconds()

        # Send heartbeat if working for >15 mins without update
        if time_since_update > self.heartbeat_interval:
            self.send_progress_update(
                progress_pct=50,  # Generic progress
                details=f"Still working on this (running for {int(time_since_update/60)} mins)"
            )
            return True

        return False

    def auto_heartbeat_loop(self, check_interval=60):
        """Background thread to auto-send heartbeats"""
        while self.is_working:
            time.sleep(check_interval)
            self.check_if_stale()


# Global heartbeat instance
heartbeat = WorkHeartbeat()


def start_work_session(task_name):
    """Start a work session"""
    heartbeat.start_task(task_name)


def finish_work_session(next_task=None):
    """Finish current work session"""
    heartbeat.complete_task(next_task)


def progress(percent, details=None):
    """Quick progress update"""
    heartbeat.send_progress_update(percent, details)


def blocked(reason):
    """Mark as blocked"""
    heartbeat.mark_blocked(reason)


def taking_break(reason="All tasks completed"):
    """Take a break"""
    heartbeat.take_break(reason)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Work Heartbeat System")
        print("Usage:")
        print("  python work_heartbeat.py start '<task_name>'")
        print("  python work_heartbeat.py complete '<next_task>'")
        print("  python work_heartbeat.py progress <percent> '<details>'")
        print("  python work_heartbeat.py blocked '<reason>'")
        print("  python work_heartbeat.py break '<reason>'")
        sys.exit(1)

    command = sys.argv[1]

    if command == "start":
        task = sys.argv[2] if len(sys.argv) > 2 else "Task"
        start_work_session(task)

    elif command == "complete":
        next_task = sys.argv[2] if len(sys.argv) > 2 else None
        finish_work_session(next_task)

    elif command == "progress":
        pct = int(sys.argv[2]) if len(sys.argv) > 2 else 50
        details = sys.argv[3] if len(sys.argv) > 3 else None
        progress(pct, details)

    elif command == "blocked":
        reason = sys.argv[2] if len(sys.argv) > 2 else "Unknown blocker"
        blocked(reason)

    elif command == "break":
        reason = sys.argv[2] if len(sys.argv) > 2 else "All tasks completed"
        taking_break(reason)
