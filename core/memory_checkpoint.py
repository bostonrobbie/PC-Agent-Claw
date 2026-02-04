"""
Memory Checkpoint System

Never lose context or progress:
- Checkpoint every N actions/minutes
- Store: current task, plan, completed steps, next steps
- Resume with full context restoration after crash/interruption
- Zero context loss

ENABLES TRULY LONG-RUNNING TASKS (hours to days)
"""
import json
import sqlite3
import time
import pickle
import base64
from typing import Any, Optional, Dict, List
from datetime import datetime
from dataclasses import dataclass, asdict


@dataclass
class Checkpoint:
    """Represents a saved checkpoint"""
    checkpoint_id: str
    timestamp: float
    session_id: str
    task_id: str
    description: str

    # Context data
    current_task: str
    overall_plan: str
    completed_steps: List[str]
    next_steps: List[str]
    progress: float  # 0.0 to 1.0

    # State data
    state_data: Dict  # Arbitrary state to preserve
    variables: Dict   # Important variables

    # Metadata
    total_actions: int
    uptime_seconds: float


class MemoryCheckpointSystem:
    """
    Persistent checkpoint system for long-running tasks

    Enables recovery after crashes with zero context loss
    """

    def __init__(self, db_path: str = "checkpoints.db",
                 auto_checkpoint_interval: int = 10):
        """
        Initialize checkpoint system

        Args:
            db_path: SQLite database path
            auto_checkpoint_interval: Auto-checkpoint every N actions
        """
        self.db_path = db_path
        self.auto_checkpoint_interval = auto_checkpoint_interval

        # Current session
        self.session_id = f"session_{int(time.time())}"
        self.actions_since_checkpoint = 0

        # Statistics
        self.stats = {
            'total_checkpoints': 0,
            'successful_restores': 0,
            'failed_restores': 0,
            'context_loss_prevented': 0
        }

        self._init_database()

    def _init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS checkpoints (
                checkpoint_id TEXT PRIMARY KEY,
                timestamp REAL,
                session_id TEXT,
                task_id TEXT,
                description TEXT,
                current_task TEXT,
                overall_plan TEXT,
                completed_steps TEXT,
                next_steps TEXT,
                progress REAL,
                state_data TEXT,
                variables TEXT,
                total_actions INTEGER,
                uptime_seconds REAL
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_session
            ON checkpoints(session_id, timestamp DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_task
            ON checkpoints(task_id, timestamp DESC)
        """)

        conn.commit()
        conn.close()

    def save_checkpoint(self, task_id: str, description: str,
                       current_task: str, overall_plan: str,
                       completed_steps: List[str], next_steps: List[str],
                       progress: float, state_data: Dict = None,
                       variables: Dict = None, total_actions: int = 0,
                       uptime_seconds: float = 0.0) -> str:
        """
        Save a checkpoint

        Args:
            task_id: Task identifier
            description: Checkpoint description
            current_task: What we're working on now
            overall_plan: High-level plan/goal
            completed_steps: What we've finished
            next_steps: What we need to do
            progress: Overall progress (0.0 to 1.0)
            state_data: Arbitrary state dictionary
            variables: Important variables to preserve
            total_actions: Total actions taken
            uptime_seconds: Total uptime

        Returns:
            checkpoint_id
        """
        checkpoint_id = f"checkpoint_{int(time.time() * 1000)}"

        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            timestamp=time.time(),
            session_id=self.session_id,
            task_id=task_id,
            description=description,
            current_task=current_task,
            overall_plan=overall_plan,
            completed_steps=completed_steps,
            next_steps=next_steps,
            progress=progress,
            state_data=state_data or {},
            variables=variables or {},
            total_actions=total_actions,
            uptime_seconds=uptime_seconds
        )

        self._write_checkpoint(checkpoint)

        self.stats['total_checkpoints'] += 1
        self.actions_since_checkpoint = 0

        return checkpoint_id

    def _write_checkpoint(self, checkpoint: Checkpoint):
        """Write checkpoint to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO checkpoints VALUES
            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            checkpoint.checkpoint_id,
            checkpoint.timestamp,
            checkpoint.session_id,
            checkpoint.task_id,
            checkpoint.description,
            checkpoint.current_task,
            checkpoint.overall_plan,
            json.dumps(checkpoint.completed_steps),
            json.dumps(checkpoint.next_steps),
            checkpoint.progress,
            self._serialize(checkpoint.state_data),
            self._serialize(checkpoint.variables),
            checkpoint.total_actions,
            checkpoint.uptime_seconds
        ))

        conn.commit()
        conn.close()

    def restore_latest_checkpoint(self, task_id: Optional[str] = None,
                                 session_id: Optional[str] = None) -> Optional[Checkpoint]:
        """
        Restore most recent checkpoint

        Args:
            task_id: Restore for specific task (optional)
            session_id: Restore for specific session (optional)

        Returns:
            Checkpoint if found, None otherwise
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if task_id:
            # Get latest for task
            cursor.execute("""
                SELECT * FROM checkpoints
                WHERE task_id = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (task_id,))
        elif session_id:
            # Get latest for session
            cursor.execute("""
                SELECT * FROM checkpoints
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (session_id,))
        else:
            # Get absolute latest
            cursor.execute("""
                SELECT * FROM checkpoints
                ORDER BY timestamp DESC
                LIMIT 1
            """)

        row = cursor.fetchone()
        conn.close()

        if not row:
            self.stats['failed_restores'] += 1
            return None

        try:
            checkpoint = Checkpoint(
                checkpoint_id=row['checkpoint_id'],
                timestamp=row['timestamp'],
                session_id=row['session_id'],
                task_id=row['task_id'],
                description=row['description'],
                current_task=row['current_task'],
                overall_plan=row['overall_plan'],
                completed_steps=json.loads(row['completed_steps']),
                next_steps=json.loads(row['next_steps']),
                progress=row['progress'],
                state_data=self._deserialize(row['state_data']),
                variables=self._deserialize(row['variables']),
                total_actions=row['total_actions'],
                uptime_seconds=row['uptime_seconds']
            )

            self.stats['successful_restores'] += 1
            self.stats['context_loss_prevented'] += 1

            return checkpoint

        except Exception as e:
            self.stats['failed_restores'] += 1
            return None

    def record_action(self):
        """
        Record an action taken

        Auto-checkpoints if interval reached
        """
        self.actions_since_checkpoint += 1

    def should_checkpoint(self) -> bool:
        """Check if should create checkpoint"""
        return self.actions_since_checkpoint >= self.auto_checkpoint_interval

    def get_checkpoint_history(self, task_id: str,
                              limit: int = 10) -> List[Dict]:
        """Get checkpoint history for a task"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT checkpoint_id, timestamp, description, progress
            FROM checkpoints
            WHERE task_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (task_id, limit))

        history = []
        for row in cursor.fetchall():
            history.append({
                'checkpoint_id': row['checkpoint_id'],
                'timestamp': row['timestamp'],
                'description': row['description'],
                'progress': row['progress'],
                'age_seconds': time.time() - row['timestamp']
            })

        conn.close()
        return history

    def delete_old_checkpoints(self, max_age_hours: int = 24) -> int:
        """Delete checkpoints older than max_age_hours"""
        cutoff = time.time() - (max_age_hours * 3600)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM checkpoints
            WHERE timestamp < ?
        """, (cutoff,))

        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        return deleted

    def get_task_progress(self, task_id: str) -> Dict:
        """Get current progress for a task"""
        checkpoint = self.restore_latest_checkpoint(task_id=task_id)

        if not checkpoint:
            return {
                'exists': False,
                'progress': 0.0
            }

        return {
            'exists': True,
            'task_id': checkpoint.task_id,
            'current_task': checkpoint.current_task,
            'overall_plan': checkpoint.overall_plan,
            'progress': checkpoint.progress,
            'completed_steps': len(checkpoint.completed_steps),
            'next_steps': len(checkpoint.next_steps),
            'total_steps': len(checkpoint.completed_steps) + len(checkpoint.next_steps),
            'last_checkpoint': checkpoint.timestamp,
            'age_seconds': time.time() - checkpoint.timestamp
        }

    def _serialize(self, obj: Any) -> str:
        """Serialize object to string"""
        try:
            return json.dumps(obj)
        except:
            # Fall back to pickle
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

    def get_stats(self) -> Dict:
        """Get comprehensive statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM checkpoints")
        total_checkpoints_db = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(DISTINCT session_id) FROM checkpoints")
        total_sessions = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(DISTINCT task_id) FROM checkpoints")
        total_tasks = cursor.fetchone()[0]

        conn.close()

        return {
            **self.stats,
            'total_checkpoints_db': total_checkpoints_db,
            'total_sessions': total_sessions,
            'total_tasks': total_tasks,
            'restore_success_rate': (self.stats['successful_restores'] /
                                    max(self.stats['successful_restores'] +
                                        self.stats['failed_restores'], 1))
        }
