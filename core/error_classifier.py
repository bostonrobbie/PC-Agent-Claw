"""
Smart Error Classification - HIGH PRIORITY ENHANCEMENT #2
"""
import sqlite3
from dataclasses import dataclass
from typing import Dict

@dataclass  
class ErrorClassification:
    error_type: str
    severity: str
    is_recoverable: bool
    recovery_strategy: str

class SmartErrorClassifier:
    def __init__(self):
        self.rules = [
            {'patterns': ['connection'], 'type': 'network', 'severity': 'high', 'recoverable': True, 'strategy': 'retry'},
            {'patterns': ['memory'], 'type': 'resource', 'severity': 'critical', 'recoverable': True, 'strategy': 'cleanup'}
        ]
    
    def classify(self, error: Exception) -> ErrorClassification:
        msg = str(error).lower()
        for rule in self.rules:
            if any(p in msg for p in rule['patterns']):
                return ErrorClassification(rule['type'], rule['severity'], rule['recoverable'], rule['strategy'])
        return ErrorClassification('unknown', 'medium', True, 'log')
