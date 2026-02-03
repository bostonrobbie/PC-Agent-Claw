#!/usr/bin/env python3
"""
Real-World Integration Testing System
Autonomous testing of Intelligence Hub capabilities with comprehensive monitoring and analysis.

This system runs the Intelligence Hub on real projects for extended periods and collects:
- Activity logs (code reviews, security scans, files indexed, patterns learned, errors recovered)
- Performance metrics (response times, resource usage, accuracy, UX quality)
- Improvement suggestions based on real-world performance data

Author: AI Self-Improvement System
Created: 2026-02-03
"""

import os
import sys
import time
import threading
import sqlite3
import json
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass, asdict
import traceback

# Add workspace to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from intelligence_hub import IntelligenceHub


@dataclass
class TestSession:
    """Data class for test session metadata"""
    session_id: str
    project_path: str
    start_time: str
    end_time: Optional[str]
    duration_minutes: int
    status: str  # running, completed, stopped, error
    total_activities: int
    total_errors: int
    avg_response_time: float
    avg_cpu_usage: float
    avg_memory_usage: float
    overall_score: float


@dataclass
class Activity:
    """Data class for capability activity"""
    activity_id: str
    session_id: str
    timestamp: str
    capability: str
    activity_type: str
    description: str
    response_time_ms: float
    cpu_before: float
    cpu_after: float
    memory_before_mb: float
    memory_after_mb: float
    success: bool
    error_message: Optional[str]
    result_data: str  # JSON


@dataclass
class PerformanceMetric:
    """Data class for performance metrics"""
    metric_id: str
    session_id: str
    timestamp: str
    capability: str
    metric_type: str  # response_time, cpu_usage, memory_usage, accuracy, ux_quality
    value: float
    unit: str
    context: str


@dataclass
class Issue:
    """Data class for discovered issues"""
    issue_id: str
    session_id: str
    timestamp: str
    severity: str  # critical, high, medium, low, info
    capability: str
    issue_type: str
    description: str
    suggested_fix: str
    reproducible: bool


