#!/usr/bin/env python3
"""Market Condition Detector (#13) - Identify market regimes and conditions"""
import sys
from pathlib import Path
from typing import Dict, List
import numpy as np

sys.path.append(str(Path(__file__).parent.parent))

from core.persistent_memory import PersistentMemory

class MarketConditionDetector:
    """Detect market conditions and regimes"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            workspace = Path(__file__).parent.parent
            db_path = str(workspace / "memory.db")

        self.memory = PersistentMemory(db_path)

    def detect_volatility_regime(self, prices: List[float], window: int = 20) -> str:
        """Detect volatility regime (low, medium, high)"""
        if len(prices) < window + 1:
            return 'unknown'

        # Calculate returns
        returns = np.diff(prices) / prices[:-1]

        # Calculate rolling volatility
        volatility = np.std(returns[-window:])

        # Define thresholds (these would be calibrated)
        if volatility < 0.01:
            regime = 'low'
        elif volatility < 0.02:
            regime = 'medium'
        else:
            regime = 'high'

        self.memory.log_decision(
            f'Volatility regime detected: {regime}',
            f'Volatility: {volatility:.4f}, Window: {window}',
            tags=['market_condition', 'volatility', regime]
        )

        return regime

    def detect_trend(self, prices: List[float], short_period: int = 10, long_period: int = 50) -> str:
        """Detect trend direction (uptrend, downtrend, sideways)"""
        if len(prices) < long_period:
            return 'unknown'

        short_ma = np.mean(prices[-short_period:])
        long_ma = np.mean(prices[-long_period:])

        if short_ma > long_ma * 1.01:
            trend = 'uptrend'
        elif short_ma < long_ma * 0.99:
            trend = 'downtrend'
        else:
            trend = 'sideways'

        self.memory.log_decision(
            f'Trend detected: {trend}',
            f'Short MA: {short_ma:.2f}, Long MA: {long_ma:.2f}',
            tags=['market_condition', 'trend', trend]
        )

        return trend

    def detect_market_phase(self, prices: List[float]) -> str:
        """Detect market phase (accumulation, markup, distribution, markdown)"""
        if len(prices) < 50:
            return 'unknown'

        # Simple phase detection based on price action
        recent_prices = prices[-20:]
        older_prices = prices[-50:-30]

        recent_avg = np.mean(recent_prices)
        older_avg = np.mean(older_prices)
        recent_vol = np.std(recent_prices)

        if recent_avg > older_avg and recent_vol < np.std(older_prices):
            phase = 'markup'
        elif recent_avg < older_avg and recent_vol < np.std(older_prices):
            phase = 'markdown'
        elif recent_vol > np.std(older_prices) * 1.5:
            phase = 'distribution' if recent_avg > older_avg else 'accumulation'
        else:
            phase = 'consolidation'

        self.memory.log_decision(
            f'Market phase detected: {phase}',
            f'Recent avg: {recent_avg:.2f}, Older avg: {older_avg:.2f}',
            tags=['market_condition', 'phase', phase]
        )

        return phase

    def detect_session(self, hour: int) -> str:
        """Detect trading session (asian, london, nyc, after_hours)"""
        # EST times
        if 18 <= hour or hour < 2:
            session = 'asian'
        elif 2 <= hour < 8:
            session = 'london'
        elif 8 <= hour < 16:
            session = 'nyc'
        else:
            session = 'after_hours'

        return session

    def analyze_conditions(self, prices: List[float], hour: int) -> Dict:
        """Comprehensive market condition analysis"""
        conditions = {
            'volatility_regime': self.detect_volatility_regime(prices),
            'trend': self.detect_trend(prices),
            'market_phase': self.detect_market_phase(prices),
            'session': self.detect_session(hour),
            'timestamp': hour
        }

        self.memory.log_decision(
            'Market conditions analyzed',
            f'Volatility: {conditions["volatility_regime"]}, Trend: {conditions["trend"]}, '
            f'Phase: {conditions["market_phase"]}, Session: {conditions["session"]}',
            tags=['market_condition', 'analysis']
        )

        return conditions


if __name__ == '__main__':
    # Test the system
    detector = MarketConditionDetector()

    # Generate sample price data
    prices = [100 + i * 0.5 + np.random.randn() * 2 for i in range(100)]

    print("Market Condition Detector ready!")

    # Detect conditions
    print("\nAnalyzing market conditions...")
    conditions = detector.analyze_conditions(prices, hour=10)

    print(f"  Volatility regime: {conditions['volatility_regime']}")
    print(f"  Trend: {conditions['trend']}")
    print(f"  Market phase: {conditions['market_phase']}")
    print(f"  Session: {conditions['session']}")
