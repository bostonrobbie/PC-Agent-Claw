#!/usr/bin/env python3
"""
Send proactive status updates to Rob
"""

import requests
import json
from datetime import datetime

BOT_TOKEN = "7509919329:AAEm5g4H7YYiUTkrQiRNdoJmMgM4PW5M4gA"
CHAT_ID = "5791597360"

def send_update(status_type, message):
    """
    Send status update to Rob

    status_type: 'starting', 'progress', 'blocked', 'complete', 'error'
    """

    icons = {
        'starting': '🚀',
        'progress': '⏳',
        'blocked': '🚧',
        'complete': '✅',
        'error': '❌'
    }

    icon = icons.get(status_type, 'ℹ️')
    timestamp = datetime.now().strftime('%I:%M %p')

    formatted_msg = f"{icon} [{timestamp}] {message}"

    try:
        response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": formatted_msg},
            timeout=10
        )
        return response.status_code == 200
    except Exception as e:
        print(f"Failed to send update: {e}")
        return False

# Quick functions for common updates
def notify_starting(task):
    send_update('starting', f"Starting: {task}")

def notify_progress(task, details):
    send_update('progress', f"{task} - {details}")

def notify_blocked(task, blocker):
    send_update('blocked', f"BLOCKED on {task}: {blocker}")

def notify_complete(task):
    send_update('complete', f"Completed: {task}")

def notify_error(task, error):
    send_update('error', f"ERROR in {task}: {error}")

if __name__ == "__main__":
    # Test
    send_update('starting', "Test notification system")
