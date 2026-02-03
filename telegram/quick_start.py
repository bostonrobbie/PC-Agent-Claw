#!/usr/bin/env python3
"""
Telegram Intelligence Bot - Quick Start Example

Simple example showing how to use the bot.
"""

import sys
from pathlib import Path

# Add workspace to path
WORKSPACE_PATH = Path(__file__).parent.parent
sys.path.append(str(WORKSPACE_PATH))

from telegram.intelligence_bot import TelegramIntelligenceBot


def main():
    """Quick start example"""
    print("Telegram Intelligence Bot - Quick Start")
    print("=" * 60)
    print()

    # Initialize the bot
    print("1. Initializing bot...")
    bot = TelegramIntelligenceBot()
    print("   OK Bot initialized")
    print()

    # Example 1: Get system status
    print("2. Getting system status...")
    status = bot.handle_command("status", [], "quick_start_chat")
    print(status[:300] + "..." if len(status) > 300 else status)
    print()

    # Example 2: Search for code
    print("3. Searching for code...")
    search_result = bot.handle_command("search", ["database"], "quick_start_chat")
    print(search_result[:300] + "..." if len(search_result) > 300 else search_result)
    print()

    # Example 3: Natural language query
    print("4. Using natural language...")
    nl_result = bot.handle_natural_language("what's your status?", "quick_start_chat")
    print(nl_result[:300] + "..." if len(nl_result) > 300 else nl_result)
    print()

    # Example 4: Get statistics
    print("5. Getting bot statistics...")
    stats = bot.get_stats()
    print(f"   Total interactions: {stats.get('total_interactions', 0)}")
    print(f"   Commands executed: {sum(stats.get('command_breakdown', {}).values())}")
    print(f"   Average response time: {stats.get('avg_response_time', 0):.2f}s")
    print()

    print("=" * 60)
    print("Quick start complete!")
    print()
    print("To use with real Telegram:")
    print("1. Set TELEGRAM_BOT_TOKEN environment variable")
    print("2. Set TELEGRAM_CHAT_ID environment variable")
    print("3. Call bot.connect(your_chat_id)")
    print("4. Start messaging the bot!")
    print()


if __name__ == "__main__":
    main()
