#!/usr/bin/env python3
"""
15-Minute Opening Range Strategy Backtest
Uses historical NQ data to generate equity curve and performance stats
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, time
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

WORKSPACE = Path(r"C:\Users\User\.openclaw\workspace")

class OpeningRangeBacktest:
    """Backtest 15-minute opening range strategy"""

    def __init__(self, data_file):
        self.data = None
        self.trades = []
        self.equity_curve = []
        self.load_data(data_file)

    def load_data(self, data_file):
        """Load historical trades from CSV"""
        df = pd.read_csv(data_file)

        # Parse dates
        if 'Date and time' in df.columns:
            df['datetime'] = pd.to_datetime(df['Date and time'])
        elif 'Date/Time' in df.columns:
            df['datetime'] = pd.to_datetime(df['Date/Time'])

        self.data = df
        print(f"Loaded {len(df)} trades from {data_file}")

    def filter_opening_range_trades(self):
        """Filter only trades that match 15min opening strategy logic"""

        if self.data is None:
            return []

        # Extract time from datetime
        self.data['time'] = self.data['datetime'].dt.time
        self.data['date'] = self.data['datetime'].dt.date

        # Filter for 9:30-9:45 entries only
        opening_trades = self.data[
            (self.data['time'] >= time(9, 30)) &
            (self.data['time'] <= time(9, 45))
        ].copy()

        # Only one trade per day
        opening_trades = opening_trades.sort_values('datetime')
        opening_trades = opening_trades.groupby('date').first().reset_index()

        print(f"Filtered to {len(opening_trades)} opening range trades (1 per day)")
        return opening_trades

    def calculate_statistics(self, trades_df):
        """Calculate top 5 performance metrics"""

        if len(trades_df) == 0:
            return None

        # PnL calculations
        pnl_values = trades_df['Net P&L USD'].values
        cumulative_pnl = np.cumsum(pnl_values)

        # Total Return
        initial_capital = 100000  # $100k starting capital
        total_return_pct = (cumulative_pnl[-1] / initial_capital) * 100

        # Max Drawdown
        equity = initial_capital + cumulative_pnl
        running_max = np.maximum.accumulate(equity)
        drawdown = (equity - running_max) / running_max * 100
        max_drawdown_pct = abs(drawdown.min())

        # Win Rate
        winning_trades = len(trades_df[trades_df['Net P&L USD'] > 0])
        total_trades = len(trades_df)
        win_rate_pct = (winning_trades / total_trades) * 100

        # Profit Factor
        gross_profit = trades_df[trades_df['Net P&L USD'] > 0]['Net P&L USD'].sum()
        gross_loss = abs(trades_df[trades_df['Net P&L USD'] < 0]['Net P&L USD'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        # Sharpe Ratio (simplified - using trade returns)
        returns = pnl_values / initial_capital
        sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() > 0 else 0

        stats = {
            'Total Return (%)': round(total_return_pct, 2),
            'Max Drawdown (%)': round(max_drawdown_pct, 2),
            'Sharpe Ratio': round(sharpe_ratio, 2),
            'Profit Factor': round(profit_factor, 2),
            'Win Rate (%)': round(win_rate_pct, 2),
            'Total Trades': total_trades,
            'Winning Trades': winning_trades,
            'Losing Trades': total_trades - winning_trades,
            'Total PnL': round(cumulative_pnl[-1], 2),
            'Avg Win': round(trades_df[trades_df['Net P&L USD'] > 0]['Net P&L USD'].mean(), 2),
            'Avg Loss': round(trades_df[trades_df['Net P&L USD'] < 0]['Net P&L USD'].mean(), 2),
        }

        return stats, equity

    def plot_equity_curve(self, equity, trades_df, output_file):
        """Generate equity curve chart"""

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), gridspec_kw={'height_ratios': [3, 1]})

        # Equity Curve
        dates = trades_df['datetime'].values
        ax1.plot(dates, equity, linewidth=2, color='#2E86AB', label='Portfolio Value')
        ax1.axhline(y=100000, color='gray', linestyle='--', linewidth=1, label='Initial Capital')
        ax1.fill_between(dates, 100000, equity, where=(equity >= 100000), alpha=0.3, color='green')
        ax1.fill_between(dates, 100000, equity, where=(equity < 100000), alpha=0.3, color='red')
        ax1.set_ylabel('Portfolio Value ($)', fontsize=12, fontweight='bold')
        ax1.set_title('15-Minute Opening Range Strategy - Equity Curve', fontsize=14, fontweight='bold')
        ax1.legend(loc='upper left')
        ax1.grid(True, alpha=0.3)
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))

        # Drawdown
        running_max = np.maximum.accumulate(equity)
        drawdown_pct = ((equity - running_max) / running_max) * 100
        ax2.fill_between(dates, 0, drawdown_pct, color='red', alpha=0.5)
        ax2.set_ylabel('Drawdown (%)', fontsize=12, fontweight='bold')
        ax2.set_xlabel('Date', fontsize=12, fontweight='bold')
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        print(f"Equity curve saved to: {output_file}")
        plt.close()

    def run_backtest(self):
        """Run complete backtest and generate report"""

        print("\n" + "="*70)
        print("15-MINUTE OPENING RANGE STRATEGY BACKTEST")
        print("="*70 + "\n")

        # Filter trades
        trades = self.filter_opening_range_trades()

        if len(trades) == 0:
            print("No trades found matching criteria!")
            return

        # Calculate stats
        stats, equity = self.calculate_statistics(trades)

        # Print results
        print("\nTOP 5 PERFORMANCE METRICS:")
        print("-" * 70)
        print(f"  Total Return:     {stats['Total Return (%)']}%")
        print(f"  Max Drawdown:     {stats['Max Drawdown (%)']}%")
        print(f"  Sharpe Ratio:     {stats['Sharpe Ratio']}")
        print(f"  Profit Factor:    {stats['Profit Factor']}")
        print(f"  Win Rate:         {stats['Win Rate (%)']}%")
        print("-" * 70)

        print("\nADDITIONAL METRICS:")
        print(f"  Total Trades:     {stats['Total Trades']}")
        print(f"  Winning Trades:   {stats['Winning Trades']}")
        print(f"  Losing Trades:    {stats['Losing Trades']}")
        print(f"  Total PnL:        ${stats['Total PnL']:,.2f}")
        print(f"  Avg Win:          ${stats['Avg Win']:,.2f}")
        print(f"  Avg Loss:         ${stats['Avg Loss']:,.2f}")

        # Generate equity curve
        output_file = WORKSPACE / "15min_opening_strategy_equity_curve.png"
        self.plot_equity_curve(equity, trades, output_file)

        # Save detailed report
        report_file = WORKSPACE / "15min_opening_strategy_backtest_report.txt"
        with open(report_file, 'w') as f:
            f.write("15-MINUTE OPENING RANGE STRATEGY BACKTEST REPORT\n")
            f.write("="*70 + "\n\n")
            f.write(f"Backtest Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Data Period: {trades['datetime'].min()} to {trades['datetime'].max()}\n\n")

            f.write("TOP 5 PERFORMANCE METRICS:\n")
            f.write("-"*70 + "\n")
            for key in ['Total Return (%)', 'Max Drawdown (%)', 'Sharpe Ratio', 'Profit Factor', 'Win Rate (%)']:
                f.write(f"  {key:20s} {stats[key]}\n")

            f.write("\nADDITIONAL METRICS:\n")
            f.write("-"*70 + "\n")
            for key, value in stats.items():
                if key not in ['Total Return (%)', 'Max Drawdown (%)', 'Sharpe Ratio', 'Profit Factor', 'Win Rate (%)']:
                    f.write(f"  {key:20s} {value}\n")

        print(f"\nReport saved to: {report_file}")
        print("\n" + "="*70)
        print("BACKTEST COMPLETE")
        print("="*70 + "\n")

        return stats, equity


if __name__ == "__main__":
    # Use the Triple NQ data as proxy for now
    data_file = Path(r"C:\Users\User\Downloads\Triple_NQ_Variant_[Trend_+_ORB_+_Short]_%_Scaling_CME_MINI_NQ1!_2026-01-21.csv")

    if not data_file.exists():
        print(f"Data file not found: {data_file}")
        print("Please run this strategy on TradingView to get 15 years of backtest data")
    else:
        backtest = OpeningRangeBacktest(data_file)
        backtest.run_backtest()
