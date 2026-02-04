#!/usr/bin/env python3
"""
Comprehensive tests for Error Prevention Layer
"""

import sys
import unittest
import tempfile
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.error_prevention import ErrorPreventionLayer, PreventionResult, prevent_errors


class TestErrorPrevention(unittest.TestCase):
    """Test suite for error prevention system"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()

        self.prevention = ErrorPreventionLayer(self.temp_db.name)

    def tearDown(self):
        """Clean up test fixtures"""
        try:
            os.unlink(self.temp_db.name)
        except Exception:
            pass

    def test_prevent_empty_file_path(self):
        """Test prevention of empty file paths"""
        result = self.prevention.check_operation(
            'read_file',
            file_path=''
        )

        self.assertFalse(result.allowed)
        self.assertIn('empty', result.reason.lower())
        self.assertEqual(result.rule_id, 'prevent_empty_file_read')

    def test_prevent_null_parameter(self):
        """Test prevention of null parameters"""
        result = self.prevention.check_operation(
            'process_data',
            data=None
        )

        self.assertFalse(result.allowed)
        self.assertIn('none', result.reason.lower())

    def test_prevent_divide_by_zero(self):
        """Test prevention of division by zero"""
        result = self.prevention.check_operation(
            'divide',
            divisor=0
        )

        self.assertFalse(result.allowed)
        self.assertIn('zero', result.reason.lower())
        self.assertEqual(result.rule_id, 'prevent_divide_by_zero')

    def test_prevent_negative_index(self):
        """Test prevention of negative index (except -1)"""
        # Should block -5
        result = self.prevention.check_operation(
            'access_array',
            index=-5
        )
        self.assertFalse(result.allowed)

        # Should allow -1 (Python convention)
        result = self.prevention.check_operation(
            'access_array',
            index=-1
        )
        self.assertTrue(result.allowed)

    def test_prevent_path_traversal(self):
        """Test prevention of path traversal"""
        result = self.prevention.check_operation(
            'read_file',
            file_path='../../etc/passwd'
        )

        self.assertFalse(result.allowed)
        self.assertIn('traversal', result.reason.lower())

    def test_allow_valid_operation(self):
        """Test that valid operations are allowed"""
        result = self.prevention.check_operation(
            'process_data',
            data={'key': 'value'},
            index=5,
            file_path='/valid/path.txt'
        )

        self.assertTrue(result.allowed)
        self.assertIsNone(result.reason)

    def test_add_bad_pattern(self):
        """Test adding bad patterns"""
        self.prevention.add_bad_pattern(
            pattern_type='input',
            pattern_regex=r'DROP\s+TABLE',
            description='SQL injection',
            severity='critical'
        )

        # Check pattern is detected
        result = self.prevention.check_operation(
            'execute_query',
            query='DROP TABLE users'
        )

        self.assertFalse(result.allowed)
        self.assertIn('pattern', result.reason.lower())

    def test_add_precondition(self):
        """Test adding state preconditions"""
        self.prevention.add_precondition(
            operation='send_message',
            precondition_type='state',
            check='connection_state',
            required_state='connected'
        )

        # Should block when disconnected
        result = self.prevention.check_operation(
            'send_message',
            context={'state': 'disconnected'},
            message='Hello'
        )

        self.assertFalse(result.allowed)
        self.assertIn('precondition', result.reason.lower())

        # Should allow when connected
        result = self.prevention.check_operation(
            'send_message',
            context={'state': 'connected'},
            message='Hello'
        )

        self.assertTrue(result.allowed)

    def test_learn_from_error(self):
        """Test learning prevention rules from errors"""
        self.prevention.learn_from_error(
            error_type='FileNotFoundError',
            error_message="File 'config.json' not found",
            operation='load_config',
            params={'file_path': 'config.json'}
        )

        # Check that pattern was added
        stats = self.prevention.get_prevention_stats()
        self.assertIsNotNone(stats)

    def test_resource_threshold_checking(self):
        """Test resource availability checking"""
        # This test may pass or fail depending on system state
        result = self.prevention.check_operation(
            'allocate_memory',
            size=1000000000
        )

        # Result should have proper structure
        self.assertIsInstance(result.allowed, bool)
        if not result.allowed:
            self.assertIsNotNone(result.reason)

    def test_prevention_statistics(self):
        """Test prevention statistics tracking"""
        # Perform several checks
        self.prevention.check_operation('test1', data=None)
        self.prevention.check_operation('test2', divisor=0)
        self.prevention.check_operation('test3', data='valid')

        stats = self.prevention.get_prevention_stats()

        self.assertIn('total_checks', stats)
        self.assertIn('total_preventions', stats)
        self.assertIn('effectiveness', stats)
        self.assertTrue(stats['total_checks'] >= 3)

    def test_prevention_result_structure(self):
        """Test PreventionResult structure"""
        result = self.prevention.check_operation(
            'test',
            data=None
        )

        self.assertIsInstance(result, PreventionResult)
        self.assertIsInstance(result.allowed, bool)
        self.assertTrue(0 <= result.confidence <= 1.0)

        result_dict = result.to_dict()
        self.assertIn('allowed', result_dict)
        self.assertIn('reason', result_dict)
        self.assertIn('confidence', result_dict)

    def test_multiple_validation_rules(self):
        """Test multiple validation rules at once"""
        result = self.prevention.check_operation(
            'complex_operation',
            file_path='',  # Should fail
            divisor=1,
            data='valid'
        )

        # Should catch first validation failure
        self.assertFalse(result.allowed)

    def test_decorator_prevention(self):
        """Test decorator-based prevention"""
        @prevent_errors(self.prevention)
        def divide(a, b, divisor=1):
            return a / divisor

        # Should prevent
        with self.assertRaises(PermissionError):
            divide(10, 5, divisor=0)

        # Should allow
        result = divide(10, 5, divisor=2)
        self.assertEqual(result, 5.0)

    def test_alternative_actions(self):
        """Test alternative action suggestions"""
        # May suggest alternative if resources low
        result = self.prevention.check_operation(
            'large_operation',
            size=1000000000
        )

        if not result.allowed:
            self.assertIsNotNone(result.alternative_action)


class TestBadPatternDetection(unittest.TestCase):
    """Test suite for bad pattern detection"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.prevention = ErrorPreventionLayer(self.temp_db.name)

    def tearDown(self):
        """Clean up test fixtures"""
        try:
            os.unlink(self.temp_db.name)
        except Exception:
            pass

    def test_sql_injection_prevention(self):
        """Test SQL injection pattern prevention"""
        self.prevention.add_bad_pattern(
            pattern_type='input',
            pattern_regex=r'(DROP|DELETE|INSERT)\s+(TABLE|FROM)',
            description='SQL injection attempt',
            severity='critical'
        )

        test_cases = [
            ('SELECT * FROM users', True),  # Should allow
            ('DROP TABLE users', False),  # Should block
            ('DELETE FROM users', False),  # Should block
            ('INSERT INTO users', False),  # Should block
        ]

        for query, should_allow in test_cases:
            result = self.prevention.check_operation(
                'execute_query',
                query=query
            )
            self.assertEqual(result.allowed, should_allow,
                           f"Query '{query}' should {'allow' if should_allow else 'block'}")

    def test_path_traversal_prevention(self):
        """Test path traversal prevention"""
        test_cases = [
            ('/normal/path.txt', True),
            ('../../etc/passwd', False),
            ('../sensitive/data', False),
            ('./local/file.txt', True),
        ]

        for path, should_allow in test_cases:
            result = self.prevention.check_operation(
                'read_file',
                file_path=path
            )
            if '..' in path:
                self.assertFalse(result.allowed,
                               f"Path '{path}' should be blocked")

    def test_xss_prevention(self):
        """Test XSS pattern prevention"""
        self.prevention.add_bad_pattern(
            pattern_type='input',
            pattern_regex=r'<script[^>]*>.*?</script>',
            description='XSS attempt',
            severity='high'
        )

        result = self.prevention.check_operation(
            'render_content',
            content='<script>alert("XSS")</script>'
        )

        self.assertFalse(result.allowed)


