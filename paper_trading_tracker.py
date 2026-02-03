#!/usr/bin/env python3
"""
Paper Trading Tracker - 15min Opening Range Strategy
Tracks live trades and compares to backtest expectations
"""

import json
import csv
from pathlib import Path
from datetime import datetime, time
from task_status_notifier import TaskStatusNotifier

WORKSPACE = Path(r"C:\Users\User\.openclaw\workspace")

class PaperTradingTracker:
    """Track paper trades and validate strategy performance"""

    def __init__(self):
        self.trades_file = WORKSPACE / "paper_trades_15min_OR.json"
        self.trades = self.load_trades()
        self.notifier = TaskStatusNotifier()

        # Backtest benchmarks for comparison
        self.backtest_benchmarks = {
            'win_rate': 53.6,
            'avg_win': 1038,
            'avg_loss': -985,
            'profit_factor': 1.22,
            'sharpe_ratio': 0.93
        }

    def load_trades(self):
        """Load existing paper trades"""
        if self.trades_file.exists():
            with open(self.trades_file, 'r') as f:
                return json.load(f)
        return []

    def save_trades(self):
        """Save trades to file"""
        with open(self.trades_file, 'w') as f:
            json.dump(self.trades, f, indent=2)

    def log_opening_range(self, date, or_high, or_low):
        """Log the opening range for the day"""
        trade = {
            'date': date,
            'or_high': or_high,
            'or_low': or_low,
            'entry_time': None,
            'entry_price': None,
            'direction': None,
            'exit_time': None,
            'exit_price': None,
            'pnl': None,
            'status': 'waiting_for_entry'
        }

        self.trades.append(trade)
        self.save_trades()

        print(f"\n{'='*70}")
        print(f"OPENING RANGE LOGGED - {date}")
        print(f"{'='*70}")
        print(f"High: ${or_high}")
        print(f"Low:  ${or_low}")
        print(f"Range Width: ${or_high - or_low}")
        print(f"\nWaiting for breakout (9:35-9:45)...")
        print(f"{'='*70}\n")

    def log_entry(self, date, direction, entry_price, entry_time):
        """Log trade entry"""
        # Find today's trade
        for trade in self.trades:
            if trade['date'] == date and trade['status'] == 'waiting_for_entry':
                trade['direction'] = direction
                trade['entry_price'] = entry_price
                trade['entry_time'] = entry_time
                trade['status'] = 'in_position'
                self.save_trades()

                breakout_type = "above OR High" if direction == "LONG" else "below OR Low"

                print(f"\n{'='*70}")
                print(f"TRADE ENTRY - {date} {entry_time}")
                print(f"{'='*70}")
                print(f"Direction: {direction}")
                print(f"Entry Price: ${entry_price}")
                print(f"Breakout: {breakout_type}")
                print(f"\nHolding until 9:45 AM...")
                print(f"{'='*70}\n")

                # Send notification
                self.notifier.task_started(
                    f"Paper Trade: {direction} @ ${entry_price} - Holding until 9:45"
                )
                return True

        return False

    def log_exit(self, date, exit_price, exit_time="9:45"):
        """Log trade exit and calculate PnL"""
        # Find today's trade
        for trade in self.trades:
            if trade['date'] == date and trade['status'] == 'in_position':
                trade['exit_price'] = exit_price
                trade['exit_time'] = exit_time

                # Calculate PnL ($5 per point for NQ)
                if trade['direction'] == 'LONG':
                    pnl = (exit_price - trade['entry_price']) * 5
                else:  # SHORT
                    pnl = (trade['entry_price'] - exit_price) * 5

                trade['pnl'] = pnl
                trade['status'] = 'closed'
                self.save_trades()

                result = "WIN" if pnl > 0 else "LOSS"

                print(f"\n{'='*70}")
                print(f"TRADE EXIT - {date} {exit_time}")
                print(f"{'='*70}")
                print(f"Direction: {trade['direction']}")
                print(f"Entry: ${trade['entry_price']}")
                print(f"Exit:  ${exit_price}")
                print(f"PnL:   ${pnl:.2f} ({result})")
                print(f"{'='*70}\n")

                # Send notification
                self.notifier.task_completed(
                    f"Paper Trade Closed: {result} ${pnl:.2f}",
                    f"Total paper trades: {len([t for t in self.trades if t['status'] == 'closed'])}"
                )

                # Check if we have enough data for analysis
                closed_trades = [t for t in self.trades if t['status'] == 'closed']
                if len(closed_trades) >= 10:
                    self.analyze_performance()

                return True

        return False

    def log_no_trade(self, date, reason="No breakout"):
        """Log days with no trade"""
        trade = {
            'date': date,
            'or_high': None,
            'or_low': None,
            'entry_time': None,
            'entry_price': None,
            'direction': None,
            'exit_time': None,
            'exit_price': None,
            'pnl': 0,
            'status': 'no_trade',
            'reason': reason
        }

        self.trades.append(trade)
        self.save_trades()

        print(f"\n{'='*70}")
        print(f"NO TRADE - {date}")
        print(f"{'='*70}")
        print(f"Reason: {reason}")
        print(f"{'='*70}\n")

    def analyze_performance(self):
        """Analyze paper trading performance vs backtest"""
        closed_trades = [t for t in self.trades if t['status'] == 'closed']

        if len(closed_trades) < 5:
            print("Not enough trades for analysis (need at least 5)")
            return

        # Calculate metrics
        winning_trades = [t for t in closed_trades if t['pnl'] > 0]
        losing_trades = [t for t in closed_trades if t['pnl'] < 0]

        total_trades = len(closed_trades)
        win_rate = (len(winning_trades) / total_trades) * 100

        avg_win = sum(t['pnl'] for t in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = sum(t['pnl'] for t in losing_trades) / len(losing_trades) if losing_trades else 0

        total_profit = sum(t['pnl'] for t in winning_trades)
        total_loss = abs(sum(t['pnl'] for t in losing_trades))
        profit_factor = total_profit / total_loss if total_loss > 0 else 0

        total_pnl = sum(t['pnl'] for t in closed_trades)

        print(f"\n{'='*70}")
        print(f"PAPER TRADING PERFORMANCE ANALYSIS")
        print(f"{'='*70}")
        print(f"\nSample Size: {total_trades} trades")
        print(f"\n{'Metric':<20} {'Paper':<15} {'Backtest':<15} {'Diff':<15}")
        print(f"{'-'*70}")
        print(f"{'Win Rate %':<20} {win_rate:<15.1f} {self.backtest_benchmarks['win_rate']:<15.1f} {win_rate - self.backtest_benchmarks['win_rate']:<15.1f}")
        print(f"{'Avg Win $':<20} {avg_win:<15.2f} {self.backtest_benchmarks['avg_win']:<15.2f} {avg_win - self.backtest_benchmarks['avg_win']:<15.2f}")
        print(f"{'Avg Loss $':<20} {avg_loss:<15.2f} {self.backtest_benchmarks['avg_loss']:<15.2f} {avg_loss - self.backtest_benchmarks['avg_loss']:<15.2f}")
        print(f"{'Profit Factor':<20} {profit_factor:<15.2f} {self.backtest_benchmarks['profit_factor']:<15.2f} {profit_factor - self.backtest_benchmarks['profit_factor']:<15.2f}")
        print(f"{'-'*70}")
        print(f"{'Total PnL $':<20} {total_pnl:<15.2f}")
        print(f"{'='*70}\n")

        # Assessment
        if abs(win_rate - self.backtest_benchmarks['win_rate']) < 10:
            print("✅ Win rate matches backtest (within 10%)")
        else:
            print("⚠️ Win rate differs significantly from backtest")

        if abs(profit_factor - self.backtest_benchmarks['profit_factor']) < 0.3:
            print("✅ Profit factor matches backtest")
        else:
            print("⚠️ Profit factor differs from backtest")

        # Send notification
        self.notifier.send_message(
            f"<b>Paper Trading Update ({total_trades} trades)</b>\n\n"
            f"Win Rate: {win_rate:.1f}% (Backtest: {self.backtest_benchmarks['win_rate']:.1f}%)\n"
            f"Profit Factor: {profit_factor:.2f} (Backtest: {self.backtest_benchmarks['profit_factor']:.2f})\n"
            f"Total PnL: ${total_pnl:.2f}"
        )

    def export_to_csv(self):
        """Export trades to CSV for analysis"""
        csv_file = WORKSPACE / "paper_trades_15min_OR.csv"

        closed_trades = [t for t in self.trades if t['status'] == 'closed']

        with open(csv_file, 'w', newline='') as f:
            fieldnames = ['date', 'direction', 'entry_time', 'entry_price',
                         'exit_time', 'exit_price', 'pnl']
            writer = csv.DictWriter(f, fieldnames=fieldnames)

            writer.writeheader()
            for trade in closed_trades:
                writer.writerow({
                    'date': trade['date'],
                    'direction': trade['direction'],
                    'entry_time': trade['entry_time'],
                    'entry_price': trade['entry_price'],
                    'exit_time': trade['exit_time'],
                    'exit_price': trade['exit_price'],
                    'pnl': trade['pnl']
                })

        print(f"Trades exported to: {csv_file}")


def main():
    """Demo usage"""
    tracker = PaperTradingTracker()

    print("="*70)
    print("PAPER TRADING TRACKER - 15min Opening Range Strategy")
    print("="*70)
    print()
    print("Usage:")
    print("  tracker.log_opening_range('2026-02-03', 19500, 19450)")
    print("  tracker.log_entry('2026-02-03', 'LONG', 19502, '9:37')")
    print("  tracker.log_exit('2026-02-03', 19520, '9:45')")
    print("  tracker.analyze_performance()")
    print()
    print(f"Current trades logged: {len(tracker.trades)}")
    print(f"Closed trades: {len([t for t in tracker.trades if t['status'] == 'closed'])}")
    print()

    if tracker.trades:
        print("Last 5 trades:")
        for trade in tracker.trades[-5:]:
            status = trade['status']
            pnl = trade.get('pnl', 0)
            print(f"  {trade['date']}: {status} - PnL: ${pnl:.2f}" if pnl else f"  {trade['date']}: {status}")


if __name__ == "__main__":
    main()
