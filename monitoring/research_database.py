#!/usr/bin/env python3
"""Research Database (#8) - Organize research, findings, and insights"""
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import json
import sys

sys.path.append(str(Path(__file__).parent.parent))

class ResearchDatabase:
    def __init__(self, db_path: str = None):
        if db_path is None:
            workspace = Path(__file__).parent.parent
            db_path = str(workspace / "research.db")

        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        """Initialize database schema"""
        cursor = self.conn.cursor()

        # Research entries table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS research (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                category TEXT,
                source TEXT,
                url TEXT,
                tags TEXT,
                rating INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Insights table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                insight TEXT NOT NULL,
                context TEXT,
                confidence REAL DEFAULT 0.5,
                research_ids TEXT,
                tags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Hypotheses table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS hypotheses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hypothesis TEXT NOT NULL,
                evidence TEXT,
                status TEXT DEFAULT 'untested',
                confidence REAL DEFAULT 0.5,
                test_results TEXT,
                tags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Experiments table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS experiments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                hypothesis_id INTEGER,
                parameters TEXT,
                results TEXT,
                status TEXT DEFAULT 'planned',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (hypothesis_id) REFERENCES hypotheses (id)
            )
        ''')

        self.conn.commit()

    def add_research(self, title: str, content: str, category: str = None,
                     source: str = None, url: str = None, tags: List[str] = None,
                     rating: int = 0) -> int:
        """Add a research entry"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO research (title, content, category, source, url, tags, rating)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (title, content, category, source, url,
              json.dumps(tags) if tags else None, rating))
        self.conn.commit()
        return cursor.lastrowid

    def add_insight(self, insight: str, context: str = None, confidence: float = 0.5,
                    research_ids: List[int] = None, tags: List[str] = None) -> int:
        """Add an insight derived from research"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO insights (insight, context, confidence, research_ids, tags)
            VALUES (?, ?, ?, ?, ?)
        ''', (insight, context, confidence,
              json.dumps(research_ids) if research_ids else None,
              json.dumps(tags) if tags else None))
        self.conn.commit()
        return cursor.lastrowid

    def add_hypothesis(self, hypothesis: str, evidence: str = None,
                       confidence: float = 0.5, tags: List[str] = None) -> int:
        """Add a hypothesis to test"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO hypotheses (hypothesis, evidence, confidence, tags)
            VALUES (?, ?, ?, ?)
        ''', (hypothesis, evidence, confidence, json.dumps(tags) if tags else None))
        self.conn.commit()
        return cursor.lastrowid

    def add_experiment(self, name: str, description: str = None,
                       hypothesis_id: int = None, parameters: Dict = None) -> int:
        """Add an experiment"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO experiments (name, description, hypothesis_id, parameters)
            VALUES (?, ?, ?, ?)
        ''', (name, description, hypothesis_id,
              json.dumps(parameters) if parameters else None))
        self.conn.commit()
        return cursor.lastrowid

    def search_research(self, query: str, category: str = None, limit: int = 10) -> List[Dict]:
        """Search research entries"""
        cursor = self.conn.cursor()

        if category:
            cursor.execute('''
                SELECT * FROM research
                WHERE (title LIKE ? OR content LIKE ?) AND category = ?
                ORDER BY rating DESC, created_at DESC
                LIMIT ?
            ''', (f'%{query}%', f'%{query}%', category, limit))
        else:
            cursor.execute('''
                SELECT * FROM research
                WHERE title LIKE ? OR content LIKE ?
                ORDER BY rating DESC, created_at DESC
                LIMIT ?
            ''', (f'%{query}%', f'%{query}%', limit))

        return [dict(row) for row in cursor.fetchall()]

    def get_insights_by_confidence(self, min_confidence: float = 0.7, limit: int = 10) -> List[Dict]:
        """Get high-confidence insights"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM insights
            WHERE confidence >= ?
            ORDER BY confidence DESC, created_at DESC
            LIMIT ?
        ''', (min_confidence, limit))
        return [dict(row) for row in cursor.fetchall()]

    def update_hypothesis_status(self, hypothesis_id: int, status: str,
                                 test_results: Dict = None, confidence: float = None):
        """Update hypothesis after testing"""
        cursor = self.conn.cursor()

        if confidence is not None:
            cursor.execute('''
                UPDATE hypotheses
                SET status = ?, test_results = ?, confidence = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, json.dumps(test_results) if test_results else None,
                  confidence, hypothesis_id))
        else:
            cursor.execute('''
                UPDATE hypotheses
                SET status = ?, test_results = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, json.dumps(test_results) if test_results else None, hypothesis_id))

        self.conn.commit()

    def get_statistics(self) -> Dict:
        """Get database statistics"""
        cursor = self.conn.cursor()

        cursor.execute('SELECT COUNT(*) as count FROM research')
        research_count = cursor.fetchone()['count']

        cursor.execute('SELECT COUNT(*) as count FROM insights')
        insights_count = cursor.fetchone()['count']

        cursor.execute('SELECT COUNT(*) as count FROM hypotheses')
        hypotheses_count = cursor.fetchone()['count']

        cursor.execute('SELECT COUNT(*) as count FROM experiments')
        experiments_count = cursor.fetchone()['count']

        cursor.execute('SELECT AVG(confidence) as avg FROM insights')
        avg_insight_confidence = cursor.fetchone()['avg'] or 0

        return {
            'research_entries': research_count,
            'insights': insights_count,
            'hypotheses': hypotheses_count,
            'experiments': experiments_count,
            'avg_insight_confidence': round(avg_insight_confidence, 2)
        }

    def close(self):
        """Close database connection"""
        self.conn.close()


if __name__ == '__main__':
    # Test the system
    db = ResearchDatabase()

    # Add some research
    research_id = db.add_research(
        "NQ Futures Trading Strategy",
        "Opening range breakout strategy shows promise on 15-minute timeframe",
        category="Trading",
        source="Backtest Results",
        tags=["NQ", "strategy", "futures"]
    )

    # Add an insight
    insight_id = db.add_insight(
        "Opening range strategies perform better during high volatility periods",
        context="Analysis of 3 months of backtest data",
        confidence=0.8,
        research_ids=[research_id],
        tags=["trading", "volatility"]
    )

    # Add a hypothesis
    hypothesis_id = db.add_hypothesis(
        "Adding volume filter will improve win rate by 5%",
        evidence="Initial analysis shows volume correlation",
        confidence=0.6,
        tags=["trading", "optimization"]
    )

    # Get statistics
    stats = db.get_statistics()
    print("Research Database Statistics:")
    print(json.dumps(stats, indent=2))

    # Search
    results = db.search_research("NQ")
    print(f"\nSearch results for 'NQ': {len(results)} entries")

    db.close()
    print("\nResearch Database system ready!")
