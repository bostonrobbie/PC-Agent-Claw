#!/usr/bin/env python3
"""
Send image to Telegram
"""
import requests
import json
import sys
from pathlib import Path

WORKSPACE = Path(r"C:\Users\User\.openclaw\workspace")

def send_image(image_path, caption=""):
    """Send image to Rob via Telegram"""

    # Load config
    config_file = WORKSPACE / "telegram_config.json"
    if not config_file.exists():
        print("Telegram config not found")
        return False

    with open(config_file, 'r') as f:
        config = json.load(f)

    bot_token = config.get('bot_token')
    chat_id = config.get('chat_id', '5791597360')

    if not bot_token:
        print("Bot token not configured")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"

    with open(image_path, 'rb') as photo:
        files = {'photo': photo}
        data = {
            'chat_id': chat_id,
            'caption': caption,
            'parse_mode': 'HTML'
        }

        try:
            response = requests.post(url, files=files, data=data, timeout=30)
            if response.status_code == 200:
                print(f"Image sent successfully: {image_path}")
                return True
            else:
                print(f"Error sending image: {response.status_code}")
                print(response.text)
                return False
        except Exception as e:
            print(f"Failed to send image: {e}")
            return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python send_telegram_image.py <image_path> [caption]")
        sys.exit(1)

    image_path = sys.argv[1]
    caption = sys.argv[2] if len(sys.argv) > 2 else ""

    send_image(image_path, caption)
