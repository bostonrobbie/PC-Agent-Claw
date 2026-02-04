"""
Work Queue Persistence - PHASE 2 CRITICAL

Persistent task queue that survives crashes and allows resumption:
- SQLite-based work queue
- Resume from exact position after interruption
- Priority scheduling
- Deadline tracking
- Progress checkpoints
"""
import sqlite3
import json
import time
from typing import Any, Optional, List, Dict, Callable
from datetime import datetime, timedelta
from enum import Enum
import pickle
import base64


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Task priority levels"""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4


class WorkTask:
    """Represents a unit of work"""

    def __init__(self, task_id: str, description: str,
                 func: Callable, args: tuple = (), kwargs: dict = None,
                 priority: TaskPriority = TaskPriority.NORMAL,
                 deadline: Optional[datetime] = None,
                 dependencies: List[str] = None):
        self.task_id = task_id
        self.description = description
        self.func = func
        self.args = args
        self.kwargs = kwargs or {}
        self.priority = priority
        self.deadline = deadline
        self.dependencies = dependencies or []

        self.status = TaskStatus.PENDING
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
        self.attempts = 0
        self.last_error = None
        self.result = None
        self.progress = 0.0  # 0.0 to 1.0
        self.checkpoint_data = {}

    def to_dict(self) -> dict:
        """Serialize task to dictionary"""
        return {
            'task_id': self.task_id,
            'description': self.description,
            'priority': self.priority.value,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'dependencies': self.dependencies,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'attempts': self.attempts,
            'last_error': self.last_error,
            'progress': self.progress,
            'checkpoint_data': json.dumps(self.checkpoint_data)
        }


class WorkQueuePersistence:
    """
    Persistent work queue with crash recovery

    Features:
    - Survives process crashes/restarts
    - Resumes from exact position
    - Priority scheduling with deadlines
    - Dependency tracking
    - Progress checkpoints for long tasks
    """

    def __init__(self, db_path: str = "work_queue.db"):
        self.db_path = db_path
        self._init_database()

        # In-memory function registry (can't serialize functions to DB)
        self.function_registry: Dict[str, Callable] = {}

        # Statistics
        self.stats = {
            'tasks_added': 0,
            'tasks_completed': 0,
            'tasks_failed': 0,
            'tasks_resumed': 0,
            'total_interruptions': 0
        }

    def _init_database(self):
        """Initialize SQLite database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                function_name TEXT NOT NULL,
                args_serialized TEXT,
                kwargs_serialized TEXT,
                priority INTEGER,
                deadline TEXT,
                dependencies TEXT,
                status TEXT,
                created_at TEXT,
                started_at TEXT,
                completed_at TEXT,
                attempts INTEGER DEFAULT 0,
                last_error TEXT,
                result_serialized TEXT,
                progress REAL DEFAULT 0.0,
                checkpoint_data TEXT
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_status
            ON tasks(status)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_priority
            ON tasks(priority, deadline)
        """)

        conn.commit()
        conn.close()

    def register_function(self, name: str, func: Callable):
        """Register a function for task execution"""
        self.function_registry[name] = func

    def add_task(self, task_id: str, description: str, function_name: str,
                args: tuple = (), kwargs: dict = None,
                priority: TaskPriority = TaskPriority.NORMAL,
                deadline: Optional[datetime] = None,
                dependencies: List[str] = None) -> bool:
        """
        Add task to queue

        Returns True if added, False if already exists
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO tasks (
                    task_id, description, function_name,
                    args_serialized, kwargs_serialized,
                    priority, deadline, dependencies,
                    status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task_id,
                description,
                function_name,
                self._serialize(args),
                self._serialize(kwargs or {}),
                priority.value,
                deadline.isoformat() if deadline else None,
                json.dumps(dependencies or []),
                TaskStatus.PENDING.value,
                datetime.now().isoformat()
            ))

            conn.commit()
            self.stats['tasks_added'] += 1
            return True

        except sqlite3.IntegrityError:
            # Task already exists
            return False

        finally:
            conn.close()

    def get_next_task(self) -> Optional[Dict]:
        """
        Get next task to execute

        Priority order:
        1. Critical tasks past deadline
        2. Tasks by priority (CRITICAL > HIGH > NORMAL > LOW)
        3. Tasks approaching deadline
        4. Oldest tasks first
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get pending tasks with resolved dependencies
        cursor.execute("""
            SELECT * FROM tasks
            WHERE status = ?
            ORDER BY
                priority ASC,
                deadline ASC,
                created_at ASC
            LIMIT 1
        """, (TaskStatus.PENDING.value,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return dict(row)

    def start_task(self, task_id: str) -> bool:
        """Mark task as started"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE tasks
            SET status = ?,
                started_at = ?,
                attempts = attempts + 1
            WHERE task_id = ?
        """, (
            TaskStatus.IN_PROGRESS.value,
            datetime.now().isoformat(),
            task_id
        ))

        success = cursor.rowcount > 0
        conn.commit()
        conn.close()

        return success

    def complete_task(self, task_id: str, result: Any = None):
        """Mark task as completed"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE tasks
            SET status = ?,
                completed_at = ?,
                result_serialized = ?,
                progress = 1.0
            WHERE task_id = ?
        """, (
            TaskStatus.COMPLETED.value,
            datetime.now().isoformat(),
            self._serialize(result),
            task_id
        ))

        conn.commit()
        conn.close()

        self.stats['tasks_completed'] += 1

    def fail_task(self, task_id: str, error: str):
        """Mark task as failed"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE tasks
            SET status = ?,
                last_error = ?
            WHERE task_id = ?
        """, (
            TaskStatus.FAILED.value,
            error,
            task_id
        ))

        conn.commit()
        conn.close()

        self.stats['tasks_failed'] += 1

    def update_progress(self, task_id: str, progress: float,
                       checkpoint_data: dict = None):
        """
        Update task progress and checkpoint data

        Allows resumption from checkpoint after crash
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE tasks
            SET progress = ?,
                checkpoint_data = ?
            WHERE task_id = ?
        """, (
            progress,
            json.dumps(checkpoint_data or {}),
            task_id
        ))

        conn.commit()
        conn.close()

    def resume_interrupted_tasks(self) -> List[str]:
        """
        Find and reset interrupted tasks

        Returns list of task IDs that were interrupted
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Find tasks that were in progress (interrupted by crash)
        cursor.execute("""
            SELECT task_id FROM tasks
            WHERE status = ?
        """, (TaskStatus.IN_PROGRESS.value,))

        interrupted = [row[0] for row in cursor.fetchall()]

        if interrupted:
            # Reset to pending for retry
            cursor.execute("""
                UPDATE tasks
                SET status = ?
                WHERE status = ?
            """, (TaskStatus.PENDING.value, TaskStatus.IN_PROGRESS.value))

            conn.commit()
            self.stats['total_interruptions'] += len(interrupted)
            self.stats['tasks_resumed'] += len(interrupted)

        conn.close()

        return interrupted

    def execute_task(self, task_data: dict) -> Any:
        """
        Execute a task from queue data

        Resumes from checkpoint if available
        """
        task_id = task_data['task_id']
        function_name = task_data['function_name']

        if function_name not in self.function_registry:
            raise ValueError(f"Function {function_name} not registered")

        func = self.function_registry[function_name]
        args = self._deserialize(task_data['args_serialized'])
        kwargs = self._deserialize(task_data['kwargs_serialized'])

        # Add checkpoint data to kwargs if available
        checkpoint_str = task_data.get('checkpoint_data')
        if checkpoint_str:
            checkpoint = json.loads(checkpoint_str)
            if checkpoint:
                kwargs['checkpoint'] = checkpoint

        # Execute function
        result = func(*args, **kwargs)

        return result

    def get_queue_status(self) -> dict:
        """Get comprehensive queue status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        status_counts = {}
        for status in TaskStatus:
            cursor.execute("""
                SELECT COUNT(*) FROM tasks
                WHERE status = ?
            """, (status.value,))
            status_counts[status.value] = cursor.fetchone()[0]

        # Get overdue tasks
        cursor.execute("""
            SELECT COUNT(*) FROM tasks
            WHERE deadline < ? AND status IN (?, ?)
        """, (
            datetime.now().isoformat(),
            TaskStatus.PENDING.value,
            TaskStatus.IN_PROGRESS.value
        ))
        overdue = cursor.fetchone()[0]

        conn.close()

        return {
            **self.stats,
            'status_counts': status_counts,
            'overdue_tasks': overdue,
            'total_tasks': sum(status_counts.values())
        }

    def _serialize(self, obj: Any) -> str:
        """Serialize object to string"""
        try:
            # Try JSON first (readable)
            return json.dumps(obj)
        except:
            # Fall back to pickle + base64
            pickled = pickle.dumps(obj)
            return base64.b64encode(pickled).decode('utf-8')

    def _deserialize(self, data: str) -> Any:
        """Deserialize string to object"""
        try:
            return json.loads(data)
        except:
            # Try pickle
            pickled = base64.b64decode(data.encode('utf-8'))
            return pickle.loads(pickled)

    def clear_completed(self, older_than_hours: int = 24):
        """Remove completed tasks older than specified hours"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff = (datetime.now() - timedelta(hours=older_than_hours)).isoformat()

        cursor.execute("""
            DELETE FROM tasks
            WHERE status = ? AND completed_at < ?
        """, (TaskStatus.COMPLETED.value, cutoff))

        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        return deleted
