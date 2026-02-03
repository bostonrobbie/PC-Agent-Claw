#!/usr/bin/env python3
"""
Resource-Aware Execution Manager
Monitor and optimize resource usage
"""
import sys
from pathlib import Path
import psutil
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
import threading
import time

sys.path.append(str(Path(__file__).parent.parent))


class ResourceManager:
    """
    Resource-aware execution manager

    Features:
    - CPU/memory/disk monitoring
    - Adaptive execution based on resources
    - Pause non-critical work when busy
    - Schedule work for optimal times
    - Cost optimization
    """

    def __init__(self, db_path: str = None):
        workspace = Path(__file__).parent.parent
        if db_path is None:
            db_path = str(workspace / "memory.db")

        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

        # Resource thresholds
        self.thresholds = {
            'cpu_high': 80,      # % CPU usage
            'memory_high': 80,   # % Memory usage
            'disk_high': 85,     # % Disk usage
            'cpu_critical': 95,
            'memory_critical': 95
        }

        # Monitoring state
        self.monitoring = False
        self.monitor_thread = None
        self.paused_tasks = []

    def _init_db(self):
        """Initialize database schema"""
        cursor = self.conn.cursor()

        # Resource usage history
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS resource_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cpu_percent REAL,
                memory_percent REAL,
                disk_percent REAL,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Scheduled tasks
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scheduled_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_name TEXT NOT NULL,
                task_priority INTEGER DEFAULT 2,
                resource_requirements TEXT,
                scheduled_for TIMESTAMP,
                status TEXT DEFAULT 'pending',
                executed_at TIMESTAMP,
                execution_duration REAL
            )
        ''')

        # Resource events
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS resource_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                severity TEXT,
                details TEXT,
                action_taken TEXT,
                occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        self.conn.commit()

    # === RESOURCE MONITORING ===

    def get_current_resources(self) -> Dict:
        """Get current resource usage"""
        return {
            'cpu_percent': psutil.cpu_percent(interval=0.1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
            'timestamp': datetime.now()
        }

    def record_resources(self) -> Dict:
        """Record current resources to database"""
        resources = self.get_current_resources()

        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO resource_usage (cpu_percent, memory_percent, disk_percent)
            VALUES (?, ?, ?)
        ''', (resources['cpu_percent'], resources['memory_percent'], resources['disk_percent']))
        self.conn.commit()

        return resources

    def start_monitoring(self, interval_seconds: int = 60):
        """Start resource monitoring"""
        if self.monitoring:
            return

        self.monitoring = True

        def monitor_loop():
            while self.monitoring:
                resources = self.record_resources()

                # Check thresholds
                self._check_thresholds(resources)

                time.sleep(interval_seconds)

        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()

        print("[RESOURCE] Monitoring started")

    def stop_monitoring(self):
        """Stop resource monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)

        print("[RESOURCE] Monitoring stopped")

    def _check_thresholds(self, resources: Dict):
        """Check resource thresholds and take action"""
        cpu = resources['cpu_percent']
        memory = resources['memory_percent']

        # Critical levels - pause non-essential work
        if cpu > self.thresholds['cpu_critical'] or memory > self.thresholds['memory_critical']:
            self._handle_critical_resources(cpu, memory)

        # High levels - warning
        elif cpu > self.thresholds['cpu_high'] or memory > self.thresholds['memory_high']:
            self._log_event(
                "high_usage",
                "warning",
                f"CPU: {cpu:.1f}%, Memory: {memory:.1f}%",
                "Monitoring"
            )

    def _handle_critical_resources(self, cpu: float, memory: float):
        """Handle critical resource situation"""
        self._log_event(
            "critical_usage",
            "critical",
            f"CPU: {cpu:.1f}%, Memory: {memory:.1f}%",
            "Pausing non-critical tasks"
        )

        # Here would pause actual tasks
        # For now, just log
        print(f"[RESOURCE] CRITICAL: CPU {cpu:.1f}%, Memory {memory:.1f}%")

    def _log_event(self, event_type: str, severity: str, details: str, action: str):
        """Log resource event"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO resource_events (event_type, severity, details, action_taken)
            VALUES (?, ?, ?, ?)
        ''', (event_type, severity, details, action))
        self.conn.commit()

    # === ADAPTIVE EXECUTION ===

    def should_execute_now(self, resource_requirements: Dict) -> bool:
        """
        Determine if task should execute now based on resources

        Args:
            resource_requirements: Required resources (cpu, memory)

        Returns:
            True if sufficient resources available
        """
        current = self.get_current_resources()

        required_cpu = resource_requirements.get('cpu', 0)
        required_memory = resource_requirements.get('memory', 0)

        # Check if enough resources available
        if current['cpu_percent'] + required_cpu > self.thresholds['cpu_high']:
            return False

        if current['memory_percent'] + required_memory > self.thresholds['memory_high']:
            return False

        return True

    def execute_when_available(self, task_func: Callable, resource_requirements: Dict,
                              priority: int = 2, timeout_hours: float = 24) -> bool:
        """
        Execute task when resources available

        Args:
            task_func: Function to execute
            resource_requirements: Required resources
            priority: Task priority (1=low, 3=high)
            timeout_hours: Max wait time

        Returns:
            True if executed successfully
        """
        start_time = datetime.now()
        timeout = timedelta(hours=timeout_hours)

        while datetime.now() - start_time < timeout:
            if self.should_execute_now(resource_requirements):
                try:
                    task_func()
                    return True
                except Exception as e:
                    print(f"[RESOURCE] Task execution failed: {e}")
                    return False

            # Wait before retry
            time.sleep(60)  # Check every minute

        print(f"[RESOURCE] Task timed out waiting for resources")
        return False

    # === SCHEDULING ===

    def schedule_task(self, task_name: str, scheduled_for: datetime,
                     resource_requirements: Dict = None, priority: int = 2) -> int:
        """
        Schedule task for future execution

        Args:
            task_name: Task identifier
            scheduled_for: When to execute
            resource_requirements: Required resources
            priority: Task priority

        Returns:
            Task ID
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO scheduled_tasks
            (task_name, task_priority, resource_requirements, scheduled_for)
            VALUES (?, ?, ?, ?)
        ''', (task_name, priority,
              str(resource_requirements) if resource_requirements else None,
              scheduled_for))
        self.conn.commit()

        return cursor.lastrowid

    def get_pending_tasks(self) -> List[Dict]:
        """Get tasks ready to execute"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM scheduled_tasks
            WHERE status = 'pending'
            AND scheduled_for <= CURRENT_TIMESTAMP
            ORDER BY task_priority DESC, scheduled_for ASC
        ''')

        return [dict(row) for row in cursor.fetchall()]

    # === OPTIMIZATION ===

    def find_optimal_time(self, duration_hours: float = 1, days_ahead: int = 7) -> datetime:
        """
        Find optimal time for resource-intensive task

        Args:
            duration_hours: Task duration
            days_ahead: Days to look ahead

        Returns:
            Optimal start time
        """
        cursor = self.conn.cursor()

        # Get historical usage patterns
        cursor.execute('''
            SELECT
                CAST(strftime('%H', recorded_at) AS INTEGER) as hour,
                AVG(cpu_percent) as avg_cpu,
                AVG(memory_percent) as avg_memory
            FROM resource_usage
            WHERE recorded_at >= datetime('now', '-7 days')
            GROUP BY hour
            ORDER BY avg_cpu ASC, avg_memory ASC
        ''')

        results = cursor.fetchall()

        if not results:
            # Default to 2 AM
            optimal_time = datetime.now().replace(hour=2, minute=0, second=0, microsecond=0)
            if optimal_time < datetime.now():
                optimal_time += timedelta(days=1)
            return optimal_time

        # Find hour with lowest usage
        best_hour = results[0]['hour']

        # Schedule for that hour tomorrow
        optimal_time = datetime.now().replace(hour=best_hour, minute=0, second=0, microsecond=0)
        if optimal_time < datetime.now():
            optimal_time += timedelta(days=1)

        return optimal_time

    # === ANALYTICS ===

    def get_resource_summary(self, hours: int = 24) -> Dict:
        """Get resource usage summary"""
        cursor = self.conn.cursor()

        cursor.execute('''
            SELECT
                AVG(cpu_percent) as avg_cpu,
                MAX(cpu_percent) as max_cpu,
                AVG(memory_percent) as avg_memory,
                MAX(memory_percent) as max_memory,
                AVG(disk_percent) as avg_disk
            FROM resource_usage
            WHERE recorded_at >= datetime('now', ? || ' hours')
        ''', (f'-{hours}',))

        result = cursor.fetchone()

        # Recent events
        cursor.execute('''
            SELECT COUNT(*) as count, severity
            FROM resource_events
            WHERE occurred_at >= datetime('now', ? || ' hours')
            GROUP BY severity
        ''', (f'-{hours}',))

        events = {row['severity']: row['count'] for row in cursor.fetchall()}

        return {
            'avg_cpu': round(result['avg_cpu'], 1) if result['avg_cpu'] else 0,
            'max_cpu': round(result['max_cpu'], 1) if result['max_cpu'] else 0,
            'avg_memory': round(result['avg_memory'], 1) if result['avg_memory'] else 0,
            'max_memory': round(result['max_memory'], 1) if result['max_memory'] else 0,
            'avg_disk': round(result['avg_disk'], 1) if result['avg_disk'] else 0,
            'events': events
        }

    def close(self):
        """Close database connection"""
        self.stop_monitoring()
        self.conn.close()


# === TEST CODE ===

def main():
    """Test resource manager"""
    print("Testing Resource Manager")
    print("=" * 70)

    manager = ResourceManager()

    try:
        # Get current resources
        print("\n1. Getting current resources...")
        resources = manager.get_current_resources()
        print(f"   CPU: {resources['cpu_percent']:.1f}%")
        print(f"   Memory: {resources['memory_percent']:.1f}%")
        print(f"   Disk: {resources['disk_percent']:.1f}%")

        # Record resources
        print("\n2. Recording resources...")
        manager.record_resources()
        print("   Resources recorded")

        # Check if should execute
        print("\n3. Checking if should execute...")
        can_execute = manager.should_execute_now({'cpu': 10, 'memory': 5})
        print(f"   Can execute: {can_execute}")

        # Schedule task
        print("\n4. Scheduling task...")
        task_id = manager.schedule_task(
            "test_task",
            datetime.now() + timedelta(hours=1),
            {'cpu': 20, 'memory': 10},
            priority=2
        )
        print(f"   Task scheduled: ID {task_id}")

        # Find optimal time
        print("\n5. Finding optimal execution time...")
        optimal_time = manager.find_optimal_time(duration_hours=2)
        print(f"   Optimal time: {optimal_time.strftime('%Y-%m-%d %H:%M')}")

        # Get summary
        print("\n6. Getting resource summary...")
        summary = manager.get_resource_summary(hours=24)
        print(f"   Avg CPU: {summary['avg_cpu']}%")
        print(f"   Avg Memory: {summary['avg_memory']}%")
        print(f"   Events: {summary['events']}")

        # Start monitoring briefly
        print("\n7. Testing monitoring (5 seconds)...")
        manager.start_monitoring(interval_seconds=2)
        time.sleep(5)
        manager.stop_monitoring()

        print(f"\n[OK] Resource Manager working!")
        print(f"Database: {manager.db_path}")

    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        manager.close()


if __name__ == "__main__":
    main()
