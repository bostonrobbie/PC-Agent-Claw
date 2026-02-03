"""
Telegram Intelligence Bot - Deep Integration System
Provides natural language access to all 25 Intelligence Hub capabilities via Telegram.

Features:
1. Command-based access to all major capabilities
2. Natural language understanding and routing
3. Real-time notifications with priority-based delivery
4. Rich formatted responses with code snippets
5. User interaction tracking and analytics
6. Progress indicators for long-running operations

Author: Intelligence Hub Team
Created: 2026-02-03
"""

import os
import sys
import json
import time
import sqlite3
import logging
import requests
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

# Add workspace to path for imports
WORKSPACE_PATH = Path(__file__).parent.parent
sys.path.append(str(WORKSPACE_PATH))

# Import Intelligence Hub
from intelligence_hub import IntelligenceHub
from notifications.smart_notifier import UrgencyLevel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CommandType(Enum):
    """Supported command types"""
    ANALYZE = "analyze"
    REVIEW = "review"
    SECURITY = "security"
    SEARCH = "search"
    ASK = "ask"
    LEARN = "learn"
    STATUS = "status"
    PATTERNS = "patterns"
    IMPROVE = "improve"
    TEST = "test"
    MEMORY = "memory"
    PERFORMANCE = "performance"
    HELP = "help"
    START = "start"


@dataclass
class UserInteraction:
    """User interaction tracking"""
    user_id: str
    chat_id: str
    command: str
    query: str
    timestamp: float
    response_time: float
    success: bool
    error_message: Optional[str] = None


