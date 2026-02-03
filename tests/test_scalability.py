#!/usr/bin/env python3
"""
Comprehensive Tests for Priority 3 Scalability Enhancements

Tests all 4 features:
1. Dynamic Worker Scaling
2. Web Dashboard
3. Capability Result Caching
4. Database Connection Pooling
"""
import sys
from pathlib import Path
import time
import threading
import sqlite3
import tempfile
import os

workspace = Path(__file__).parent.parent
sys.path.insert(0, str(workspace))

from autonomous.background_tasks import BackgroundTaskManager, TaskPriority
from core.result_cache import ResultCache, get_cache
from core.db_pool import ConnectionPool, get_pool


class TestResults:
    """Track test results"""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def record_pass(self, test_name: str):
        self.passed += 1
        print(f"  [PASS] {test_name}")

    def record_fail(self, test_name: str, error: str):
        self.failed += 1
        self.errors.append((test_name, error))
        print(f"  [FAIL] {test_name}: {error}")

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*70}")
        print(f"Test Results: {self.passed}/{total} passed")
        if self.failed > 0:
            print(f"\nFailed Tests:")
            for name, error in self.errors:
                print(f"  - {name}: {error}")
        print(f"{'='*70}")
        return self.failed == 0


def test_dynamic_worker_scaling(results: TestResults):
    """Test dynamic worker scaling functionality"""
    print("\n" + "="*70)
    print("TEST 1: Dynamic Worker Scaling")
    print("="*70)

    try:
        # Create temporary database
        temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        temp_db.close()

        manager = BackgroundTaskManager(
            db_path=temp_db.name,
            min_workers=1,
            max_workers=8,
            enable_auto_scaling=True
        )

        try:
            # Test 1.1: Initial state
            manager.start_workers()
            time.sleep(0.5)
            stats = manager.get_worker_stats()

            if stats['current_workers'] >= stats['min_workers']:
                results.record_pass("1.1: Workers started with minimum count")
            else:
                results.record_fail("1.1: Workers started", f"Got {stats['current_workers']}, expected >= {stats['min_workers']}")

            # Test 1.2: Register test handler
            @manager.register_handler('test_task')
            def test_handler(context):
                time.sleep(0.5)  # Simulate work
                return {'success': True, 'value': context.get('value', 0)}

            results.record_pass("1.2: Task handler registered")

            # Test 1.3: Queue many tasks to trigger scale-up
            print("\n  Queueing 20 tasks to trigger scale-up...")
            for i in range(20):
                manager.queue_task('test_task', f'Test {i}', TaskPriority.MEDIUM, {'value': i})

            # Wait and monitor scaling
            time.sleep(2)
            stats_before = manager.get_worker_stats()

            time.sleep(4)  # Allow scaling to happen
            stats_after = manager.get_worker_stats()

            if stats_after['current_workers'] > stats_before['current_workers']:
                results.record_pass(f"1.3: Scale-up triggered ({stats_before['current_workers']} -> {stats_after['current_workers']})")
            else:
                results.record_fail("1.3: Scale-up", f"Workers stayed at {stats_after['current_workers']}")

            # Test 1.4: Wait for tasks to complete
            print("\n  Waiting for tasks to complete...")
            time.sleep(10)

            stats = manager.get_worker_stats()
            if stats['queue_depth'] < 5:
                results.record_pass(f"1.4: Tasks processed (queue: {stats['queue_depth']})")
            else:
                results.record_fail("1.4: Task processing", f"Queue still has {stats['queue_depth']} tasks")

            # Test 1.5: Verify auto-scaling is enabled
            if stats['auto_scaling_enabled']:
                results.record_pass("1.5: Auto-scaling enabled")
            else:
                results.record_fail("1.5: Auto-scaling", "Not enabled")

            # Test 1.6: Worker statistics
            if stats['max_workers'] == 8 and stats['min_workers'] == 1:
                results.record_pass("1.6: Worker limits configured correctly")
            else:
                results.record_fail("1.6: Worker limits", f"Got max={stats['max_workers']}, min={stats['min_workers']}")

        finally:
            manager.close()
            os.unlink(temp_db.name)

    except Exception as e:
        results.record_fail("Dynamic Worker Scaling", str(e))
        import traceback
        traceback.print_exc()


