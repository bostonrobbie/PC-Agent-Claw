#!/usr/bin/env python3
"""
Conversational Intelligence & Context Tracking
Deep understanding of ongoing conversations
"""
import sys
from pathlib import Path
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import deque

sys.path.append(str(Path(__file__).parent.parent))


class ConversationManager:
    """
    Manage deep conversational context

    Features:
    - Track conversation threads
    - Remember what was discussed when
    - Understand implicit references
    - Maintain conversation state
    - Suggest relevant past discussions
    - Context-aware responses
    """

    def __init__(self, db_path: str = None, context_window: int = 10):
        workspace = Path(__file__).parent.parent
        if db_path is None:
            db_path = str(workspace / "memory.db")

        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

        self.context_window = context_window
        self.current_thread_id = None
        self.conversation_state = {}
        self.recent_context = deque(maxlen=context_window)

    def _init_db(self):
        """Initialize database schema"""
        cursor = self.conn.cursor()

        # Conversation threads
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversation_threads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_name TEXT,
                topic TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_message_at TIMESTAMP,
                message_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active'
            )
        ''')

        # Messages in threads
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS thread_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                intent TEXT,
                entities TEXT,
                sentiment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (thread_id) REFERENCES conversation_threads(id)
            )
        ''')

        # Conversation entities (topics, people, concepts mentioned)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversation_entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type TEXT NOT NULL,
                entity_value TEXT NOT NULL,
                first_mentioned TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_mentioned TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                mention_count INTEGER DEFAULT 1,
                context TEXT
            )
        ''')

        # References (pronoun resolution, implicit references)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversation_references (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id INTEGER NOT NULL,
                reference_text TEXT NOT NULL,
                refers_to TEXT NOT NULL,
                confidence REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (thread_id) REFERENCES conversation_threads(id)
            )
        ''')

        # Conversation state (tracking what's being discussed)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversation_state (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id INTEGER NOT NULL,
                state_key TEXT NOT NULL,
                state_value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (thread_id) REFERENCES conversation_threads(id)
            )
        ''')

        self.conn.commit()

    # === THREAD MANAGEMENT ===

    def start_thread(self, topic: str = None) -> int:
        """Start new conversation thread"""
        cursor = self.conn.cursor()

        cursor.execute('''
            INSERT INTO conversation_threads (thread_name, topic, status)
            VALUES (?, ?, 'active')
        ''', (f"Thread {datetime.now().strftime('%Y%m%d_%H%M%S')}", topic))

        self.conn.commit()
        self.current_thread_id = cursor.lastrowid

        return self.current_thread_id

    def get_or_create_thread(self) -> int:
        """Get current thread or create new one"""
        if self.current_thread_id:
            return self.current_thread_id

        return self.start_thread()

    def close_thread(self, thread_id: int = None):
        """Close conversation thread"""
        if thread_id is None:
            thread_id = self.current_thread_id

        if thread_id:
            cursor = self.conn.cursor()
            cursor.execute('''
                UPDATE conversation_threads
                SET status = 'closed'
                WHERE id = ?
            ''', (thread_id,))
            self.conn.commit()

            if thread_id == self.current_thread_id:
                self.current_thread_id = None

    # === MESSAGE TRACKING ===

    def add_message(self, role: str, content: str,
                   intent: str = None, entities: List[str] = None,
                   sentiment: str = 'neutral', thread_id: int = None) -> int:
        """
        Add message to conversation

        Args:
            role: 'user' or 'assistant'
            content: Message content
            intent: Detected intent
            entities: Entities mentioned
            sentiment: Message sentiment
            thread_id: Thread ID (or current)

        Returns:
            Message ID
        """
        if thread_id is None:
            thread_id = self.get_or_create_thread()

        cursor = self.conn.cursor()

        # Add message
        cursor.execute('''
            INSERT INTO thread_messages
            (thread_id, role, content, intent, entities, sentiment)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (thread_id, role, content, intent,
              json.dumps(entities) if entities else None, sentiment))

        message_id = cursor.lastrowid

        # Update thread
        cursor.execute('''
            UPDATE conversation_threads
            SET last_message_at = CURRENT_TIMESTAMP,
                message_count = message_count + 1
            WHERE id = ?
        ''', (thread_id,))

        self.conn.commit()

        # Track entities
        if entities:
            for entity in entities:
                self._track_entity('mention', entity, content)

        # Add to recent context
        self.recent_context.append({
            'role': role,
            'content': content,
            'thread_id': thread_id,
            'timestamp': datetime.now()
        })

        return message_id

    def _track_entity(self, entity_type: str, entity_value: str, context: str):
        """Track entity mentions"""
        cursor = self.conn.cursor()

        cursor.execute('''
            SELECT id FROM conversation_entities
            WHERE entity_type = ? AND entity_value = ?
        ''', (entity_type, entity_value))

        result = cursor.fetchone()

        if result:
            # Update existing
            cursor.execute('''
                UPDATE conversation_entities
                SET last_mentioned = CURRENT_TIMESTAMP,
                    mention_count = mention_count + 1,
                    context = ?
                WHERE id = ?
            ''', (context[:200], result['id']))
        else:
            # Insert new
            cursor.execute('''
                INSERT INTO conversation_entities
                (entity_type, entity_value, context)
                VALUES (?, ?, ?)
            ''', (entity_type, entity_value, context[:200]))

        self.conn.commit()

    # === CONTEXT UNDERSTANDING ===

    def resolve_reference(self, reference: str, thread_id: int = None) -> Optional[str]:
        """
        Resolve implicit reference

        Args:
            reference: Reference text (e.g., "that idea", "it", "the database")
            thread_id: Thread ID (or current)

        Returns:
            What the reference refers to
        """
        if thread_id is None:
            thread_id = self.current_thread_id

        # Check recent context first
        for msg in reversed(self.recent_context):
            if msg['thread_id'] == thread_id:
                # Simple keyword matching
                content_lower = msg['content'].lower()

                if "database" in reference.lower() and "database" in content_lower:
                    # Extract database reference
                    words = msg['content'].split()
                    for i, word in enumerate(words):
                        if "database" in word.lower() and i > 0:
                            return f"{words[i-1]} {word}"

                if "idea" in reference.lower():
                    return msg['content'][:100]

        # Check database for stored references
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT refers_to FROM conversation_references
            WHERE thread_id = ? AND reference_text LIKE ?
            ORDER BY created_at DESC
            LIMIT 1
        ''', (thread_id, f"%{reference}%"))

        result = cursor.fetchone()
        if result:
            return result['refers_to']

        return None

    def get_conversation_context(self, lookback: int = 5, thread_id: int = None) -> List[Dict]:
        """
        Get recent conversation context

        Args:
            lookback: Number of messages to retrieve
            thread_id: Thread ID (or current)

        Returns:
            List of recent messages
        """
        if thread_id is None:
            thread_id = self.current_thread_id

        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT role, content, intent, sentiment, created_at
            FROM thread_messages
            WHERE thread_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        ''', (thread_id, lookback))

        return [dict(row) for row in reversed(cursor.fetchall())]

    def find_relevant_past_discussion(self, query: str, limit: int = 3) -> List[Dict]:
        """
        Find relevant past discussions

        Args:
            query: Search query
            limit: Max results

        Returns:
            Relevant past messages
        """
        cursor = self.conn.cursor()

        cursor.execute('''
            SELECT tm.thread_id, tm.role, tm.content, tm.created_at, ct.topic
            FROM thread_messages tm
            JOIN conversation_threads ct ON tm.thread_id = ct.id
            WHERE tm.content LIKE ?
            ORDER BY tm.created_at DESC
            LIMIT ?
        ''', (f"%{query}%", limit))

        return [dict(row) for row in cursor.fetchall()]

    # === STATE MANAGEMENT ===

    def set_state(self, key: str, value: Any, thread_id: int = None):
        """Set conversation state variable"""
        if thread_id is None:
            thread_id = self.get_or_create_thread()

        cursor = self.conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO conversation_state
            (thread_id, state_key, state_value, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (thread_id, key, json.dumps(value)))

        self.conn.commit()

        # Also store in memory
        self.conversation_state[key] = value

    def get_state(self, key: str, thread_id: int = None) -> Optional[Any]:
        """Get conversation state variable"""
        # Check memory first
        if key in self.conversation_state:
            return self.conversation_state[key]

        # Check database
        if thread_id is None:
            thread_id = self.current_thread_id

        if thread_id:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT state_value FROM conversation_state
                WHERE thread_id = ? AND state_key = ?
                ORDER BY updated_at DESC
                LIMIT 1
            ''', (thread_id, key))

            result = cursor.fetchone()
            if result:
                value = json.loads(result['state_value'])
                self.conversation_state[key] = value
                return value

        return None

    # === ANALYTICS ===

    def get_thread_summary(self, thread_id: int) -> Dict:
        """Get summary of conversation thread"""
        cursor = self.conn.cursor()

        # Thread info
        cursor.execute('''
            SELECT * FROM conversation_threads WHERE id = ?
        ''', (thread_id,))
        thread = dict(cursor.fetchone())

        # Message breakdown
        cursor.execute('''
            SELECT role, COUNT(*) as count
            FROM thread_messages
            WHERE thread_id = ?
            GROUP BY role
        ''', (thread_id,))
        message_breakdown = {row['role']: row['count'] for row in cursor.fetchall()}

        # Entities mentioned
        cursor.execute('''
            SELECT DISTINCT entity_value
            FROM conversation_entities
            WHERE context LIKE ?
        ''', (f"%thread_{thread_id}%",))
        entities = [row['entity_value'] for row in cursor.fetchall()]

        # Sentiment analysis
        cursor.execute('''
            SELECT sentiment, COUNT(*) as count
            FROM thread_messages
            WHERE thread_id = ?
            GROUP BY sentiment
        ''', (thread_id,))
        sentiment_breakdown = {row['sentiment']: row['count'] for row in cursor.fetchall()}

        return {
            'thread': thread,
            'message_breakdown': message_breakdown,
            'entities_mentioned': entities,
            'sentiment_breakdown': sentiment_breakdown
        }

    def get_active_topics(self) -> List[Dict]:
        """Get currently active conversation topics"""
        cursor = self.conn.cursor()

        cursor.execute('''
            SELECT topic, COUNT(*) as thread_count, MAX(last_message_at) as last_active
            FROM conversation_threads
            WHERE status = 'active' AND topic IS NOT NULL
            GROUP BY topic
            ORDER BY last_active DESC
        ''')

        return [dict(row) for row in cursor.fetchall()]

    def close(self):
        """Close database connection"""
        self.conn.close()


# === TEST CODE ===

def main():
    """Test conversation manager"""
    print("Testing Conversation Manager")
    print("=" * 70)

    manager = ConversationManager(context_window=10)

    try:
        # Start thread
        print("\n1. Starting conversation thread...")
        thread_id = manager.start_thread(topic="Database optimization")
        print(f"   Thread ID: {thread_id}")

        # Add messages
        print("\n2. Adding conversation messages...")
        manager.add_message(
            "user",
            "We should optimize the database queries",
            entities=["database", "queries"]
        )

        manager.add_message(
            "assistant",
            "Good idea. I'll analyze the slow queries first.",
            sentiment="positive"
        )

        manager.add_message(
            "user",
            "How long will that take?",
            intent="time_estimate"
        )

        manager.add_message(
            "assistant",
            "About 10 minutes to analyze",
            sentiment="neutral"
        )

        print("   Added 4 messages")

        # Get context
        print("\n3. Getting conversation context...")
        context = manager.get_conversation_context(lookback=3)
        print(f"   Recent messages: {len(context)}")

        # Resolve reference
        print("\n4. Resolving implicit reference...")
        refers_to = manager.resolve_reference("that")
        if refers_to:
            print(f"   'that' refers to: {refers_to[:50]}...")

        # Set state
        print("\n5. Setting conversation state...")
        manager.set_state("current_task", "database_optimization")
        manager.set_state("progress", 0.25)

        # Get state
        task = manager.get_state("current_task")
        progress = manager.get_state("progress")
        print(f"   Current task: {task}")
        print(f"   Progress: {progress:.0%}")

        # Find past discussion
        print("\n6. Finding past discussions...")
        past = manager.find_relevant_past_discussion("database")
        print(f"   Found {len(past)} relevant past discussions")

        # Thread summary
        print("\n7. Getting thread summary...")
        summary = manager.get_thread_summary(thread_id)
        print(f"   Messages: {summary['message_breakdown']}")
        print(f"   Entities: {len(summary['entities_mentioned'])}")

        print(f"\n[OK] Conversation Manager working!")
        print(f"Database: {manager.db_path}")

    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        manager.close()


if __name__ == "__main__":
    main()