class TelegramIntelligenceBot:
    """
    Telegram Intelligence Bot - Deep Integration with Intelligence Hub

    Provides natural language access to all 25 capabilities through Telegram.
    Tracks user interactions, learns preferences, and provides proactive assistance.
    """

    def __init__(self,
                 bot_token: Optional[str] = None,
                 chat_id: Optional[str] = None,
                 workspace_path: Optional[str] = None,
                 db_path: str = "telegram_bot.db"):
        """
        Initialize Telegram Intelligence Bot

        Args:
            bot_token: Telegram bot token (or read from config/env)
            chat_id: Default chat ID for notifications
            workspace_path: Workspace path for analysis
            db_path: SQLite database path for tracking
        """
        self.workspace_path = workspace_path or str(WORKSPACE_PATH)
        self.db_path = db_path

        # Load configuration
        self.bot_token = bot_token or self._load_bot_token()
        self.chat_id = chat_id or self._load_chat_id()

        if not self.bot_token:
            logger.warning("No bot token configured. Bot will not send messages.")

        # Initialize Intelligence Hub
        logger.info("[Telegram Bot] Initializing Intelligence Hub...")
        self.hub = IntelligenceHub(
            workspace_path=self.workspace_path,
            telegram_bot_token=self.bot_token
        )

        # Initialize database
        self._init_database()

        # Bot state
        self.running = False
        self.active_operations = {}  # Track long-running operations
        self.notification_queue = []

        # Natural language patterns
        self._init_nl_patterns()

        logger.info(f"[Telegram Bot] Initialized successfully")
        logger.info(f"[Telegram Bot] Workspace: {self.workspace_path}")
        logger.info(f"[Telegram Bot] Database: {self.db_path}")

    def _load_bot_token(self) -> Optional[str]:
        """Load bot token from config or environment"""
        # Try environment variable first
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if token:
            return token

        # Try config file
        config_file = WORKSPACE_PATH / "telegram_config.json"
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    return config.get('bot_token')
            except Exception as e:
                logger.error(f"Error loading config: {e}")

        return None

    def _load_chat_id(self) -> Optional[str]:
        """Load default chat ID from config"""
        config_file = WORKSPACE_PATH / "telegram_config.json"
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    return config.get('chat_id')
            except Exception as e:
                logger.error(f"Error loading config: {e}")

        return os.getenv("TELEGRAM_CHAT_ID", "5791597360")

    def _init_database(self):
        """Initialize SQLite database for tracking"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # User interactions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                chat_id TEXT NOT NULL,
                command TEXT NOT NULL,
                query TEXT,
                timestamp REAL NOT NULL,
                response_time REAL,
                success BOOLEAN,
                error_message TEXT
            )
        """)

        # Commands executed table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS commands_executed (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                command_type TEXT NOT NULL,
                args TEXT,
                execution_time REAL,
                result_size INTEGER,
                timestamp REAL NOT NULL
            )
        """)

        # User satisfaction indicators
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS satisfaction (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                interaction_id INTEGER,
                rating INTEGER,
                feedback TEXT,
                timestamp REAL NOT NULL,
                FOREIGN KEY (interaction_id) REFERENCES interactions(id)
            )
        """)

        # Notifications sent
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notifications_sent (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT NOT NULL,
                message TEXT NOT NULL,
                priority TEXT NOT NULL,
                category TEXT,
                timestamp REAL NOT NULL,
                delivered BOOLEAN DEFAULT 0
            )
        """)

        conn.commit()
        conn.close()

        logger.info("[Telegram Bot] Database initialized")

    def _init_nl_patterns(self):
        """Initialize natural language understanding patterns"""
        self.nl_patterns = {
            # Search patterns
            "find": CommandType.SEARCH,
            "search": CommandType.SEARCH,
            "look for": CommandType.SEARCH,
            "locate": CommandType.SEARCH,
            "where is": CommandType.SEARCH,

            # Ask patterns
            "ask": CommandType.ASK,
            "question": CommandType.ASK,
            "tell me": CommandType.ASK,
            "what is": CommandType.ASK,
            "how does": CommandType.ASK,

            # Review patterns
            "review": CommandType.REVIEW,
            "check": CommandType.REVIEW,
            "analyze": CommandType.ANALYZE,
            "examine": CommandType.REVIEW,

            # Security patterns
            "security": CommandType.SECURITY,
            "vulnerabilities": CommandType.SECURITY,
            "scan": CommandType.SECURITY,

            # Status patterns
            "status": CommandType.STATUS,
            "health": CommandType.STATUS,
            "how are": CommandType.STATUS,

            # Performance patterns
            "performance": CommandType.PERFORMANCE,
            "metrics": CommandType.PERFORMANCE,
            "resource": CommandType.PERFORMANCE,

            # Pattern discovery
            "patterns": CommandType.PATTERNS,
            "learned": CommandType.PATTERNS,

            # Improvement suggestions
            "improve": CommandType.IMPROVE,
            "suggestions": CommandType.IMPROVE,
            "optimize": CommandType.IMPROVE,

            # Memory patterns
            "memory": CommandType.MEMORY,
            "remember": CommandType.MEMORY,
            "recall": CommandType.MEMORY,

            # Test patterns
            "test": CommandType.TEST,
            "benchmark": CommandType.TEST,
        }

    def connect(self, chat_id: str) -> bool:
        """
        Connect to a specific chat

        Args:
            chat_id: Telegram chat ID to connect to

        Returns:
            True if connection successful
        """
        if not self.bot_token:
            logger.error("No bot token configured")
            return False

        try:
            # Test connection by sending a test message
            url = f"https://api.telegram.org/bot{self.bot_token}/getChat"
            response = requests.post(url, json={"chat_id": chat_id}, timeout=10)

            if response.status_code == 200:
                self.chat_id = chat_id
                logger.info(f"[Telegram Bot] Connected to chat {chat_id}")

                # Send welcome message
                self._send_message(
                    chat_id,
                    "🤖 *Intelligence Hub Bot Connected*\n\n"
                    "I provide natural language access to all 25 AI capabilities.\n\n"
                    "Type /help to see available commands or just ask me naturally!",
                    parse_mode="Markdown"
                )

                return True
            else:
                logger.error(f"Failed to connect: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False

    def handle_command(self, command: str, args: List[str], chat_id: str = None) -> str:
        """
        Handle a command-based request

        Args:
            command: Command name (without /)
            args: List of command arguments
            chat_id: Chat ID for response

        Returns:
            Response message
        """
        chat_id = chat_id or self.chat_id
        start_time = time.time()

        try:
            # Map command to handler
            command_upper = command.upper()

            if command_upper == "START":
                return self._handle_start()
            elif command_upper == "HELP":
                return self._handle_help()
            elif command_upper == "ANALYZE":
                return self._handle_analyze(chat_id)
            elif command_upper == "REVIEW":
                return self._handle_review(args, chat_id)
            elif command_upper == "SECURITY":
                return self._handle_security(chat_id)
            elif command_upper == "SEARCH":
                return self._handle_search(args)
            elif command_upper == "ASK":
                return self._handle_ask(args)
            elif command_upper == "LEARN":
                return self._handle_learn(args)
            elif command_upper == "STATUS":
                return self._handle_status()
            elif command_upper == "PATTERNS":
                return self._handle_patterns()
            elif command_upper == "IMPROVE":
                return self._handle_improve()
            elif command_upper == "PERFORMANCE":
                return self._handle_performance()
            elif command_upper == "TEST":
                return self._handle_test(args, chat_id)
            elif command_upper == "MEMORY":
                return self._handle_memory(args)
            else:
                return f"❌ Unknown command: {command}\n\nType /help for available commands."

        except Exception as e:
            logger.error(f"Command error: {e}")
            return f"❌ Error executing command: {str(e)}"

        finally:
            # Track command execution
            execution_time = time.time() - start_time
            self._record_command_execution(command, args, execution_time)

    def handle_natural_language(self, message: str, chat_id: str = None) -> str:
        """
        Handle a natural language request

        Args:
            message: Natural language message
            chat_id: Chat ID for response

        Returns:
            Response message
        """
        chat_id = chat_id or self.chat_id
        message_lower = message.lower()

        # Detect intent from patterns
        detected_command = None
        for pattern, command_type in self.nl_patterns.items():
            if pattern in message_lower:
                detected_command = command_type
                break

        if not detected_command:
            # Default to search if no clear intent
            detected_command = CommandType.SEARCH

        # Route to appropriate handler
        if detected_command == CommandType.SEARCH:
            return self._handle_search([message])
        elif detected_command == CommandType.ASK:
            return self._handle_ask([message])
        elif detected_command == CommandType.REVIEW:
            # Extract file reference if any
            words = message.split()
            file_refs = [w for w in words if '.' in w or '/' in w or '\\' in w]
            return self._handle_review(file_refs if file_refs else [message], chat_id)
        elif detected_command == CommandType.ANALYZE:
            return self._handle_analyze(chat_id)
        elif detected_command == CommandType.SECURITY:
            return self._handle_security(chat_id)
        elif detected_command == CommandType.STATUS:
            return self._handle_status()
        elif detected_command == CommandType.PERFORMANCE:
            return self._handle_performance()
        elif detected_command == CommandType.PATTERNS:
            return self._handle_patterns()
        elif detected_command == CommandType.IMPROVE:
            return self._handle_improve()
        elif detected_command == CommandType.MEMORY:
            return self._handle_memory([message])
        elif detected_command == CommandType.TEST:
            # Extract duration if mentioned
            words = message.split()
            duration_args = [w for w in words if w.isdigit()]
            return self._handle_test(duration_args if duration_args else ["5"], chat_id)
        else:
            return self._handle_search([message])

    def _handle_start(self) -> str:
        """Handle /start command"""
        return """🤖 *Welcome to Intelligence Hub Bot!*

