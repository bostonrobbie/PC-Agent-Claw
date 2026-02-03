#!/usr/bin/env python3
"""Trade Scheduler (#17) - Schedule and execute trades at optimal times"""
import sys
from pathlib import Path
from typing import Dict, List, Callable
from datetime import datetime, timedelta
import time
import threading

sys.path.append(str(Path(__file__).parent.parent))

from core.persistent_memory import PersistentMemory

class TradeScheduler:
    """Schedule trades to execute at specific times"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            workspace = Path(__file__).parent.parent
            db_path = str(workspace / "memory.db")

        self.memory = PersistentMemory(db_path)
        self.scheduled_trades: List[Dict] = []
        self.running = False
        self.thread = None

    def schedule_trade(self, execute_at: datetime, trade_func: Callable,
                      symbol: str, **trade_params) -> int:
        """Schedule a trade to execute at a specific time"""
        trade = {
            'id': len(self.scheduled_trades) + 1,
            'execute_at': execute_at,
            'trade_func': trade_func,
            'symbol': symbol,
            'params': trade_params,
            'status': 'scheduled'
        }

        self.scheduled_trades.append(trade)

        self.memory.log_decision(
            f'Trade scheduled: {symbol}',
            f'Execute at: {execute_at.isoformat()}, Params: {trade_params}',
            tags=['trade_scheduler', 'scheduled', symbol]
        )

        return trade['id']

    def schedule_market_on_open(self, trade_func: Callable, symbol: str,
                               market_open_time: str = '09:30', **trade_params) -> int:
        """Schedule trade for market open"""
        now = datetime.now()
        hour, minute = map(int, market_open_time.split(':'))

        execute_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        # If time has passed today, schedule for tomorrow
        if execute_time < now:
            execute_time += timedelta(days=1)

        return self.schedule_trade(execute_time, trade_func, symbol, **trade_params)

    def schedule_market_on_close(self, trade_func: Callable, symbol: str,
                                market_close_time: str = '16:00', **trade_params) -> int:
        """Schedule trade for market close"""
        return self.schedule_market_on_open(trade_func, symbol, market_close_time, **trade_params)

    def schedule_after_delay(self, delay_seconds: int, trade_func: Callable,
                           symbol: str, **trade_params) -> int:
        """Schedule trade after a delay"""
        execute_time = datetime.now() + timedelta(seconds=delay_seconds)
        return self.schedule_trade(execute_time, trade_func, symbol, **trade_params)

    def cancel_trade(self, trade_id: int) -> bool:
        """Cancel a scheduled trade"""
        for trade in self.scheduled_trades:
            if trade['id'] == trade_id and trade['status'] == 'scheduled':
                trade['status'] = 'cancelled'

                self.memory.log_decision(
                    f'Trade cancelled: {trade["symbol"]}',
                    f'Trade ID: {trade_id}',
                    tags=['trade_scheduler', 'cancelled', trade['symbol']]
                )

                return True

        return False

    def start(self):
        """Start the scheduler"""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.thread.start()

        self.memory.log_decision(
            'Trade scheduler started',
            f'Monitoring {len([t for t in self.scheduled_trades if t["status"] == "scheduled"])} trades',
            tags=['trade_scheduler', 'start']
        )

    def stop(self):
        """Stop the scheduler"""
        self.running = False

        self.memory.log_decision(
            'Trade scheduler stopped',
            '',
            tags=['trade_scheduler', 'stop']
        )

    def _scheduler_loop(self):
        """Main scheduler loop"""
        while self.running:
            now = datetime.now()

            for trade in self.scheduled_trades:
                if trade['status'] == 'scheduled' and now >= trade['execute_at']:
                    self._execute_trade(trade)

            time.sleep(1)  # Check every second

    def _execute_trade(self, trade: Dict):
        """Execute a scheduled trade"""
        try:
            # Execute the trade function
            result = trade['trade_func'](**trade['params'])

            trade['status'] = 'executed'
            trade['executed_at'] = datetime.now()
            trade['result'] = result

            self.memory.log_decision(
                f'Trade executed: {trade["symbol"]}',
                f'Trade ID: {trade["id"]}, Result: {result}',
                tags=['trade_scheduler', 'executed', trade['symbol']]
            )

        except Exception as e:
            trade['status'] = 'failed'
            trade['error'] = str(e)

            self.memory.log_decision(
                f'Trade execution failed: {trade["symbol"]}',
                f'Trade ID: {trade["id"]}, Error: {str(e)}',
                tags=['trade_scheduler', 'failed', trade['symbol']]
            )

    def get_scheduled_trades(self, status: str = None) -> List[Dict]:
        """Get list of scheduled trades"""
        if status:
            return [t for t in self.scheduled_trades if t['status'] == status]

        return self.scheduled_trades


# Example trade functions
def example_buy_trade(symbol: str, quantity: int, price: float = None):
    """Example buy trade function"""
    print(f"Executing BUY {quantity} {symbol} @ {price or 'MARKET'}")
    return f"ORDER_BUY_{symbol}"

def example_sell_trade(symbol: str, quantity: int, price: float = None):
    """Example sell trade function"""
    print(f"Executing SELL {quantity} {symbol} @ {price or 'MARKET'}")
    return f"ORDER_SELL_{symbol}"


if __name__ == '__main__':
    # Test the system
    scheduler = TradeScheduler()

    print("Trade Scheduler ready!")

    # Schedule some trades
    print("\nScheduling trades...")

    # Schedule for 5 seconds from now
    trade_id1 = scheduler.schedule_after_delay(
        5,
        example_buy_trade,
        'NQ',
        quantity=2,
        price=16500
    )
    print(f"  Scheduled trade {trade_id1} for 5 seconds from now")

    # Schedule for market open tomorrow
    trade_id2 = scheduler.schedule_market_on_open(
        example_buy_trade,
        'ES',
        quantity=1
    )
    print(f"  Scheduled trade {trade_id2} for market open")

    # Start scheduler
    scheduler.start()

    # Wait and show status
    print("\nScheduler running. Waiting for execution...")
    time.sleep(10)

    # Show results
    executed = scheduler.get_scheduled_trades(status='executed')
    print(f"\nExecuted trades: {len(executed)}")

    scheduler.stop()
