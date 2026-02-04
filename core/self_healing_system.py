"""
Self-Healing System - SILENT AUTO-RECOVERY

Automatically recovers from stops WITHOUT spamming user with notifications.

User feedback (message 426):
"I don't want to get annoyed by all the texts can we just have
a self healing function running in the background fixing it"

SOLUTION:
- Detects when AI stops
- Automatically resumes work
- Only notifies if recovery fails
- Silent self-healing by default
"""

import time
import threading
import logging
from datetime import datetime
from typing import Optional, Callable, Dict, Any
import queue

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SelfHealingSystem:
    """
    Silent background system that auto-recovers from stops

    No notification spam - just silently fixes the problem
    """

    def __init__(self, recovery_interval: int = 30, max_recovery_attempts: int = 3):
        """
        Initialize self-healing system

        Args:
            recovery_interval: Seconds to wait before attempting recovery
            max_recovery_attempts: Max times to try recovering before alerting user
        """
        self.recovery_interval = recovery_interval
        self.max_recovery_attempts = max_recovery_attempts

        # Tracking
        self.last_activity = datetime.now()
        self.is_working = False
        self.current_task_id = None
        self.work_queue = queue.Queue()
        self.recovery_count = 0
        self.total_recoveries = 0

        # Recovery functions
        self.recovery_handlers: Dict[str, Callable] = {}
        self.task_context: Dict[str, Any] = {}

        # Threading
        self.running = False
        self.monitor_thread = None

    def start_task(self, task_id: str, task_name: str, resume_handler: Callable):
        """
        Start tracking a task with auto-recovery

        Args:
            task_id: Unique task identifier
            task_name: Human-readable task name
            resume_handler: Function to call to resume work
        """
        self.is_working = True
        self.current_task_id = task_id
        self.recovery_handlers[task_id] = resume_handler
        self.last_activity = datetime.now()
        self.recovery_count = 0

        logger.info(f"Self-healing enabled for task: {task_name}")

        # Start monitoring if not running
        if not self.running:
            self.start_monitoring()

    def heartbeat(self, context: Dict[str, Any] = None):
        """
        Record activity heartbeat

        Args:
            context: Optional context about current work state
        """
        self.last_activity = datetime.now()

        if context and self.current_task_id:
            self.task_context[self.current_task_id] = context

    def stop_task(self, task_id: str, reason: str = "completed"):
        """
        Stop tracking a task

        Args:
            task_id: Task to stop tracking
            reason: Why stopping
        """
        self.is_working = False

        if task_id in self.recovery_handlers:
            del self.recovery_handlers[task_id]

        if task_id in self.task_context:
            del self.task_context[task_id]

        logger.info(f"Self-healing disabled for {task_id}: {reason}")

    def start_monitoring(self):
        """Start background self-healing monitor"""
        if self.running:
            return

        self.running = True
        self.monitor_thread = threading.Thread(
            target=self._healing_loop,
            daemon=True
        )
        self.monitor_thread.start()

        logger.info("Self-healing monitor started (silent mode)")

    def stop_monitoring(self):
        """Stop background monitor"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)

        logger.info("Self-healing monitor stopped")

    def _healing_loop(self):
        """Background loop that auto-recovers from stops"""
        while self.running:
            try:
                if self.is_working:
                    idle_seconds = (datetime.now() - self.last_activity).total_seconds()

                    # Check if we've been idle too long
                    if idle_seconds > self.recovery_interval:
                        self._attempt_recovery()

            except Exception as e:
                logger.error(f"Healing loop error: {e}")

            time.sleep(self.recovery_interval)

    def _attempt_recovery(self):
        """Attempt to auto-recover from stop"""
        if not self.current_task_id:
            return

        if self.current_task_id not in self.recovery_handlers:
            return

        self.recovery_count += 1

        logger.info(f"Auto-recovery attempt #{self.recovery_count} for {self.current_task_id}")

        try:
            # Get recovery handler
            handler = self.recovery_handlers[self.current_task_id]

            # Get context if available
            context = self.task_context.get(self.current_task_id, {})

            # Attempt recovery
            success = handler(context)

            if success:
                # Recovery successful
                self.total_recoveries += 1
                self.recovery_count = 0
                self.heartbeat()

                logger.info(f"✓ Auto-recovery successful (total: {self.total_recoveries})")

            else:
                # Recovery failed
                if self.recovery_count >= self.max_recovery_attempts:
                    logger.error(f"Recovery failed after {self.recovery_count} attempts")
                    self._escalate_to_user()
                else:
                    logger.warning(f"Recovery attempt failed, will retry")

        except Exception as e:
            logger.error(f"Recovery error: {e}")

            if self.recovery_count >= self.max_recovery_attempts:
                self._escalate_to_user()

    def _escalate_to_user(self):
        """Only notify user if recovery repeatedly fails"""
        # This is the ONLY time we notify - when we can't fix it ourselves
        logger.critical(
            f"ESCALATION: Cannot auto-recover from stop after {self.recovery_count} attempts. "
            f"Task: {self.current_task_id}"
        )

        # Could send ONE notification here if recovery completely fails
        # But only after max attempts, not for every hiccup

    def get_stats(self) -> Dict:
        """Get self-healing statistics"""
        return {
            'is_monitoring': self.running,
            'is_working': self.is_working,
            'current_task': self.current_task_id,
            'total_recoveries': self.total_recoveries,
            'recovery_count_current': self.recovery_count,
            'last_activity': self.last_activity.isoformat()
        }


class WorkflowAutoRecovery:
    """
    Integration between self-healing and continuous workflow

    Automatically continues work when stops detected
    """

    def __init__(self, workflow_system):
        self.workflow = workflow_system
        self.healing = SelfHealingSystem(
            recovery_interval=30,  # Check every 30 seconds
            max_recovery_attempts=3  # Try 3 times before giving up
        )

        self.pending_work = {}

    def start_self_healing_task(self, task_id: str, description: str,
                                subtasks: list, work_function: Callable):
        """
        Start a task with automatic recovery

        Args:
            task_id: Task identifier
            description: What the task is
            subtasks: All subtasks to complete
            work_function: Function that does the actual work
                          Should accept (task_id, remaining_subtasks) and return bool
        """
        # Start in workflow system
        task = self.workflow.start_task(task_id, description, subtasks)

        # Store work function
        self.pending_work[task_id] = {
            'work_function': work_function,
            'subtasks': subtasks,
            'completed': []
        }

        # Create recovery handler
        def recovery_handler(context):
            """Handler that resumes work automatically"""
            try:
                # Get remaining work
                remaining = self._get_remaining_work(task_id)

                if not remaining:
                    # Nothing to recover - work is complete
                    return True

                # Resume work
                logger.info(f"Auto-resuming work: {len(remaining)} subtasks remaining")

                work_fn = self.pending_work[task_id]['work_function']
                return work_fn(task_id, remaining)

            except Exception as e:
                logger.error(f"Recovery handler error: {e}")
                return False

        # Start self-healing monitoring
        self.healing.start_task(task_id, description, recovery_handler)

        logger.info(f"Self-healing task started: {description}")

        return task

    def complete_subtask(self, task_id: str, subtask: str):
        """Complete a subtask and update recovery state"""
        # Mark in workflow
        self.workflow.complete_subtask(task_id, subtask)

        # Track for recovery
        if task_id in self.pending_work:
            self.pending_work[task_id]['completed'].append(subtask)

        # Send heartbeat
        self.healing.heartbeat({
            'task_id': task_id,
            'last_completed': subtask,
            'remaining': self._get_remaining_work(task_id)
        })

    def _get_remaining_work(self, task_id: str) -> list:
        """Get list of remaining subtasks"""
        if task_id not in self.pending_work:
            return []

        all_subtasks = self.pending_work[task_id]['subtasks']
        completed = self.pending_work[task_id]['completed']

        return [s for s in all_subtasks if s not in completed]

    def finish_task(self, task_id: str):
        """Finish task and stop self-healing"""
        # Finish in workflow
        result = self.workflow.mark_complete(task_id)

        # Stop self-healing
        self.healing.stop_task(task_id, "completed")

        # Clean up
        if task_id in self.pending_work:
            del self.pending_work[task_id]

        logger.info(f"Self-healing task completed: {task_id}")

        return result


# Simple example work function
def example_work_function(task_id: str, remaining_subtasks: list) -> bool:
    """
    Example work function that can be auto-resumed

    Args:
        task_id: Task being worked on
        remaining_subtasks: Subtasks that still need completion

    Returns:
        True if work progressed, False if failed
    """
    try:
        logger.info(f"Resuming work on {task_id}: {len(remaining_subtasks)} subtasks")

        # Do actual work here
        for subtask in remaining_subtasks:
            # ... work on subtask ...
            logger.info(f"  Working on: {subtask}")
            time.sleep(1)  # Simulate work

        return True

    except Exception as e:
        logger.error(f"Work function failed: {e}")
        return False


# Example usage
if __name__ == '__main__':
    from continuous_workflow import ContinuousWorkflowSystem

    print("="*80)
    print("SELF-HEALING SYSTEM - Silent Auto-Recovery")
    print("="*80)

    # Initialize
    workflow = ContinuousWorkflowSystem("test_healing.db")
    auto_recovery = WorkflowAutoRecovery(workflow)

    # Define work function
    def my_work(task_id, remaining):
        print(f"  Auto-resuming: {len(remaining)} tasks remaining")
        for task in remaining[:2]:  # Process 2 at a time
            print(f"    Working on: {task}")
            time.sleep(1)
            auto_recovery.complete_subtask(task_id, task)
        return True

    # Start self-healing task
    print("\nStarting self-healing task...")
    task = auto_recovery.start_self_healing_task(
        task_id='auto_healing_test',
        description='Test auto-recovery',
        subtasks=['step1', 'step2', 'step3', 'step4', 'step5'],
        work_function=my_work
    )

    # Do some work
    print("\nDoing initial work...")
    auto_recovery.complete_subtask('auto_healing_test', 'step1')
    auto_recovery.complete_subtask('auto_healing_test', 'step2')

    print("\nSimulating stop (no activity for 30+ seconds)...")
    print("Self-healing system should auto-resume work...")

    # Wait for auto-recovery to kick in
    time.sleep(35)

    # Check stats
    stats = auto_recovery.healing.get_stats()
    print(f"\nStats:")
    print(f"  Total auto-recoveries: {stats['total_recoveries']}")
    print(f"  Currently working: {stats['is_working']}")

    # Finish
    print("\nCleaning up...")
    auto_recovery.healing.stop_monitoring()

    print("\n" + "="*80)
    print("Self-healing system: SILENT, AUTOMATIC, NO SPAM")
    print("="*80)
