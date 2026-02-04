"""
Smart Retry Engine - PHASE 2 CRITICAL

Intelligent retry logic with:
- Exponential backoff with jitter
- Circuit breaker pattern
- Per-error-type retry policies
- Success rate tracking
- Adaptive retry limits
"""
import time
import random
from typing import Callable, Any, Optional, Dict
from datetime import datetime, timedelta
from enum import Enum


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class RetryPolicy:
    """Retry policy for specific error type"""

    def __init__(self, max_retries: int = 3, base_delay: float = 1.0,
                 max_delay: float = 60.0, backoff_factor: float = 2.0,
                 jitter: bool = True):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter

    def get_delay(self, attempt: int) -> float:
        """
        Calculate delay for retry attempt

        Uses exponential backoff: delay = base * (factor ^ attempt)
        Adds jitter to prevent thundering herd
        """
        delay = min(self.base_delay * (self.backoff_factor ** attempt),
                   self.max_delay)

        if self.jitter:
            # Add random jitter (±25%)
            jitter_amount = delay * 0.25
            delay += random.uniform(-jitter_amount, jitter_amount)

        return max(0, delay)


class CircuitBreaker:
    """
    Circuit breaker to prevent cascading failures

    Opens after threshold failures, closes after recovery period
    """

    def __init__(self, failure_threshold: int = 5,
                 recovery_timeout: float = 60.0,
                 half_open_attempts: int = 1):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_attempts = half_open_attempts

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.half_open_successes = 0

    def can_attempt(self) -> bool:
        """Check if operation can be attempted"""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Check if recovery timeout elapsed
            if self.last_failure_time:
                elapsed = time.time() - self.last_failure_time
                if elapsed >= self.recovery_timeout:
                    # Transition to half-open
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_successes = 0
                    return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            # Allow limited attempts in half-open state
            return self.half_open_successes < self.half_open_attempts

        return False

    def record_success(self):
        """Record successful operation"""
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_successes += 1
            if self.half_open_successes >= self.half_open_attempts:
                # Recovery confirmed, close circuit
                self.state = CircuitState.CLOSED
                self.failure_count = 0
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = max(0, self.failure_count - 1)

    def record_failure(self):
        """Record failed operation"""
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            # Failed during recovery, reopen circuit
            self.state = CircuitState.OPEN
        elif self.state == CircuitState.CLOSED:
            self.failure_count += 1
            if self.failure_count >= self.failure_threshold:
                # Too many failures, open circuit
                self.state = CircuitState.OPEN


