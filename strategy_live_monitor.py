#!/usr/bin/env python3
"""
Live Strategy Monitor - 15min Opening Range
Real-time monitoring with Telegram notifications
"""

import time
from datetime import datetime, time as dt_time
from paper_trading_tracker import PaperTradingTracker
from task_status_notifier import TaskStatusNotifier

class StrategyLiveMonitor:
    """Monitor strategy in real-time and send alerts"""

    def __init__(self):
        self.tracker = PaperTradingTracker()
        self.notifier = TaskStatusNotifier()
        self.current_date = None
        self.or_high = None
        self.or_low = None
        self.in_position = False
        self.position_direction = None
        self.entry_price = None

    def check_market_open(self):
        """Check if market is open (9:30-16:00 ET)"""
        now = datetime.now()
        current_time = now.time()

        # Market hours: 9:30 AM - 4:00 PM ET
        market_open = dt_time(9, 30)
        market_close = dt_time(16, 0)

        return market_open <= current_time <= market_close

    def check_trading_window(self):
        """Check if in strategy trading window (9:30-9:45)"""
        now = datetime.now()
        current_time = now.time()

        window_start = dt_time(9, 30)
        window_end = dt_time(9, 45)

        return window_start <= current_time <= window_end

    def morning_setup(self):
        """Send morning setup notification"""
        self.notifier.send_message(
            "<b>🌅 MORNING SETUP - 15min Opening Range</b>\n\n"
            "<b>Today's Plan:</b>\n"
            "1. Wait for 9:30-9:35 bar to close\n"
            "2. Record opening range high/low\n"
            "3. Watch for breakout (9:35-9:45)\n"
            "4. Exit at 9:45 sharp\n\n"
            "<b>Strategy Active</b> ✅"
        )

    def alert_opening_range(self, high, low):
        """Alert when opening range is captured"""
        range_width = high - low

        self.notifier.send_message(
            f"<b>📊 OPENING RANGE CAPTURED</b>\n\n"
            f"<b>High:</b> ${high:.2f}\n"
            f"<b>Low:</b> ${low:.2f}\n"
            f"<b>Range Width:</b> ${range_width:.2f}\n\n"
            f"<b>Watching for breakout...</b>\n"
            f"• Long if breaks above ${high:.2f}\n"
            f"• Short if breaks below ${low:.2f}"
        )

    def alert_entry_signal(self, direction, price):
        """Alert trade entry"""
        self.notifier.send_message(
            f"<b>🚀 TRADE SIGNAL - {direction}</b>\n\n"
            f"<b>Entry Price:</b> ${price:.2f}\n"
            f"<b>Direction:</b> {direction}\n"
            f"<b>Time:</b> {datetime.now().strftime('%H:%M:%S')}\n\n"
            f"<b>Holding until 9:45 AM</b>"
        )

    def alert_exit_signal(self, exit_price, pnl):
        """Alert trade exit"""
        result = "PROFIT" if pnl > 0 else "LOSS"
        emoji = "✅" if pnl > 0 else "❌"

        self.notifier.send_message(
            f"<b>{emoji} TRADE CLOSED - {result}</b>\n\n"
            f"<b>Exit Price:</b> ${exit_price:.2f}\n"
            f"<b>PnL:</b> ${pnl:.2f}\n"
            f"<b>Time:</b> {datetime.now().strftime('%H:%M:%S')}\n\n"
            f"<b>Done for today</b>"
        )

    def alert_no_trade(self, reason="No breakout"):
        """Alert when no trade taken"""
        self.notifier.send_message(
            f"<b>⏸️ NO TRADE TODAY</b>\n\n"
            f"<b>Reason:</b> {reason}\n"
            f"<b>Time:</b> {datetime.now().strftime('%H:%M:%S')}\n\n"
            f"See you tomorrow"
        )

    def pre_market_briefing(self):
        """Send pre-market briefing (8:00 AM)"""
        # Get yesterday's performance
        closed_trades = [t for t in self.tracker.trades if t['status'] == 'closed']
        last_5 = closed_trades[-5:] if len(closed_trades) >= 5 else closed_trades

        recent_pnl = sum(t['pnl'] for t in last_5)
        recent_wins = len([t for t in last_5 if t['pnl'] > 0])

        briefing = (
            "<b>📈 PRE-MARKET BRIEFING</b>\n\n"
            f"<b>Strategy:</b> 15min Opening Range\n"
            f"<b>Trading Window:</b> 9:30-9:45 AM\n\n"
        )

        if closed_trades:
            briefing += (
                f"<b>Last 5 Trades:</b>\n"
                f"• PnL: ${recent_pnl:.2f}\n"
                f"• Wins: {recent_wins}/5\n\n"
            )

        briefing += (
            "<b>Today's Checklist:</b>\n"
            "✅ Watch 9:30-9:35 bar\n"
            "✅ Record high/low\n"
            "✅ Wait for breakout\n"
            "✅ Exit at 9:45\n\n"
            "<b>Ready to trade</b>"
        )

        self.notifier.send_message(briefing)

    def end_of_day_summary(self):
        """Send end of day summary"""
        today = datetime.now().strftime('%Y-%m-%d')
        today_trade = next((t for t in self.tracker.trades if t['date'] == today), None)

        if not today_trade:
            summary = "<b>📊 END OF DAY</b>\n\nNo trade data recorded today"
        elif today_trade['status'] == 'no_trade':
            summary = (
                f"<b>📊 END OF DAY</b>\n\n"
                f"<b>Result:</b> No trade\n"
                f"<b>Reason:</b> {today_trade.get('reason', 'Unknown')}"
            )
        else:
            pnl = today_trade.get('pnl', 0)
            result = "WIN" if pnl > 0 else "LOSS"

            summary = (
                f"<b>📊 END OF DAY</b>\n\n"
                f"<b>Result:</b> {result}\n"
                f"<b>PnL:</b> ${pnl:.2f}\n"
                f"<b>Direction:</b> {today_trade.get('direction', 'N/A')}\n"
                f"<b>Entry:</b> ${today_trade.get('entry_price', 0):.2f}\n"
                f"<b>Exit:</b> ${today_trade.get('exit_price', 0):.2f}"
            )

        # Add running totals
        closed_trades = [t for t in self.tracker.trades if t['status'] == 'closed']
        if closed_trades:
            total_pnl = sum(t['pnl'] for t in closed_trades)
            wins = len([t for t in closed_trades if t['pnl'] > 0])
            total = len(closed_trades)

            summary += (
                f"\n\n<b>Running Totals:</b>\n"
                f"• Total PnL: ${total_pnl:.2f}\n"
                f"• Win Rate: {(wins/total)*100:.1f}%\n"
                f"• Trades: {total}"
            )

        self.notifier.send_message(summary)

    def run_daily_schedule(self):
        """Run the daily monitoring schedule"""
        print("="*70)
        print("STRATEGY LIVE MONITOR - Running")
        print("="*70)
        print()
        print("Schedule:")
        print("  8:00 AM - Pre-market briefing")
        print("  9:25 AM - Morning setup reminder")
        print("  9:30-9:35 - Capture opening range")
        print("  9:35-9:45 - Watch for entry")
        print("  9:45 AM - Force exit if in position")
        print("  4:00 PM - End of day summary")
        print()
        print("Monitoring active. Press Ctrl+C to stop.")
        print("="*70)

        try:
            while True:
                now = datetime.now()
                current_time = now.time()

                # Pre-market briefing (8:00 AM)
                if current_time.hour == 8 and current_time.minute == 0:
                    self.pre_market_briefing()
                    time.sleep(60)  # Wait 1 min to avoid duplicate

                # Morning setup (9:25 AM)
                elif current_time.hour == 9 and current_time.minute == 25:
                    self.morning_setup()
                    time.sleep(60)

                # End of day summary (4:00 PM)
                elif current_time.hour == 16 and current_time.minute == 0:
                    self.end_of_day_summary()
                    time.sleep(60)

                # Sleep and check again
                time.sleep(30)  # Check every 30 seconds

        except KeyboardInterrupt:
            print("\nMonitoring stopped")


