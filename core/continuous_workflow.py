"""
Continuous Workflow System - CRITICAL IMPROVEMENT #4

Ensures AI never stops working until task is 100% complete.
Learned from user feedback: "Why do you keep stopping?"

This system:
1. Tracks task completion state
2. Automatically continues work if incomplete
3. Validates all subtasks before claiming done
4. Prevents premature stopping
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Task:
    """Represents a task with completion tracking"""
    id: str
    description: str
    subtasks: List[str]
    completed_subtasks: List[str]
    verification_required: bool
    verified: bool
    claimed_done: bool
    actually_done: bool


class ContinuousWorkflowSystem:
    """
    Prevents stopping until work is 100% complete

    Critical learned behavior from user feedback.
    """

    def __init__(self, db_path: str = "continuous_workflow.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database for tracking work"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                description TEXT,
                subtasks TEXT,  -- JSON array
                completed_subtasks TEXT,  -- JSON array
                verification_required INTEGER DEFAULT 1,
                verified INTEGER DEFAULT 0,
                claimed_done INTEGER DEFAULT 0,
                actually_done INTEGER DEFAULT 0,
                started_at TEXT,
                completed_at TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS work_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT,
                action TEXT,
                timestamp TEXT,
                notes TEXT,
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stop_prevention_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT,
                reason TEXT,
                prevented_at TEXT,
                continued_with TEXT
            )
        ''')

        conn.commit()
        conn.close()

    def start_task(self, task_id: str, description: str, subtasks: List[str],
                   verification_required: bool = True) -> Task:
        """
        Start tracking a new task

        Args:
            task_id: Unique task identifier
            description: What the task is
            subtasks: List of subtasks that must be completed
            verification_required: Whether to verify before claiming done

        Returns:
            Task object
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO tasks
            (id, description, subtasks, completed_subtasks, verification_required,
             verified, claimed_done, actually_done, started_at)
            VALUES (?, ?, ?, ?, ?, 0, 0, 0, ?)
        ''', (
            task_id,
            description,
            json.dumps(subtasks),
            json.dumps([]),
            1 if verification_required else 0,
            datetime.now().isoformat()
        ))

        self._log_action(cursor, task_id, "started", f"Task with {len(subtasks)} subtasks")

        conn.commit()
        conn.close()

        return self.get_task(task_id)

    def complete_subtask(self, task_id: str, subtask: str) -> bool:
        """
        Mark a subtask as complete

        Args:
            task_id: Task identifier
            subtask: Subtask that was completed

        Returns:
            True if subtask was marked complete
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT completed_subtasks FROM tasks WHERE id = ?', (task_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False

        completed = json.loads(row[0])
        if subtask not in completed:
            completed.append(subtask)

        cursor.execute('''
            UPDATE tasks SET completed_subtasks = ? WHERE id = ?
        ''', (json.dumps(completed), task_id))

        self._log_action(cursor, task_id, "subtask_completed", subtask)

        conn.commit()
        conn.close()

        return True

    def check_should_stop(self, task_id: str) -> Dict:
        """
        Check if it's OK to stop working

        This is the CRITICAL function that prevents premature stopping.

        Returns:
            {
                'should_stop': bool,
                'reason': str,
                'missing_work': List[str],
                'verification_status': str
            }
        """
        task = self.get_task(task_id)
        if not task:
            return {
                'should_stop': True,
                'reason': 'Task not found',
                'missing_work': [],
                'verification_status': 'unknown'
            }

        completed = set(task.completed_subtasks)
        required = set(task.subtasks)
        missing = required - completed

        # RULE 1: Can't stop if subtasks incomplete
        if missing:
            self._log_stop_prevention(
                task_id,
                f"{len(missing)} subtasks incomplete",
                f"Continue with: {list(missing)}"
            )
            return {
                'should_stop': False,
                'reason': f'{len(missing)} subtasks still incomplete',
                'missing_work': list(missing),
                'verification_status': 'not_applicable'
            }

        # RULE 2: Can't stop if verification required but not done
        if task.verification_required and not task.verified:
            self._log_stop_prevention(
                task_id,
                "Verification required but not completed",
                "Run verification tests"
            )
            return {
                'should_stop': False,
                'reason': 'Verification required but not completed',
                'missing_work': ['Run verification tests'],
                'verification_status': 'required_not_done'
            }

        # RULE 3: OK to stop - everything is complete
        return {
            'should_stop': True,
            'reason': 'All work complete and verified',
            'missing_work': [],
            'verification_status': 'complete' if task.verified else 'not_required'
        }

    def verify_task(self, task_id: str, verification_passed: bool,
                    verification_notes: str = "") -> bool:
        """
        Record task verification results

        Args:
            task_id: Task identifier
            verification_passed: Whether verification succeeded
            verification_notes: Details about verification

        Returns:
            True if verification was recorded
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE tasks SET verified = ? WHERE id = ?
        ''', (1 if verification_passed else 0, task_id))

        self._log_action(
            cursor, task_id, "verified",
            f"{'PASSED' if verification_passed else 'FAILED'}: {verification_notes}"
        )

        conn.commit()
        conn.close()

        return True

    def mark_complete(self, task_id: str) -> Dict:
        """
        Attempt to mark task as complete

        This will FAIL if task is not actually complete.

        Returns:
            {
                'success': bool,
                'message': str,
                'task_complete': bool
            }
        """
        # Check if we SHOULD stop
        check = self.check_should_stop(task_id)

        if not check['should_stop']:
            return {
                'success': False,
                'message': check['reason'],
                'task_complete': False,
                'missing_work': check['missing_work']
            }

        # OK to mark complete
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE tasks
            SET claimed_done = 1, actually_done = 1, completed_at = ?
            WHERE id = ?
        ''', (datetime.now().isoformat(), task_id))

        self._log_action(cursor, task_id, "completed", "Task fully complete")

        conn.commit()
        conn.close()

        return {
            'success': True,
            'message': 'Task completed successfully',
            'task_complete': True
        }

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get current task state"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return Task(
            id=row[0],
            description=row[1],
            subtasks=json.loads(row[2]),
            completed_subtasks=json.loads(row[3]),
            verification_required=bool(row[4]),
            verified=bool(row[5]),
            claimed_done=bool(row[6]),
            actually_done=bool(row[7])
        )

    def get_work_summary(self, task_id: str) -> Dict:
        """Get summary of work completed and remaining"""
        task = self.get_task(task_id)
        if not task:
            return {'error': 'Task not found'}

        completed = set(task.completed_subtasks)
        required = set(task.subtasks)

        return {
            'task_id': task_id,
            'description': task.description,
            'total_subtasks': len(required),
            'completed_subtasks': len(completed),
            'remaining_subtasks': len(required - completed),
            'completion_percentage': (len(completed) / len(required) * 100) if required else 0,
            'verified': task.verified,
            'can_claim_done': len(required - completed) == 0 and (task.verified or not task.verification_required),
            'missing_work': list(required - completed)
        }

    def _log_action(self, cursor, task_id: str, action: str, notes: str = ""):
        """Log an action in the work session"""
        cursor.execute('''
            INSERT INTO work_sessions (task_id, action, timestamp, notes)
            VALUES (?, ?, ?, ?)
        ''', (task_id, action, datetime.now().isoformat(), notes))

    def _log_stop_prevention(self, task_id: str, reason: str, continued_with: str):
        """Log when we prevented premature stopping"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO stop_prevention_log (task_id, reason, prevented_at, continued_with)
            VALUES (?, ?, ?, ?)
        ''', (task_id, reason, datetime.now().isoformat(), continued_with))

        conn.commit()
        conn.close()

    def get_stop_prevention_stats(self) -> Dict:
        """Get statistics on how many times we prevented stopping"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM stop_prevention_log')
        total_preventions = cursor.fetchone()[0]

        cursor.execute('''
            SELECT reason, COUNT(*) as count
            FROM stop_prevention_log
            GROUP BY reason
            ORDER BY count DESC
        ''')
        reasons = cursor.fetchall()

        conn.close()

        return {
            'total_stops_prevented': total_preventions,
            'top_reasons': [{'reason': r[0], 'count': r[1]} for r in reasons]
        }


# Example usage
if __name__ == '__main__':
    system = ContinuousWorkflowSystem()

    # Start a task with subtasks
    task = system.start_task(
        'build_5_systems',
        'Build all 5 advanced AI systems',
        [
            'Build self-improvement loop',
            'Build capability synergy',
            'Build real-world testing',
            'Build Telegram integration',
            'Build relationship memory',
            'Test all systems',
            'Verify everything works',
            'Commit to GitHub'
        ],
        verification_required=True
    )

    print(f"Started task: {task.description}")
    print(f"Subtasks: {len(task.subtasks)}")

    # Complete some subtasks
    system.complete_subtask('build_5_systems', 'Build self-improvement loop')
    system.complete_subtask('build_5_systems', 'Build capability synergy')

    # Try to stop - should FAIL
    check = system.check_should_stop('build_5_systems')
    print(f"\nCan we stop? {check['should_stop']}")
    print(f"Reason: {check['reason']}")
    print(f"Missing work: {check['missing_work']}")

    # Complete all remaining
    for subtask in task.subtasks[2:]:
        system.complete_subtask('build_5_systems', subtask)

    # Verify
    system.verify_task('build_5_systems', True, "All tests passed")

    # Now try to stop - should SUCCEED
    check = system.check_should_stop('build_5_systems')
    print(f"\nCan we stop now? {check['should_stop']}")
    print(f"Reason: {check['reason']}")

    # Mark complete
    result = system.mark_complete('build_5_systems')
    print(f"\nTask completion: {result['message']}")

    # Get stats
    stats = system.get_stop_prevention_stats()
    print(f"\nStops prevented: {stats['total_stops_prevented']}")
