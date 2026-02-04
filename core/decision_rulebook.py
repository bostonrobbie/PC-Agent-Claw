"""
Decision Rulebook - PHASE 1 CRITICAL

Pre-defined rules for common decisions to eliminate delays.
"""
import json
from typing import Any, Optional

class DecisionRulebook:
    def __init__(self):
        self.rules = {
            'unicode_error': {
                'decision': 'use_ascii_alternative',
                'confidence': 1.0,
                'action': lambda: '[OK]'
            },
            'import_error': {
                'decision': 'try_alternative_continue',
                'confidence': 0.9,
                'action': 'log_and_degrade'
            },
            'database_locked': {
                'decision': 'retry_with_backoff',
                'confidence': 0.95,
                'action': 'retry_3_times'
            },
            'path_error': {
                'decision': 'auto_convert_path',
                'confidence': 0.95,
                'action': 'use_os_path'
            },
            'memory_high': {
                'decision': 'run_cleanup',
                'confidence': 0.9,
                'action': 'gc_collect'
            },
            'task_complete': {
                'decision': 'continue_to_next',
                'confidence': 1.0,
                'action': 'never_stop_unless_told'
            },
            'test_timeout': {
                'decision': 'continue_other_work',
                'confidence': 0.8,
                'action': 'background_test'
            },
            'unknown_error': {
                'decision': 'log_and_continue',
                'confidence': 0.6,
                'action': 'best_effort_continue'
            }
        }
    
    def decide(self, situation: str) -> dict:
        """Get pre-defined decision for situation"""
        return self.rules.get(situation, self.rules['unknown_error'])
    
    def should_ask_user(self, confidence: float) -> bool:
        """Determine if user input needed based on confidence"""
        return confidence < 0.7
    
    def add_rule(self, situation: str, decision: str, confidence: float):
        """Add new rule"""
        self.rules[situation] = {
            'decision': decision,
            'confidence': confidence
        }
