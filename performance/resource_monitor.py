"""
System Resource Monitor - Production-Ready Resource Management System

This module provides comprehensive system resource monitoring, tracking, and optimization
recommendations using psutil and SQLite for persistent storage.

Features:
- Real-time CPU, memory, and disk usage monitoring
- Resource-aware suggestions for optimization
- Performance optimization recommendations
- System health monitoring and alerts
- Efficient resource usage tracking
- Constraint-aware planning
- Optimization triggers based on resource thresholds
- Historical tracking with SQLite
- Alerting system for resource anomalies
"""

import sqlite3
import psutil
import time
import json
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ResourceMetrics:
    """Data class for system resource metrics"""
    timestamp: str
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_used_gb: float
    disk_total_gb: float
    process_count: int
    system_health_score: float


@dataclass
class Alert:
    """Data class for system alerts"""
    timestamp: str
    alert_type: str
    severity: str
    message: str
    metric_value: float
    threshold: float


class ResourceMonitor:
    """
    Production-ready system resource monitoring and management system.

    Tracks CPU, memory, and disk usage with optimization recommendations
    and constraint-aware planning.
    """

    def __init__(self, db_path: str = "resource_monitor.db",
                 retention_days: int = 30):
        """
        Initialize the Resource Monitor.

        Args:
            db_path: Path to SQLite database
            retention_days: Days of historical data to retain
        """
        self.db_path = db_path
        self.retention_days = retention_days

        # Resource thresholds (percentages)
        self.thresholds = {
            'cpu_warning': 75.0,
            'cpu_critical': 90.0,
            'memory_warning': 80.0,
            'memory_critical': 95.0,
            'disk_warning': 85.0,
            'disk_critical': 95.0,
        }

        # Alert tracking
        self.recent_alerts = []
        self.max_recent_alerts = 100

        # Initialize database
        self._init_database()

    def _init_database(self) -> None:
        """Initialize SQLite database with required tables."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    cpu_percent REAL,
                    memory_percent REAL,
                    disk_percent REAL,
                    memory_used_mb REAL,
                    memory_available_mb REAL,
                    disk_used_gb REAL,
                    disk_total_gb REAL,
                    process_count INTEGER,
                    system_health_score REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Alerts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT,
                    metric_value REAL,
                    threshold REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Optimization history table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS optimizations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    recommendation TEXT NOT NULL,
                    estimated_savings REAL,
                    applied BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Create indexes for better query performance
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_metrics_timestamp
                ON metrics(timestamp)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_alerts_timestamp
                ON alerts(timestamp)
            ''')

            conn.commit()
            conn.close()
            logger.info(f"Database initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            raise

    def get_system_metrics(self) -> ResourceMetrics:
        """
        Collect current system resource metrics.

        Returns:
            ResourceMetrics: Current system metrics
        """
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            process_count = len(psutil.pids())

            # Calculate system health score (0-100)
            health_score = self._calculate_health_score(
                cpu_percent,
                memory.percent,
                disk.percent
            )

            metrics = ResourceMetrics(
                timestamp=datetime.now().isoformat(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                disk_percent=disk.percent,
                memory_used_mb=memory.used / (1024 ** 2),
                memory_available_mb=memory.available / (1024 ** 2),
                disk_used_gb=disk.used / (1024 ** 3),
                disk_total_gb=disk.total / (1024 ** 3),
                process_count=process_count,
                system_health_score=health_score
            )

            return metrics
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            raise

    def _calculate_health_score(self, cpu: float, memory: float,
                                 disk: float) -> float:
        """
        Calculate overall system health score.

        Args:
            cpu: CPU usage percentage
            memory: Memory usage percentage
            disk: Disk usage percentage

        Returns:
            float: Health score (0-100, higher is better)
        """
        # Weight the components
        cpu_score = max(0, 100 - cpu)
        memory_score = max(0, 100 - memory)
        disk_score = max(0, 100 - disk)

        # Weighted average (memory is most critical)
        health = (cpu_score * 0.3 + memory_score * 0.5 + disk_score * 0.2)
        return round(health, 2)

    def store_metrics(self, metrics: ResourceMetrics) -> None:
        """
        Store metrics in database.

        Args:
            metrics: ResourceMetrics to store
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO metrics (
                    timestamp, cpu_percent, memory_percent, disk_percent,
                    memory_used_mb, memory_available_mb, disk_used_gb,
                    disk_total_gb, process_count, system_health_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                metrics.timestamp,
                metrics.cpu_percent,
                metrics.memory_percent,
                metrics.disk_percent,
                metrics.memory_used_mb,
                metrics.memory_available_mb,
                metrics.disk_used_gb,
                metrics.disk_total_gb,
                metrics.process_count,
                metrics.system_health_score
            ))

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error storing metrics: {e}")

    def check_thresholds(self, metrics: ResourceMetrics) -> List[Alert]:
        """
        Check if metrics exceed defined thresholds and generate alerts.

        Args:
            metrics: ResourceMetrics to check

        Returns:
            List[Alert]: List of alerts if thresholds exceeded
        """
        alerts = []

        # Check CPU
        if metrics.cpu_percent >= self.thresholds['cpu_critical']:
            alerts.append(self._create_alert(
                'CPU',
                'CRITICAL',
                f"CPU usage critical: {metrics.cpu_percent:.1f}%",
                metrics.cpu_percent,
                self.thresholds['cpu_critical']
            ))
        elif metrics.cpu_percent >= self.thresholds['cpu_warning']:
            alerts.append(self._create_alert(
                'CPU',
                'WARNING',
                f"CPU usage elevated: {metrics.cpu_percent:.1f}%",
                metrics.cpu_percent,
                self.thresholds['cpu_warning']
            ))

        # Check Memory
        if metrics.memory_percent >= self.thresholds['memory_critical']:
            alerts.append(self._create_alert(
                'MEMORY',
                'CRITICAL',
                f"Memory usage critical: {metrics.memory_percent:.1f}%",
                metrics.memory_percent,
                self.thresholds['memory_critical']
            ))
        elif metrics.memory_percent >= self.thresholds['memory_warning']:
            alerts.append(self._create_alert(
                'MEMORY',
                'WARNING',
                f"Memory usage elevated: {metrics.memory_percent:.1f}%",
                metrics.memory_percent,
                self.thresholds['memory_warning']
            ))

        # Check Disk
        if metrics.disk_percent >= self.thresholds['disk_critical']:
            alerts.append(self._create_alert(
                'DISK',
                'CRITICAL',
                f"Disk usage critical: {metrics.disk_percent:.1f}%",
                metrics.disk_percent,
                self.thresholds['disk_critical']
            ))
        elif metrics.disk_percent >= self.thresholds['disk_warning']:
            alerts.append(self._create_alert(
                'DISK',
                'WARNING',
                f"Disk usage elevated: {metrics.disk_percent:.1f}%",
                metrics.disk_percent,
                self.thresholds['disk_warning']
            ))

        return alerts

    def _create_alert(self, alert_type: str, severity: str,
                     message: str, metric_value: float,
                     threshold: float) -> Alert:
        """Create an Alert object and store it."""
        alert = Alert(
            timestamp=datetime.now().isoformat(),
            alert_type=alert_type,
            severity=severity,
            message=message,
            metric_value=metric_value,
            threshold=threshold
        )

        # Store in database
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO alerts (timestamp, alert_type, severity, message,
                                   metric_value, threshold)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (alert.timestamp, alert.alert_type, alert.severity,
                  alert.message, alert.metric_value, alert.threshold))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error storing alert: {e}")

        self.recent_alerts.append(alert)
        if len(self.recent_alerts) > self.max_recent_alerts:
            self.recent_alerts.pop(0)

        logger.warning(f"[{severity}] {message}")
        return alert

    def get_optimization_recommendations(self,
                                        metrics: ResourceMetrics) -> List[Dict]:
        """
        Generate resource optimization recommendations based on current metrics.

        Args:
            metrics: Current ResourceMetrics

        Returns:
            List[Dict]: List of recommendations with estimated savings
        """
        recommendations = []

        # CPU optimization recommendations
        if metrics.cpu_percent > 75:
            recommendations.append({
                'type': 'CPU_OPTIMIZATION',
                'priority': 'HIGH' if metrics.cpu_percent > 90 else 'MEDIUM',
                'recommendation': 'Reduce CPU-intensive processes or enable CPU throttling',
                'estimated_savings': min(metrics.cpu_percent - 50, 25),
                'action': 'identify_high_cpu_processes'
            })

        # Memory optimization recommendations
        if metrics.memory_percent > 80:
            freed_memory = metrics.memory_available_mb
            recommendations.append({
                'type': 'MEMORY_OPTIMIZATION',
                'priority': 'HIGH' if metrics.memory_percent > 95 else 'MEDIUM',
                'recommendation': f'Clear cache or close unused applications (Available: {freed_memory:.0f}MB)',
                'estimated_savings': freed_memory,
                'action': 'memory_optimization'
            })

        # Disk optimization recommendations
        if metrics.disk_percent > 85:
            recommendations.append({
                'type': 'DISK_OPTIMIZATION',
                'priority': 'HIGH' if metrics.disk_percent > 95 else 'MEDIUM',
                'recommendation': 'Remove temporary files, old logs, or archive unused data',
                'estimated_savings': (100 - metrics.disk_percent) * 10,
                'action': 'disk_cleanup'
            })

        # Proactive recommendations
        if metrics.process_count > 300:
            recommendations.append({
                'type': 'PROCESS_MANAGEMENT',
                'priority': 'MEDIUM',
                'recommendation': f'Consider closing unnecessary processes ({metrics.process_count} active)',
                'estimated_savings': 5,
                'action': 'process_review'
            })

        # Store recommendations in database
        for rec in recommendations:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO optimizations (timestamp, recommendation, estimated_savings)
                    VALUES (?, ?, ?)
                ''', (datetime.now().isoformat(), json.dumps(rec),
                      rec['estimated_savings']))
                conn.commit()
                conn.close()
            except Exception as e:
                logger.error(f"Error storing recommendation: {e}")

        return recommendations

    def is_resource_constrained(self, metrics: ResourceMetrics) -> bool:
        """
        Determine if system resources are constrained.

        Args:
            metrics: Current ResourceMetrics

        Returns:
            bool: True if resources are constrained
        """
        return (metrics.cpu_percent > 80 or
                metrics.memory_percent > 85 or
                metrics.disk_percent > 90)

    def get_constraint_aware_plan(self,
                                  metrics: ResourceMetrics) -> Dict:
        """
        Generate constraint-aware resource planning recommendations.

        Args:
            metrics: Current ResourceMetrics

        Returns:
            Dict: Resource allocation plan
        """
        plan = {
            'timestamp': datetime.now().isoformat(),
            'resource_constrained': self.is_resource_constrained(metrics),
            'constraints': [],
            'suggested_actions': [],
            'estimated_improvement': 0
        }

        # Identify constraints
        if metrics.cpu_percent > 75:
            plan['constraints'].append({
                'resource': 'CPU',
                'current': metrics.cpu_percent,
                'recommended_max': 70,
                'severity': 'HIGH' if metrics.cpu_percent > 90 else 'MEDIUM'
            })

        if metrics.memory_percent > 80:
            plan['constraints'].append({
                'resource': 'Memory',
                'current': metrics.memory_percent,
                'recommended_max': 75,
                'severity': 'HIGH' if metrics.memory_percent > 95 else 'MEDIUM'
            })

        if metrics.disk_percent > 85:
            plan['constraints'].append({
                'resource': 'Disk',
                'current': metrics.disk_percent,
                'recommended_max': 80,
                'severity': 'HIGH' if metrics.disk_percent > 95 else 'MEDIUM'
            })

        # Generate suggested actions
        if plan['resource_constrained']:
            plan['suggested_actions'] = [
                'Prioritize critical processes only',
                'Defer non-critical background tasks',
                'Enable resource-saving mode',
                'Monitor for resource-intensive operations'
            ]
            plan['estimated_improvement'] = len(plan['constraints']) * 10
        else:
            plan['suggested_actions'] = [
                'System operating normally',
                'Continue standard operations',
                'Schedule routine maintenance'
            ]

        return plan

    def get_metrics_history(self, hours: int = 24) -> List[Dict]:
        """
        Retrieve historical metrics.

        Args:
            hours: Number of hours to retrieve

        Returns:
            List[Dict]: Historical metrics
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cutoff_time = datetime.now() - timedelta(hours=hours)
            cursor.execute('''
                SELECT * FROM metrics
                WHERE created_at > ?
                ORDER BY created_at DESC
                LIMIT 1000
            ''', (cutoff_time.isoformat(),))

            rows = cursor.fetchall()
            conn.close()

            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error retrieving metrics history: {e}")
            return []

    def get_alerts_history(self, hours: int = 24) -> List[Dict]:
        """
        Retrieve alert history.

        Args:
            hours: Number of hours to retrieve

        Returns:
            List[Dict]: Historical alerts
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cutoff_time = datetime.now() - timedelta(hours=hours)
            cursor.execute('''
                SELECT * FROM alerts
                WHERE created_at > ?
                ORDER BY created_at DESC
                LIMIT 500
            ''', (cutoff_time.isoformat(),))

            rows = cursor.fetchall()
            conn.close()

            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error retrieving alerts: {e}")
            return []

    def cleanup_old_data(self) -> None:
        """Remove data older than retention period."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cutoff_date = datetime.now() - timedelta(days=self.retention_days)
            cutoff_iso = cutoff_date.isoformat()

            cursor.execute('DELETE FROM metrics WHERE created_at < ?',
                          (cutoff_iso,))
            cursor.execute('DELETE FROM alerts WHERE created_at < ?',
                          (cutoff_iso,))
            cursor.execute('DELETE FROM optimizations WHERE created_at < ?',
                          (cutoff_iso,))

            conn.commit()
            deleted = cursor.total_changes
            conn.close()

            logger.info(f"Cleaned up {deleted} old records")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

    def get_summary_report(self, metrics: ResourceMetrics) -> Dict:
        """
        Generate comprehensive system summary report.

        Args:
            metrics: Current ResourceMetrics

        Returns:
            Dict: Summary report
        """
        return {
            'timestamp': metrics.timestamp,
            'system_health_score': metrics.system_health_score,
            'resources': {
                'cpu': {
                    'usage_percent': metrics.cpu_percent,
                    'status': self._get_status(metrics.cpu_percent, 75, 90)
                },
                'memory': {
                    'usage_percent': metrics.memory_percent,
                    'used_mb': metrics.memory_used_mb,
                    'available_mb': metrics.memory_available_mb,
                    'status': self._get_status(metrics.memory_percent, 80, 95)
                },
                'disk': {
                    'usage_percent': metrics.disk_percent,
                    'used_gb': metrics.disk_used_gb,
                    'total_gb': metrics.disk_total_gb,
                    'status': self._get_status(metrics.disk_percent, 85, 95)
                },
                'processes': metrics.process_count
            },
            'constrained': self.is_resource_constrained(metrics)
        }

    def _get_status(self, current: float, warning: float,
                    critical: float) -> str:
        """Determine resource status."""
        if current >= critical:
            return 'CRITICAL'
        elif current >= warning:
            return 'WARNING'
        else:
            return 'HEALTHY'


def main():
    """Main function for testing and demonstration."""
    print("\n" + "="*70)
    print("SYSTEM RESOURCE MONITOR - PRODUCTION-READY DEMONSTRATION")
    print("="*70 + "\n")

    # Initialize monitor
    monitor = ResourceMonitor(db_path="resource_monitor.db")

    # Collect metrics
    print("1. COLLECTING CURRENT SYSTEM METRICS...")
    metrics = monitor.get_system_metrics()
    monitor.store_metrics(metrics)
    print(f"   CPU: {metrics.cpu_percent:.1f}%")
    print(f"   Memory: {metrics.memory_percent:.1f}% ({metrics.memory_used_mb:.0f}MB used)")
    print(f"   Disk: {metrics.disk_percent:.1f}%")
    print(f"   Processes: {metrics.process_count}")
    print(f"   Health Score: {metrics.system_health_score}/100")

    # Check thresholds
    print("\n2. CHECKING RESOURCE THRESHOLDS...")
    alerts = monitor.check_thresholds(metrics)
    if alerts:
        print(f"   {len(alerts)} alert(s) triggered:")
        for alert in alerts:
            print(f"   - [{alert.severity}] {alert.message}")
    else:
        print("   No alerts - all resources within normal limits")

    # Get optimization recommendations
    print("\n3. GENERATING OPTIMIZATION RECOMMENDATIONS...")
    recommendations = monitor.get_optimization_recommendations(metrics)
    if recommendations:
        for i, rec in enumerate(recommendations, 1):
            print(f"   {i}. [{rec['priority']}] {rec['recommendation']}")
            print(f"      Estimated savings: {rec['estimated_savings']:.1f}")
    else:
        print("   System operating optimally - no recommendations at this time")

    # Get constraint-aware plan
    print("\n4. CONSTRAINT-AWARE RESOURCE PLAN...")
    plan = monitor.get_constraint_aware_plan(metrics)
    print(f"   Resource Constrained: {plan['resource_constrained']}")
    if plan['constraints']:
        print("   Active Constraints:")
        for constraint in plan['constraints']:
            print(f"   - {constraint['resource']}: {constraint['current']:.1f}% "
                  f"(recommended max: {constraint['recommended_max']:.1f}%)")
    print("   Suggested Actions:")
    for action in plan['suggested_actions']:
        print(f"   - {action}")

    # Summary report
    print("\n5. COMPREHENSIVE SYSTEM REPORT...")
    report = monitor.get_summary_report(metrics)
    print(f"   Health Score: {report['system_health_score']}/100")
    print(f"   CPU Status: {report['resources']['cpu']['status']}")
    print(f"   Memory Status: {report['resources']['memory']['status']}")
    print(f"   Disk Status: {report['resources']['disk']['status']}")

    # Cleanup old data
    print("\n6. DATABASE MAINTENANCE...")
    monitor.cleanup_old_data()
    print("   Old data cleanup completed")

    # Retrieve history
    print("\n7. HISTORICAL DATA (Last 24 hours)...")
    history = monitor.get_metrics_history(hours=24)
    print(f"   Metrics records: {len(history)}")

    alerts_hist = monitor.get_alerts_history(hours=24)
    print(f"   Alert records: {len(alerts_hist)}")

    print("\n" + "="*70)
    print("Resource monitor demonstration complete!")
    print(f"Database saved to: resource_monitor.db")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
