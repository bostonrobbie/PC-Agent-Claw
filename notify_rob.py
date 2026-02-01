#!/usr/bin/env python3
"""
Notify Rob - Quick notification wrapper
"""

import sys
from telegram_notifier import TelegramNotifier

def notify(message, priority="info"):
    """Quick notification function"""
    notifier = TelegramNotifier()
    notifier.send_message(message, priority=priority)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python notify_rob.py <message> [priority]")
        print("Priority: info, error, success, urgent")
        sys.exit(1)

    message = sys.argv[1]
    priority = sys.argv[2] if len(sys.argv) > 2 else "info"

    notify(message, priority)
