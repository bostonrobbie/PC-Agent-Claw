"""
Error Prevention Layer - HIGH PRIORITY ENHANCEMENT #3
Blocks known error patterns before they trigger
"""
import sqlite3
from typing import Callable, Any
import psutil

class ErrorPreventionLayer:
    def __init__(self):
        self.blocked_operations = []
        self.prevention_rules = {
            'memory_check': lambda: psutil.virtual_memory().percent < 95,
            'disk_check': lambda: psutil.disk_usage('.').percent < 95
        }
    
    def prevent_if_unsafe(self, operation: Callable, operation_name: str) -> Any:
        """Execute operation only if safe"""
        # Check prevention rules
        for rule_name, check in self.prevention_rules.items():
            if not check():
                self.blocked_operations.append(operation_name)
                raise Exception(f"Prevented {operation_name}: {rule_name} failed")
        
        # Safe to execute
        return operation()
    
    def add_prevention_rule(self, name: str, check: Callable):
        """Add custom prevention rule"""
        self.prevention_rules[name] = check
    
    def get_stats(self):
        return {'blocked_operations': len(self.blocked_operations)}
