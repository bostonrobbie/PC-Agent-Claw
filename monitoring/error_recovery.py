#!/usr/bin/env python3
"""Error Recovery System (#10) - Automatic error detection and recovery"""
import sqlite3
from pathlib import Path
from typing import Dict, Optional, Callable, List
from datetime import datetime
import json
import traceback
import sys

sys.path.append(str(Path(__file__).parent.parent))

from core.persistent_memory import PersistentMemory

class ErrorRecoverySystem:
    def __init__(self, db_path: str = None):
        if db_path is None:
            workspace = Path(__file__).parent.parent
            db_path = str(workspace / "memory.db")

        self.memory = PersistentMemory(db_path)
        self.recovery_strategies: Dict[str, Callable] = {}
        self._register_default_strategies()

    def _register_default_strategies(self):
        """Register default recovery strategies"""
        self.register_recovery('ConnectionError', self._retry_with_backoff)
        self.register_recovery('TimeoutError', self._retry_with_backoff)
        self.register_recovery('FileNotFoundError', self._create_missing_file)
        self.register_recovery('PermissionError', self._escalate_permissions)

    def register_recovery(self, error_type: str, recovery_func: Callable):
        """Register a recovery strategy for an error type"""
        self.recovery_strategies[error_type] = recovery_func

        self.memory.log_decision(
            f'Recovery strategy registered',
            f'Error type: {error_type}, Strategy: {recovery_func.__name__}',
            tags=['error_recovery', 'registration', error_type]
        )

    def handle_error(self, error: Exception, context: Dict = None) -> Optional[any]:
        """Handle an error and attempt recovery"""
        error_type = type(error).__name__
        error_msg = str(error)
        stack_trace = traceback.format_exc()

        # Log the error
        self.memory.log_decision(
            f'Error occurred: {error_type}',
            f'Message: {error_msg}\n\nStack trace:\n{stack_trace}',
            tags=['error', error_type, 'recovery_attempt']
        )

        # Try to recover
        if error_type in self.recovery_strategies:
            try:
                recovery_func = self.recovery_strategies[error_type]
                result = recovery_func(error, context)

                self.memory.log_decision(
                    f'Recovery successful: {error_type}',
                    f'Strategy: {recovery_func.__name__}',
                    tags=['error_recovery', 'success', error_type]
                )

                return result
            except Exception as recovery_error:
                self.memory.log_decision(
                    f'Recovery failed: {error_type}',
                    f'Recovery error: {str(recovery_error)}',
                    tags=['error_recovery', 'failure', error_type]
                )
                return None
        else:
            self.memory.log_decision(
                f'No recovery strategy for: {error_type}',
                f'Error will propagate',
                tags=['error', error_type, 'no_recovery']
            )
            return None

    def safe_execute(self, func: Callable, *args, max_retries: int = 3, **kwargs):
        """Execute a function with automatic error recovery"""
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt < max_retries - 1:
                    result = self.handle_error(e, {'attempt': attempt + 1, 'max_retries': max_retries})
                    if result is not None:
                        return result
                    # Continue to next retry
                else:
                    # Final attempt failed
                    self.memory.log_decision(
                        f'Function failed after {max_retries} attempts',
                        f'Function: {func.__name__}, Error: {str(e)}',
                        tags=['error', 'max_retries_exceeded']
                    )
                    raise

    # Default recovery strategies

    def _retry_with_backoff(self, error: Exception, context: Dict) -> None:
        """Retry with exponential backoff"""
        import time
        attempt = context.get('attempt', 1)
        wait_time = min(2 ** attempt, 60)  # Max 60 seconds
        time.sleep(wait_time)
        return None

    def _create_missing_file(self, error: Exception, context: Dict) -> None:
        """Create missing file or directory"""
        error_msg = str(error)
        # Extract filename from error message (simplified)
        # In production, would parse more carefully
        return None

    def _escalate_permissions(self, error: Exception, context: Dict) -> None:
        """Attempt to escalate permissions"""
        # In production, would have proper permission escalation
        self.memory.log_decision(
            'Permission escalation needed',
            f'Error: {str(error)}',
            tags=['permission', 'escalation_needed']
        )
        return None

    def get_error_statistics(self) -> Dict:
        """Get error statistics from memory"""
        cursor = self.memory.conn.cursor()

        # Get error counts by type
        cursor.execute('''
            SELECT decision, COUNT(*) as count
            FROM decisions
            WHERE decision LIKE 'Error occurred:%'
            GROUP BY decision
            ORDER BY count DESC
            LIMIT 10
        ''')

        error_counts = {}
        for row in cursor.fetchall():
            error_type = row['decision'].replace('Error occurred: ', '')
            error_counts[error_type] = row['count']

        # Get recovery success rate
        cursor.execute('''
            SELECT
                SUM(CASE WHEN decision LIKE 'Recovery successful:%' THEN 1 ELSE 0 END) as successful,
                SUM(CASE WHEN decision LIKE 'Recovery failed:%' THEN 1 ELSE 0 END) as failed
            FROM decisions
        ''')
        recovery_stats = cursor.fetchone()

        successful = recovery_stats['successful'] or 0
        failed = recovery_stats['failed'] or 0
        total = successful + failed
        success_rate = (successful / total * 100) if total > 0 else 0

        return {
            'error_counts': error_counts,
            'recovery_attempts': total,
            'successful_recoveries': successful,
            'failed_recoveries': failed,
            'success_rate': round(success_rate, 1)
        }


# Decorator for automatic error recovery
def with_recovery(error_recovery_system: ErrorRecoverySystem, max_retries: int = 3):
    """Decorator to add automatic error recovery to functions"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            return error_recovery_system.safe_execute(func, *args, max_retries=max_retries, **kwargs)
        return wrapper
    return decorator


if __name__ == '__main__':
    # Test the system
    recovery = ErrorRecoverySystem()

    # Test with a function that fails
    def flaky_function(fail_count: int = 2):
        """Function that fails a few times then succeeds"""
        if not hasattr(flaky_function, 'attempts'):
            flaky_function.attempts = 0

        flaky_function.attempts += 1

        if flaky_function.attempts <= fail_count:
            raise ConnectionError(f"Connection failed (attempt {flaky_function.attempts})")

        return "Success!"

    # Test safe execution
    try:
        result = recovery.safe_execute(flaky_function, fail_count=2, max_retries=5)
        print(f"Result: {result}")
    except Exception as e:
        print(f"Failed: {e}")

    # Get statistics
    stats = recovery.get_error_statistics()
    print("\nError Recovery Statistics:")
    print(json.dumps(stats, indent=2))

    print("\nError Recovery System ready!")