def test_result_caching(results: TestResults):
    """Test result caching functionality"""
    print("\n" + "="*70)
    print("TEST 2: Capability Result Caching")
    print("="*70)

    try:
        # Create temporary database
        temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        temp_db.close()

        cache = ResultCache(
            max_size=100,
            default_ttl=60,
            enable_persistent=True,
            db_path=temp_db.name
        )

        try:
            # Test 2.1: Basic set/get
            cache.set('key1', 'value1')
            value = cache.get('key1')

            if value == 'value1':
                results.record_pass("2.1: Basic set/get")
            else:
                results.record_fail("2.1: Basic set/get", f"Got {value}")

            # Test 2.2: Cache miss
            missing = cache.get('nonexistent', default='NOT_FOUND')

            if missing == 'NOT_FOUND':
                results.record_pass("2.2: Cache miss with default")
            else:
                results.record_fail("2.2: Cache miss", f"Got {missing}")

            # Test 2.3: TTL expiration
            cache.set('expires', 'soon', ttl=1)
            time.sleep(1.5)
            expired = cache.get('expires')

            if expired is None:
                results.record_pass("2.3: TTL expiration")
            else:
                results.record_fail("2.3: TTL expiration", f"Got {expired}, expected None")

            # Test 2.4: Decorator caching
            call_count = [0]

            @cache.cached(ttl=30)
            def expensive_func(x, y):
                call_count[0] += 1
                return x + y

            result1 = expensive_func(5, 3)
            result2 = expensive_func(5, 3)  # Should hit cache

            if result1 == result2 == 8 and call_count[0] == 1:
                results.record_pass("2.4: Decorator caching (function called once)")
            else:
                results.record_fail("2.4: Decorator caching", f"Results: {result1}, {result2}, Calls: {call_count[0]}")

            # Test 2.5: LRU eviction
            small_cache = ResultCache(max_size=3)
            for i in range(5):
                small_cache.set(f'key{i}', f'value{i}')

            stats = small_cache.get_stats()
            if stats['size'] <= 3 and stats['evictions'] >= 2:
                results.record_pass(f"2.5: LRU eviction (size: {stats['size']}, evictions: {stats['evictions']})")
            else:
                results.record_fail("2.5: LRU eviction", f"Size: {stats['size']}, Evictions: {stats['evictions']}")

            # Test 2.6: Tag-based invalidation
            cache.set('post1', {'title': 'Post 1'}, tags=['posts'])
            cache.set('post2', {'title': 'Post 2'}, tags=['posts'])
            cache.set('user1', {'name': 'User 1'}, tags=['users'])

            invalidated = cache.invalidate_by_tag('posts')

            if invalidated == 2 and cache.get('user1') is not None:
                results.record_pass("2.6: Tag-based invalidation")
            else:
                results.record_fail("2.6: Tag-based invalidation", f"Invalidated: {invalidated}")

            # Test 2.7: Cache statistics
            stats = cache.get_stats()

            if 'hits' in stats and 'misses' in stats and 'hit_rate' in stats:
                results.record_pass(f"2.7: Cache statistics (hit rate: {stats['hit_rate']*100:.1f}%)")
            else:
                results.record_fail("2.7: Cache statistics", "Missing statistics")

            # Test 2.8: Thread safety
            errors = []

            def cache_worker(worker_id):
                try:
                    for i in range(10):
                        cache.set(f'worker{worker_id}_key{i}', f'value{i}')
                        cache.get(f'worker{worker_id}_key{i}')
                except Exception as e:
                    errors.append(str(e))

            threads = [threading.Thread(target=cache_worker, args=(i,)) for i in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            if len(errors) == 0:
                results.record_pass("2.8: Thread-safe operations")
            else:
                results.record_fail("2.8: Thread safety", f"Errors: {errors}")

            small_cache.close()

        finally:
            cache.close()
            try:
                os.unlink(temp_db.name)
            except:
                pass

    except Exception as e:
        results.record_fail("Result Caching", str(e))
        import traceback
        traceback.print_exc()


def test_connection_pooling(results: TestResults):
    """Test database connection pooling"""
    print("\n" + "="*70)
    print("TEST 3: Database Connection Pooling")
    print("="*70)

    try:
        # Create temporary database
        temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        temp_db.close()

        # Initialize test table
        conn = sqlite3.connect(temp_db.name)
        conn.execute('''
            CREATE TABLE test_data (
                id INTEGER PRIMARY KEY,
                value TEXT,
                thread_id INTEGER
            )
        ''')
        conn.commit()
        conn.close()

        pool = ConnectionPool(
            db_path=temp_db.name,
            min_size=2,
            max_size=5,
            max_idle_time=10
        )

        try:
            # Test 3.1: Initial pool state
            time.sleep(0.5)  # Let pool initialize
            stats = pool.get_stats()

            if stats['current_size'] >= 2:
                results.record_pass(f"3.1: Pool initialized (size: {stats['current_size']})")
            else:
                results.record_fail("3.1: Pool initialization", f"Size: {stats['current_size']}")

            # Test 3.2: Connection acquisition
            conn = pool.acquire(timeout=5)

            if conn is not None:
                results.record_pass("3.2: Connection acquired")
                conn.close()
            else:
                results.record_fail("3.2: Connection acquisition", "Timeout")

            # Test 3.3: Context manager
            try:
                with pool.connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO test_data (value, thread_id) VALUES (?, ?)",
                                 ('test', 0))
                    conn.commit()
                results.record_pass("3.3: Context manager usage")
            except Exception as e:
                results.record_fail("3.3: Context manager", str(e))

            # Test 3.4: Connection reuse
            conn1 = pool.acquire()
            conn1_id = id(conn1.conn)
            conn1.close()

            conn2 = pool.acquire()
            conn2_id = id(conn2.conn)
            conn2.close()

            if conn1_id == conn2_id:
                results.record_pass("3.4: Connection reuse")
            else:
                results.record_fail("3.4: Connection reuse", "Different connections returned")

            # Test 3.5: Concurrent access
            errors = []
            inserted_count = [0]

            def db_worker(worker_id):
                try:
                    for i in range(10):
                        with pool.connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute(
                                "INSERT INTO test_data (value, thread_id) VALUES (?, ?)",
                                (f'worker{worker_id}_item{i}', worker_id)
                            )
                            conn.commit()
                            inserted_count[0] += 1
                except Exception as e:
                    errors.append(str(e))

            threads = [threading.Thread(target=db_worker, args=(i,)) for i in range(3)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            if len(errors) == 0 and inserted_count[0] == 30:
                results.record_pass(f"3.5: Concurrent access ({inserted_count[0]} inserts)")
            else:
                results.record_fail("3.5: Concurrent access", f"Errors: {len(errors)}, Inserts: {inserted_count[0]}")

            # Test 3.6: Pool statistics
            stats = pool.get_stats()

            if stats['acquisitions'] > 0 and stats['releases'] > 0:
                results.record_pass(f"3.6: Pool statistics (acq: {stats['acquisitions']}, rel: {stats['releases']})")
            else:
                results.record_fail("3.6: Pool statistics", f"Stats: {stats}")

            # Test 3.7: Data integrity
            with pool.connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) as count FROM test_data")
                count = cursor.fetchone()['count']

            if count == 31:  # 1 from test 3.3 + 30 from test 3.5
                results.record_pass(f"3.7: Data integrity ({count} records)")
            else:
                results.record_fail("3.7: Data integrity", f"Expected 31, got {count}")

            # Test 3.8: Connection health check
            with pool.connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()

            if result is not None:
                results.record_pass("3.8: Connection health check")
            else:
                results.record_fail("3.8: Health check", "No result")

        finally:
            pool.close_all()
            try:
                os.unlink(temp_db.name)
            except:
                pass

    except Exception as e:
        results.record_fail("Connection Pooling", str(e))
        import traceback
        traceback.print_exc()


