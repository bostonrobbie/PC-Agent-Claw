#!/usr/bin/env python3
"""
Persistent Cross-Session Memory
Remember everything across all conversations forever
"""
import sys
from pathlib import Path
import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional
import hashlib

sys.path.append(str(Path(__file__).parent.parent))


class PersistentMemory:
    """
    Cross-session memory system

    Remembers:
    - User preferences and coding style
    - Past decisions and their rationale
    - Project context and goals
    - Conversation summaries
    - Key learnings and insights
    - Technical patterns that work
    """

    def __init__(self, db_path: str = None):
        workspace = Path(__file__).parent.parent
        if db_path is None:
            db_path = str(workspace / "persistent_memory.db")

        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        """Initialize memory database"""
        cursor = self.conn.cursor()

        # User preferences
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                preference_key TEXT NOT NULL,
                preference_value TEXT,
                confidence REAL DEFAULT 1.0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source TEXT,
                UNIQUE(category, preference_key)
            )
        ''')

        # Past decisions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision_context TEXT NOT NULL,
                decision_made TEXT NOT NULL,
                rationale TEXT,
                outcome TEXT,
                success INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                project TEXT,
                tags TEXT
            )
        ''')

        # Conversation summaries
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversation_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_date DATE NOT NULL,
                summary TEXT NOT NULL,
                key_topics TEXT,
                achievements TEXT,
                next_steps TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Key learnings
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                learning TEXT NOT NULL,
                category TEXT,
                importance REAL DEFAULT 0.5,
                verified INTEGER DEFAULT 0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source TEXT
            )
        ''')

        # Project context
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS project_context (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_name TEXT NOT NULL,
                description TEXT,
                goals TEXT,
                tech_stack TEXT,
                status TEXT,
                last_worked TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(project_name)
            )
        ''')

        # Code patterns that work
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS code_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_name TEXT NOT NULL,
                pattern_code TEXT NOT NULL,
                use_case TEXT,
                language TEXT,
                success_count INTEGER DEFAULT 0,
                last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        self.conn.commit()

    # === USER PREFERENCES ===

    def learn_preference(self, category: str, key: str, value: str,
                        confidence: float = 1.0, source: str = None):
        """
        Learn user preference

        Examples:
        - category="coding_style", key="indentation", value="4 spaces"
        - category="naming", key="variables", value="snake_case"
        - category="architecture", key="preferred_pattern", value="MVC"
        """
        cursor = self.conn.cursor()

        cursor.execute('''
            INSERT INTO user_preferences (category, preference_key, preference_value, confidence, source)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(category, preference_key) DO UPDATE SET
                preference_value = excluded.preference_value,
                confidence = excluded.confidence,
                last_updated = CURRENT_TIMESTAMP,
                source = excluded.source
        ''', (category, key, value, confidence, source))

        self.conn.commit()

    def get_preference(self, category: str, key: str = None) -> Optional[Dict]:
        """Get user preference"""
        cursor = self.conn.cursor()

        if key:
            cursor.execute('''
                SELECT * FROM user_preferences
                WHERE category = ? AND preference_key = ?
                ORDER BY confidence DESC
                LIMIT 1
            ''', (category, key))

            row = cursor.fetchone()
            return dict(row) if row else None
        else:
            # Get all preferences in category
            cursor.execute('''
                SELECT * FROM user_preferences
                WHERE category = ?
                ORDER BY confidence DESC
            ''', (category,))

            return [dict(row) for row in cursor.fetchall()]

    def get_all_preferences(self) -> Dict[str, List[Dict]]:
        """Get all preferences grouped by category"""
        cursor = self.conn.cursor()

        cursor.execute('SELECT DISTINCT category FROM user_preferences')
        categories = [row['category'] for row in cursor.fetchall()]

        result = {}
        for category in categories:
            result[category] = self.get_preference(category)

        return result

    # === DECISIONS ===

    def record_decision(self, context: str, decision: str, rationale: str = None,
                       project: str = None, tags: List[str] = None):
        """Record a decision made"""
        cursor = self.conn.cursor()

        tags_json = json.dumps(tags) if tags else None

        cursor.execute('''
            INSERT INTO decisions (decision_context, decision_made, rationale, project, tags)
            VALUES (?, ?, ?, ?, ?)
        ''', (context, decision, rationale, project, tags_json))

        self.conn.commit()
        return cursor.lastrowid

    def update_decision_outcome(self, decision_id: int, outcome: str, success: bool):
        """Update decision with outcome"""
        cursor = self.conn.cursor()

        cursor.execute('''
            UPDATE decisions
            SET outcome = ?, success = ?
            WHERE id = ?
        ''', (outcome, 1 if success else 0, decision_id))

        self.conn.commit()

    def find_similar_decisions(self, context: str, limit: int = 5) -> List[Dict]:
        """Find similar past decisions"""
        cursor = self.conn.cursor()

        # Simple keyword matching (could be enhanced with embeddings)
        keywords = context.lower().split()

        cursor.execute('''
            SELECT * FROM decisions
            WHERE decision_context LIKE ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (f'%{keywords[0]}%', limit))

        return [dict(row) for row in cursor.fetchall()]

    # === CONVERSATION SUMMARIES ===

    def save_conversation_summary(self, summary: str, key_topics: List[str],
                                  achievements: List[str], next_steps: List[str]):
        """Save conversation summary"""
        cursor = self.conn.cursor()

        today = datetime.now().date()

        cursor.execute('''
            INSERT INTO conversation_summaries
            (session_date, summary, key_topics, achievements, next_steps)
            VALUES (?, ?, ?, ?, ?)
        ''', (today, summary, json.dumps(key_topics), json.dumps(achievements),
              json.dumps(next_steps)))

        self.conn.commit()

    def get_recent_conversations(self, days: int = 7) -> List[Dict]:
        """Get recent conversation summaries"""
        cursor = self.conn.cursor()

        cursor.execute('''
            SELECT * FROM conversation_summaries
            WHERE session_date >= DATE('now', ? || ' days')
            ORDER BY session_date DESC
        ''', (f'-{days}',))

        return [dict(row) for row in cursor.fetchall()]

    def get_session_context(self) -> str:
        """Generate context from recent sessions for current session"""
        recent = self.get_recent_conversations(30)

        if not recent:
            return "No previous session context available."

        context = "## Recent Session Context\n\n"

        for session in recent[:5]:
            context += f"### {session['session_date']}\n"
            context += f"{session['summary']}\n\n"

            if session['key_topics']:
                topics = json.loads(session['key_topics'])
                context += f"Topics: {', '.join(topics)}\n"

            if session['next_steps']:
                steps = json.loads(session['next_steps'])
                if steps:
                    context += f"Next steps: {', '.join(steps)}\n"

            context += "\n"

        return context

    # === LEARNINGS ===

    def record_learning(self, learning: str, category: str = None,
                       importance: float = 0.5, source: str = None):
        """Record a key learning"""
        cursor = self.conn.cursor()

        cursor.execute('''
            INSERT INTO learnings (learning, category, importance, source)
            VALUES (?, ?, ?, ?)
        ''', (learning, category, importance, source))

        self.conn.commit()

    def verify_learning(self, learning_id: int):
        """Mark learning as verified through repeated success"""
        cursor = self.conn.cursor()

        cursor.execute('''
            UPDATE learnings
            SET verified = 1
            WHERE id = ?
        ''', (learning_id,))

        self.conn.commit()

    def get_learnings(self, category: str = None, verified_only: bool = False) -> List[Dict]:
        """Get learnings"""
        cursor = self.conn.cursor()

        query = 'SELECT * FROM learnings WHERE 1=1'
        params = []

        if category:
            query += ' AND category = ?'
            params.append(category)

        if verified_only:
            query += ' AND verified = 1'

        query += ' ORDER BY importance DESC, timestamp DESC'

        cursor.execute(query, params)

        return [dict(row) for row in cursor.fetchall()]

    # === PROJECT CONTEXT ===

    def update_project_context(self, project_name: str, description: str = None,
                              goals: List[str] = None, tech_stack: List[str] = None,
                              status: str = None):
        """Update project context"""
        cursor = self.conn.cursor()

        goals_json = json.dumps(goals) if goals else None
        tech_json = json.dumps(tech_stack) if tech_stack else None

        cursor.execute('''
            INSERT INTO project_context (project_name, description, goals, tech_stack, status)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(project_name) DO UPDATE SET
                description = COALESCE(excluded.description, description),
                goals = COALESCE(excluded.goals, goals),
                tech_stack = COALESCE(excluded.tech_stack, tech_stack),
                status = COALESCE(excluded.status, status),
                last_worked = CURRENT_TIMESTAMP
        ''', (project_name, description, goals_json, tech_json, status))

        self.conn.commit()

    def get_project_context(self, project_name: str) -> Optional[Dict]:
        """Get project context"""
        cursor = self.conn.cursor()

        cursor.execute('''
            SELECT * FROM project_context
            WHERE project_name = ?
        ''', (project_name,))

        row = cursor.fetchone()
        return dict(row) if row else None

    def get_all_projects(self) -> List[Dict]:
        """Get all projects"""
        cursor = self.conn.cursor()

        cursor.execute('''
            SELECT * FROM project_context
            ORDER BY last_worked DESC
        ''')

        return [dict(row) for row in cursor.fetchall()]

    # === CODE PATTERNS ===

    def save_code_pattern(self, pattern_name: str, code: str,
                         use_case: str = None, language: str = None):
        """Save successful code pattern"""
        cursor = self.conn.cursor()

        cursor.execute('''
            INSERT INTO code_patterns (pattern_name, pattern_code, use_case, language)
            VALUES (?, ?, ?, ?)
        ''', (pattern_name, code, use_case, language))

        self.conn.commit()

    def increment_pattern_usage(self, pattern_id: int):
        """Increment pattern usage count"""
        cursor = self.conn.cursor()

        cursor.execute('''
            UPDATE code_patterns
            SET success_count = success_count + 1,
                last_used = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (pattern_id,))

        self.conn.commit()

    def search_patterns(self, query: str, language: str = None) -> List[Dict]:
        """Search code patterns"""
        cursor = self.conn.cursor()

        sql = 'SELECT * FROM code_patterns WHERE pattern_name LIKE ? OR use_case LIKE ?'
        params = [f'%{query}%', f'%{query}%']

        if language:
            sql += ' AND language = ?'
            params.append(language)

        sql += ' ORDER BY success_count DESC, last_used DESC'

        cursor.execute(sql, params)

        return [dict(row) for row in cursor.fetchall()]

    # === MEMORY RECALL ===

    def recall_everything_about(self, topic: str) -> Dict:
        """Comprehensive recall about a topic"""
        cursor = self.conn.cursor()

        result = {
            'topic': topic,
            'preferences': [],
            'decisions': [],
            'learnings': [],
            'patterns': []
        }

        # Search preferences
        cursor.execute('''
            SELECT * FROM user_preferences
            WHERE preference_key LIKE ? OR preference_value LIKE ?
        ''', (f'%{topic}%', f'%{topic}%'))
        result['preferences'] = [dict(row) for row in cursor.fetchall()]

        # Search decisions
        cursor.execute('''
            SELECT * FROM decisions
            WHERE decision_context LIKE ? OR decision_made LIKE ?
            ORDER BY timestamp DESC
            LIMIT 10
        ''', (f'%{topic}%', f'%{topic}%'))
        result['decisions'] = [dict(row) for row in cursor.fetchall()]

        # Search learnings
        cursor.execute('''
            SELECT * FROM learnings
            WHERE learning LIKE ? OR category LIKE ?
            ORDER BY importance DESC
            LIMIT 10
        ''', (f'%{topic}%', f'%{topic}%'))
        result['learnings'] = [dict(row) for row in cursor.fetchall()]

        # Search patterns
        cursor.execute('''
            SELECT * FROM code_patterns
            WHERE pattern_name LIKE ? OR use_case LIKE ?
            ORDER BY success_count DESC
            LIMIT 10
        ''', (f'%{topic}%', f'%{topic}%'))
        result['patterns'] = [dict(row) for row in cursor.fetchall()]

        return result

    def close(self):
        """Close database connection"""
        self.conn.close()


