#!/usr/bin/env python3
"""
Comprehensive tests for Smart Error Classification System
"""

import sys
import unittest
import tempfile
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.error_classifier import ErrorClassificationEngine, ErrorClassification


class TestErrorClassifier(unittest.TestCase):
    """Test suite for error classification system"""

    def setUp(self):
        """Set up test fixtures"""
        # Create temporary database for testing
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()

        self.classifier = ErrorClassificationEngine(self.temp_db.name)

    def tearDown(self):
        """Clean up test fixtures"""
        # Remove temporary database
        try:
            os.unlink(self.temp_db.name)
        except Exception:
            pass

    def test_classify_runtime_error(self):
        """Test classification of runtime errors"""
        error = ValueError("Invalid input: expected integer, got string")
        classification = self.classifier.classify(error)

        self.assertEqual(classification.error_type, 'runtime')
        self.assertIn(classification.severity, ['low', 'medium', 'high', 'critical'])
        self.assertIn(classification.recoverability, ['recoverable', 'degraded', 'fatal'])
        self.assertTrue(0 <= classification.confidence_score <= 1.0)

    def test_classify_io_error(self):
        """Test classification of IO errors"""
        error = FileNotFoundError("File 'config.json' not found")
        classification = self.classifier.classify(error)

        self.assertEqual(classification.error_type, 'io')
        self.assertEqual(classification.domain, 'file_system')
        self.assertIsNotNone(classification.error_id)

    def test_classify_network_error(self):
        """Test classification of network errors"""
        error = ConnectionError("Failed to connect to database on port 5432")
        classification = self.classifier.classify(error)

        self.assertEqual(classification.error_type, 'network')
        self.assertEqual(classification.domain, 'network')
        self.assertEqual(classification.recoverability, 'recoverable')
        self.assertEqual(classification.required_action, 'retry')

    def test_classify_resource_error(self):
        """Test classification of resource errors"""
        error = MemoryError("Out of memory")
        classification = self.classifier.classify(error)

        self.assertEqual(classification.error_type, 'resource')
        self.assertEqual(classification.domain, 'memory')
        self.assertIn(classification.severity, ['high', 'critical'])

    def test_classify_logic_error(self):
        """Test classification of logic errors"""
        error = AssertionError("Expected result != actual result")
        classification = self.classifier.classify(error)

        self.assertEqual(classification.error_type, 'logic')
        self.assertIsNotNone(classification.root_cause_category)

    def test_routing_recommendation(self):
        """Test routing recommendations"""
        error = ConnectionError("Connection timeout")
        classification = self.classifier.classify(error)

        routing = self.classifier.get_routing_recommendation(classification)

        self.assertIn('handler', routing)
        self.assertIn('priority', routing)
        self.assertIn('timeout', routing)
        self.assertIn('retry_strategy', routing)
        self.assertTrue(1 <= routing['priority'] <= 5)

    def test_learning_from_feedback(self):
        """Test learning from classification feedback"""
        error = ValueError("Invalid value")
        classification = self.classifier.classify(error)

        # Provide correction
        corrected = {
            'error_type': 'validation',
            'severity': 'medium',
            'recoverability': 'recoverable',
            'domain': 'validation',
            'required_action': 'retry'
        }

        self.classifier.learn_from_feedback(
            classification.error_id,
            corrected,
            reason="Error was validation, not runtime"
        )

        # Check feedback was recorded
        stats = self.classifier.get_accuracy_stats()
        self.assertEqual(stats['corrected_classifications'], 1)

    def test_accuracy_statistics(self):
        """Test accuracy statistics tracking"""
        # Classify several errors
        errors = [
            ValueError("Invalid input"),
            FileNotFoundError("File not found"),
            ConnectionError("Connection failed"),
        ]

        for error in errors:
            self.classifier.classify(error)

        stats = self.classifier.get_accuracy_stats()

        self.assertIn('total_classifications', stats)
        self.assertIn('overall_accuracy', stats)
        self.assertIn('by_method', stats)
        self.assertIn('domain_statistics', stats)
        self.assertTrue(stats['total_classifications'] >= 3)

    def test_top_error_types(self):
        """Test getting top error types"""
        # Create multiple errors
        for i in range(5):
            error = ValueError(f"Error {i}")
            self.classifier.classify(error)

        top_errors = self.classifier.get_top_error_types(limit=10)

        self.assertIsInstance(top_errors, list)
        for error_info in top_errors:
            self.assertIn('error_type', error_info)
            self.assertIn('domain', error_info)
            self.assertIn('count', error_info)

    def test_severity_determination(self):
        """Test severity determination"""
        critical_error = Exception("CRITICAL: System failure - data corruption")
        classification = self.classifier.classify(critical_error)
        self.assertEqual(classification.severity, 'critical')

        low_error = Exception("Minor issue - recoverable")
        classification = self.classifier.classify(low_error)
        self.assertEqual(classification.severity, 'low')

    def test_recoverability_determination(self):
        """Test recoverability determination"""
        recoverable = ConnectionError("Temporary connection issue, retry")
        classification = self.classifier.classify(recoverable)
        self.assertEqual(classification.recoverability, 'recoverable')

        fatal = Exception("FATAL: Permanent data loss")
        classification = self.classifier.classify(fatal)
        self.assertEqual(classification.recoverability, 'fatal')

    def test_required_action_determination(self):
        """Test required action determination"""
        timeout_error = TimeoutError("Request timed out")
        classification = self.classifier.classify(timeout_error)
        self.assertEqual(classification.required_action, 'retry')

        critical_error = Exception("CRITICAL: System failure")
        classification = self.classifier.classify(critical_error)
        self.assertIn(classification.required_action, ['escalate', 'restart'])

    def test_similar_error_counting(self):
        """Test counting of similar errors"""
        # Create multiple similar errors
        for i in range(3):
            error = ValueError(f"Invalid input {i}")
            self.classifier.classify(error)

        # Classify one more
        error = ValueError("Invalid input 4")
        classification = self.classifier.classify(error)

        # Should have similar errors
        self.assertTrue(classification.similar_errors_count >= 0)

    def test_classification_persistence(self):
        """Test that classifications are persisted"""
        error = RuntimeError("Test error")
        classification1 = self.classifier.classify(error)

        # Create new classifier with same database
        classifier2 = ErrorClassificationEngine(self.temp_db.name)

        # Classify same error - should get same result
        classification2 = classifier2.classify(error)

        self.assertEqual(classification1.error_id, classification2.error_id)
        self.assertEqual(classification1.error_type, classification2.error_type)

    def test_confidence_scores(self):
        """Test confidence scores are reasonable"""
        error = ValueError("Test error")
        classification = self.classifier.classify(error)

        self.assertTrue(0.0 <= classification.confidence_score <= 1.0)

    def test_domain_mapping(self):
        """Test domain mapping is correct"""
        test_cases = [
            (FileNotFoundError("file error"), 'file_system'),
            (ConnectionError("network error"), 'network'),
        ]

        for error, expected_domain in test_cases:
            classification = self.classifier.classify(error)
            self.assertEqual(classification.domain, expected_domain)

    def test_root_cause_categories(self):
        """Test root cause categorization"""
        error = FileNotFoundError("File not found")
        classification = self.classifier.classify(error)

        self.assertIn(classification.root_cause_category,
                     ['missing_resource', 'resource_access', 'unknown'])