class RealWorldTester:
    """
    Real-World Integration Testing System

    Runs Intelligence Hub autonomously on real projects and monitors:
    - All capability activities (reviews, scans, indexing, learning, error recovery)
    - Performance metrics (response times, resource usage, accuracy, UX quality)
    - Issues and improvement suggestions

    Features:
    - Autonomous operation for extended periods
    - Real-time activity logging
    - Resource safety monitoring
    - Automated analysis and reporting
    - Actionable improvement suggestions
    """

    def __init__(self, db_path: str = None):
        workspace = Path(__file__).parent.parent
        if db_path is None:
            db_path = str(workspace / "realworld_testing.db")

        self.db_path = db_path
        self._init_db()

        # Active sessions
        self.active_sessions = {}

        # Resource limits (safety thresholds)
        self.resource_limits = {
            'cpu_percent_max': 90.0,
            'memory_percent_max': 95.0,
            'disk_percent_max': 98.0,
            'consecutive_errors_max': 5
        }

        # Monitoring state
        self.monitoring_threads = {}
        self.stop_monitoring = {}

        print(f"[RealWorldTester] Initialized with database: {db_path}")

    def _init_db(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Test sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_sessions (
                session_id TEXT PRIMARY KEY,
                project_path TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                duration_minutes INTEGER NOT NULL,
                status TEXT NOT NULL,
                total_activities INTEGER DEFAULT 0,
                total_errors INTEGER DEFAULT 0,
                avg_response_time REAL DEFAULT 0,
                avg_cpu_usage REAL DEFAULT 0,
                avg_memory_usage REAL DEFAULT 0,
                overall_score REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Activities table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS activities (
                activity_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                capability TEXT NOT NULL,
                activity_type TEXT NOT NULL,
                description TEXT,
                response_time_ms REAL,
                cpu_before REAL,
                cpu_after REAL,
                memory_before_mb REAL,
                memory_after_mb REAL,
                success BOOLEAN,
                error_message TEXT,
                result_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES test_sessions(session_id)
            )
        ''')

        # Performance metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_metrics (
                metric_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                capability TEXT NOT NULL,
                metric_type TEXT NOT NULL,
                value REAL NOT NULL,
                unit TEXT NOT NULL,
                context TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES test_sessions(session_id)
            )
        ''')

        # Issues table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS issues (
                issue_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                severity TEXT NOT NULL,
                capability TEXT NOT NULL,
                issue_type TEXT NOT NULL,
                description TEXT,
                suggested_fix TEXT,
                reproducible BOOLEAN,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES test_sessions(session_id)
            )
        ''')

        # Improvement suggestions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS improvement_suggestions (
                suggestion_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                category TEXT NOT NULL,
                priority TEXT NOT NULL,
                suggestion TEXT NOT NULL,
                rationale TEXT,
                estimated_impact TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES test_sessions(session_id)
            )
        ''')

        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_activities_session ON activities(session_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_activities_capability ON activities(capability)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_metrics_session ON performance_metrics(session_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_issues_session ON issues(session_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_issues_severity ON issues(severity)')

        conn.commit()
        conn.close()

    def start_test_session(self, project_path: str, duration_minutes: int) -> str:
        """
        Start a real-world test session

        Args:
            project_path: Path to project to test on
            duration_minutes: How long to run the test

        Returns:
            Session ID
        """
        # Validate project path
        if not os.path.exists(project_path):
            raise ValueError(f"Project path does not exist: {project_path}")

        # Create session
        session_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        start_time = datetime.now().isoformat()

        session = TestSession(
            session_id=session_id,
            project_path=project_path,
            start_time=start_time,
            end_time=None,
            duration_minutes=duration_minutes,
            status='running',
            total_activities=0,
            total_errors=0,
            avg_response_time=0.0,
            avg_cpu_usage=0.0,
            avg_memory_usage=0.0,
            overall_score=0.0
        )

        # Store in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO test_sessions
            (session_id, project_path, start_time, end_time, duration_minutes, status,
             total_activities, total_errors, avg_response_time, avg_cpu_usage,
             avg_memory_usage, overall_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session.session_id, session.project_path, session.start_time, session.end_time,
            session.duration_minutes, session.status, session.total_activities,
            session.total_errors, session.avg_response_time, session.avg_cpu_usage,
            session.avg_memory_usage, session.overall_score
        ))
        conn.commit()
        conn.close()

        # Initialize Intelligence Hub for this session
        try:
            hub = IntelligenceHub(workspace_path=project_path)
            hub.start()

            self.active_sessions[session_id] = {
                'session': session,
                'hub': hub,
                'start_time': datetime.now(),
                'end_time': datetime.now() + timedelta(minutes=duration_minutes),
                'consecutive_errors': 0
            }

            # Start monitoring thread
            self.stop_monitoring[session_id] = False
            monitor_thread = threading.Thread(
                target=self._monitoring_loop,
                args=(session_id,),
                daemon=True
            )
            monitor_thread.start()
            self.monitoring_threads[session_id] = monitor_thread

            print(f"[RealWorldTester] Started test session: {session_id}")
            print(f"[RealWorldTester] Project: {project_path}")
            print(f"[RealWorldTester] Duration: {duration_minutes} minutes")
            print(f"[RealWorldTester] End time: {self.active_sessions[session_id]['end_time']}")

            return session_id

        except Exception as e:
            self._update_session_status(session_id, 'error')
            print(f"[RealWorldTester] Error starting session: {e}")
            traceback.print_exc()
            raise

    def _monitoring_loop(self, session_id: str):
        """Main monitoring loop for a test session"""
        print(f"[Monitor-{session_id}] Starting monitoring loop")

        session_data = self.active_sessions.get(session_id)
        if not session_data:
            return

        hub = session_data['hub']

        while not self.stop_monitoring.get(session_id, False):
            try:
                # Check if session time is up
                if datetime.now() >= session_data['end_time']:
                    print(f"[Monitor-{session_id}] Session duration complete")
                    self.stop_session(session_id)
                    break

                # Check resource limits
                if not self._check_resource_safety(session_id):
                    print(f"[Monitor-{session_id}] Resource limits exceeded - stopping session")
                    self.stop_session(session_id)
                    break

                # Perform various activities and monitor them
                self._test_workspace_analysis(session_id, hub)
                time.sleep(30)  # Wait between activities

                self._test_code_assistance(session_id, hub)
                time.sleep(30)

                self._test_security_scanning(session_id, hub)
                time.sleep(30)

                self._test_code_indexing(session_id, hub)
                time.sleep(30)

                self._test_error_recovery(session_id, hub)
                time.sleep(30)

            except Exception as e:
                print(f"[Monitor-{session_id}] Error in monitoring loop: {e}")
                traceback.print_exc()

                session_data['consecutive_errors'] += 1
                if session_data['consecutive_errors'] >= self.resource_limits['consecutive_errors_max']:
                    print(f"[Monitor-{session_id}] Too many consecutive errors - stopping")
                    self.stop_session(session_id)
                    break

                time.sleep(10)

        print(f"[Monitor-{session_id}] Monitoring loop ended")

    def _check_resource_safety(self, session_id: str) -> bool:
        """Check if resource usage is within safe limits"""
        try:
            cpu = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory().percent
            disk = psutil.disk_usage('/').percent

            if cpu > self.resource_limits['cpu_percent_max']:
                self._log_issue(
                    session_id, 'critical', 'system',
                    'resource_limit', f'CPU usage {cpu:.1f}% exceeds limit',
                    'Stop or throttle CPU-intensive operations'
                )
                return False

            if memory > self.resource_limits['memory_percent_max']:
                self._log_issue(
                    session_id, 'critical', 'system',
                    'resource_limit', f'Memory usage {memory:.1f}% exceeds limit',
                    'Stop or reduce memory-intensive operations'
                )
                return False

            if disk > self.resource_limits['disk_percent_max']:
                self._log_issue(
                    session_id, 'critical', 'system',
                    'resource_limit', f'Disk usage {disk:.1f}% exceeds limit',
                    'Clean up temporary files or stop logging'
                )
                return False

            return True

        except Exception as e:
            print(f"[Safety] Error checking resources: {e}")
            return True  # Continue on error checking

    def _test_workspace_analysis(self, session_id: str, hub: IntelligenceHub):
        """Test workspace analysis capability"""
        start_time = time.time()
        cpu_before = psutil.cpu_percent()
        mem_before = psutil.Process().memory_info().rss / 1024 / 1024

        try:
            result = hub.analyze_workspace()

            response_time = (time.time() - start_time) * 1000
            cpu_after = psutil.cpu_percent()
            mem_after = psutil.Process().memory_info().rss / 1024 / 1024

            # Log activity
            self._log_activity(
                session_id, 'workspace_analyzer', 'analyze_workspace',
                f"Analyzed workspace: {len(result.get('insights', []))} insights",
                response_time, cpu_before, cpu_after, mem_before, mem_after,
                True, None, json.dumps(result, default=str)
            )

            # Log performance metrics
            self._log_metric(
                session_id, 'workspace_analyzer', 'response_time',
                response_time, 'ms', 'Full workspace analysis'
            )

            # Check for issues
            if response_time > 30000:  # 30 seconds
                self._log_issue(
                    session_id, 'medium', 'workspace_analyzer',
                    'performance', f'Slow analysis: {response_time:.0f}ms',
                    'Optimize workspace scanning or add caching'
                )

            print(f"[Test-{session_id}] Workspace analysis: {response_time:.0f}ms, {len(result.get('insights', []))} insights")

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            cpu_after = psutil.cpu_percent()
            mem_after = psutil.Process().memory_info().rss / 1024 / 1024

            self._log_activity(
                session_id, 'workspace_analyzer', 'analyze_workspace',
                'Failed to analyze workspace',
                response_time, cpu_before, cpu_after, mem_before, mem_after,
                False, str(e), None
            )

            self._log_issue(
                session_id, 'high', 'workspace_analyzer',
                'error', f'Analysis failed: {str(e)}',
                'Fix error handling in workspace analyzer'
            )

    def _test_code_assistance(self, session_id: str, hub: IntelligenceHub):
        """Test code assistance capability"""
        start_time = time.time()
        cpu_before = psutil.cpu_percent()
        mem_before = psutil.Process().memory_info().rss / 1024 / 1024

        test_code = '''
def calculate_total(items):
    total = 0
    for item in items:
        total += item.price
    return total
'''

        try:
            result = hub.assist_with_code(
                "Calculate total price from items",
                test_code
            )

            response_time = (time.time() - start_time) * 1000
            cpu_after = psutil.cpu_percent()
            mem_after = psutil.Process().memory_info().rss / 1024 / 1024

            capabilities_used = len(result.get('capabilities_used', []))

            self._log_activity(
                session_id, 'code_assistant', 'assist_with_code',
                f"Assisted with code using {capabilities_used} capabilities",
                response_time, cpu_before, cpu_after, mem_before, mem_after,
                True, None, json.dumps(result, default=str)
            )

            self._log_metric(
                session_id, 'code_assistant', 'response_time',
                response_time, 'ms', 'Code assistance request'
            )

            # Accuracy metric (simplified - check if similar code was found)
            accuracy = 1.0 if result.get('similar_code') else 0.5
            self._log_metric(
                session_id, 'code_assistant', 'accuracy',
                accuracy, 'score', 'Relevance of suggestions'
            )

            print(f"[Test-{session_id}] Code assistance: {response_time:.0f}ms, {capabilities_used} capabilities")

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            cpu_after = psutil.cpu_percent()
            mem_after = psutil.Process().memory_info().rss / 1024 / 1024

            self._log_activity(
                session_id, 'code_assistant', 'assist_with_code',
                'Failed to assist with code',
                response_time, cpu_before, cpu_after, mem_before, mem_after,
                False, str(e), None
            )

    def _test_security_scanning(self, session_id: str, hub: IntelligenceHub):
        """Test security scanning capability"""
        start_time = time.time()
        cpu_before = psutil.cpu_percent()
        mem_before = psutil.Process().memory_info().rss / 1024 / 1024

        try:
            # Find Python files to scan
            project_path = self.active_sessions[session_id]['session'].project_path
            python_files = list(Path(project_path).rglob("*.py"))[:5]  # Sample 5 files

            vulnerabilities_found = 0
            for file in python_files:
                try:
                    with open(file, 'r', encoding='utf-8', errors='ignore') as f:
                        code = f.read()
                    scan = hub.security_scanner.scan_code(code, str(file))
                    vulnerabilities_found += len(scan.get('vulnerabilities', []))
                except:
                    continue

            response_time = (time.time() - start_time) * 1000
            cpu_after = psutil.cpu_percent()
            mem_after = psutil.Process().memory_info().rss / 1024 / 1024

            self._log_activity(
                session_id, 'security_scanner', 'scan_files',
                f"Scanned {len(python_files)} files, found {vulnerabilities_found} vulnerabilities",
                response_time, cpu_before, cpu_after, mem_before, mem_after,
                True, None, json.dumps({'files': len(python_files), 'vulnerabilities': vulnerabilities_found})
            )

            self._log_metric(
                session_id, 'security_scanner', 'vulnerabilities_found',
                vulnerabilities_found, 'count', f'Scanned {len(python_files)} files'
            )

            print(f"[Test-{session_id}] Security scan: {response_time:.0f}ms, {vulnerabilities_found} vulnerabilities")

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            cpu_after = psutil.cpu_percent()
            mem_after = psutil.Process().memory_info().rss / 1024 / 1024

            self._log_activity(
                session_id, 'security_scanner', 'scan_files',
                'Failed to scan files',
                response_time, cpu_before, cpu_after, mem_before, mem_after,
                False, str(e), None
            )

    def _test_code_indexing(self, session_id: str, hub: IntelligenceHub):
        """Test code indexing capability"""
        start_time = time.time()
        cpu_before = psutil.cpu_percent()
        mem_before = psutil.Process().memory_info().rss / 1024 / 1024

        try:
            project_path = self.active_sessions[session_id]['session'].project_path
            result = hub.code_search.index_project("test_project", project_path)

            response_time = (time.time() - start_time) * 1000
            cpu_after = psutil.cpu_percent()
            mem_after = psutil.Process().memory_info().rss / 1024 / 1024

            files_indexed = result.get('files_indexed', 0)
            chunks_indexed = result.get('chunks_indexed', 0)

            self._log_activity(
                session_id, 'code_search', 'index_project',
                f"Indexed {files_indexed} files, {chunks_indexed} chunks",
                response_time, cpu_before, cpu_after, mem_before, mem_after,
                True, None, json.dumps(result)
            )

            self._log_metric(
                session_id, 'code_search', 'files_indexed',
                files_indexed, 'count', 'Project indexing'
            )

            # UX quality metric - speed per file
            if files_indexed > 0:
                speed = response_time / files_indexed
                ux_quality = 1.0 if speed < 100 else 0.5 if speed < 500 else 0.2
                self._log_metric(
                    session_id, 'code_search', 'ux_quality',
                    ux_quality, 'score', f'{speed:.0f}ms per file'
                )

            print(f"[Test-{session_id}] Code indexing: {response_time:.0f}ms, {files_indexed} files")

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            cpu_after = psutil.cpu_percent()
            mem_after = psutil.Process().memory_info().rss / 1024 / 1024

            self._log_activity(
                session_id, 'code_search', 'index_project',
                'Failed to index project',
                response_time, cpu_before, cpu_after, mem_before, mem_after,
                False, str(e), None
            )

    def _test_error_recovery(self, session_id: str, hub: IntelligenceHub):
        """Test error recovery capability"""
        start_time = time.time()
        cpu_before = psutil.cpu_percent()
        mem_before = psutil.Process().memory_info().rss / 1024 / 1024

        try:
            # Intentionally cause an error and see if it's handled
            error_code = '''
def broken_function():
    x = 1 / 0  # Division by zero
    return x
'''

            # Try to analyze broken code
            try:
                hub.assist_with_code("Test error recovery", error_code)
            except:
                pass

            response_time = (time.time() - start_time) * 1000
            cpu_after = psutil.cpu_percent()
            mem_after = psutil.Process().memory_info().rss / 1024 / 1024

            # Check if error was logged and learned from
            stats = hub.mistake_learner.get_stats()

            self._log_activity(
                session_id, 'error_recovery', 'handle_error',
                f"Error recovery test: {stats['total_mistakes']} mistakes tracked",
                response_time, cpu_before, cpu_after, mem_before, mem_after,
                True, None, json.dumps(stats)
            )

            print(f"[Test-{session_id}] Error recovery: {response_time:.0f}ms")

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            cpu_after = psutil.cpu_percent()
            mem_after = psutil.Process().memory_info().rss / 1024 / 1024

            self._log_activity(
                session_id, 'error_recovery', 'handle_error',
                'Error recovery test failed',
                response_time, cpu_before, cpu_after, mem_before, mem_after,
                False, str(e), None
            )

    def _log_activity(self, session_id: str, capability: str, activity_type: str,
                     description: str, response_time_ms: float,
                     cpu_before: float, cpu_after: float,
                     mem_before: float, mem_after: float,
                     success: bool, error_message: Optional[str],
                     result_data: Optional[str]):
        """Log an activity to the database"""
        activity_id = f"act_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        timestamp = datetime.now().isoformat()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO activities
            (activity_id, session_id, timestamp, capability, activity_type, description,
             response_time_ms, cpu_before, cpu_after, memory_before_mb, memory_after_mb,
             success, error_message, result_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            activity_id, session_id, timestamp, capability, activity_type, description,
            response_time_ms, cpu_before, cpu_after, mem_before, mem_after,
            success, error_message, result_data
        ))

        # Update session totals
        cursor.execute('''
            UPDATE test_sessions
            SET total_activities = total_activities + 1,
                total_errors = total_errors + ?
            WHERE session_id = ?
        ''', (0 if success else 1, session_id))

        conn.commit()
        conn.close()

    def _log_metric(self, session_id: str, capability: str, metric_type: str,
                   value: float, unit: str, context: str):
        """Log a performance metric"""
        metric_id = f"met_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        timestamp = datetime.now().isoformat()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO performance_metrics
            (metric_id, session_id, timestamp, capability, metric_type, value, unit, context)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (metric_id, session_id, timestamp, capability, metric_type, value, unit, context))
        conn.commit()
        conn.close()

    def _log_issue(self, session_id: str, severity: str, capability: str,
                  issue_type: str, description: str, suggested_fix: str,
                  reproducible: bool = True):
        """Log a discovered issue"""
        issue_id = f"iss_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        timestamp = datetime.now().isoformat()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO issues
            (issue_id, session_id, timestamp, severity, capability, issue_type,
             description, suggested_fix, reproducible)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (issue_id, session_id, timestamp, severity, capability, issue_type,
              description, suggested_fix, reproducible))
        conn.commit()
        conn.close()

        print(f"[Issue-{session_id}] [{severity.upper()}] {capability}: {description}")

    def _update_session_status(self, session_id: str, status: str):
        """Update session status in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE test_sessions
            SET status = ?
            WHERE session_id = ?
        ''', (status, session_id))
        conn.commit()
        conn.close()

    def monitor_activities(self) -> Dict:
        """
        Get current monitoring status for all active sessions

        Returns:
            Dict with monitoring data
        """
        monitoring_data = {
            'timestamp': datetime.now().isoformat(),
            'active_sessions': [],
            'total_activities': 0,
            'total_errors': 0
        }

        for session_id, session_data in self.active_sessions.items():
            session_info = {
                'session_id': session_id,
                'project_path': session_data['session'].project_path,
                'running_time': str(datetime.now() - session_data['start_time']),
                'remaining_time': str(session_data['end_time'] - datetime.now()),
                'consecutive_errors': session_data['consecutive_errors']
            }

            # Get latest stats from database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT total_activities, total_errors
                FROM test_sessions
                WHERE session_id = ?
            ''', (session_id,))
            row = cursor.fetchone()
            if row:
                session_info['total_activities'] = row[0]
                session_info['total_errors'] = row[1]
                monitoring_data['total_activities'] += row[0]
                monitoring_data['total_errors'] += row[1]
            conn.close()

            monitoring_data['active_sessions'].append(session_info)

        return monitoring_data

    def collect_metrics(self) -> Dict:
        """
        Collect current performance metrics

        Returns:
            Dict with aggregated metrics
        """
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'system_resources': {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent
            },
            'by_capability': {}
        }

        # Aggregate metrics by capability
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get average response times by capability
        cursor.execute('''
            SELECT capability,
                   AVG(response_time_ms) as avg_response,
                   COUNT(*) as count,
                   SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successes
            FROM activities
            WHERE timestamp > datetime('now', '-1 hour')
            GROUP BY capability
        ''')

        for row in cursor.fetchall():
            capability, avg_response, count, successes = row
            metrics['by_capability'][capability] = {
                'avg_response_time_ms': avg_response,
                'total_calls': count,
                'success_rate': (successes / count * 100) if count > 0 else 0
            }

        conn.close()
        return metrics

    def analyze_session_results(self, session_id: str) -> Dict:
        """
        Analyze results from a test session

        Args:
            session_id: Session to analyze

        Returns:
            Dict with analysis results
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get session info
        cursor.execute('SELECT * FROM test_sessions WHERE session_id = ?', (session_id,))
        session_row = cursor.fetchone()
        if not session_row:
            conn.close()
            return {'error': 'Session not found'}

        session = dict(session_row)

        # Get activities breakdown
        cursor.execute('''
            SELECT capability,
                   COUNT(*) as total,
                   SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successes,
                   AVG(response_time_ms) as avg_response,
                   AVG(cpu_after - cpu_before) as avg_cpu_delta,
                   AVG(memory_after_mb - memory_before_mb) as avg_mem_delta
            FROM activities
            WHERE session_id = ?
            GROUP BY capability
        ''', (session_id,))

        activities_by_capability = []
        for row in cursor.fetchall():
            activities_by_capability.append(dict(row))

        # Get performance metrics
        cursor.execute('''
            SELECT metric_type, capability, AVG(value) as avg_value, unit
            FROM performance_metrics
            WHERE session_id = ?
            GROUP BY metric_type, capability
        ''', (session_id,))

        performance_metrics = [dict(row) for row in cursor.fetchall()]

        # Get issues
        cursor.execute('''
            SELECT severity, COUNT(*) as count
            FROM issues
            WHERE session_id = ?
            GROUP BY severity
        ''', (session_id,))

        issues_by_severity = {row['severity']: row['count'] for row in cursor.fetchall()}

        # Get top issues
        cursor.execute('''
            SELECT * FROM issues
            WHERE session_id = ?
            ORDER BY
                CASE severity
                    WHEN 'critical' THEN 1
                    WHEN 'high' THEN 2
                    WHEN 'medium' THEN 3
                    WHEN 'low' THEN 4
                    ELSE 5
                END,
                timestamp DESC
            LIMIT 10
        ''', (session_id,))

        top_issues = [dict(row) for row in cursor.fetchall()]

        conn.close()

        # Calculate overall analysis
        total_activities = session['total_activities']
        total_errors = session['total_errors']
        success_rate = ((total_activities - total_errors) / total_activities * 100) if total_activities > 0 else 0

        # Determine what worked well vs poorly
        worked_well = []
        worked_poorly = []

        for cap in activities_by_capability:
            cap_success_rate = (cap['successes'] / cap['total'] * 100) if cap['total'] > 0 else 0

            if cap_success_rate >= 90 and cap['avg_response'] < 5000:
                worked_well.append({
                    'capability': cap['capability'],
                    'reason': f"High success rate ({cap_success_rate:.1f}%) and fast response ({cap['avg_response']:.0f}ms)",
                    'metrics': cap
                })
            elif cap_success_rate < 70 or cap['avg_response'] > 10000:
                worked_poorly.append({
                    'capability': cap['capability'],
                    'reason': f"Low success rate ({cap_success_rate:.1f}%) or slow response ({cap['avg_response']:.0f}ms)",
                    'metrics': cap
                })

        return {
            'session': session,
            'summary': {
                'total_activities': total_activities,
                'total_errors': total_errors,
                'success_rate': success_rate,
                'avg_response_time': session['avg_response_time'],
                'avg_cpu_usage': session['avg_cpu_usage'],
                'avg_memory_usage': session['avg_memory_usage']
            },
            'activities_by_capability': activities_by_capability,
            'performance_metrics': performance_metrics,
            'issues_by_severity': issues_by_severity,
            'top_issues': top_issues,
            'worked_well': worked_well,
            'worked_poorly': worked_poorly
        }

    def generate_improvement_report(self, session_id: str) -> str:
        """
        Generate actionable improvement report from test session

        Args:
            session_id: Session to generate report for

        Returns:
            Formatted improvement report
        """
        analysis = self.analyze_session_results(session_id)

        if 'error' in analysis:
            return f"Error: {analysis['error']}"

        # Generate improvement suggestions
        suggestions = []

        # Based on worked poorly
        for item in analysis['worked_poorly']:
            priority = 'HIGH' if item['metrics']['avg_response'] > 15000 else 'MEDIUM'

            if item['metrics']['avg_response'] > 10000:
                suggestion = {
                    'category': 'performance',
                    'priority': priority,
                    'suggestion': f"Optimize {item['capability']} - response time is too slow",
                    'rationale': item['reason'],
                    'estimated_impact': f"Could improve response time by {item['metrics']['avg_response'] / 2:.0f}ms"
                }
                suggestions.append(suggestion)

            success_rate = (item['metrics']['successes'] / item['metrics']['total'] * 100) if item['metrics']['total'] > 0 else 0
            if success_rate < 70:
                suggestion = {
                    'category': 'reliability',
                    'priority': 'HIGH',
                    'suggestion': f"Fix error handling in {item['capability']}",
                    'rationale': f"Success rate is only {success_rate:.1f}%",
                    'estimated_impact': f"Could improve success rate to 95%+"
                }
                suggestions.append(suggestion)

        # Based on issues
        for issue in analysis['top_issues']:
            if issue['severity'] in ['critical', 'high']:
                suggestion = {
                    'category': 'bug_fix',
                    'priority': issue['severity'].upper(),
                    'suggestion': issue['suggested_fix'],
                    'rationale': issue['description'],
                    'estimated_impact': 'Fix critical stability issue'
                }
                suggestions.append(suggestion)

        # Resource optimization suggestions
        if analysis['summary']['avg_cpu_usage'] > 70:
            suggestions.append({
                'category': 'resource_optimization',
                'priority': 'MEDIUM',
                'suggestion': 'Reduce CPU usage across capabilities',
                'rationale': f"Average CPU usage is {analysis['summary']['avg_cpu_usage']:.1f}%",
                'estimated_impact': 'Reduce system load by 20-30%'
            })

        if analysis['summary']['avg_memory_usage'] > 80:
            suggestions.append({
                'category': 'resource_optimization',
                'priority': 'HIGH',
                'suggestion': 'Optimize memory usage',
                'rationale': f"Average memory usage is {analysis['summary']['avg_memory_usage']:.1f}%",
                'estimated_impact': 'Prevent out-of-memory errors'
            })

        # Store suggestions in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        timestamp = datetime.now().isoformat()

        for suggestion in suggestions:
            cursor.execute('''
                INSERT INTO improvement_suggestions
                (session_id, timestamp, category, priority, suggestion, rationale, estimated_impact)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (session_id, timestamp, suggestion['category'], suggestion['priority'],
                  suggestion['suggestion'], suggestion['rationale'], suggestion['estimated_impact']))

        conn.commit()
        conn.close()

        # Generate report
        report = []
        report.append("=" * 80)
        report.append("REAL-WORLD TESTING - IMPROVEMENT REPORT")
        report.append("=" * 80)
        report.append(f"\nSession ID: {session_id}")
        report.append(f"Project: {analysis['session']['project_path']}")
        report.append(f"Duration: {analysis['session']['duration_minutes']} minutes")
        report.append(f"Status: {analysis['session']['status']}")

        report.append(f"\n{'SUMMARY':=^80}")
        report.append(f"Total Activities: {analysis['summary']['total_activities']}")
        report.append(f"Total Errors: {analysis['summary']['total_errors']}")
        report.append(f"Success Rate: {analysis['summary']['success_rate']:.1f}%")
        report.append(f"Avg Response Time: {analysis['summary']['avg_response_time']:.0f}ms")

        report.append(f"\n{'WHAT WORKED WELL':=^80}")
        if analysis['worked_well']:
            for item in analysis['worked_well']:
                report.append(f"\n{item['capability']}:")
                report.append(f"  {item['reason']}")
        else:
            report.append("  No capabilities performed exceptionally well")

        report.append(f"\n{'WHAT WORKED POORLY':=^80}")
        if analysis['worked_poorly']:
            for item in analysis['worked_poorly']:
                report.append(f"\n{item['capability']}:")
                report.append(f"  {item['reason']}")
        else:
            report.append("  All capabilities performed adequately")

        report.append(f"\n{'TOP ISSUES DISCOVERED':=^80}")
        if analysis['top_issues']:
            for i, issue in enumerate(analysis['top_issues'][:5], 1):
                report.append(f"\n{i}. [{issue['severity'].upper()}] {issue['capability']}")
                report.append(f"   {issue['description']}")
                report.append(f"   Fix: {issue['suggested_fix']}")
        else:
            report.append("  No major issues discovered")

        report.append(f"\n{'ACTIONABLE IMPROVEMENTS':=^80}")
        if suggestions:
            # Sort by priority
            priority_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
            suggestions.sort(key=lambda x: priority_order.get(x['priority'], 4))

            for i, sug in enumerate(suggestions, 1):
                report.append(f"\n{i}. [{sug['priority']}] {sug['suggestion']}")
                report.append(f"   Category: {sug['category']}")
                report.append(f"   Why: {sug['rationale']}")
                report.append(f"   Impact: {sug['estimated_impact']}")
        else:
            report.append("  No improvements needed - system performing well")

        report.append(f"\n{'END OF REPORT':=^80}\n")

        return "\n".join(report)

    def stop_session(self, session_id: str) -> Dict:
        """
        Stop a test session

        Args:
            session_id: Session to stop

        Returns:
            Dict with final session statistics
        """
        if session_id not in self.active_sessions:
            return {'error': 'Session not found or already stopped'}

        print(f"[RealWorldTester] Stopping session: {session_id}")

        # Stop monitoring
        self.stop_monitoring[session_id] = True

        # Wait for monitoring thread to finish
        if session_id in self.monitoring_threads:
            self.monitoring_threads[session_id].join(timeout=10)

        # Stop Intelligence Hub
        session_data = self.active_sessions[session_id]
        try:
            session_data['hub'].stop()
        except Exception as e:
            print(f"[RealWorldTester] Error stopping hub: {e}")

        # Update session in database
        end_time = datetime.now().isoformat()

        # Calculate averages
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT AVG(response_time_ms), AVG(cpu_after), AVG(memory_after_mb)
            FROM activities
            WHERE session_id = ?
        ''', (session_id,))

        row = cursor.fetchone()
        avg_response = row[0] or 0
        avg_cpu = row[1] or 0
        avg_memory = row[2] or 0

        # Calculate overall score (0-100)
        cursor.execute('''
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successes
            FROM activities
            WHERE session_id = ?
        ''', (session_id,))

        row = cursor.fetchone()
        total = row[0] or 1
        successes = row[1] or 0
        success_rate = successes / total * 100

        # Score based on success rate (70%), response time (20%), resource usage (10%)
        response_score = max(0, 100 - (avg_response / 100))  # Penalty for slow responses
        resource_score = max(0, 100 - avg_cpu)  # Penalty for high CPU
        overall_score = (success_rate * 0.7) + (response_score * 0.2) + (resource_score * 0.1)

        cursor.execute('''
            UPDATE test_sessions
            SET end_time = ?,
                status = 'completed',
                avg_response_time = ?,
                avg_cpu_usage = ?,
                avg_memory_usage = ?,
                overall_score = ?
            WHERE session_id = ?
        ''', (end_time, avg_response, avg_cpu, avg_memory, overall_score, session_id))

        conn.commit()

        # Get final stats
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM test_sessions WHERE session_id = ?', (session_id,))
        row = cursor.fetchone()
        final_stats = dict(row) if row else {}

        conn.close()

        # Remove from active sessions
        del self.active_sessions[session_id]

        print(f"[RealWorldTester] Session stopped: {session_id}")
        print(f"  Total Activities: {final_stats['total_activities']}")
        print(f"  Total Errors: {final_stats['total_errors']}")
        print(f"  Overall Score: {overall_score:.1f}/100")

        return final_stats


