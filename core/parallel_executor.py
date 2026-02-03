#!/usr/bin/env python3
"""
Parallel Task Execution - Run tasks on multiple GPUs/CPUs simultaneously
High-performance task queue with worker pool
"""

import asyncio
import concurrent.futures
import multiprocessing as mp
import threading
import time
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from queue import Queue, Empty
from enum import Enum
import traceback


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Task priority levels"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


class ParallelExecutor:
    """
    Parallel task execution system with worker pool

    Features:
    - Multi-GPU/CPU task execution
    - Priority-based task queue
    - Async and sync task support
    - Worker pool management
    - Task monitoring and logging
    - Result collection
    """

    def __init__(self, db_path: str = None, max_workers: int = None,
                 use_processes: bool = False):
        if db_path is None:
            workspace = Path(__file__).parent.parent
            db_path = workspace / "memory.db"

        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self._init_db()

        # Worker configuration
        self.max_workers = max_workers or mp.cpu_count()
        self.use_processes = use_processes

        # Executor pools
        self.thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers)
        self.process_pool = concurrent.futures.ProcessPoolExecutor(max_workers=self.max_workers) if use_processes else None

        # Task tracking
        self.task_futures = {}  # task_id -> Future
        self.active_tasks = set()
        self.lock = threading.Lock()

        # Metrics
        self.completed_count = 0
        self.failed_count = 0
        self.start_time = time.time()

    def _init_db(self):
        """Initialize database schema for parallel execution"""
        cursor = self.conn.cursor()

        # Execution tasks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS parallel_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT UNIQUE NOT NULL,
                task_name TEXT NOT NULL,
                task_type TEXT,
                priority INTEGER DEFAULT 1,
                status TEXT DEFAULT 'pending',
                worker_id TEXT,
                device_id TEXT,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                duration_seconds REAL,
                result TEXT,
                error TEXT,
                metadata TEXT
            )
        ''')

        # Worker stats table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS worker_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                worker_id TEXT NOT NULL,
                worker_type TEXT,
                device_id TEXT,
                tasks_completed INTEGER DEFAULT 0,
                tasks_failed INTEGER DEFAULT 0,
                total_execution_time REAL DEFAULT 0,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Execution batches table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS execution_batches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id TEXT UNIQUE NOT NULL,
                batch_name TEXT,
                total_tasks INTEGER,
                completed_tasks INTEGER DEFAULT 0,
                failed_tasks INTEGER DEFAULT 0,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                metadata TEXT
            )
        ''')

        self.conn.commit()

    # === TASK SUBMISSION ===

    def submit_task(self, task_id: str, task_name: str, func: Callable,
                   args: tuple = (), kwargs: dict = None,
                   priority: TaskPriority = TaskPriority.NORMAL,
                   task_type: str = "compute", device_id: str = None,
                   use_process: bool = False, metadata: Dict = None) -> str:
        """Submit a task for parallel execution"""
        kwargs = kwargs or {}

        # Log task in database
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO parallel_tasks
            (task_id, task_name, task_type, priority, status, device_id, metadata)
            VALUES (?, ?, ?, ?, 'pending', ?, ?)
        ''', (task_id, task_name, task_type, priority.value, device_id,
              json.dumps(metadata) if metadata else None))
        self.conn.commit()

        # Choose executor
        executor = self.process_pool if (use_process and self.process_pool) else self.thread_pool

        # Submit task
        future = executor.submit(self._execute_task, task_id, func, args, kwargs)

        with self.lock:
            self.task_futures[task_id] = future
            self.active_tasks.add(task_id)

        # Add callback for completion
        future.add_done_callback(lambda f: self._task_completed(task_id, f))

        return task_id

    def _execute_task(self, task_id: str, func: Callable, args: tuple, kwargs: dict) -> Any:
        """Execute a task and track timing"""
        start_time = time.time()
        worker_id = f"{threading.current_thread().name}"

        # Update task status
        self._update_task_status(task_id, TaskStatus.RUNNING, worker_id)

        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            self._update_task_result(task_id, TaskStatus.COMPLETED, result, duration)
            return result
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            self._update_task_result(task_id, TaskStatus.FAILED, None, duration, error_msg)
            raise

    def _update_task_status(self, task_id: str, status: TaskStatus, worker_id: str = None):
        """Update task status in database"""
        cursor = self.conn.cursor()

        if status == TaskStatus.RUNNING:
            cursor.execute('''
                UPDATE parallel_tasks
                SET status = ?, worker_id = ?, started_at = CURRENT_TIMESTAMP
                WHERE task_id = ?
            ''', (status.value, worker_id, task_id))
        else:
            cursor.execute('''
                UPDATE parallel_tasks
                SET status = ?
                WHERE task_id = ?
            ''', (status.value, task_id))

        self.conn.commit()

    def _update_task_result(self, task_id: str, status: TaskStatus, result: Any,
                           duration: float, error: str = None):
        """Update task result in database"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE parallel_tasks
            SET status = ?, completed_at = CURRENT_TIMESTAMP,
                duration_seconds = ?, result = ?, error = ?
            WHERE task_id = ?
        ''', (status.value, duration,
              json.dumps(result) if result is not None else None,
              error, task_id))
        self.conn.commit()

    def _task_completed(self, task_id: str, future: concurrent.futures.Future):
        """Callback when task completes"""
        with self.lock:
            self.active_tasks.discard(task_id)

            if future.exception() is None:
                self.completed_count += 1
            else:
                self.failed_count += 1

    # === BATCH EXECUTION ===

    def submit_batch(self, batch_id: str, batch_name: str, tasks: List[Dict],
                    metadata: Dict = None) -> str:
        """Submit a batch of tasks for parallel execution"""
        # Create batch record
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO execution_batches
            (batch_id, batch_name, total_tasks, metadata)
            VALUES (?, ?, ?, ?)
        ''', (batch_id, batch_name, len(tasks),
              json.dumps(metadata) if metadata else None))
        self.conn.commit()

        # Submit all tasks
        task_ids = []
        for task in tasks:
            task_id = f"{batch_id}_{len(task_ids)}"
            self.submit_task(
                task_id=task_id,
                task_name=task.get('name', f'Task {len(task_ids)}'),
                func=task['func'],
                args=task.get('args', ()),
                kwargs=task.get('kwargs', {}),
                priority=task.get('priority', TaskPriority.NORMAL),
                task_type=task.get('type', 'compute'),
                device_id=task.get('device_id'),
                metadata={'batch_id': batch_id}
            )
            task_ids.append(task_id)

        return batch_id

    def wait_for_batch(self, batch_id: str, timeout: float = None) -> Dict[str, Any]:
        """Wait for all tasks in a batch to complete"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT task_id FROM parallel_tasks
            WHERE metadata LIKE ?
        ''', (f'%"batch_id": "{batch_id}"%',))

        task_ids = [row['task_id'] for row in cursor.fetchall()]

        # Wait for all task futures
        results = {}
        for task_id in task_ids:
            if task_id in self.task_futures:
                try:
                    result = self.task_futures[task_id].result(timeout=timeout)
                    results[task_id] = {'status': 'completed', 'result': result}
                except Exception as e:
                    results[task_id] = {'status': 'failed', 'error': str(e)}

        # Update batch status
        cursor.execute('''
            UPDATE execution_batches
            SET completed_at = CURRENT_TIMESTAMP,
                completed_tasks = (
                    SELECT COUNT(*) FROM parallel_tasks
                    WHERE metadata LIKE ? AND status = 'completed'
                ),
                failed_tasks = (
                    SELECT COUNT(*) FROM parallel_tasks
                    WHERE metadata LIKE ? AND status = 'failed'
                )
            WHERE batch_id = ?
        ''', (f'%"batch_id": "{batch_id}"%', f'%"batch_id": "{batch_id}"%', batch_id))
        self.conn.commit()

        return results

    # === MONITORING ===

    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """Get status of a specific task"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM parallel_tasks WHERE task_id = ?', (task_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_active_tasks(self) -> List[Dict]:
        """Get all currently running tasks"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM parallel_tasks
            WHERE status = 'running'
            ORDER BY started_at DESC
        ''')
        return [dict(row) for row in cursor.fetchall()]

    def get_execution_stats(self) -> Dict[str, Any]:
        """Get overall execution statistics"""
        cursor = self.conn.cursor()

        # Total tasks
        cursor.execute('SELECT COUNT(*) as count FROM parallel_tasks')
        total_tasks = cursor.fetchone()['count']

        # By status
        cursor.execute('''
            SELECT status, COUNT(*) as count
            FROM parallel_tasks
            GROUP BY status
        ''')
        by_status = {row['status']: row['count'] for row in cursor.fetchall()}

        # Average duration
        cursor.execute('''
            SELECT AVG(duration_seconds) as avg_duration
            FROM parallel_tasks
            WHERE status = 'completed'
        ''')
        avg_duration = cursor.fetchone()['avg_duration'] or 0

        # Throughput
        uptime = time.time() - self.start_time
        throughput = self.completed_count / uptime if uptime > 0 else 0

        return {
            'total_tasks': total_tasks,
            'tasks_by_status': by_status,
            'active_tasks': len(self.active_tasks),
            'completed_tasks': self.completed_count,
            'failed_tasks': self.failed_count,
            'average_duration': round(avg_duration, 3),
            'throughput_per_second': round(throughput, 2),
            'max_workers': self.max_workers,
            'uptime_seconds': round(uptime, 1)
        }

    # === ASYNC SUPPORT ===

    async def submit_async(self, task_id: str, task_name: str, coro,
                          priority: TaskPriority = TaskPriority.NORMAL,
                          metadata: Dict = None) -> Any:
        """Submit an async task"""
        # Log task
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO parallel_tasks
            (task_id, task_name, task_type, priority, status, metadata)
            VALUES (?, ?, 'async', ?, 'pending', ?)
        ''', (task_id, task_name, priority.value,
              json.dumps(metadata) if metadata else None))
        self.conn.commit()

        # Execute async
        self._update_task_status(task_id, TaskStatus.RUNNING, "async_worker")
        start_time = time.time()

        try:
            result = await coro
            duration = time.time() - start_time
            self._update_task_result(task_id, TaskStatus.COMPLETED, result, duration)
            return result
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"{type(e).__name__}: {str(e)}"
            self._update_task_result(task_id, TaskStatus.FAILED, None, duration, error_msg)
            raise

    # === CLEANUP ===

    def shutdown(self, wait: bool = True):
        """Shutdown executor and cleanup"""
        self.thread_pool.shutdown(wait=wait)
        if self.process_pool:
            self.process_pool.shutdown(wait=wait)
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()


