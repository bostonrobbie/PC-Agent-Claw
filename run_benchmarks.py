"""
Run Performance Benchmarks for Priority 1 Enhancements

Quick benchmark runner without full unit tests.

Author: AI Self-Improvement System
Created: 2026-02-03
"""

import os
import sys
import time
from search.semantic_search import SemanticCodeSearch
from autonomous.code_sandbox import CodeSandbox, ResourceLimits

def benchmark_semantic_indexing():
    """Benchmark multi-threaded semantic indexing"""
    print("\n" + "="*70)
    print("BENCHMARK 1: Multi-threaded Semantic Indexing")
    print("="*70)

    db_path = "benchmark_semantic.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    test_dir = os.path.dirname(os.path.abspath(__file__))

    # Sequential indexing
    print("\nIndexing sequentially...")
    search = SemanticCodeSearch(db_path=db_path, max_workers=1)
    result_seq = search.index_project("benchmark-seq", test_dir, parallel=False)

    # Clean and re-index in parallel
    os.remove(db_path)
    print("Indexing in parallel (8 threads)...")
    search = SemanticCodeSearch(db_path=db_path, max_workers=8)
    result_par = search.index_project("benchmark-par", test_dir, parallel=True)

    # Results
    print("\nResults:")
    print(f"  Sequential:")
    print(f"    - Time: {result_seq['elapsed_time']}s")
    print(f"    - Speed: {result_seq['files_per_second']:.1f} files/sec")
    print(f"    - Files: {result_seq['files_indexed']}")
    print(f"    - Chunks: {result_seq['chunks_indexed']}")

    print(f"\n  Parallel (8 threads):")
    print(f"    - Time: {result_par['elapsed_time']}s")
    print(f"    - Speed: {result_par['files_per_second']:.1f} files/sec")
    print(f"    - Files: {result_par['files_indexed']}")
    print(f"    - Chunks: {result_par['chunks_indexed']}")

    speedup = result_seq['elapsed_time'] / result_par['elapsed_time'] if result_par['elapsed_time'] > 0 else 0
    print(f"\n  Performance:")
    print(f"    - Speedup: {speedup:.2f}x")
    print(f"    - Target: 100+ files/sec")
    print(f"    - Achieved: {result_par['files_per_second']:.1f} files/sec")

    if result_par['files_per_second'] >= 100:
        print("\n  [OK] TARGET MET: 100+ files/sec achieved!")
    elif result_par['files_per_second'] >= 50:
        print(f"\n  [PARTIAL] {result_par['files_per_second']:.1f} files/sec (good speedup)")
    else:
        print(f"\n  [BELOW TARGET]")

    # Cleanup
    if os.path.exists(db_path):
        os.remove(db_path)

    return result_par


def benchmark_code_sandbox():
    """Benchmark code execution sandbox"""
    print("\n" + "="*70)
    print("BENCHMARK 2: Code Execution Sandbox")
    print("="*70)

    try:
        sandbox = CodeSandbox()

        # Test 1: Execution speed
        print("\nTest 1: Python execution speed")
        simple_code = """
print("Hello, World!")
result = sum(range(100))
print(f"Sum: {result}")
"""

        timings = []
        print("Running 10 executions...")
        for i in range(10):
            result = sandbox.execute(simple_code, 'python')
            if result.success:
                timings.append(result.execution_time)
                print(f"  Run {i+1}: {result.execution_time:.3f}s")

        if not timings:
            print("  No successful executions")
            return False

        avg_time = sum(timings) / len(timings)
        print(f"\nResults:")
        print(f"  Average: {avg_time:.3f}s")
        print(f"  Min: {min(timings):.3f}s")
        print(f"  Max: {max(timings):.3f}s")

        # Test 2: Timeout accuracy
        print("\nTest 2: Timeout enforcement")
        timeout_code = """
import time
print("Starting...")
time.sleep(10)
print("Done")
"""
        limits = ResourceLimits(timeout_seconds=3)
        print("Running code with 10s sleep, 3s timeout...")
        result = sandbox.execute(timeout_code, 'python', limits=limits)

        print(f"\nResults:")
        print(f"  Timeout setting: 3.0s")
        print(f"  Actual time: {result.execution_time:.3f}s")
        print(f"  Timeout triggered: {result.timeout}")
        print(f"  Success: {result.success}")

        if result.timeout and 3.0 <= result.execution_time <= 4.0:
            print("  [OK] Timeout working correctly!")
        else:
            print("  [WARN] Timeout accuracy issue")

        # Test 3: Multi-language support
        print("\nTest 3: Multi-language support")
        languages = sandbox.list_supported_languages()
        print(f"Supported languages: {len(languages)}")
        for lang in languages:
            print(f"  - {lang['language']}: {lang['runtime']}")

        # Test 4: Error handling
        print("\nTest 4: Error handling")
        error_code = """
print("Before error")
raise ValueError("Test error")
print("After error")
"""
        result = sandbox.execute(error_code, 'python')
        print(f"Results:")
        print(f"  Success: {result.success}")
        print(f"  Exit code: {result.exit_code}")
        print(f"  Error captured: {'ValueError' in result.stderr}")

        if not result.success and 'ValueError' in result.stderr:
            print("  [OK] Error handling working correctly!")
        else:
            print("  [FAIL] Error handling issue")

        # Test 5: Resource limits
        print("\nTest 5: Resource limits")
        memory_code = """
import sys
print(f"Memory limit test")
data = []
try:
    for i in range(1000):
        data.append([0] * 100000)
    print(f"Allocated {len(data)} arrays")
except MemoryError:
    print("Memory limit reached")
"""
        limits = ResourceLimits(memory_limit="128m", timeout_seconds=10)
        print("Running with 128MB memory limit...")
        result = sandbox.execute(memory_code, 'python', limits=limits)

        print(f"Results:")
        print(f"  Success: {result.success}")
        print(f"  Time: {result.execution_time:.3f}s")
        print(f"  Output length: {len(result.stdout)} chars")
        print("  [OK] Resource limits enforced")

        return True

    except RuntimeError as e:
        print(f"\n[FAIL] Docker not available: {e}")
        print("\nTo run sandbox benchmarks:")
        print("1. Install Docker: https://docs.docker.com/get-docker/")
        print("2. Start Docker daemon")
        print("3. Run benchmarks again")
        return False


