#!/usr/bin/env python3
"""Entry/Exit Manager (#18) - Manage trade entries and exits"""
import sys
from pathlib import Path
from typing import Dict, List, Optional, Callable

sys.path.append(str(Path(__file__).parent.parent))

from core.persistent_memory import PersistentMemory

class EntryExitManager:
    """Manage trade entry and exit conditions"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            workspace = Path(__file__).parent.parent
            db_path = str(workspace / "memory.db")

        self.memory = PersistentMemory(db_path)
        self.entry_rules: Dict[str, List[Callable]] = {}
        self.exit_rules: Dict[str, List[Callable]] = {}

    def register_entry_rule(self, strategy_name: str, rule_func: Callable, rule_name: str = None):
        """Register an entry rule for a strategy"""
        if strategy_name not in self.entry_rules:
            self.entry_rules[strategy_name] = []

        self.entry_rules[strategy_name].append({
            'name': rule_name or rule_func.__name__,
            'func': rule_func
        })

        self.memory.log_decision(
            f'Entry rule registered: {strategy_name}',
            f'Rule: {rule_name or rule_func.__name__}',
            tags=['entry_exit', 'entry_rule', strategy_name]
        )

    def register_exit_rule(self, strategy_name: str, rule_func: Callable, rule_name: str = None):
        """Register an exit rule for a strategy"""
        if strategy_name not in self.exit_rules:
            self.exit_rules[strategy_name] = []

        self.exit_rules[strategy_name].append({
            'name': rule_name or rule_func.__name__,
            'func': rule_func
        })

        self.memory.log_decision(
            f'Exit rule registered: {strategy_name}',
            f'Rule: {rule_name or rule_func.__name__}',
            tags=['entry_exit', 'exit_rule', strategy_name]
        )

    def check_entry(self, strategy_name: str, market_data: Dict) -> Dict:
        """Check if entry conditions are met"""
        if strategy_name not in self.entry_rules:
            return {'allowed': False, 'reason': 'No entry rules registered'}

        results = []
        all_passed = True

        for rule in self.entry_rules[strategy_name]:
            try:
                passed = rule['func'](market_data)
                results.append({
                    'rule': rule['name'],
                    'passed': passed
                })

                if not passed:
                    all_passed = False

            except Exception as e:
                results.append({
                    'rule': rule['name'],
                    'passed': False,
                    'error': str(e)
                })
                all_passed = False

        self.memory.log_decision(
            f'Entry check: {strategy_name}',
            f'Result: {"ALLOWED" if all_passed else "REJECTED"}, Rules: {len(results)} checked',
            tags=['entry_exit', 'entry_check', strategy_name, 'allowed' if all_passed else 'rejected']
        )

        return {
            'allowed': all_passed,
            'results': results
        }

    def check_exit(self, strategy_name: str, position: Dict, market_data: Dict) -> Dict:
        """Check if exit conditions are met"""
        if strategy_name not in self.exit_rules:
            return {'should_exit': False, 'reason': 'No exit rules registered'}

        results = []
        any_triggered = False

        for rule in self.exit_rules[strategy_name]:
            try:
                triggered = rule['func'](position, market_data)
                results.append({
                    'rule': rule['name'],
                    'triggered': triggered
                })

                if triggered:
                    any_triggered = True

            except Exception as e:
                results.append({
                    'rule': rule['name'],
                    'triggered': False,
                    'error': str(e)
                })

        self.memory.log_decision(
            f'Exit check: {strategy_name}',
            f'Result: {"EXIT" if any_triggered else "HOLD"}, Rules: {len(results)} checked',
            tags=['entry_exit', 'exit_check', strategy_name, 'exit' if any_triggered else 'hold']
        )

        return {
            'should_exit': any_triggered,
            'results': results
        }


# Example entry rules
def price_above_ma(market_data: Dict) -> bool:
    """Entry rule: Price above moving average"""
    price = market_data.get('price', 0)
    ma = market_data.get('ma_50', 0)
    return price > ma

def volume_above_average(market_data: Dict) -> bool:
    """Entry rule: Volume above average"""
    volume = market_data.get('volume', 0)
    avg_volume = market_data.get('avg_volume', 0)
    return volume > avg_volume * 1.5

def rsi_not_overbought(market_data: Dict) -> bool:
    """Entry rule: RSI not overbought"""
    rsi = market_data.get('rsi', 50)
    return rsi < 70


# Example exit rules
def stop_loss_hit(position: Dict, market_data: Dict) -> bool:
    """Exit rule: Stop loss hit"""
    current_price = market_data.get('price', 0)
    stop_loss = position.get('stop_loss', 0)
    side = position.get('side', 'long')

    if side == 'long':
        return current_price <= stop_loss
    else:
        return current_price >= stop_loss

def take_profit_hit(position: Dict, market_data: Dict) -> bool:
    """Exit rule: Take profit hit"""
    current_price = market_data.get('price', 0)
    take_profit = position.get('take_profit', float('inf'))
    side = position.get('side', 'long')

    if side == 'long':
        return current_price >= take_profit
    else:
        return current_price <= take_profit

def trailing_stop_hit(position: Dict, market_data: Dict) -> bool:
    """Exit rule: Trailing stop hit"""
    current_price = market_data.get('price', 0)
    trailing_stop = position.get('trailing_stop', 0)

    if trailing_stop == 0:
        return False

    return current_price <= trailing_stop


if __name__ == '__main__':
    # Test the system
    manager = EntryExitManager()

    print("Entry/Exit Manager ready!")

    # Register rules for a strategy
    print("\nRegistering rules for 'Opening Range' strategy...")
    manager.register_entry_rule('Opening Range', price_above_ma, 'Price above MA')
    manager.register_entry_rule('Opening Range', volume_above_average, 'Volume above average')
    manager.register_entry_rule('Opening Range', rsi_not_overbought, 'RSI not overbought')

    manager.register_exit_rule('Opening Range', stop_loss_hit, 'Stop loss')
    manager.register_exit_rule('Opening Range', take_profit_hit, 'Take profit')
    manager.register_exit_rule('Opening Range', trailing_stop_hit, 'Trailing stop')

    # Test entry check
    print("\nChecking entry conditions...")
    market_data = {
        'price': 16500,
        'ma_50': 16450,
        'volume': 120000,
        'avg_volume': 75000,
        'rsi': 65
    }

    entry_result = manager.check_entry('Opening Range', market_data)
    print(f"  Entry allowed: {entry_result['allowed']}")
    for result in entry_result['results']:
        print(f"    {result['rule']}: {'PASS' if result['passed'] else 'FAIL'}")

    # Test exit check
    print("\nChecking exit conditions...")
    position = {
        'side': 'long',
        'entry_price': 16450,
        'stop_loss': 16400,
        'take_profit': 16550,
        'trailing_stop': 0
    }

    exit_result = manager.check_exit('Opening Range', position, market_data)
    print(f"  Should exit: {exit_result['should_exit']}")
    for result in exit_result['results']:
        print(f"    {result['rule']}: {'TRIGGERED' if result['triggered'] else 'NOT TRIGGERED'}")
