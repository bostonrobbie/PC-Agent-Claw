#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Intelligence Bot - Interactive Demo

Demonstrates all features of the Telegram Intelligence Bot without
requiring an actual Telegram connection.
"""

import sys
import io

# Fix Unicode output on Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import sys
import time
from pathlib import Path

# Add workspace to path
WORKSPACE_PATH = Path(__file__).parent.parent
sys.path.append(str(WORKSPACE_PATH))

from telegram.intelligence_bot import TelegramIntelligenceBot


def print_section(title):
    """Print a section header"""
    print("\n" + "="*80)
    print(title)
    print("="*80 + "\n")


def demo_commands(bot):
    """Demonstrate command-based interface"""
    print_section("COMMAND-BASED INTERFACE DEMO")

    commands = [
        ("help", [], "Show available commands"),
        ("status", [], "Get system status"),
        ("search", ["memory management"], "Search for memory-related code"),
        ("patterns", [], "Show learned patterns"),
        ("improve", [], "Get improvement suggestions"),
    ]

    for cmd, args, description in commands:
        print(f"Command: /{cmd} {' '.join(args)}")
        print(f"Description: {description}")
        print("-" * 80)

        start_time = time.time()
        response = bot.handle_command(cmd, args, "demo_chat")
        execution_time = time.time() - start_time

        # Truncate long responses
        if len(response) > 500:
            print(response[:500] + "\n... (truncated)")
        else:
            print(response)

        print(f"\nExecution time: {execution_time:.2f}s")
        print()


def demo_natural_language(bot):
    """Demonstrate natural language interface"""
    print_section("NATURAL LANGUAGE INTERFACE DEMO")

    queries = [
        "find authentication code",
        "what's your status?",
        "show me patterns you've learned",
        "how can I improve my code?",
        "search for database connections",
    ]

    for query in queries:
        print(f"User: \"{query}\"")
        print("-" * 80)

        start_time = time.time()
        response = bot.handle_natural_language(query, "demo_chat")
        execution_time = time.time() - start_time

        # Truncate long responses
        if len(response) > 500:
            print(f"Bot: {response[:500]}\n... (truncated)")
        else:
            print(f"Bot: {response}")

        print(f"\nExecution time: {execution_time:.2f}s")
        print()


def demo_notifications(bot):
    """Demonstrate notification system"""
    print_section("NOTIFICATION SYSTEM DEMO")

    notifications = [
        ("Analysis complete!", "normal", "analysis"),
        ("Security vulnerability detected", "high", "security"),
        ("System performance degraded", "critical", "monitoring"),
        ("Pattern discovered in code", "low", "learning"),
    ]

    print("Sending notifications with various priorities...\n")

    for message, priority, category in notifications:
        print(f"Priority: {priority.upper()}")
        print(f"Category: {category}")
        print(f"Message: {message}")

        # Mock sending (won't actually send without token)
        success = bot.send_notification(message, priority, category, "demo_chat")

        print(f"Status: {'✅ Sent' if success else '📝 Logged (no token)'}")
        print()


def demo_analytics(bot):
    """Demonstrate analytics and tracking"""
    print_section("ANALYTICS & TRACKING DEMO")

    # Get statistics
    stats = bot.get_stats()

    print("Bot Usage Statistics:")
    print("-" * 80)
    print(f"Total interactions: {stats.get('total_interactions', 0)}")
    print(f"Average response time: {stats.get('avg_response_time', 0):.2f}s")

    print("\nCommand Breakdown:")
    breakdown = stats.get('command_breakdown', {})
    if breakdown:
        for cmd, count in sorted(breakdown.items(), key=lambda x: x[1], reverse=True):
            print(f"  {cmd}: {count} executions")
    else:
        print("  No commands executed yet")

    print("\nNotifications:")
    notifs = stats.get('notifications', {})
    print(f"  Total: {notifs.get('total', 0)}")
    print(f"  Delivered: {notifs.get('delivered', 0)}")
    print(f"  Delivery rate: {notifs.get('delivery_rate', 0):.1%}")

    # Get interaction history
    print("\n" + "-" * 80)
    print("Recent Interaction History:")
    history = bot.get_interaction_history(limit=5)

    if history:
        for i, interaction in enumerate(history, 1):
            print(f"\n{i}. Command: {interaction['command']}")
            print(f"   Success: {'✅' if interaction['success'] else '❌'}")
            if interaction['response_time']:
                print(f"   Response time: {interaction['response_time']:.2f}s")
    else:
        print("  No interaction history yet")


def demo_hub_integration(bot):
    """Demonstrate Intelligence Hub integration"""
    print_section("INTELLIGENCE HUB INTEGRATION DEMO")

    print("The bot deeply integrates with all 25 Intelligence Hub capabilities:")
    print()

    capabilities = [
        ("Memory Systems", ["Persistent memory", "Context manager", "Mistake learner"]),
        ("Search & Discovery", ["Semantic code search", "Pattern detection"]),
        ("Autonomous", ["Background tasks", "Auto-debugger"]),
        ("Security", ["Vulnerability scanner", "Security monitoring"]),
        ("Advanced", ["Math engine", "Real-time internet"]),
    ]

    for category, items in capabilities:
        print(f"✅ {category}:")
        for item in items:
            print(f"   - {item}")
        print()

    print("Testing hub access...")
    print("-" * 80)

    # Test hub is accessible
    print(f"Hub workspace: {bot.hub.workspace_path}")
    print(f"Hub session: {bot.hub.session_id}")
    print(f"Hub running: {bot.hub.running}")

    # Test some capabilities
    print("\nCapability Health Check:")

    try:
        memory_stats = bot.hub.memory.get_stats()
        print(f"✅ Memory: {memory_stats['total_decisions']} decisions stored")
    except Exception as e:
        print(f"❌ Memory: {e}")

    try:
        search_stats = bot.hub.code_search.get_stats()
        print(f"✅ Code Search: {search_stats['total_chunks']} chunks indexed")
    except Exception as e:
        print(f"❌ Code Search: {e}")

    try:
        task_stats = bot.hub.background_tasks.get_stats()
        print(f"✅ Background Tasks: {task_stats['tasks_completed']} completed")
    except Exception as e:
        print(f"❌ Background Tasks: {e}")


def main():
    """Run the interactive demo"""
    print("="*80)
    print("TELEGRAM INTELLIGENCE BOT - INTERACTIVE DEMO")
    print("="*80)
    print()
    print("This demo shows all features without requiring a Telegram connection.")
    print("The bot will work in 'mock mode' - logging messages instead of sending.")
    print()

    # Initialize bot
    print("Initializing bot...")
    bot = TelegramIntelligenceBot(
        bot_token=None,  # No token = mock mode
        chat_id="demo_chat_123",
        db_path="demo_telegram_bot.db"
    )
    print("✅ Bot initialized successfully!")
    print()

    # Run demonstrations
    try:
        demo_commands(bot)
        demo_natural_language(bot)
        demo_notifications(bot)
        demo_analytics(bot)
        demo_hub_integration(bot)

        # Final summary
        print_section("DEMO COMPLETE")
        print("The Telegram Intelligence Bot successfully demonstrated:")
        print("  ✅ Command-based interface (8 commands)")
        print("  ✅ Natural language understanding")
        print("  ✅ Real-time notifications with priorities")
        print("  ✅ Rich formatted responses")
        print("  ✅ User interaction tracking")
        print("  ✅ Deep Intelligence Hub integration")
        print()
        print("Next Steps:")
        print("  1. Configure your Telegram bot token")
        print("  2. Connect to your chat ID")
        print("  3. Start using natural language to access all 25 AI capabilities!")
        print()
        print("="*80)

    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        print(f"\n\nError during demo: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        import os
        if os.path.exists("demo_telegram_bot.db"):
            try:
                time.sleep(0.1)
                os.remove("demo_telegram_bot.db")
                print("Cleaned up demo database")
            except:
                pass


if __name__ == "__main__":
    main()
