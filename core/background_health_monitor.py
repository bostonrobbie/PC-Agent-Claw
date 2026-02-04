"""
Continuous Background Health Monitoring - HIGH PRIORITY IMPROVEMENT #2

Monitors all systems continuously in the background to detect issues early.
Based on real-world testing data showing value of continuous monitoring.
"""

import threading
import time
import sqlite3
import psutil
from datetime import datetime
from typing import Dict, List, Callable
from dataclasses import dataclass
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class HealthCheck:
    """Result of a health check"""
    component: str
    status: str  # healthy, degraded, unhealthy
    metric_value: float
    threshold: float
    message: str
    timestamp: str


class BackgroundHealthMonitor:
    """
    Continuously monitors system health in background thread

    Detects issues early before they impact users.
    """

    def __init__(self, db_path: str = "health_monitor.db", check_interval: int = 30):
        self.db_path = db_path
        self.check_interval = check_interval
        self.running = False
        self.monitor_thread = None
        self.health_checks: List[Callable] = []
        self.alerts: List[str] = []

        self._init_db()
        self._register_default_checks()

    def _init_db(self):
        """Initialize health monitoring database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS health_checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                component TEXT,
                status TEXT,
                metric_value REAL,
                threshold REAL,
                message TEXT,
                timestamp TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                component TEXT,
                severity TEXT,
                message TEXT,
                triggered_at TEXT,
                resolved_at TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cpu_percent REAL,
                memory_mb REAL,
                disk_percent REAL,
                timestamp TEXT
            )
        ''')

        conn.commit()
        conn.close()

    def _register_default_checks(self):
        """Register default health checks"""
        self.health_checks = [
            self._check_cpu_usage,
            self._check_memory_usage,
            self._check_disk_space,
            self._check_database_sizes,
            self._check_capability_status
        ]

    def _check_cpu_usage(self) -> HealthCheck:
        """Check CPU usage"""
        cpu = psutil.cpu_percent(interval=1)
        threshold = 80.0

        if cpu > threshold:
            status = "degraded" if cpu < 90 else "unhealthy"
            message = f"High CPU usage: {cpu:.1f}%"
        else:
            status = "healthy"
            message = f"CPU usage normal: {cpu:.1f}%"

        return HealthCheck(
            component="cpu",
            status=status,
            metric_value=cpu,
            threshold=threshold,
            message=message,
            timestamp=datetime.now().isoformat()
        )

    def _check_memory_usage(self) -> HealthCheck:
        """Check memory usage"""
        mem = psutil.virtual_memory()
        mem_mb = mem.used / 1024 / 1024
        threshold = 1024.0  # 1GB

        if mem_mb > threshold:
            status = "degraded" if mem_mb < 2048 else "unhealthy"
            message = f"High memory usage: {mem_mb:.0f} MB"
        else:
            status = "healthy"
            message = f"Memory usage normal: {mem_mb:.0f} MB"

        return HealthCheck(
            component="memory",
            status=status,
            metric_value=mem_mb,
            threshold=threshold,
            message=message,
            timestamp=datetime.now().isoformat()
        )

    def _check_disk_space(self) -> HealthCheck:
        """Check disk space"""
        disk = psutil.disk_usage('.')
        percent = disk.percent
        threshold = 80.0

        if percent > threshold:
            status = "degraded" if percent < 90 else "unhealthy"
            message = f"Low disk space: {percent:.1f}% used"
        else:
            status = "healthy"
            message = f"Disk space OK: {percent:.1f}% used"

        return HealthCheck(
            component="disk",
            status=status,
            metric_value=percent,
            threshold=threshold,
            message=message,
            timestamp=datetime.now().isoformat()
        )

    def _check_database_sizes(self) -> HealthCheck:
        """Check database file sizes"""
        import os
        import glob

        db_files = glob.glob("*.db")
        total_size_mb = sum(os.path.getsize(f) for f in db_files if os.path.exists(f)) / 1024 / 1024
        threshold = 500.0  # 500MB

        if total_size_mb > threshold:
            status = "degraded"
            message = f"Large database size: {total_size_mb:.0f} MB across {len(db_files)} DBs"
        else:
            status = "healthy"
            message = f"Database sizes normal: {total_size_mb:.0f} MB"

        return HealthCheck(
            component="databases",
            status=status,
            metric_value=total_size_mb,
            threshold=threshold,
            message=message,
            timestamp=datetime.now().isoformat()
        )

    def _check_capability_status(self) -> HealthCheck:
        """Check if key capabilities are responding"""
        # Try to connect to key databases
        key_dbs = [
            'semantic_code_search.db',
            'persistent_memory.db',
            'capability_synergy.db'
        ]

        accessible = 0
        for db in key_dbs:
            try:
                import os
                if os.path.exists(db):
                    conn = sqlite3.connect(db, timeout=1)
                    conn.close()
                    accessible += 1
            except:
                pass

        status = "healthy" if accessible == len(key_dbs) else "degraded"
        message = f"{accessible}/{len(key_dbs)} key capabilities accessible"

        return HealthCheck(
            component="capabilities",
            status=status,
            metric_value=accessible,
            threshold=len(key_dbs),
            message=message,
            timestamp=datetime.now().isoformat()
        )

    def _run_health_checks(self):
        """Run all registered health checks"""
        results = []

        for check in self.health_checks:
            try:
                result = check()
                results.append(result)

                # Record in database
                self._record_check(result)

                # Generate alert if unhealthy
                if result.status in ['degraded', 'unhealthy']:
                    self._generate_alert(result)

            except Exception as e:
                logger.error(f"Health check failed: {e}")

        return results

    def _record_check(self, check: HealthCheck):
        """Record health check result"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO health_checks
            (component, status, metric_value, threshold, message, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            check.component,
            check.status,
            check.metric_value,
            check.threshold,
            check.message,
            check.timestamp
        ))

        # Record system metrics
        if check.component in ['cpu', 'memory']:
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory().used / 1024 / 1024
            disk = psutil.disk_usage('.').percent

            cursor.execute('''
                INSERT INTO system_metrics (cpu_percent, memory_mb, disk_percent, timestamp)
                VALUES (?, ?, ?, ?)
            ''', (cpu, mem, disk, datetime.now().isoformat()))

        conn.commit()
        conn.close()

    def _generate_alert(self, check: HealthCheck):
        """Generate alert for unhealthy component"""
        severity = "warning" if check.status == "degraded" else "critical"

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check if alert already exists
        cursor.execute('''
            SELECT id FROM alerts
            WHERE component = ? AND resolved_at IS NULL
        ''', (check.component,))

        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO alerts (component, severity, message, triggered_at)
                VALUES (?, ?, ?, ?)
            ''', (check.component, severity, check.message, datetime.now().isoformat()))

            self.alerts.append(f"[{severity.upper()}] {check.component}: {check.message}")
            logger.warning(f"Alert generated: {check.message}")

        conn.commit()
        conn.close()

    def _monitoring_loop(self):
        """Main monitoring loop that runs in background"""
        logger.info(f"Background health monitoring started (interval: {self.check_interval}s)")

        while self.running:
            try:
                results = self._run_health_checks()

                # Log summary
                healthy = sum(1 for r in results if r.status == "healthy")
                logger.info(f"Health check: {healthy}/{len(results)} components healthy")

            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")

            time.sleep(self.check_interval)

        logger.info("Background health monitoring stopped")

    def start(self):
        """Start background monitoring"""
        if self.running:
            logger.warning("Monitor already running")
            return

        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Background health monitor started")

    def stop(self):
        """Stop background monitoring"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Background health monitor stopped")

    def get_current_status(self) -> Dict:
        """Get current system health status"""
        results = self._run_health_checks()

        return {
            'overall_status': 'healthy' if all(r.status == 'healthy' for r in results) else 'degraded',
            'components': [
                {
                    'name': r.component,
                    'status': r.status,
                    'metric': r.metric_value,
                    'threshold': r.threshold,
                    'message': r.message
                }
                for r in results
            ],
            'active_alerts': len(self.alerts),
            'timestamp': datetime.now().isoformat()
        }

    def get_health_history(self, hours: int = 1) -> Dict:
        """Get health check history"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get recent checks
        cursor.execute('''
            SELECT component, status, COUNT(*) as count
            FROM health_checks
            WHERE datetime(timestamp) > datetime('now', '-{} hours')
            GROUP BY component, status
            ORDER BY component
        '''.replace('{}', str(hours)))

        history = {}
        for row in cursor.fetchall():
            component = row[0]
            if component not in history:
                history[component] = {}
            history[component][row[1]] = row[2]

        conn.close()

        return history


# Example usage
if __name__ == '__main__':
    monitor = BackgroundHealthMonitor(check_interval=10)

    # Start monitoring
    monitor.start()

    # Let it run for a minute
    print("Monitoring for 60 seconds...")
    time.sleep(60)

    # Get status
    status = monitor.get_current_status()
    print(f"\nOverall status: {status['overall_status']}")
    print(f"Components: {len(status['components'])}")
    for comp in status['components']:
        print(f"  [{comp['status']}] {comp['name']}: {comp['message']}")

    # Stop monitoring
    monitor.stop()
