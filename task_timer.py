#!/usr/bin/env python3
"""
Enforces time-boxing on tasks
"""

import time
import json
from datetime import datetime, timedelta
from pathlib import Path

class TaskTimer:
    def __init__(self):
        self.state_file = Path("C:/Users/User/.openclaw/workspace/current_task.json")
        self.max_attempts = 3
        self.max_time_per_attempt = 60  # 1 hour

    def start_task(self, task_name, approach):
        """Start tracking a task"""
        state = {
            'task': task_name,
            'approach': approach,
            'attempt': 1,
            'start_time': datetime.now().isoformat(),
            'deadline': (datetime.now() + timedelta(minutes=self.max_time_per_attempt)).isoformat()
        }
        self.state_file.write_text(json.dumps(state, indent=2))
        print(f"⏱️ Started: {task_name} (Attempt 1/{self.max_attempts})")
        print(f"⏱️ Deadline: {state['deadline']}")
        return state

    def check_should_pivot(self):
        """Check if I should give up on current approach"""
        if not self.state_file.exists():
            return False, None

        state = json.loads(self.state_file.read_text())
        deadline = datetime.fromisoformat(state['deadline'])

        # Time expired?
        if datetime.now() > deadline:
            return True, f"⚠️ Time limit exceeded on attempt {state['attempt']}"

        return False, None

    def record_failure(self):
        """Record that current approach failed"""
        if not self.state_file.exists():
            return False

        state = json.loads(self.state_file.read_text())
        state['attempt'] += 1

        if state['attempt'] > self.max_attempts:
            print(f"❌ {state['task']}: Failed {self.max_attempts} times - MUST CHANGE STRATEGY")
            return True  # Must pivot

        # Reset timer for next attempt
        state['start_time'] = datetime.now().isoformat()
        state['deadline'] = (datetime.now() + timedelta(minutes=self.max_time_per_attempt)).isoformat()
        self.state_file.write_text(json.dumps(state, indent=2))

        print(f"⚠️ Attempt {state['attempt']}/{self.max_attempts} - trying again")
        return False

    def complete_task(self):
        """Mark task as complete"""
        if self.state_file.exists():
            state = json.loads(self.state_file.read_text())
            print(f"✅ Completed: {state['task']} (took {state['attempt']} attempt(s))")
            self.state_file.unlink()

# Usage example:
# timer = TaskTimer()
# timer.start_task("Fix Telegram bot", "Approach: Kill zombie processes")
# ... try to fix ...
# if failed:
#     must_pivot = timer.record_failure()
#     if must_pivot:
#         # STOP and try different approach
# else:
#     timer.complete_task()
