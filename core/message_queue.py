#!/usr/bin/env python3
"""Message Queue Integration (#94) - Send/receive via message queues"""
import json
import queue
import threading
from pathlib import Path
from typing import Dict, Callable, Any, Optional
from datetime import datetime
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from core.persistent_memory import PersistentMemory

class MessageQueue:
    """In-memory message queue system

    For production, replace with RabbitMQ, Kafka, Redis, etc.
    This provides the interface structure.
    """

    def __init__(self, db_path: str = None):
        self.queues: Dict[str, queue.Queue] = {}
        self.subscribers: Dict[str, list] = {}
        self.running = False

        if db_path is None:
            workspace = Path(__file__).parent.parent
            db_path = str(workspace / "memory.db")
        self.memory = PersistentMemory(db_path)

    def create_queue(self, queue_name: str, maxsize: int = 0):
        """Create a new queue"""
        if queue_name not in self.queues:
            self.queues[queue_name] = queue.Queue(maxsize=maxsize)
            self.subscribers[queue_name] = []

            self.memory.log_decision(
                f'Queue created: {queue_name}',
                f'Max size: {maxsize}',
                tags=['message_queue', 'create', queue_name]
            )

    def publish(self, queue_name: str, message: Any, metadata: Dict = None):
        """Publish a message to a queue"""
        if queue_name not in self.queues:
            self.create_queue(queue_name)

        envelope = {
            'message': message,
            'metadata': metadata or {},
            'timestamp': datetime.now().isoformat(),
            'queue': queue_name
        }

        self.queues[queue_name].put(envelope)

        # Notify subscribers
        for callback in self.subscribers.get(queue_name, []):
            try:
                callback(envelope)
            except Exception as e:
                print(f"Subscriber error: {e}")

    def subscribe(self, queue_name: str, callback: Callable):
        """Subscribe to a queue with a callback function"""
        if queue_name not in self.queues:
            self.create_queue(queue_name)

        self.subscribers[queue_name].append(callback)

        self.memory.log_decision(
            f'Subscribed to queue: {queue_name}',
            f'Callback: {callback.__name__}',
            tags=['message_queue', 'subscribe', queue_name]
        )

    def consume(self, queue_name: str, block: bool = True, timeout: Optional[float] = None) -> Optional[Dict]:
        """Consume a single message from a queue"""
        if queue_name not in self.queues:
            return None

        try:
            return self.queues[queue_name].get(block=block, timeout=timeout)
        except queue.Empty:
            return None

    def start_worker(self, queue_name: str, worker_func: Callable, num_workers: int = 1):
        """Start background worker threads to process messages"""
        if queue_name not in self.queues:
            self.create_queue(queue_name)

        self.running = True

        def worker():
            while self.running:
                try:
                    envelope = self.consume(queue_name, block=True, timeout=1.0)
                    if envelope:
                        worker_func(envelope['message'], envelope['metadata'])
                except Exception as e:
                    print(f"Worker error: {e}")

        threads = []
        for i in range(num_workers):
            thread = threading.Thread(target=worker, daemon=True)
            thread.start()
            threads.append(thread)

        self.memory.log_decision(
            f'Started {num_workers} workers for queue: {queue_name}',
            f'Worker function: {worker_func.__name__}',
            tags=['message_queue', 'worker', queue_name]
        )

        return threads

    def stop(self):
        """Stop all workers"""
        self.running = False

    def get_stats(self, queue_name: str) -> Dict:
        """Get queue statistics"""
        if queue_name not in self.queues:
            return {}

        q = self.queues[queue_name]
        return {
            'queue_name': queue_name,
            'size': q.qsize(),
            'empty': q.empty(),
            'full': q.full(),
            'subscribers': len(self.subscribers.get(queue_name, []))
        }


# Example usage patterns
def example_task_processor(message: Any, metadata: Dict):
    """Example worker function for processing tasks"""
    print(f"Processing task: {message}")
    # Do work here
    return f"Completed: {message}"

def example_log_processor(message: Any, metadata: Dict):
    """Example worker for processing logs"""
    print(f"Log entry: {message}")


if __name__ == '__main__':
    # Create message queue
    mq = MessageQueue()

    # Create queues
    mq.create_queue('tasks')
    mq.create_queue('logs')
    mq.create_queue('alerts')

    # Start workers
    mq.start_worker('tasks', example_task_processor, num_workers=2)
    mq.start_worker('logs', example_log_processor, num_workers=1)

    # Publish some messages
    for i in range(5):
        mq.publish('tasks', f'Task {i}', {'priority': i})

    mq.publish('logs', 'System started')
    mq.publish('alerts', 'Test alert')

    # Check stats
    print("\nQueue stats:")
    for queue_name in ['tasks', 'logs', 'alerts']:
        stats = mq.get_stats(queue_name)
        print(f"  {queue_name}: {stats}")

    # Keep running to process messages
    import time
    print("\nProcessing messages (press Ctrl+C to stop)...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        mq.stop()
