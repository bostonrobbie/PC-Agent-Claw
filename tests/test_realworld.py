#!/usr/bin/env python3
"""
Tests for Real-World Integration Testing System

Comprehensive test suite covering:
- Session management
- Activity monitoring
- Performance metrics collection
- Issue tracking
- Improvement report generation
- Resource safety monitoring
"""

import os
import sys
import time
import unittest
import sqlite3
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# Add workspace to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from autonomous.realworld_tester import (
    RealWorldTester,
    TestSession,
    Activity,
    PerformanceMetric,
    Issue
)


class TestRealWorldTester(unittest.TestCase):
    """Test suite for RealWorldTester"""

    def setUp(self):
        """Set up test fixtures"""
        # Create temporary directory for test database
        self.test_dir = tempfile.mkdtemp()
        self.test_db = os.path.join(self.test_dir, "test_realworld.db")

        # Initialize tester
        self.tester = RealWorldTester(db_path=self.test_db)

        # Use current workspace as test project
        self.test_project = os.path.dirname(os.path.dirname(__file__))

    def tearDown(self):
        """Clean up test fixtures"""
        # Stop any active sessions
        for session_id in list(self.tester.active_sessions.keys()):
            try:
                self.tester.stop_session(session_id)
            except:
                pass

        # Clean up test directory
        try:
            shutil.rmtree(self.test_dir)
        except:
            pass

    def test_01_initialization(self):
        """Test tester initialization"""
        print("\n[TEST 1] Testing initialization...")

        # Check database was created
        self.assertTrue(os.path.exists(self.test_db))

        # Check tables exist
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table'
            ORDER BY name
        """)

        tables = [row[0] for row in cursor.fetchall()]
        conn.close()

        expected_tables = [
            'activities',
            'improvement_suggestions',
            'issues',
            'performance_metrics',
            'test_sessions'
        ]

        for table in expected_tables:
            self.assertIn(table, tables, f"Table {table} should exist")

        print("   [OK] Initialization successful")

    def test_02_start_session(self):
        """Test starting a test session"""
        print("\n[TEST 2] Testing session start...")

        session_id = self.tester.start_test_session(
            self.test_project,
            duration_minutes=1
        )

        # Check session was created
        self.assertIsNotNone(session_id)
        self.assertIn(session_id, self.tester.active_sessions)

        # Check session in database
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM test_sessions WHERE session_id = ?', (session_id,))
        session = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(session)
        print(f"   [OK] Session started: {session_id}")

        # Clean up
        self.tester.stop_session(session_id)

    def test_03_invalid_project_path(self):
        """Test error handling for invalid project path"""
        print("\n[TEST 3] Testing invalid project path...")

        with self.assertRaises(ValueError):
            self.tester.start_test_session(
                "/nonexistent/path/to/project",
                duration_minutes=1
            )

        print("   [OK] Invalid path handled correctly")

    def test_04_activity_logging(self):
        """Test activity logging"""
        print("\n[TEST 4] Testing activity logging...")

        session_id = self.tester.start_test_session(self.test_project, 1)

        # Manually log an activity
        self.tester._log_activity(
            session_id=session_id,
            capability='test_capability',
            activity_type='test_action',
            description='Test activity',
            response_time_ms=123.45,
            cpu_before=10.0,
            cpu_after=15.0,
            mem_before=100.0,
            mem_after=120.0,
            success=True,
            error_message=None,
            result_data='{"test": "data"}'
        )

        # Check activity was logged
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) FROM activities WHERE session_id = ?
        ''', (session_id,))
        count = cursor.fetchone()[0]
        conn.close()

        self.assertEqual(count, 1)
        print("   [OK] Activity logged successfully")

        self.tester.stop_session(session_id)

    def test_05_metric_logging(self):
        """Test performance metric logging"""
        print("\n[TEST 5] Testing metric logging...")

        session_id = self.tester.start_test_session(self.test_project, 1)

        # Log metrics
        self.tester._log_metric(
            session_id=session_id,
            capability='test_capability',
            metric_type='response_time',
            value=123.45,
            unit='ms',
            context='Test metric'
        )

        # Check metric was logged
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) FROM performance_metrics WHERE session_id = ?
        ''', (session_id,))
        count = cursor.fetchone()[0]
        conn.close()

        self.assertEqual(count, 1)
        print("   [OK] Metric logged successfully")

        self.tester.stop_session(session_id)

    def test_06_issue_logging(self):
        """Test issue logging"""
        print("\n[TEST 6] Testing issue logging...")

        session_id = self.tester.start_test_session(self.test_project, 1)

        # Log issues of different severities
        severities = ['critical', 'high', 'medium', 'low', 'info']
        for severity in severities:
            self.tester._log_issue(
                session_id=session_id,
                severity=severity,
                capability='test_capability',
                issue_type='test_issue',
                description=f'Test {severity} issue',
                suggested_fix=f'Fix for {severity} issue'
            )

        # Check issues were logged
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) FROM issues WHERE session_id = ?
        ''', (session_id,))
        count = cursor.fetchone()[0]
        conn.close()

        self.assertEqual(count, len(severities))
        print(f"   [OK] {len(severities)} issues logged successfully")

        self.tester.stop_session(session_id)

    def test_07_monitor_activities(self):
        """Test activity monitoring"""
        print("\n[TEST 7] Testing activity monitoring...")

        session_id = self.tester.start_test_session(self.test_project, 1)

        # Give it time to do something
        time.sleep(2)

        # Get monitoring data
        monitor_data = self.tester.monitor_activities()

        self.assertIn('timestamp', monitor_data)
        self.assertIn('active_sessions', monitor_data)
        self.assertIsInstance(monitor_data['active_sessions'], list)

        if monitor_data['active_sessions']:
            session_info = monitor_data['active_sessions'][0]
            self.assertEqual(session_info['session_id'], session_id)

        print("   [OK] Activity monitoring working")

        self.tester.stop_session(session_id)

    def test_08_collect_metrics(self):
        """Test metrics collection"""
        print("\n[TEST 8] Testing metrics collection...")

        session_id = self.tester.start_test_session(self.test_project, 1)

        # Log some test metrics
        for i in range(5):
            self.tester._log_metric(
                session_id, 'test_cap', 'response_time',
                100 + i * 10, 'ms', 'Test'
            )

        # Collect metrics
        metrics = self.tester.collect_metrics()

        self.assertIn('timestamp', metrics)
        self.assertIn('system_resources', metrics)
        self.assertIn('by_capability', metrics)

        # Check system resources
        resources = metrics['system_resources']
        self.assertIn('cpu_percent', resources)
        self.assertIn('memory_percent', resources)
        self.assertIn('disk_percent', resources)

        print("   [OK] Metrics collection working")

        self.tester.stop_session(session_id)

    def test_09_resource_safety_check(self):
        """Test resource safety monitoring"""
        print("\n[TEST 9] Testing resource safety check...")

        session_id = self.tester.start_test_session(self.test_project, 1)

        # Normal resources should be safe
        is_safe = self.tester._check_resource_safety(session_id)
        self.assertTrue(is_safe)

        print("   [OK] Resource safety check working")

        self.tester.stop_session(session_id)

    def test_10_stop_session(self):
        """Test stopping a session"""
        print("\n[TEST 10] Testing session stop...")

        session_id = self.tester.start_test_session(self.test_project, 1)

        # Give it time to do something
        time.sleep(2)

        # Stop session
        final_stats = self.tester.stop_session(session_id)

        # Check session was stopped
        self.assertNotIn(session_id, self.tester.active_sessions)
        self.assertIn('total_activities', final_stats)

        # Check database was updated
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT status, end_time FROM test_sessions WHERE session_id = ?
        ''', (session_id,))
        row = cursor.fetchone()
        conn.close()

        self.assertEqual(row[0], 'completed')
        self.assertIsNotNone(row[1])

        print("   [OK] Session stopped successfully")

    def test_11_analyze_session_results(self):
        """Test session results analysis"""
        print("\n[TEST 11] Testing session analysis...")

        session_id = self.tester.start_test_session(self.test_project, 1)

        # Log some test activities
        for i in range(5):
            self.tester._log_activity(
                session_id, 'test_cap', 'test_action',
                f'Activity {i}', 100 + i * 10,
                10.0, 15.0, 100.0, 120.0,
                True, None, '{}'
            )

        # Log some issues
        self.tester._log_issue(
            session_id, 'high', 'test_cap',
            'performance', 'Slow response',
            'Optimize code'
        )

        # Stop session
        self.tester.stop_session(session_id)

        # Analyze results
        analysis = self.tester.analyze_session_results(session_id)

        # Check analysis structure
        self.assertIn('session', analysis)
        self.assertIn('summary', analysis)
        self.assertIn('activities_by_capability', analysis)
        self.assertIn('performance_metrics', analysis)
        self.assertIn('issues_by_severity', analysis)
        self.assertIn('top_issues', analysis)
        self.assertIn('worked_well', analysis)
        self.assertIn('worked_poorly', analysis)

        # Check summary
        summary = analysis['summary']
        self.assertIn('total_activities', summary)
        self.assertIn('success_rate', summary)

        print("   [OK] Session analysis working")

    def test_12_generate_improvement_report(self):
        """Test improvement report generation"""
        print("\n[TEST 12] Testing improvement report generation...")

        session_id = self.tester.start_test_session(self.test_project, 1)

        # Log activities with varying performance
        # Good performance
        for i in range(3):
            self.tester._log_activity(
                session_id, 'good_cap', 'test',
                'Fast activity', 50.0,
                10.0, 12.0, 100.0, 105.0,
                True, None, '{}'
            )

        # Poor performance
        for i in range(3):
            self.tester._log_activity(
                session_id, 'slow_cap', 'test',
                'Slow activity', 15000.0,
                10.0, 50.0, 100.0, 200.0,
                False, 'Error occurred', '{}'
            )

        # Log critical issue
        self.tester._log_issue(
            session_id, 'critical', 'slow_cap',
            'performance', 'Very slow responses',
            'Optimize algorithm'
        )

        # Stop session
        self.tester.stop_session(session_id)

        # Generate report
        report = self.tester.generate_improvement_report(session_id)

        # Check report content
        self.assertIsInstance(report, str)
        self.assertIn('IMPROVEMENT REPORT', report)
        self.assertIn('SUMMARY', report)
        self.assertIn('WHAT WORKED WELL', report)
        self.assertIn('WHAT WORKED POORLY', report)
        self.assertIn('TOP ISSUES', report)
        self.assertIn('ACTIONABLE IMPROVEMENTS', report)

        # Check suggestions were stored
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) FROM improvement_suggestions WHERE session_id = ?
        ''', (session_id,))
        count = cursor.fetchone()[0]
        conn.close()

        self.assertGreater(count, 0, "Should generate improvement suggestions")

        print(f"   [OK] Generated report with {count} suggestions")

    def test_13_multiple_sessions(self):
        """Test handling multiple concurrent sessions"""
        print("\n[TEST 13] Testing multiple concurrent sessions...")

        # Start multiple sessions
        session_ids = []
        for i in range(3):
            sid = self.tester.start_test_session(self.test_project, 1)
            session_ids.append(sid)

        # Check all are active
        self.assertEqual(len(self.tester.active_sessions), 3)

        # Monitor all
        monitor_data = self.tester.monitor_activities()
        self.assertEqual(len(monitor_data['active_sessions']), 3)

        # Stop all
        for sid in session_ids:
            self.tester.stop_session(sid)

        self.assertEqual(len(self.tester.active_sessions), 0)

        print("   [OK] Multiple sessions handled correctly")

    def test_14_session_duration_timeout(self):
        """Test session auto-stop after duration"""
        print("\n[TEST 14] Testing session duration timeout...")

        # Start session with very short duration
        session_id = self.tester.start_test_session(self.test_project, 0.1)  # 6 seconds

        # Wait for timeout
        time.sleep(15)

        # Session should have stopped
        self.assertNotIn(session_id, self.tester.active_sessions)

        # Check database
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        cursor.execute('SELECT status FROM test_sessions WHERE session_id = ?', (session_id,))
        status = cursor.fetchone()[0]
        conn.close()

        self.assertEqual(status, 'completed')

        print("   [OK] Session auto-stopped after duration")

    def test_15_error_recovery_tracking(self):
        """Test error recovery activity tracking"""
        print("\n[TEST 15] Testing error recovery tracking...")

        session_id = self.tester.start_test_session(self.test_project, 1)

        # Log error recovery activity
        self.tester._log_activity(
            session_id, 'error_recovery', 'handle_error',
            'Recovered from error', 50.0,
            10.0, 12.0, 100.0, 105.0,
            True, None, '{"recovered": true}'
        )

        # Check activity was logged
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) FROM activities
            WHERE session_id = ? AND capability = 'error_recovery'
        ''', (session_id,))
        count = cursor.fetchone()[0]
        conn.close()

        self.assertEqual(count, 1)

        print("   [OK] Error recovery tracking working")

        self.tester.stop_session(session_id)

    def test_16_worked_well_detection(self):
        """Test detection of what worked well"""
        print("\n[TEST 16] Testing worked-well detection...")

        session_id = self.tester.start_test_session(self.test_project, 1)

        # Log excellent performance
        for i in range(10):
            self.tester._log_activity(
                session_id, 'excellent_cap', 'test',
                'Great activity', 50.0,
                10.0, 11.0, 100.0, 101.0,
                True, None, '{}'
            )

        self.tester.stop_session(session_id)

        # Analyze
        analysis = self.tester.analyze_session_results(session_id)

        # Should detect this worked well
        worked_well = analysis['worked_well']
        self.assertGreater(len(worked_well), 0)

        if worked_well:
            self.assertEqual(worked_well[0]['capability'], 'excellent_cap')

        print("   [OK] Worked-well detection functioning")

    def test_17_worked_poorly_detection(self):
        """Test detection of what worked poorly"""
        print("\n[TEST 17] Testing worked-poorly detection...")

        session_id = self.tester.start_test_session(self.test_project, 1)

        # Log poor performance
        for i in range(10):
            self.tester._log_activity(
                session_id, 'poor_cap', 'test',
                'Bad activity', 20000.0,  # Very slow
                10.0, 80.0, 100.0, 500.0,
                i % 2 == 0,  # 50% failure rate
                'Error' if i % 2 else None,
                '{}'
            )

        self.tester.stop_session(session_id)

        # Analyze
        analysis = self.tester.analyze_session_results(session_id)

        # Should detect this worked poorly
        worked_poorly = analysis['worked_poorly']
        self.assertGreater(len(worked_poorly), 0)

        if worked_poorly:
            self.assertEqual(worked_poorly[0]['capability'], 'poor_cap')

        print("   [OK] Worked-poorly detection functioning")

    def test_18_overall_score_calculation(self):
        """Test overall session score calculation"""
        print("\n[TEST 18] Testing overall score calculation...")

        session_id = self.tester.start_test_session(self.test_project, 1)

        # Log mix of good and bad activities
        # 80% success rate, fast responses
        for i in range(10):
            self.tester._log_activity(
                session_id, 'test_cap', 'test',
                f'Activity {i}', 100.0,
                10.0, 15.0, 100.0, 110.0,
                i < 8,  # 80% success
                None if i < 8 else 'Error',
                '{}'
            )

        final_stats = self.tester.stop_session(session_id)

        # Check score
        self.assertIn('overall_score', final_stats)
        score = final_stats['overall_score']

        # Score should be reasonable (50-90 range for 80% success)
        self.assertGreater(score, 50)
        self.assertLess(score, 100)

        print(f"   [OK] Overall score calculated: {score:.1f}/100")

    def test_19_database_indexes(self):
        """Test database indexes exist for performance"""
        print("\n[TEST 19] Testing database indexes...")

        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='index'
        """)

        indexes = [row[0] for row in cursor.fetchall()]
        conn.close()

        # Check key indexes exist
        expected_indexes = [
            'idx_activities_session',
            'idx_activities_capability',
            'idx_metrics_session',
            'idx_issues_session',
            'idx_issues_severity'
        ]

        for idx in expected_indexes:
            self.assertIn(idx, indexes, f"Index {idx} should exist")

        print(f"   [OK] All {len(expected_indexes)} indexes present")

    def test_20_full_integration_test(self):
        """Full integration test of the entire system"""
        print("\n[TEST 20] Running full integration test...")

        # Start session
        print("   - Starting session...")
        session_id = self.tester.start_test_session(self.test_project, 0.5)

        # Let it run for a bit
        print("   - Running for 30 seconds...")
        time.sleep(30)

        # Monitor activities
        print("   - Monitoring activities...")
        monitor_data = self.tester.monitor_activities()
        self.assertGreater(monitor_data['total_activities'], 0)

        # Collect metrics
        print("   - Collecting metrics...")
        metrics = self.tester.collect_metrics()
        self.assertIn('system_resources', metrics)

        # Stop session
        print("   - Stopping session...")
        final_stats = self.tester.stop_session(session_id)
        self.assertGreater(final_stats['total_activities'], 0)

        # Analyze results
        print("   - Analyzing results...")
        analysis = self.tester.analyze_session_results(session_id)
        self.assertIn('summary', analysis)

        # Generate report
        print("   - Generating report...")
        report = self.tester.generate_improvement_report(session_id)
        self.assertIn('IMPROVEMENT REPORT', report)

        print("   [OK] Full integration test complete")
        print(f"        Activities: {final_stats['total_activities']}")
        print(f"        Errors: {final_stats['total_errors']}")
        print(f"        Score: {final_stats['overall_score']:.1f}/100")


def run_tests():
    """Run all tests with detailed output"""
    print("\n" + "="*80)
    print("REAL-WORLD TESTING SYSTEM - TEST SUITE")
    print("="*80)

    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestRealWorldTester)

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Tests Run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

    if result.wasSuccessful():
        print("\n[OK] ALL TESTS PASSED")
    else:
        print("\n[FAIL] SOME TESTS FAILED")

    print("="*80 + "\n")

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
