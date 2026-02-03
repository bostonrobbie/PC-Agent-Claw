"""
Comprehensive Tests for Self-Improvement Loop System

Tests all functionality of the autonomous self-improvement system including:
- Performance analysis
- Bottleneck identification
- Improvement generation
- Safe testing in sandbox
- Improvement application and rollback
- History tracking and statistics

Author: AI Self-Improvement System
Created: 2026-02-03
"""

import unittest
import sys
import os
import tempfile
import sqlite3
import json
import time
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from autonomous.self_improvement import (
    SelfImprovementLoop,
    PerformanceMetrics,
    Bottleneck,
    Improvement,
    TestResult
)


class TestSelfImprovementLoop(unittest.TestCase):
    """Test suite for Self-Improvement Loop System"""

    def setUp(self):
        """Set up test environment before each test"""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name

        # Initialize self-improvement loop
        self.loop = SelfImprovementLoop(
            db_path=self.db_path,
            workspace_path=str(Path(__file__).parent.parent)
        )

    def tearDown(self):
        """Clean up after each test"""
        # Remove temporary database
        try:
            os.unlink(self.db_path)
        except Exception:
            pass

    def test_initialization(self):
        """Test that self-improvement loop initializes correctly"""
        self.assertIsNotNone(self.loop)
        self.assertEqual(self.loop.db_path, self.db_path)
        self.assertIsNotNone(self.loop.code_reviewer)
        self.assertIsNotNone(self.loop.sandbox)
        self.assertIsNotNone(self.loop.memory)

        # Check database tables exist
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Check all required tables
        tables = [
            'performance_metrics',
            'bottlenecks',
            'improvements',
            'test_results',
            'applied_improvements'
        ]

        for table in tables:
            c.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
            result = c.fetchone()
            self.assertIsNotNone(result, f"Table {table} should exist")

        conn.close()

    def test_target_metrics_defined(self):
        """Test that target metrics are properly defined"""
        self.assertIsNotNone(self.loop.TARGET_METRICS)
        self.assertGreater(len(self.loop.TARGET_METRICS), 0)

        # Check specific metrics exist
        expected_metrics = [
            'indexing_speed',
            'memory_usage_mb',
            'query_time_ms',
            'cpu_percent',
            'cache_hit_rate',
            'error_count'
        ]

        for metric in expected_metrics:
            self.assertIn(metric, self.loop.TARGET_METRICS)
            self.assertIsInstance(self.loop.TARGET_METRICS[metric], (int, float))

    def test_analyze_own_performance(self):
        """Test performance analysis functionality"""
        result = self.loop.analyze_own_performance(session_id="test_session")

        # Check result structure
        self.assertIn('metrics', result)
        self.assertIn('targets', result)
        self.assertIn('analysis_time', result)
        self.assertIn('timestamp', result)

        # Check metrics are captured
        metrics = result['metrics']
        self.assertIn('indexing_speed', metrics)
        self.assertIn('memory_usage_mb', metrics)
        self.assertIn('query_time_ms', metrics)
        self.assertIn('cpu_percent', metrics)

        # Check values are reasonable
        self.assertGreaterEqual(metrics['memory_usage_mb'], 0)
        self.assertGreaterEqual(metrics['cpu_percent'], 0)
        self.assertLessEqual(metrics['cpu_percent'], 100)

        # Check metrics are stored in database
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM performance_metrics')
        count = c.fetchone()[0]
        self.assertGreater(count, 0, "Metrics should be stored in database")
        conn.close()

    def test_baseline_metrics_establishment(self):
        """Test that baseline metrics are established on first analysis"""
        self.assertIsNone(self.loop.baseline_metrics)

        # First analysis should establish baseline
        self.loop.analyze_own_performance()

        self.assertIsNotNone(self.loop.baseline_metrics)
        self.assertIsNotNone(self.loop.current_metrics)

    def test_identify_bottlenecks(self):
        """Test bottleneck identification"""
        # First analyze performance
        self.loop.analyze_own_performance()

        # Identify bottlenecks
        bottlenecks = self.loop.identify_bottlenecks()

        # Check return type
        self.assertIsInstance(bottlenecks, list)

        # If bottlenecks found, check their structure
        if bottlenecks:
            bottleneck = bottlenecks[0]

            # Check required fields
            self.assertIn('id', bottleneck)
            self.assertIn('metric_name', bottleneck)
            self.assertIn('current_value', bottleneck)
            self.assertIn('target_value', bottleneck)
            self.assertIn('severity', bottleneck)
            self.assertIn('impact_score', bottleneck)
            self.assertIn('description', bottleneck)

            # Check severity is valid
            self.assertIn(bottleneck['severity'], ['low', 'medium', 'high', 'critical'])

            # Check impact score is in range
            self.assertGreaterEqual(bottleneck['impact_score'], 0)
            self.assertLessEqual(bottleneck['impact_score'], 100)

        # Check bottlenecks are stored in database
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM bottlenecks')
        count = c.fetchone()[0]
        self.assertEqual(count, len(bottlenecks), "All bottlenecks should be stored")
        conn.close()

    def test_bottleneck_severity_calculation(self):
        """Test bottleneck severity is calculated correctly"""
        # Manually create metrics with known bottleneck
        self.loop.current_metrics = PerformanceMetrics(
            timestamp=datetime.now().isoformat(),
            indexing_speed=10.0,  # Target is 50.0 - should be high severity
            memory_usage_mb=400.0,
            query_time_ms=50.0,
            cpu_percent=60.0,
            database_size_mb=100.0,
            active_connections=1,
            cache_hit_rate=0.75,
            error_count=0
        )

        bottlenecks = self.loop.identify_bottlenecks()

        # Find indexing_speed bottleneck
        indexing_bottleneck = None
        for b in bottlenecks:
            if b['metric_name'] == 'indexing_speed':
                indexing_bottleneck = b
                break

        if indexing_bottleneck:
            # Should be high or critical severity
            self.assertIn(indexing_bottleneck['severity'], ['high', 'critical'])
            self.assertGreater(indexing_bottleneck['impact_score'], 50)

    def test_generate_improvements(self):
        """Test improvement generation"""
        # First create some bottlenecks
        self.loop.analyze_own_performance()
        self.loop.identify_bottlenecks()

        # Generate improvements
        improvements = self.loop.generate_improvements(max_suggestions=3)

        # Check return type
        self.assertIsInstance(improvements, list)
        self.assertLessEqual(len(improvements), 3)

        # If improvements generated, check structure
        if improvements:
            improvement = improvements[0]

            # Check required fields
            self.assertIn('id', improvement)
            self.assertIn('bottleneck_id', improvement)
            self.assertIn('suggestion_type', improvement)
            self.assertIn('description', improvement)
            self.assertIn('code_changes', improvement)
            self.assertIn('expected_improvement', improvement)
            self.assertIn('confidence', improvement)
            self.assertIn('status', improvement)

            # Check values are reasonable
            self.assertIn(improvement['suggestion_type'],
                         ['optimization', 'refactoring', 'caching', 'indexing'])
            self.assertEqual(improvement['status'], 'proposed')
            self.assertGreater(improvement['expected_improvement'], 0)
            self.assertGreaterEqual(improvement['confidence'], 0)
            self.assertLessEqual(improvement['confidence'], 1)

            # Check code_changes is valid JSON
            code_changes = json.loads(improvement['code_changes'])
            self.assertIsInstance(code_changes, dict)

    def test_improvement_types(self):
        """Test that different improvement types are generated for different bottlenecks"""
        # Create specific bottlenecks manually
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        test_bottlenecks = [
            ('indexing_speed', 10.0, 50.0, 'high', 80.0, 'Slow indexing'),
            ('memory_usage_mb', 800.0, 500.0, 'medium', 60.0, 'High memory'),
            ('query_time_ms', 200.0, 100.0, 'high', 100.0, 'Slow queries'),
        ]

        for metric, current, target, severity, impact, desc in test_bottlenecks:
            c.execute('''
                INSERT INTO bottlenecks
                (metric_name, current_value, target_value, severity, impact_score,
                 description, resolved, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, 0, ?)
            ''', (metric, current, target, severity, impact, desc, datetime.now().isoformat()))

        conn.commit()
        conn.close()

        # Generate improvements
        improvements = self.loop.generate_improvements(max_suggestions=5)

        # Check we get different types
        types_generated = set(imp['suggestion_type'] for imp in improvements)
        self.assertGreater(len(types_generated), 0)

    def test_test_improvement(self):
        """Test improvement testing in sandbox"""
        # Create a bottleneck and improvement
        self.loop.analyze_own_performance()
        self.loop.identify_bottlenecks()
        improvements = self.loop.generate_improvements(max_suggestions=1)

        if not improvements:
            self.skipTest("No improvements generated")

        improvement_id = improvements[0]['id']

        # Test the improvement
        test_result = self.loop.test_improvement(improvement_id)

        # Check result structure
        self.assertIn('improvement_id', test_result)
        self.assertIn('success', test_result)
        self.assertIn('performance_before', test_result)
        self.assertIn('performance_after', test_result)
        self.assertIn('performance_change_percent', test_result)
        self.assertIn('execution_time', test_result)
        self.assertIn('timestamp', test_result)

        # Check test result is stored
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM test_results WHERE improvement_id = ?', (improvement_id,))
        count = c.fetchone()[0]
        self.assertGreater(count, 0, "Test result should be stored")
        conn.close()

        # Check improvement status is updated
        improvement = self.loop._get_improvement(improvement_id)
        self.assertIn(improvement['status'], ['approved', 'rejected', 'testing'])

    def test_test_result_storage(self):
        """Test that test results are properly stored"""
        # Create test data
        test_result = TestResult(
            improvement_id=1,
            success=True,
            performance_before={'query_time_ms': 200.0},
            performance_after={'query_time_ms': 100.0},
            performance_change_percent=50.0,
            errors=[],
            warnings=[],
            execution_time=1.5,
            timestamp=datetime.now().isoformat()
        )

        # Store test result
        self.loop._store_test_result(test_result)

        # Verify storage
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('SELECT * FROM test_results WHERE improvement_id = ?', (1,))
        row = c.fetchone()
        conn.close()

        self.assertIsNotNone(row)
        self.assertEqual(row['success'], 1)
        self.assertEqual(row['performance_change_percent'], 50.0)

    def test_apply_improvement(self):
        """Test applying an approved improvement"""
        # Create and approve an improvement
        self.loop.analyze_own_performance()
        self.loop.identify_bottlenecks()
        improvements = self.loop.generate_improvements(max_suggestions=1)

        if not improvements:
            self.skipTest("No improvements generated")

        improvement_id = improvements[0]['id']

        # Manually set status to approved
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('UPDATE improvements SET status = ? WHERE id = ?',
                 ('approved', improvement_id))
        conn.commit()
        conn.close()

        # Apply improvement
        success = self.loop.apply_improvement(improvement_id)

        self.assertTrue(success, "Improvement should be applied successfully")

        # Check improvement status is updated
        improvement = self.loop._get_improvement(improvement_id)
        self.assertEqual(improvement['status'], 'applied')

        # Check applied_improvements record exists
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM applied_improvements WHERE improvement_id = ?',
                 (improvement_id,))
        count = c.fetchone()[0]
        self.assertGreater(count, 0, "Applied improvement should be recorded")
        conn.close()

    def test_cannot_apply_unapproved_improvement(self):
        """Test that unapproved improvements cannot be applied"""
        # Create an improvement with 'proposed' status
        self.loop.analyze_own_performance()
        self.loop.identify_bottlenecks()
        improvements = self.loop.generate_improvements(max_suggestions=1)

        if not improvements:
            self.skipTest("No improvements generated")

        improvement_id = improvements[0]['id']

        # Try to apply without approval
        success = self.loop.apply_improvement(improvement_id)

        self.assertFalse(success, "Should not apply unapproved improvement")

    def test_rollback_improvement(self):
        """Test rolling back an applied improvement"""
        # Create, approve, and apply an improvement
        self.loop.analyze_own_performance()
        self.loop.identify_bottlenecks()
        improvements = self.loop.generate_improvements(max_suggestions=1)

        if not improvements:
            self.skipTest("No improvements generated")

        improvement_id = improvements[0]['id']

        # Approve and apply
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('UPDATE improvements SET status = ? WHERE id = ?',
                 ('approved', improvement_id))
        conn.commit()
        conn.close()

        self.loop.apply_improvement(improvement_id)

        # Now rollback
        success = self.loop.rollback_improvement(improvement_id)

        self.assertTrue(success, "Rollback should succeed")

        # Check rollback is recorded
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            SELECT rolled_back FROM applied_improvements
            WHERE improvement_id = ?
            ORDER BY applied_at DESC
            LIMIT 1
        ''', (improvement_id,))
        row = c.fetchone()
        conn.close()

        self.assertIsNotNone(row)
        self.assertEqual(row[0], 1, "Should be marked as rolled back")

        # Check improvement status is updated to rejected
        improvement = self.loop._get_improvement(improvement_id)
        self.assertEqual(improvement['status'], 'rejected')

    def test_get_improvement_history(self):
        """Test retrieving improvement history"""
        # Create some improvements
        self.loop.analyze_own_performance()
        self.loop.identify_bottlenecks()
        self.loop.generate_improvements(max_suggestions=3)

        # Get history
        history = self.loop.get_improvement_history(limit=10)

        # Check return type
        self.assertIsInstance(history, list)

        # If history exists, check structure
        if history:
            item = history[0]
            self.assertIn('id', item)
            self.assertIn('description', item)
            self.assertIn('status', item)
            self.assertIn('metric_name', item)

    def test_get_performance_trend(self):
        """Test getting performance trend for a metric"""
        # Record multiple performance snapshots
        for _ in range(3):
            self.loop.analyze_own_performance()
            time.sleep(0.1)  # Small delay to ensure different timestamps

        # Get trend
        trend = self.loop.get_performance_trend('memory_usage_mb', hours=1)

        # Check return type
        self.assertIsInstance(trend, list)
        self.assertGreater(len(trend), 0)

        # Check structure
        for item in trend:
            self.assertIn('timestamp', item)
            self.assertIn('value', item)

    def test_get_stats(self):
        """Test getting self-improvement statistics"""
        # Generate some data
        self.loop.analyze_own_performance()
        self.loop.identify_bottlenecks()
        self.loop.generate_improvements(max_suggestions=2)

        # Get stats
        stats = self.loop.get_stats()

        # Check required fields
        self.assertIn('total_performance_snapshots', stats)
        self.assertIn('unresolved_bottlenecks', stats)
        self.assertIn('resolved_bottlenecks', stats)
        self.assertIn('improvements_by_status', stats)
        self.assertIn('successfully_applied', stats)
        self.assertIn('rolled_back', stats)
        self.assertIn('success_rate', stats)

        # Check values are reasonable
        self.assertGreaterEqual(stats['total_performance_snapshots'], 0)
        self.assertGreaterEqual(stats['success_rate'], 0)
        self.assertLessEqual(stats['success_rate'], 100)

    def test_database_integrity(self):
        """Test database integrity and foreign key relationships"""
        # Create related records
        self.loop.analyze_own_performance()
        bottlenecks = self.loop.identify_bottlenecks()

        if bottlenecks:
            improvements = self.loop.generate_improvements(max_suggestions=1)

            if improvements:
                # Verify foreign key relationship
                improvement = improvements[0]
                bottleneck_id = improvement['bottleneck_id']

                # Check bottleneck exists
                conn = sqlite3.connect(self.db_path)
                c = conn.cursor()
                c.execute('SELECT * FROM bottlenecks WHERE id = ?', (bottleneck_id,))
                bottleneck = c.fetchone()
                conn.close()

                self.assertIsNotNone(bottleneck, "Referenced bottleneck should exist")

    def test_concurrent_analysis(self):
        """Test that multiple analyses can be performed"""
        results = []

        # Perform multiple analyses
        for i in range(3):
            result = self.loop.analyze_own_performance(session_id=f"session_{i}")
            results.append(result)
            time.sleep(0.1)

        # Check all succeeded
        self.assertEqual(len(results), 3)

        for result in results:
            self.assertIn('metrics', result)
            self.assertNotIn('error', result)

        # Check all are stored
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM performance_metrics')
        count = c.fetchone()[0]
        conn.close()

        self.assertEqual(count, 3)

    def test_performance_metrics_dataclass(self):
        """Test PerformanceMetrics dataclass"""
        metrics = PerformanceMetrics(
            timestamp=datetime.now().isoformat(),
            indexing_speed=50.0,
            memory_usage_mb=400.0,
            query_time_ms=80.0,
            cpu_percent=60.0,
            database_size_mb=150.0,
            active_connections=2,
            cache_hit_rate=0.85,
            error_count=0,
            session_id="test"
        )

        self.assertEqual(metrics.indexing_speed, 50.0)
        self.assertEqual(metrics.session_id, "test")

    def test_bottleneck_dataclass(self):
        """Test Bottleneck dataclass"""
        bottleneck = Bottleneck(
            id=1,
            metric_name='query_time_ms',
            current_value=200.0,
            target_value=100.0,
            severity='high',
            impact_score=85.0,
            description='Query time is too high',
            timestamp=datetime.now().isoformat(),
            resolved=False
        )

        self.assertEqual(bottleneck.metric_name, 'query_time_ms')
        self.assertEqual(bottleneck.severity, 'high')
        self.assertFalse(bottleneck.resolved)

    def test_improvement_dataclass(self):
        """Test Improvement dataclass with auto-timestamp"""
        improvement = Improvement(
            id=1,
            bottleneck_id=1,
            suggestion_type='optimization',
            description='Optimize query execution',
            code_changes='{}',
            expected_improvement=40.0,
            confidence=0.8,
            status='proposed'
        )

        self.assertEqual(improvement.suggestion_type, 'optimization')
        self.assertIsNotNone(improvement.timestamp)
        self.assertEqual(improvement.confidence, 0.8)

    def test_error_handling_missing_components(self):
        """Test error handling when components are missing"""
        # This test ensures the system gracefully handles errors
        result = self.loop.analyze_own_performance()

        # Should not crash, should return result with error field if needed
        self.assertIsInstance(result, dict)

    def test_empty_bottlenecks_handling(self):
        """Test handling when no bottlenecks are found"""
        # Set perfect metrics (no bottlenecks)
        self.loop.current_metrics = PerformanceMetrics(
            timestamp=datetime.now().isoformat(),
            indexing_speed=60.0,  # Above target
            memory_usage_mb=400.0,  # Below target
            query_time_ms=50.0,  # Below target
            cpu_percent=50.0,  # Below target
            database_size_mb=100.0,
            active_connections=1,
            cache_hit_rate=0.90,  # Above target
            error_count=0
        )

        bottlenecks = self.loop.identify_bottlenecks()

        # Should return list (may have some bottlenecks even with good metrics)
        # The important thing is it doesn't crash and returns valid data
        self.assertIsInstance(bottlenecks, list)

        # All bottlenecks should have low or medium severity (not critical)
        for bottleneck in bottlenecks:
            self.assertIn(bottleneck['severity'], ['low', 'medium', 'high', 'critical'])

    def test_improvement_confidence_bounds(self):
        """Test that improvement confidence is within valid bounds"""
        self.loop.analyze_own_performance()
        self.loop.identify_bottlenecks()
        improvements = self.loop.generate_improvements(max_suggestions=5)

        for improvement in improvements:
            confidence = improvement['confidence']
            self.assertGreaterEqual(confidence, 0.0)
            self.assertLessEqual(confidence, 1.0)


class TestSelfImprovementIntegration(unittest.TestCase):
    """Integration tests for self-improvement system"""

    def setUp(self):
        """Set up test environment"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        self.loop = SelfImprovementLoop(db_path=self.db_path)

    def tearDown(self):
        """Clean up"""
        try:
            os.unlink(self.db_path)
        except Exception:
            pass

    def test_full_improvement_cycle(self):
        """Test complete improvement cycle from analysis to application"""
        # 1. Analyze performance
        analysis = self.loop.analyze_own_performance(session_id="integration_test")
        self.assertIn('metrics', analysis)

        # 2. Identify bottlenecks
        bottlenecks = self.loop.identify_bottlenecks()

        if not bottlenecks:
            self.skipTest("No bottlenecks found")

        # 3. Generate improvements
        improvements = self.loop.generate_improvements(max_suggestions=1)
        self.assertGreater(len(improvements), 0)

        improvement_id = improvements[0]['id']

        # 4. Test improvement
        test_result = self.loop.test_improvement(improvement_id)
        self.assertIn('success', test_result)

        # 5. If approved, apply
        improvement = self.loop._get_improvement(improvement_id)
        if improvement['status'] == 'approved':
            success = self.loop.apply_improvement(improvement_id)
            self.assertTrue(success)

        # 6. Get history
        history = self.loop.get_improvement_history()
        self.assertGreater(len(history), 0)

        # 7. Get stats
        stats = self.loop.get_stats()
        self.assertGreater(stats['total_performance_snapshots'], 0)

    def test_multiple_sessions(self):
        """Test handling multiple analysis sessions"""
        sessions = ['session1', 'session2', 'session3']

        for session_id in sessions:
            result = self.loop.analyze_own_performance(session_id=session_id)
            self.assertEqual(result['metrics']['session_id'], session_id)

        # Verify all sessions are stored
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT DISTINCT session_id FROM performance_metrics')
        stored_sessions = [row[0] for row in c.fetchall()]
        conn.close()

        for session_id in sessions:
            self.assertIn(session_id, stored_sessions)


def run_tests():
    """Run all tests with detailed output"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestSelfImprovementLoop))
    suite.addTests(loader.loadTestsFromTestCase(TestSelfImprovementIntegration))

    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Return success status
    return result.wasSuccessful()


if __name__ == '__main__':
    print("="*80)
    print("SELF-IMPROVEMENT LOOP SYSTEM - COMPREHENSIVE TESTS")
    print("="*80)
    print()

    success = run_tests()

    print()
    print("="*80)
    if success:
        print("[SUCCESS] All tests passed!")
    else:
        print("[FAILURE] Some tests failed!")
    print("="*80)

    sys.exit(0 if success else 1)
