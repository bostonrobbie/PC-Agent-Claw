#!/usr/bin/env python3
"""System Monitor - Comprehensive monitoring with notifications"""
import threading
import time
from datetime import datetime
from pathlib import Path
import sys
import json

sys.path.append(str(Path(__file__).parent.parent))

from core.persistent_memory import PersistentMemory
from core.telegram_connector import TelegramConnector
from monitoring.keep_alive import KeepAliveMonitor

class SystemMonitor:
    """Comprehensive system monitoring with Telegram notifications"""

    def __init__(self):
        workspace = Path(__file__).parent.parent
        self.memory = PersistentMemory(str(workspace / "memory.db"))
        self.telegram = TelegramConnector()
        self.keep_alive = KeepAliveMonitor(check_interval=300)  # 5 min

        self.running = False
        self.start_time = datetime.now()

        # Monitoring configuration
        self.config = {
            'heartbeat_interval': 3600,  # 1 hour
            'error_notification': True,
            'completion_notification': True,
            'progress_updates': True,
            'update_interval': 600  # 10 minutes
        }

        self.last_heartbeat = None
        self.last_update = None

    def start(self):
        """Start comprehensive monitoring"""
        if self.running:
            return

        self.running = True

        # Start keep-alive monitor
        self.keep_alive.start(send_startup_notification=False)

        # Start monitoring thread
        thread = threading.Thread(target=self._monitor_loop, daemon=True)
        thread.start()

        # Send startup notification
        self.notify_startup()

        self.memory.log_decision(
            'System monitor started',
            f'Full monitoring enabled',
            tags=['system_monitor', 'start']
        )

    def stop(self):
        """Stop monitoring"""
        self.running = False
        self.keep_alive.stop()

        self.notify_shutdown()

        self.memory.log_decision(
            'System monitor stopped',
            '',
            tags=['system_monitor', 'stop']
        )

    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                now = datetime.now()

                # Periodic heartbeat
                if (self.last_heartbeat is None or
                    (now - self.last_heartbeat).total_seconds() >= self.config['heartbeat_interval']):
                    self.send_heartbeat()
                    self.last_heartbeat = now

                # Progress updates
                if (self.config['progress_updates'] and
                    (self.last_update is None or
                     (now - self.last_update).total_seconds() >= self.config['update_interval'])):
                    self.send_progress_update()
                    self.last_update = now

                time.sleep(60)  # Check every minute

            except Exception as e:
                self.memory.log_decision(
                    'System monitor error',
                    f'Error: {str(e)}',
                    tags=['system_monitor', 'error']
                )
                time.sleep(60)

    def notify_startup(self):
        """Send startup notification"""
        message = (
            f"[SYSTEM ONLINE]\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"All systems initialized\n"
            f"Monitoring active"
        )

        self.telegram.send_message(message)

        self.memory.log_decision(
            'Startup notification sent',
            '',
            tags=['system_monitor', 'notification', 'startup']
        )

    def notify_shutdown(self):
        """Send shutdown notification"""
        uptime = self._format_uptime()

        message = (
            f"[SYSTEM OFFLINE]\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Uptime: {uptime}\n"
            f"Shutting down gracefully"
        )

        self.telegram.send_message(message)

    def notify_error(self, error_type: str, error_message: str, details: str = None):
        """Send error notification"""
        if not self.config['error_notification']:
            return

        message = (
            f"[ERROR] {error_type}\n"
            f"Message: {error_message}\n"
            f"Time: {datetime.now().strftime('%H:%M:%S')}"
        )

        if details:
            message += f"\nDetails: {details[:200]}"

        self.telegram.send_message(message)

        self.memory.log_decision(
            f'Error notification sent: {error_type}',
            error_message,
            tags=['system_monitor', 'notification', 'error']
        )

    def notify_completion(self, task: str, result: str = None):
        """Send task completion notification"""
        if not self.config['completion_notification']:
            return

        message = f"[COMPLETE] {task}\n"

        if result:
            message += f"Result: {result}\n"

        message += f"Time: {datetime.now().strftime('%H:%M:%S')}"

        self.telegram.send_message(message)

        self.memory.log_decision(
            f'Completion notification sent: {task}',
            result or '',
            tags=['system_monitor', 'notification', 'completion']
        )

    def send_heartbeat(self):
        """Send periodic heartbeat"""
        uptime = self._format_uptime()
        health = self.keep_alive.run_health_checks()
        healthy_count = len([r for r in health.values() if r['healthy']])

        # Get task stats
        cursor = self.memory.conn.cursor()
        cursor.execute("SELECT status, COUNT(*) FROM tasks GROUP BY status")
        task_stats = dict(cursor.fetchall())

        message = (
            f"[HEARTBEAT]\n"
            f"Time: {datetime.now().strftime('%H:%M:%S')}\n"
            f"Uptime: {uptime}\n"
            f"Health: {healthy_count}/{len(health)} checks passing\n"
            f"Tasks - Pending: {task_stats.get('pending', 0)}, "
            f"In Progress: {task_stats.get('in_progress', 0)}, "
            f"Complete: {task_stats.get('completed', 0)}"
        )

        self.telegram.send_message(message)

    def send_progress_update(self):
        """Send progress update"""
        # Get recent activity
        cursor = self.memory.conn.cursor()

        # Get recent tasks
        cursor.execute("""
            SELECT COUNT(*) FROM tasks
            WHERE updated_at >= datetime('now', '-10 minutes')
        """)
        recent_tasks = cursor.fetchone()[0]

        # Get recent decisions
        cursor.execute("""
            SELECT COUNT(*) FROM decisions
            WHERE created_at >= datetime('now', '-10 minutes')
        """)
        recent_decisions = cursor.fetchone()[0]

        if recent_tasks > 0 or recent_decisions > 0:
            message = (
                f"[UPDATE]\n"
                f"Last 10 min:\n"
                f"Tasks updated: {recent_tasks}\n"
                f"Decisions logged: {recent_decisions}\n"
                f"Time: {datetime.now().strftime('%H:%M:%S')}"
            )

            self.telegram.send_message(message)

    def notify_work_complete(self, summary: str):
        """Send work completion summary"""
        message = (
            f"[WORK COMPLETE]\n"
            f"{summary}\n"
            f"Time: {datetime.now().strftime('%H:%M:%S')}"
        )

        self.telegram.send_message(message)

    def _format_uptime(self) -> str:
        """Format uptime as readable string"""
        uptime = datetime.now() - self.start_time
        hours = int(uptime.total_seconds() // 3600)
        minutes = int((uptime.total_seconds() % 3600) // 60)

        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"

    def get_stats(self) -> dict:
        """Get monitoring statistics"""
        return {
            'running': self.running,
            'uptime': self._format_uptime(),
            'telegram_enabled': self.telegram.enabled,
            'messages_sent': self.telegram.messages_sent,
            'messages_failed': self.telegram.messages_failed,
            'config': self.config
        }


# Global monitor instance
_monitor = None

def get_monitor() -> SystemMonitor:
    """Get or create global monitor instance"""
    global _monitor
    if _monitor is None:
        _monitor = SystemMonitor()
    return _monitor

def start_monitoring():
    """Start system monitoring"""
    monitor = get_monitor()
    monitor.start()
    return monitor

def notify_error(error_type: str, message: str, details: str = None):
    """Quick error notification"""
    monitor = get_monitor()
    monitor.notify_error(error_type, message, details)

def notify_completion(task: str, result: str = None):
    """Quick completion notification"""
    monitor = get_monitor()
    monitor.notify_completion(task, result)


if __name__ == '__main__':
    # Test the system
    print("System Monitor ready!")

    monitor = SystemMonitor()

    print("\nStarting monitoring...")
    monitor.start()

    print("Monitor running. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(10)
            stats = monitor.get_stats()
            print(f"\nUptime: {stats['uptime']}")
            print(f"Telegram: {'Enabled' if stats['telegram_enabled'] else 'Disabled'}")
            print(f"Messages sent: {stats['messages_sent']}")

    except KeyboardInterrupt:
        print("\nStopping monitor...")
        monitor.stop()
