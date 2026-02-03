#!/usr/bin/env python3
"""
Autonomous GPU Worker - Processes LLM tasks continuously
Runs in background, picks up tasks from queue, uses GPU automatically
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime

# Add workspace to path
WORKSPACE = Path(r"C:\Users\User\.openclaw\workspace")
sys.path.append(str(WORKSPACE))

from task_status_notifier import TaskStatusNotifier
from smart_gpu_llm import SmartGPU

class AutonomousGPUWorker:
    """Continuously processes GPU tasks from a queue"""

    def __init__(self):
        self.notifier = TaskStatusNotifier()
        self.gpu = SmartGPU()
        self.task_queue_file = WORKSPACE / "gpu_task_queue.json"
        self.results_dir = WORKSPACE / "gpu_results"
        self.results_dir.mkdir(exist_ok=True)

        self.running = True
        self.tasks_completed = 0
        self.check_interval = 10  # Check for new tasks every 10 seconds

    def load_task_queue(self):
        """Load pending tasks from queue file"""
        if not self.task_queue_file.exists():
            return []

        try:
            with open(self.task_queue_file, 'r') as f:
                return json.load(f)
        except:
            return []

    def save_task_queue(self, tasks):
        """Save task queue to file"""
        with open(self.task_queue_file, 'w') as f:
            json.dump(tasks, f, indent=2)

    def add_task(self, task_type, prompt, model="qwen2.5:7b", priority=5):
        """
        Add a new task to the queue

        Args:
            task_type (str): Type of task (analysis, generation, etc.)
            prompt (str): The prompt to send to LLM
            model (str): Which model to use
            priority (int): 1-10, lower = higher priority
        """
        tasks = self.load_task_queue()

        new_task = {
            'id': f"task_{int(time.time())}_{len(tasks)}",
            'type': task_type,
            'prompt': prompt,
            'model': model,
            'priority': priority,
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
            'result': None
        }

        tasks.append(new_task)

        # Sort by priority (lower number = higher priority)
        tasks.sort(key=lambda x: x['priority'])

        self.save_task_queue(tasks)
        print(f"Added task: {new_task['id']}")

    def process_task(self, task):
        """Process a single task"""
        print(f"Processing: {task['id']}")

        # Select best GPU
        gpu_name = self.gpu.select_best_gpu()
        if not gpu_name:
            print("No GPU available, skipping task")
            return None

        gpu_info = self.gpu.get_status()

        # Notify start
        self.notifier.send_message(
            f"🔄 <b>GPU Task Started</b>\n\n"
            f"<b>Task:</b> {task['type']}\n"
            f"<b>GPU:</b> {gpu_info['gpu']}\n"
            f"<b>Model:</b> {task['model']}"
        )

        # Run the task
        start_time = time.time()
        result = self.gpu.run_prompt(task['model'], task['prompt'])
        elapsed = time.time() - start_time

        # Save result
        result_file = self.results_dir / f"{task['id']}_result.txt"
        with open(result_file, 'w', encoding='utf-8') as f:
            f.write(f"Task ID: {task['id']}\n")
            f.write(f"Type: {task['type']}\n")
            f.write(f"Model: {task['model']}\n")
            f.write(f"GPU: {gpu_info['gpu']}\n")
            f.write(f"Time: {elapsed:.2f}s\n")
            f.write(f"\n{'='*70}\n\n")
            f.write(result)

        # Notify completion
        self.notifier.send_message(
            f"✅ <b>GPU Task Complete</b>\n\n"
            f"<b>Task:</b> {task['type']}\n"
            f"<b>Time:</b> {elapsed:.1f}s\n"
            f"<b>Result saved:</b> {result_file.name}"
        )

        self.tasks_completed += 1
        return result

    def run(self):
        """Main worker loop - runs continuously"""
        print("=" * 70)
        print("Autonomous GPU Worker - STARTED")
        print("=" * 70)
        print()

        # Notify startup
        self.notifier.send_message(
            "🤖 <b>Autonomous GPU Worker Started</b>\n\n"
            "Monitoring task queue every 10 seconds...\n"
            "Ready to process LLM tasks automatically."
        )

        last_status_update = time.time()
        status_interval = 3600  # Hourly status updates

        while self.running:
            try:
                # Load pending tasks
                tasks = self.load_task_queue()
                pending_tasks = [t for t in tasks if t['status'] == 'pending']

                if pending_tasks:
                    # Process highest priority task
                    task = pending_tasks[0]

                    # Mark as in progress
                    task['status'] = 'in_progress'
                    self.save_task_queue(tasks)

                    # Process it
                    result = self.process_task(task)

                    # Update status
                    task['status'] = 'completed' if result else 'failed'
                    task['result'] = result
                    task['completed_at'] = datetime.now().isoformat()
                    self.save_task_queue(tasks)

                    # Remove completed tasks older than 24 hours
                    self.cleanup_old_tasks()

                else:
                    # No tasks, wait
                    time.sleep(self.check_interval)

                # Periodic status update
                if time.time() - last_status_update > status_interval:
                    self.send_status_update()
                    last_status_update = time.time()

            except KeyboardInterrupt:
                print("\nShutting down gracefully...")
                self.running = False
                break
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(self.check_interval)

        # Shutdown notification
        self.notifier.send_message(
            f"⏸️ <b>GPU Worker Stopped</b>\n\n"
            f"<b>Tasks completed:</b> {self.tasks_completed}"
        )

        print()
        print("=" * 70)
        print(f"Autonomous GPU Worker - STOPPED")
        print(f"Tasks completed: {self.tasks_completed}")
        print("=" * 70)

    def cleanup_old_tasks(self):
        """Remove completed tasks older than 24 hours"""
        tasks = self.load_task_queue()

        cutoff_time = time.time() - (24 * 3600)

        cleaned_tasks = []
        for task in tasks:
            if task['status'] != 'completed':
                cleaned_tasks.append(task)
            else:
                # Check if old
                if 'completed_at' in task:
                    completed_timestamp = datetime.fromisoformat(task['completed_at']).timestamp()
                    if completed_timestamp > cutoff_time:
                        cleaned_tasks.append(task)

        self.save_task_queue(cleaned_tasks)

    def send_status_update(self):
        """Send hourly status update"""
        tasks = self.load_task_queue()
        pending = len([t for t in tasks if t['status'] == 'pending'])

        gpu_status = self.gpu.get_status()

        self.notifier.send_message(
            f"📊 <b>GPU Worker Status</b>\n\n"
            f"<b>Pending tasks:</b> {pending}\n"
            f"<b>Completed today:</b> {self.tasks_completed}\n"
            f"<b>Active GPU:</b> {gpu_status['gpu']}"
        )


def add_task_cli():
    """CLI for adding tasks"""
    if len(sys.argv) < 3:
        print("Usage:")
        print("  Add task: python autonomous_gpu_worker.py add <type> <prompt>")
        print("  Start worker: python autonomous_gpu_worker.py start")
        print()
        print("Examples:")
        print("  python autonomous_gpu_worker.py add analysis 'Analyze this code...'")
        print("  python autonomous_gpu_worker.py add generation 'Generate 5 strategy variants'")
        return

    worker = AutonomousGPUWorker()

    task_type = sys.argv[2]
    prompt = ' '.join(sys.argv[3:])

    worker.add_task(task_type, prompt)
    print(f"Task added to queue!")
    print(f"Type: {task_type}")
    print(f"Prompt: {prompt[:100]}...")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "add":
            add_task_cli()
        elif sys.argv[1] == "start":
            worker = AutonomousGPUWorker()
            worker.run()
        else:
            print("Unknown command. Use 'add' or 'start'")
    else:
        # Default: start worker
        worker = AutonomousGPUWorker()
        worker.run()
