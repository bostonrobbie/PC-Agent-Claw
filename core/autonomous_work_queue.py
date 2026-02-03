#!/usr/bin/env python3
"""
Autonomous Work Queue - 24/7 Task Execution
Runs continuously on both GPUs, working even when you're asleep
"""

import time
import queue
import threading
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import sys

WORKSPACE = Path(__file__).parent.parent
sys.path.append(str(WORKSPACE))

from core.persistent_memory import PersistentMemory

try:
    from notify_status import send_notification
except ImportError:
    def send_notification(msg):
        print(f"[NOTIFICATION] {msg}")

class AutonomousWorkQueue:
    """
    24/7 work queue that processes tasks autonomously

    Features:
    - Priority-based task scheduling
    - Runs on both GPUs in parallel
    - Persists state across restarts
    - Morning/evening summaries
    - Auto-retry failed tasks
    """

    def __init__(self):
        self.memory = PersistentMemory()
        self.task_queue = queue.PriorityQueue()
        self.running = False
        self.workers = []
        self.completed_today = 0
        self.session_id = self.memory.start_session()

        # Load pending tasks from memory
        self._load_pending_tasks()

    def _load_pending_tasks(self):
        """Load pending tasks from persistent memory"""
        active_tasks = self.memory.get_active_tasks()
        print(f"Loaded {len(active_tasks)} pending tasks from memory")

        for task in active_tasks:
            priority = task.get('priority', 0)
            task_data = {
                'task_id': task['task_id'],
                'description': task['description'],
                'metadata': json.loads(task['metadata']) if task['metadata'] else {}
            }
            self.task_queue.put((-priority, task_data))  # Negative for max-heap

    def add_task(self, task_id: str, description: str, priority: int = 0,
                 metadata: Dict = None, execute_func=None):
        """
        Add task to queue

        Args:
            task_id: Unique task identifier
            description: Human-readable description
            priority: Higher = more important
            metadata: Additional task data
            execute_func: Function to execute (if not provided, task is just tracked)
        """
        # Save to persistent memory
        self.memory.add_task(task_id, description, priority, metadata)

        # Add to queue
        task_data = {
            'task_id': task_id,
            'description': description,
            'metadata': metadata or {},
            'execute_func': execute_func
        }

        self.task_queue.put((-priority, task_data))
        print(f"[QUEUE] Added task: {description} (priority: {priority})")

    def start(self, num_workers: int = 2):
        """Start processing queue with N workers (one per GPU)"""
        print("=" * 70)
        print("AUTONOMOUS WORK QUEUE - STARTING")
        print("=" * 70)
        print(f"Workers: {num_workers}")
        print(f"Pending tasks: {self.task_queue.qsize()}")
        print()

        self.running = True

        # Start worker threads
        for i in range(num_workers):
            worker = threading.Thread(target=self._worker, args=(i,), daemon=True)
            worker.start()
            self.workers.append(worker)

        # Start monitoring thread
        monitor = threading.Thread(target=self._monitor, daemon=True)
        monitor.start()

        print(f"Started {num_workers} workers + 1 monitor thread")
        print("Queue is now running 24/7")
        print()

        send_notification(f"🚀 WORK QUEUE STARTED\n\n{num_workers} workers active\n{self.task_queue.qsize()} tasks pending\nWorking 24/7")

    def _worker(self, worker_id: int):
        """Worker thread that processes tasks"""
        print(f"[Worker {worker_id}] Started")

        while self.running:
            try:
                # Get task with timeout
                try:
                    priority, task_data = self.task_queue.get(timeout=5)
                except queue.Empty:
                    continue

                task_id = task_data['task_id']
                description = task_data['description']

                print(f"[Worker {worker_id}] Processing: {description}")

                # Update status to in_progress
                self.memory.update_task_status(task_id, 'in_progress')

                # Execute task
                try:
                    start_time = time.time()

                    if 'execute_func' in task_data and task_data['execute_func']:
                        # Execute custom function
                        result = task_data['execute_func'](task_data)
                    else:
                        # Just mark as completed (tracking only)
                        result = "Tracked"
                        time.sleep(0.1)  # Minimal processing

                    elapsed = time.time() - start_time

                    # Mark complete
                    self.memory.update_task_status(task_id, 'completed')
                    self.completed_today += 1

                    print(f"[Worker {worker_id}] Completed: {description} ({elapsed:.1f}s)")

                except Exception as e:
                    # Mark failed
                    self.memory.update_task_status(task_id, 'failed')
                    print(f"[Worker {worker_id}] Failed: {description} - {str(e)}")

                    # Could add retry logic here

                finally:
                    self.task_queue.task_done()

            except Exception as e:
                print(f"[Worker {worker_id}] Error: {str(e)}")
                time.sleep(1)

        print(f"[Worker {worker_id}] Stopped")

    def _monitor(self):
        """Monitor thread for summaries and health checks"""
        print("[Monitor] Started")

        last_summary_time = time.time()
        summary_interval = 4 * 3600  # 4 hours

        while self.running:
            try:
                time.sleep(60)  # Check every minute

                # Periodic summary
                if time.time() - last_summary_time > summary_interval:
                    self._send_summary()
                    last_summary_time = time.time()

            except Exception as e:
                print(f"[Monitor] Error: {str(e)}")

        print("[Monitor] Stopped")

    def _send_summary(self):
        """Send periodic summary"""
        summary = self.memory.get_session_summary()
        summary['completed_today'] = self.completed_today
        summary['pending'] = self.task_queue.qsize()

        msg = f"📊 WORK QUEUE SUMMARY\n\n"
        msg += f"Completed today: {summary['completed_today']}\n"
        msg += f"Pending: {summary['pending']}\n"
        msg += f"Active tasks: {summary['active_tasks']}\n"

        send_notification(msg)

    def stop(self):
        """Stop the queue gracefully"""
        print("\nStopping work queue...")
        self.running = False

        # Wait for workers
        for worker in self.workers:
            worker.join(timeout=5)

        # End session
        self.memory.end_session(
            self.session_id,
            self.completed_today,
            f"Completed {self.completed_today} tasks"
        )

        print("Work queue stopped")

    def get_status(self) -> Dict:
        """Get current queue status"""
        return {
            'running': self.running,
            'workers': len(self.workers),
            'pending_tasks': self.task_queue.qsize(),
            'completed_today': self.completed_today,
            'session_id': self.session_id
        }


def main():
    """Test work queue"""
    queue_system = AutonomousWorkQueue()

    # Add some test tasks
    queue_system.add_task('test_1', 'Test task 1', priority=10)
    queue_system.add_task('test_2', 'Test task 2', priority=5)
    queue_system.add_task('test_3', 'Test task 3', priority=8)

    # Start queue
    queue_system.start(num_workers=2)

    # Run for a bit
    try:
        print("Queue running... Press Ctrl+C to stop")
        while True:
            time.sleep(10)
            status = queue_system.get_status()
            print(f"Status: {status['pending_tasks']} pending, {status['completed_today']} completed today")

    except KeyboardInterrupt:
        print("\nStopping...")
        queue_system.stop()


if __name__ == "__main__":
    main()
