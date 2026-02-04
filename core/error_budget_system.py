"""
Error Budget System

Allow N errors per hour before concern:
- Budget: 10 errors/hour = healthy
- 10-20 errors/hour = degraded but continue
- >20 errors/hour = investigate patterns
- Never stop due to single error type

PREVENTS EARLY STOPPING due to transient errors
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import time


class ErrorBudgetStatus:
    """Status of error budget"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    EXCEEDED = "exceeded"


class ErrorBudgetSystem:
    """
    Tracks error budget to prevent premature stopping

    Philosophy: Some errors are expected. Don't stop unless
    error rate exceeds budget.
    """

    def __init__(self, budget_per_hour: int = 10,
                 warning_threshold: float = 0.8,
                 critical_threshold: float = 1.5):
        """
        Initialize error budget system

        Args:
            budget_per_hour: Allowed errors per hour (default: 10)
            warning_threshold: Warn when budget * threshold reached (0.8 = 80%)
            critical_threshold: Critical when budget * threshold reached (1.5 = 150%)
        """
        self.budget_per_hour = budget_per_hour
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold

        # Error tracking
        self.errors: List[dict] = []  # All errors with timestamps
        self.errors_by_type: Dict[str, List[dict]] = defaultdict(list)

        # Budget tracking per error type
        self.type_budgets: Dict[str, int] = {}

        # Statistics
        self.stats = {
            'total_errors': 0,
            'errors_last_hour': 0,
            'budget_remaining': budget_per_hour,
            'budget_status': ErrorBudgetStatus.HEALTHY,
            'stops_prevented': 0,
            'type_diversification': 0.0
        }

    def record_error(self, error: Exception, error_type: str = None,
                    context: dict = None) -> dict:
        """
        Record an error occurrence

        Returns:
            Decision on whether to continue or stop
        """
        now = time.time()

        # Classify error type if not provided
        if error_type is None:
            error_type = type(error).__name__

        # Record error
        error_record = {
            'timestamp': now,
            'type': error_type,
            'message': str(error),
            'context': context or {}
        }

        self.errors.append(error_record)
        self.errors_by_type[error_type].append(error_record)
        self.stats['total_errors'] += 1

        # Clean old errors (>1 hour)
        self._cleanup_old_errors()

        # Update statistics
        self._update_stats()

        # Check if should continue
        return self._should_continue(error_type)

    def _cleanup_old_errors(self):
        """Remove errors older than 1 hour"""
        cutoff = time.time() - 3600  # 1 hour ago

        # Clean main list
        self.errors = [e for e in self.errors if e['timestamp'] > cutoff]

        # Clean type lists
        for error_type in list(self.errors_by_type.keys()):
            self.errors_by_type[error_type] = [
                e for e in self.errors_by_type[error_type]
                if e['timestamp'] > cutoff
            ]
            # Remove type if no recent errors
            if not self.errors_by_type[error_type]:
                del self.errors_by_type[error_type]

    def _update_stats(self):
        """Update current statistics"""
        # Errors in last hour
        self.stats['errors_last_hour'] = len(self.errors)

        # Remaining budget
        self.stats['budget_remaining'] = max(
            0,
            self.budget_per_hour - self.stats['errors_last_hour']
        )

        # Budget status
        usage_ratio = self.stats['errors_last_hour'] / self.budget_per_hour

        if usage_ratio >= self.critical_threshold:
            self.stats['budget_status'] = ErrorBudgetStatus.EXCEEDED
        elif usage_ratio >= self.warning_threshold:
            self.stats['budget_status'] = ErrorBudgetStatus.CRITICAL
        elif usage_ratio >= self.warning_threshold * 0.5:
            self.stats['budget_status'] = ErrorBudgetStatus.DEGRADED
        else:
            self.stats['budget_status'] = ErrorBudgetStatus.HEALTHY

        # Type diversification (higher = errors spread across types)
        if self.errors:
            unique_types = len(self.errors_by_type)
            total_errors = len(self.errors)
            # Shannon entropy-like measure
            self.stats['type_diversification'] = unique_types / max(total_errors, 1)

    def _should_continue(self, error_type: str) -> dict:
        """
        Decide if should continue after error

        Returns decision with reasoning
        """
        # Check overall budget
        if self.stats['budget_status'] == ErrorBudgetStatus.EXCEEDED:
            # Over budget, but check if errors are diverse
            if self.stats['type_diversification'] > 0.5:
                # Errors are diverse, probably transient - continue
                self.stats['stops_prevented'] += 1
                return {
                    'should_continue': True,
                    'reason': 'Over budget but errors diverse (transient)',
                    'confidence': 0.7,
                    'recommendation': 'Continue with monitoring'
                }
            else:
                # Errors concentrated in few types - potential systemic issue
                return {
                    'should_continue': False,
                    'reason': 'Over budget with concentrated errors',
                    'confidence': 0.9,
                    'recommendation': 'Investigate error patterns'
                }

        # Check single error type budget
        type_count = len(self.errors_by_type.get(error_type, []))
        type_budget = self.type_budgets.get(error_type, self.budget_per_hour // 2)

        if type_count > type_budget:
            # Single error type over its budget
            return {
                'should_continue': False,
                'reason': f'{error_type} exceeds individual budget ({type_count}/{type_budget})',
                'confidence': 0.8,
                'recommendation': f'Fix {error_type} errors'
            }

        # Within budget - continue
        self.stats['stops_prevented'] += 1
        return {
            'should_continue': True,
            'reason': f'Within budget ({self.stats["errors_last_hour"]}/{self.budget_per_hour})',
            'confidence': 1.0,
            'recommendation': 'Continue normally'
        }

    def set_type_budget(self, error_type: str, budget: int):
        """Set specific budget for an error type"""
        self.type_budgets[error_type] = budget

    def get_error_rate(self, window_minutes: int = 60) -> float:
        """Get error rate for time window (errors per minute)"""
        cutoff = time.time() - (window_minutes * 60)
        recent_errors = [e for e in self.errors if e['timestamp'] > cutoff]

        return len(recent_errors) / window_minutes

    def get_top_error_types(self, limit: int = 5) -> List[tuple]:
        """Get most common error types"""
        type_counts = [
            (error_type, len(errors))
            for error_type, errors in self.errors_by_type.items()
        ]

        type_counts.sort(key=lambda x: x[1], reverse=True)
        return type_counts[:limit]

    def is_error_trending(self, error_type: str, window_minutes: int = 10) -> bool:
        """Check if error type is trending upward"""
        if error_type not in self.errors_by_type:
            return False

        errors = self.errors_by_type[error_type]
        if len(errors) < 3:
            return False

        # Split window in half
        half_window = (window_minutes * 60) / 2
        cutoff = time.time() - (window_minutes * 60)

        first_half = [e for e in errors
                     if cutoff <= e['timestamp'] < time.time() - half_window]
        second_half = [e for e in errors
                      if e['timestamp'] >= time.time() - half_window]

        # Trending if second half has more errors
        return len(second_half) > len(first_half)

    def get_budget_report(self) -> dict:
        """Get comprehensive budget report"""
        return {
            **self.stats,
            'budget_per_hour': self.budget_per_hour,
            'usage_percentage': (self.stats['errors_last_hour'] /
                                self.budget_per_hour * 100),
            'top_error_types': self.get_top_error_types(),
            'error_rate_per_minute': self.get_error_rate(),
            'trending_errors': [
                error_type for error_type in self.errors_by_type.keys()
                if self.is_error_trending(error_type)
            ],
            'recommendations': self._get_recommendations()
        }

    def _get_recommendations(self) -> List[str]:
        """Get recommendations based on current state"""
        recommendations = []

        status = self.stats['budget_status']

        if status == ErrorBudgetStatus.EXCEEDED:
            recommendations.append("Error budget exceeded - investigate patterns")

            top_types = self.get_top_error_types(3)
            if top_types:
                recommendations.append(
                    f"Focus on: {', '.join(t[0] for t in top_types)}"
                )

        elif status == ErrorBudgetStatus.CRITICAL:
            recommendations.append("Approaching error budget limit")

            trending = [t for t in self.errors_by_type.keys()
                       if self.is_error_trending(t)]
            if trending:
                recommendations.append(
                    f"Trending errors: {', '.join(trending)}"
                )

        elif status == ErrorBudgetStatus.DEGRADED:
            recommendations.append("Error rate elevated but manageable")

        else:
            recommendations.append("Error budget healthy - continue normally")

        # Check for repeated errors
        for error_type, errors in self.errors_by_type.items():
            if len(errors) >= 5:
                recommendations.append(
                    f"Recurring: {error_type} ({len(errors)} times) - consider auto-fix"
                )

        return recommendations

    def reset_budget(self):
        """Reset error budget (use at start of new work session)"""
        self.errors.clear()
        self.errors_by_type.clear()
        self.stats = {
            'total_errors': 0,
            'errors_last_hour': 0,
            'budget_remaining': self.budget_per_hour,
            'budget_status': ErrorBudgetStatus.HEALTHY,
            'stops_prevented': 0,
            'type_diversification': 0.0
        }

    def adjust_budget(self, new_budget: int):
        """Adjust budget based on workload"""
        self.budget_per_hour = new_budget
        self._update_stats()

    def allow_error(self, error: Exception, error_type: str = None) -> bool:
        """
        Check if error is within budget (quick check without recording)

        Returns True if error is allowed, False if over budget
        """
        if error_type is None:
            error_type = type(error).__name__

        # Check overall budget
        if self.stats['errors_last_hour'] >= self.budget_per_hour * self.critical_threshold:
            return False

        # Check type-specific budget
        type_count = len(self.errors_by_type.get(error_type, []))
        type_budget = self.type_budgets.get(error_type, self.budget_per_hour // 2)

        return type_count < type_budget