I provide natural language access to all 25 AI capabilities.

*Commands:*
/analyze - Full workspace analysis (all 25 capabilities)
/review [file] - Deep code review with suggestions
/security - Security scan and report issues
/performance - Show current performance metrics
/search [query] - Semantic code search
/ask [question] - Ask about the codebase
/learn [feedback] - Record learning/feedback
/status - System status (all 25 capabilities)
/patterns - Show discovered patterns
/improve - Get self-improvement suggestions
/test [duration] - Start real-world test (minutes)
/memory [query] - Query relationship memory
/help - Show this help

*Natural Language:*
Just ask me naturally!
- "find authentication code"
- "review my latest changes"
- "check for security issues"
- "what patterns have you learned?"
- "show me performance metrics"
- "test the system for 5 minutes"

Let's build something amazing! 🚀"""

    def _handle_help(self) -> str:
        """Handle /help command"""
        return self._handle_start()

    def _handle_analyze(self, chat_id: str) -> str:
        """Handle /analyze command - full workspace analysis"""
        # Send progress indicator
        self._send_message(chat_id, "🔍 *Analyzing workspace...*\n\nThis may take a minute.", parse_mode="Markdown")

        start_time = time.time()

        # Start hub if not running
        if not self.hub.running:
            self.hub.start()

        # Run analysis
        analysis = self.hub.analyze_workspace()

        execution_time = time.time() - start_time

        # Format response
        response = f"✅ *Workspace Analysis Complete*\n\n"
        response += f"⏱️ Completed in {execution_time:.1f}s\n\n"

        # Code indexing
        if 'code_indexed' in analysis:
            indexed = analysis['code_indexed']
            if 'error' not in indexed:
                response += f"📚 *Code Indexed:*\n"
                response += f"- Files: {indexed.get('files_indexed', 0)}\n"
                response += f"- Chunks: {indexed.get('chunks_indexed', 0)}\n\n"

        # Security
        if 'security' in analysis:
            security = analysis['security']
            if 'error' not in security:
                response += f"🔒 *Security Scan:*\n"
                response += f"- Files scanned: {security.get('files_scanned', 0)}\n"
                response += f"- Vulnerabilities: {security.get('vulnerabilities_found', 0)}\n"
                if security.get('critical', 0) > 0:
                    response += f"- ⚠️ Critical: {security['critical']}\n"
                response += "\n"

        # Resources
        if 'resources' in analysis:
            res = analysis['resources']
            if 'error' not in res:
                response += f"💻 *System Resources:*\n"
                response += f"- CPU: {res.get('cpu_percent', 0):.1f}%\n"
                response += f"- Memory: {res.get('memory_percent', 0):.1f}%\n\n"

        # Insights
        insights = analysis.get('insights', [])
        if insights:
            response += f"💡 *Key Insights ({len(insights)}):*\n"
            for insight in insights[:5]:  # Top 5
                level_emoji = {"info": "ℹ️", "warning": "⚠️", "error": "❌"}.get(insight['level'], "•")
                response += f"{level_emoji} {insight['title']}: {insight['message']}\n"

        return response

    def _handle_review(self, args: List[str], chat_id: str) -> str:
        """Handle /review command - code review"""
        if not args:
            return "❌ Please specify a file to review.\n\nUsage: /review <file_path>"

        file_path = " ".join(args)

        # Send progress indicator
        self._send_message(chat_id, f"🔍 *Reviewing: {file_path}*\n\nAnalyzing...", parse_mode="Markdown")

        # Check if file exists
        full_path = Path(self.workspace_path) / file_path
        if not full_path.exists():
            return f"❌ File not found: {file_path}"

        try:
            # Read file
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                code = f.read()

            # Use Intelligence Hub to assist with review
            assistance = self.hub.assist_with_code(
                f"Review code in {file_path}",
                code
            )

            response = f"✅ *Code Review: {file_path}*\n\n"

            # Style check
            if 'style_check' in assistance and 'error' not in assistance['style_check']:
                score = assistance['style_check'].get('score', 0)
                response += f"📊 *Style Score:* {score:.1f}/100\n\n"

            # Security scan
            if 'security_scan' in assistance and 'error' not in assistance['security_scan']:
                vulns = assistance['security_scan'].get('vulnerabilities', [])
                response += f"🔒 *Security:* {len(vulns)} issue(s)\n"

                if vulns:
                    response += "\n*Vulnerabilities:*\n"
                    for v in vulns[:3]:  # Top 3
                        response += f"- {v.get('type', 'Unknown')}: {v.get('description', '')}\n"
                response += "\n"

            # Similar code
            if 'similar_code' in assistance and assistance['similar_code']:
                response += f"🔍 *Similar Code:* {len(assistance['similar_code'])} matches found\n\n"

            # Capabilities used
            caps = assistance.get('capabilities_used', [])
            if caps:
                response += f"🤖 *Analysis using:* {', '.join(caps)}"

            return response

        except Exception as e:
            return f"❌ Error reviewing file: {str(e)}"

    def _handle_security(self, chat_id: str) -> str:
        """Handle /security command - security scan"""
        self._send_message(chat_id, "🔒 *Security Scan Starting...*\n\nScanning workspace...", parse_mode="Markdown")

        try:
            # Find Python files
            python_files = list(Path(self.workspace_path).rglob("*.py"))[:20]  # Sample

            all_vulnerabilities = []
            files_scanned = 0

            for file in python_files:
                try:
                    with open(file, 'r', encoding='utf-8', errors='ignore') as f:
                        code = f.read()

                    scan = self.hub.security_scanner.scan_code(code, str(file))
                    if scan['vulnerabilities']:
                        all_vulnerabilities.extend([
                            {**v, 'file': str(file.relative_to(self.workspace_path))}
                            for v in scan['vulnerabilities']
                        ])
                    files_scanned += 1
                except:
                    continue

            response = f"✅ *Security Scan Complete*\n\n"
            response += f"📁 Files scanned: {files_scanned}\n"
            response += f"⚠️ Vulnerabilities found: {len(all_vulnerabilities)}\n\n"

            if all_vulnerabilities:
                # Group by severity
                critical = [v for v in all_vulnerabilities if v.get('severity') == 'critical']
                high = [v for v in all_vulnerabilities if v.get('severity') == 'high']
                medium = [v for v in all_vulnerabilities if v.get('severity') == 'medium']

                if critical:
                    response += f"🔴 *Critical:* {len(critical)}\n"
                if high:
                    response += f"🟠 *High:* {len(high)}\n"
                if medium:
                    response += f"🟡 *Medium:* {len(medium)}\n"

                response += "\n*Top Issues:*\n"
                for v in all_vulnerabilities[:5]:
                    response += f"- {v.get('type', 'Unknown')} in {v.get('file', 'unknown')}\n"
            else:
                response += "✅ No vulnerabilities detected!"

            return response

        except Exception as e:
            return f"❌ Security scan error: {str(e)}"

    def _handle_search(self, args: List[str]) -> str:
        """Handle /search command - semantic code search"""
        if not args:
            return "❌ Please provide a search query.\n\nUsage: /search <query>"

        query = " ".join(args)

        try:
            # Use semantic search
            results = self.hub.code_search.search(query, limit=5)

            if not results:
                return f"🔍 No results found for: *{query}*"

            response = f"🔍 *Search Results for:* {query}\n\n"
            response += f"Found {len(results)} matches:\n\n"

            for i, result in enumerate(results, 1):
                file_path = result.get('file_path', 'Unknown')
                chunk = result.get('chunk_text', '')
                similarity = result.get('similarity', 0)

                response += f"*{i}. {file_path}*\n"
                response += f"Similarity: {similarity:.1%}\n"

                # Show snippet
                snippet = chunk[:200] + "..." if len(chunk) > 200 else chunk
                response += f"```\n{snippet}\n```\n\n"

            return response

        except Exception as e:
            return f"❌ Search error: {str(e)}"

    def _handle_learn(self, args: List[str]) -> str:
        """Handle /learn command - record learning"""
        if not args:
            return "❌ Please provide feedback to learn from.\n\nUsage: /learn <feedback>"

        feedback = " ".join(args)

        try:
            # Record in memory
            self.hub.memory.record_learning(
                learning=feedback,
                category='user_feedback'
            )

            return f"✅ *Learning Recorded*\n\nI've learned: {feedback}\n\nThis will influence my future behavior!"

        except Exception as e:
            return f"❌ Learning error: {str(e)}"

    def _handle_status(self) -> str:
        """Handle /status command - system status"""
        try:
            health = self.hub.get_health_status()

            response = f"🤖 *System Status*\n\n"
            response += f"Session: {health['session_id']}\n"
            response += f"Running: {'✅' if health['running'] else '❌'}\n\n"

            response += "*Capabilities Health:*\n"

            for cap_name, cap_status in health.get('capabilities', {}).items():
                status = cap_status.get('status', 'unknown')
                emoji = "✅" if status == "healthy" else "❌"
                response += f"{emoji} {cap_name}: {status}\n"

                # Show key metrics
                if status == "healthy":
                    for key, value in cap_status.items():
                        if key != 'status':
                            response += f"  - {key}: {value}\n"

            return response

        except Exception as e:
            return f"❌ Status check error: {str(e)}"

    def _handle_patterns(self) -> str:
        """Handle /patterns command - show discovered patterns"""
        try:
            # Get review stats
            review_stats = self.hub.code_reviewer.get_review_stats()
            style_guide = self.hub.code_reviewer.get_style_guide('python')

            # Get mistake stats - use correct method name
            mistake_stats = self.hub.mistake_learner.get_learning_stats()

            response = f"🧠 *Learned Patterns*\n\n"

            # Code review patterns
            response += f"📝 *Code Review Learning:*\n"
            response += f"- Total reviews: {review_stats['total_reviews']}\n"
            response += f"- Approval rate: {review_stats['approval_rate']:.1%}\n"
            response += f"- Style preferences: {len(style_guide)}\n\n"

            if style_guide:
                response += "*Top Style Patterns:*\n"
                for pattern, count in list(style_guide.items())[:5]:
                    response += f"- {pattern}: {count} occurrences\n"
                response += "\n"

            # Mistake learning
            response += f"🔧 *Mistake Learning:*\n"
            response += f"- Total mistakes: {mistake_stats.get('total_mistakes', 0)}\n"
            response += f"- Corrections: {mistake_stats.get('total_corrections', 0)}\n"
            response += f"- Success rate: {mistake_stats.get('correction_success_rate', 0):.1%}\n"

            return response

        except Exception as e:
            return f"❌ Pattern retrieval error: {str(e)}"

    def _handle_improve(self) -> str:
        """Handle /improve command - improvement suggestions"""
        try:
            # Get workspace analysis for suggestions
            analysis = self.hub.analyze_workspace()

            suggestions = []

            # Check security issues
            if 'security' in analysis:
                sec = analysis['security']
                if sec.get('vulnerabilities_found', 0) > 0:
                    suggestions.append(f"🔒 Fix {sec['vulnerabilities_found']} security vulnerabilities")

            # Check resource usage
            if 'resources' in analysis:
                res = analysis['resources']
                if res.get('cpu_percent', 0) > 80:
                    suggestions.append(f"💻 Optimize CPU usage (currently {res['cpu_percent']:.1f}%)")
                if res.get('memory_percent', 0) > 80:
                    suggestions.append(f"🧠 Optimize memory usage (currently {res['memory_percent']:.1f}%)")

            # Check code style
            if 'code_style' in analysis:
                style = analysis['code_style']
                if style.get('approval_rate', 1.0) < 0.8:
                    suggestions.append("📝 Review code style consistency")

            response = f"💡 *Improvement Suggestions*\n\n"

            if suggestions:
                response += "Based on my analysis, I suggest:\n\n"
                for i, suggestion in enumerate(suggestions, 1):
                    response += f"{i}. {suggestion}\n"
            else:
                response += "✅ Everything looks good!\n\nNo immediate improvements needed."

            return response

        except Exception as e:
            return f"❌ Improvement analysis error: {str(e)}"

    def _handle_ask(self, args: List[str]) -> str:
        """Handle /ask command - ask questions about the codebase"""
        if not args:
            return "❌ Please provide a question.\n\nUsage: /ask <question>"

        question = " ".join(args)

        try:
            # Use semantic search to find relevant code
            results = self.hub.code_search.search(question, limit=3)

            if not results:
                # Try to recall from memory
                memory_recall = self.hub.memory.recall_everything_about("PC-Agent-Claw")
                response = f"🔍 *Question:* {question}\n\n"
                response += "I couldn't find specific code matching your question, but here's what I know:\n\n"

                if memory_recall.get('learnings'):
                    response += f"📚 *Knowledge:*\n"
                    for learning in memory_recall['learnings'][:3]:
                        response += f"- {learning.get('learning', '')}\n"
                else:
                    response += "No relevant information found. Try indexing the project with /analyze first."

                return response

            response = f"🔍 *Question:* {question}\n\n"
            response += f"Found {len(results)} relevant code sections:\n\n"

            for i, result in enumerate(results, 1):
                file_path = result.get('file_path', 'Unknown')
                chunk = result.get('chunk_text', '')
                similarity = result.get('similarity', 0)

                response += f"*{i}. {file_path}*\n"
                response += f"Relevance: {similarity:.1%}\n"

                # Show snippet
                snippet = chunk[:250] + "..." if len(chunk) > 250 else chunk
                response += f"```\n{snippet}\n```\n\n"

            return response

        except Exception as e:
            return f"❌ Question processing error: {str(e)}"

    def _handle_performance(self) -> str:
        """Handle /performance command - show performance metrics"""
        try:
            # Get resource monitoring data
            resources = self.hub.resource_monitor.get_current_usage()

            response = f"📊 *Performance Metrics*\n\n"

            # System resources
            response += f"💻 *System Resources:*\n"
            response += f"- CPU: {resources.get('cpu_percent', 0):.1f}%\n"
            response += f"- Memory: {resources.get('memory_percent', 0):.1f}%\n"
            response += f"- Available RAM: {resources.get('memory_available_mb', 0):.0f} MB\n\n"

            # Get search stats if available
            try:
                search_stats = self.hub.code_search.get_stats()
                response += f"🔍 *Semantic Search:*\n"
                response += f"- Projects indexed: {search_stats.get('total_projects', 0)}\n"
                response += f"- Code chunks: {search_stats.get('total_chunks', 0)}\n"
                response += f"- Files indexed: {search_stats.get('total_files', 0)}\n\n"
            except:
                pass

            # Get memory stats
            try:
                memory_stats = self.hub.memory.get_stats()
                response += f"🧠 *Memory System:*\n"
                response += f"- Preferences: {memory_stats.get('total_preferences', 0)}\n"
                response += f"- Decisions: {memory_stats.get('total_decisions', 0)}\n"
                response += f"- Learnings: {memory_stats.get('total_learnings', 0)}\n\n"
            except:
                pass

            # Get background task stats
            try:
                task_stats = self.hub.background_tasks.get_stats()
                response += f"⚙️ *Background Tasks:*\n"
                response += f"- Workers active: {task_stats.get('workers_active', 0)}\n"
                response += f"- Tasks completed: {task_stats.get('tasks_completed', 0)}\n"
                response += f"- Tasks pending: {task_stats.get('tasks_pending', 0)}\n"
            except:
                pass

            return response

        except Exception as e:
            return f"❌ Performance metrics error: {str(e)}"

    def _handle_test(self, args: List[str], chat_id: str) -> str:
        """Handle /test command - start real-world testing"""
        if not args:
            duration = 5  # Default 5 minutes
        else:
            try:
                duration = int(args[0])
            except ValueError:
                return "❌ Invalid duration. Please provide a number in minutes.\n\nUsage: /test <minutes>"

        if duration < 1 or duration > 60:
            return "❌ Duration must be between 1 and 60 minutes."

        # Send starting message
        self._send_message(
            chat_id,
            f"🧪 *Real-World Test Starting*\n\n"
            f"Duration: {duration} minute(s)\n"
            f"Testing all 25 capabilities...\n\n"
            f"I'll notify you when complete!",
            parse_mode="Markdown"
        )

        try:
            # Import tester
            sys.path.append(str(Path(self.workspace_path)))
            from autonomous.realworld_tester import RealWorldTester

            # Start test in background
            def run_test():
                try:
                    tester = RealWorldTester(self.workspace_path)
                    session_id = tester.start_session(duration_minutes=duration)

                    # Wait for test to complete
                    time.sleep(duration * 60)

                    # Get results
                    report = tester.generate_report(session_id)

                    # Send completion notification
                    response = f"✅ *Test Complete!*\n\n"
                    response += f"Duration: {duration} minutes\n"
                    response += f"Activities: {report.get('total_activities', 0)}\n"
                    response += f"Success rate: {report.get('success_rate', 0):.1%}\n"
                    response += f"Avg response time: {report.get('avg_response_time', 0):.0f}ms\n\n"

                    if report.get('issues'):
                        response += f"⚠️ Issues found: {len(report['issues'])}\n"
                        for issue in report['issues'][:3]:
                            response += f"- {issue.get('description', '')}\n"

                    self._send_message(chat_id, response, parse_mode="Markdown")

                except Exception as e:
                    self._send_message(
                        chat_id,
                        f"❌ Test error: {str(e)}",
                        parse_mode="Markdown"
                    )

            # Start test thread
            test_thread = threading.Thread(target=run_test, daemon=True)
            test_thread.start()

            return f"✅ Test started! Duration: {duration} minute(s)\n\nI'll notify you when it's done."

        except Exception as e:
            return f"❌ Test initialization error: {str(e)}"

    def _handle_memory(self, args: List[str]) -> str:
        """Handle /memory command - query relationship memory"""
        if not args:
            # Show memory stats
            try:
                memory_stats = self.hub.memory.get_stats()

                response = f"🧠 *Memory System*\n\n"
                response += f"📝 *Stored Information:*\n"
                response += f"- User preferences: {memory_stats.get('total_preferences', 0)}\n"
                response += f"- Decisions recorded: {memory_stats.get('total_decisions', 0)}\n"
                response += f"- Learnings captured: {memory_stats.get('total_learnings', 0)}\n\n"

                response += "💡 *Usage:*\n"
                response += "Use /memory <query> to search memory\n"
                response += "Example: /memory Python preferences"

                return response

            except Exception as e:
                return f"❌ Memory error: {str(e)}"

        # Query memory
        query = " ".join(args)

        try:
            # Recall everything about the query
            memory_recall = self.hub.memory.recall_everything_about(query)

            response = f"🧠 *Memory Recall: {query}*\n\n"

            # Show preferences
            if memory_recall.get('preferences'):
                response += f"📌 *Preferences ({len(memory_recall['preferences'])}):*\n"
                for pref in memory_recall['preferences'][:5]:
                    response += f"- {pref.get('preference', '')}\n"
                response += "\n"

            # Show decisions
            if memory_recall.get('decisions'):
                response += f"🎯 *Decisions ({len(memory_recall['decisions'])}):*\n"
                for decision in memory_recall['decisions'][:5]:
                    response += f"- {decision.get('decision', '')}\n"
                response += "\n"

            # Show learnings
            if memory_recall.get('learnings'):
                response += f"📚 *Learnings ({len(memory_recall['learnings'])}):*\n"
                for learning in memory_recall['learnings'][:5]:
                    response += f"- {learning.get('learning', '')}\n"

            if not any([memory_recall.get('preferences'),
                       memory_recall.get('decisions'),
                       memory_recall.get('learnings')]):
                response += "No memory found for this query.\n"
                response += "I'll remember things as we interact!"

            return response

        except Exception as e:
            return f"❌ Memory query error: {str(e)}"

    def send_notification(self, message: str, priority: str = "normal",
                         category: str = "general", chat_id: str = None) -> bool:
        """
        Send a notification to user

        Args:
            message: Notification message
            priority: Priority level (critical, high, normal, low)
            category: Notification category
            chat_id: Chat ID to send to

        Returns:
            True if sent successfully
        """
        chat_id = chat_id or self.chat_id

        # Map priority to emoji
        priority_emoji = {
            "critical": "🚨",
            "high": "⚠️",
            "normal": "ℹ️",
            "low": "💬"
        }

        emoji = priority_emoji.get(priority.lower(), "💬")
        formatted_message = f"{emoji} *{priority.upper()}*\n\n{message}"

        success = self._send_message(chat_id, formatted_message, parse_mode="Markdown")

        # Record notification
        self._record_notification(chat_id, message, priority, category, success)

        return success

    def _send_message(self, chat_id: str, text: str, parse_mode: str = None) -> bool:
        """Send a message via Telegram API"""
        if not self.bot_token:
            logger.warning(f"No bot token. Would send: {text[:100]}...")
            return False

        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": text
            }

            if parse_mode:
                payload["parse_mode"] = parse_mode

            response = requests.post(url, json=payload, timeout=10)

            if response.status_code == 200:
                logger.info(f"Message sent to {chat_id}")
                return True
            else:
                logger.error(f"Telegram API error: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Send message error: {e}")
            return False

    def get_interaction_history(self, limit: int = 50) -> List[Dict]:
        """
        Get user interaction history

        Args:
            limit: Maximum number of interactions to return

        Returns:
            List of interaction records
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT user_id, chat_id, command, query, timestamp,
                   response_time, success, error_message
            FROM interactions
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))

        interactions = []
        for row in cursor.fetchall():
            interactions.append({
                "user_id": row[0],
                "chat_id": row[1],
                "command": row[2],
                "query": row[3],
                "timestamp": row[4],
                "response_time": row[5],
                "success": bool(row[6]),
                "error_message": row[7]
            })

        conn.close()
        return interactions

    def _record_command_execution(self, command: str, args: List[str],
                                   execution_time: float):
        """Record command execution for analytics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO commands_executed
                (command_type, args, execution_time, result_size, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (command, json.dumps(args), execution_time, 0, time.time()))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Error recording command: {e}")

    def _record_notification(self, chat_id: str, message: str,
                            priority: str, category: str, delivered: bool):
        """Record notification for tracking"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO notifications_sent
                (chat_id, message, priority, category, timestamp, delivered)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (chat_id, message, priority, category, time.time(), delivered))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Error recording notification: {e}")

    def get_stats(self) -> Dict:
        """Get bot usage statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Total interactions
            cursor.execute("SELECT COUNT(*) FROM interactions")
            total_interactions = cursor.fetchone()[0]

            # Command breakdown
            cursor.execute("""
                SELECT command_type, COUNT(*)
                FROM commands_executed
                GROUP BY command_type
                ORDER BY COUNT(*) DESC
            """)
            command_stats = dict(cursor.fetchall())

            # Average response time
            cursor.execute("""
                SELECT AVG(execution_time) FROM commands_executed
            """)
            avg_response_time = cursor.fetchone()[0] or 0

            # Notifications sent
            cursor.execute("""
                SELECT COUNT(*), SUM(CASE WHEN delivered = 1 THEN 1 ELSE 0 END)
                FROM notifications_sent
            """)
            notif_row = cursor.fetchone()
            total_notifications = notif_row[0] or 0
            delivered_notifications = notif_row[1] or 0

            conn.close()

            return {
                "total_interactions": total_interactions,
                "command_breakdown": command_stats,
                "avg_response_time": round(avg_response_time, 2),
                "notifications": {
                    "total": total_notifications,
                    "delivered": delivered_notifications,
                    "delivery_rate": delivered_notifications / total_notifications if total_notifications > 0 else 0
                }
            }

        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}