# === INITIALIZATION & SEEDING ===

def initialize_with_current_knowledge(memory: PersistentMemory):
    """Seed memory with what we know so far"""

    # User preferences learned from this session
    memory.learn_preference("workspace", "location", "C:\\Users\\User\\.openclaw\\workspace")
    memory.learn_preference("github", "username", "bostonrobbie")
    memory.learn_preference("github", "repo", "PC-Agent-Claw")
    memory.learn_preference("communication", "telegram_preferred", "true")
    memory.learn_preference("ai_tool", "preferred_cli", "anthropic")
    memory.learn_preference("development", "style", "autonomous_agents")

    # Project context
    memory.update_project_context(
        "PC-Agent-Claw",
        description="Autonomous AI agent with business process management",
        goals=["Build autonomous capabilities", "Self-improving AI", "Business automation"],
        tech_stack=["Python", "SQLite", "React", "Flask", "Anthropic CLI"],
        status="active"
    )

    # Key learnings
    memory.record_learning(
        "User prefers Anthropic CLI over Claude Code CLI for GitHub integration",
        category="tools",
        importance=0.9
    )

    memory.record_learning(
        "User wants Telegram for all notifications, not Slack or Email",
        category="communication",
        importance=1.0
    )

    memory.record_learning(
        "Use free LLMs to save costs when hitting rate limits",
        category="optimization",
        importance=0.8
    )

    # Today's conversation summary
    memory.save_conversation_summary(
        summary="Built business process management system with 5 core systems and 6 enhancements. Added Telegram integration, Anthropic CLI support, and AI self-analysis. Now building top 5 persistent capabilities.",
        key_topics=["business automation", "SOPs", "Telegram", "AI capabilities", "persistent memory"],
        achievements=[
            "8,600+ lines of code",
            "38 database tables",
            "50+ API endpoints",
            "All pushed to GitHub"
        ],
        next_steps=[
            "Build persistent cross-session memory",
            "Build mistake learning system",
            "Add real-time internet access",
            "Implement background tasks",
            "Create autonomous debugging"
        ]
    )

    print("[INIT] Persistent memory initialized with current knowledge")