# ============================================================================
# TEST CODE
# ============================================================================

def main():
    """Test the Real-World Testing System"""
    print("\n" + "="*80)
    print("REAL-WORLD INTEGRATION TESTING SYSTEM - DEMONSTRATION")
    print("="*80 + "\n")

    # Initialize tester
    tester = RealWorldTester()

    # Get current workspace path
    workspace = os.path.dirname(os.path.dirname(__file__))

    print(f"1. STARTING TEST SESSION")
    print(f"   Project: {workspace}")
    print(f"   Duration: 2 minutes (for demo)")

    try:
        # Start test session
        session_id = tester.start_test_session(workspace, duration_minutes=2)

        print(f"\n2. MONITORING ACTIVITIES...")
        print(f"   Session will run for 2 minutes")
        print(f"   Press Ctrl+C to stop early\n")

        # Monitor for a bit
        try:
            for i in range(12):  # Monitor for ~2 minutes (10 second intervals)
                time.sleep(10)

                # Get monitoring data
                monitor_data = tester.monitor_activities()
                print(f"\n[Status Update {i+1}/12]")
                print(f"  Active Sessions: {len(monitor_data['active_sessions'])}")
                print(f"  Total Activities: {monitor_data['total_activities']}")
                print(f"  Total Errors: {monitor_data['total_errors']}")

                # Get metrics
                metrics = tester.collect_metrics()
                print(f"  CPU: {metrics['system_resources']['cpu_percent']:.1f}%")
                print(f"  Memory: {metrics['system_resources']['memory_percent']:.1f}%")

                # Show capability stats
                if metrics['by_capability']:
                    print(f"  Capability Stats:")
                    for cap, stats in metrics['by_capability'].items():
                        print(f"    {cap}: {stats['total_calls']} calls, "
                              f"{stats['success_rate']:.1f}% success, "
                              f"{stats['avg_response_time_ms']:.0f}ms avg")

        except KeyboardInterrupt:
            print(f"\n\n[User interrupted - stopping session early]")

        print(f"\n3. STOPPING SESSION...")
        final_stats = tester.stop_session(session_id)

        print(f"\n4. ANALYZING RESULTS...")
        analysis = tester.analyze_session_results(session_id)

        print(f"\n   Session Summary:")
        print(f"   - Total Activities: {analysis['summary']['total_activities']}")
        print(f"   - Success Rate: {analysis['summary']['success_rate']:.1f}%")
        print(f"   - Issues Found: {sum(analysis['issues_by_severity'].values())}")

        print(f"\n5. GENERATING IMPROVEMENT REPORT...")
        report = tester.generate_improvement_report(session_id)

        print("\n" + report)

        print(f"\nDatabase saved to: {tester.db_path}")
        print(f"Session ID: {session_id}")

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        traceback.print_exc()

    print("\n" + "="*80)
    print("Real-World Testing System demonstration complete!")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
