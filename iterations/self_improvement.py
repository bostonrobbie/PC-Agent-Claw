#!/usr/bin/env python3
"""
Self-Improvement System - Learn and iterate to become better
"""

from pathlib import Path
from datetime import datetime
import json

WORKSPACE = Path(r"C:\Users\User\.openclaw\workspace")
ITERATIONS = WORKSPACE / "iterations"
MEMORY = WORKSPACE / "memory"

class SelfImprovement:
    """Track performance, learn from mistakes, iterate and improve"""

    def __init__(self):
        ITERATIONS.mkdir(parents=True, exist_ok=True)
        self.metrics_file = ITERATIONS / "metrics.json"
        self.version_log = ITERATIONS / "version-log.md"
        self.improvements = ITERATIONS / "improvements.md"
        self.goals = ITERATIONS / "goals.md"

        self.metrics = self._load_metrics()

    def _load_metrics(self):
        """Load performance metrics"""
        if self.metrics_file.exists():
            with open(self.metrics_file, 'r') as f:
                return json.load(f)
        else:
            return {
                'version': '1.0.0',
                'sessions_completed': 0,
                'tasks_completed': 0,
                'tasks_failed': 0,
                'success_rate': 100.0,
                'mistakes_made': 0,
                'mistakes_avoided': 0,
                'learnings_captured': 0,
                'capabilities_added': [],
                'performance_history': []
            }

    def _save_metrics(self):
        """Save metrics to file"""
        with open(self.metrics_file, 'w', encoding='utf-8') as f:
            json.dump(self.metrics, f, indent=2)

    def record_session(self, tasks_done, tasks_failed, learnings_captured):
        """Record session statistics"""
        self.metrics['sessions_completed'] += 1
        self.metrics['tasks_completed'] += tasks_done
        self.metrics['tasks_failed'] += tasks_failed
        self.metrics['learnings_captured'] += learnings_captured

        total = self.metrics['tasks_completed'] + self.metrics['tasks_failed']
        if total > 0:
            self.metrics['success_rate'] = (self.metrics['tasks_completed'] / total) * 100

        # Add to history
        self.metrics['performance_history'].append({
            'date': datetime.now().isoformat(),
            'tasks_done': tasks_done,
            'tasks_failed': tasks_failed,
            'success_rate': (tasks_done / (tasks_done + tasks_failed) * 100) if (tasks_done + tasks_failed) > 0 else 100
        })

        self._save_metrics()

    def add_capability(self, capability_name, description):
        """Record a new capability I gained"""
        self.metrics['capabilities_added'].append({
            'date': datetime.now().isoformat(),
            'name': capability_name,
            'description': description
        })
        self._save_metrics()

        # Log to improvements
        with open(self.improvements, 'a', encoding='utf-8') as f:
            f.write(f"\n## {datetime.now().strftime('%Y-%m-%d')} - New Capability: {capability_name}\n")
            f.write(f"{description}\n\n")

    def record_mistake_avoided(self, mistake_type, how_avoided):
        """Record that I avoided a past mistake"""
        self.metrics['mistakes_avoided'] += 1
        self._save_metrics()

        with open(self.improvements, 'a', encoding='utf-8') as f:
            f.write(f"\n## {datetime.now().strftime('%Y-%m-%d %H:%M')} - Avoided Mistake\n")
            f.write(f"**Type:** {mistake_type}\n")
            f.write(f"**How:** {how_avoided}\n\n")

    def record_mistake_made(self, mistake_type):
        """Record a new mistake"""
        self.metrics['mistakes_made'] += 1
        self._save_metrics()

    def set_goals(self, goals_list):
        """Set improvement goals"""
        with open(self.goals, 'w', encoding='utf-8') as f:
            f.write(f"# Self-Improvement Goals\n")
            f.write(f"**Set:** {datetime.now().strftime('%Y-%m-%d')}\n\n")

            for goal in goals_list:
                f.write(f"- [ ] {goal}\n")

    def version_upgrade(self, new_version, changes):
        """Log a version upgrade"""
        self.metrics['version'] = new_version
        self._save_metrics()

        with open(self.version_log, 'a', encoding='utf-8') as f:
            f.write(f"\n## Version {new_version} - {datetime.now().strftime('%Y-%m-%d')}\n")
            for change in changes:
                f.write(f"- {change}\n")
            f.write("\n")

    def get_performance_report(self):
        """Generate performance report"""
        total_tasks = self.metrics['tasks_completed'] + self.metrics['tasks_failed']

        report = f"""
# Performance Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Overall Statistics
- Version: {self.metrics['version']}
- Sessions Completed: {self.metrics['sessions_completed']}
- Tasks Completed: {self.metrics['tasks_completed']}
- Tasks Failed: {self.metrics['tasks_failed']}
- Success Rate: {self.metrics['success_rate']:.1f}%

## Learning & Growth
- Learnings Captured: {self.metrics['learnings_captured']}
- Mistakes Made: {self.metrics['mistakes_made']}
- Mistakes Avoided: {self.metrics['mistakes_avoided']}
- Improvement Rate: {(self.metrics['mistakes_avoided'] / max(self.metrics['mistakes_made'], 1) * 100):.1f}%

## New Capabilities
"""
        for cap in self.metrics['capabilities_added']:
            report += f"- {cap['date'][:10]}: {cap['name']}\n"

        return report

# Initialize for today
if __name__ == "__main__":
    improver = SelfImprovement()

    # Record today's session
    improver.record_session(
        tasks_done=15,  # Connected 5 AIs, built router, created memory system
        tasks_failed=1,  # Claude Web timeout
        learnings_captured=5  # Multiple learnings documented
    )

    # New capabilities added today
    improver.add_capability(
        "Multi-AI Orchestration",
        "Can now coordinate 5 different AI services (GPU, ChatGPT, Manus, Antigravity, Claude) with intelligent routing"
    )

    improver.add_capability(
        "Local GPU Inference",
        "Running Llama 3.2 3B on RTX 3060 for free, fast inference (~7 tok/s)"
    )

    improver.add_capability(
        "Memory System",
        "Persistent memory across sessions with conversation logging, learnings extraction, and knowledge building"
    )

    # Avoided a mistake
    improver.record_mistake_avoided(
        "Unicode encoding",
        "Remembered to handle unicode properly in console output, used ASCII alternatives and utf-8 encoding"
    )

    # Set goals
    improver.set_goals([
        "Achieve >95% success rate on tasks",
        "Build autonomous business operations",
        "Reduce Rob's workload by 80%",
        "Learn from every mistake immediately",
        "Proactively suggest improvements",
        "Anticipate Rob's needs before he asks"
    ])

    # Version upgrade
    improver.version_upgrade("1.1.0", [
        "Added multi-AI orchestration",
        "Implemented GPU local LLM",
        "Built memory and learning systems",
        "Created self-improvement loop",
        "Established backup strategy"
    ])

    print(improver.get_performance_report())

    print(f"\nMetrics saved to: {improver.metrics_file}")
    print(f"Version log: {improver.version_log}")
    print(f"Improvements: {improver.improvements}")
    print(f"Goals: {improver.goals}")