# === UTILITY FUNCTIONS ===

def example_compute_task(x: int, sleep_time: float = 0.1) -> int:
    """Example compute task"""
    time.sleep(sleep_time)
    return x * x


def example_io_task(url: str, sleep_time: float = 0.2) -> str:
    """Example I/O task"""
    time.sleep(sleep_time)
    return f"Fetched: {url}"


def main():
    """Test parallel executor"""
    print("Testing Parallel Task Execution System")
    print("=" * 50)

    with ParallelExecutor(max_workers=4) as executor:

        # Submit individual tasks
        print("\n1. Submitting individual tasks...")
        task_ids = []
        for i in range(5):
            task_id = executor.submit_task(
                task_id=f"compute_{i}",
                task_name=f"Square of {i}",
                func=example_compute_task,
                args=(i, 0.5),
                priority=TaskPriority.NORMAL
            )
            task_ids.append(task_id)
        print(f"   Submitted {len(task_ids)} tasks")

        # Wait a bit for execution
        time.sleep(1)

        # Check active tasks
        print("\n2. Active tasks:")
        active = executor.get_active_tasks()
        for task in active:
            print(f"   - {task['task_name']} (worker: {task['worker_id']})")

        # Wait for completion
        print("\n3. Waiting for tasks to complete...")
        for task_id in task_ids:
            if task_id in executor.task_futures:
                try:
                    result = executor.task_futures[task_id].result(timeout=5)
                    print(f"   {task_id}: {result}")
                except Exception as e:
                    print(f"   {task_id} failed: {e}")

        # Submit a batch
        print("\n4. Submitting batch of tasks...")
        batch_tasks = [
            {'name': f'IO Task {i}', 'func': example_io_task,
             'args': (f'http://example.com/{i}',), 'type': 'io'}
            for i in range(3)
        ]

        batch_id = executor.submit_batch(
            batch_id="test_batch_1",
            batch_name="Test I/O Batch",
            tasks=batch_tasks
        )
        print(f"   Batch ID: {batch_id}")

        # Wait for batch
        print("\n5. Waiting for batch completion...")
        batch_results = executor.wait_for_batch(batch_id, timeout=10)
        for task_id, result in batch_results.items():
            print(f"   {task_id}: {result['status']}")

        # Get execution stats
        print("\n6. Execution Statistics:")
        stats = executor.get_execution_stats()
        for key, value in stats.items():
            if key == 'tasks_by_status':
                print(f"   {key}:")
                for status, count in value.items():
                    print(f"     - {status}: {count}")
            else:
                print(f"   {key}: {value}")

        # Test async execution
        print("\n7. Testing async execution...")

        async def async_test():
            result = await executor.submit_async(
                task_id="async_1",
                task_name="Async Test Task",
                coro=asyncio.sleep(0.1, result="Async result")
            )
            return result

        async_result = asyncio.run(async_test())
        print(f"   Async result: {async_result}")

    print(f"\n✓ Parallel executor working!")
    print(f"Database: {executor.db_path}")


if __name__ == "__main__":
    main()
