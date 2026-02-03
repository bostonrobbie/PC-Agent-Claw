#!/usr/bin/env python3
"""Position Sizer (#16) - Calculate optimal position sizes"""
import sys
from pathlib import Path
from typing import Dict

sys.path.append(str(Path(__file__).parent.parent))

class PositionSizer:
    """Calculate optimal position sizes based on various methods"""

    def __init__(self):
        self.methods = {
            'fixed_dollar': self.fixed_dollar_size,
            'fixed_risk': self.fixed_risk_size,
            'percent_equity': self.percent_equity_size,
            'kelly_criterion': self.kelly_criterion_size,
            'volatility_adjusted': self.volatility_adjusted_size
        }

    def fixed_dollar_size(self, account_balance: float, **kwargs) -> int:
        """Fixed dollar amount per trade"""
        fixed_amount = kwargs.get('fixed_amount', 10000)
        entry_price = kwargs.get('entry_price', 1)

        quantity = int(fixed_amount / entry_price)
        return max(1, quantity)

    def fixed_risk_size(self, account_balance: float, **kwargs) -> int:
        """Fixed risk amount per trade"""
        risk_amount = kwargs.get('risk_amount', 500)
        entry_price = kwargs.get('entry_price')
        stop_loss = kwargs.get('stop_loss')

        if entry_price is None or stop_loss is None:
            return 1

        risk_per_unit = abs(entry_price - stop_loss)
        if risk_per_unit == 0:
            return 1

        quantity = int(risk_amount / risk_per_unit)
        return max(1, quantity)

    def percent_equity_size(self, account_balance: float, **kwargs) -> int:
        """Risk a percentage of equity per trade"""
        risk_percent = kwargs.get('risk_percent', 1.0)  # 1% default
        entry_price = kwargs.get('entry_price')
        stop_loss = kwargs.get('stop_loss')

        if entry_price is None or stop_loss is None:
            return 1

        risk_amount = account_balance * (risk_percent / 100)
        risk_per_unit = abs(entry_price - stop_loss)

        if risk_per_unit == 0:
            return 1

        quantity = int(risk_amount / risk_per_unit)
        return max(1, quantity)

    def kelly_criterion_size(self, account_balance: float, **kwargs) -> int:
        """Kelly Criterion for optimal position sizing"""
        win_rate = kwargs.get('win_rate', 0.5)  # 50% default
        avg_win = kwargs.get('avg_win', 1.0)
        avg_loss = kwargs.get('avg_loss', 1.0)
        entry_price = kwargs.get('entry_price', 1)

        if avg_loss == 0:
            return 1

        win_loss_ratio = avg_win / avg_loss

        # Kelly % = W - [(1-W) / R]
        # W = win rate, R = win/loss ratio
        kelly_pct = win_rate - ((1 - win_rate) / win_loss_ratio)

        # Use fractional Kelly (50% of full Kelly for safety)
        kelly_pct = max(0, kelly_pct * 0.5)

        position_value = account_balance * kelly_pct
        quantity = int(position_value / entry_price)

        return max(1, quantity)

    def volatility_adjusted_size(self, account_balance: float, **kwargs) -> int:
        """Adjust position size based on volatility"""
        target_risk = kwargs.get('target_risk', 500)
        volatility = kwargs.get('volatility', 0.02)  # 2% default
        entry_price = kwargs.get('entry_price', 1)

        if volatility == 0:
            return 1

        # Risk per unit based on volatility
        risk_per_unit = entry_price * volatility

        quantity = int(target_risk / risk_per_unit)
        return max(1, quantity)

    def calculate_position_size(self, method: str, account_balance: float, **kwargs) -> Dict:
        """Calculate position size using specified method"""
        if method not in self.methods:
            method = 'fixed_risk'

        quantity = self.methods[method](account_balance, **kwargs)

        entry_price = kwargs.get('entry_price', 1)
        stop_loss = kwargs.get('stop_loss', entry_price * 0.99)

        position_value = quantity * entry_price
        risk_amount = quantity * abs(entry_price - stop_loss)
        risk_percent = (risk_amount / account_balance) * 100

        return {
            'method': method,
            'quantity': quantity,
            'position_value': position_value,
            'risk_amount': risk_amount,
            'risk_percent': risk_percent
        }

    def compare_methods(self, account_balance: float, **kwargs) -> Dict:
        """Compare position sizes across all methods"""
        results = {}

        for method_name in self.methods.keys():
            try:
                results[method_name] = self.calculate_position_size(
                    method_name, account_balance, **kwargs
                )
            except Exception as e:
                results[method_name] = {'error': str(e)}

        return results


if __name__ == '__main__':
    # Test the system
    sizer = PositionSizer()

    print("Position Sizer ready!")

    # Test parameters
    account_balance = 100000
    params = {
        'entry_price': 16500,
        'stop_loss': 16450,
        'risk_amount': 500,
        'risk_percent': 1.0,
        'win_rate': 0.55,
        'avg_win': 150,
        'avg_loss': 100,
        'volatility': 0.015
    }

    # Compare all methods
    print(f"\nAccount balance: ${account_balance:,.0f}")
    print(f"Entry price: ${params['entry_price']}")
    print(f"Stop loss: ${params['stop_loss']}")
    print("\nPosition sizes by method:")

    results = sizer.compare_methods(account_balance, **params)

    for method, result in results.items():
        if 'error' in result:
            print(f"  {method}: ERROR - {result['error']}")
        else:
            print(f"  {method}:")
            print(f"    Quantity: {result['quantity']}")
            print(f"    Position value: ${result['position_value']:,.0f}")
            print(f"    Risk: ${result['risk_amount']:.2f} ({result['risk_percent']:.2f}%)")