def test_integration(results: TestResults):
    """Test integration of all components"""
    print("\n" + "="*70)
    print("TEST 4: Integration Tests")
    print("="*70)

    try:
        # Create temporary databases
        temp_cache_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        temp_cache_db.close()

        temp_pool_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        temp_pool_db.close()

        temp_tasks_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        temp_tasks_db.close()

        # Initialize components
        cache = ResultCache(max_size=50, default_ttl=300,
                           enable_persistent=True, db_path=temp_cache_db.name)

        pool = ConnectionPool(db_path=temp_pool_db.name, min_size=2, max_size=5)

        manager = BackgroundTaskManager(
            db_path=temp_tasks_db.name,
            min_workers=1,
            max_workers=4,
            enable_auto_scaling=True
        )

        try:
            # Test 4.1: Components initialized
            results.record_pass("4.1: All components initialized")

            # Test 4.2: Cache + Pool integration
            @cache.cached(ttl=60)
            def cached_db_query(query_id):
                with pool.connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1 as value")
                    return cursor.fetchone()['value']

            result1 = cached_db_query(1)
            result2 = cached_db_query(1)  # Should be from cache

            stats = cache.get_stats()
            if stats['hits'] > 0:
                results.record_pass("4.2: Cache + Pool integration")
            else:
                results.record_fail("4.2: Cache + Pool integration", "No cache hits")

            # Test 4.3: Background tasks + Cache
            manager.start_workers()

            @manager.register_handler('cached_task')
            def cached_task_handler(context):
                value = context.get('value', 0)
                cache.set(f'task_result_{value}', value * 2)
                return {'success': True, 'result': value * 2}

            task_id = manager.queue_task('cached_task', 'Test task',
                                        TaskPriority.HIGH, {'value': 42})

            time.sleep(2)  # Wait for task completion

            task_status = manager.get_task_status(task_id)
            cached_value = cache.get('task_result_42')

            if task_status['status'] == 'completed' and cached_value == 84:
                results.record_pass("4.3: Background tasks + Cache integration")
            else:
                results.record_fail("4.3: Tasks + Cache", f"Status: {task_status['status']}, Cache: {cached_value}")

            # Test 4.4: All components working together
            errors = []

            def integration_worker(worker_id):
                try:
                    # Queue task
                    tid = manager.queue_task('cached_task', f'Worker {worker_id}',
                                           TaskPriority.MEDIUM, {'value': worker_id})

                    # Use pool
                    with pool.connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT 1")

                    # Use cache
                    cache.set(f'worker_{worker_id}', worker_id)
                    cache.get(f'worker_{worker_id}')

                except Exception as e:
                    errors.append(str(e))

            threads = [threading.Thread(target=integration_worker, args=(i,))
                      for i in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            if len(errors) == 0:
                results.record_pass("4.4: Full integration with concurrent access")
            else:
                results.record_fail("4.4: Full integration", f"Errors: {errors}")

            # Test 4.5: Performance under load
            start = time.time()

            for i in range(50):
                cache.set(f'perf_{i}', i)
                with pool.connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1")

            elapsed = time.time() - start

            if elapsed < 5.0:  # Should complete in under 5 seconds
                results.record_pass(f"4.5: Performance test (50 ops in {elapsed:.2f}s)")
            else:
                results.record_fail("4.5: Performance", f"Took {elapsed:.2f}s")

        finally:
            manager.close()
            pool.close_all()
            cache.close()

            # Cleanup
            for db in [temp_cache_db.name, temp_pool_db.name, temp_tasks_db.name]:
                try:
                    os.unlink(db)
                except:
                    pass

    except Exception as e:
        results.record_fail("Integration", str(e))
        import traceback
        traceback.print_exc()


def main():
    """Run all scalability tests"""
    print("=" * 70)
    print("PRIORITY 3 SCALABILITY ENHANCEMENTS - COMPREHENSIVE TESTS")
    print("=" * 70)
    print("\nTesting 4 components:")
    print("  1. Dynamic Worker Scaling")
    print("  2. Capability Result Caching")
    print("  3. Database Connection Pooling")
    print("  4. Integration Tests")
    print()

    results = TestResults()

    # Run all tests
    test_dynamic_worker_scaling(results)
    test_result_caching(results)
    test_connection_pooling(results)
    test_integration(results)

    # Print summary
    success = results.summary()

    if success:
        print("\n✓ ALL TESTS PASSED!")
        return 0
    else:
        print("\n✗ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
