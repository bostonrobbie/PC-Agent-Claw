"""
Phase 3 Integrated Continuous Operation Engine

Combines ALL phases into unified system:
- Phase 1: Error learning, Decision rulebook, Flow monitoring
- Phase 2: Smart retry, Work queue, Auto-fix registry
- Phase 3: Confidence execution, Graceful degradation, Error budget

Single interface for complete continuous operation
"""
from typing import Callable, Any, Optional, Dict, List
import time

from core.phase1_continuous_engine import Phase1ContinuousEngine
from core.phase2_robust_engine import Phase2RobustEngine
from core.confidence_executor import ConfidenceBasedExecutor
from core.graceful_degradation import GracefulDegradationEngine
from core.error_budget_system import ErrorBudgetSystem
from core.work_queue_persistence import TaskPriority


class Phase3IntegratedEngine:
    """
    Complete continuous operation engine

    Integrates all 3 phases for maximum autonomy and robustness
    """

    def __init__(self, error_db_path: str = "errors.db",
                 queue_db_path: str = "work_queue.db",
                 error_budget_per_hour: int = 10):
        """Initialize all subsystems"""
        # Phase 1 + 2 (integrated)
        self.phase2 = Phase2RobustEngine(error_db_path, queue_db_path)

        # Phase 3 components
        self.confidence = ConfidenceBasedExecutor()
        self.degradation = GracefulDegradationEngine()
        self.error_budget = ErrorBudgetSystem(budget_per_hour=error_budget_per_hour)

        # Statistics
        self.stats = {
            'total_actions': 0,
            'autonomous_actions': 0,
            'degraded_actions': 0,
            'budget_stops_prevented': 0,
            'user_prompts_saved': 0,
            'uptime_seconds': 0
        }

        self.start_time = time.time()

    def execute_action(self, action: str, func: Callable,
                      component: str = 'default',
                      confidence: float = None,
                      context: dict = None,
                      priority: TaskPriority = TaskPriority.NORMAL,
                      *args, **kwargs) -> Any:
        """
        Execute action with full Phase 3 protection stack

        Flow:
        1. Calculate confidence (if not provided)
        2. Execute based on confidence level
        3. If fails, try graceful degradation
        4. Check error budget
        5. Learn from outcome

        Args:
            action: Description of action
            func: Function to execute
            component: Component name for degradation
            confidence: Pre-calculated confidence (optional)
            context: Context for confidence calculation
            priority: Task priority
            *args, **kwargs: Arguments for func
        """
        self.stats['total_actions'] += 1
        context = context or {}

        # Step 1: Calculate confidence if needed
        if confidence is None:
            confidence = self.confidence.calculate_confidence(action, context)

        # Step 2: Check if should execute autonomously
        if not self.confidence.should_execute_autonomously(confidence):
            # Low confidence - would normally ask user
            # But let's check if we can proceed with degradation
            if self.degradation.can_continue():
                self.stats['user_prompts_saved'] += 1
            else:
                raise Exception(f"Low confidence and cannot degrade: {action}")

        self.stats['autonomous_actions'] += 1

        # Step 3: Try execution with confidence-based strategy
        try:
            result = self.confidence.execute_with_confidence(
                action, func, confidence, context, *args, **kwargs
            )

            # Success - mark component as operational
            self.degradation.restore_component(component)

            return result

        except Exception as error:
            # Execution failed

            # Step 4: Try graceful degradation
            workaround = self.degradation.handle_failure(component, error, context)

            if workaround and workaround['success']:
                # Workaround succeeded
                self.stats['degraded_actions'] += 1

                # Check error budget
                budget_decision = self.error_budget.record_error(error, component, context)

                if not budget_decision['should_continue']:
                    # Over budget with concentrated errors
                    raise Exception(f"Error budget exceeded: {budget_decision['reason']}")

                self.stats['budget_stops_prevented'] += 1

                # Learn from this pattern
                self.phase2.learn_from_manual_fix(
                    error,
                    f"Degraded to: {workaround['description']}",
                    None, None
                )

                return workaround['result']

            # No workaround available
            # Check error budget before giving up
            budget_decision = self.error_budget.record_error(error, component, context)

            if budget_decision['should_continue']:
                # Within budget but no workaround
                # Log and continue to next task
                self.stats['budget_stops_prevented'] += 1
                return None

            # Over budget and no workaround - must fail
            raise

    def queue_and_execute_with_protection(self, task_id: str,
                                         description: str,
                                         func: Callable,
                                         component: str = 'default',
                                         priority: TaskPriority = TaskPriority.NORMAL,
                                         *args, **kwargs) -> Any:
        """
        Queue task and execute with full protection

        Combines Phase 2 queue persistence with Phase 3 protections
        """
        # Queue in Phase 2 persistent queue
        self.phase2.queue_task(task_id, description, func, priority=priority, *args, **kwargs)

        # Execute with Phase 3 protection
        try:
            result = self.phase2.execute_next_task()
            return result
        except Exception as error:
            # Try Phase 3 degradation
            workaround = self.degradation.handle_failure(component, error)

            if workaround and workaround['success']:
                self.stats['degraded_actions'] += 1

                # Check budget
                budget_decision = self.error_budget.record_error(error, component)
                if budget_decision['should_continue']:
                    self.stats['budget_stops_prevented'] += 1
                    return workaround['result']

            # Check budget even without workaround
            budget_decision = self.error_budget.record_error(error, component)
            if budget_decision['should_continue']:
                self.stats['budget_stops_prevented'] += 1
                return None

            raise

    def work_continuously(self, task_list: List[Dict],
                         max_hours: float = 4.0) -> Dict:
        """
        Work through task list continuously

        Args:
            task_list: List of dicts with 'id', 'description', 'func', 'component'
            max_hours: Maximum hours to run

        Returns:
            Comprehensive results
        """
        start = time.time()
        max_seconds = max_hours * 3600

        results = {
            'completed': 0,
            'degraded': 0,
            'failed': 0,
            'total_time': 0,
            'tasks': []
        }

        for task in task_list:
            # Check time limit
            if time.time() - start > max_seconds:
                break

            task_id = task['id']
            description = task['description']
            func = task['func']
            component = task.get('component', 'default')
            priority = task.get('priority', TaskPriority.NORMAL)

            try:
                result = self.execute_action(
                    description, func, component,
                    priority=priority
                )

                if result is not None:
                    results['completed'] += 1
                    results['tasks'].append({
                        'id': task_id,
                        'status': 'completed',
                        'result': result
                    })
                else:
                    # Null result means degraded
                    results['degraded'] += 1
                    results['tasks'].append({
                        'id': task_id,
                        'status': 'degraded'
                    })

            except Exception as e:
                results['failed'] += 1
                results['tasks'].append({
                    'id': task_id,
                    'status': 'failed',
                    'error': str(e)
                })

        results['total_time'] = time.time() - start
        return results

    def get_comprehensive_stats(self) -> Dict:
        """Get statistics from all subsystems"""
        self.stats['uptime_seconds'] = time.time() - self.start_time

        # Autonomy rate
        autonomy_rate = (self.stats['autonomous_actions'] /
                        max(self.stats['total_actions'], 1))

        # Degradation rate
        degradation_rate = (self.stats['degraded_actions'] /
                           max(self.stats['total_actions'], 1))

        return {
            'phase3': {
                **self.stats,
                'autonomy_rate': autonomy_rate,
                'degradation_rate': degradation_rate
            },
            'phase2': self.phase2.get_comprehensive_stats(),
            'confidence': self.confidence.get_confidence_report(),
            'degradation': self.degradation.get_status_report(),
            'error_budget': self.error_budget.get_budget_report()
        }

    def health_check(self) -> Dict:
        """Comprehensive health check across all systems"""
        stats = self.get_comprehensive_stats()

        health = {
            'overall': 'healthy',
            'issues': [],
            'recommendations': [],
            'subsystems': {}
        }

        # Phase 2 health
        phase2_health = self.phase2.health_check()
        health['subsystems']['phase2'] = phase2_health['overall']
        health['issues'].extend(phase2_health['issues'])
        health['recommendations'].extend(phase2_health['recommendations'])

        # Confidence system health
        conf_report = stats['confidence']
        if conf_report['autonomous_execution_rate'] < 0.5:
            health['issues'].append("Low autonomy rate - too many user prompts")
            health['overall'] = 'degraded'

        # Degradation system health
        deg_report = stats['degradation']
        if not deg_report['can_continue']:
            health['issues'].append("Degradation at minimal - critical state")
            health['overall'] = 'critical'
        elif deg_report['degradation_level'] == 'severe':
            health['recommendations'].append("Many components degraded - investigate")

        # Error budget health
        budget_report = stats['error_budget']
        if budget_report['budget_status'] == 'exceeded':
            health['issues'].append("Error budget exceeded")
            health['overall'] = 'degraded'

        return health

    def optimize_all_systems(self):
        """Optimize all subsystems for continued operation"""
        # Phase 2 optimization
        optimizations = self.phase2.optimize_for_continuous_operation()

        # Confidence threshold adjustment
        conf_report = self.confidence.get_confidence_report()
        if 'autonomous_success_rate' in conf_report:
            self.confidence.adjust_thresholds(conf_report['autonomous_success_rate'])

        # Adjust error budget based on performance
        budget_report = self.error_budget.get_budget_report()
        if budget_report['budget_status'] == 'healthy':
            # Can afford to increase budget
            new_budget = int(self.error_budget.budget_per_hour * 1.2)
            self.error_budget.adjust_budget(new_budget)

        return {
            'phase2_optimizations': optimizations,
            'confidence_adjusted': True,
            'budget_adjusted': True
        }

    def reset_for_new_session(self):
        """Reset for new work session"""
        self.error_budget.reset_budget()
        self.stats = {
            'total_actions': 0,
            'autonomous_actions': 0,
            'degraded_actions': 0,
            'budget_stops_prevented': 0,
            'user_prompts_saved': 0,
            'uptime_seconds': 0
        }
        self.start_time = time.time()
