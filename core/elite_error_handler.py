#!/usr/bin/env python3
"""Elite Error Handler - World-class error handling and recovery"""
import sys
import traceback
import functools
import time
import inspect
from pathlib import Path
from typing import Callable, Any, Dict, Optional, List, Type
from datetime import datetime
import json

sys.path.append(str(Path(__file__).parent.parent))

from core.persistent_memory import PersistentMemory
from core.telegram_connector import TelegramConnector

class ErrorContext:
    """Rich context for error analysis"""

    def __init__(self, error: Exception, function_name: str, args: tuple, kwargs: dict):
        self.error = error
        self.error_type = type(error).__name__
        self.error_message = str(error)
        self.function_name = function_name
        self.args = args
        self.kwargs = kwargs
        self.timestamp = datetime.now()
        self.stack_trace = traceback.format_exc()
        self.locals_snapshot = None
        self.recovery_attempted = False
        self.recovery_successful = False

    def to_dict(self) -> dict:
        """Convert to dictionary for logging"""
        return {
            'error_type': self.error_type,
            'error_message': self.error_message,
            'function': self.function_name,
            'timestamp': self.timestamp.isoformat(),
            'stack_trace': self.stack_trace,
            'recovery_attempted': self.recovery_attempted,
            'recovery_successful': self.recovery_successful
        }


class RecoveryStrategy:
    """Base class for recovery strategies"""

    def __init__(self, name: str, max_retries: int = 3):
        self.name = name
        self.max_retries = max_retries
        self.success_count = 0
        self.failure_count = 0

    def can_handle(self, error_context: ErrorContext) -> bool:
        """Check if this strategy can handle the error"""
        raise NotImplementedError

    def recover(self, error_context: ErrorContext, func: Callable, *args, **kwargs) -> Any:
        """Attempt recovery"""
        raise NotImplementedError

    def get_stats(self) -> dict:
        """Get strategy statistics"""
        total = self.success_count + self.failure_count
        success_rate = (self.success_count / total * 100) if total > 0 else 0

        return {
            'name': self.name,
            'success_count': self.success_count,
            'failure_count': self.failure_count,
            'success_rate': round(success_rate, 1)
        }


class RetryStrategy(RecoveryStrategy):
    """Retry with exponential backoff"""

    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        super().__init__('retry', max_retries)
        self.base_delay = base_delay

    def can_handle(self, error_context: ErrorContext) -> bool:
        # Handle transient errors
        transient_errors = [
            'ConnectionError', 'TimeoutError', 'ConnectionResetError',
            'BrokenPipeError', 'ConnectionAbortedError', 'ConnectionRefusedError'
        ]
        return error_context.error_type in transient_errors

    def recover(self, error_context: ErrorContext, func: Callable, *args, **kwargs) -> Any:
        for attempt in range(self.max_retries):
            try:
                # Exponential backoff
                if attempt > 0:
                    delay = self.base_delay * (2 ** (attempt - 1))
                    time.sleep(delay)

                result = func(*args, **kwargs)
                self.success_count += 1
                return result

            except Exception as e:
                if attempt == self.max_retries - 1:
                    self.failure_count += 1
                    raise
                continue


class FallbackStrategy(RecoveryStrategy):
    """Fallback to alternative implementation"""

    def __init__(self):
        super().__init__('fallback')
        self.fallback_functions = {}

    def register_fallback(self, original_func_name: str, fallback_func: Callable):
        """Register fallback function"""
        self.fallback_functions[original_func_name] = fallback_func

    def can_handle(self, error_context: ErrorContext) -> bool:
        return error_context.function_name in self.fallback_functions

    def recover(self, error_context: ErrorContext, func: Callable, *args, **kwargs) -> Any:
        fallback = self.fallback_functions.get(error_context.function_name)

        if fallback:
            try:
                result = fallback(*args, **kwargs)
                self.success_count += 1
                return result
            except Exception:
                self.failure_count += 1
                raise
        else:
            self.failure_count += 1
            raise error_context.error


