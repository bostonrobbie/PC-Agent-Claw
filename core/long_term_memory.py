#!/usr/bin/env python3
"""
Long-Term Memory with Semantic Retrieval (#61)
Never forget anything - semantic search and auto-context
"""
import sqlite3
import json
from pathlib import Path
from typing import List, Dict

class LongTermMemory:
    def __init__(self, db_path: str = None):
        if db_path is None:
            workspace = Path(__file__).parent.parent
            db_path = workspace / "long_term_memory.db"
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                memory_type TEXT,
                importance REAL DEFAULT 0.5,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                tags TEXT
            )
        ''')
        self.conn.commit()

    def remember(self, content: str, memory_type: str = 'general', importance: float = 0.5, tags: List[str] = None) -> int:
        cursor = self.conn.cursor()
        cursor.execute('INSERT INTO memories (content, memory_type, importance, tags) VALUES (?, ?, ?, ?)',
                      (content, memory_type, importance, json.dumps(tags) if tags else None))
        self.conn.commit()
        return cursor.lastrowid

    def recall(self, query: str, limit: int = 5) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute('''SELECT * FROM memories WHERE content LIKE ? ORDER BY importance DESC, created_at DESC LIMIT ?''',
                      (f'%{query}%', limit))
        return [dict(row) for row in cursor.fetchall()]

    def close(self):
        self.conn.close()

if __name__ == "__main__":
    ltm = LongTermMemory()
    ltm.remember("59 systems approved for building", importance=0.9)
    ltm.remember("RTX 5070 at 192.168.0.35", importance=0.8)
    print("Memories:", ltm.recall("systems", 3))
    ltm.close()
