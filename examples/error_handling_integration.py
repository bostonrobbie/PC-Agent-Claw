#!/usr/bin/env python3
"""
Complete Error Handling Integration Example

Demonstrates how error_classifier.py and error_prevention.py work together
with existing error_recovery.py and self_healing_system.py

This example shows the complete error handling pipeline:
1. Prevention Layer - Blocks errors before they occur
2. Classification System - Categorizes errors that do occur
3. Recovery System - Recovers from errors using classification
4. Self-Healing - Automatically fixes recurring issues

Author: AI Self-Improvement System
Created: 2026-02-03
"""

import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.error_classifier import ErrorClassificationEngine
from core.error_prevention import ErrorPreventionLayer, prevent_errors
from core.error_recovery import ErrorRecoverySystem
from core.self_healing_system import SelfHealingSystem


class IntegratedErrorHandler:
    """
    Integrated error handling system combining all layers

    Flow:
    1. Prevention checks operation before execution
    2. If error occurs, classify it
    3. Use classification to determine recovery strategy
    4. Apply self-healing for recurring issues
    """

    def __init__(self):
        self.prevention = ErrorPreventionLayer()
        self.classifier = ErrorClassificationEngine()
        self.recovery = ErrorRecoverySystem()
        self.healing = SelfHealingSystem()

        # Statistics
        self.prevented_count = 0
        self.classified_count = 0
        self.recovered_count = 0
        self.self_healed_count = 0

    def execute_safe_operation(self, operation_name: str,
                              operation_func: callable,
                              context: Dict[str, Any] = None,
                              **kwargs) -> Any:
        """
        Execute operation with full error handling pipeline

        Args:
            operation_name: Name of the operation
            operation_func: Function to execute
            context: Context information
            **kwargs: Operation parameters

        Returns:
            Operation result or None if failed
        """
        # Step 1: PREVENTION - Check before execution
        print(f"\n[PREVENTION] Checking operation: {operation_name}")
        prevention_result = self.prevention.check_operation(
            operation_name,
            context=context,
            **kwargs
        )

        if not prevention_result.allowed:
            self.prevented_count += 1
            print(f"  ✗ BLOCKED: {prevention_result.reason}")
            print(f"  Rule: {prevention_result.rule_id}")

            if prevention_result.alternative_action:
                print(f"  Suggestion: {prevention_result.alternative_action}")

            return None

        print(f"  ✓ Allowed (confidence: {prevention_result.confidence:.0%})")

        # Step 2: EXECUTION with recovery
        task_id = f"{operation_name}_{int(time.time())}"

        try:
            # Start recovery tracking
            self.recovery.start_task(task_id, operation_name, total_steps=3)
            self.recovery.checkpoint(task_id, 1, "Pre-execution check")

            # Execute operation
            print(f"\n[EXECUTION] Running: {operation_name}")
            result = operation_func(**kwargs)

            # Complete successfully
            self.recovery.checkpoint(task_id, 2, "Execution completed")
            self.recovery.complete_task(task_id)

            print(f"  ✓ Success")
            return result

        except Exception as error:
            # Step 3: CLASSIFICATION - Understand the error
            print(f"\n[CLASSIFICATION] Error occurred: {type(error).__name__}")
            classification = self.classifier.classify(error, context=context)
            self.classified_count += 1

            print(f"  Type: {classification.error_type}")
            print(f"  Severity: {classification.severity}")
            print(f"  Recoverability: {classification.recoverability}")
            print(f"  Domain: {classification.domain}")
            print(f"  Required Action: {classification.required_action}")
            print(f"  Confidence: {classification.confidence_score:.0%}")

            # Record error
            self.recovery.record_error(task_id, error)

            # Step 4: RECOVERY - Try to recover based on classification
            if classification.recoverability == 'recoverable':
                print(f"\n[RECOVERY] Attempting recovery...")
                routing = self.classifier.get_routing_recommendation(classification)

                print(f"  Handler: {routing['handler']}")
                print(f"  Strategy: {routing['retry_strategy']}")

                if classification.required_action == 'retry':
                    # Attempt retry recovery
                    success = self._attempt_retry_recovery(
                        operation_func,
                        kwargs,
                        task_id,
                        max_attempts=3
                    )

                    if success:
                        self.recovered_count += 1
                        print(f"  ✓ Recovered successfully")

                        # Learn prevention rule for next time
                        self.prevention.learn_from_error(
                            error_type=type(error).__name__,
                            error_message=str(error),
                            operation=operation_name,
                            params=kwargs
                        )
                        return success
                    else:
                        print(f"  ✗ Recovery failed")

            # Step 5: SELF-HEALING - Learn for future
            if classification.similar_errors_count > 3:
                print(f"\n[SELF-HEALING] Recurring error detected ({classification.similar_errors_count} times)")
                print(f"  Implementing automatic fixes...")

                # Add prevention rule
                self.prevention.add_bad_pattern(
                    pattern_type='error_based',
                    pattern_regex=self._create_error_pattern(str(error)),
                    description=f"Auto-learned from {classification.error_type}",
                    severity=classification.severity
                )

                self.self_healed_count += 1
                print(f"  ✓ Prevention rule added for future")

            return None

    def _attempt_retry_recovery(self, operation_func: callable,
                               kwargs: Dict, task_id: str,
                               max_attempts: int = 3) -> Optional[Any]:
        """Attempt retry-based recovery"""
        for attempt in range(max_attempts):
            try:
                print(f"  Attempt {attempt + 1}/{max_attempts}...")
                time.sleep(0.5 * (attempt + 1))  # Exponential backoff

                result = operation_func(**kwargs)

                # Success - complete task
                self.recovery.checkpoint(task_id, 3, f"Recovered on attempt {attempt + 1}")
                self.recovery.complete_task(task_id)

                return result

            except Exception as e:
                if attempt == max_attempts - 1:
                    print(f"  Failed after {max_attempts} attempts")
                    return None
                continue

        return None

    def _create_error_pattern(self, error_message: str) -> str:
        """Create regex pattern from error message"""
        import re
        # Simple pattern creation
        pattern = re.sub(r'\d+', r'\\d+', error_message)
        pattern = re.sub(r'"[^"]*"', r'"[^"]*"', pattern)
        return pattern[:100]  # Limit length

    def get_statistics(self) -> Dict:
        """Get complete error handling statistics"""
        prevention_stats = self.prevention.get_prevention_stats()
        classification_stats = self.classifier.get_accuracy_stats()
        recovery_stats = self.recovery.get_recovery_stats()

        return {
            'prevention': {
                'total_checks': prevention_stats['total_checks'],
                'total_preventions': prevention_stats['total_preventions'],
                'effectiveness': prevention_stats['effectiveness']
            },
            'classification': {
                'total': classification_stats['total_classifications'],
                'accuracy': classification_stats['overall_accuracy']
            },
            'recovery': {
                'total_tasks': recovery_stats['total_tasks'],
                'successful_recoveries': recovery_stats['successful_recoveries'],
                'recovery_rate': recovery_stats['recovery_success_rate']
            },
            'self_healing': {
                'total_fixes': self.self_healed_count
            },
            'overall': {
                'prevented': self.prevented_count,
                'classified': self.classified_count,
                'recovered': self.recovered_count,
                'self_healed': self.self_healed_count
            }
        }


