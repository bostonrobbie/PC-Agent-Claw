#!/usr/bin/env python3
"""
Auto Notify Wrapper - Automatically send Telegram notifications on task changes
This monitors todo list changes and sends proactive updates to Rob
"""

import json
import sys
from pathlib import Path
from task_status_notifier import TaskStatusNotifier

WORKSPACE = Path(r"C:\Users\User\.openclaw\workspace")

def detect_task_changes(old_todos, new_todos):
    """Detect what changed between old and new todo lists"""

    notifier = TaskStatusNotifier()

    # Convert to dicts for easier comparison
    old_dict = {t['content']: t['status'] for t in old_todos}
    new_dict = {t['content']: t['status'] for t in new_todos}

    # Find newly completed tasks
    for task_name, new_status in new_dict.items():
        old_status = old_dict.get(task_name)

        # Task completed!
        if old_status != 'completed' and new_status == 'completed':
            # Find what's next (first pending or in_progress task)
            next_task = None
            for t in new_todos:
                if t['status'] in ['pending', 'in_progress'] and t['content'] != task_name:
                    next_task = t['content']
                    break

            notifier.task_completed(task_name, next_task)

        # Task started
        elif old_status != 'in_progress' and new_status == 'in_progress':
            notifier.task_started(task_name)

    # Check if all tasks are completed or we're idle
    active_tasks = [t for t in new_todos if t['status'] in ['pending', 'in_progress']]
    if len(active_tasks) == 0:
        notifier.taking_break("All tasks completed! Awaiting new direction.")

def load_previous_state():
    """Load the previous todo state"""
    state_file = WORKSPACE / ".todo_state.json"
    if state_file.exists():
        with open(state_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_current_state(todos):
    """Save current todo state for next comparison"""
    state_file = WORKSPACE / ".todo_state.json"
    with open(state_file, 'w', encoding='utf-8') as f:
        json.dump(todos, f, indent=2)

def notify_on_todo_change(new_todos):
    """Main function to handle todo changes"""
    old_todos = load_previous_state()

    if old_todos:  # Only detect changes if we have previous state
        detect_task_changes(old_todos, new_todos)

    save_current_state(new_todos)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python auto_notify_wrapper.py '<todos_json>'")
        sys.exit(1)

    todos_json = sys.argv[1]
    todos = json.loads(todos_json)
    notify_on_todo_change(todos)