# ============================================================================
# DEMONSTRATION AND TESTING
# ============================================================================

def demo_bot():
    """Demonstrate the Telegram Intelligence Bot"""
    print("="*80)
    print("TELEGRAM INTELLIGENCE BOT - DEMONSTRATION")
    print("="*80)
    print()

    # Initialize bot
    bot = TelegramIntelligenceBot()

    print("[Demo] Bot initialized successfully")
    print(f"[Demo] Workspace: {bot.workspace_path}")
    print(f"[Demo] Database: {bot.db_path}")
    print()

    # Test commands
    print("="*80)
    print("TESTING COMMANDS")
    print("="*80)
    print()

    # Test /status
    print("[Test] /status command")
    status_response = bot.handle_command("status", [], "demo_chat")
    print(status_response)
    print()

    # Test /search
    print("[Test] /search command")
    search_response = bot.handle_command("search", ["memory system"], "demo_chat")
    print(search_response[:500] + "..." if len(search_response) > 500 else search_response)
    print()

    # Test natural language
    print("="*80)
    print("TESTING NATURAL LANGUAGE")
    print("="*80)
    print()

    nl_queries = [
        "find authentication code",
        "check system status",
        "what patterns have you learned?"
    ]

    for query in nl_queries:
        print(f"[NL Test] '{query}'")
        response = bot.handle_natural_language(query, "demo_chat")
        print(response[:300] + "..." if len(response) > 300 else response)
        print()

    # Test stats
    print("="*80)
    print("BOT STATISTICS")
    print("="*80)
    print()

    stats = bot.get_stats()
    print(f"Total interactions: {stats.get('total_interactions', 0)}")
    print(f"Average response time: {stats.get('avg_response_time', 0):.2f}s")
    print(f"Command breakdown: {stats.get('command_breakdown', {})}")
    print()

    print("="*80)
    print("DEMONSTRATION COMPLETE")
    print("="*80)


if __name__ == "__main__":
    demo_bot()