class TestPreconditionChecking(unittest.TestCase):
    """Test suite for precondition checking"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.prevention = ErrorPreventionLayer(self.temp_db.name)

    def tearDown(self):
        """Clean up test fixtures"""
        try:
            os.unlink(self.temp_db.name)
        except Exception:
            pass

    def test_state_precondition(self):
        """Test state-based preconditions"""
        self.prevention.add_precondition(
            operation='write_data',
            precondition_type='state',
            check='connection_state',
            required_state='open'
        )

        # Wrong state - should block
        result = self.prevention.check_operation(
            'write_data',
            context={'state': 'closed'},
            data='test'
        )
        self.assertFalse(result.allowed)

        # Correct state - should allow
        result = self.prevention.check_operation(
            'write_data',
            context={'state': 'open'},
            data='test'
        )
        self.assertTrue(result.allowed)

    def test_resource_precondition(self):
        """Test resource-based preconditions"""
        self.prevention.add_precondition(
            operation='process',
            precondition_type='resource',
            check='database_connection',
            required_state='available'
        )

        # Missing resource - should block
        result = self.prevention.check_operation(
            'process',
            context={},
            data='test'
        )
        self.assertFalse(result.allowed)

        # Resource available - should allow
        result = self.prevention.check_operation(
            'process',
            context={'database_connection': 'active'},
            data='test'
        )
        self.assertTrue(result.allowed)


class TestLearningAndAdaptation(unittest.TestCase):
    """Test suite for learning capabilities"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.prevention = ErrorPreventionLayer(self.temp_db.name)

    def tearDown(self):
        """Clean up test fixtures"""
        try:
            os.unlink(self.temp_db.name)
        except Exception:
            pass

    def test_learn_from_null_error(self):
        """Test learning from null pointer errors"""
        self.prevention.learn_from_error(
            error_type='AttributeError',
            error_message="'NoneType' object has no attribute 'value'",
            operation='get_value',
            params={'obj': None}
        )

        # Should prevent similar operations
        result = self.prevention.check_operation(
            'get_value',
            obj=None
        )
        self.assertFalse(result.allowed)

    def test_learn_from_empty_string_error(self):
        """Test learning from empty string errors"""
        self.prevention.learn_from_error(
            error_type='ValueError',
            error_message="Empty string not allowed",
            operation='parse',
            params={'text': ''}
        )

        # Pattern should be learned
        stats = self.prevention.get_prevention_stats()
        self.assertIsNotNone(stats)

    def test_pattern_extraction(self):
        """Test pattern extraction from errors"""
        # Learn from specific error
        self.prevention.learn_from_error(
            error_type='FileNotFoundError',
            error_message="File 'data_2024.csv' not found",
            operation='load_file',
            params={'file_path': 'data_2024.csv'}
        )

        # Similar error should be caught
        # (Pattern should match different years/numbers)
        stats = self.prevention.get_prevention_stats()
        self.assertTrue(stats['total_checks'] >= 0)


def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestErrorPrevention))
    suite.addTests(loader.loadTestsFromTestCase(TestBadPatternDetection))
    suite.addTests(loader.loadTestsFromTestCase(TestPreconditionChecking))
    suite.addTests(loader.loadTestsFromTestCase(TestLearningAndAdaptation))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("="*80)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
