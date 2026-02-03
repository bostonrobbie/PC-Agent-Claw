#!/usr/bin/env python3
"""Paper Trading Tracker (#11) - Track simulated trades and performance"""
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import json
import sys

sys.path.append(str(Path(__file__).parent.parent))

class PaperTradingTracker:
    def __init__(self, db_path: str = None):
        if db_path is None:
            workspace = Path(__file__).parent.parent
            db_path = str(workspace / "paper_trading.db")

        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        """Initialize database schema"""
        cursor = self.conn.cursor()

        # Accounts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                initial_balance REAL NOT NULL,
                current_balance REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Trades table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity REAL NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL,
                entry_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                exit_time TIMESTAMP,
                status TEXT DEFAULT 'open',
                strategy TEXT,
                pnl REAL,
                pnl_percent REAL,
                commission REAL DEFAULT 0,
                notes TEXT,
                FOREIGN KEY (account_id) REFERENCES accounts (id)
            )
        ''')

        # Performance metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                date DATE NOT NULL,
                balance REAL NOT NULL,
                daily_pnl REAL,
                daily_return REAL,
                trades_count INTEGER,
                win_count INTEGER,
                loss_count INTEGER,
                FOREIGN KEY (account_id) REFERENCES accounts (id)
            )
        ''')

        self.conn.commit()

    def create_account(self, name: str, initial_balance: float) -> int:
        """Create a paper trading account"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO accounts (name, initial_balance, current_balance)
            VALUES (?, ?, ?)
        ''', (name, initial_balance, initial_balance))
        self.conn.commit()
        return cursor.lastrowid

    def open_trade(self, account_id: int, symbol: str, side: str, quantity: float,
                   entry_price: float, strategy: str = None, notes: str = None) -> int:
        """Open a new trade"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO trades (account_id, symbol, side, quantity, entry_price, strategy, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (account_id, symbol, side, quantity, entry_price, strategy, notes))
        self.conn.commit()
        return cursor.lastrowid

    def close_trade(self, trade_id: int, exit_price: float, commission: float = 0):
        """Close an existing trade"""
        cursor = self.conn.cursor()

        # Get trade details
        cursor.execute('SELECT * FROM trades WHERE id = ?', (trade_id,))
        trade = cursor.fetchone()

        if not trade or trade['status'] != 'open':
            return False

        # Calculate P&L
        if trade['side'].lower() == 'long':
            pnl = (exit_price - trade['entry_price']) * trade['quantity'] - commission
        else:  # short
            pnl = (trade['entry_price'] - exit_price) * trade['quantity'] - commission

        pnl_percent = (pnl / (trade['entry_price'] * trade['quantity'])) * 100

        # Update trade
        cursor.execute('''
            UPDATE trades
            SET exit_price = ?, exit_time = CURRENT_TIMESTAMP, status = 'closed',
                pnl = ?, pnl_percent = ?, commission = ?
            WHERE id = ?
        ''', (exit_price, pnl, pnl_percent, commission, trade_id))

        # Update account balance
        cursor.execute('''
            UPDATE accounts
            SET current_balance = current_balance + ?
            WHERE id = ?
        ''', (pnl, trade['account_id']))

        self.conn.commit()
        return True

    def get_open_trades(self, account_id: int = None) -> List[Dict]:
        """Get all open trades"""
        cursor = self.conn.cursor()

        if account_id:
            cursor.execute('''
                SELECT * FROM trades
                WHERE status = 'open' AND account_id = ?
                ORDER BY entry_time DESC
            ''', (account_id,))
        else:
            cursor.execute('''
                SELECT * FROM trades
                WHERE status = 'open'
                ORDER BY entry_time DESC
            ''')

        return [dict(row) for row in cursor.fetchall()]

    def get_account_performance(self, account_id: int) -> Dict:
        """Get account performance statistics"""
        cursor = self.conn.cursor()

        # Get account info
        cursor.execute('SELECT * FROM accounts WHERE id = ?', (account_id,))
        account = cursor.fetchone()

        if not account:
            return {}

        # Get all closed trades
        cursor.execute('''
            SELECT * FROM trades
            WHERE account_id = ? AND status = 'closed'
            ORDER BY exit_time DESC
        ''', (account_id,))
        closed_trades = [dict(row) for row in cursor.fetchall()]

        # Calculate metrics
        total_trades = len(closed_trades)
        winning_trades = [t for t in closed_trades if t['pnl'] > 0]
        losing_trades = [t for t in closed_trades if t['pnl'] < 0]

        total_pnl = sum(t['pnl'] for t in closed_trades)
        total_return = ((account['current_balance'] - account['initial_balance']) / account['initial_balance']) * 100

        win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0
        avg_win = sum(t['pnl'] for t in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = sum(t['pnl'] for t in losing_trades) / len(losing_trades) if losing_trades else 0

        return {
            'account_name': account['name'],
            'initial_balance': account['initial_balance'],
            'current_balance': account['current_balance'],
            'total_pnl': round(total_pnl, 2),
            'total_return_pct': round(total_return, 2),
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': round(win_rate, 2),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'profit_factor': round(abs(avg_win / avg_loss), 2) if avg_loss != 0 else 0
        }

    def get_strategy_performance(self, strategy: str) -> Dict:
        """Get performance for a specific strategy"""
        cursor = self.conn.cursor()

        cursor.execute('''
            SELECT * FROM trades
            WHERE strategy = ? AND status = 'closed'
        ''', (strategy,))

        trades = [dict(row) for row in cursor.fetchall()]

        if not trades:
            return {}

        total_pnl = sum(t['pnl'] for t in trades)
        winning_trades = [t for t in trades if t['pnl'] > 0]
        win_rate = (len(winning_trades) / len(trades)) * 100

        return {
            'strategy': strategy,
            'total_trades': len(trades),
            'total_pnl': round(total_pnl, 2),
            'win_rate': round(win_rate, 2),
            'avg_pnl_per_trade': round(total_pnl / len(trades), 2)
        }

    def close(self):
        """Close database connection"""
        self.conn.close()


if __name__ == '__main__':
    # Test the system
    tracker = PaperTradingTracker()

    # Create account
    account_id = tracker.create_account("Test Account", 100000.0)
    print(f"Created account: {account_id}")

    # Open some trades
    trade1 = tracker.open_trade(account_id, "NQ", "long", 1, 16500.0, "Opening Range")
    trade2 = tracker.open_trade(account_id, "ES", "long", 2, 4800.0, "Opening Range")

    # Close a trade
    tracker.close_trade(trade1, 16550.0, 4.16)

    # Get performance
    performance = tracker.get_account_performance(account_id)
    print("\nAccount Performance:")
    print(json.dumps(performance, indent=2))

    # Get open trades
    open_trades = tracker.get_open_trades(account_id)
    print(f"\nOpen trades: {len(open_trades)}")

    tracker.close()
    print("\nPaper Trading Tracker ready!")
