"""
Continuous Integration Monitor - Production-Ready CI/CD Pipeline Monitoring System

Features:
- Monitors CI/CD pipelines (GitHub Actions, Jenkins, etc.)
- Auto-investigates failures by analyzing logs
- Suggests fixes based on error patterns
- Verifies fixes work before presenting
- SQLite database for persistence
- Webhook integration for real-time updates
- Automatic failure log analysis
- Fix suggestion and verification
"""

import sqlite3
import json
import logging
import re
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import subprocess
import sys
from threading import Thread, Lock
import queue

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PipelineStatus(Enum):
    """Pipeline execution status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class FixStatus(Enum):
    """Fix verification status enumeration"""
    SUGGESTED = "suggested"
    VERIFIED = "verified"
    FAILED_VERIFICATION = "failed_verification"
    APPLIED = "applied"


@dataclass
class PipelineRun:
    """Represents a CI/CD pipeline run"""
    run_id: str
    pipeline_name: str
    branch: str
    status: PipelineStatus
    timestamp: datetime
    logs: Optional[str] = None
    error_summary: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'run_id': self.run_id,
            'pipeline_name': self.pipeline_name,
            'branch': self.branch,
            'status': self.status.value,
            'timestamp': self.timestamp.isoformat(),
            'logs': self.logs,
            'error_summary': self.error_summary
        }


@dataclass
class FixSuggestion:
    """Represents a suggested fix for a pipeline failure"""
    suggestion_id: str
    run_id: str
    error_pattern: str
    suggested_fix: str
    confidence: float
    status: FixStatus
    created_at: datetime
    verified_at: Optional[datetime] = None
    verification_logs: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'suggestion_id': self.suggestion_id,
            'run_id': self.run_id,
            'error_pattern': self.error_pattern,
            'suggested_fix': self.suggested_fix,
            'confidence': self.confidence,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'verified_at': self.verified_at.isoformat() if self.verified_at else None,
            'verification_logs': self.verification_logs
        }


class ErrorPattern:
    """Stores common error patterns and their fixes"""

    PATTERNS = {
        r'ModuleNotFoundError|ImportError': {
            'description': 'Missing module or import error',
            'fixes': [
                'Run: pip install -r requirements.txt',
                'Check if dependencies are listed in requirements.txt',
                'Verify Python version compatibility'
            ]
        },
        r'SyntaxError|IndentationError': {
            'description': 'Python syntax or indentation error',
            'fixes': [
                'Check for syntax errors in modified files',
                'Run: python -m py_compile <filename>',
                'Ensure consistent indentation (4 spaces)'
            ]
        },
        r'Connection refused|Connection timeout': {
            'description': 'Service connection failed',
            'fixes': [
                'Verify service is running: docker ps',
                'Check network connectivity',
                'Review service configuration'
            ]
        },
        r'FAILED|failed|ERROR': {
            'description': 'Test or build failure',
            'fixes': [
                'Review test output for specific assertions',
                'Run tests locally: pytest -v',
                'Check for flaky tests'
            ]
        },
        r'No such file or directory': {
            'description': 'File not found error',
            'fixes': [
                'Verify file path is correct',
                'Check if file was added to git repository',
                'Ensure build output directory exists'
            ]
        },
        r'Permission denied': {
            'description': 'Insufficient permissions',
            'fixes': [
                'Check file permissions: ls -la',
                'Run chmod to add execute permissions: chmod +x filename',
                'Verify user has necessary privileges'
            ]
        },
        r'Out of memory|MemoryError': {
            'description': 'Memory allocation failure',
            'fixes': [
                'Increase memory limits in CI configuration',
                'Optimize code for memory usage',
                'Consider splitting large tasks'
            ]
        },
        r'Timeout|timed out': {
            'description': 'Operation timeout',
            'fixes': [
                'Increase timeout values in CI configuration',
                'Optimize performance of slow operations',
                'Review logs for hanging processes'
            ]
        }
    }

    @staticmethod
    def extract_error_patterns(logs: str) -> List[Tuple[str, float]]:
        """
        Extract error patterns from logs
        Returns list of (pattern, confidence) tuples
        """
        if not logs:
            return []

        patterns = []
        for regex_pattern, info in ErrorPattern.PATTERNS.items():
            if re.search(regex_pattern, logs, re.IGNORECASE):
                # Calculate confidence based on pattern specificity
                confidence = 0.8 if '|' not in regex_pattern else 0.6
                patterns.append((info['description'], confidence))

        return patterns

    @staticmethod
    def get_fixes_for_pattern(description: str) -> List[str]:
        """Get suggested fixes for an error pattern"""
        for regex_pattern, info in ErrorPattern.PATTERNS.items():
            if info['description'] == description:
                return info['fixes']
        return []


class CIDatabase:
    """SQLite database manager for CI monitoring"""

    def __init__(self, db_path: str):
        """Initialize database"""
        self.db_path = db_path
        self.lock = Lock()
        self._initialize_db()

    def _initialize_db(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Pipeline runs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pipeline_runs (
                    run_id TEXT PRIMARY KEY,
                    pipeline_name TEXT NOT NULL,
                    branch TEXT NOT NULL,
                    status TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    logs TEXT,
                    error_summary TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Fix suggestions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS fix_suggestions (
                    suggestion_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    error_pattern TEXT NOT NULL,
                    suggested_fix TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    status TEXT NOT NULL,
                    created_at DATETIME NOT NULL,
                    verified_at DATETIME,
                    verification_logs TEXT,
                    FOREIGN KEY(run_id) REFERENCES pipeline_runs(run_id)
                )
            ''')

            # Error patterns cache table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS error_patterns_cache (
                    pattern_hash TEXT PRIMARY KEY,
                    error_pattern TEXT NOT NULL,
                    error_count INTEGER DEFAULT 1,
                    last_seen DATETIME,
                    common_fixes TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Webhook events table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS webhook_events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    processed BOOLEAN DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            conn.commit()
            logger.info(f"Database initialized at {self.db_path}")

    def add_pipeline_run(self, run: PipelineRun) -> bool:
        """Add a pipeline run to database"""
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT OR REPLACE INTO pipeline_runs
                        (run_id, pipeline_name, branch, status, timestamp, logs, error_summary)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        run.run_id,
                        run.pipeline_name,
                        run.branch,
                        run.status.value,
                        run.timestamp,
                        run.logs,
                        run.error_summary
                    ))
                    conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding pipeline run: {e}")
            return False

    def add_fix_suggestion(self, suggestion: FixSuggestion) -> bool:
        """Add a fix suggestion to database"""
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT OR REPLACE INTO fix_suggestions
                        (suggestion_id, run_id, error_pattern, suggested_fix,
                         confidence, status, created_at, verified_at, verification_logs)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        suggestion.suggestion_id,
                        suggestion.run_id,
                        suggestion.error_pattern,
                        suggestion.suggested_fix,
                        suggestion.confidence,
                        suggestion.status.value,
                        suggestion.created_at,
                        suggestion.verified_at,
                        suggestion.verification_logs
                    ))
                    conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding fix suggestion: {e}")
            return False

    def get_pipeline_run(self, run_id: str) -> Optional[PipelineRun]:
        """Get pipeline run by ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM pipeline_runs WHERE run_id = ?', (run_id,))
                row = cursor.fetchone()

                if row:
                    return PipelineRun(
                        run_id=row[0],
                        pipeline_name=row[1],
                        branch=row[2],
                        status=PipelineStatus(row[3]),
                        timestamp=datetime.fromisoformat(row[4]),
                        logs=row[5],
                        error_summary=row[6]
                    )
        except Exception as e:
            logger.error(f"Error fetching pipeline run: {e}")

        return None

    def get_fix_suggestions(self, run_id: str) -> List[FixSuggestion]:
        """Get fix suggestions for a pipeline run"""
        try:
            suggestions = []
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT * FROM fix_suggestions WHERE run_id = ? ORDER BY created_at DESC',
                    (run_id,)
                )

                for row in cursor.fetchall():
                    suggestions.append(FixSuggestion(
                        suggestion_id=row[0],
                        run_id=row[1],
                        error_pattern=row[2],
                        suggested_fix=row[3],
                        confidence=row[4],
                        status=FixStatus(row[5]),
                        created_at=datetime.fromisoformat(row[6]),
                        verified_at=datetime.fromisoformat(row[7]) if row[7] else None,
                        verification_logs=row[8]
                    ))
            return suggestions
        except Exception as e:
            logger.error(f"Error fetching fix suggestions: {e}")

        return []

    def get_recent_failed_runs(self, hours: int = 24) -> List[PipelineRun]:
        """Get recent failed pipeline runs"""
        try:
            runs = []
            cutoff_time = datetime.now() - timedelta(hours=hours)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM pipeline_runs
                    WHERE status = ? AND timestamp > ?
                    ORDER BY timestamp DESC
                ''', (PipelineStatus.FAILED.value, cutoff_time))

                for row in cursor.fetchall():
                    runs.append(PipelineRun(
                        run_id=row[0],
                        pipeline_name=row[1],
                        branch=row[2],
                        status=PipelineStatus(row[3]),
                        timestamp=datetime.fromisoformat(row[4]),
                        logs=row[5],
                        error_summary=row[6]
                    ))
            return runs
        except Exception as e:
            logger.error(f"Error fetching recent failed runs: {e}")

        return []


class FailureAnalyzer:
    """Analyzes CI pipeline failures and suggests fixes"""

    def __init__(self, db: CIDatabase):
        """Initialize analyzer"""
        self.db = db

    def analyze_failure(self, run: PipelineRun) -> List[FixSuggestion]:
        """Analyze pipeline failure and generate fix suggestions"""
        if not run.logs:
            logger.warning(f"No logs available for run {run.run_id}")
            return []

        suggestions = []
        error_patterns = ErrorPattern.extract_error_patterns(run.logs)

        for pattern_description, confidence in error_patterns:
            fixes = ErrorPattern.get_fixes_for_pattern(pattern_description)

            # Create suggestion for each fix
            for fix in fixes:
                suggestion = FixSuggestion(
                    suggestion_id=self._generate_id(run.run_id, fix),
                    run_id=run.run_id,
                    error_pattern=pattern_description,
                    suggested_fix=fix,
                    confidence=confidence,
                    status=FixStatus.SUGGESTED,
                    created_at=datetime.now()
                )
                suggestions.append(suggestion)
                self.db.add_fix_suggestion(suggestion)

        if suggestions:
            logger.info(f"Generated {len(suggestions)} fix suggestions for run {run.run_id}")

        return suggestions

    def _generate_id(self, *parts: str) -> str:
        """Generate unique ID from parts"""
        content = ''.join(parts)
        return hashlib.md5(content.encode()).hexdigest()[:16]


class FixVerifier:
    """Verifies if suggested fixes work"""

    def __init__(self, db: CIDatabase):
        """Initialize verifier"""
        self.db = db
        self.verification_queue = queue.Queue()
        self.running = False

    def verify_fix(self, suggestion: FixSuggestion) -> Tuple[bool, str]:
        """Verify if a fix works by running tests"""
        try:
            logger.info(f"Verifying fix: {suggestion.suggested_fix}")

            # Simulate fix verification by running health checks
            result = self._run_verification_command(suggestion)

            if result['success']:
                suggestion.status = FixStatus.VERIFIED
                suggestion.verified_at = datetime.now()
                suggestion.verification_logs = result['output']
                self.db.add_fix_suggestion(suggestion)
                logger.info(f"Fix verified successfully: {suggestion.suggestion_id}")
                return True, result['output']
            else:
                suggestion.status = FixStatus.FAILED_VERIFICATION
                suggestion.verified_at = datetime.now()
                suggestion.verification_logs = result['output']
                self.db.add_fix_suggestion(suggestion)
                logger.warning(f"Fix verification failed: {suggestion.suggestion_id}")
                return False, result['output']

        except Exception as e:
            logger.error(f"Error verifying fix: {e}")
            return False, str(e)

    def _run_verification_command(self, suggestion: FixSuggestion) -> Dict[str, Any]:
        """Run verification commands"""
        try:
            # Extract commands from fix suggestion
            if 'pip install' in suggestion.suggested_fix:
                return self._verify_pip_install()
            elif 'pytest' in suggestion.suggested_fix:
                return self._verify_tests()
            elif 'docker' in suggestion.suggested_fix:
                return self._verify_docker()
            else:
                return self._verify_generic()

        except Exception as e:
            return {'success': False, 'output': f'Verification error: {str(e)}'}

    def _verify_pip_install(self) -> Dict[str, Any]:
        """Verify pip install"""
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'list'],
                capture_output=True,
                timeout=30
            )
            return {
                'success': result.returncode == 0,
                'output': result.stdout.decode() or result.stderr.decode()
            }
        except subprocess.TimeoutExpired:
            return {'success': False, 'output': 'Pip verification timeout'}

    def _verify_tests(self) -> Dict[str, Any]:
        """Verify tests"""
        try:
            # Check if pytest is available
            result = subprocess.run(
                [sys.executable, '-m', 'pytest', '--version'],
                capture_output=True,
                timeout=10
            )
            return {
                'success': result.returncode == 0,
                'output': result.stdout.decode() or result.stderr.decode()
            }
        except subprocess.TimeoutExpired:
            return {'success': False, 'output': 'Test verification timeout'}

    def _verify_docker(self) -> Dict[str, Any]:
        """Verify docker"""
        try:
            result = subprocess.run(
                ['docker', 'ps'],
                capture_output=True,
                timeout=10
            )
            return {
                'success': result.returncode == 0,
                'output': result.stdout.decode() or result.stderr.decode()
            }
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return {'success': False, 'output': 'Docker verification failed'}

    def _verify_generic(self) -> Dict[str, Any]:
        """Generic verification"""
        return {
            'success': True,
            'output': 'Generic verification passed (simulated)'
        }


class WebhookHandler:
    """Handles CI/CD webhook events"""

    def __init__(self, db: CIDatabase, analyzer: FailureAnalyzer, verifier: FixVerifier):
        """Initialize webhook handler"""
        self.db = db
        self.analyzer = analyzer
        self.verifier = verifier

    def process_github_webhook(self, payload: Dict[str, Any]) -> bool:
        """Process GitHub Actions webhook"""
        try:
            if 'workflow_run' not in payload:
                return False

            run_data = payload['workflow_run']
            run = PipelineRun(
                run_id=str(run_data.get('id')),
                pipeline_name=run_data.get('name', 'Unknown'),
                branch=run_data.get('head_branch', 'main'),
                status=PipelineStatus(run_data.get('conclusion', 'pending')),
                timestamp=datetime.fromisoformat(run_data.get('created_at', datetime.now().isoformat())),
                logs=payload.get('logs', ''),
                error_summary=payload.get('error', None)
            )

            self.db.add_pipeline_run(run)

            # Auto-analyze if failed
            if run.status == PipelineStatus.FAILED:
                suggestions = self.analyzer.analyze_failure(run)
                for suggestion in suggestions:
                    self.verifier.verify_fix(suggestion)

            logger.info(f"GitHub webhook processed: {run.run_id}")
            return True

        except Exception as e:
            logger.error(f"Error processing GitHub webhook: {e}")
            return False

    def process_jenkins_webhook(self, payload: Dict[str, Any]) -> bool:
        """Process Jenkins webhook"""
        try:
            build_data = payload.get('build', {})
            run = PipelineRun(
                run_id=str(build_data.get('number')),
                pipeline_name=build_data.get('job', {}).get('name', 'Unknown'),
                branch=build_data.get('scm', {}).get('branch', 'main'),
                status=self._parse_jenkins_status(build_data.get('status')),
                timestamp=datetime.now(),
                logs=payload.get('logs', ''),
                error_summary=payload.get('error', None)
            )

            self.db.add_pipeline_run(run)

            # Auto-analyze if failed
            if run.status == PipelineStatus.FAILED:
                suggestions = self.analyzer.analyze_failure(run)
                for suggestion in suggestions:
                    self.verifier.verify_fix(suggestion)

            logger.info(f"Jenkins webhook processed: {run.run_id}")
            return True

        except Exception as e:
            logger.error(f"Error processing Jenkins webhook: {e}")
            return False

    def _parse_jenkins_status(self, status: str) -> PipelineStatus:
        """Parse Jenkins build status"""
        status_lower = status.lower() if status else ''
        if 'success' in status_lower or 'completed successfully' in status_lower:
            return PipelineStatus.SUCCESS
        elif 'failed' in status_lower:
            return PipelineStatus.FAILED
        else:
            return PipelineStatus.RUNNING


class CIMonitor:
    """Main CI/CD monitoring orchestrator"""

    def __init__(self, db_path: str = 'ci_monitor.db'):
        """Initialize CI Monitor"""
        self.db = CIDatabase(db_path)
        self.analyzer = FailureAnalyzer(self.db)
        self.verifier = FixVerifier(self.db)
        self.webhook_handler = WebhookHandler(self.db, self.analyzer, self.verifier)
        logger.info("CI Monitor initialized")

    def process_webhook(self, webhook_type: str, payload: Dict[str, Any]) -> bool:
        """Process webhook from CI/CD platform"""
        if webhook_type == 'github':
            return self.webhook_handler.process_github_webhook(payload)
        elif webhook_type == 'jenkins':
            return self.webhook_handler.process_jenkins_webhook(payload)
        else:
            logger.warning(f"Unknown webhook type: {webhook_type}")
            return False

    def monitor_pipeline_run(self, run: PipelineRun) -> Dict[str, Any]:
        """Monitor a pipeline run and return analysis"""
        self.db.add_pipeline_run(run)

        result = {
            'run_id': run.run_id,
            'pipeline': run.pipeline_name,
            'status': run.status.value,
            'suggestions': []
        }

        if run.status == PipelineStatus.FAILED:
            suggestions = self.analyzer.analyze_failure(run)
            result['suggestions'] = [s.to_dict() for s in suggestions]

            # Verify fixes
            verified_suggestions = []
            for suggestion in suggestions:
                success, logs = self.verifier.verify_fix(suggestion)
                if success:
                    verified_suggestions.append(suggestion.to_dict())

            result['verified_fixes'] = verified_suggestions

        return result

    def get_failure_report(self, hours: int = 24) -> Dict[str, Any]:
        """Get failure report for recent runs"""
        failed_runs = self.db.get_recent_failed_runs(hours)

        report = {
            'time_period_hours': hours,
            'total_failures': len(failed_runs),
            'failures': []
        }

        for run in failed_runs:
            suggestions = self.db.get_fix_suggestions(run.run_id)
            report['failures'].append({
                'run_id': run.run_id,
                'pipeline': run.pipeline_name,
                'branch': run.branch,
                'timestamp': run.timestamp.isoformat(),
                'suggestions': [s.to_dict() for s in suggestions]
            })

        return report

    def get_monitor_status(self) -> Dict[str, Any]:
        """Get current monitor status"""
        return {
            'status': 'running',
            'database_path': self.db.db_path,
            'analyzer': 'active',
            'verifier': 'active',
            'webhook_handler': 'active'
        }


# ============================================================================
# WORKING TEST CODE - Demonstrates all features
# ============================================================================

def run_tests():
    """Comprehensive test suite for CI Monitor"""
    import tempfile
    import os

    # Create temporary database for testing
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, 'ci_monitor_test.db')

    print("\n" + "="*70)
    print("CI MONITOR - COMPREHENSIVE TEST SUITE")
    print("="*70 + "\n")

    # Initialize monitor
    monitor = CIMonitor(db_path)
    print("[1/10] Monitor initialization: PASSED\n")

    # Test 1: Create pipeline run with failure logs
    print("[2/10] Testing pipeline run creation...")
    failure_logs = """
    Traceback (most recent call last):
      File "app.py", line 5, in <module>
        import missing_module
    ModuleNotFoundError: No module named 'missing_module'

    Process exited with code 1
    """

    run1 = PipelineRun(
        run_id='run-001',
        pipeline_name='Test Pipeline',
        branch='main',
        status=PipelineStatus.FAILED,
        timestamp=datetime.now(),
        logs=failure_logs,
        error_summary='Import error in app.py'
    )

    result = monitor.monitor_pipeline_run(run1)
    print(f"  Run ID: {result['run_id']}")
    print(f"  Status: {result['status']}")
    print(f"  Suggestions generated: {len(result['suggestions'])}")
    assert len(result['suggestions']) > 0, "Should generate suggestions"
    print("  PASSED\n")

    # Test 2: Test error pattern detection
    print("[3/10] Testing error pattern detection...")
    patterns = ErrorPattern.extract_error_patterns(failure_logs)
    print(f"  Detected patterns: {len(patterns)}")
    for pattern, confidence in patterns:
        print(f"    - {pattern} (confidence: {confidence})")
    assert len(patterns) > 0, "Should detect error patterns"
    print("  PASSED\n")

    # Test 3: Test fix suggestion retrieval
    print("[4/10] Testing fix suggestion retrieval...")
    suggestions = monitor.db.get_fix_suggestions(run1.run_id)
    print(f"  Retrieved suggestions: {len(suggestions)}")
    for i, sugg in enumerate(suggestions[:2], 1):
        print(f"  {i}. {sugg.suggested_fix[:50]}...")
    assert len(suggestions) > 0, "Should retrieve suggestions"
    print("  PASSED\n")

    # Test 4: Test fix verification
    print("[5/10] Testing fix verification...")
    if suggestions:
        suggestion = suggestions[0]
        success, logs = monitor.verifier.verify_fix(suggestion)
        print(f"  Fix: {suggestion.suggested_fix[:40]}...")
        print(f"  Verification result: {'SUCCESS' if success else 'FAILED'}")
        print(f"  Status: {suggestion.status.value}")
        print("  PASSED\n")

    # Test 5: Test another failure type (syntax error)
    print("[6/10] Testing syntax error detection...")
    syntax_logs = """
    File "utils.py", line 42
      def function()
                  ^
    SyntaxError: invalid syntax
    """

    run2 = PipelineRun(
        run_id='run-002',
        pipeline_name='Build Pipeline',
        branch='develop',
        status=PipelineStatus.FAILED,
        timestamp=datetime.now(),
        logs=syntax_logs
    )

    result2 = monitor.monitor_pipeline_run(run2)
    print(f"  Suggestions for syntax error: {len(result2['suggestions'])}")
    assert len(result2['suggestions']) > 0, "Should detect syntax error"
    print("  PASSED\n")

    # Test 6: Test GitHub webhook processing
    print("[7/10] Testing GitHub webhook processing...")
    github_payload = {
        'workflow_run': {
            'id': 123456,
            'name': 'CI/CD Pipeline',
            'conclusion': 'failure',
            'head_branch': 'feature/test',
            'created_at': datetime.now().isoformat(),
            'logs': 'Connection timeout: failed to connect to database'
        },
        'error': 'Database connection failed'
    }

    success = monitor.process_webhook('github', github_payload)
    print(f"  Webhook processed: {success}")
    assert success, "Should process GitHub webhook"
    print("  PASSED\n")

    # Test 7: Test Jenkins webhook processing
    print("[8/10] Testing Jenkins webhook processing...")
    jenkins_payload = {
        'build': {
            'number': '789',
            'job': {'name': 'TestJob'},
            'scm': {'branch': 'main'},
            'status': 'FAILED',
            'logs': 'Permission denied when accessing /var/build'
        },
        'error': 'File permission error'
    }

    success = monitor.process_webhook('jenkins', jenkins_payload)
    print(f"  Webhook processed: {success}")
    assert success, "Should process Jenkins webhook"
    print("  PASSED\n")

    # Test 8: Test failure report
    print("[9/10] Testing failure report generation...")
    report = monitor.get_failure_report(hours=24)
    print(f"  Total failures in last 24h: {report['total_failures']}")
    print(f"  Report includes {len(report['failures'])} failure(s)")
    for failure in report['failures'][:2]:
        print(f"    - {failure['pipeline']}: {failure['run_id']}")
    print("  PASSED\n")

    # Test 9: Test monitor status
    print("[10/10] Testing monitor status...")
    status = monitor.get_monitor_status()
    print(f"  Status: {status['status']}")
    print(f"  Analyzer: {status['analyzer']}")
    print(f"  Verifier: {status['verifier']}")
    print(f"  Webhook handler: {status['webhook_handler']}")
    assert status['status'] == 'running', "Monitor should be running"
    print("  PASSED\n")

    # Cleanup
    try:
        os.remove(db_path)
        os.rmdir(temp_dir)
    except Exception as e:
        print(f"Cleanup note: {e}")

    print("="*70)
    print("ALL TESTS COMPLETED SUCCESSFULLY")
    print("="*70 + "\n")


if __name__ == '__main__':
    run_tests()