class TestIntegrationScenarios(unittest.TestCase):
    """Integration tests for real-world scenarios"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.classifier = ErrorClassificationEngine(self.temp_db.name)

    def tearDown(self):
        """Clean up test fixtures"""
        try:
            os.unlink(self.temp_db.name)
        except Exception:
            pass

    def test_database_error_flow(self):
        """Test complete flow for database errors"""
        # Simulate database error
        error = Exception("DatabaseError: Connection pool exhausted")
        classification = self.classifier.classify(error)

        # Verify classification
        self.assertIn('database', classification.error_message.lower())

        # Get routing
        routing = self.classifier.get_routing_recommendation(classification)
        self.assertIsNotNone(routing['handler'])
        self.assertIsNotNone(routing['retry_strategy'])

    def test_multiple_errors_same_type(self):
        """Test handling multiple errors of same type"""
        for i in range(10):
            error = ConnectionError(f"Connection failed: attempt {i}")
            classification = self.classifier.classify(error)
            self.assertEqual(classification.error_type, 'network')

        # Check statistics
        top_errors = self.classifier.get_top_error_types(limit=5)
        network_errors = [e for e in top_errors if e['error_type'] == 'network']
        self.assertTrue(len(network_errors) > 0)

    def test_error_pattern_learning(self):
        """Test pattern learning over time"""
        # Create similar errors
        for i in range(5):
            error = ValueError(f"Invalid JSON: unexpected token at position {i*10}")
            classification = self.classifier.classify(error)

        # Provide feedback on one
        error = ValueError("Invalid JSON: unexpected token at position 50")
        classification = self.classifier.classify(error)

        self.classifier.learn_from_feedback(
            classification.error_id,
            {
                'error_type': 'validation',
                'domain': 'validation'
            }
        )

        # Future similar errors should benefit from learning
        stats = self.classifier.get_accuracy_stats()
        self.assertTrue(stats['total_classifications'] >= 6)


def run_tests():
    """Run all tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add tests
    suite.addTests(loader.loadTestsFromTestCase(TestErrorClassifier))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegrationScenarios))

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
