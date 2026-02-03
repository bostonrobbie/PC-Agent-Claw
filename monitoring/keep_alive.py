#!/usr/bin/env python3
"""Keep-Alive Monitor - Ensures systems stay online"""
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
import sys
import json

sys.path.append(str(Path(__file__).parent.parent))

from core.persistent_memory import PersistentMemory
from core.telegram_connector import TelegramConnector

class KeepAliveMonitor:
    """Monitor system health and send keep-alive signals"""

    def __init__(self, check_interval: int = 60):
        """
        Args:
            check_interval: Seconds between health checks
        """
        workspace = Path(__file__).parent.parent
        self.memory = PersistentMemory(str(workspace / "memory.db"))
        self.telegram = TelegramConnector()

        self.check_interval = check_interval
        self.running = False
        self.thread = None

        self.last_heartbeat = datetime.now()
        self.heartbeat_file = workspace / "heartbeat.json"

        # Health check functions
        self.health_checks = {}
        self._register_default_checks()

    def _register_default_checks(self):
        """Register default health checks"""
        self.register_check('database', self._check_database)
        self.register_check('memory_usage', self._check_memory)
        self.register_check('disk_space', self._check_disk)

    def register_check(self, name: str, check_func):
        """Register a health check function"""
        self.health_checks[name] = check_func

        self.memory.log_decision(
            f'Health check registered: {name}',
            f'Function: {check_func.__name__}',
            tags=['keep_alive', 'registration', name]
        )

    def start(self, send_startup_notification: bool = True):
        """Start keep-alive monitoring"""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()

        self.memory.log_decision(
            'Keep-alive monitor started',
            f'Check interval: {self.check_interval}s',
            tags=['keep_alive', 'start']
        )

        if send_startup_notification:
            self.telegram.send_message(
                f"[ONLINE] System started at {datetime.now().strftime('%H:%M:%S')}"
            )

    def stop(self):
        """Stop keep-alive monitoring"""
        self.running = False

        self.memory.log_decision(
            'Keep-alive monitor stopped',
            '',
            tags=['keep_alive', 'stop']
        )

    def _monitor_loop(self):
        """Main monitoring loop"""
        consecutive_failures = 0

        while self.running:
            try:
                # Run health checks
                results = self.run_health_checks()

                # Update heartbeat
                self._update_heartbeat(results)

                # Check for failures
                failed_checks = [name for name, result in results.items() if not result['healthy']]

                if failed_checks:
                    consecutive_failures += 1

                    self.memory.log_decision(
                        f'Health check failures: {len(failed_checks)}',
                        f'Failed: {", ".join(failed_checks)}',
                        tags=['keep_alive', 'failure']
                    )

                    # Send alert if critical
                    if consecutive_failures >= 3:
                        self.telegram.send_message(
                            f"[ALERT] System health check failing\n"
                            f"Failed checks: {', '.join(failed_checks)}\n"
                            f"Consecutive failures: {consecutive_failures}"
                        )
                else:
                    consecutive_failures = 0

                # Sleep until next check
                time.sleep(self.check_interval)

            except Exception as e:
                self.memory.log_decision(
                    'Keep-alive monitor error',
                    f'Error: {str(e)}',
                    tags=['keep_alive', 'error']
                )
                time.sleep(self.check_interval)

    def run_health_checks(self) -> dict:
        """Run all registered health checks"""
        results = {}

        for name, check_func in self.health_checks.items():
            try:
                result = check_func()
                results[name] = {
                    'healthy': result,
                    'timestamp': datetime.now().isoformat()
                }
            except Exception as e:
                results[name] = {
                    'healthy': False,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }

        return results

    def _update_heartbeat(self, health_results: dict):
        """Update heartbeat file"""
        self.last_heartbeat = datetime.now()

        heartbeat_data = {
            'timestamp': self.last_heartbeat.isoformat(),
            'health_checks': health_results,
            'uptime_seconds': self._get_uptime()
        }

        try:
            with open(self.heartbeat_file, 'w') as f:
                json.dump(heartbeat_data, f, indent=2)
        except Exception as e:
            print(f"Failed to update heartbeat: {e}")

    def _get_uptime(self) -> float:
        """Get system uptime in seconds"""
        # Read from heartbeat file to get start time
        try:
            if self.heartbeat_file.exists():
                with open(self.heartbeat_file, 'r') as f:
                    data = json.load(f)
                    start_time = datetime.fromisoformat(data['timestamp'])
                    return (datetime.now() - start_time).total_seconds()
        except:
            pass

        return 0

    def send_heartbeat_notification(self):
        """Send periodic heartbeat notification"""
        health = self.run_health_checks()
        all_healthy = all(r['healthy'] for r in health.values())

        status = "[OK]" if all_healthy else "[ISSUE]"

        self.telegram.send_message(
            f"{status} System heartbeat\n"
            f"Time: {datetime.now().strftime('%H:%M:%S')}\n"
            f"Health checks: {len([r for r in health.values() if r['healthy']])}/{len(health)} passing"
        )

    # Default health check implementations
    def _check_database(self) -> bool:
        """Check if database is accessible"""
        try:
            cursor = self.memory.conn.cursor()
            cursor.execute('SELECT 1')
            return True
        except:
            return False

    def _check_memory(self) -> bool:
        """Check memory usage"""
        try:
            import psutil
            memory = psutil.virtual_memory()
            return memory.percent < 90  # Alert if >90% used
        except:
            return True  # Can't check, assume OK

    def _check_disk(self) -> bool:
        """Check disk space"""
        try:
            import psutil
            disk = psutil.disk_usage('C:\\')
            return disk.percent < 90  # Alert if >90% used
        except:
            return True  # Can't check, assume OK