def main():
    """Main entry point"""
    monitor = StrategyLiveMonitor()

    print("Strategy Live Monitor")
    print("1. Run daily schedule (automated)")
    print("2. Send test notification")
    print("3. Manual trade entry")

    choice = input("\nChoice (1-3): ")

    if choice == "1":
        monitor.run_daily_schedule()
    elif choice == "2":
        monitor.pre_market_briefing()
        print("Test notification sent!")
    elif choice == "3":
        print("\nManual trade entry:")
        date = input("Date (YYYY-MM-DD): ")
        or_high = float(input("Opening range high: "))
        or_low = float(input("Opening range low: "))
        monitor.tracker.log_opening_range(date, or_high, or_low)

        has_entry = input("Was there an entry? (y/n): ")
        if has_entry.lower() == 'y':
            direction = input("Direction (LONG/SHORT): ").upper()
            entry_price = float(input("Entry price: "))
            entry_time = input("Entry time (HH:MM): ")
            monitor.tracker.log_entry(date, direction, entry_price, entry_time)

            exit_price = float(input("Exit price: "))
            monitor.tracker.log_exit(date, exit_price)
        else:
            reason = input("Reason for no trade: ")
            monitor.tracker.log_no_trade(date, reason)


if __name__ == "__main__":
    main()
