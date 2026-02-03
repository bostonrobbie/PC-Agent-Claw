#!/usr/bin/env python3
"""
Persistent Memory System - Never Lose Context
SQLite-based memory that survives session resets
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

class PersistentMemory:
    """
    Persistent memory system that survives context resets

    Stores:
    - Current tasks and their status
    - Key decisions and rationale
    - Project state and context
    - Important findings and research
    - Strategy performance data
    - User preferences
    """

    def __init__(self, db_path: str = None):
        if db_path is None:
            workspace = Path(__file__).parent.parent
            db_path = workspace / "memory.db"

        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        """Initialize database schema"""
        cursor = self.conn.cursor()

        # Tasks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT UNIQUE,
                description TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                priority INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                metadata TEXT
            )
        ''')

        # Decisions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision TEXT NOT NULL,
                rationale TEXT,
                outcome TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                tags TEXT
            )
        ''')

        # Context table (key-value store)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS context (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Research findings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS research (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                source TEXT,
                score REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                tags TEXT
            )
        ''')

        # Strategy performance table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS strategy_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_name TEXT NOT NULL,
                timeframe TEXT,
                metric_name TEXT,
                metric_value REAL,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Session log table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS session_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                session_end TIMESTAMP,
                tasks_completed INTEGER DEFAULT 0,
                context_summary TEXT
            )
        ''')

        self.conn.commit()

    # === TASK MANAGEMENT ===

    def add_task(self, task_id: str, description: str, priority: int = 0, metadata: Dict = None):
        """Add a new task"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO tasks (task_id, description, priority, metadata)
            VALUES (?, ?, ?, ?)
        ''', (task_id, description, priority, json.dumps(metadata) if metadata else None))
        self.conn.commit()

    def update_task_status(self, task_id: str, status: str):
        """Update task status (pending, in_progress, completed, failed)"""
        cursor = self.conn.cursor()
        completed_at = datetime.now() if status == 'completed' else None
        cursor.execute('''
            UPDATE tasks
            SET status = ?, updated_at = CURRENT_TIMESTAMP, completed_at = ?
            WHERE task_id = ?
        ''', (status, completed_at, task_id))
        self.conn.commit()

    def get_active_tasks(self) -> List[Dict]:
        """Get all non-completed tasks"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM tasks
            WHERE status != 'completed'
            ORDER BY priority DESC, created_at ASC
        ''')
        return [dict(row) for row in cursor.fetchall()]

    def get_recent_completed_tasks(self, limit: int = 10) -> List[Dict]:
        """Get recently completed tasks"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM tasks
            WHERE status = 'completed'
            ORDER BY completed_at DESC
            LIMIT ?
        ''', (limit,))
        return [dict(row) for row in cursor.fetchall()]

    # === DECISION TRACKING ===

    def log_decision(self, decision: str, rationale: str, tags: List[str] = None):
        """Log an important decision"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO decisions (decision, rationale, tags)
            VALUES (?, ?, ?)
        ''', (decision, rationale, json.dumps(tags) if tags else None))
        self.conn.commit()

    def update_decision_outcome(self, decision_id: int, outcome: str):
        """Update outcome of a decision"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE decisions SET outcome = ? WHERE id = ?
        ''', (outcome, decision_id))
        self.conn.commit()

    def get_recent_decisions(self, limit: int = 20) -> List[Dict]:
        """Get recent decisions"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM decisions
            ORDER BY created_at DESC
            LIMIT ?
        ''', (limit,))
        return [dict(row) for row in cursor.fetchall()]

    # === CONTEXT MANAGEMENT ===

    def set_context(self, key: str, value: Any):
        """Store a context value"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO context (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (key, json.dumps(value)))
        self.conn.commit()

    def get_context(self, key: str) -> Optional[Any]:
        """Retrieve a context value"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT value FROM context WHERE key = ?', (key,))
        row = cursor.fetchone()
        return json.loads(row['value']) if row else None

    def get_all_context(self) -> Dict:
        """Get all context"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT key, value FROM context')
        return {row['key']: json.loads(row['value']) for row in cursor.fetchall()}

    # === RESEARCH TRACKING ===

    def add_research_finding(self, title: str, content: str, source: str = None,
                            score: float = None, tags: List[str] = None):
        """Add a research finding"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO research (title, content, source, score, tags)
            VALUES (?, ?, ?, ?, ?)
        ''', (title, content, source, score, json.dumps(tags) if tags else None))
        self.conn.commit()
        return cursor.lastrowid

    def search_research(self, query: str, limit: int = 10) -> List[Dict]:
        """Search research findings"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM research
            WHERE title LIKE ? OR content LIKE ? OR tags LIKE ?
            ORDER BY score DESC, created_at DESC
            LIMIT ?
        ''', (f'%{query}%', f'%{query}%', f'%{query}%', limit))
        return [dict(row) for row in cursor.fetchall()]

    # === STRATEGY PERFORMANCE ===

    def log_strategy_metric(self, strategy_name: str, timeframe: str,
                           metric_name: str, metric_value: float):
        """Log a strategy performance metric"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO strategy_performance (strategy_name, timeframe, metric_name, metric_value)
            VALUES (?, ?, ?, ?)
        ''', (strategy_name, timeframe, metric_name, metric_value))
        self.conn.commit()

    def get_strategy_metrics(self, strategy_name: str, timeframe: str = None,
                            days: int = 30) -> List[Dict]:
        """Get recent metrics for a strategy"""
        cursor = self.conn.cursor()
        if timeframe:
            cursor.execute('''
                SELECT * FROM strategy_performance
                WHERE strategy_name = ? AND timeframe = ?
                  AND recorded_at >= datetime('now', '-' || ? || ' days')
                ORDER BY recorded_at DESC
            ''', (strategy_name, timeframe, days))
        else:
            cursor.execute('''
                SELECT * FROM strategy_performance
                WHERE strategy_name = ?
                  AND recorded_at >= datetime('now', '-' || ? || ' days')
                ORDER BY recorded_at DESC
            ''', (strategy_name, days))
        return [dict(row) for row in cursor.fetchall()]

    # === SESSION MANAGEMENT ===

    def start_session(self):
        """Log session start"""
        cursor = self.conn.cursor()
        cursor.execute('INSERT INTO session_log (session_start) VALUES (CURRENT_TIMESTAMP)')
        self.conn.commit()
        return cursor.lastrowid

    def end_session(self, session_id: int, tasks_completed: int, context_summary: str):
        """Log session end"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE session_log
            SET session_end = CURRENT_TIMESTAMP,
                tasks_completed = ?,
                context_summary = ?
            WHERE id = ?
        ''', (tasks_completed, context_summary, session_id))
        self.conn.commit()

    def get_session_summary(self) -> Dict:
        """Get summary of current state"""
        return {
            'active_tasks': len(self.get_active_tasks()),
            'completed_tasks_today': self._get_tasks_completed_today(),
            'recent_decisions': len(self.get_recent_decisions(limit=5)),
            'context_items': len(self.get_all_context()),
            'research_findings': self._get_research_count()
        }

    def _get_tasks_completed_today(self) -> int:
        """Count tasks completed today"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) as count FROM tasks
            WHERE status = 'completed'
              AND DATE(completed_at) = DATE('now')
        ''')
        return cursor.fetchone()['count']

    def _get_research_count(self) -> int:
        """Count research findings"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) as count FROM research')
        return cursor.fetchone()['count']

    # === EXPORT/IMPORT ===

    def export_to_json(self, output_path: str):
        """Export all memory to JSON"""
        data = {
            'tasks': self.get_all_tasks(),
            'decisions': self.get_recent_decisions(limit=100),
            'context': self.get_all_context(),
            'research': self.get_all_research(),
            'exported_at': datetime.now().isoformat()
        }
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)

    def get_all_tasks(self) -> List[Dict]:
        """Get all tasks"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM tasks ORDER BY created_at DESC')
        return [dict(row) for row in cursor.fetchall()]

    def get_all_research(self) -> List[Dict]:
        """Get all research"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM research ORDER BY created_at DESC LIMIT 100')
        return [dict(row) for row in cursor.fetchall()]

    def close(self):
        """Close database connection"""
        self.conn.close()


def main():
    """Test persistent memory"""
    memory = PersistentMemory()

    # Add some test tasks
    memory.add_task('task_001', 'Build persistent memory system', priority=10)
    memory.add_task('task_002', 'Create performance dashboard', priority=8)

    # Log a decision
    memory.log_decision(
        'Use SQLite for persistent memory',
        'SQLite is lightweight, fast, and requires no server',
        tags=['architecture', 'database']
    )

    # Store some context
    memory.set_context('current_focus', 'Building agent infrastructure')
    memory.set_context('top_priorities', ['persistent_memory', 'work_queue', 'dashboard'])

    # Add research finding
    memory.add_research_finding(
        'Value Rebound Strategy',
        '12-15% annual returns, low capital requirement',
        source='Financial Analysis Report',
        score=0.8175,
        tags=['investment', 'trading']
    )

    # Get summary
    summary = memory.get_session_summary()
    print("Session Summary:")
    for key, value in summary.items():
        print(f"  {key}: {value}")

    print(f"\nDatabase location: {memory.db_path}")
    memory.close()


if __name__ == "__main__":
    main()
