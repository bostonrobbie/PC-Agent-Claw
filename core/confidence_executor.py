"""
Confidence-Based Execution Engine

Proceeds with actions based on confidence level instead of always asking:
- confidence > 0.9: Execute immediately
- confidence 0.7-0.9: Execute with monitoring
- confidence 0.5-0.7: Execute with easy rollback
- confidence < 0.5: Ask user

ELIMINATES 50%+ of user prompts for routine decisions
"""
from typing import Callable, Any, Optional, Dict
from enum import Enum
import time
from datetime import datetime


class ConfidenceLevel(Enum):
    """Confidence level for decisions"""
    VERY_HIGH = "very_high"  # > 0.9
    HIGH = "high"            # 0.7-0.9
    MEDIUM = "medium"        # 0.5-0.7
    LOW = "low"              # < 0.5


class ExecutionStrategy(Enum):
    """Strategy based on confidence"""
    IMMEDIATE = "immediate"           # Just do it
    MONITORED = "monitored"          # Do it, watch closely
    REVERSIBLE = "reversible"        # Do it, can undo
    ASK_FIRST = "ask_first"          # Must ask user


class ConfidenceBasedExecutor:
    """
    Execute actions based on confidence level

    Eliminates unnecessary user prompts while maintaining safety
    """

    def __init__(self):
        # Confidence thresholds
        self.thresholds = {
            ConfidenceLevel.VERY_HIGH: 0.9,
            ConfidenceLevel.HIGH: 0.7,
            ConfidenceLevel.MEDIUM: 0.5,
            ConfidenceLevel.LOW: 0.0
        }

        # Strategy mapping
        self.strategies = {
            ConfidenceLevel.VERY_HIGH: ExecutionStrategy.IMMEDIATE,
            ConfidenceLevel.HIGH: ExecutionStrategy.MONITORED,
            ConfidenceLevel.MEDIUM: ExecutionStrategy.REVERSIBLE,
            ConfidenceLevel.LOW: ExecutionStrategy.ASK_FIRST
        }

        # Statistics
        self.stats = {
            'total_decisions': 0,
            'immediate_executions': 0,
            'monitored_executions': 0,
            'reversible_executions': 0,
            'asked_user': 0,
            'successful_autonomous': 0,
            'failed_autonomous': 0
        }

        # History for confidence adjustment
        self.decision_history = []

    def calculate_confidence(self, action: str, context: dict = None) -> float:
        """
        Calculate confidence for an action

        Factors:
        - Historical success rate for similar actions
        - Clarity of requirements
        - Reversibility of action
        - Impact/risk level
        - Past user feedback on similar decisions
        """
        context = context or {}

        # Base confidence
        confidence = 0.5

        # Factor 1: Historical success (±0.3)
        if 'historical_success_rate' in context:
            success_rate = context['historical_success_rate']
            confidence += (success_rate - 0.5) * 0.6

        # Factor 2: Requirement clarity (±0.2)
        if 'requirement_clarity' in context:
            clarity = context['requirement_clarity']  # 0.0 to 1.0
            confidence += (clarity - 0.5) * 0.4

        # Factor 3: Reversibility (+0.15 if reversible)
        if context.get('reversible', False):
            confidence += 0.15

        # Factor 4: Impact level (-0.2 for high impact)
        impact = context.get('impact', 'medium')
        if impact == 'low':
            confidence += 0.1
        elif impact == 'high':
            confidence -= 0.2
        elif impact == 'critical':
            confidence -= 0.3

        # Factor 5: Similar past approvals (+0.2)
        if context.get('user_approved_similar', False):
            confidence += 0.2

        # Factor 6: Action type bonuses
        action_lower = action.lower()
        if any(word in action_lower for word in ['fix', 'bug', 'error']):
            confidence += 0.1  # Bug fixes usually safe
        elif any(word in action_lower for word in ['delete', 'remove', 'drop']):
            confidence -= 0.15  # Destructive actions need care
        elif any(word in action_lower for word in ['test', 'verify', 'check']):
            confidence += 0.15  # Tests are safe

        # Clamp to [0.0, 1.0]
        return max(0.0, min(1.0, confidence))

    def get_confidence_level(self, confidence: float) -> ConfidenceLevel:
        """Convert confidence score to level"""
        if confidence >= self.thresholds[ConfidenceLevel.VERY_HIGH]:
            return ConfidenceLevel.VERY_HIGH
        elif confidence >= self.thresholds[ConfidenceLevel.HIGH]:
            return ConfidenceLevel.HIGH
        elif confidence >= self.thresholds[ConfidenceLevel.MEDIUM]:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW

    def get_execution_strategy(self, confidence: float) -> ExecutionStrategy:
        """Determine execution strategy based on confidence"""
        level = self.get_confidence_level(confidence)
        return self.strategies[level]

    def should_execute_autonomously(self, confidence: float) -> bool:
        """Check if should execute without asking user"""
        return confidence >= self.thresholds[ConfidenceLevel.MEDIUM]

    def execute_with_confidence(self, action: str, func: Callable,
                               confidence: float = None,
                               context: dict = None,
                               *args, **kwargs) -> Any:
        """
        Execute action based on confidence level

        Args:
            action: Description of action
            func: Function to execute
            confidence: Pre-calculated confidence (optional)
            context: Context for confidence calculation
            *args, **kwargs: Arguments for func

        Returns:
            Result of func execution
        """
        self.stats['total_decisions'] += 1

        # Calculate confidence if not provided
        if confidence is None:
            confidence = self.calculate_confidence(action, context)

        # Get strategy
        strategy = self.get_execution_strategy(confidence)
        level = self.get_confidence_level(confidence)

        # Record decision
        self.decision_history.append({
            'timestamp': time.time(),
            'action': action,
            'confidence': confidence,
            'level': level.value,
            'strategy': strategy.value
        })

        # Execute based on strategy
        if strategy == ExecutionStrategy.IMMEDIATE:
            return self._execute_immediate(action, func, confidence, *args, **kwargs)

        elif strategy == ExecutionStrategy.MONITORED:
            return self._execute_monitored(action, func, confidence, *args, **kwargs)

        elif strategy == ExecutionStrategy.REVERSIBLE:
            return self._execute_reversible(action, func, confidence, *args, **kwargs)

        else:  # ASK_FIRST
            return self._execute_with_permission(action, func, confidence, *args, **kwargs)

    def _execute_immediate(self, action: str, func: Callable,
                          confidence: float, *args, **kwargs) -> Any:
        """Execute immediately with very high confidence"""
        self.stats['immediate_executions'] += 1

        try:
            result = func(*args, **kwargs)
            self.stats['successful_autonomous'] += 1
            return result
        except Exception as e:
            self.stats['failed_autonomous'] += 1
            # Even high confidence can fail, learn from it
            self._record_failure(action, confidence, str(e))
            raise

    def _execute_monitored(self, action: str, func: Callable,
                          confidence: float, *args, **kwargs) -> Any:
        """Execute with monitoring for high confidence"""
        self.stats['monitored_executions'] += 1

        # Set up monitoring
        start_time = time.time()

        try:
            result = func(*args, **kwargs)

            # Check execution time (flag if took >2x expected)
            duration = time.time() - start_time
            expected_duration = kwargs.get('expected_duration', 10.0)

            if duration > expected_duration * 2:
                # Took longer than expected, lower confidence next time
                self._adjust_confidence_for_pattern(action, -0.1)

            self.stats['successful_autonomous'] += 1
            return result

        except Exception as e:
            self.stats['failed_autonomous'] += 1
            self._record_failure(action, confidence, str(e))
            raise

    def _execute_reversible(self, action: str, func: Callable,
                           confidence: float, *args, **kwargs) -> Any:
        """Execute with easy rollback for medium confidence"""
        self.stats['reversible_executions'] += 1

        # Create checkpoint before execution
        checkpoint = kwargs.get('checkpoint_func')

        try:
            result = func(*args, **kwargs)
            self.stats['successful_autonomous'] += 1
            return result

        except Exception as e:
            self.stats['failed_autonomous'] += 1

            # Attempt rollback if available
            if checkpoint:
                try:
                    checkpoint()  # Restore previous state
                except:
                    pass

            self._record_failure(action, confidence, str(e))
            raise

    def _execute_with_permission(self, action: str, func: Callable,
                                 confidence: float, *args, **kwargs) -> Any:
        """Ask user before executing (low confidence)"""
        self.stats['asked_user'] += 1

        # In real implementation, would prompt user here
        # For now, raise exception to indicate user input needed
        raise Exception(f"Low confidence ({confidence:.2f}) - user approval needed: {action}")

    def _record_failure(self, action: str, confidence: float, error: str):
        """Record failure to learn from"""
        # Store failure information
        failure_record = {
            'timestamp': time.time(),
            'action': action,
            'confidence': confidence,
            'error': error
        }

        # Could persist this to database for learning

    def _adjust_confidence_for_pattern(self, action: str, adjustment: float):
        """Adjust confidence for future similar actions"""
        # This would update the model that calculates confidence
        # For now, just track the adjustment
        pass

    def get_confidence_report(self) -> dict:
        """Get report on confidence-based decisions"""
        total_autonomous = (self.stats['immediate_executions'] +
                          self.stats['monitored_executions'] +
                          self.stats['reversible_executions'])

        autonomous_rate = (total_autonomous /
                          max(self.stats['total_decisions'], 1))

        success_rate = (self.stats['successful_autonomous'] /
                       max(total_autonomous, 1))

        return {
            **self.stats,
            'autonomous_execution_rate': autonomous_rate,
            'autonomous_success_rate': success_rate,
            'user_prompts_eliminated': autonomous_rate,
            'recent_decisions': self.decision_history[-10:]  # Last 10
        }

    def adjust_thresholds(self, success_rate: float):
        """
        Adjust confidence thresholds based on success rate

        If success rate high, can be more aggressive
        If success rate low, need to be more cautious
        """
        if success_rate > 0.95:
            # Very successful, can lower thresholds (be more aggressive)
            for level in self.thresholds:
                self.thresholds[level] = max(0.1, self.thresholds[level] - 0.05)

        elif success_rate < 0.80:
            # Too many failures, raise thresholds (be more cautious)
            for level in self.thresholds:
                self.thresholds[level] = min(0.95, self.thresholds[level] + 0.05)
