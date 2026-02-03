#!/usr/bin/env python3
"""Correlation Analyzer (#14) - Track correlations between instruments"""
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
import json

sys.path.append(str(Path(__file__).parent.parent))

from core.persistent_memory import PersistentMemory

class CorrelationAnalyzer:
    """Analyze correlations between instruments"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            workspace = Path(__file__).parent.parent
            db_path = str(workspace / "memory.db")

        self.memory = PersistentMemory(db_path)
        self.price_data: Dict[str, List[float]] = {}

    def add_price_data(self, symbol: str, prices: List[float]):
        """Add price data for a symbol"""
        self.price_data[symbol] = prices

    def calculate_correlation(self, symbol1: str, symbol2: str, method: str = 'pearson') -> float:
        """Calculate correlation between two symbols"""
        if symbol1 not in self.price_data or symbol2 not in self.price_data:
            return 0.0

        prices1 = np.array(self.price_data[symbol1])
        prices2 = np.array(self.price_data[symbol2])

        # Ensure same length
        min_len = min(len(prices1), len(prices2))
        prices1 = prices1[-min_len:]
        prices2 = prices2[-min_len:]

        if method == 'pearson':
            correlation = np.corrcoef(prices1, prices2)[0, 1]
        elif method == 'returns':
            # Correlation of returns
            returns1 = np.diff(prices1) / prices1[:-1]
            returns2 = np.diff(prices2) / prices2[:-1]
            correlation = np.corrcoef(returns1, returns2)[0, 1]
        else:
            correlation = 0.0

        self.memory.log_decision(
            f'Correlation calculated: {symbol1} vs {symbol2}',
            f'Method: {method}, Correlation: {correlation:.4f}',
            tags=['correlation', symbol1, symbol2]
        )

        return correlation

    def get_correlation_matrix(self, symbols: List[str] = None) -> Dict:
        """Get correlation matrix for all or specified symbols"""
        if symbols is None:
            symbols = list(self.price_data.keys())

        matrix = {}
        for sym1 in symbols:
            matrix[sym1] = {}
            for sym2 in symbols:
                if sym1 == sym2:
                    matrix[sym1][sym2] = 1.0
                else:
                    matrix[sym1][sym2] = self.calculate_correlation(sym1, sym2)

        return matrix

    def find_correlated_pairs(self, min_correlation: float = 0.7) -> List[Tuple[str, str, float]]:
        """Find highly correlated pairs"""
        pairs = []
        symbols = list(self.price_data.keys())

        for i, sym1 in enumerate(symbols):
            for sym2 in symbols[i+1:]:
                corr = self.calculate_correlation(sym1, sym2)

                if abs(corr) >= min_correlation:
                    pairs.append((sym1, sym2, corr))

        # Sort by absolute correlation
        pairs.sort(key=lambda x: abs(x[2]), reverse=True)

        return pairs

    def detect_divergence(self, symbol1: str, symbol2: str, threshold: float = 0.1) -> bool:
        """Detect if two normally correlated instruments are diverging"""
        if symbol1 not in self.price_data or symbol2 not in self.price_data:
            return False

        # Calculate recent vs historical correlation
        prices1 = self.price_data[symbol1]
        prices2 = self.price_data[symbol2]

        if len(prices1) < 50 or len(prices2) < 50:
            return False

        # Historical correlation (full period)
        hist_corr = self.calculate_correlation(symbol1, symbol2)

        # Recent correlation (last 20 periods)
        recent_prices1 = prices1[-20:]
        recent_prices2 = prices2[-20:]

        recent_corr = np.corrcoef(recent_prices1, recent_prices2)[0, 1]

        # Check divergence
        divergence = abs(hist_corr - recent_corr)

        if divergence > threshold:
            self.memory.log_decision(
                f'Divergence detected: {symbol1} vs {symbol2}',
                f'Historical: {hist_corr:.4f}, Recent: {recent_corr:.4f}, '
                f'Divergence: {divergence:.4f}',
                tags=['correlation', 'divergence', symbol1, symbol2]
            )
            return True

        return False

    def get_correlation_strength(self, correlation: float) -> str:
        """Classify correlation strength"""
        abs_corr = abs(correlation)

        if abs_corr >= 0.9:
            return 'very_strong'
        elif abs_corr >= 0.7:
            return 'strong'
        elif abs_corr >= 0.5:
            return 'moderate'
        elif abs_corr >= 0.3:
            return 'weak'
        else:
            return 'very_weak'


if __name__ == '__main__':
    # Test the system
    analyzer = CorrelationAnalyzer()

    print("Correlation Analyzer ready!")

    # Add sample data
    print("\nAdding sample data...")
    base_prices = [100 + i * 0.5 + np.random.randn() * 2 for i in range(100)]

    analyzer.add_price_data('NQ', base_prices)
    analyzer.add_price_data('ES', [p * 0.29 + np.random.randn() * 1 for p in base_prices])  # Correlated
    analyzer.add_price_data('CL', [80 + np.random.randn() * 5 for _ in range(100)])  # Uncorrelated

    # Calculate correlations
    print("\nCalculating correlations...")
    corr_nq_es = analyzer.calculate_correlation('NQ', 'ES')
    corr_nq_cl = analyzer.calculate_correlation('NQ', 'CL')

    print(f"  NQ vs ES: {corr_nq_es:.4f} ({analyzer.get_correlation_strength(corr_nq_es)})")
    print(f"  NQ vs CL: {corr_nq_cl:.4f} ({analyzer.get_correlation_strength(corr_nq_cl)})")

    # Find correlated pairs
    pairs = analyzer.find_correlated_pairs(min_correlation=0.5)
    print(f"\nCorrelated pairs (>0.5): {len(pairs)}")
    for sym1, sym2, corr in pairs:
        print(f"  {sym1} - {sym2}: {corr:.4f}")
