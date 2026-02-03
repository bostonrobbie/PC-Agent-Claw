#!/usr/bin/env python3
"""
Self-Initiated Background Tasks
Proactive task execution without waiting for commands
"""
import sys
from pathlib import Path
import sqlite3
import json
import threading
import queue
import time
from typing import Dict, List, Optional, Callable
from datetime import datetime
from enum import Enum

sys.path.append(str(Path(__file__).parent.parent))


class TaskPriority(Enum):
    """Task priority levels"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class TaskStatus(Enum):
    """Task statuses"""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BackgroundTaskManager:
    """
    Self-initiated background task system

    Features:
    - Proactive task execution
    - Priority queue
    - Parallel execution
    - Auto-testing after code changes
    - Dependency updates
    - Performance monitoring
    - Log analysis
    """

    def __init__(self, db_path: str = None, max_workers: int = 3,
                 min_workers: int = 1, enable_auto_scaling: bool = True):
        workspace = Path(__file__).parent.parent
        if db_path is None:
            db_path = str(workspace / "background_tasks.db")

        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

        # Task queue
        self.task_queue = queue.PriorityQueue()
        self.max_workers = max_workers
        self.min_workers = min_workers
        self.workers = []
        self.running = False
        self.worker_lock = threading.Lock()

        # Dynamic scaling settings
        self.enable_auto_scaling = enable_auto_scaling
        self.current_workers = 0
        self.scaling_check_interval = 5  # seconds
        self.last_scaling_check = time.time()

        # Scaling thresholds
        self.scale_up_queue_depth = 5  # Tasks per worker
        self.scale_down_idle_time = 30  # Seconds of idle before scaling down
        self.cpu_threshold = 80  # Don't scale up if CPU > this %

        # Worker activity tracking
        self.worker_activity = {}  # worker_id -> last_activity_time

        # Task handlers
        self.task_handlers = {}

        # Register default handlers
        self._register_default_handlers()

    def _init_db(self):
        """Initialize task database"""
        cursor = self.conn.cursor()

        # Background tasks
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS background_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_type TEXT NOT NULL,
                task_description TEXT,
                priority INTEGER DEFAULT 2,
                status TEXT DEFAULT 'queued',
                context TEXT,
                result TEXT,
                error TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP
            )
        ''')

        # Task rules (when to auto-trigger)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trigger_event TEXT NOT NULL,
                task_type TEXT NOT NULL,
                condition TEXT,
                priority INTEGER DEFAULT 2,
                enabled INTEGER DEFAULT 1
            )
        ''')

        self.conn.commit()

    def _register_default_handlers(self):
        """Register default task handlers"""

        @self.register_handler('run_tests')
        def run_tests(context):
            """Run tests automatically"""
            import subprocess
            try:
                result = subprocess.run(
                    ['python', '-m', 'pytest', '-v'],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                return {
                    'success': result.returncode == 0,
                    'output': result.stdout,
                    'errors': result.stderr
                }
            except Exception as e:
                return {'success': False, 'error': str(e)}

        @self.register_handler('check_dependencies')
        def check_dependencies(context):
            """Check for outdated dependencies"""
            import subprocess
            try:
                # Check Python packages
                result = subprocess.run(
                    ['pip', 'list', '--outdated', '--format=json'],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                if result.returncode == 0:
                    outdated = json.loads(result.stdout)
                    return {
                        'success': True,
                        'outdated_count': len(outdated),
                        'outdated': outdated
                    }
                return {'success': False, 'error': 'pip check failed'}
            except Exception as e:
                return {'success': False, 'error': str(e)}

        @self.register_handler('analyze_logs')
        def analyze_logs(context):
            """Analyze application logs for errors"""
            log_file = context.get('log_file')
            if not log_file or not Path(log_file).exists():
                return {'success': False, 'error': 'Log file not found'}

            try:
                errors = []
                warnings = []

                with open(log_file, 'r') as f:
                    for line in f.readlines()[-1000:]:  # Last 1000 lines
                        if 'ERROR' in line.upper():
                            errors.append(line.strip())
                        elif 'WARNING' in line.upper():
                            warnings.append(line.strip())

                return {
                    'success': True,
                    'errors': errors,
                    'warnings': warnings,
                    'error_count': len(errors),
                    'warning_count': len(warnings)
                }
            except Exception as e:
                return {'success': False, 'error': str(e)}

        @self.register_handler('monitor_performance')
        def monitor_performance(context):
            """Monitor system performance"""
            try:
                import psutil

                return {
                    'success': True,
                    'cpu_percent': psutil.cpu_percent(interval=1),
                    'memory_percent': psutil.virtual_memory().percent,
                    'disk_percent': psutil.disk_usage('/').percent,
                    'timestamp': datetime.now().isoformat()
                }
            except Exception as e:
                return {'success': False, 'error': str(e)}

    # === TASK REGISTRATION ===

    def register_handler(self, task_type: str):
        """Decorator to register task handler"""
        def decorator(func: Callable):
            self.task_handlers[task_type] = func
            return func
        return decorator

    def register_rule(self, trigger_event: str, task_type: str,
                     condition: str = None, priority: TaskPriority = TaskPriority.MEDIUM):
        """
        Register automatic task trigger rule

        Args:
            trigger_event: Event that triggers task (e.g., 'code_changed', 'error_detected')
            task_type: Type of task to run
            condition: Optional condition (Python expression)
            priority: Task priority
        """
        cursor = self.conn.cursor()

        cursor.execute('''
            INSERT INTO task_rules (trigger_event, task_type, condition, priority)
            VALUES (?, ?, ?, ?)
        ''', (trigger_event, task_type, condition, priority.value))

        self.conn.commit()

    # === TASK QUEUEING ===

    def queue_task(self, task_type: str, description: str = None,
                  priority: TaskPriority = TaskPriority.MEDIUM,
                  context: Dict = None) -> int:
        """
        Queue a background task

        Args:
            task_type: Type of task
            description: Task description
            priority: Priority level
            context: Task context data

        Returns:
            Task ID
        """
        cursor = self.conn.cursor()

        context_json = json.dumps(context) if context else None

        cursor.execute('''
            INSERT INTO background_tasks (task_type, task_description, priority, context)
            VALUES (?, ?, ?, ?)
        ''', (task_type, description, priority.value, context_json))

        self.conn.commit()
        task_id = cursor.lastrowid

        # Add to queue (priority, task_id)
        self.task_queue.put((-priority.value, task_id))  # Negative for highest first

        return task_id

    # === AUTOMATIC TRIGGERING ===

    def trigger_event(self, event: str, context: Dict = None):
        """
        Trigger an event that may queue tasks

        Args:
            event: Event name
            context: Event context
        """
        cursor = self.conn.cursor()

        # Find matching rules
        cursor.execute('''
            SELECT * FROM task_rules
            WHERE trigger_event = ? AND enabled = 1
        ''', (event,))

        for rule in cursor.fetchall():
            rule_dict = dict(rule)

            # Check condition if exists
            if rule_dict['condition']:
                try:
                    # Safe evaluation of condition
                    if not eval(rule_dict['condition'], {"__builtins__": {}}, context or {}):
                        continue
                except:
                    continue

            # Queue task
            self.queue_task(
                rule_dict['task_type'],
                f"Auto-triggered by {event}",
                TaskPriority(rule_dict['priority']),
                context
            )

    # === TASK EXECUTION ===

    def start_workers(self):
        """Start background workers with dynamic scaling"""
        if self.running:
            return

        self.running = True

        # Start with minimum workers
        initial_workers = self.min_workers if self.enable_auto_scaling else self.max_workers
        self._scale_workers(initial_workers)

        # Start scaling monitor if enabled
        if self.enable_auto_scaling:
            scaling_thread = threading.Thread(target=self._scaling_monitor, daemon=True)
            scaling_thread.start()

        print(f"[BACKGROUND] Started {self.current_workers} workers (auto-scaling: {self.enable_auto_scaling})")

    def stop_workers(self):
        """Stop background workers gracefully"""
        print("[BACKGROUND] Stopping workers gracefully...")
        self.running = False

        # Wait for tasks to complete
        self.task_queue.join()

        # Wait for workers to finish
        for worker in self.workers:
            worker.join(timeout=5)

        self.workers = []
        self.current_workers = 0
        print("[BACKGROUND] All workers stopped")

    def _scale_workers(self, target_count: int):
        """Scale workers to target count"""
        target_count = max(self.min_workers, min(target_count, self.max_workers))

        with self.worker_lock:
            current_count = self.current_workers

            if target_count > current_count:
                # Scale up
                for i in range(current_count, target_count):
                    worker_id = f"worker-{i}"
                    worker = threading.Thread(
                        target=self._worker_loop,
                        args=(worker_id,),
                        daemon=True
                    )
                    worker.start()
                    self.workers.append(worker)
                    self.worker_activity[worker_id] = time.time()

                self.current_workers = target_count
                print(f"[SCALING] Scaled up: {current_count} -> {target_count} workers")

            elif target_count < current_count:
                # Scale down is handled by workers checking self.current_workers
                self.current_workers = target_count
                print(f"[SCALING] Scaling down: {current_count} -> {target_count} workers")

    def _scaling_monitor(self):
        """Monitor and adjust worker count based on load"""
        while self.running:
            try:
                time.sleep(self.scaling_check_interval)

                if not self.enable_auto_scaling:
                    continue

                # Get queue depth
                queue_depth = self.task_queue.qsize()

                # Get CPU usage
                try:
                    import psutil
                    cpu_percent = psutil.cpu_percent(interval=1)
                except:
                    cpu_percent = 0

                # Calculate optimal worker count
                if queue_depth > 0:
                    # Scale up if queue is deep and CPU is available
                    tasks_per_worker = queue_depth / max(self.current_workers, 1)

                    if tasks_per_worker > self.scale_up_queue_depth and cpu_percent < self.cpu_threshold:
                        # Need more workers
                        new_count = min(
                            self.current_workers + 1,
                            self.max_workers,
                            (queue_depth // self.scale_up_queue_depth) + 1
                        )
                        self._scale_workers(new_count)

                else:
                    # Check if workers are idle - scale down
                    current_time = time.time()
                    idle_workers = sum(
                        1 for last_active in self.worker_activity.values()
                        if current_time - last_active > self.scale_down_idle_time
                    )

                    if idle_workers > 0 and self.current_workers > self.min_workers:
                        new_count = max(self.current_workers - 1, self.min_workers)
                        self._scale_workers(new_count)

            except Exception as e:
                print(f"[SCALING] Error in scaling monitor: {e}")

    def _worker_loop(self, worker_id: str):
        """Worker loop with dynamic scaling support"""
        print(f"[{worker_id}] Started")

        while self.running:
            try:
                # Check if this worker should exit (scale down)
                worker_num = int(worker_id.split('-')[1])
                if worker_num >= self.current_workers:
                    print(f"[{worker_id}] Exiting due to scale down")
                    break

                # Get task from queue (timeout 1s)
                try:
                    priority, task_id = self.task_queue.get(timeout=1)
                except queue.Empty:
                    continue

                # Update activity
                self.worker_activity[worker_id] = time.time()

                # Execute task
                self._execute_task(task_id, worker_id)

                self.task_queue.task_done()

                # Update activity again after task
                self.worker_activity[worker_id] = time.time()

            except Exception as e:
                print(f"[{worker_id}] Error: {e}")
                time.sleep(1)

        print(f"[{worker_id}] Stopped")

    def _execute_task(self, task_id: int, worker_id: str):
        """Execute a single task"""
        cursor = self.conn.cursor()

        # Get task details
        cursor.execute('SELECT * FROM background_tasks WHERE id = ?', (task_id,))
        task = dict(cursor.fetchone())

        print(f"[{worker_id}] Executing task {task_id}: {task['task_type']}")

        # Update status
        cursor.execute('''
            UPDATE background_tasks
            SET status = 'running', started_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (task_id,))
        self.conn.commit()

        # Get handler
        handler = self.task_handlers.get(task['task_type'])

        if not handler:
            # No handler
            cursor.execute('''
                UPDATE background_tasks
                SET status = 'failed', completed_at = CURRENT_TIMESTAMP,
                    error = 'No handler registered'
                WHERE id = ?
            ''', (task_id,))
            self.conn.commit()
            return

        # Execute
        try:
            context = json.loads(task['context']) if task['context'] else {}
            result = handler(context)

            # Store result
            cursor.execute('''
                UPDATE background_tasks
                SET status = 'completed', completed_at = CURRENT_TIMESTAMP,
                    result = ?
                WHERE id = ?
            ''', (json.dumps(result), task_id))
            self.conn.commit()

            print(f"[{worker_id}] Task {task_id} completed: {result.get('success', False)}")

        except Exception as e:
            # Store error
            cursor.execute('''
                UPDATE background_tasks
                SET status = 'failed', completed_at = CURRENT_TIMESTAMP,
                    error = ?
                WHERE id = ?
            ''', (str(e), task_id))
            self.conn.commit()

            print(f"[{worker_id}] Task {task_id} failed: {e}")

    # === TASK STATUS ===

    def get_task_status(self, task_id: int) -> Optional[Dict]:
        """Get task status"""
        cursor = self.conn.cursor()

        cursor.execute('SELECT * FROM background_tasks WHERE id = ?', (task_id,))

        row = cursor.fetchone()
        if row:
            task = dict(row)
            if task['result']:
                task['result'] = json.loads(task['result'])
            if task['context']:
                task['context'] = json.loads(task['context'])
            return task
        return None

    def get_queued_tasks(self) -> List[Dict]:
        """Get all queued tasks"""
        cursor = self.conn.cursor()

        cursor.execute('''
            SELECT * FROM background_tasks
            WHERE status = 'queued'
            ORDER BY priority DESC, created_at ASC
        ''')

        return [dict(row) for row in cursor.fetchall()]

    def get_running_tasks(self) -> List[Dict]:
        """Get all running tasks"""
        cursor = self.conn.cursor()

        cursor.execute('''
            SELECT * FROM background_tasks
            WHERE status = 'running'
        ''')

        return [dict(row) for row in cursor.fetchall()]

    def get_worker_stats(self) -> Dict:
        """Get worker statistics for monitoring"""
        return {
            'current_workers': self.current_workers,
            'min_workers': self.min_workers,
            'max_workers': self.max_workers,
            'auto_scaling_enabled': self.enable_auto_scaling,
            'queue_depth': self.task_queue.qsize(),
            'active_workers': len([
                w for w, t in self.worker_activity.items()
                if time.time() - t < 10
            ]),
            'worker_activity': dict(self.worker_activity)
        }

    def close(self):
        """Close manager"""
        self.stop_workers()
        self.conn.close()


# === TEST CODE ===

def main():
    """Test background task manager with dynamic scaling"""
    print("=" * 70)
    print("Self-Initiated Background Tasks with Dynamic Scaling")
    print("=" * 70)

    manager = BackgroundTaskManager(
        min_workers=1,
        max_workers=8,
        enable_auto_scaling=True
    )

    try:
        print("\n1. Registering custom task handler...")

        @manager.register_handler('test_task')
        def test_task(context):
            time.sleep(2)  # Simulate work
            return {'success': True, 'message': 'Test completed', 'data': context}

        print("   Handler registered")

        print("\n2. Queueing tasks...")
        task1 = manager.queue_task('test_task', 'Test 1', TaskPriority.HIGH, {'test': 1})
        task2 = manager.queue_task('check_dependencies', 'Check deps', TaskPriority.MEDIUM)
        task3 = manager.queue_task('monitor_performance', 'Performance check', TaskPriority.LOW)

        print(f"   Queued tasks: {task1}, {task2}, {task3}")

        print("\n3. Registering automatic trigger rule...")
        manager.register_rule(
            trigger_event='code_changed',
            task_type='run_tests',
            priority=TaskPriority.HIGH
        )
        print("   Rule: code_changed -> run_tests")

        print("\n4. Starting workers...")
        manager.start_workers()

        print("\n5. Waiting for tasks to complete...")
        time.sleep(8)

        print("\n6. Checking task status...")
        status1 = manager.get_task_status(task1)
        print(f"   Task {task1}: {status1['status']}")

        status2 = manager.get_task_status(task2)
        print(f"   Task {task2}: {status2['status']}")
        if status2['result']:
            result = status2['result']
            print(f"      Outdated packages: {result.get('outdated_count', 0)}")

        print("\n7. Testing automatic triggering...")
        manager.trigger_event('code_changed', {'file': 'test.py'})
        time.sleep(2)

        queued = manager.get_queued_tasks()
        print(f"   Auto-queued tasks: {len(queued)}")

        print("\n8. Testing dynamic scaling...")
        print("   Queueing many tasks to trigger scale-up...")
        for i in range(20):
            manager.queue_task('test_task', f'Scale test {i}', TaskPriority.MEDIUM, {'test': i})

        # Monitor scaling
        for i in range(10):
            time.sleep(2)
            stats = manager.get_worker_stats()
            print(f"   T+{(i+1)*2}s: Workers={stats['current_workers']}, Queue={stats['queue_depth']}, Active={stats['active_workers']}")

        print(f"\n[OK] Background Task System with Dynamic Scaling Working!")
        print(f"Database: {manager.db_path}")
        print(f"\nFinal worker stats: {manager.get_worker_stats()}")

    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        manager.close()


if __name__ == "__main__":
    main()
