#!/usr/bin/env python3
"""Session Profiler (#20) - Profile trading sessions for patterns"""
import sqlite3
from pathlib import Path
from typing import Dict, List
from datetime import datetime, time
import json
import sys

sys.path.append(str(Path(__file__).parent.parent))

class SessionProfiler:
    """Profile trading performance across different sessions"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            workspace = Path(__file__).parent.parent
            db_path = str(workspace / "session_profiles.db")

        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        """Initialize database schema"""
        cursor = self.conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS session_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session TEXT NOT NULL,
                hour INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                pnl REAL NOT NULL,
                trade_date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        self.conn.commit()

    def get_session(self, hour: int) -> str:
        """Determine session based on hour"""
        if 18 <= hour or hour < 2:
            return 'asian'
        elif 2 <= hour < 8:
            return 'london'
        elif 8 <= hour < 16:
            return 'nyc'
        else:
            return 'after_hours'

    def log_trade(self, hour: int, symbol: str, pnl: float, trade_date: str = None):
        """Log a trade for session profiling"""
        if trade_date is None:
            trade_date = datetime.now().strftime('%Y-%m-%d')

        session = self.get_session(hour)

        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO session_trades (session, hour, symbol, pnl, trade_date)
            VALUES (?, ?, ?, ?, ?)
        ''', (session, hour, symbol, pnl, trade_date))
        self.conn.commit()

    def get_session_statistics(self, session: str = None) -> Dict:
        """Get statistics for a session"""
        cursor = self.conn.cursor()

        if session:
            cursor.execute('''
                SELECT
                    COUNT(*) as trade_count,
                    SUM(pnl) as total_pnl,
                    AVG(pnl) as avg_pnl,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winners,
                    SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losers
                FROM session_trades
                WHERE session = ?
            ''', (session,))
        else:
            cursor.execute('''
                SELECT
                    session,
                    COUNT(*) as trade_count,
                    SUM(pnl) as total_pnl,
                    AVG(pnl) as avg_pnl,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winners,
                    SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losers
                FROM session_trades
                GROUP BY session
            ''')

        if session:
            row = cursor.fetchone()
            if row:
                stats = dict(row)
                win_rate = (stats['winners'] / stats['trade_count'] * 100) if stats['trade_count'] > 0 else 0
                stats['win_rate'] = round(win_rate, 2)
                return stats
            return {}
        else:
            results = {}
            for row in cursor.fetchall():
                stats = dict(row)
                win_rate = (stats['winners'] / stats['trade_count'] * 100) if stats['trade_count'] > 0 else 0
                stats['win_rate'] = round(win_rate, 2)
                results[stats['session']] = stats

            return results

    def get_hourly_profile(self) -> Dict[int, Dict]:
        """Get performance profile by hour"""
        cursor = self.conn.cursor()

        cursor.execute('''
            SELECT
                hour,
                COUNT(*) as trade_count,
                SUM(pnl) as total_pnl,
                AVG(pnl) as avg_pnl,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winners
            FROM session_trades
            GROUP BY hour
            ORDER BY hour
        ''')

        profile = {}
        for row in cursor.fetchall():
            stats = dict(row)
            win_rate = (stats['winners'] / stats['trade_count'] * 100) if stats['trade_count'] > 0 else 0
            stats['win_rate'] = round(win_rate, 2)
            stats['session'] = self.get_session(stats['hour'])
            profile[stats['hour']] = stats

        return profile

    def get_best_sessions(self, metric: str = 'total_pnl', limit: int = 3) -> List[str]:
        """Get best performing sessions"""
        stats = self.get_session_statistics()

        # Sort by metric
        sorted_sessions = sorted(
            stats.items(),
            key=lambda x: x[1].get(metric, 0),
            reverse=True
        )

        return [session for session, _ in sorted_sessions[:limit]]

    def get_symbol_by_session(self, symbol: str) -> Dict:
        """Get performance of a symbol by session"""
        cursor = self.conn.cursor()

        cursor.execute('''
            SELECT
                session,
                COUNT(*) as trade_count,
                SUM(pnl) as total_pnl,
                AVG(pnl) as avg_pnl
            FROM session_trades
            WHERE symbol = ?
            GROUP BY session
        ''', (symbol,))

        results = {}
        for row in cursor.fetchall():
            stats = dict(row)
            results[stats['session']] = stats

        return results

    def close(self):
        """Close database connection"""
        self.conn.close()


if __name__ == '__main__':
    # Test the system
    profiler = SessionProfiler()

    print("Session Profiler ready!")

    # Log some sample trades
    print("\nLogging sample trades...")
    sessions_hours = {
        'asian': [20, 22, 0],
        'london': [3, 5, 7],
        'nyc': [9, 11, 13, 15]
    }

    for session, hours in sessions_hours.items():
        for hour in hours:
            # Simulate trades with varying performance
            for _ in range(5):
                pnl = 50 if session == 'nyc' else -20  # NYC performs better
                profiler.log_trade(hour, 'NQ', pnl + (hash(f'{session}{hour}') % 100 - 50))

    # Get session statistics
    print("\nSession Statistics:")
    stats = profiler.get_session_statistics()
    for session, data in stats.items():
        print(f"\n  {session.upper()}:")
        print(f"    Trades: {data['trade_count']}")
        print(f"    Total P&L: ${data['total_pnl']:.2f}")
        print(f"    Avg P&L: ${data['avg_pnl']:.2f}")
        print(f"    Win rate: {data['win_rate']:.1f}%")

    # Get best sessions
    best = profiler.get_best_sessions()
    print(f"\nBest sessions: {', '.join(best)}")

    profiler.close()
