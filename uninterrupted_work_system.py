#!/usr/bin/env python3
"""
Uninterrupted Work System - Ensures continuous work with auto-recovery
Tracks work state, handles interruptions, resumes automatically
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime

WORKSPACE = Path(r"C:\Users\User\.openclaw\workspace")
sys.path.append(str(WORKSPACE))

from task_status_notifier import TaskStatusNotifier

class WorkStateManager:
    """Manages work state and handles interruptions"""

    def __init__(self):
        self.notifier = TaskStatusNotifier()
        self.state_file = WORKSPACE / "work_state.json"
        self.session_log = WORKSPACE / "work_sessions.log"

        self.state = self.load_state()
        self.session_start = datetime.now()

    def load_state(self):
        """Load work state from file"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except:
                pass

        return {
            'current_task': None,
            'task_queue': [],
            'completed_tasks': [],
            'last_checkpoint': None,
            'session_id': None,
            'interruptions': 0,
            'work_mode': 'idle'  # idle, working, interrupted, recovering
        }

    def save_state(self):
        """Save work state to file"""
        self.state['last_checkpoint'] = datetime.now().isoformat()

        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)

    def start_session(self):
        """Start a new work session"""
        self.state['session_id'] = f"session_{int(time.time())}"
        self.state['work_mode'] = 'working'
        self.save_state()

        self.log_event("SESSION_START", "Work session started")

        self.notifier.send_message(
            f"🚀 <b>Work Session Started</b>\n\n"
            f"<b>Session:</b> {self.state['session_id']}\n"
            f"<b>Mode:</b> Continuous work\n"
            f"<b>Auto-recovery:</b> Enabled"
        )

    def add_task(self, task_name, description, priority=5):
        """Add task to queue"""
        task = {
            'id': f"task_{int(time.time())}",
            'name': task_name,
            'description': description,
            'priority': priority,
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
            'attempts': 0
        }

        self.state['task_queue'].append(task)
        self.state['task_queue'].sort(key=lambda x: x['priority'])
        self.save_state()

        return task['id']

    def start_task(self, task_id):
        """Start working on a task"""
        task = self.find_task(task_id)
        if not task:
            return False

        self.state['current_task'] = task_id
        task['status'] = 'in_progress'
        task['started_at'] = datetime.now().isoformat()
        task['attempts'] += 1

        self.save_state()

        self.log_event("TASK_START", f"Started: {task['name']}")

        self.notifier.send_message(
            f"🔨 <b>Task Started</b>\n\n"
            f"<b>Task:</b> {task['name']}\n"
            f"<b>Attempt:</b> {task['attempts']}"
        )

        return True

    def complete_task(self, task_id, result=None):
        """Mark task as completed"""
        task = self.find_task(task_id)
        if not task:
            return False

        task['status'] = 'completed'
        task['completed_at'] = datetime.now().isoformat()
        task['result'] = result

        # Move to completed
        self.state['task_queue'] = [t for t in self.state['task_queue'] if t['id'] != task_id]
        self.state['completed_tasks'].append(task)
        self.state['current_task'] = None

        self.save_state()

        self.log_event("TASK_COMPLETE", f"Completed: {task['name']}")

        # Check if more tasks
        next_task = self.get_next_task()
        next_info = f"\n\n🔨 <b>Next:</b> {next_task['name']}" if next_task else ""

        self.notifier.send_message(
            f"✅ <b>Task Completed</b>\n\n"
            f"<b>Task:</b> {task['name']}\n"
            f"<b>Duration:</b> {self.get_task_duration(task)}"
            f"{next_info}"
        )

        return True

    def handle_interruption(self, reason="Unknown"):
        """Handle work interruption"""
        self.state['work_mode'] = 'interrupted'
        self.state['interruptions'] += 1

        interruption = {
            'timestamp': datetime.now().isoformat(),
            'reason': reason,
            'current_task': self.state['current_task']
        }

        self.save_state()

        self.log_event("INTERRUPTION", f"Interrupted: {reason}")

        self.notifier.send_message(
            f"⚠️ <b>Work Interrupted</b>\n\n"
            f"<b>Reason:</b> {reason}\n"
            f"<b>Interruptions today:</b> {self.state['interruptions']}\n\n"
            f"<b>Auto-recovery will activate...</b>"
        )

    def recover_from_interruption(self):
        """Auto-recover from interruption"""
        self.state['work_mode'] = 'recovering'
        self.save_state()

        self.log_event("RECOVERY_START", "Attempting recovery")

        # Check current task
        if self.state['current_task']:
            task = self.find_task(self.state['current_task'])

            if task and task['status'] == 'in_progress':
                # Resume current task
                self.notifier.send_message(
                    f"🔄 <b>Auto-Recovery</b>\n\n"
                    f"<b>Resuming:</b> {task['name']}\n"
                    f"<b>Status:</b> In progress"
                )

                self.state['work_mode'] = 'working'
                self.save_state()
                return task

        # No current task, get next from queue
        next_task = self.get_next_task()
        if next_task:
            self.start_task(next_task['id'])
            self.state['work_mode'] = 'working'
            self.save_state()
            return next_task

        # No tasks, go idle
        self.state['work_mode'] = 'idle'
        self.save_state()

        self.notifier.send_message(
            f"✅ <b>Recovery Complete</b>\n\n"
            f"No pending tasks.\n"
            f"Awaiting new work..."
        )

        return None

    def get_next_task(self):
        """Get next pending task"""
        pending = [t for t in self.state['task_queue'] if t['status'] == 'pending']

        if pending:
            return pending[0]  # Already sorted by priority
        return None

    def find_task(self, task_id):
        """Find task by ID"""
        for task in self.state['task_queue']:
            if task['id'] == task_id:
                return task

        for task in self.state['completed_tasks']:
            if task['id'] == task_id:
                return task

        return None

    def get_task_duration(self, task):
        """Calculate task duration"""
        if 'started_at' not in task or 'completed_at' not in task:
            return "Unknown"

        start = datetime.fromisoformat(task['started_at'])
        end = datetime.fromisoformat(task['completed_at'])
        duration = (end - start).total_seconds()

        if duration < 60:
            return f"{duration:.0f}s"
        elif duration < 3600:
            return f"{duration/60:.1f}m"
        else:
            return f"{duration/3600:.1f}h"

    def log_event(self, event_type, message):
        """Log work event"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with open(self.session_log, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] {event_type}: {message}\n")

    def get_session_summary(self):
        """Get summary of current session"""
        duration = (datetime.now() - self.session_start).total_seconds() / 3600

        return {
            'session_id': self.state['session_id'],
            'duration_hours': duration,
            'completed_tasks': len(self.state['completed_tasks']),
            'pending_tasks': len([t for t in self.state['task_queue'] if t['status'] == 'pending']),
            'interruptions': self.state['interruptions'],
            'current_mode': self.state['work_mode']
        }

    def send_hourly_update(self):
        """Send hourly progress update"""
        summary = self.get_session_summary()

        self.notifier.send_message(
            f"📊 <b>Hourly Update</b>\n\n"
            f"<b>Session time:</b> {summary['duration_hours']:.1f}h\n"
            f"<b>Completed:</b> {summary['completed_tasks']}\n"
            f"<b>Pending:</b> {summary['pending_tasks']}\n"
            f"<b>Interruptions:</b> {summary['interruptions']}\n"
            f"<b>Mode:</b> {summary['current_mode']}"
        )


# CLI Interface
def main():
    """CLI for work state management"""
    manager = WorkStateManager()

    if len(sys.argv) < 2:
        print("Uninterrupted Work System")
        print()
        print("Usage:")
        print("  start     - Start work session")
        print("  add       - Add task to queue")
        print("  status    - Show current status")
        print("  recover   - Manually trigger recovery")
        print()
        return

    command = sys.argv[1]

    if command == "start":
        manager.start_session()
        print("Work session started!")

    elif command == "add":
        if len(sys.argv) < 4:
            print("Usage: python uninterrupted_work_system.py add <name> <description>")
            return

        name = sys.argv[2]
        description = ' '.join(sys.argv[3:])

        task_id = manager.add_task(name, description)
        print(f"Task added: {task_id}")

    elif command == "status":
        summary = manager.get_session_summary()
        print(json.dumps(summary, indent=2))

    elif command == "recover":
        task = manager.recover_from_interruption()
        if task:
            print(f"Recovered, resuming: {task['name']}")
        else:
            print("No tasks to resume")

    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
