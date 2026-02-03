#!/usr/bin/env python3
"""Robust Telegram Connector - Fixes all connection issues"""
import requests
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict
import queue
import threading

class TelegramConnector:
    """Robust Telegram connection with retry logic and error handling"""

    def __init__(self, bot_token: str = None, chat_id: str = None):
        workspace = Path(__file__).parent.parent
        self.config_file = workspace / "telegram_config.json"

        # Load config
        self.bot_token = bot_token
        self.chat_id = chat_id or "5791597360"
        self.enabled = False

        if not bot_token:
            self._load_config()

        if self.bot_token:
            self.enabled = True

        # Message queue for retry logic
        self.message_queue = queue.Queue()
        self.running = False
        self.worker_thread = None

        # Stats
        self.messages_sent = 0
        self.messages_failed = 0
        self.last_error = None

    def _load_config(self):
        """Load configuration from file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.bot_token = config.get('bot_token')
                    self.chat_id = config.get('chat_id', self.chat_id)
            except Exception as e:
                print(f"Error loading config: {e}")

    def save_config(self, bot_token: str):
        """Save configuration to file"""
        config = {
            'bot_token': bot_token,
            'chat_id': self.chat_id,
            'enabled': True
        }

        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)

            self.bot_token = bot_token
            self.enabled = True
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False

    def send_message(self, message: str, priority: str = "normal",
                    parse_mode: str = None, retry: bool = True) -> bool:
        """
        Send message to Telegram with retry logic

        Args:
            message: Message text (will be sanitized for encoding)
            priority: Priority level (for future use)
            parse_mode: 'Markdown' or 'HTML' (None for plain text)
            retry: Whether to retry on failure
        """
        if not self.enabled:
            print(f"[Telegram Disabled] Message: {message[:100]}")
            self._log_to_file(message)
            return False

        # Sanitize message for encoding issues
        message = self._sanitize_message(message)

        # Build request
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

        payload = {
            'chat_id': self.chat_id,
            'text': message
        }

        if parse_mode:
            payload['parse_mode'] = parse_mode

        # Try to send
        for attempt in range(3 if retry else 1):
            try:
                response = requests.post(url, json=payload, timeout=10)

                if response.status_code == 200:
                    self.messages_sent += 1
                    print(f"[OK] Sent to Telegram ({len(message)} chars)")
                    return True

                elif response.status_code == 401:
                    self.last_error = "Unauthorized - Invalid bot token"
                    print(f"[ERROR] {self.last_error}")
                    self.enabled = False
                    self._log_to_file(f"AUTH ERROR: {message}")
                    return False

                else:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    self.last_error = error_msg
                    print(f"[ERROR] {error_msg}")

                    if attempt < 2:
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue

            except requests.exceptions.Timeout:
                print(f"[TIMEOUT] Attempt {attempt + 1}/3")
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue

            except Exception as e:
                self.last_error = str(e)
                print(f"[ERROR] {e}")
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue

        # All attempts failed
        self.messages_failed += 1
        self._log_to_file(f"FAILED: {message}")
        return False

    def _sanitize_message(self, message: str) -> str:
        """Sanitize message to avoid encoding issues"""
        # Remove problematic Unicode characters
        replacements = {
            '\u2705': '[OK]',      # ✅
            '\u274c': '[X]',       # ❌
            '\u2139': '[i]',       # ℹ️
            '\U0001f680': '[*]',   # 🚀
            '\U0001f4ca': '[^]',   # 📊
            '\u23f3': '...',       # ⏳
            '\U0001f916': '[AI]',  # 🤖
            '\U0001f4bc': '[$$]',  # 💼
            '\U0001f9e0': '[*]',   # 🧠
        }

        for unicode_char, replacement in replacements.items():
            message = message.replace(unicode_char, replacement)

        # Ensure ASCII-safe
        try:
            message.encode('ascii')
        except UnicodeEncodeError:
            # Replace remaining non-ASCII
            message = message.encode('ascii', errors='replace').decode('ascii')

        return message

    def _log_to_file(self, message: str):
        """Log message to file as backup"""
        workspace = Path(__file__).parent.parent
        log_file = workspace / "telegram_log.txt"

        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"[{timestamp}] {message}\n")
        except Exception as e:
            print(f"Failed to log to file: {e}")

    def start_queue_worker(self):
        """Start background worker for message queue"""
        if self.running:
            return

        self.running = True
        self.worker_thread = threading.Thread(target=self._queue_worker, daemon=True)
        self.worker_thread.start()

    def stop_queue_worker(self):
        """Stop background worker"""
        self.running = False

    def _queue_worker(self):
        """Background worker to process queued messages"""
        while self.running:
            try:
                message = self.message_queue.get(timeout=1)
                self.send_message(message['text'], message.get('priority', 'normal'))
                self.message_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Queue worker error: {e}")

    def queue_message(self, message: str, priority: str = "normal"):
        """Add message to queue for async sending"""
        self.message_queue.put({
            'text': message,
            'priority': priority,
            'timestamp': datetime.now().isoformat()
        })

    def test_connection(self) -> bool:
        """Test Telegram connection"""
        if not self.enabled:
            print("[TEST] Telegram not enabled")
            return False

        test_msg = "Test message from Claude AI Agent"
        return self.send_message(test_msg, retry=False)

    def get_stats(self) -> Dict:
        """Get connection statistics"""
        return {
            'enabled': self.enabled,
            'messages_sent': self.messages_sent,
            'messages_failed': self.messages_failed,
            'last_error': self.last_error,
            'queue_size': self.message_queue.qsize()
        }


# Convenience functions
def send_update(message: str):
    """Quick send update"""
    connector = TelegramConnector()
    connector.send_message(message)

def send_error(message: str):
    """Quick send error"""
    connector = TelegramConnector()
    connector.send_message(f"[ERROR] {message}")

def send_success(message: str):
    """Quick send success"""
    connector = TelegramConnector()
    connector.send_message(f"[OK] {message}")


if __name__ == '__main__':
    import sys

    connector = TelegramConnector()

    if len(sys.argv) > 2 and sys.argv[1] == 'setup':
        # Setup bot token
        bot_token = sys.argv[2]
        if connector.save_config(bot_token):
            print("Config saved!")
            if connector.test_connection():
                print("Connection successful!")
            else:
                print("Connection failed - check token")
    elif len(sys.argv) > 1 and sys.argv[1] == 'test':
        # Test connection
        stats = connector.get_stats()
        print(f"Telegram Status: {'Enabled' if stats['enabled'] else 'Disabled'}")
        print(f"Messages sent: {stats['messages_sent']}")
        print(f"Messages failed: {stats['messages_failed']}")

        if stats['enabled']:
            print("\nTesting connection...")
            if connector.test_connection():
                print("SUCCESS!")
            else:
                print(f"FAILED: {stats['last_error']}")
    else:
        print("Robust Telegram Connector")
        print("\nUsage:")
        print("  python telegram_connector.py setup BOT_TOKEN")
        print("  python telegram_connector.py test")
        print("\nStatus:", "Enabled" if connector.enabled else "Disabled")
