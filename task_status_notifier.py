#!/usr/bin/env python3
"""
Task Status Notifier - Proactive task updates to Rob via Telegram
Redesigned for continuous task completion notifications
"""

import requests
import json
import sys
from pathlib import Path
from datetime import datetime

WORKSPACE = Path(r"C:\Users\User\.openclaw\workspace")

class TaskStatusNotifier:
    """Proactive task status updates via Telegram"""

    def __init__(self):
        self.bot_token = None
        self.chat_id = "5791597360"  # Rob's Telegram ID
        self.enabled = False
        self.load_config()

        # Last notification time for throttling
        self.last_notification = None
        self.min_interval_seconds = 0  # No throttling - send immediately

    def load_config(self):
        """Load Telegram configuration"""
        config_file = WORKSPACE / "telegram_config.json"
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
                self.bot_token = config.get('bot_token')
                self.chat_id = config.get('chat_id', self.chat_id)
                self.enabled = bool(self.bot_token)

    def send_message(self, message):
        """Send message to Telegram - handles encoding properly"""

        if not self.enabled:
            # Log to file if Telegram disabled
            log_file = WORKSPACE / "task_status_log.txt"
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"[{datetime.now()}] {message}\n")
            # Safely print without emoji encoding errors on Windows
            try:
                print(f"[Logged] {message}")
            except UnicodeEncodeError:
                print(f"[Logged] {message.encode('ascii', 'replace').decode('ascii')}")
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

        payload = {
            'chat_id': self.chat_id,
            'text': message,
            'parse_mode': 'HTML'  # Using HTML instead of Markdown for better emoji support
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                # Safely print without emoji encoding errors
                try:
                    print(f"[Telegram] Sent: {message[:60]}...")
                except UnicodeEncodeError:
                    print("[Telegram] Sent (message contains emojis)")
                self.last_notification = datetime.now()
                return True
            else:
                print(f"[ERROR] Telegram API error: {response.status_code}")
                print(f"Response: {response.text}")
                return False
        except UnicodeEncodeError as e:
            # This shouldn't happen with requests, but handle it
            print(f"[ERROR] Unicode encoding issue: {e}")
            return False
        except Exception as e:
            print(f"[ERROR] Could not send: {e}")
            return False

    # ========================================================================
    # TASK STATUS METHODS
    # ========================================================================

    def task_completed(self, task_name, next_task=None):
        """Notify that a task was completed and what's next"""
        msg = f"✅ <b>Completed:</b> {task_name}"
        if next_task:
            msg += f"\n\n🔨 <b>Next:</b> {next_task}"
        self.send_message(msg)

    def task_started(self, task_name):
        """Notify that a task was started"""
        msg = f"🚀 <b>Started:</b> {task_name}"
        self.send_message(msg)

    def taking_break(self, reason="No active tasks"):
        """Notify that I'm taking a break"""
        msg = f"⏸️ <b>Taking a break</b>\n\n{reason}"
        self.send_message(msg)

    def blocked(self, task_name, blocker_reason):
        """Notify that I'm blocked on something"""
        msg = f"🚧 <b>Blocked:</b> {task_name}\n\n<b>Reason:</b> {blocker_reason}"
        self.send_message(msg)

    def error_occurred(self, task_name, error_message):
        """Notify about an error"""
        msg = f"❌ <b>Error in:</b> {task_name}\n\n<b>Details:</b> {error_message}"
        self.send_message(msg)

    def milestone_reached(self, milestone, completed_count, total_count):
        """Notify about reaching a milestone"""
        msg = f"🎯 <b>Milestone:</b> {milestone}\n\n<b>Progress:</b> {completed_count}/{total_count} tasks"
        self.send_message(msg)

    def progress_update(self, current_task, progress_pct, details=None):
        """General progress update"""
        msg = f"📊 <b>Progress:</b> {progress_pct}%\n\n<b>Current:</b> {current_task}"
        if details:
            msg += f"\n<b>Details:</b> {details}"
        self.send_message(msg)

    def timeout_occurred(self, task_name, timeout_duration):
        """Notify about a timeout"""
        msg = f"⏱️ <b>Timeout:</b> {task_name}\n\n<b>Duration:</b> {timeout_duration}"
        self.send_message(msg)

    def day_summary(self, tasks_completed, tasks_remaining, highlights):
        """End of day summary"""
        msg = f"📋 <b>Day Summary</b>\n\n"
        msg += f"✅ Completed: {tasks_completed}\n"
        msg += f"⏳ Remaining: {tasks_remaining}\n\n"
        msg += f"<b>Highlights:</b>\n{highlights}"
        self.send_message(msg)


def quick_notify(message_type, *args):
    """Quick notification wrapper for command line use"""
    notifier = TaskStatusNotifier()

    if message_type == "completed":
        task = args[0] if len(args) > 0 else "Task"
        next_task = args[1] if len(args) > 1 else None
        notifier.task_completed(task, next_task)

    elif message_type == "started":
        task = args[0] if len(args) > 0 else "Task"
        notifier.task_started(task)

    elif message_type == "break":
        reason = args[0] if len(args) > 0 else "No active tasks"
        notifier.taking_break(reason)

    elif message_type == "blocked":
        task = args[0] if len(args) > 0 else "Task"
        reason = args[1] if len(args) > 1 else "Unknown blocker"
        notifier.blocked(task, reason)

    elif message_type == "error":
        task = args[0] if len(args) > 0 else "Task"
        error = args[1] if len(args) > 1 else "Unknown error"
        notifier.error_occurred(task, error)

    else:
        print(f"Unknown message type: {message_type}")
        print("Valid types: completed, started, break, blocked, error")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("=" * 70)
        print("Task Status Notifier - Proactive Updates to Rob")
        print("=" * 70)
        print()
        print("Usage:")
        print("  python task_status_notifier.py completed '<task>' '<next_task>'")
        print("  python task_status_notifier.py started '<task>'")
        print("  python task_status_notifier.py break '<reason>'")
        print("  python task_status_notifier.py blocked '<task>' '<reason>'")
        print("  python task_status_notifier.py error '<task>' '<error_msg>'")
        print()
        print("Examples:")
        print("  python task_status_notifier.py completed 'Fixed TypeScript errors' 'Working on Google Ads'")
        print("  python task_status_notifier.py break 'Waiting for browser access'")
        print("  python task_status_notifier.py blocked 'Manus access' 'Need login credentials'")
        print()
        sys.exit(1)

    message_type = sys.argv[1]
    args = sys.argv[2:] if len(sys.argv) > 2 else []

    quick_notify(message_type, *args)
