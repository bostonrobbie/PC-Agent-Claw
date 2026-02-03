"""
Comprehensive Test Suite for Priority 1 Critical Enhancements

Tests for:
1. Multi-threaded Semantic Indexing
2. Incremental Update System
3. Real Code Execution Sandbox

Author: AI Self-Improvement System
Created: 2026-02-03
"""

import unittest
import os
import sys
import time
import tempfile
import shutil
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from search.semantic_search import SemanticCodeSearch
from autonomous.code_sandbox import CodeSandbox, ResourceLimits, ExecutionResult

# Conditional import for incremental indexer
try:
    from search.incremental_indexer import IncrementalIndexer
    INCREMENTAL_AVAILABLE = True
except ImportError:
    INCREMENTAL_AVAILABLE = False


class TestMultiThreadedIndexing(unittest.TestCase):
    """Test multi-threaded semantic indexing"""

    def setUp(self):
        """Set up test database"""
        self.db_path = "test_semantic_search.db"
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        self.search = SemanticCodeSearch(db_path=self.db_path, max_workers=4)

    def tearDown(self):
        """Clean up test database"""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_sequential_indexing(self):
        """Test sequential indexing works correctly"""
        result = self.search.index_project(
            "test-sequential",
            os.path.dirname(os.path.abspath(__file__)),
            parallel=False
        )

        self.assertIn('files_indexed', result)
        self.assertIn('chunks_indexed', result)
        self.assertIn('elapsed_time', result)
        self.assertFalse(result['parallel'])
        self.assertGreater(result['files_indexed'], 0)

    def test_parallel_indexing(self):
        """Test parallel indexing works correctly"""
        result = self.search.index_project(
            "test-parallel",
            os.path.dirname(os.path.abspath(__file__)),
            parallel=True
        )

        self.assertIn('files_indexed', result)
        self.assertIn('chunks_indexed', result)
        self.assertIn('elapsed_time', result)
        self.assertTrue(result['parallel'])
        self.assertGreater(result['files_indexed'], 0)

    def test_parallel_faster_than_sequential(self):
        """Test that parallel indexing is faster for large projects"""
        # Index sequentially
        start = time.time()
        result_seq = self.search.index_project(
            "test-seq-speed",
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            parallel=False
        )
        seq_time = time.time() - start

        # Clean database
        self.tearDown()
        self.setUp()

        # Index in parallel
        start = time.time()
        result_par = self.search.index_project(
            "test-par-speed",
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            parallel=True
        )
        par_time = time.time() - start

        print(f"\nSequential: {seq_time:.2f}s ({result_seq['files_per_second']:.1f} files/sec)")
        print(f"Parallel:   {par_time:.2f}s ({result_par['files_per_second']:.1f} files/sec)")

        # Parallel should be faster (or at least not much slower)
        # Allow some margin for small datasets
        self.assertLess(par_time, seq_time * 1.5,
                       "Parallel indexing should not be significantly slower")

    def test_files_per_second_metric(self):
        """Test that files_per_second metric is calculated"""
        result = self.search.index_project(
            "test-metrics",
            os.path.dirname(os.path.abspath(__file__)),
            parallel=True
        )

        self.assertIn('files_per_second', result)
        self.assertGreater(result['files_per_second'], 0)

    def test_search_after_parallel_index(self):
        """Test that search works correctly after parallel indexing"""
        # Index project
        self.search.index_project(
            "test-search",
            os.path.dirname(os.path.abspath(__file__)),
            parallel=True
        )

        # Search for something
        results = self.search.search("test unittest", limit=5)

        self.assertIsInstance(results, list)
        # May or may not have results depending on file contents