class SmartRetryEngine:
    """
    Intelligent retry system with adaptive policies

    Features:
    - Per-error-type retry policies
    - Circuit breakers to prevent cascading failures
    - Success rate tracking
    - Adaptive retry limits based on historical performance
    """

    def __init__(self):
        # Default retry policies for common errors
        self.policies: Dict[str, RetryPolicy] = {
            'network': RetryPolicy(max_retries=5, base_delay=1.0, max_delay=30.0),
            'database': RetryPolicy(max_retries=3, base_delay=0.5, max_delay=10.0),
            'timeout': RetryPolicy(max_retries=2, base_delay=2.0, max_delay=20.0),
            'resource': RetryPolicy(max_retries=4, base_delay=1.0, max_delay=60.0),
            'default': RetryPolicy(max_retries=3, base_delay=1.0, max_delay=30.0),
        }

        # Circuit breakers per error category
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}

        # Statistics
        self.stats = {
            'total_attempts': 0,
            'total_retries': 0,
            'total_successes': 0,
            'total_failures': 0,
            'circuit_opens': 0,
        }

        # Success tracking per error type
        self.success_rates: Dict[str, list] = {}

    def execute_with_retry(self, func: Callable, error_category: str = 'default',
                          *args, **kwargs) -> Any:
        """
        Execute function with intelligent retry logic

        Args:
            func: Function to execute
            error_category: Category for retry policy selection
            *args, **kwargs: Arguments for func

        Returns:
            Result of func

        Raises:
            Last exception if all retries exhausted
        """
        # Get policy and circuit breaker
        policy = self.policies.get(error_category, self.policies['default'])

        if error_category not in self.circuit_breakers:
            self.circuit_breakers[error_category] = CircuitBreaker()

        breaker = self.circuit_breakers[error_category]

        # Check circuit breaker
        if not breaker.can_attempt():
            self.stats['circuit_opens'] += 1
            raise Exception(f"Circuit breaker open for {error_category}")

        last_error = None

        for attempt in range(policy.max_retries + 1):
            self.stats['total_attempts'] += 1

            try:
                result = func(*args, **kwargs)

                # Success
                self.stats['total_successes'] += 1
                breaker.record_success()
                self._record_success(error_category)

                return result

            except Exception as e:
                last_error = e

                # Check if we should retry
                if attempt >= policy.max_retries:
                    # Out of retries
                    self.stats['total_failures'] += 1
                    breaker.record_failure()
                    self._record_failure(error_category)
                    raise

                # Calculate retry delay
                delay = policy.get_delay(attempt)

                self.stats['total_retries'] += 1

                # Wait before retry
                time.sleep(delay)

        # Should not reach here, but just in case
        if last_error:
            raise last_error

    def _record_success(self, error_category: str):
        """Record successful execution"""
        if error_category not in self.success_rates:
            self.success_rates[error_category] = []

        self.success_rates[error_category].append({
            'timestamp': time.time(),
            'success': True
        })

        # Keep only recent history (last 100 attempts)
        self.success_rates[error_category] = \
            self.success_rates[error_category][-100:]

    def _record_failure(self, error_category: str):
        """Record failed execution"""
        if error_category not in self.success_rates:
            self.success_rates[error_category] = []

        self.success_rates[error_category].append({
            'timestamp': time.time(),
            'success': False
        })

        # Keep only recent history
        self.success_rates[error_category] = \
            self.success_rates[error_category][-100:]

    def get_success_rate(self, error_category: str) -> float:
        """
        Get success rate for error category

        Returns value between 0.0 and 1.0
        """
        if error_category not in self.success_rates:
            return 1.0  # No history, assume success

        history = self.success_rates[error_category]
        if not history:
            return 1.0

        successes = sum(1 for h in history if h['success'])
        return successes / len(history)

    def adapt_policy(self, error_category: str):
        """
        Adapt retry policy based on success rate

        Increases retries for consistently failing categories
        Decreases retries for consistently successful categories
        """
        success_rate = self.get_success_rate(error_category)

        if error_category not in self.policies:
            self.policies[error_category] = RetryPolicy()

        policy = self.policies[error_category]

        if success_rate < 0.5:
            # Lots of failures, increase retries
            policy.max_retries = min(policy.max_retries + 1, 10)
            policy.max_delay = min(policy.max_delay * 1.5, 300.0)
        elif success_rate > 0.95:
            # High success, can reduce retries
            policy.max_retries = max(policy.max_retries - 1, 1)

    def get_stats(self) -> dict:
        """Get comprehensive statistics"""
        return {
            **self.stats,
            'success_rate': (self.stats['total_successes'] /
                           max(self.stats['total_attempts'], 1)),
            'retry_rate': (self.stats['total_retries'] /
                         max(self.stats['total_attempts'], 1)),
            'categories': {
                cat: {
                    'success_rate': self.get_success_rate(cat),
                    'policy': {
                        'max_retries': self.policies[cat].max_retries,
                        'base_delay': self.policies[cat].base_delay,
                    } if cat in self.policies else None,
                    'circuit_state': self.circuit_breakers[cat].state.value
                                   if cat in self.circuit_breakers else 'closed'
                }
                for cat in set(list(self.policies.keys()) +
                             list(self.circuit_breakers.keys()))
            }
        }

    def reset_circuit(self, error_category: str):
        """Manually reset circuit breaker"""
        if error_category in self.circuit_breakers:
            breaker = self.circuit_breakers[error_category]
            breaker.state = CircuitState.CLOSED
            breaker.failure_count = 0
