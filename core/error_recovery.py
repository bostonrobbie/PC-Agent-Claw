"""
Error Recovery & Auto-Resume System

Handles the "stopped typing" problem where tasks are interrupted.
Provides checkpointing, auto-resume, and graceful failure handling.

Author: AI Self-Improvement System
Created: 2026-02-03
"""

import sqlite3
import json
import os
import traceback
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import time


class TaskStatus(Enum):
    """Status of a task"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    CHECKPOINTED = "checkpointed"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"
    RESUMED = "resumed"


@dataclass
class TaskCheckpoint:
    """A checkpoint for task recovery"""
    task_id: str
    step_number: int
    step_name: str
    state_data: Dict
    timestamp: str
    status: TaskStatus


class ErrorRecoverySystem:
    """
    Handles task interruptions and provides auto-resume capability

    This solves the "robot stopped typing" problem by:
    1. Saving progress at checkpoints
    2. Detecting when tasks fail to complete
    3. Auto-resuming from last checkpoint
    4. Notifying user of issues
    """

    def __init__(self, db_path: str = "error_recovery.db"):
        self.db_path = db_path
        self.current_task = None
        self.checkpoints = []
        self._init_db()

    def _init_db(self):
        """Initialize database"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Tasks table
        c.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                task_name TEXT NOT NULL,
                total_steps INTEGER,
                current_step INTEGER DEFAULT 0,
                status TEXT NOT NULL,
                context TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT
            )
        ''')

        # Checkpoints table
        c.execute('''
            CREATE TABLE IF NOT EXISTS checkpoints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                step_number INTEGER NOT NULL,
                step_name TEXT NOT NULL,
                state_data TEXT,
                status TEXT NOT NULL,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks (task_id)
            )
        ''')

        # Errors table
        c.execute('''
            CREATE TABLE IF NOT EXISTS errors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT,
                error_type TEXT NOT NULL,
                error_message TEXT NOT NULL,
                traceback TEXT,
                recovery_attempted INTEGER DEFAULT 0,
                recovery_successful INTEGER DEFAULT 0,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks (task_id)
            )
        ''')

        # Recovery attempts table
        c.execute('''
            CREATE TABLE IF NOT EXISTS recovery_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                checkpoint_id INTEGER,
                attempt_number INTEGER NOT NULL,
                strategy TEXT NOT NULL,
                success INTEGER DEFAULT 0,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks (task_id)
            )
        ''')

        conn.commit()
        conn.close()

    def start_task(self, task_id: str, task_name: str, total_steps: int, context: Dict = None) -> str:
        """Start a new recoverable task"""

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Check if task already exists (resuming)
        c.execute('SELECT status FROM tasks WHERE task_id = ?', (task_id,))
        existing = c.fetchone()

        if existing:
            if existing[0] in ['interrupted', 'failed']:
                # Resume task
                c.execute('''
                    UPDATE tasks
                    SET status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE task_id = ?
                ''', (TaskStatus.RESUMED.value, task_id))
                print(f"[Recovery] Resuming task: {task_name} (ID: {task_id})")
            else:
                print(f"[Recovery] Task already exists with status: {existing[0]}")
        else:
            # New task
            c.execute('''
                INSERT INTO tasks (task_id, task_name, total_steps, status, context)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                task_id,
                task_name,
                total_steps,
                TaskStatus.IN_PROGRESS.value,
                json.dumps(context) if context else None
            ))
            print(f"[Recovery] Started task: {task_name} (ID: {task_id}, {total_steps} steps)")

        conn.commit()
        conn.close()

        self.current_task = task_id
        return task_id

    def checkpoint(self, task_id: str, step_number: int, step_name: str, state_data: Dict = None):
        """Save a checkpoint for recovery"""

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Save checkpoint
        c.execute('''
            INSERT INTO checkpoints (task_id, step_number, step_name, state_data, status)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            task_id,
            step_number,
            step_name,
            json.dumps(state_data) if state_data else None,
            TaskStatus.CHECKPOINTED.value
        ))

        # Update task progress
        c.execute('''
            UPDATE tasks
            SET current_step = ?, updated_at = CURRENT_TIMESTAMP
            WHERE task_id = ?
        ''', (step_number, task_id))

        conn.commit()
        conn.close()

        print(f"[Recovery] Checkpoint saved: Step {step_number}/{self._get_total_steps(task_id)} - {step_name}")

    def _get_total_steps(self, task_id: str) -> int:
        """Get total steps for task"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT total_steps FROM tasks WHERE task_id = ?', (task_id,))
        result = c.fetchone()
        conn.close()
        return result[0] if result else 0

    def complete_task(self, task_id: str):
        """Mark task as completed"""

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute('''
            UPDATE tasks
            SET status = ?, completed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE task_id = ?
        ''', (TaskStatus.COMPLETED.value, task_id))

        conn.commit()
        conn.close()

        print(f"[Recovery] Task completed: {task_id}")
        self.current_task = None

    def record_error(self, task_id: str, error: Exception, error_type: str = None):
        """Record an error for later recovery"""

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        error_msg = str(error)
        error_trace = traceback.format_exc()

        c.execute('''
            INSERT INTO errors (task_id, error_type, error_message, traceback)
            VALUES (?, ?, ?, ?)
        ''', (
            task_id,
            error_type or type(error).__name__,
            error_msg,
            error_trace
        ))

        # Mark task as failed
        c.execute('''
            UPDATE tasks
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE task_id = ?
        ''', (TaskStatus.FAILED.value, task_id))

        conn.commit()
        conn.close()

        print(f"[Recovery] Error recorded for task {task_id}: {error_msg}")

    def get_last_checkpoint(self, task_id: str) -> Optional[TaskCheckpoint]:
        """Get the last checkpoint for resuming"""

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute('''
            SELECT task_id, step_number, step_name, state_data, timestamp, status
            FROM checkpoints
            WHERE task_id = ?
            ORDER BY step_number DESC
            LIMIT 1
        ''', (task_id,))

        row = c.fetchone()
        conn.close()

        if row:
            return TaskCheckpoint(
                task_id=row[0],
                step_number=row[1],
                step_name=row[2],
                state_data=json.loads(row[3]) if row[3] else {},
                timestamp=row[4],
                status=TaskStatus(row[5])
            )
        return None

    def get_incomplete_tasks(self) -> List[Dict]:
        """Get tasks that didn't complete (for auto-resume)"""

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute('''
            SELECT task_id, task_name, total_steps, current_step, status, context, created_at
            FROM tasks
            WHERE status IN (?, ?, ?)
            ORDER BY updated_at DESC
        ''', (
            TaskStatus.IN_PROGRESS.value,
            TaskStatus.INTERRUPTED.value,
            TaskStatus.FAILED.value
        ))

        tasks = []
        for row in c.fetchall():
            tasks.append({
                'task_id': row[0],
                'task_name': row[1],
                'total_steps': row[2],
                'current_step': row[3],
                'status': row[4],
                'context': json.loads(row[5]) if row[5] else {},
                'created_at': row[6]
            })

        conn.close()
        return tasks

    def attempt_recovery(self, task_id: str, recovery_function: Callable) -> bool:
        """
        Attempt to recover a failed task

        Args:
            task_id: The task to recover
            recovery_function: Function that takes (checkpoint) and continues the task

        Returns:
            True if recovery succeeded, False otherwise
        """

        checkpoint = self.get_last_checkpoint(task_id)

        if not checkpoint:
            print(f"[Recovery] No checkpoint found for task {task_id}")
            return False

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Record recovery attempt
        c.execute('''
            SELECT COUNT(*) FROM recovery_attempts WHERE task_id = ?
        ''', (task_id,))
        attempt_num = c.fetchone()[0] + 1

        c.execute('''
            INSERT INTO recovery_attempts (task_id, attempt_number, strategy)
            VALUES (?, ?, ?)
        ''', (task_id, attempt_num, 'resume_from_checkpoint'))

        attempt_id = c.lastrowid
        conn.commit()
        conn.close()

        print(f"[Recovery] Attempting recovery #{attempt_num} for task {task_id}")
        print(f"[Recovery] Resuming from step {checkpoint.step_number}: {checkpoint.step_name}")

        try:
            # Call recovery function
            recovery_function(checkpoint)

            # Mark recovery successful
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('''
                UPDATE recovery_attempts
                SET success = 1
                WHERE id = ?
            ''', (attempt_id,))
            conn.commit()
            conn.close()

            print(f"[Recovery] Successfully recovered task {task_id}")
            return True

        except Exception as e:
            print(f"[Recovery] Recovery attempt failed: {str(e)}")
            self.record_error(task_id, e, "recovery_failure")
            return False

    def wrap_with_recovery(self, task_id: str, task_name: str, total_steps: int):
        """
        Decorator to wrap a function with automatic recovery

        Usage:
            @recovery.wrap_with_recovery("my_task", "My Task", 5)
            def my_function():
                recovery.checkpoint("my_task", 1, "Step 1")
                # ... do work ...
                recovery.checkpoint("my_task", 2, "Step 2")
                # ... more work ...
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                self.start_task(task_id, task_name, total_steps)
                try:
                    result = func(*args, **kwargs)
                    self.complete_task(task_id)
                    return result
                except Exception as e:
                    self.record_error(task_id, e)
                    raise
            return wrapper
        return decorator

    def get_recovery_stats(self) -> Dict:
        """Get statistics about error recovery"""

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute('SELECT COUNT(*) FROM tasks')
        total_tasks = c.fetchone()[0]

        c.execute('SELECT COUNT(*) FROM tasks WHERE status = ?', (TaskStatus.COMPLETED.value,))
        completed = c.fetchone()[0]

        c.execute('SELECT COUNT(*) FROM tasks WHERE status IN (?, ?)',
                 (TaskStatus.FAILED.value, TaskStatus.INTERRUPTED.value))
        failed = c.fetchone()[0]

        c.execute('SELECT COUNT(*) FROM recovery_attempts')
        total_attempts = c.fetchone()[0]

        c.execute('SELECT COUNT(*) FROM recovery_attempts WHERE success = 1')
        successful_recoveries = c.fetchone()[0]

        conn.close()

        success_rate = (successful_recoveries / total_attempts * 100) if total_attempts > 0 else 0

        return {
            'total_tasks': total_tasks,
            'completed': completed,
            'failed': failed,
            'recovery_attempts': total_attempts,
            'successful_recoveries': successful_recoveries,
            'recovery_success_rate': success_rate
        }


# Test and demonstration
if __name__ == "__main__":
    print("="*80)
    print("ERROR RECOVERY & AUTO-RESUME SYSTEM TEST")
    print("="*80)

    recovery = ErrorRecoverySystem()

    # Test 1: Normal task completion
    print("\n1. Testing normal task completion...")
    task_id = "test_task_1"
    recovery.start_task(task_id, "Test Task 1", total_steps=3)

    recovery.checkpoint(task_id, 1, "Initialize", {"data": "initialized"})
    time.sleep(0.1)
    recovery.checkpoint(task_id, 2, "Process", {"data": "processed"})
    time.sleep(0.1)
    recovery.checkpoint(task_id, 3, "Finalize", {"data": "finalized"})

    recovery.complete_task(task_id)
    print("   [OK] Task completed successfully")

    # Test 2: Task with error
    print("\n2. Testing task interruption...")
    task_id_2 = "test_task_2"
    recovery.start_task(task_id_2, "Test Task 2", total_steps=5)

    recovery.checkpoint(task_id_2, 1, "Step 1", {"progress": 20})
    recovery.checkpoint(task_id_2, 2, "Step 2", {"progress": 40})

    # Simulate error
    try:
        raise RuntimeError("Simulated error at step 3")
    except Exception as e:
        recovery.record_error(task_id_2, e)

    print("   [OK] Error recorded")

    # Test 3: Check incomplete tasks
    print("\n3. Checking incomplete tasks...")
    incomplete = recovery.get_incomplete_tasks()
    print(f"   Found {len(incomplete)} incomplete tasks:")
    for task in incomplete:
        print(f"   - {task['task_name']}: Step {task['current_step']}/{task['total_steps']} ({task['status']})")

    # Test 4: Recovery attempt
    print("\n4. Testing recovery...")
    def recovery_func(checkpoint: TaskCheckpoint):
        print(f"   Resuming from: {checkpoint.step_name}")
        print(f"   State: {checkpoint.state_data}")
        # Continue from where we left off
        recovery.checkpoint(task_id_2, 3, "Step 3 (recovered)", {"progress": 60})
        recovery.checkpoint(task_id_2, 4, "Step 4", {"progress": 80})
        recovery.checkpoint(task_id_2, 5, "Step 5", {"progress": 100})
        recovery.complete_task(task_id_2)

    success = recovery.attempt_recovery(task_id_2, recovery_func)
    print(f"   Recovery {'succeeded' if success else 'failed'}")

    # Test 5: Get statistics
    print("\n5. Recovery statistics...")
    stats = recovery.get_recovery_stats()
    print(f"   Total tasks: {stats['total_tasks']}")
    print(f"   Completed: {stats['completed']}")
    print(f"   Failed: {stats['failed']}")
    print(f"   Recovery attempts: {stats['recovery_attempts']}")
    print(f"   Successful recoveries: {stats['successful_recoveries']}")
    print(f"   Success rate: {stats['recovery_success_rate']:.1f}%")

    print("\n" + "="*80)
    print("[OK] ALL TESTS COMPLETE")
    print("="*80)
    print("\nThe Error Recovery System successfully demonstrated:")
    print("  1. Task tracking with checkpoints")
    print("  2. Error detection and recording")
    print("  3. Incomplete task detection")
    print("  4. Automatic recovery from checkpoints")
    print("  5. Recovery success rate tracking")
    print("\nThis solves the 'robot stopped typing' problem by saving progress")
    print("and auto-resuming from the last successful checkpoint.")
    print("="*80)