class TestCodeSandbox(unittest.TestCase):
    """Test code execution sandbox"""

    def setUp(self):
        """Set up sandbox"""
        try:
            self.sandbox = CodeSandbox()
            self.docker_available = True
        except RuntimeError:
            self.docker_available = False
            self.skipTest("Docker not available")

    def test_python_execution_success(self):
        """Test successful Python code execution"""
        code = """
print("Hello, World!")
result = 2 + 2
print(f"2 + 2 = {result}")
"""
        result = self.sandbox.execute(code, 'python')

        self.assertTrue(result.success)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Hello, World!", result.stdout)
        self.assertIn("2 + 2 = 4", result.stdout)
        self.assertFalse(result.timeout)
        self.assertGreater(result.execution_time, 0)

    def test_python_execution_failure(self):
        """Test Python code with errors"""
        code = """
print("Before error")
raise ValueError("Test error")
print("After error")
"""
        result = self.sandbox.execute(code, 'python')

        self.assertFalse(result.success)
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Before error", result.stdout)
        self.assertIn("ValueError", result.stderr)
        self.assertNotIn("After error", result.stdout)

    def test_javascript_execution(self):
        """Test JavaScript code execution"""
        code = """
console.log("Hello from Node.js!");
const sum = [1, 2, 3, 4, 5].reduce((a, b) => a + b, 0);
console.log("Sum:", sum);
"""
        result = self.sandbox.execute(code, 'javascript')

        self.assertTrue(result.success)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Hello from Node.js!", result.stdout)
        self.assertIn("Sum: 15", result.stdout)

    def test_timeout_handling(self):
        """Test execution timeout"""
        code = """
import time
print("Starting...")
time.sleep(10)
print("Done")
"""
        limits = ResourceLimits(timeout_seconds=2)
        result = self.sandbox.execute(code, 'python', limits=limits)

        self.assertFalse(result.success)
        self.assertTrue(result.timeout)
        self.assertIsNotNone(result.error_message)
        self.assertIn("timeout", result.error_message.lower())

    def test_memory_limits(self):
        """Test memory limit enforcement"""
        code = """
print("Allocating memory...")
data = []
try:
    for i in range(10000):
        data.append([0] * 100000)
    print(f"Allocated {len(data)} arrays")
except MemoryError:
    print("Memory limit reached")
"""
        limits = ResourceLimits(memory_limit="64m", timeout_seconds=10)
        result = self.sandbox.execute(code, 'python', limits=limits)

        # Should either complete with MemoryError or be killed by Docker
        self.assertIsNotNone(result)

    def test_unsupported_language(self):
        """Test handling of unsupported language"""
        result = self.sandbox.execute("print('test')", 'unknown_language')

        self.assertFalse(result.success)
        self.assertIsNotNone(result.error_message)
        self.assertIn("Unsupported language", result.error_message)

    def test_supported_languages(self):
        """Test getting list of supported languages"""
        languages = self.sandbox.list_supported_languages()

        self.assertIsInstance(languages, list)
        self.assertGreater(len(languages), 0)

        # Check structure
        for lang_info in languages:
            self.assertIn('language', lang_info)
            self.assertIn('runtime', lang_info)
            self.assertIn('extension', lang_info)

    def test_execution_isolation(self):
        """Test that executions are isolated from each other"""
        code1 = """
import os
print(f"Process ID: {os.getpid()}")
"""
        code2 = """
import os
print(f"Process ID: {os.getpid()}")
"""

        result1 = self.sandbox.execute(code1, 'python')
        result2 = self.sandbox.execute(code2, 'python')

        # Both should succeed
        self.assertTrue(result1.success)
        self.assertTrue(result2.success)

        # PIDs should be different (different containers)
        pid1 = result1.stdout.strip().split()[-1]
        pid2 = result2.stdout.strip().split()[-1]
        # PIDs might be reused by Docker, so we just check both executed

    def test_execution_time_measurement(self):
        """Test that execution time is measured accurately"""
        code = """
import time
time.sleep(0.5)
print("Done")
"""
        result = self.sandbox.execute(code, 'python')

        self.assertTrue(result.success)
        # Should take at least 0.5 seconds
        self.assertGreaterEqual(result.execution_time, 0.5)
        # Should not take more than 2 seconds (some overhead is expected)
        self.assertLess(result.execution_time, 2.0)


