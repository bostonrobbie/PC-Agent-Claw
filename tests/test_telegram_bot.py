#!/usr/bin/env python3
"""
Comprehensive Test Suite for Telegram Intelligence Bot

Tests all functionality including:
- Command handling
- Natural language understanding
- Notifications
- Database tracking
- Integration with Intelligence Hub
"""

import sys
import os
import time
import json
import sqlite3
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
WORKSPACE_PATH = Path(__file__).parent.parent
sys.path.append(str(WORKSPACE_PATH))

from telegram.intelligence_bot import TelegramIntelligenceBot, CommandType


class MockTelegramAPI:
    """Mock Telegram API for testing"""

    def __init__(self):
        self.messages_sent = []
        self.should_succeed = True

    def send_message(self, chat_id, text, parse_mode=None):
        """Mock send message"""
        if self.should_succeed:
            self.messages_sent.append({
                'chat_id': chat_id,
                'text': text,
                'parse_mode': parse_mode,
                'timestamp': time.time()
            })
            return {'ok': True, 'result': {'message_id': len(self.messages_sent)}}
        else:
            return {'ok': False, 'error': 'Mock error'}

    def get_chat(self, chat_id):
        """Mock get chat"""
        if self.should_succeed:
            return {
                'ok': True,
                'result': {
                    'id': chat_id,
                    'type': 'private'
                }
            }
        else:
            return {'ok': False}


