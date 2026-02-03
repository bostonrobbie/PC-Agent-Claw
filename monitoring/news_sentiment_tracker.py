#!/usr/bin/env python3
"""News/Sentiment Tracker (#21) - Track news and market sentiment"""
import sqlite3
from pathlib import Path
from typing import Dict, List
from datetime import datetime
import json
import sys

sys.path.append(str(Path(__file__).parent.parent))

class NewsSentimentTracker:
    """Track news and sentiment for trading"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            workspace = Path(__file__).parent.parent
            db_path = str(workspace / "news_sentiment.db")

        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        """Initialize database schema"""
        cursor = self.conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS news_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT,
                source TEXT,
                url TEXT,
                symbols TEXT,
                sentiment_score REAL,
                importance INTEGER DEFAULT 5,
                published_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sentiment_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                sentiment_score REAL NOT NULL,
                volume_score REAL,
                social_mentions INTEGER,
                news_count INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        self.conn.commit()

    def add_news(self, title: str, content: str = None, source: str = None,
                url: str = None, symbols: List[str] = None, sentiment_score: float = 0,
                importance: int = 5, published_at: str = None) -> int:
        """Add a news item"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO news_items (title, content, source, url, symbols, sentiment_score, importance, published_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (title, content, source, url,
              json.dumps(symbols) if symbols else None,
              sentiment_score, importance, published_at))
        self.conn.commit()
        return cursor.lastrowid

    def add_sentiment_snapshot(self, symbol: str, sentiment_score: float,
                              volume_score: float = None, social_mentions: int = 0,
                              news_count: int = 0) -> int:
        """Add a sentiment snapshot"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO sentiment_snapshots (symbol, sentiment_score, volume_score, social_mentions, news_count)
            VALUES (?, ?, ?, ?, ?)
        ''', (symbol, sentiment_score, volume_score, social_mentions, news_count))
        self.conn.commit()
        return cursor.lastrowid

    def get_recent_news(self, symbol: str = None, limit: int = 10) -> List[Dict]:
        """Get recent news items"""
        cursor = self.conn.cursor()

        if symbol:
            cursor.execute('''
                SELECT * FROM news_items
                WHERE symbols LIKE ?
                ORDER BY created_at DESC
                LIMIT ?
            ''', (f'%{symbol}%', limit))
        else:
            cursor.execute('''
                SELECT * FROM news_items
                ORDER BY created_at DESC
                LIMIT ?
            ''', (limit,))

        return [dict(row) for row in cursor.fetchall()]

    def get_sentiment_trend(self, symbol: str, hours: int = 24) -> Dict:
        """Get sentiment trend for a symbol"""
        cursor = self.conn.cursor()

        cursor.execute('''
            SELECT
                AVG(sentiment_score) as avg_sentiment,
                COUNT(*) as snapshot_count,
                SUM(social_mentions) as total_mentions,
                SUM(news_count) as total_news
            FROM sentiment_snapshots
            WHERE symbol = ? AND created_at >= datetime('now', ?)
        ''', (symbol, f'-{hours} hours'))

        row = cursor.fetchone()
        if row:
            return dict(row)

        return {}

    def get_market_sentiment(self) -> Dict:
        """Get overall market sentiment"""
        cursor = self.conn.cursor()

        # Get sentiment across all symbols
        cursor.execute('''
            SELECT
                AVG(sentiment_score) as overall_sentiment,
                COUNT(DISTINCT symbol) as symbols_tracked
            FROM sentiment_snapshots
            WHERE created_at >= datetime('now', '-1 hour')
        ''')

        overall = dict(cursor.fetchone())

        # Get news sentiment
        cursor.execute('''
            SELECT
                AVG(sentiment_score) as news_sentiment,
                COUNT(*) as news_count
            FROM news_items
            WHERE created_at >= datetime('now', '-24 hours')
        ''')

        news = dict(cursor.fetchone())

        return {
            'overall_sentiment': overall.get('overall_sentiment', 0),
            'symbols_tracked': overall.get('symbols_tracked', 0),
            'news_sentiment': news.get('news_sentiment', 0),
            'recent_news_count': news.get('news_count', 0)
        }

    def get_high_impact_news(self, min_importance: int = 8, hours: int = 24) -> List[Dict]:
        """Get high-impact news"""
        cursor = self.conn.cursor()

        cursor.execute('''
            SELECT * FROM news_items
            WHERE importance >= ? AND created_at >= datetime('now', ?)
            ORDER BY importance DESC, created_at DESC
        ''', (min_importance, f'-{hours} hours'))

        return [dict(row) for row in cursor.fetchall()]

    def analyze_sentiment_change(self, symbol: str, hours: int = 24) -> Dict:
        """Analyze sentiment change over time"""
        cursor = self.conn.cursor()

        # Get recent sentiment
        cursor.execute('''
            SELECT AVG(sentiment_score) as recent
            FROM sentiment_snapshots
            WHERE symbol = ? AND created_at >= datetime('now', '-1 hour')
        ''', (symbol,))
        recent = cursor.fetchone()['recent'] or 0

        # Get historical sentiment
        cursor.execute('''
            SELECT AVG(sentiment_score) as historical
            FROM sentiment_snapshots
            WHERE symbol = ? AND created_at >= datetime('now', ?) AND created_at < datetime('now', '-1 hour')
        ''', (symbol, f'-{hours} hours'))
        historical = cursor.fetchone()['historical'] or 0

        change = recent - historical

        return {
            'symbol': symbol,
            'recent_sentiment': round(recent, 3),
            'historical_sentiment': round(historical, 3),
            'change': round(change, 3),
            'direction': 'improving' if change > 0.1 else 'deteriorating' if change < -0.1 else 'stable'
        }

    def close(self):
        """Close database connection"""
        self.conn.close()


if __name__ == '__main__':
    # Test the system
    tracker = NewsSentimentTracker()

    print("News/Sentiment Tracker ready!")

    # Add sample news
    print("\nAdding sample news...")
    tracker.add_news(
        "Fed Holds Rates Steady",
        "The Federal Reserve maintained interest rates at current levels",
        source="Reuters",
        symbols=["NQ", "ES"],
        sentiment_score=0.2,
        importance=9
    )

    tracker.add_news(
        "Tech Earnings Beat Expectations",
        "Major tech companies report strong Q4 earnings",
        source="Bloomberg",
        symbols=["NQ"],
        sentiment_score=0.7,
        importance=7
    )

    # Add sentiment snapshots
    print("Adding sentiment snapshots...")
    for i in range(5):
        tracker.add_sentiment_snapshot(
            "NQ",
            sentiment_score=0.5 + (i * 0.1),
            social_mentions=1000 + i * 100,
            news_count=5 + i
        )

    # Get market sentiment
    print("\nMarket Sentiment:")
    sentiment = tracker.get_market_sentiment()
    print(json.dumps(sentiment, indent=2))

    # Get sentiment trend
    print("\nNQ Sentiment Trend:")
    trend = tracker.get_sentiment_trend("NQ", hours=24)
    print(json.dumps(trend, indent=2))

    # Analyze sentiment change
    print("\nSentiment Change Analysis:")
    analysis = tracker.analyze_sentiment_change("NQ", hours=24)
    print(json.dumps(analysis, indent=2))

    tracker.close()
