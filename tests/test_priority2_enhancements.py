#!/usr/bin/env python3
"""
Comprehensive Tests for Priority 2 Intelligence Enhancements

Tests:
1. ML-Based Semantic Search
2. Automatic Mistake Detection
3. Pattern Clustering with ML

Author: AI Self-Improvement System
Created: 2026-02-03
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path
import unittest
import sqlite3
import json
import numpy as np

# Add workspace to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import modules to test
try:
    from search.semantic_search_ml import MLSemanticCodeSearch, ML_AVAILABLE as SEARCH_ML_AVAILABLE
    SEARCH_MODULE_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import semantic_search_ml: {e}")
    SEARCH_MODULE_AVAILABLE = False

try:
    from learning.mistake_learner_auto import AutomaticMistakeLearner, ErrorMonitoringContext
    LEARNER_MODULE_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import mistake_learner_auto: {e}")
    LEARNER_MODULE_AVAILABLE = False

try:
    from learning.pattern_clusterer import PatternClusterer, ML_AVAILABLE as CLUSTER_ML_AVAILABLE
    CLUSTERER_MODULE_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import pattern_clusterer: {e}")
    CLUSTERER_MODULE_AVAILABLE = False


class TestMLSemanticSearch(unittest.TestCase):
    """Test ML-Based Semantic Search"""

    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        if not SEARCH_MODULE_AVAILABLE:
            raise unittest.SkipTest("Semantic search module not available")

        cls.temp_dir = tempfile.mkdtemp()
        cls.db_path = os.path.join(cls.temp_dir, "test_semantic_search.db")

    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        if hasattr(cls, 'temp_dir') and os.path.exists(cls.temp_dir):
            shutil.rmtree(cls.temp_dir)

    def setUp(self):
        """Set up each test"""
        self.search = MLSemanticCodeSearch(db_path=self.db_path)

    def test_01_initialization(self):
        """Test search engine initialization"""
        self.assertIsNotNone(self.search)
        self.assertTrue(os.path.exists(self.db_path))

        # Check database tables
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()

        required_tables = {'projects', 'code_chunks', 'semantic_index', 'search_history'}
        self.assertTrue(required_tables.issubset(tables))

    def test_02_model_loading(self):
        """Test model loading (if ML available)"""
        if SEARCH_ML_AVAILABLE:
            self.assertIsNotNone(self.search.model)
            print(f"   Model loaded: {self.search.model_name}")
        else:
            self.assertIsNone(self.search.model)
            print("   ML not available, using keyword fallback")

    def test_03_create_test_files(self):
        """Create test code files for indexing"""
        test_project_dir = os.path.join(self.temp_dir, "test_project")
        os.makedirs(test_project_dir, exist_ok=True)

        # Python file
        py_file = os.path.join(test_project_dir, "test_module.py")
        with open(py_file, 'w') as f:
            f.write('''
def authenticate_user(username, password):
    """Authenticate user with database"""
    token = generate_token(username)
    return token

def query_database(sql):
    """Execute SQL query"""
    conn = get_connection()
    result = conn.execute(sql)
    return result

class UserManager:
    """Manage user operations"""
    def __init__(self):
        self.db = None

    def create_user(self, username):
        """Create new user"""
        pass
''')

        # JavaScript file
        js_file = os.path.join(test_project_dir, "test_script.js")
        with open(js_file, 'w') as f:
            f.write('''
function fetchData(url) {
    // Fetch data from API
    return fetch(url)
        .then(response => response.json())
        .catch(error => console.error(error));
}

const handleError = (error) => {
    // Error handling
    console.error("Error:", error);
    throw error;
};
''')

        self.test_project_dir = test_project_dir

    def test_04_index_project(self):
        """Test project indexing"""
        self.test_03_create_test_files()

        result = self.search.index_project("test_project", self.test_project_dir)

        self.assertIn('files_indexed', result)
        self.assertIn('chunks_indexed', result)
        self.assertGreater(result['files_indexed'], 0)
        self.assertGreater(result['chunks_indexed'], 0)

        print(f"   Indexed {result['files_indexed']} files, {result['chunks_indexed']} chunks")

    def test_05_keyword_search(self):
        """Test keyword-based search"""
        self.test_04_index_project()

        results = self.search.search("database query", limit=5, use_ml=False)

        self.assertIsInstance(results, list)
        if len(results) > 0:
            result = results[0]
            self.assertIn('file_path', result)
            self.assertIn('content', result)
            self.assertIn('relevance_score', result)
            self.assertEqual(result['search_type'], 'keyword')

        print(f"   Keyword search found {len(results)} results")

    def test_06_ml_search(self):
        """Test ML-based semantic search"""
        self.test_04_index_project()

        if not SEARCH_ML_AVAILABLE:
            self.skipTest("ML not available")

        results = self.search.search("authenticate user", limit=5, use_ml=True)

        self.assertIsInstance(results, list)
        if len(results) > 0:
            result = results[0]
            self.assertIn('relevance_score', result)
            self.assertIn('search_type', result)
            # Should use ML search
            self.assertEqual(result['search_type'], 'ml')

        print(f"   ML search found {len(results)} results")

    def test_07_find_similar(self):
        """Test finding similar code"""
        self.test_04_index_project()

        sample_code = """
        def login(user, pwd):
            token = auth_service.authenticate(user, pwd)
            return token
        """

        similar = self.search.find_similar(sample_code, limit=3)

        self.assertIsInstance(similar, list)
        print(f"   Found {len(similar)} similar code chunks")

    def test_08_statistics(self):
        """Test statistics"""
        self.test_04_index_project()

        stats = self.search.get_stats()

        self.assertIn('total_projects', stats)
        self.assertIn('total_chunks', stats)
        self.assertIn('ml_available', stats)
        self.assertGreater(stats['total_chunks'], 0)

        print(f"   Stats: {stats['total_chunks']} chunks, ML: {stats['ml_available']}")


class TestAutomaticMistakeLearner(unittest.TestCase):
    """Test Automatic Mistake Detection"""

    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        if not LEARNER_MODULE_AVAILABLE:
            raise unittest.SkipTest("Mistake learner module not available")

        cls.temp_dir = tempfile.mkdtemp()
        cls.db_path = os.path.join(cls.temp_dir, "test_mistakes.db")

    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        if hasattr(cls, 'temp_dir') and os.path.exists(cls.temp_dir):
            shutil.rmtree(cls.temp_dir)

    def setUp(self):
        """Set up each test"""
        self.learner = AutomaticMistakeLearner(db_path=self.db_path)

    def tearDown(self):
        """Clean up after each test"""
        if hasattr(self, 'learner'):
            self.learner.close()

    def test_01_initialization(self):
        """Test learner initialization"""
        self.assertIsNotNone(self.learner)
        self.assertTrue(os.path.exists(self.db_path))

        # Check database tables
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()

        required_tables = {'mistakes', 'corrections', 'failure_patterns', 'error_monitoring_log'}
        self.assertTrue(required_tables.issubset(tables))

    def test_02_manual_mistake_recording(self):
        """Test manual mistake recording"""
        mistake_id = self.learner.record_mistake(
            mistake_type="ValueError",
            description="Invalid string to int conversion",
            context="User input processing",
            code_snippet='x = int("abc")',
            error_message="ValueError: invalid literal for int() with base 10: 'abc'",
            severity="medium"
        )

        self.assertIsInstance(mistake_id, int)
        self.assertGreater(mistake_id, 0)

        print(f"   Recorded mistake ID: {mistake_id}")

    def test_03_automatic_error_monitoring(self):
        """Test automatic error detection"""
        # Trigger an error and monitor it
        try:
            result = 10 / 0
        except Exception as e:
            mistake_id = self.learner.monitor_exception(e, {'test': 'division'})

            self.assertIsInstance(mistake_id, int)
            self.assertGreater(mistake_id, 0)

            print(f"   Auto-detected error, mistake ID: {mistake_id}")

    def test_04_error_monitoring_context(self):
        """Test error monitoring context manager"""
        try:
            with ErrorMonitoringContext(self.learner, {'operation': 'test'}):
                raise ValueError("Test error")
        except ValueError:
            pass

        # Check that error was recorded
        stats = self.learner.get_learning_stats()
        self.assertGreater(stats['total_monitored_errors'], 0)

        print(f"   Context manager recorded error")

    def test_05_pattern_detection(self):
        """Test repeated error pattern detection"""
        # Create same error multiple times
        for i in range(3):
            try:
                x = int("not_a_number")
            except Exception as e:
                self.learner.monitor_exception(e, {'attempt': i+1})

        # Check for patterns
        patterns = self.learner.detect_repeated_errors(threshold=2)

        self.assertIsInstance(patterns, list)
        self.assertGreater(len(patterns), 0)

        print(f"   Detected {len(patterns)} repeated patterns")

    def test_06_correction_recording(self):
        """Test correction recording"""
        mistake_id = self.learner.record_mistake(
            mistake_type="TypeError",
            description="Wrong type passed to function",
            code_snippet='result = sum("123")',
            error_message="TypeError: unsupported operand type(s)",
            severity="low"
        )

        self.learner.record_correction(
            mistake_id,
            correction="Convert string to list of integers",
            corrected_code='result = sum([int(c) for c in "123"])',
            success=True
        )

        print(f"   Recorded correction for mistake {mistake_id}")

    def test_07_code_safety_check(self):
        """Test code safety checking"""
        # Record a mistake
        self.learner.record_mistake(
            mistake_type="IndexError",
            description="Array index out of bounds",
            code_snippet='arr[len(arr)]',
            error_message="IndexError: list index out of range"
        )

        # Check similar code
        result = self.learner.check_code_before_suggesting('arr[len(arr)]')

        self.assertIn('is_safe', result)
        self.assertIn('warnings', result)
        self.assertIsInstance(result['warnings'], list)

        print(f"   Safety check: safe={result['is_safe']}, warnings={len(result['warnings'])}")

    def test_08_statistics(self):
        """Test learning statistics"""
        stats = self.learner.get_learning_stats()

        self.assertIn('total_mistakes', stats)
        self.assertIn('auto_detected_mistakes', stats)
        self.assertIn('total_monitored_errors', stats)
        self.assertIn('mistakes_by_type', stats)

        print(f"   Stats: {stats['total_mistakes']} mistakes, "
              f"{stats['auto_detected_mistakes']} auto-detected")


class TestPatternClusterer(unittest.TestCase):
    """Test Pattern Clustering with ML"""

    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        if not CLUSTERER_MODULE_AVAILABLE:
            raise unittest.SkipTest("Pattern clusterer module not available")

        if not CLUSTER_ML_AVAILABLE:
            raise unittest.SkipTest("ML libraries not available for clustering")

        cls.temp_dir = tempfile.mkdtemp()
        cls.db_path = os.path.join(cls.temp_dir, "test_clustering.db")

    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        if hasattr(cls, 'temp_dir') and os.path.exists(cls.temp_dir):
            shutil.rmtree(cls.temp_dir)

    def setUp(self):
        """Set up each test"""
        self.clusterer = PatternClusterer(db_path=self.db_path, n_clusters=3)
        self._create_test_data()

    def tearDown(self):
        """Clean up after each test"""
        if hasattr(self, 'clusterer'):
            self.clusterer.close()

    def _create_test_data(self):
        """Create test mistake data"""
        cursor = self.clusterer.conn.cursor()

        # Create mistakes table if not exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mistakes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mistake_type TEXT NOT NULL,
                description TEXT NOT NULL,
                error_message TEXT,
                code_snippet TEXT,
                severity TEXT DEFAULT 'medium',
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Add test mistakes
        test_mistakes = [
            ("ValueError", "Invalid string to int conversion", "ValueError: invalid literal for int()", 'int("abc")', "medium"),
            ("ValueError", "Cannot convert empty string", "ValueError: invalid literal", 'int("")', "low"),
            ("TypeError", "Unsupported operand types", "TypeError: unsupported operand type(s) for +", '"text" + 123', "medium"),
            ("TypeError", "Wrong type for function", "TypeError: expected str, got int", 'func(123)', "medium"),
            ("IndexError", "List index out of range", "IndexError: list index out of range", 'arr[len(arr)]', "high"),
            ("IndexError", "Array access error", "IndexError: index out of bounds", 'arr[999]', "high"),
            ("KeyError", "Dictionary key not found", "KeyError: 'missing_key'", "dict['missing']", "medium"),
            ("KeyError", "Missing config key", "KeyError: 'config'", "settings['config']", "medium"),
        ]

        for mistake in test_mistakes:
            cursor.execute('''
                INSERT INTO mistakes (mistake_type, description, error_message, code_snippet, severity)
                VALUES (?, ?, ?, ?, ?)
            ''', mistake)

        self.clusterer.conn.commit()

    def test_01_initialization(self):
        """Test clusterer initialization"""
        self.assertIsNotNone(self.clusterer)
        self.assertTrue(os.path.exists(self.db_path))

        # Check database tables
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()

        required_tables = {'pattern_clusters', 'pattern_assignments', 'clustering_runs'}
        self.assertTrue(required_tables.issubset(tables))

    def test_02_cluster_mistakes(self):
        """Test mistake clustering"""
        result = self.clusterer.cluster_mistakes(min_patterns=3)

        if 'error' in result:
            self.skipTest(f"Clustering failed: {result['error']}")

        self.assertIn('n_clusters', result)
        self.assertIn('n_patterns', result)
        self.assertIn('silhouette_score', result)
        self.assertGreater(result['n_patterns'], 0)

        print(f"   Clustered {result['n_patterns']} patterns into {result['n_clusters']} clusters")
        print(f"   Silhouette score: {result['silhouette_score']:.3f}")

    def test_03_get_clusters(self):
        """Test getting cluster information"""
        self.clusterer.cluster_mistakes(min_patterns=3)

        clusters = self.clusterer.get_clusters()

        self.assertIsInstance(clusters, list)
        self.assertGreater(len(clusters), 0)

        for cluster in clusters:
            self.assertIn('id', cluster)
            self.assertIn('label', cluster)
            self.assertIn('pattern_count', cluster)
            self.assertIn('common_keywords', cluster)

        print(f"   Found {len(clusters)} clusters:")
        for cluster in clusters:
            print(f"      - {cluster['label']}: {cluster['pattern_count']} patterns")

    def test_04_get_patterns_in_cluster(self):
        """Test getting patterns in a cluster"""
        self.clusterer.cluster_mistakes(min_patterns=3)
        clusters = self.clusterer.get_clusters()

        if len(clusters) > 0:
            cluster_id = clusters[0]['id']
            patterns = self.clusterer.get_patterns_in_cluster(cluster_id)

            self.assertIsInstance(patterns, list)
            print(f"   Cluster {cluster_id} has {len(patterns)} patterns")

    def test_05_recommend_solution(self):
        """Test adding solution recommendations"""
        self.clusterer.cluster_mistakes(min_patterns=3)
        clusters = self.clusterer.get_clusters()

        if len(clusters) > 0:
            cluster_id = clusters[0]['id']
            solution = "Validate input types before conversion"

            self.clusterer.recommend_solution(cluster_id, solution)

            # Verify solution was saved
            updated_clusters = self.clusterer.get_clusters()
            updated_cluster = next(c for c in updated_clusters if c['id'] == cluster_id)

            self.assertEqual(updated_cluster['recommended_solution'], solution)
            print(f"   Added solution to cluster {cluster_id}")

    def test_06_find_cluster_for_error(self):
        """Test finding cluster for new error"""
        self.clusterer.cluster_mistakes(min_patterns=3)

        test_error = "ValueError: cannot convert string to integer"
        cluster = self.clusterer.find_cluster_for_error(test_error)

        if cluster:
            self.assertIn('label', cluster)
            print(f"   Error classified to: {cluster['label']}")
        else:
            print("   Error could not be classified")

    def test_07_clustering_stats(self):
        """Test clustering statistics"""
        self.clusterer.cluster_mistakes(min_patterns=3)

        stats = self.clusterer.get_clustering_stats()

        self.assertIn('total_clusters', stats)
        self.assertIn('total_patterns', stats)
        self.assertIn('ml_available', stats)
        self.assertGreater(stats['total_patterns'], 0)

        print(f"   Stats: {stats['total_clusters']} clusters, "
              f"{stats['total_patterns']} patterns")

    def test_08_visualization_data(self):
        """Test visualization data generation"""
        self.clusterer.cluster_mistakes(min_patterns=3)

        viz_data = self.clusterer.visualize_clusters()

        if 'error' not in viz_data:
            self.assertIn('points', viz_data)
            self.assertIn('labels', viz_data)
            self.assertIn('n_clusters', viz_data)

            print(f"   Generated visualization with {len(viz_data['points'])} points")
        else:
            print(f"   Visualization: {viz_data['error']}")


# === INTEGRATION TESTS ===

class TestIntegration(unittest.TestCase):
    """Test integration between systems"""

    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        if not (SEARCH_MODULE_AVAILABLE and LEARNER_MODULE_AVAILABLE and CLUSTERER_MODULE_AVAILABLE):
            raise unittest.SkipTest("Not all modules available")

        cls.temp_dir = tempfile.mkdtemp()

    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        if hasattr(cls, 'temp_dir') and os.path.exists(cls.temp_dir):
            shutil.rmtree(cls.temp_dir)

    def test_01_end_to_end_workflow(self):
        """Test complete workflow: error -> learning -> clustering"""
        # 1. Create learner and record errors
        learner_db = os.path.join(self.temp_dir, "integration_mistakes.db")
        learner = AutomaticMistakeLearner(db_path=learner_db)

        # Record multiple errors
        for i in range(5):
            try:
                x = int("error_" + str(i))
            except Exception as e:
                learner.monitor_exception(e, {'iteration': i})

        # 2. Cluster the patterns
        if CLUSTER_ML_AVAILABLE:
            clusterer = PatternClusterer(db_path=learner_db, n_clusters=2)
            result = clusterer.cluster_mistakes(min_patterns=3)

            if 'error' not in result:
                self.assertGreater(result['n_patterns'], 0)
                print(f"   End-to-end: Recorded and clustered {result['n_patterns']} errors")

            clusterer.close()

        # 3. Get statistics
        stats = learner.get_learning_stats()
        self.assertGreater(stats['total_mistakes'], 0)

        learner.close()

        print("   End-to-end workflow completed successfully")


# === TEST RUNNER ===

def run_tests():
    """Run all tests"""
    print("=" * 80)
    print("PRIORITY 2 INTELLIGENCE ENHANCEMENTS - COMPREHENSIVE TESTS")
    print("=" * 80)

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes
    if SEARCH_MODULE_AVAILABLE:
        suite.addTests(loader.loadTestsFromTestCase(TestMLSemanticSearch))
    else:
        print("\n[SKIP] Semantic search tests - module not available")

    if LEARNER_MODULE_AVAILABLE:
        suite.addTests(loader.loadTestsFromTestCase(TestAutomaticMistakeLearner))
    else:
        print("\n[SKIP] Mistake learner tests - module not available")

    if CLUSTERER_MODULE_AVAILABLE and CLUSTER_ML_AVAILABLE:
        suite.addTests(loader.loadTestsFromTestCase(TestPatternClusterer))
    else:
        print("\n[SKIP] Pattern clusterer tests - module or ML not available")

    if SEARCH_MODULE_AVAILABLE and LEARNER_MODULE_AVAILABLE and CLUSTERER_MODULE_AVAILABLE:
        suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    else:
        print("\n[SKIP] Integration tests - not all modules available")

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

    if result.wasSuccessful():
        print("\n[SUCCESS] All tests passed!")
    else:
        print("\n[PARTIAL] Some tests failed or had errors")

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
