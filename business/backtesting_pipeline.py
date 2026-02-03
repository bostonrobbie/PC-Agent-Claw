#!/usr/bin/env python3
"""Backtesting Pipeline (#9) - Automated strategy backtesting"""
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Callable
from datetime import datetime
import json
import sys

sys.path.append(str(Path(__file__).parent.parent))

from core.persistent_memory import PersistentMemory

class BacktestingPipeline:
    """Pipeline for backtesting trading strategies"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            workspace = Path(__file__).parent.parent
            db_path = str(workspace / "memory.db")

        self.memory = PersistentMemory(db_path)
        self.results_history: List[Dict] = []

    def backtest_strategy(self, strategy_name: str, strategy_func: Callable,
                         data: pd.DataFrame, initial_capital: float = 100000,
                         commission: float = 0.0, slippage: float = 0.0) -> Dict:
        """
        Run a backtest on a strategy

        Args:
            strategy_name: Name of the strategy
            strategy_func: Function that generates signals (1 for long, -1 for short, 0 for flat)
            data: DataFrame with OHLCV data
            initial_capital: Starting capital
            commission: Commission per trade (as decimal, e.g., 0.001 for 0.1%)
            slippage: Slippage per trade (as decimal)
        """
        start_time = datetime.now()

        # Generate signals
        signals = strategy_func(data)

        # Initialize tracking
        capital = initial_capital
        position = 0
        entry_price = 0
        trades = []
        equity_curve = [initial_capital]

        # Run backtest
        for i in range(1, len(data)):
            current_price = data.iloc[i]['Close']
            signal = signals.iloc[i] if i < len(signals) else 0

            # Check for position changes
            if signal != position:
                # Close existing position
                if position != 0:
                    exit_price = current_price * (1 - slippage if position > 0 else 1 + slippage)
                    pnl = (exit_price - entry_price) * position
                    capital += pnl - abs(commission * exit_price)

                    trades.append({
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'pnl': pnl,
                        'side': 'long' if position > 0 else 'short',
                        'exit_time': data.index[i]
                    })

                # Open new position
                if signal != 0:
                    entry_price = current_price * (1 + slippage if signal > 0 else 1 - slippage)
                    entry_price += abs(commission * entry_price)

                position = signal

            equity_curve.append(capital)

        # Close final position if open
        if position != 0:
            exit_price = data.iloc[-1]['Close']
            pnl = (exit_price - entry_price) * position
            capital += pnl
            trades.append({
                'entry_price': entry_price,
                'exit_price': exit_price,
                'pnl': pnl,
                'side': 'long' if position > 0 else 'short',
                'exit_time': data.index[-1]
            })

        # Calculate metrics
        total_return = ((capital - initial_capital) / initial_capital) * 100
        winning_trades = [t for t in trades if t['pnl'] > 0]
        losing_trades = [t for t in trades if t['pnl'] < 0]

        win_rate = (len(winning_trades) / len(trades) * 100) if trades else 0
        avg_win = sum(t['pnl'] for t in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = sum(t['pnl'] for t in losing_trades) / len(losing_trades) if losing_trades else 0

        # Calculate max drawdown
        equity_series = pd.Series(equity_curve)
        cummax = equity_series.cummax()
        drawdown = (equity_series - cummax) / cummax * 100
        max_drawdown = drawdown.min()

        # Calculate Sharpe ratio (simplified, assuming daily data)
        returns = equity_series.pct_change().dropna()
        sharpe = (returns.mean() / returns.std() * (252 ** 0.5)) if returns.std() > 0 else 0

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        results = {
            'strategy_name': strategy_name,
            'initial_capital': initial_capital,
            'final_capital': capital,
            'total_return_pct': round(total_return, 2),
            'total_trades': len(trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': round(win_rate, 2),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'profit_factor': round(abs(avg_win / avg_loss), 2) if avg_loss != 0 else 0,
            'max_drawdown': round(max_drawdown, 2),
            'sharpe_ratio': round(sharpe, 2),
            'backtest_duration': round(duration, 2),
            'timestamp': start_time.isoformat()
        }

        # Save to memory
        self.memory.log_decision(
            f'Backtest completed: {strategy_name}',
            f'Return: {total_return:.2f}%, Win rate: {win_rate:.2f}%, Sharpe: {sharpe:.2f}',
            tags=['backtest', strategy_name, 'completed']
        )

        self.results_history.append(results)

        return results

    def compare_strategies(self, results: List[Dict]) -> pd.DataFrame:
        """Compare multiple backtest results"""
        df = pd.DataFrame(results)

        # Sort by Sharpe ratio
        df = df.sort_values('sharpe_ratio', ascending=False)

        return df

    def save_results(self, results: Dict, filename: str = None):
        """Save backtest results to file"""
        if filename is None:
            workspace = Path(__file__).parent.parent
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = workspace / f"backtest_{results['strategy_name']}_{timestamp}.json"

        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)

        return filename


# Example strategy function
def simple_moving_average_strategy(data: pd.DataFrame, fast_period: int = 10, slow_period: int = 30):
    """Simple moving average crossover strategy"""
    fast_ma = data['Close'].rolling(window=fast_period).mean()
    slow_ma = data['Close'].rolling(window=slow_period).mean()

    signals = pd.Series(0, index=data.index)
    signals[fast_ma > slow_ma] = 1  # Long
    signals[fast_ma < slow_ma] = -1  # Short

    return signals


if __name__ == '__main__':
    # Test with sample data
    print("Backtesting Pipeline ready!")

    # Create sample data
    dates = pd.date_range('2024-01-01', periods=100)
    sample_data = pd.DataFrame({
        'Close': 100 + pd.Series(range(100)).apply(lambda x: x * 0.5 + (x % 10) * 2)
    }, index=dates)

    # Run backtest
    pipeline = BacktestingPipeline()
    results = pipeline.backtest_strategy(
        'Simple MA Crossover',
        simple_moving_average_strategy,
        sample_data,
        initial_capital=100000
    )

    print("\nBacktest Results:")
    print(json.dumps(results, indent=2))
