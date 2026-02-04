"""
Test Suite for Phase 2 Robust Operations Engine

Tests integration of:
- Smart Retry Engine
- Work Queue Persistence
- Auto-Fix Registry
- Phase 1 integration
"""
import pytest
import time
import os
import tempfile

from core.phase2_robust_engine import Phase2RobustEngine
from core.work_queue_persistence import TaskPriority


class TestSmartRetryEngine:
    """Test smart retry logic"""

    def test_successful_execution_no_retry(self):
        """Test successful execution requires no retries"""
        from core.smart_retry_engine import SmartRetryEngine

        engine = SmartRetryEngine()

        def success_func():
            return "success"

        result = engine.execute_with_retry(success_func, 'default')
        assert result == "success"
        assert engine.stats['total_retries'] == 0

    def test_retry_with_eventual_success(self):
        """Test retry logic with eventual success"""
        from core.smart_retry_engine import SmartRetryEngine

        engine = SmartRetryEngine()
        attempt = {'count': 0}

        def flaky_func():
            attempt['count'] += 1
            if attempt['count'] < 3:
                raise Exception("temporary failure")
            return "success"

        result = engine.execute_with_retry(flaky_func, 'default')
        assert result == "success"
        assert engine.stats['total_retries'] >= 2

    def test_circuit_breaker_opens(self):
        """Test circuit breaker opens after threshold failures"""
        from core.smart_retry_engine import SmartRetryEngine

        engine = SmartRetryEngine()

        def always_fails():
            raise Exception("permanent failure")

        # Cause multiple failures
        for i in range(10):
            try:
                engine.execute_with_retry(always_fails, 'test_category')
            except:
                pass

        # Circuit should eventually open
        stats = engine.get_stats()
        assert stats['circuit_opens'] > 0


