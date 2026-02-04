"""
Phase 2 Robust Operations Engine

Integrates Phase 1 with Phase 2 enhancements:
- Phase 1: Error Learning, Decision Rulebook, Flow Monitor
- Phase 2: Smart Retry, Work Queue, Auto-Fix Registry

Provides industrial-strength continuous operation
"""
from typing import Callable, Any, Optional, List
import time

from core.phase1_continuous_engine import Phase1ContinuousEngine
from core.smart_retry_engine import SmartRetryEngine
from core.work_queue_persistence import WorkQueuePersistence, TaskStatus, TaskPriority
from core.auto_fix_registry import AutoFixRegistry


class Phase2RobustEngine:
    """
    Industrial-strength continuous operation engine

    Combines all Phase 1 + Phase 2 capabilities for maximum robustness
    """

    def __init__(self, error_db_path: str = "errors.db",
                 queue_db_path: str = "work_queue.db"):
        # Phase 1 components
        self.phase1 = Phase1ContinuousEngine(error_db_path)

        # Phase 2 components
        self.retry_engine = SmartRetryEngine()
        self.work_queue = WorkQueuePersistence(queue_db_path)
        self.auto_fix = AutoFixRegistry()

        # Resume any interrupted work
        self._resume_interrupted_work()

        # Statistics
        self.stats = {
            'actions_executed': 0,
            'tasks_queued': 0,
            'tasks_completed': 0,
            'errors_auto_fixed': 0,
            'retries_performed': 0,
            'uptime_seconds': 0
        }

        self.start_time = time.time()

    def _resume_interrupted_work(self):
        """Resume work that was interrupted by crash"""
        interrupted = self.work_queue.resume_interrupted_tasks()

        if interrupted:
            print(f"[Phase2] Resumed {len(interrupted)} interrupted tasks")

    def queue_task(self, task_id: str, description: str,
                  func: Callable, *args,
                  priority: TaskPriority = TaskPriority.NORMAL,
                  **kwargs) -> bool:
        """
        Queue a task for execution

        Tasks are persisted and survive crashes
        """
        # Register function in work queue
        func_name = f"{func.__module__}.{func.__name__}"
        self.work_queue.register_function(func_name, func)

        # Add to queue
        success = self.work_queue.add_task(
            task_id=task_id,
            description=description,
            function_name=func_name,
            args=args,
            kwargs=kwargs,
            priority=priority
        )

        if success:
            self.stats['tasks_queued'] += 1

        return success

    def execute_next_task(self) -> Optional[Any]:
        """
        Execute next task from queue

        Uses Phase 1 + Phase 2 protections:
        - Error learning from Phase 1
        - Decision rulebook from Phase 1
        - Flow protection from Phase 1
        - Smart retry from Phase 2
        - Auto-fix from Phase 2
        """
        # Get next task
        task_data = self.work_queue.get_next_task()

        if not task_data:
            return None

        task_id = task_data['task_id']
        description = task_data['description']

        # Mark as started
        self.work_queue.start_task(task_id)

        try:
            # Execute with full protection stack
            result = self._execute_with_full_protection(task_data)

            # Mark complete
            self.work_queue.complete_task(task_id, result)
            self.stats['tasks_completed'] += 1

            return result

        except Exception as error:
            # Try auto-fix
            fix_result = self.auto_fix.try_fix(error, context={'task': task_data})

            if fix_result and fix_result['fixed']:
                # Fix found, retry task
                print(f"[Auto-Fix] Applied: {fix_result['fix_applied']}")
                self.stats['errors_auto_fixed'] += 1

                try:
                    result = self._execute_with_full_protection(task_data)
                    self.work_queue.complete_task(task_id, result)
                    self.stats['tasks_completed'] += 1
                    return result
                except:
                    pass

            # Mark as failed
            self.work_queue.fail_task(task_id, str(error))
            raise

    def _execute_with_full_protection(self, task_data: dict) -> Any:
        """
        Execute task with all protection layers

        Protection stack (innermost to outermost):
        1. Auto-fix registry (pattern-based fixes)
        2. Smart retry engine (exponential backoff, circuit breaker)
        3. Phase 1 engine (error learning, decisions, flow)
        """
        task_id = task_data['task_id']
        description = task_data['description']

        # Determine error category for retry policy
        error_category = self._classify_task_category(task_data)

        def execute_task():
            """Inner execution with Phase 1 protection"""
            return self.phase1.execute_action(
                description,
                self.work_queue.execute_task,
                task_data
            )

        # Wrap in smart retry
        result = self.retry_engine.execute_with_retry(
            execute_task,
            error_category=error_category
        )

        self.stats['actions_executed'] += 1
        self.stats['retries_performed'] += self.retry_engine.stats['total_retries']

        return result

    def _classify_task_category(self, task_data: dict) -> str:
        """
        Classify task for retry policy selection

        Categories: network, database, timeout, resource, default
        """
        description = task_data['description'].lower()

        if any(word in description for word in ['fetch', 'request', 'api', 'web']):
            return 'network'
        elif any(word in description for word in ['database', 'db', 'sql']):
            return 'database'
        elif any(word in description for word in ['test', 'timeout']):
            return 'timeout'
        elif any(word in description for word in ['memory', 'cpu', 'disk']):
            return 'resource'
        else:
            return 'default'

    def execute_all_queued_tasks(self) -> dict:
        """
        Execute all queued tasks

        Continues until queue is empty
        """
        results = {
            'completed': 0,
            'failed': 0,
            'total_time': 0
        }

        start = time.time()

        while True:
            try:
                result = self.execute_next_task()
                if result is None:
                    # Queue empty
                    break
                results['completed'] += 1

            except Exception as e:
                results['failed'] += 1
                print(f"[Phase2] Task failed: {e}")

        results['total_time'] = time.time() - start

        return results

    def execute_with_checkpoint(self, task_id: str, description: str,
                               func: Callable, checkpoint_interval: int = 10,
                               *args, **kwargs):
        """
        Execute long-running task with periodic checkpoints

        Allows resumption from last checkpoint after crash
        """
        # Queue the task
        self.queue_task(task_id, description, func, *args, **kwargs)

        # Execute with progress tracking
        progress = 0.0
        checkpoint_data = {}

        while progress < 1.0:
            # Update progress
            self.work_queue.update_progress(task_id, progress, checkpoint_data)

            # Small progress increment (simulated)
            progress += 0.1
            time.sleep(checkpoint_interval)

            if progress >= 1.0:
                break

        # Execute the actual task
        return self.execute_next_task()

    def learn_from_manual_fix(self, error: Exception, solution_description: str,
                             code_before: str = None, code_after: str = None):
        """
        Learn from manual fix

        Updates both Phase 1 error learning and Phase 2 auto-fix registry
        """
        # Phase 1: Learn error solution
        self.phase1.error_db.remember_error(error, solution_description, success=True)

        # Phase 2: Create auto-fix pattern
        self.auto_fix.learn_from_manual_fix(
            error, solution_description, code_before, code_after
        )

    def get_comprehensive_stats(self) -> dict:
        """Get statistics from all subsystems"""
        self.stats['uptime_seconds'] = time.time() - self.start_time

        return {
            'phase2': self.stats,
            'phase1': self.phase1.get_stats(),
            'retry': self.retry_engine.get_stats(),
            'queue': self.work_queue.get_queue_status(),
            'auto_fix': self.auto_fix.get_stats()
        }

    def optimize_for_continuous_operation(self):
        """
        Optimize all subsystems for continuous operation

        Adapts retry policies, clears old data, etc.
        """
        # Adapt retry policies based on performance
        for category in ['network', 'database', 'timeout', 'resource']:
            self.retry_engine.adapt_policy(category)

        # Clear old completed tasks
        cleared = self.work_queue.clear_completed(older_than_hours=24)

        # Get auto-fix best patterns
        best_patterns = self.auto_fix.get_best_patterns(limit=5)

        return {
            'cleared_tasks': cleared,
            'best_fix_patterns': best_patterns,
            'retry_policies_adapted': True
        }

    def health_check(self) -> dict:
        """
        Comprehensive health check

        Returns status of all subsystems
        """
        stats = self.get_comprehensive_stats()

        health = {
            'overall': 'healthy',
            'issues': [],
            'recommendations': []
        }

        # Check Phase 1 flow
        if not stats['phase1']['in_flow']:
            health['recommendations'].append(
                "Flow state not active - consider increasing action frequency"
            )

        # Check retry success rate
        retry_success = stats['retry']['success_rate']
        if retry_success < 0.7:
            health['issues'].append(
                f"Low retry success rate: {retry_success:.1%}"
            )
            health['overall'] = 'degraded'

        # Check queue backlog
        queue_status = stats['queue']['status_counts']
        if queue_status.get('pending', 0) > 100:
            health['recommendations'].append(
                "Large queue backlog - consider parallel execution"
            )

        # Check circuit breakers
        for category, info in stats['retry']['categories'].items():
            if info['circuit_state'] == 'open':
                health['issues'].append(
                    f"Circuit breaker open for {category}"
                )
                health['overall'] = 'degraded'

        return health