class SystemWatchdog:
    """Watchdog to restart crashed components"""

    def __init__(self):
        workspace = Path(__file__).parent.parent
        self.memory = PersistentMemory(str(workspace / "memory.db"))
        self.telegram = TelegramConnector()

        self.watched_processes = {}
        self.running = False

    def watch_process(self, name: str, check_func, restart_func):
        """Watch a process and restart if it crashes"""
        self.watched_processes[name] = {
            'check': check_func,
            'restart': restart_func,
            'last_check': None,
            'restart_count': 0
        }

    def start(self):
        """Start watchdog"""
        if self.running:
            return

        self.running = True
        thread = threading.Thread(target=self._watchdog_loop, daemon=True)
        thread.start()

        self.memory.log_decision(
            'Watchdog started',
            f'Watching {len(self.watched_processes)} processes',
            tags=['watchdog', 'start']
        )

    def _watchdog_loop(self):
        """Watchdog monitoring loop"""
        while self.running:
            for name, process in self.watched_processes.items():
                try:
                    is_running = process['check']()

                    if not is_running:
                        self.memory.log_decision(
                            f'Process crashed: {name}',
                            f'Attempting restart',
                            tags=['watchdog', 'crash', name]
                        )

                        # Restart
                        process['restart']()
                        process['restart_count'] += 1

                        self.telegram.send_message(
                            f"[WATCHDOG] Restarted {name}\n"
                            f"Restart count: {process['restart_count']}"
                        )

                    process['last_check'] = datetime.now()

                except Exception as e:
                    self.memory.log_decision(
                        f'Watchdog error: {name}',
                        f'Error: {str(e)}',
                        tags=['watchdog', 'error', name]
                    )

            time.sleep(30)  # Check every 30 seconds


if __name__ == '__main__':
    # Test the system
    monitor = KeepAliveMonitor(check_interval=10)

    print("Keep-Alive Monitor ready!")
    print("\nStarting monitoring...")

    monitor.start(send_startup_notification=False)

    # Run for a bit
    try:
        for i in range(6):
            time.sleep(10)
            print(f"\nHeartbeat {i+1}")

            # Run checks
            results = monitor.run_health_checks()
            print(f"Health checks: {len([r for r in results.values() if r['healthy']])}/{len(results)} passing")

    except KeyboardInterrupt:
        print("\nStopping...")
        monitor.stop()