class CircuitBreakerStrategy(RecoveryStrategy):
    """Circuit breaker pattern"""

    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        super().__init__('circuit_breaker')
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.circuits = {}  # function_name -> state

    def can_handle(self, error_context: ErrorContext) -> bool:
        # Can handle any repeated failures
        return True

    def recover(self, error_context: ErrorContext, func: Callable, *args, **kwargs) -> Any:
        func_name = error_context.function_name

        # Initialize circuit if needed
        if func_name not in self.circuits:
            self.circuits[func_name] = {
                'state': 'closed',
                'failures': 0,
                'last_failure': None
            }

        circuit = self.circuits[func_name]

        # Check circuit state
        if circuit['state'] == 'open':
            # Check if timeout has passed
            if circuit['last_failure']:
                elapsed = (datetime.now() - circuit['last_failure']).total_seconds()
                if elapsed >= self.timeout:
                    circuit['state'] = 'half_open'
                else:
                    raise Exception(f"Circuit breaker OPEN for {func_name}")

        try:
            result = func(*args, **kwargs)

            # Success - reset or close circuit
            if circuit['state'] == 'half_open':
                circuit['state'] = 'closed'
                circuit['failures'] = 0

            self.success_count += 1
            return result

        except Exception as e:
            circuit['failures'] += 1
            circuit['last_failure'] = datetime.now()

            # Trip circuit if threshold exceeded
            if circuit['failures'] >= self.failure_threshold:
                circuit['state'] = 'open'

            self.failure_count += 1
            raise


class GracefulDegradationStrategy(RecoveryStrategy):
    """Gracefully degrade functionality"""

    def __init__(self):
        super().__init__('graceful_degradation')
        self.degraded_responses = {}

    def register_degraded_response(self, func_name: str, response: Any):
        """Register degraded response for a function"""
        self.degraded_responses[func_name] = response

    def can_handle(self, error_context: ErrorContext) -> bool:
        return error_context.function_name in self.degraded_responses

    def recover(self, error_context: ErrorContext, func: Callable, *args, **kwargs) -> Any:
        response = self.degraded_responses.get(error_context.function_name)

        if response is not None:
            self.success_count += 1
            return response() if callable(response) else response
        else:
            self.failure_count += 1
            raise error_context.error