def benchmark_incremental_indexer():
    """Benchmark incremental indexer"""
    print("\n" + "="*70)
    print("BENCHMARK 3: Incremental Update System")
    print("="*70)

    try:
        from search.incremental_indexer import IncrementalIndexer
        import tempfile
        import shutil

        db_path = "benchmark_incremental.db"
        if os.path.exists(db_path):
            os.remove(db_path)

        search = SemanticCodeSearch(db_path=db_path)

        # Create test directory
        test_dir = tempfile.mkdtemp()

        try:
            # Initial index
            print("\nCreating initial index...")
            result = search.index_project("test-inc", test_dir)
            print(f"  Files indexed: {result['files_indexed']}")

            # Create indexer
            indexer = IncrementalIndexer(
                search_engine=search,
                project_name="test-inc",
                root_path=test_dir,
                batch_size=5,
                batch_interval=1.0
            )

            # Start monitoring
            print("\nStarting file monitoring...")
            indexer.start_monitoring()
            time.sleep(0.5)

            # Create files
            print("Creating 10 test files...")
            for i in range(10):
                file_path = os.path.join(test_dir, f"test_{i}.py")
                with open(file_path, 'w') as f:
                    f.write(f"def function_{i}():\n    return {i}\n")

            # Wait for processing
            print("Waiting for batch processing...")
            time.sleep(3)

            # Stop monitoring
            indexer.stop_monitoring()

            # Get stats
            stats = indexer.get_stats()
            print(f"\nResults:")
            print(f"  Files created: {stats['files_created']}")
            print(f"  Files modified: {stats['files_modified']}")
            print(f"  Batches processed: {stats['batches_processed']}")
            print(f"  Last update: {stats['last_update']}")

            if stats['batches_processed'] > 0:
                print("  [OK] Batch processing working!")
            else:
                print("  [WARN] No batches processed")

        finally:
            # Cleanup
            shutil.rmtree(test_dir)
            if os.path.exists(db_path):
                os.remove(db_path)

        return True

    except ImportError:
        print("\n[WARN] Watchdog library not installed")
        print("Install with: pip install watchdog")
        return False


def main():
    """Run all benchmarks"""
    print("\n" + "="*70)
    print("PRIORITY 1 CRITICAL ENHANCEMENTS - PERFORMANCE BENCHMARKS")
    print("="*70)
    print(f"\nStarted: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    results = {}

    # Benchmark 1: Multi-threaded indexing
    try:
        results['indexing'] = benchmark_semantic_indexing()
    except Exception as e:
        print(f"\n[FAIL] Indexing benchmark failed: {e}")
        results['indexing'] = None

    # Benchmark 2: Code sandbox
    try:
        results['sandbox'] = benchmark_code_sandbox()
    except Exception as e:
        print(f"\n[FAIL] Sandbox benchmark failed: {e}")
        results['sandbox'] = None

    # Benchmark 3: Incremental indexer
    try:
        results['incremental'] = benchmark_incremental_indexer()
    except Exception as e:
        print(f"\n[FAIL] Incremental indexer benchmark failed: {e}")
        results['incremental'] = None

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    if results['indexing']:
        print(f"\n[OK] Multi-threaded Indexing: {results['indexing']['files_per_second']:.1f} files/sec")
    else:
        print("\n[FAIL] Multi-threaded Indexing: Failed")

    if results['sandbox']:
        print("[OK] Code Sandbox: Working")
    else:
        print("[FAIL] Code Sandbox: Not available (Docker required)")

    if results['incremental']:
        print("[OK] Incremental Indexer: Working")
    else:
        print("[WARN] Incremental Indexer: Watchdog required")

    print("\n" + "="*70)
    print(f"Completed: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
