#!/usr/bin/env python3
"""Strategy Library (#37) - Organize and manage trading strategies"""
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import json
import sys

sys.path.append(str(Path(__file__).parent.parent))

class StrategyLibrary:
    """Library for managing trading strategies"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            workspace = Path(__file__).parent.parent
            db_path = str(workspace / "strategy_library.db")

        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        """Initialize database schema"""
        cursor = self.conn.cursor()

        # Strategies table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS strategies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                category TEXT,
                timeframe TEXT,
                instruments TEXT,
                code TEXT,
                parameters TEXT,
                status TEXT DEFAULT 'development',
                rating INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Backtest results table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS backtest_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_id INTEGER NOT NULL,
                start_date DATE,
                end_date DATE,
                initial_capital REAL,
                final_capital REAL,
                total_return REAL,
                win_rate REAL,
                sharpe_ratio REAL,
                max_drawdown REAL,
                total_trades INTEGER,
                parameters TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (strategy_id) REFERENCES strategies (id)
            )
        ''')

        # Live performance table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS live_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_id INTEGER NOT NULL,
                date DATE NOT NULL,
                pnl REAL,
                trades_count INTEGER,
                win_count INTEGER,
                loss_count INTEGER,
                notes TEXT,
                FOREIGN KEY (strategy_id) REFERENCES strategies (id)
            )
        ''')

        self.conn.commit()

    def add_strategy(self, name: str, description: str = None, category: str = None,
                    timeframe: str = None, instruments: List[str] = None,
                    code: str = None, parameters: Dict = None) -> int:
        """Add a new strategy to the library"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO strategies (name, description, category, timeframe, instruments, code, parameters)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (name, description, category, timeframe,
              json.dumps(instruments) if instruments else None,
              code,
              json.dumps(parameters) if parameters else None))
        self.conn.commit()
        return cursor.lastrowid

    def get_strategy(self, strategy_id: int = None, name: str = None) -> Optional[Dict]:
        """Get a strategy by ID or name"""
        cursor = self.conn.cursor()

        if strategy_id:
            cursor.execute('SELECT * FROM strategies WHERE id = ?', (strategy_id,))
        elif name:
            cursor.execute('SELECT * FROM strategies WHERE name = ?', (name,))
        else:
            return None

        row = cursor.fetchone()
        if row:
            strategy = dict(row)
            # Parse JSON fields
            if strategy.get('instruments'):
                strategy['instruments'] = json.loads(strategy['instruments'])
            if strategy.get('parameters'):
                strategy['parameters'] = json.loads(strategy['parameters'])
            return strategy

        return None

    def update_strategy(self, strategy_id: int, **kwargs):
        """Update strategy fields"""
        allowed_fields = ['description', 'category', 'timeframe', 'instruments',
                         'code', 'parameters', 'status', 'rating']

        updates = []
        values = []

        for field, value in kwargs.items():
            if field in allowed_fields:
                updates.append(f'{field} = ?')
                if field in ['instruments', 'parameters']:
                    values.append(json.dumps(value) if value else None)
                else:
                    values.append(value)

        if updates:
            values.append(strategy_id)
            cursor = self.conn.cursor()
            cursor.execute(f'''
                UPDATE strategies
                SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', values)
            self.conn.commit()

    def add_backtest_result(self, strategy_id: int, start_date: str, end_date: str,
                           initial_capital: float, final_capital: float,
                           total_return: float, win_rate: float, sharpe_ratio: float,
                           max_drawdown: float, total_trades: int,
                           parameters: Dict = None) -> int:
        """Add a backtest result for a strategy"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO backtest_results (
                strategy_id, start_date, end_date, initial_capital, final_capital,
                total_return, win_rate, sharpe_ratio, max_drawdown, total_trades, parameters
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (strategy_id, start_date, end_date, initial_capital, final_capital,
              total_return, win_rate, sharpe_ratio, max_drawdown, total_trades,
              json.dumps(parameters) if parameters else None))
        self.conn.commit()
        return cursor.lastrowid

    def get_best_strategies(self, metric: str = 'sharpe_ratio', limit: int = 10) -> List[Dict]:
        """Get top performing strategies by metric"""
        cursor = self.conn.cursor()

        # Get latest backtest result for each strategy
        cursor.execute(f'''
            SELECT s.*, MAX(b.{metric}) as best_metric
            FROM strategies s
            JOIN backtest_results b ON s.id = b.strategy_id
            GROUP BY s.id
            ORDER BY best_metric DESC
            LIMIT ?
        ''', (limit,))

        return [dict(row) for row in cursor.fetchall()]

    def search_strategies(self, query: str = None, category: str = None,
                         status: str = None, min_rating: int = 0) -> List[Dict]:
        """Search strategies with filters"""
        cursor = self.conn.cursor()

        sql = 'SELECT * FROM strategies WHERE rating >= ?'
        params = [min_rating]

        if query:
            sql += ' AND (name LIKE ? OR description LIKE ?)'
            params.extend([f'%{query}%', f'%{query}%'])

        if category:
            sql += ' AND category = ?'
            params.append(category)

        if status:
            sql += ' AND status = ?'
            params.append(status)

        sql += ' ORDER BY rating DESC, updated_at DESC'

        cursor.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_strategy_statistics(self) -> Dict:
        """Get library statistics"""
        cursor = self.conn.cursor()

        cursor.execute('SELECT COUNT(*) as count FROM strategies')
        total_strategies = cursor.fetchone()['count']

        cursor.execute('SELECT COUNT(*) as count FROM strategies WHERE status = "production"')
        production_strategies = cursor.fetchone()['count']

        cursor.execute('SELECT COUNT(*) as count FROM backtest_results')
        total_backtests = cursor.fetchone()['count']

        cursor.execute('SELECT category, COUNT(*) as count FROM strategies GROUP BY category')
        by_category = {row['category'] or 'uncategorized': row['count']
                      for row in cursor.fetchall()}

        return {
            'total_strategies': total_strategies,
            'production_strategies': production_strategies,
            'total_backtests': total_backtests,
            'by_category': by_category
        }

    def close(self):
        """Close database connection"""
        self.conn.close()


if __name__ == '__main__':
    # Test the system
    library = StrategyLibrary()

    # Add a strategy
    strategy_id = library.add_strategy(
        "NQ Opening Range Breakout",
        description="15-minute opening range breakout strategy for NQ futures",
        category="Breakout",
        timeframe="15m",
        instruments=["NQ", "MNQ"],
        parameters={"entry_minutes": 15, "stop_loss_pct": 1.0, "profit_target_pct": 2.0}
    )

    # Add a backtest result
    library.add_backtest_result(
        strategy_id,
        start_date="2024-01-01",
        end_date="2024-12-31",
        initial_capital=100000,
        final_capital=148000,
        total_return=48.0,
        win_rate=54.0,
        sharpe_ratio=0.93,
        max_drawdown=-21.0,
        total_trades=250
    )

    # Get statistics
    stats = library.get_strategy_statistics()
    print("Strategy Library ready!")
    print(f"\nLibrary Statistics:")
    print(json.dumps(stats, indent=2))

    library.close()