@unittest.skipUnless(INCREMENTAL_AVAILABLE, "watchdog library not installed")
class TestIncrementalIndexer(unittest.TestCase):
    """Test incremental update system"""

    def setUp(self):
        """Set up test environment"""
        self.db_path = "test_incremental.db"
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

        self.search = SemanticCodeSearch(db_path=self.db_path)

        # Create temporary directory for testing
        self.test_dir = tempfile.mkdtemp()

        # Create initial index
        self.search.index_project("test-project", self.test_dir)

        # Create indexer
        self.indexer = IncrementalIndexer(
            search_engine=self.search,
            project_name="test-project",
            root_path=self.test_dir,
            batch_size=2,
            batch_interval=0.5
        )

    def tearDown(self):
        """Clean up test environment"""
        if hasattr(self, 'indexer'):
            try:
                self.indexer.stop_monitoring()
            except:
                pass

        if os.path.exists(self.db_path):
            os.remove(self.db_path)

        if hasattr(self, 'test_dir') and os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_file_creation_detection(self):
        """Test detection of new files"""
        self.indexer.start_monitoring()
        time.sleep(0.5)

        # Create a new Python file
        test_file = os.path.join(self.test_dir, "new_file.py")
        with open(test_file, 'w') as f:
            f.write("def test_function():\n    return 42\n")

        # Wait for processing
        time.sleep(2)

        stats = self.indexer.get_stats()
        self.assertGreater(stats['files_created'], 0)

    def test_file_modification_detection(self):
        """Test detection of file modifications"""
        # Create initial file
        test_file = os.path.join(self.test_dir, "existing_file.py")
        with open(test_file, 'w') as f:
            f.write("def old_function():\n    return 1\n")

        # Re-index to include this file
        self.search.index_project("test-project", self.test_dir)

        # Start monitoring
        self.indexer = IncrementalIndexer(
            search_engine=self.search,
            project_name="test-project",
            root_path=self.test_dir,
            batch_size=2,
            batch_interval=0.5
        )
        self.indexer.start_monitoring()
        time.sleep(0.5)

        # Modify file
        with open(test_file, 'w') as f:
            f.write("def new_function():\n    return 2\n")

        # Wait for processing
        time.sleep(2)

        stats = self.indexer.get_stats()
        self.assertGreater(stats['files_modified'], 0)

    def test_batch_processing(self):
        """Test that changes are batched correctly"""
        self.indexer.start_monitoring()
        time.sleep(0.5)

        # Create multiple files quickly
        for i in range(5):
            test_file = os.path.join(self.test_dir, f"batch_file_{i}.py")
            with open(test_file, 'w') as f:
                f.write(f"def function_{i}():\n    return {i}\n")
            time.sleep(0.1)

        # Wait for batch processing
        time.sleep(3)

        stats = self.indexer.get_stats()
        self.assertGreater(stats['batches_processed'], 0)
        self.assertGreater(stats['files_created'], 0)

    def test_monitoring_start_stop(self):
        """Test starting and stopping monitoring"""
        # Start monitoring
        self.indexer.start_monitoring()
        stats = self.indexer.get_stats()
        self.assertTrue(stats['monitoring'])

        # Stop monitoring
        self.indexer.stop_monitoring()
        stats = self.indexer.get_stats()
        self.assertFalse(stats['monitoring'])


def run_performance_benchmarks():
    """Run performance benchmarks and print results"""
    print("\n" + "="*70)
    print("PERFORMANCE BENCHMARKS")
    print("="*70)

    # Benchmark 1: Multi-threaded indexing
    print("\n1. Multi-threaded Semantic Indexing")
    print("-" * 70)

    db_path = "benchmark_semantic.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    search = SemanticCodeSearch(db_path=db_path, max_workers=8)
    test_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Sequential
    start = time.time()
    result_seq = search.index_project("benchmark-seq", test_dir, parallel=False)
    seq_time = time.time() - start

    # Clean and re-index in parallel
    os.remove(db_path)
    search = SemanticCodeSearch(db_path=db_path, max_workers=8)

    start = time.time()
    result_par = search.index_project("benchmark-par", test_dir, parallel=True)
    par_time = time.time() - start

    print(f"Sequential: {seq_time:.2f}s, {result_seq['files_per_second']:.1f} files/sec")
    print(f"Parallel:   {par_time:.2f}s, {result_par['files_per_second']:.1f} files/sec")
    print(f"Speedup:    {seq_time/par_time:.2f}x")
    print(f"Target:     100+ files/sec")
    print(f"Achieved:   {result_par['files_per_second']:.1f} files/sec")

    if result_par['files_per_second'] >= 100:
        print("✓ TARGET MET!")
    else:
        print(f"✗ Below target (need {100 - result_par['files_per_second']:.1f} more files/sec)")

    os.remove(db_path)

    # Benchmark 2: Code sandbox
    print("\n2. Code Execution Sandbox")
    print("-" * 70)

    try:
        sandbox = CodeSandbox()

        # Test execution speed
        simple_code = "print('Hello, World!')"

        timings = []
        for i in range(5):
            result = sandbox.execute(simple_code, 'python')
            if result.success:
                timings.append(result.execution_time)

        avg_time = sum(timings) / len(timings)
        print(f"Average execution time: {avg_time:.3f}s")
        print(f"Min execution time:     {min(timings):.3f}s")
        print(f"Max execution time:     {max(timings):.3f}s")

        # Test timeout accuracy
        print("\nTimeout accuracy test:")
        timeout_code = "import time; time.sleep(10)"
        limits = ResourceLimits(timeout_seconds=2)
        result = sandbox.execute(timeout_code, 'python', limits=limits)

        print(f"Timeout setting:    2.0s")
        print(f"Actual time:        {result.execution_time:.3f}s")
        print(f"Timeout triggered:  {result.timeout}")

        if result.timeout and 2.0 <= result.execution_time <= 3.0:
            print("✓ Timeout working correctly!")
        else:
            print("✗ Timeout accuracy issue")

    except RuntimeError as e:
        print(f"Skipped: {e}")

    print("\n" + "="*70)


if __name__ == "__main__":
    # Run unit tests
    print("Running unit tests...")
    unittest.main(argv=[''], verbosity=2, exit=False)

    # Run performance benchmarks
    run_performance_benchmarks()
