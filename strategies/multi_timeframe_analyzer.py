#!/usr/bin/env python3
"""Multi-Timeframe Analyzer (#19) - Analyze across multiple timeframes"""
import sys
from pathlib import Path
from typing import Dict, List
import numpy as np

sys.path.append(str(Path(__file__).parent.parent))

class MultiTimeframeAnalyzer:
    """Analyze market data across multiple timeframes"""

    def __init__(self):
        self.timeframes = ['1m', '5m', '15m', '1h', '4h', 'D']

    def analyze_trend_alignment(self, data_by_timeframe: Dict[str, List[float]]) -> Dict:
        """Check if trends align across timeframes"""
        trends = {}

        for tf, prices in data_by_timeframe.items():
            if len(prices) < 20:
                trends[tf] = 'unknown'
                continue

            # Simple trend detection
            ma_short = np.mean(prices[-10:])
            ma_long = np.mean(prices[-20:])

            if ma_short > ma_long * 1.01:
                trends[tf] = 'uptrend'
            elif ma_short < ma_long * 0.99:
                trends[tf] = 'downtrend'
            else:
                trends[tf] = 'sideways'

        # Check alignment
        uptrends = sum(1 for t in trends.values() if t == 'uptrend')
        downtrends = sum(1 for t in trends.values() if t == 'downtrend')
        total = len(trends)

        if uptrends / total >= 0.7:
            alignment = 'strongly_bullish'
        elif downtrends / total >= 0.7:
            alignment = 'strongly_bearish'
        elif uptrends > downtrends:
            alignment = 'weakly_bullish'
        elif downtrends > uptrends:
            alignment = 'weakly_bearish'
        else:
            alignment = 'mixed'

        return {
            'trends': trends,
            'alignment': alignment,
            'uptrends': uptrends,
            'downtrends': downtrends
        }

    def find_support_resistance(self, data_by_timeframe: Dict[str, List[float]]) -> Dict:
        """Find support/resistance levels across timeframes"""
        levels = {'support': [], 'resistance': []}

        for tf, prices in data_by_timeframe.items():
            if len(prices) < 50:
                continue

            # Find local maxima (resistance)
            for i in range(10, len(prices) - 10):
                if prices[i] == max(prices[i-10:i+10]):
                    levels['resistance'].append(prices[i])

            # Find local minima (support)
            for i in range(10, len(prices) - 10):
                if prices[i] == min(prices[i-10:i+10]):
                    levels['support'].append(prices[i])

        # Cluster similar levels
        levels['support'] = self._cluster_levels(levels['support'])
        levels['resistance'] = self._cluster_levels(levels['resistance'])

        return levels

    def _cluster_levels(self, levels: List[float], threshold: float = 10) -> List[float]:
        """Cluster similar price levels"""
        if not levels:
            return []

        levels = sorted(levels)
        clusters = []
        current_cluster = [levels[0]]

        for level in levels[1:]:
            if level - current_cluster[-1] < threshold:
                current_cluster.append(level)
            else:
                clusters.append(np.mean(current_cluster))
                current_cluster = [level]

        if current_cluster:
            clusters.append(np.mean(current_cluster))

        return clusters

    def check_confluence(self, price: float, data_by_timeframe: Dict[str, List[float]]) -> Dict:
        """Check for confluence at a price level"""
        levels = self.find_support_resistance(data_by_timeframe)

        support_hits = sum(1 for s in levels['support'] if abs(price - s) < 10)
        resistance_hits = sum(1 for r in levels['resistance'] if abs(price - r) < 10)

        return {
            'price': price,
            'support_hits': support_hits,
            'resistance_hits': resistance_hits,
            'confluence_strength': support_hits + resistance_hits,
            'is_strong_level': (support_hits + resistance_hits) >= 2
        }

    def get_higher_timeframe_bias(self, data_by_timeframe: Dict[str, List[float]],
                                 current_tf: str = '15m') -> str:
        """Get bias from higher timeframes"""
        # Define timeframe hierarchy
        tf_hierarchy = ['1m', '5m', '15m', '1h', '4h', 'D']

        if current_tf not in tf_hierarchy:
            return 'unknown'

        current_idx = tf_hierarchy.index(current_tf)
        higher_tfs = tf_hierarchy[current_idx + 1:]

        bullish_count = 0
        bearish_count = 0

        for tf in higher_tfs:
            if tf not in data_by_timeframe:
                continue

            prices = data_by_timeframe[tf]
            if len(prices) < 20:
                continue

            ma = np.mean(prices[-20:])
            current_price = prices[-1]

            if current_price > ma:
                bullish_count += 1
            elif current_price < ma:
                bearish_count += 1

        if bullish_count > bearish_count:
            return 'bullish'
        elif bearish_count > bullish_count:
            return 'bearish'
        else:
            return 'neutral'


if __name__ == '__main__':
    # Test the system
    analyzer = MultiTimeframeAnalyzer()

    print("Multi-Timeframe Analyzer ready!")

    # Generate sample data for multiple timeframes
    print("\nGenerating sample data...")
    data = {}
    base = 16500

    for i, tf in enumerate(['1m', '5m', '15m', '1h', '4h']):
        # Generate trending data
        trend = i * 0.1
        data[tf] = [base + j * trend + np.random.randn() * 5 for j in range(100)]

    # Analyze trend alignment
    print("\nAnalyzing trend alignment...")
    alignment = analyzer.analyze_trend_alignment(data)
    print(f"  Overall alignment: {alignment['alignment']}")
    print(f"  Uptrends: {alignment['uptrends']}, Downtrends: {alignment['downtrends']}")
    for tf, trend in alignment['trends'].items():
        print(f"    {tf}: {trend}")

    # Find support/resistance
    print("\nFinding support/resistance levels...")
    levels = analyzer.find_support_resistance(data)
    print(f"  Support levels: {len(levels['support'])}")
    print(f"  Resistance levels: {len(levels['resistance'])}")

    # Check confluence
    print("\nChecking confluence at current price...")
    current_price = data['15m'][-1]
    confluence = analyzer.check_confluence(current_price, data)
    print(f"  Price: {confluence['price']:.2f}")
    print(f"  Confluence strength: {confluence['confluence_strength']}")
    print(f"  Strong level: {confluence['is_strong_level']}")

    # Get higher timeframe bias
    print("\nGetting higher timeframe bias...")
    bias = analyzer.get_higher_timeframe_bias(data, current_tf='15m')
    print(f"  HTF bias: {bias}")