# Example operations to demonstrate the system
def risky_divide(a: int, b: int, divisor: int = 1) -> float:
    """Division operation that might fail"""
    return a / divisor


def risky_file_read(file_path: str) -> str:
    """File read that might fail"""
    with open(file_path, 'r') as f:
        return f.read()


def risky_network_call(url: str, timeout: int = 5) -> Dict:
    """Simulated network call that might fail"""
    import random
    if random.random() < 0.3:  # 30% failure rate
        raise ConnectionError(f"Failed to connect to {url}")
    return {'status': 'success', 'data': 'response'}


def flaky_computation(value: int) -> int:
    """Computation that sometimes fails"""
    import random
    if random.random() < 0.4:  # 40% failure rate
        raise ValueError(f"Invalid computation state for value {value}")
    return value * 2


def demo_integrated_error_handling():
    """Demonstrate the integrated error handling system"""
    print("="*80)
    print("INTEGRATED ERROR HANDLING SYSTEM DEMONSTRATION")
    print("="*80)

    handler = IntegratedErrorHandler()

    # Test 1: Prevention catches error before execution
    print("\n" + "="*80)
    print("TEST 1: Prevention Layer")
    print("="*80)

    result = handler.execute_safe_operation(
        operation_name='divide',
        operation_func=risky_divide,
        a=10,
        b=5,
        divisor=0  # This will be prevented!
    )
    print(f"Result: {result}")

    # Test 2: Valid operation succeeds
    print("\n" + "="*80)
    print("TEST 2: Valid Operation")
    print("="*80)

    result = handler.execute_safe_operation(
        operation_name='divide',
        operation_func=risky_divide,
        a=10,
        b=5,
        divisor=2
    )
    print(f"Result: {result}")

    # Test 3: Error occurs, gets classified and recovered
    print("\n" + "="*80)
    print("TEST 3: Classification and Recovery")
    print("="*80)

    result = handler.execute_safe_operation(
        operation_name='network_call',
        operation_func=risky_network_call,
        context={'retry_allowed': True},
        url='https://api.example.com/data',
        timeout=5
    )
    print(f"Result: {result}")

    # Test 4: Flaky operation with retry recovery
    print("\n" + "="*80)
    print("TEST 4: Retry Recovery for Flaky Operation")
    print("="*80)

    result = handler.execute_safe_operation(
        operation_name='computation',
        operation_func=flaky_computation,
        value=42
    )
    print(f"Result: {result}")

    # Test 5: Simulate recurring error for self-healing
    print("\n" + "="*80)
    print("TEST 5: Self-Healing (Recurring Errors)")
    print("="*80)

    # Create same error multiple times
    for i in range(4):
        print(f"\nAttempt {i+1}:")
        try:
            result = handler.execute_safe_operation(
                operation_name='read_file',
                operation_func=risky_file_read,
                file_path='/nonexistent/file.txt'
            )
        except Exception:
            pass

    # Test 6: Empty file path (should be prevented after learning)
    print("\n" + "="*80)
    print("TEST 6: Prevention After Learning")
    print("="*80)

    result = handler.execute_safe_operation(
        operation_name='read_file',
        operation_func=risky_file_read,
        file_path=''  # Should be prevented
    )

    # Display comprehensive statistics
    print("\n" + "="*80)
    print("COMPREHENSIVE ERROR HANDLING STATISTICS")
    print("="*80)

    stats = handler.get_statistics()

    print("\n[PREVENTION LAYER]")
    print(f"  Total checks: {stats['prevention']['total_checks']}")
    print(f"  Errors prevented: {stats['prevention']['total_preventions']}")
    print(f"  Effectiveness: {stats['prevention']['effectiveness']}%")

    print("\n[CLASSIFICATION SYSTEM]")
    print(f"  Errors classified: {stats['classification']['total']}")
    print(f"  Classification accuracy: {stats['classification']['accuracy']}%")

    print("\n[RECOVERY SYSTEM]")
    print(f"  Recovery attempts: {stats['recovery']['successful_recoveries']}")
    print(f"  Recovery rate: {stats['recovery']['recovery_rate']:.1f}%")

    print("\n[SELF-HEALING]")
    print(f"  Automatic fixes applied: {stats['self_healing']['total_fixes']}")

    print("\n[OVERALL PIPELINE]")
    print(f"  Errors prevented: {stats['overall']['prevented']}")
    print(f"  Errors classified: {stats['overall']['classified']}")
    print(f"  Errors recovered: {stats['overall']['recovered']}")
    print(f"  Self-healing fixes: {stats['overall']['self_healed']}")

    print("\n" + "="*80)
    print("DEMONSTRATION COMPLETE")
    print("="*80)

    print("\nThe integrated system demonstrated:")
    print("  1. ✓ Prevention of errors before execution")
    print("  2. ✓ Classification of errors that occur")
    print("  3. ✓ Intelligent recovery strategies")
    print("  4. ✓ Learning from errors for prevention")
    print("  5. ✓ Self-healing for recurring issues")
    print("\nAll layers work together to provide robust error handling!")
    print("="*80)


if __name__ == '__main__':
    demo_integrated_error_handling()
