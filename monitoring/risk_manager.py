#!/usr/bin/env python3
"""Risk Manager (#15) - Real-time risk monitoring and limits"""
import sys
from pathlib import Path
from typing import Dict, List, Optional
import json

sys.path.append(str(Path(__file__).parent.parent))

from core.persistent_memory import PersistentMemory

class RiskManager:
    """Real-time risk monitoring and management"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            workspace = Path(__file__).parent.parent
            db_path = str(workspace / "memory.db")

        self.memory = PersistentMemory(db_path)

        # Default risk limits
        self.limits = {
            'max_position_size': 100000,  # Max position size in dollars
            'max_daily_loss': 2000,  # Max daily loss
            'max_open_positions': 5,  # Max number of open positions
            'max_risk_per_trade': 500,  # Max risk per trade
            'max_portfolio_risk': 0.02,  # Max 2% portfolio risk
            'max_leverage': 2.0  # Max leverage
        }

        self.current_state = {
            'daily_pnl': 0,
            'open_positions': [],
            'total_exposure': 0
        }

    def set_limits(self, **kwargs):
        """Set risk limits"""
        for key, value in kwargs.items():
            if key in self.limits:
                self.limits[key] = value

                self.memory.log_decision(
                    f'Risk limit updated: {key}',
                    f'New value: {value}',
                    tags=['risk_management', 'limit_update', key]
                )

    def check_position_size(self, position_value: float) -> bool:
        """Check if position size is within limits"""
        if position_value > self.limits['max_position_size']:
            self.memory.log_decision(
                'Position size limit exceeded',
                f'Position: ${position_value:.2f}, Limit: ${self.limits["max_position_size"]:.2f}',
                tags=['risk_management', 'limit_exceeded', 'position_size']
            )
            return False

        return True

    def check_daily_loss(self, current_pnl: float) -> bool:
        """Check if daily loss limit is exceeded"""
        if current_pnl < -self.limits['max_daily_loss']:
            self.memory.log_decision(
                'Daily loss limit exceeded',
                f'P&L: ${current_pnl:.2f}, Limit: ${-self.limits["max_daily_loss"]:.2f}',
                tags=['risk_management', 'limit_exceeded', 'daily_loss']
            )
            return False

        return True

    def check_open_positions(self, num_positions: int) -> bool:
        """Check if number of open positions is within limits"""
        if num_positions >= self.limits['max_open_positions']:
            self.memory.log_decision(
                'Open positions limit reached',
                f'Positions: {num_positions}, Limit: {self.limits["max_open_positions"]}',
                tags=['risk_management', 'limit_exceeded', 'open_positions']
            )
            return False

        return True

    def calculate_position_risk(self, entry_price: float, stop_loss: float,
                               quantity: float) -> float:
        """Calculate risk for a position"""
        risk_per_unit = abs(entry_price - stop_loss)
        total_risk = risk_per_unit * quantity

        return total_risk

    def validate_trade(self, symbol: str, entry_price: float, quantity: float,
                      stop_loss: float, account_balance: float) -> Dict:
        """Comprehensive trade validation"""
        position_value = entry_price * quantity
        position_risk = self.calculate_position_risk(entry_price, stop_loss, quantity)
        portfolio_risk_pct = (position_risk / account_balance) * 100

        checks = {
            'position_size_ok': self.check_position_size(position_value),
            'risk_per_trade_ok': position_risk <= self.limits['max_risk_per_trade'],
            'portfolio_risk_ok': portfolio_risk_pct <= (self.limits['max_portfolio_risk'] * 100),
            'position_count_ok': self.check_open_positions(len(self.current_state['open_positions']))
        }

        all_passed = all(checks.values())

        self.memory.log_decision(
            f'Trade validation: {"PASSED" if all_passed else "FAILED"}',
            f'Symbol: {symbol}, Position: ${position_value:.2f}, Risk: ${position_risk:.2f}, '
            f'Checks: {json.dumps(checks)}',
            tags=['risk_management', 'validation', 'passed' if all_passed else 'failed']
        )

        return {
            'approved': all_passed,
            'checks': checks,
            'position_value': position_value,
            'position_risk': position_risk,
            'portfolio_risk_pct': portfolio_risk_pct
        }

    def update_daily_pnl(self, pnl: float):
        """Update daily P&L"""
        self.current_state['daily_pnl'] = pnl

        # Check if limit exceeded
        if not self.check_daily_loss(pnl):
            self.memory.log_decision(
                'TRADING HALTED - Daily loss limit exceeded',
                f'Daily P&L: ${pnl:.2f}',
                tags=['risk_management', 'trading_halt', 'daily_loss']
            )

    def add_position(self, position: Dict):
        """Add an open position"""
        self.current_state['open_positions'].append(position)
        self.current_state['total_exposure'] += position.get('value', 0)

    def remove_position(self, position_id: str):
        """Remove a closed position"""
        self.current_state['open_positions'] = [
            p for p in self.current_state['open_positions']
            if p.get('id') != position_id
        ]

        # Recalculate exposure
        self.current_state['total_exposure'] = sum(
            p.get('value', 0) for p in self.current_state['open_positions']
        )

    def get_risk_report(self) -> Dict:
        """Get current risk report"""
        return {
            'limits': self.limits,
            'current_state': self.current_state,
            'daily_loss_used_pct': (abs(self.current_state['daily_pnl']) /
                                   self.limits['max_daily_loss'] * 100)
                                   if self.current_state['daily_pnl'] < 0 else 0,
            'position_capacity': (self.limits['max_open_positions'] -
                                len(self.current_state['open_positions']))
        }


if __name__ == '__main__':
    # Test the system
    risk_mgr = RiskManager()

    print("Risk Manager ready!")

    # Set custom limits
    risk_mgr.set_limits(
        max_position_size=50000,
        max_daily_loss=1000,
        max_risk_per_trade=250
    )

    # Validate a trade
    print("\nValidating trade...")
    validation = risk_mgr.validate_trade(
        symbol='NQ',
        entry_price=16500,
        quantity=2,
        stop_loss=16450,
        account_balance=100000
    )

    print(f"  Approved: {validation['approved']}")
    print(f"  Position value: ${validation['position_value']:.2f}")
    print(f"  Position risk: ${validation['position_risk']:.2f}")
    print(f"  Portfolio risk: {validation['portfolio_risk_pct']:.2f}%")

    # Get risk report
    report = risk_mgr.get_risk_report()
    print(f"\nRisk Report:")
    print(json.dumps(report, indent=2))
