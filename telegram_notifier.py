#!/usr/bin/env python3
"""
Telegram Notifier - Send messages to Rob proactively
"""

import requests
import json
from pathlib import Path
from datetime import datetime

WORKSPACE = Path(r"C:\Users\User\.openclaw\workspace")

class TelegramNotifier:
    """Send notifications to Rob via Telegram"""

    def __init__(self):
        # These will be configured
        self.bot_token = None
        self.chat_id = "5791597360"  # Rob's Telegram ID
        self.enabled = False
        self.load_config()

    def load_config(self):
        """Load Telegram configuration if it exists"""
        config_file = WORKSPACE / "telegram_config.json"
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
                self.bot_token = config.get('bot_token')
                self.chat_id = config.get('chat_id', self.chat_id)
                self.enabled = bool(self.bot_token)

    def send_message(self, message, priority="normal"):
        """Send a message to Rob"""

        if not self.enabled:
            print(f"[Telegram Disabled] Would send: {message}")
            # Log to file instead
            log_file = WORKSPACE / "notifications_log.txt"
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"[{datetime.now()}] [{priority}] {message}\n")
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

        # Add priority indicator
        if priority == "urgent":
            message = f"🚨 URGENT: {message}"
        elif priority == "error":
            message = f"❌ ERROR: {message}"
        elif priority == "success":
            message = f"✅ SUCCESS: {message}"
        elif priority == "info":
            message = f"ℹ️ INFO: {message}"

        payload = {
            'chat_id': self.chat_id,
            'text': message,
            'parse_mode': 'Markdown'
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                print(f"[OK] Sent to Telegram: {message[:50]}...")
                return True
            else:
                print(f"[ERROR] Telegram API error: {response.status_code}")
                return False
        except Exception as e:
            print(f"[ERROR] Could not send to Telegram: {e}")
            return False

    def notify_error(self, error_message, details=None):
        """Notify about an error"""
        msg = f"{error_message}"
        if details:
            msg += f"\n\nDetails: {details}"
        self.send_message(msg, priority="error")

    def notify_progress(self, task, status):
        """Notify about task progress"""
        msg = f"Task: {task}\nStatus: {status}"
        self.send_message(msg, priority="info")

    def notify_completion(self, task, result=None):
        """Notify about task completion"""
        msg = f"Completed: {task}"
        if result:
            msg += f"\nResult: {result}"
        self.send_message(msg, priority="success")

    def notify_waiting(self, waiting_for, reason):
        """Notify that I'm waiting for something"""
        msg = f"⏳ Waiting for: {waiting_for}\nReason: {reason}"
        self.send_message(msg, priority="info")

    def setup_bot(self):
        """Guide to set up Telegram bot"""
        print("=" * 60)
        print("Telegram Bot Setup Guide")
        print("=" * 60)
        print()
        print("To enable Telegram notifications:")
        print()
        print("1. Message @BotFather on Telegram")
        print("2. Send: /newbot")
        print("3. Follow prompts to create bot")
        print("4. Copy the bot token")
        print("5. Run this script with token:")
        print()
        print("   python telegram_notifier.py setup YOUR_BOT_TOKEN")
        print()
        print("Then I can message you proactively!")
        print("=" * 60)

def setup_config(bot_token):
    """Save Telegram configuration"""
    config = {
        'bot_token': bot_token,
        'chat_id': '5791597360',
        'enabled': True
    }

    config_file = WORKSPACE / "telegram_config.json"
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)

    print(f"[OK] Configuration saved to: {config_file}")
    print("Telegram notifications enabled!")

    # Test it
    notifier = TelegramNotifier()
    notifier.send_message("🤖 Claude AI Agent is now connected!\n\nI can send you updates, errors, and progress notifications.", priority="success")

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 2 and sys.argv[1] == "setup":
        setup_config(sys.argv[2])
    elif len(sys.argv) > 1 and sys.argv[1] == "test":
        notifier = TelegramNotifier()
        notifier.send_message("Test message from Claude", priority="info")
    else:
        notifier = TelegramNotifier()
        notifier.setup_bot()