class EliteErrorHandler:
    """Elite error handling system"""

    def __init__(self, db_path: str = None):
        workspace = Path(__file__).parent.parent
        if db_path is None:
            db_path = str(workspace / "memory.db")

        self.memory = PersistentMemory(db_path)
        self.telegram = TelegramConnector()

        # Recovery strategies
        self.strategies: List[RecoveryStrategy] = []
        self._register_default_strategies()

        # Error patterns
        self.error_patterns = {}  # error_type -> {count, first_seen, last_seen}

        # Critical error types that should notify immediately
        self.critical_errors = {
            'MemoryError', 'SystemError', 'OSError',
            'DatabaseError', 'DataLoss', 'SecurityError'
        }

    def _register_default_strategies(self):
        """Register default recovery strategies"""
        self.strategies.append(RetryStrategy(max_retries=3))
        self.strategies.append(FallbackStrategy())
        self.strategies.append(CircuitBreakerStrategy(failure_threshold=5))
        self.strategies.append(GracefulDegradationStrategy())

    def register_strategy(self, strategy: RecoveryStrategy):
        """Register a custom recovery strategy"""
        self.strategies.append(strategy)

        self.memory.log_decision(
            f'Recovery strategy registered: {strategy.name}',
            f'Max retries: {strategy.max_retries}',
            tags=['error_handler', 'strategy', strategy.name]
        )

    def handle_error(self, error_context: ErrorContext, func: Callable,
                    *args, **kwargs) -> Optional[Any]:
        """Handle error with recovery strategies"""

        # Log error
        self._log_error(error_context)

        # Update error patterns
        self._update_error_patterns(error_context)

        # Try recovery strategies
        for strategy in self.strategies:
            if strategy.can_handle(error_context):
                try:
                    result = strategy.recover(error_context, func, *args, **kwargs)

                    error_context.recovery_attempted = True
                    error_context.recovery_successful = True

                    self.memory.log_decision(
                        f'Error recovered: {error_context.error_type}',
                        f'Strategy: {strategy.name}, Function: {error_context.function_name}',
                        tags=['error_handler', 'recovery_success', strategy.name]
                    )

                    return result

                except Exception:
                    continue

        # All strategies failed
        error_context.recovery_attempted = True
        error_context.recovery_successful = False

        # Notify if critical
        if error_context.error_type in self.critical_errors:
            self._notify_critical_error(error_context)

        self.memory.log_decision(
            f'Error recovery failed: {error_context.error_type}',
            f'Function: {error_context.function_name}, All strategies exhausted',
            tags=['error_handler', 'recovery_failed', error_context.error_type]
        )

        return None

    def _log_error(self, error_context: ErrorContext):
        """Log error to memory"""
        self.memory.log_decision(
            f'Error occurred: {error_context.error_type}',
            f'Function: {error_context.function_name}, Message: {error_context.error_message}',
            tags=['error_handler', 'error', error_context.error_type]
        )

    def _update_error_patterns(self, error_context: ErrorContext):
        """Update error pattern tracking"""
        error_type = error_context.error_type

        if error_type not in self.error_patterns:
            self.error_patterns[error_type] = {
                'count': 0,
                'first_seen': error_context.timestamp,
                'last_seen': error_context.timestamp,
                'functions': set()
            }

        pattern = self.error_patterns[error_type]
        pattern['count'] += 1
        pattern['last_seen'] = error_context.timestamp
        pattern['functions'].add(error_context.function_name)

        # Alert if error is becoming frequent
        if pattern['count'] >= 10:
            self._notify_error_pattern(error_type, pattern)

    def _notify_critical_error(self, error_context: ErrorContext):
        """Notify about critical errors"""
        message = (
            f"[CRITICAL ERROR]\n"
            f"Type: {error_context.error_type}\n"
            f"Function: {error_context.function_name}\n"
            f"Message: {error_context.error_message[:200]}\n"
            f"Time: {error_context.timestamp.strftime('%H:%M:%S')}"
        )

        self.telegram.send_message(message)

    def _notify_error_pattern(self, error_type: str, pattern: dict):
        """Notify about error patterns"""
        if pattern['count'] % 10 == 0:  # Notify every 10 occurrences
            message = (
                f"[ERROR PATTERN]\n"
                f"Type: {error_type}\n"
                f"Count: {pattern['count']}\n"
                f"Functions: {', '.join(list(pattern['functions'])[:3])}\n"
                f"First seen: {pattern['first_seen'].strftime('%H:%M:%S')}"
            )

            self.telegram.send_message(message)

    def get_error_statistics(self) -> dict:
        """Get error handling statistics"""
        stats = {
            'error_patterns': {},
            'recovery_strategies': {},
            'total_errors': 0,
            'recovered_errors': 0
        }

        # Error patterns
        for error_type, pattern in self.error_patterns.items():
            stats['error_patterns'][error_type] = {
                'count': pattern['count'],
                'functions': list(pattern['functions'])
            }
            stats['total_errors'] += pattern['count']

        # Strategy stats
        for strategy in self.strategies:
            strategy_stats = strategy.get_stats()
            stats['recovery_strategies'][strategy.name] = strategy_stats
            stats['recovered_errors'] += strategy.success_count

        # Recovery rate
        if stats['total_errors'] > 0:
            stats['recovery_rate'] = round(
                (stats['recovered_errors'] / stats['total_errors']) * 100, 1
            )
        else:
            stats['recovery_rate'] = 0

        return stats


# Decorator for elite error handling
def elite_error_handler(handler: EliteErrorHandler = None):
    """Decorator to add elite error handling to functions"""

    if handler is None:
        handler = EliteErrorHandler()

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_context = ErrorContext(e, func.__name__, args, kwargs)

                result = handler.handle_error(error_context, func, *args, **kwargs)

                if result is not None:
                    return result
                else:
                    # Re-raise if recovery failed
                    raise

        return wrapper
    return decorator


# Global handler instance
_global_handler = None

def get_global_handler() -> EliteErrorHandler:
    """Get or create global error handler"""
    global _global_handler
    if _global_handler is None:
        _global_handler = EliteErrorHandler()
    return _global_handler


if __name__ == '__main__':
    # Test the system
    handler = EliteErrorHandler()

    print("Elite Error Handler ready!")

    # Test retry strategy
    @elite_error_handler(handler)
    def flaky_function(fail_count=2):
        if not hasattr(flaky_function, 'attempts'):
            flaky_function.attempts = 0

        flaky_function.attempts += 1

        if flaky_function.attempts <= fail_count:
            raise ConnectionError(f"Connection failed (attempt {flaky_function.attempts})")

        return "Success!"

    try:
        result = flaky_function(fail_count=2)
        print(f"Result: {result}")
    except Exception as e:
        print(f"Failed: {e}")

    # Get statistics
    stats = handler.get_error_statistics()
    print(f"\nError Statistics:")
    print(json.dumps(stats, indent=2))

    print("\nElite Error Handler operational!")