# === TEST CODE ===

def main():
    """Test persistent memory"""
    print("=" * 70)
    print("Persistent Cross-Session Memory")
    print("=" * 70)

    memory = PersistentMemory()

    try:
        print("\n1. Initializing with current knowledge...")
        initialize_with_current_knowledge(memory)

        print("\n2. Testing preference recall...")
        pref = memory.get_preference("ai_tool", "preferred_cli")
        print(f"   Preferred CLI: {pref['preference_value']}")

        print("\n3. Testing project context...")
        project = memory.get_project_context("PC-Agent-Claw")
        print(f"   Project: {project['project_name']}")
        print(f"   Status: {project['status']}")

        print("\n4. Testing learnings...")
        learnings = memory.get_learnings()
        print(f"   Learnings stored: {len(learnings)}")
        if learnings:
            print(f"   Top learning: {learnings[0]['learning']}")

        print("\n5. Testing comprehensive recall...")
        recall = memory.recall_everything_about("Telegram")
        print(f"   Found:")
        print(f"   - {len(recall['preferences'])} preferences")
        print(f"   - {len(recall['learnings'])} learnings")

        print("\n6. Testing session context generation...")
        context = memory.get_session_context()
        print(f"   Context length: {len(context)} characters")

        print(f"\n[OK] Persistent Memory System Working!")
        print(f"Database: {memory.db_path}")

    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        memory.close()


if __name__ == "__main__":
    main()