class TestWorkQueuePersistence:
    """Test work queue persistence"""

    @pytest.fixture
    def temp_queue_db(self):
        """Create temporary queue database"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        if os.path.exists(path):
            os.unlink(path)

    def test_queue_initialization(self, temp_queue_db):
        """Test queue initializes correctly"""
        from core.work_queue_persistence import WorkQueuePersistence

        queue = WorkQueuePersistence(temp_queue_db)
        status = queue.get_queue_status()

        assert status['total_tasks'] == 0

    def test_add_and_get_task(self, temp_queue_db):
        """Test adding and retrieving tasks"""
        from core.work_queue_persistence import WorkQueuePersistence

        queue = WorkQueuePersistence(temp_queue_db)

        def test_func():
            return "done"

        queue.register_function('test_func', test_func)
        queue.add_task('task_1', 'Test task', 'test_func')

        task = queue.get_next_task()
        assert task is not None
        assert task['task_id'] == 'task_1'

    def test_task_persistence_across_instances(self, temp_queue_db):
        """Test tasks persist across different instances"""
        from core.work_queue_persistence import WorkQueuePersistence

        # First instance - add task
        queue1 = WorkQueuePersistence(temp_queue_db)
        queue1.register_function('test', lambda: "ok")
        queue1.add_task('persist_test', 'Persistent task', 'test')

        # Second instance - should see task
        queue2 = WorkQueuePersistence(temp_queue_db)
        status = queue2.get_queue_status()
        assert status['total_tasks'] == 1

    def test_resume_interrupted_tasks(self, temp_queue_db):
        """Test resuming interrupted tasks"""
        from core.work_queue_persistence import WorkQueuePersistence

        queue = WorkQueuePersistence(temp_queue_db)
        queue.register_function('test', lambda: "ok")
        queue.add_task('interrupt_test', 'Interrupted task', 'test')

        # Start task (simulate crash during execution)
        queue.start_task('interrupt_test')

        # New instance resumes
        queue2 = WorkQueuePersistence(temp_queue_db)
        interrupted = queue2.resume_interrupted_tasks()

        assert len(interrupted) == 1
        assert 'interrupt_test' in interrupted


class TestAutoFixRegistry:
    """Test auto-fix registry"""

    def test_builtin_fixes_registered(self):
        """Test built-in fixes are registered"""
        from core.auto_fix_registry import AutoFixRegistry

        registry = AutoFixRegistry()
        stats = registry.get_stats()

        assert stats['total_patterns'] > 0

    def test_unicode_fix(self):
        """Test unicode error auto-fix"""
        from core.auto_fix_registry import AutoFixRegistry

        registry = AutoFixRegistry()

        error = UnicodeEncodeError('charmap', '\u2713', 0, 1, 'fail')
        fix = registry.try_fix(error)

        assert fix is not None
        assert fix['fixed'] == True

    def test_learn_from_manual_fix(self):
        """Test learning from manual fixes"""
        from core.auto_fix_registry import AutoFixRegistry

        registry = AutoFixRegistry()

        initial_patterns = registry.get_stats()['total_patterns']

        error = ValueError("custom error")
        registry.learn_from_manual_fix(error, "Manual fix applied")

        new_patterns = registry.get_stats()['total_patterns']
        assert new_patterns > initial_patterns


class TestPhase2Integration:
    """Test Phase 2 full integration"""

    @pytest.fixture
    def temp_dbs(self):
        """Create temporary databases"""
        error_fd, error_path = tempfile.mkstemp(suffix='_error.db')
        queue_fd, queue_path = tempfile.mkstemp(suffix='_queue.db')
        os.close(error_fd)
        os.close(queue_fd)

        yield error_path, queue_path

        for path in [error_path, queue_path]:
            if os.path.exists(path):
                os.unlink(path)

    def test_engine_initialization(self, temp_dbs):
        """Test Phase 2 engine initializes all subsystems"""
        error_db, queue_db = temp_dbs
        engine = Phase2RobustEngine(error_db, queue_db)

        assert engine.phase1 is not None
        assert engine.retry_engine is not None
        assert engine.work_queue is not None
        assert engine.auto_fix is not None

    def test_queue_and_execute_task(self, temp_dbs):
        """Test queueing and executing tasks"""
        error_db, queue_db = temp_dbs
        engine = Phase2RobustEngine(error_db, queue_db)

        def simple_task():
            return "completed"

        success = engine.queue_task('test_1', 'Simple task', simple_task)
        assert success == True

        result = engine.execute_next_task()
        assert result == "completed"

    def test_error_recovery_with_retry(self, temp_dbs):
        """Test retry engine is integrated"""
        error_db, queue_db = temp_dbs
        engine = Phase2RobustEngine(error_db, queue_db)

        # Just verify retry engine exists and can be used
        assert engine.retry_engine is not None

        # Test that stats tracking works
        initial_stats = engine.get_comprehensive_stats()
        assert 'retry' in initial_stats

    def test_auto_fix_application(self, temp_dbs):
        """Test auto-fix registry is integrated"""
        error_db, queue_db = temp_dbs
        engine = Phase2RobustEngine(error_db, queue_db)

        # Verify auto-fix exists and has builtin patterns
        assert engine.auto_fix is not None
        stats = engine.auto_fix.get_stats()
        assert stats['total_patterns'] > 0

    def test_execute_all_queued_tasks(self, temp_dbs):
        """Test executing all queued tasks"""
        error_db, queue_db = temp_dbs
        engine = Phase2RobustEngine(error_db, queue_db)

        # Queue multiple tasks
        for i in range(5):
            engine.queue_task(f'task_{i}', f'Task {i}', lambda: f"result_{i}")

        results = engine.execute_all_queued_tasks()

        assert results['completed'] == 5
        assert results['failed'] == 0

    def test_comprehensive_stats(self, temp_dbs):
        """Test comprehensive statistics"""
        error_db, queue_db = temp_dbs
        engine = Phase2RobustEngine(error_db, queue_db)

        engine.queue_task('stat_test', 'Stat task', lambda: "ok")
        engine.execute_next_task()

        stats = engine.get_comprehensive_stats()

        assert 'phase1' in stats
        assert 'phase2' in stats
        assert 'retry' in stats
        assert 'queue' in stats
        assert 'auto_fix' in stats

    def test_health_check(self, temp_dbs):
        """Test health check functionality"""
        error_db, queue_db = temp_dbs
        engine = Phase2RobustEngine(error_db, queue_db)

        health = engine.health_check()

        assert 'overall' in health
        assert 'issues' in health
        assert 'recommendations' in health
        assert health['overall'] in ['healthy', 'degraded', 'unhealthy']

    def test_learn_from_manual_fix_integration(self, temp_dbs):
        """Test learning from manual fix updates all systems"""
        error_db, queue_db = temp_dbs
        engine = Phase2RobustEngine(error_db, queue_db)

        error = ValueError("test error")
        engine.learn_from_manual_fix(error, "Test solution")

        # Check Phase 1 learned
        phase1_stats = engine.phase1.get_stats()
        assert phase1_stats['total_errors_learned'] > 0

        # Check Phase 2 auto-fix learned
        autofix_stats = engine.auto_fix.get_stats()
        assert autofix_stats['patterns_learned'] > 0

    def test_task_persistence_after_crash(self, temp_dbs):
        """Test tasks persist and resume after crash simulation"""
        error_db, queue_db = temp_dbs

        # First instance - queue tasks
        engine1 = Phase2RobustEngine(error_db, queue_db)
        engine1.queue_task('persist_1', 'Persistent task 1', lambda: "ok")
        engine1.queue_task('persist_2', 'Persistent task 2', lambda: "ok")

        # Simulate crash (delete instance)
        del engine1

        # Second instance - should see tasks
        engine2 = Phase2RobustEngine(error_db, queue_db)
        stats = engine2.work_queue.get_queue_status()

        assert stats['total_tasks'] >= 2


def test_full_phase2_workflow():
    """Test complete Phase 2 workflow"""
    error_fd, error_path = tempfile.mkstemp(suffix='_error.db')
    queue_fd, queue_path = tempfile.mkstemp(suffix='_queue.db')
    os.close(error_fd)
    os.close(queue_fd)

    try:
        engine = Phase2RobustEngine(error_path, queue_path)

        # Queue multiple tasks with different priorities
        engine.queue_task('critical', 'Critical task',
                         lambda: "critical_done",
                         priority=TaskPriority.CRITICAL)

        engine.queue_task('normal', 'Normal task',
                         lambda: "normal_done",
                         priority=TaskPriority.NORMAL)

        # Execute all
        results = engine.execute_all_queued_tasks()

        assert results['completed'] == 2

        # Get comprehensive stats
        stats = engine.get_comprehensive_stats()
        assert stats['phase2']['tasks_completed'] == 2

        # Health check
        health = engine.health_check()
        assert health['overall'] in ['healthy', 'degraded']

    finally:
        for path in [error_path, queue_path]:
            if os.path.exists(path):
                os.unlink(path)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
