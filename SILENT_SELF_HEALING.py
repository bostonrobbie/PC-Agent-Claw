#!/usr/bin/env python3
"""
SILENT SELF-HEALING - No Notification Spam

Automatically recovers from stops WITHOUT bothering the user.

User feedback (message 426):
"I don't want to get annoyed by all the texts can we just have
a self healing function running in the background fixing it"

HOW IT WORKS:
1. Monitors for stops in background
2. Automatically resumes work when detected
3. NO notifications (silent operation)
4. Only alerts if recovery fails multiple times
5. Logs everything for debugging

GUARANTEE:
- Work continues automatically
- No notification spam
- Silent background operation
- Only escalates if truly broken
"""

import sys
import os
import time
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.self_healing_system import WorkflowAutoRecovery
from core.continuous_workflow import ContinuousWorkflowSystem

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SilentSelfHealing:
    """
    Complete self-healing system with ZERO notification spam

    User doesn't need to know about stops - system just fixes them
    """

    def __init__(self):
        # Initialize workflow tracking
        self.workflow = ContinuousWorkflowSystem("silent_healing.db")

        # Initialize self-healing with auto-recovery
        self.auto_recovery = WorkflowAutoRecovery(self.workflow)

        logger.info("Silent self-healing system initialized")

    def start_work(self, task_id: str, description: str, subtasks: list,
                   work_function: callable):
        """
        Start work with silent auto-recovery

        Args:
            task_id: Unique identifier
            description: What we're doing
            subtasks: All work to complete
            work_function: Function(task_id, remaining_subtasks) -> bool

        Returns:
            Task object
        """
        task = self.auto_recovery.start_self_healing_task(
            task_id=task_id,
            description=description,
            subtasks=subtasks,
            work_function=work_function
        )

        logger.info(f"Started self-healing work: {description}")
        logger.info(f"  {len(subtasks)} subtasks")
        logger.info(f"  Auto-recovery: ENABLED")
        logger.info(f"  Notifications: SILENT")

        return task

    def do_work(self, task_id: str, subtask: str):
        """
        Complete a subtask

        Automatically updates recovery state
        """
        self.auto_recovery.complete_subtask(task_id, subtask)
        logger.info(f"Completed: {subtask}")

    def finish_work(self, task_id: str):
        """
        Finish all work

        Stops self-healing monitoring
        """
        result = self.auto_recovery.finish_task(task_id)
        logger.info(f"Work completed: {task_id}")
        return result

    def get_status(self) -> dict:
        """Get current system status"""
        stats = self.auto_recovery.healing.get_stats()

        return {
            'working': stats['is_working'],
            'current_task': stats['current_task'],
            'auto_recoveries': stats['total_recoveries'],
            'mode': 'SILENT (no notifications)'
        }


def example_continuous_work():
    """
    Example showing self-healing in action

    Simulates work that stops and auto-recovers WITHOUT notifications
    """
    print("="*80)
    print("SILENT SELF-HEALING DEMONSTRATION")
    print("="*80)

    healing = SilentSelfHealing()

    # Define work function that can be auto-resumed
    def do_my_work(task_id, remaining_tasks):
        """Work function that processes remaining tasks"""
        print(f"\n[Auto-Resume] Processing {len(remaining_tasks)} remaining tasks")

        # Process a few tasks
        for task in remaining_tasks[:2]:
            print(f"  Working on: {task}")
            time.sleep(0.5)
            healing.do_work(task_id, task)

        return True  # Indicate progress was made

    # Start work
    print("\n1. Starting work with self-healing...")
    task = healing.start_work(
        task_id='demo_task',
        description='Build 5 systems',
        subtasks=[
            'Build system 1',
            'Build system 2',
            'Build system 3',
            'Build system 4',
            'Build system 5',
            'Test all',
            'Verify all',
            'Commit all'
        ],
        work_function=do_my_work
    )

    print("\n2. Doing initial work...")
    healing.do_work('demo_task', 'Build system 1')
    healing.do_work('demo_task', 'Build system 2')

    print("\n3. Simulating STOP (30 seconds idle)...")
    print("   Self-healing will auto-resume work silently...")
    print("   NO notifications sent to user")

    # Wait for auto-recovery
    time.sleep(35)

    print("\n4. Checking if work auto-resumed...")
    status = healing.get_status()
    print(f"   Auto-recoveries: {status['auto_recoveries']}")
    print(f"   Mode: {status['mode']}")

    # Finish remaining work manually
    print("\n5. Finishing remaining work...")
    remaining = ['Build system 3', 'Build system 4', 'Build system 5',
                 'Test all', 'Verify all', 'Commit all']

    for subtask in remaining:
        if subtask not in ['Build system 1', 'Build system 2']:
            healing.do_work('demo_task', subtask)

    # Complete
    healing.finish_work('demo_task')

    print("\n" + "="*80)
    print("RESULT: Work completed with silent auto-recovery")
    print("User received ZERO notifications")
    print("System handled stops automatically")
    print("="*80)


if __name__ == '__main__':
    example_continuous_work()