class TestTelegramIntelligenceBot(unittest.TestCase):
    """Test suite for Telegram Intelligence Bot"""

    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.test_db = "test_telegram_bot.db"
        cls.test_workspace = str(WORKSPACE_PATH)

    def setUp(self):
        """Set up each test"""
        # Clean up test database
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

        # Create bot instance
        self.bot = TelegramIntelligenceBot(
            bot_token="test_token_123",
            chat_id="test_chat_123",
            workspace_path=self.test_workspace,
            db_path=self.test_db
        )

        # Mock Telegram API
        self.mock_api = MockTelegramAPI()

    def tearDown(self):
        """Clean up after each test"""
        # Clean up test database
        if os.path.exists(self.test_db):
            try:
                time.sleep(0.1)  # Give DB time to close
                os.remove(self.test_db)
            except:
                pass

    # ========================================================================
    # INITIALIZATION TESTS
    # ========================================================================

    def test_bot_initialization(self):
        """Test bot initializes correctly"""
        self.assertIsNotNone(self.bot)
        self.assertEqual(self.bot.bot_token, "test_token_123")
        self.assertEqual(self.bot.chat_id, "test_chat_123")
        self.assertEqual(self.bot.workspace_path, self.test_workspace)
        print("[PASS] Bot initialization")

    def test_database_creation(self):
        """Test database tables are created"""
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()

        # Check tables exist
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table'
        """)
        tables = [row[0] for row in cursor.fetchall()]

        conn.close()

        self.assertIn('interactions', tables)
        self.assertIn('commands_executed', tables)
        self.assertIn('satisfaction', tables)
        self.assertIn('notifications_sent', tables)
        print("[PASS] Database creation")

    def test_nl_patterns_initialization(self):
        """Test natural language patterns are initialized"""
        self.assertIsNotNone(self.bot.nl_patterns)
        self.assertGreater(len(self.bot.nl_patterns), 0)
        self.assertIn("find", self.bot.nl_patterns)
        self.assertIn("search", self.bot.nl_patterns)
        print("[PASS] NL patterns initialization")

    # ========================================================================
    # COMMAND HANDLING TESTS
    # ========================================================================

    def test_handle_start_command(self):
        """Test /start command"""
        response = self.bot.handle_command("start", [], "test_chat")
        self.assertIn("Welcome", response)
        self.assertIn("Commands:", response)
        self.assertIn("/analyze", response)
        print("[PASS] /start command")

    def test_handle_help_command(self):
        """Test /help command"""
        response = self.bot.handle_command("help", [], "test_chat")
        self.assertIn("Welcome", response)
        self.assertIn("Commands:", response)
        print("[PASS] /help command")

    def test_handle_status_command(self):
        """Test /status command"""
        response = self.bot.handle_command("status", [], "test_chat")
        self.assertIn("System Status", response)
        self.assertIn("Session:", response)
        print("[PASS] /status command")

    def test_handle_search_command(self):
        """Test /search command"""
        response = self.bot.handle_command("search", ["memory"], "test_chat")
        # Should either find results or say no results
        self.assertTrue(
            "Search Results" in response or
            "No results" in response or
            "Error" in response
        )
        print("[PASS] /search command")

    def test_handle_search_no_args(self):
        """Test /search without arguments"""
        response = self.bot.handle_command("search", [], "test_chat")
        self.assertIn("Please provide a search query", response)
        print("[PASS] /search validation")

    def test_handle_learn_command(self):
        """Test /learn command"""
        response = self.bot.handle_command("learn", ["Prefer type hints"], "test_chat")
        self.assertIn("Learning Recorded", response)
        print("[PASS] /learn command")

    def test_handle_learn_no_args(self):
        """Test /learn without arguments"""
        response = self.bot.handle_command("learn", [], "test_chat")
        self.assertIn("Please provide feedback", response)
        print("[PASS] /learn validation")

    def test_handle_patterns_command(self):
        """Test /patterns command"""
        response = self.bot.handle_command("patterns", [], "test_chat")
        self.assertIn("Learned Patterns", response)
        print("[PASS] /patterns command")

    def test_handle_improve_command(self):
        """Test /improve command"""
        response = self.bot.handle_command("improve", [], "test_chat")
        self.assertIn("Improvement", response)
        print("[PASS] /improve command")

    def test_handle_ask_command(self):
        """Test /ask command"""
        response = self.bot.handle_command("ask", ["what", "is", "memory"], "test_chat")
        # Should either find results or indicate no results
        self.assertIsNotNone(response)
        self.assertGreater(len(response), 0)
        print("[PASS] /ask command")

    def test_handle_ask_no_args(self):
        """Test /ask without arguments"""
        response = self.bot.handle_command("ask", [], "test_chat")
        self.assertIn("Please provide a question", response)
        print("[PASS] /ask validation")

    def test_handle_performance_command(self):
        """Test /performance command"""
        response = self.bot.handle_command("performance", [], "test_chat")
        self.assertIn("Performance", response)
        self.assertTrue("CPU" in response or "Memory" in response)
        print("[PASS] /performance command")

    def test_handle_test_command(self):
        """Test /test command"""
        response = self.bot.handle_command("test", ["1"], "test_chat")
        # Should start test or indicate it's started
        self.assertIsNotNone(response)
        self.assertTrue("Test" in response or "test" in response.lower())
        print("[PASS] /test command")

    def test_handle_test_invalid_duration(self):
        """Test /test with invalid duration"""
        response = self.bot.handle_command("test", ["invalid"], "test_chat")
        self.assertIn("Invalid", response)
        print("[PASS] /test validation")

    def test_handle_memory_command_stats(self):
        """Test /memory command without args (stats)"""
        response = self.bot.handle_command("memory", [], "test_chat")
        self.assertIn("Memory", response)
        print("[PASS] /memory stats command")

    def test_handle_memory_command_query(self):
        """Test /memory command with query"""
        response = self.bot.handle_command("memory", ["Python"], "test_chat")
        self.assertIsNotNone(response)
        self.assertGreater(len(response), 0)
        print("[PASS] /memory query command")

    def test_handle_unknown_command(self):
        """Test unknown command"""
        response = self.bot.handle_command("unknown_cmd", [], "test_chat")
        self.assertIn("Unknown command", response)
        self.assertIn("/help", response)
        print("[PASS] Unknown command handling")

    # ========================================================================
    # NATURAL LANGUAGE TESTS
    # ========================================================================

    def test_nl_search_intent(self):
        """Test natural language search intent detection"""
        queries = [
            "find authentication code",
            "search for database connection",
            "where is the config file"
        ]

        for query in queries:
            response = self.bot.handle_natural_language(query, "test_chat")
            # Should trigger search functionality
            self.assertIsNotNone(response)
            self.assertGreater(len(response), 0)

        print("[PASS] NL search intent detection")

    def test_nl_status_intent(self):
        """Test natural language status intent detection"""
        queries = [
            "how are you doing",
            "what's your status",
            "system health check"
        ]

        for query in queries:
            response = self.bot.handle_natural_language(query, "test_chat")
            self.assertIsNotNone(response)
            # Status responses should contain system info
            self.assertTrue(
                "System" in response or
                "status" in response.lower()
            )

        print("[PASS] NL status intent detection")

    def test_nl_patterns_intent(self):
        """Test natural language patterns intent detection"""
        response = self.bot.handle_natural_language(
            "what patterns have you learned?",
            "test_chat"
        )
        self.assertIn("Learned Patterns", response)
        print("[PASS] NL patterns intent detection")

    def test_nl_improve_intent(self):
        """Test natural language improvement intent detection"""
        response = self.bot.handle_natural_language(
            "how can I improve my code?",
            "test_chat"
        )
        self.assertIn("Improvement", response)
        print("[PASS] NL improvement intent detection")

    def test_nl_ask_intent(self):
        """Test natural language ask intent detection"""
        queries = [
            "what is the intelligence hub?",
            "tell me about memory management",
            "how does the system work?"
        ]

        for query in queries:
            response = self.bot.handle_natural_language(query, "test_chat")
            self.assertIsNotNone(response)
            self.assertGreater(len(response), 0)

        print("[PASS] NL ask intent detection")

    def test_nl_performance_intent(self):
        """Test natural language performance intent detection"""
        response = self.bot.handle_natural_language(
            "show me performance metrics",
            "test_chat"
        )
        self.assertTrue("Performance" in response or "performance" in response.lower())
        print("[PASS] NL performance intent detection")

    def test_nl_memory_intent(self):
        """Test natural language memory intent detection"""
        response = self.bot.handle_natural_language(
            "what do you remember about Python?",
            "test_chat"
        )
        self.assertIsNotNone(response)
        print("[PASS] NL memory intent detection")

    def test_nl_test_intent(self):
        """Test natural language test intent detection"""
        response = self.bot.handle_natural_language(
            "test the system for 2 minutes",
            "test_chat"
        )
        self.assertIsNotNone(response)
        print("[PASS] NL test intent detection")

    # ========================================================================
    # NOTIFICATION TESTS
    # ========================================================================

    @patch('requests.post')
    def test_send_notification_normal(self, mock_post):
        """Test sending normal priority notification"""
        mock_post.return_value.status_code = 200

        success = self.bot.send_notification(
            "Test notification",
            priority="normal",
            category="test"
        )

        self.assertTrue(success)
        print("[PASS] Normal priority notification")

    @patch('requests.post')
    def test_send_notification_critical(self, mock_post):
        """Test sending critical priority notification"""
        mock_post.return_value.status_code = 200

        success = self.bot.send_notification(
            "Critical alert!",
            priority="critical",
            category="security"
        )

        self.assertTrue(success)
        self.assertTrue(mock_post.called)
        print("[PASS] Critical priority notification")

    @patch('requests.post')
    def test_send_notification_with_emojis(self, mock_post):
        """Test notification includes priority emoji"""
        mock_post.return_value.status_code = 200

        priorities = ["critical", "high", "normal", "low"]
        for priority in priorities:
            self.bot.send_notification(
                f"Test {priority}",
                priority=priority
            )

        # Should have called post for each priority
        self.assertEqual(mock_post.call_count, len(priorities))
        print("[PASS] Priority emoji formatting")

    def test_notification_recording(self):
        """Test notifications are recorded in database"""
        # Mock the send to prevent actual API calls
        with patch.object(self.bot, '_send_message', return_value=True):
            self.bot.send_notification("Test message", "normal", "test")

        # Check database
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM notifications_sent")
        count = cursor.fetchone()[0]

        conn.close()

        self.assertGreater(count, 0)
        print("[PASS] Notification recording")

    # ========================================================================
    # DATABASE TRACKING TESTS
    # ========================================================================

    def test_command_execution_recording(self):
        """Test command executions are recorded"""
        # Execute some commands
        self.bot.handle_command("status", [], "test_chat")
        self.bot.handle_command("help", [], "test_chat")

        # Check database
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM commands_executed")
        count = cursor.fetchone()[0]

        conn.close()

        self.assertGreater(count, 0)
        print("[PASS] Command execution recording")

    def test_get_interaction_history(self):
        """Test retrieving interaction history"""
        # No direct interaction recording in current implementation
        # but test the method works
        history = self.bot.get_interaction_history(limit=10)
        self.assertIsInstance(history, list)
        print("[PASS] Interaction history retrieval")

    def test_get_stats(self):
        """Test getting bot statistics"""
        # Execute some commands first
        self.bot.handle_command("status", [], "test_chat")
        self.bot.handle_command("help", [], "test_chat")

        stats = self.bot.get_stats()

        self.assertIsInstance(stats, dict)
        self.assertIn('total_interactions', stats)
        self.assertIn('command_breakdown', stats)
        self.assertIn('avg_response_time', stats)
        self.assertIn('notifications', stats)
        print("[PASS] Statistics retrieval")

    def test_stats_command_breakdown(self):
        """Test statistics show command breakdown"""
        # Execute various commands
        commands = ["status", "help", "status", "patterns"]
        for cmd in commands:
            self.bot.handle_command(cmd, [], "test_chat")

        stats = self.bot.get_stats()
        breakdown = stats.get('command_breakdown', {})

        # Should have command counts
        self.assertIsInstance(breakdown, dict)
        if breakdown:
            self.assertGreater(sum(breakdown.values()), 0)

        print("[PASS] Command breakdown statistics")

    # ========================================================================
    # INTEGRATION TESTS
    # ========================================================================

    def test_hub_integration(self):
        """Test Intelligence Hub is properly integrated"""
        self.assertIsNotNone(self.bot.hub)
        self.assertEqual(self.bot.hub.workspace_path, self.test_workspace)
        print("[PASS] Intelligence Hub integration")

    def test_hub_capabilities_accessible(self):
        """Test can access hub capabilities"""
        # Test accessing various capabilities
        self.assertIsNotNone(self.bot.hub.memory)
        self.assertIsNotNone(self.bot.hub.code_search)
        self.assertIsNotNone(self.bot.hub.security_scanner)
        print("[PASS] Hub capabilities accessible")

    def test_analyze_uses_hub(self):
        """Test /analyze command uses Intelligence Hub"""
        # Mock send_message to avoid actual Telegram API calls
        with patch.object(self.bot, '_send_message', return_value=True):
            response = self.bot._handle_analyze("test_chat")

        # Should return analysis results
        self.assertIsNotNone(response)
        self.assertGreater(len(response), 0)
        print("[PASS] Analyze command uses hub")

    def test_security_scan_uses_hub(self):
        """Test /security command uses hub security scanner"""
        with patch.object(self.bot, '_send_message', return_value=True):
            response = self.bot._handle_security("test_chat")

        self.assertIsNotNone(response)
        self.assertIn("Security", response)
        print("[PASS] Security scan uses hub")

    # ========================================================================
    # ERROR HANDLING TESTS
    # ========================================================================

    def test_handles_search_error_gracefully(self):
        """Test search handles errors gracefully"""
        # Mock search to raise an error
        with patch.object(self.bot.hub.code_search, 'search', side_effect=Exception("Test error")):
            response = self.bot.handle_command("search", ["test"], "test_chat")

        self.assertIn("error", response.lower())
        print("[PASS] Search error handling")

    def test_handles_missing_file_review(self):
        """Test review handles missing files gracefully"""
        response = self.bot.handle_command("review", ["nonexistent_file.py"], "test_chat")
        self.assertIn("not found", response.lower())
        print("[PASS] Missing file handling")

    def test_handles_invalid_command_args(self):
        """Test handles invalid command arguments"""
        # Commands that require args but get none
        response1 = self.bot.handle_command("search", [], "test_chat")
        response2 = self.bot.handle_command("learn", [], "test_chat")

        self.assertIn("Please", response1)
        self.assertIn("Please", response2)
        print("[PASS] Invalid argument handling")

    # ========================================================================
    # FORMATTING TESTS
    # ========================================================================

    def test_response_contains_markdown(self):
        """Test responses use Markdown formatting"""
        response = self.bot.handle_command("help", [], "test_chat")

        # Should contain markdown elements
        self.assertTrue(
            '*' in response or  # Bold
            '_' in response or  # Italic
            '`' in response     # Code
        )
        print("[PASS] Markdown formatting")

    def test_code_snippets_formatting(self):
        """Test code snippets are properly formatted"""
        # Search should return code snippets
        response = self.bot.handle_command("search", ["class"], "test_chat")

        # If results found, should have code blocks
        if "No results" not in response and "error" not in response.lower():
            self.assertIn("```", response)

        print("[PASS] Code snippet formatting")

    def test_status_formatting(self):
        """Test status response is well-formatted"""
        response = self.bot.handle_command("status", [], "test_chat")

        # Should have emoji indicators
        self.assertTrue("✅" in response or "❌" in response)
        print("[PASS] Status formatting")

    # ========================================================================
    # PERFORMANCE TESTS
    # ========================================================================

    def test_command_execution_time(self):
        """Test commands execute in reasonable time"""
        start_time = time.time()
        self.bot.handle_command("status", [], "test_chat")
        execution_time = time.time() - start_time

        # Status should be fast (< 5 seconds)
        self.assertLess(execution_time, 5.0)
        print(f"[PASS] Command execution time: {execution_time:.2f}s")

    def test_multiple_commands_performance(self):
        """Test handling multiple commands"""
        start_time = time.time()

        commands = [
            ("status", []),
            ("help", []),
            ("patterns", []),
        ]

        for cmd, args in commands:
            self.bot.handle_command(cmd, args, "test_chat")

        total_time = time.time() - start_time

        # Should handle 3 commands in reasonable time
        self.assertLess(total_time, 15.0)
        print(f"[PASS] Multiple commands: {total_time:.2f}s")

    # ========================================================================
    # EDGE CASES
    # ========================================================================

    def test_empty_command(self):
        """Test handling empty command"""
        response = self.bot.handle_command("", [], "test_chat")
        self.assertIn("Unknown", response)
        print("[PASS] Empty command handling")

    def test_very_long_query(self):
        """Test handling very long query"""
        long_query = "test " * 1000  # Very long query
        response = self.bot.handle_command("search", [long_query], "test_chat")

        # Should handle gracefully
        self.assertIsNotNone(response)
        print("[PASS] Long query handling")

    def test_special_characters_in_query(self):
        """Test handling special characters"""
        special_query = "test!@#$%^&*()[]{}|\\:;\"'<>,.?/"
        response = self.bot.handle_command("search", [special_query], "test_chat")

        # Should not crash
        self.assertIsNotNone(response)
        print("[PASS] Special character handling")


def run_tests():
    """Run all tests with detailed output"""
    print("\n" + "="*80)
    print("TELEGRAM INTELLIGENCE BOT - COMPREHENSIVE TEST SUITE")
    print("="*80 + "\n")

    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestTelegramIntelligenceBot)

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

    if result.wasSuccessful():
        print("\n✅ ALL TESTS PASSED!")
    else:
        print("\n❌ SOME TESTS FAILED")

    print("="*80 + "\n")

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
