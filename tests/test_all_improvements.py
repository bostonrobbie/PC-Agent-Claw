"""
Comprehensive Test Suite for All 8 Improvements

Tests:
1. Integrated Phase 3 Engine
2. Background Task Processor
3. Memory Checkpoint System
4. Performance Profiler
5. Predictive Resource Manager
6. Multi-Track Parallel Engine
"""
import pytest
import time
import os
import tempfile
import threading

from core.phase3_integrated_engine import Phase3IntegratedEngine
from core.background_processor import BackgroundProcessor
from core.memory_checkpoint import MemoryCheckpointSystem
from core.performance_profiler import PerformanceProfiler
from core.predictive_resource_manager import PredictiveResourceManager
from core.multi_track_parallel import MultiTrackParallelEngine
from core.work_queue_persistence import TaskPriority


class TestPhase3IntegratedEngine:
    """Test integrated Phase 3 engine"""

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

    def test_initialization(self, temp_dbs):
        """Test Phase 3 engine initializes all subsystems"""
        error_db, queue_db = temp_dbs
        engine = Phase3IntegratedEngine(error_db, queue_db)

        assert engine.phase2 is not None
        assert engine.confidence is not None
        assert engine.degradation is not None
        assert engine.error_budget is not None

    def test_execute_action_success(self, temp_dbs):
        """Test successful action execution"""
        error_db, queue_db = temp_dbs
        engine = Phase3IntegratedEngine(error_db, queue_db)

        def simple_action():
            return "success"

        result = engine.execute_action("test_action", simple_action)
        assert result == "success"
        assert engine.stats['total_actions'] == 1

    def test_execute_with_confidence(self, temp_dbs):
        """Test confidence-based execution"""
        error_db, queue_db = temp_dbs
        engine = Phase3IntegratedEngine(error_db, queue_db)

        def action():
            return "done"

        result = engine.execute_action(
            "high_confidence_action",
            action,
            confidence=0.95
        )

        assert result == "done"
        assert engine.stats['autonomous_actions'] > 0

    def test_health_check(self, temp_dbs):
        """Test comprehensive health check"""
        error_db, queue_db = temp_dbs
        engine = Phase3IntegratedEngine(error_db, queue_db)

        health = engine.health_check()

        assert 'overall' in health
        assert 'issues' in health
        assert 'recommendations' in health


class TestBackgroundProcessor:
    """Test background task processor"""

    @pytest.fixture
    def processor(self):
        """Create background processor"""
        proc = BackgroundProcessor(max_concurrent=2)
        yield proc
        proc.shutdown(wait=False)

    def test_initialization(self, processor):
        """Test processor initializes correctly"""
        assert processor.max_concurrent == 2
        assert len(processor.workers) == 2

    def test_run_async(self, processor):
        """Test running task in background"""
        def slow_task():
            time.sleep(0.1)
            return "completed"

        task_id = processor.run_async("test_1", "Test task", slow_task)

        assert task_id == "test_1"
        assert processor.stats['total_tasks'] == 1

    def test_get_result(self, processor):
        """Test retrieving background task result"""
        def simple_task():
            return "result"

        task_id = processor.run_async("test_2", "Simple task", simple_task)
        result = processor.get_result(task_id, timeout=2.0)

        assert result == "result"

    def test_parallel_execution(self, processor):
        """Test multiple tasks run in parallel"""
        def task(n):
            time.sleep(0.1)
            return n

        start = time.time()

        processor.run_async("task_1", "Task 1", task, 1)
        processor.run_async("task_2", "Task 2", task, 2)

        processor.wait_all(timeout=5.0)
        duration = time.time() - start

        # Should complete in ~0.1s (parallel), not 0.2s (sequential)
        assert duration < 0.3


class TestMemoryCheckpointSystem:
    """Test memory checkpoint system"""

    @pytest.fixture
    def temp_db(self):
        """Create temporary checkpoint database"""
        fd, path = tempfile.mkstemp(suffix='_checkpoint.db')
        os.close(fd)
        yield path
        if os.path.exists(path):
            os.unlink(path)

    def test_initialization(self, temp_db):
        """Test checkpoint system initializes"""
        checkpoint = MemoryCheckpointSystem(temp_db)

        assert checkpoint.db_path == temp_db
        assert checkpoint.stats['total_checkpoints'] == 0

    def test_save_checkpoint(self, temp_db):
        """Test saving checkpoint"""
        checkpoint = MemoryCheckpointSystem(temp_db)

        checkpoint_id = checkpoint.save_checkpoint(
            task_id="task_1",
            description="Test checkpoint",
            current_task="Building feature",
            overall_plan="Complete project",
            completed_steps=["Step 1", "Step 2"],
            next_steps=["Step 3", "Step 4"],
            progress=0.5
        )

        assert checkpoint_id is not None
        assert checkpoint.stats['total_checkpoints'] == 1

    def test_restore_checkpoint(self, temp_db):
        """Test restoring checkpoint"""
        checkpoint = MemoryCheckpointSystem(temp_db)

        # Save
        checkpoint.save_checkpoint(
            task_id="task_2",
            description="Test restore",
            current_task="Working",
            overall_plan="Plan",
            completed_steps=["A"],
            next_steps=["B"],
            progress=0.3
        )

        # Restore
        restored = checkpoint.restore_latest_checkpoint(task_id="task_2")

        assert restored is not None
        assert restored.task_id == "task_2"
        assert restored.progress == 0.3
        assert len(restored.completed_steps) == 1

    def test_persistence_across_instances(self, temp_db):
        """Test checkpoints persist across instances"""
        # First instance
        checkpoint1 = MemoryCheckpointSystem(temp_db)
        checkpoint1.save_checkpoint(
            task_id="persist_test",
            description="Persistence test",
            current_task="Task",
            overall_plan="Plan",
            completed_steps=[],
            next_steps=[],
            progress=0.0
        )

        # Second instance
        checkpoint2 = MemoryCheckpointSystem(temp_db)
        restored = checkpoint2.restore_latest_checkpoint(task_id="persist_test")

        assert restored is not None
        assert restored.task_id == "persist_test"


class TestPerformanceProfiler:
    """Test performance profiler"""

    def test_initialization(self):
        """Test profiler initializes"""
        profiler = PerformanceProfiler()

        assert profiler.enabled == True
        assert profiler.stats['total_operations'] == 0

    def test_profile_decorator(self):
        """Test profile decorator"""
        profiler = PerformanceProfiler()

        @profiler.profile('test_operation')
        def test_func():
            time.sleep(0.01)
            return "done"

        result = test_func()

        assert result == "done"
        assert profiler.stats['total_operations'] == 1

    def test_manual_profiling(self):
        """Test manual start/end profiling"""
        profiler = PerformanceProfiler()

        entry = profiler.start_operation("manual_op")
        time.sleep(0.01)
        profiler.end_operation(entry, success=True)

        stats = profiler.get_operation_stats("manual_op")
        assert stats['count'] == 1
        assert stats['average_duration'] > 0

    def test_get_summary(self):
        """Test getting profiling summary"""
        profiler = PerformanceProfiler()

        @profiler.profile('op1')
        def func1():
            return 1

        @profiler.profile('op2')
        def func2():
            return 2

        func1()
        func2()

        summary = profiler.get_summary()

        assert summary['total_operations'] == 2
        assert summary['unique_operations'] == 2


class TestPredictiveResourceManager:
    """Test predictive resource manager"""

    def test_initialization(self):
        """Test resource manager initializes"""
        manager = PredictiveResourceManager()

        assert manager.sample_interval == 5
        assert len(manager.history) == 0

    def test_sample_resources(self):
        """Test resource sampling"""
        manager = PredictiveResourceManager()

        sample = manager.sample_resources()

        assert sample.memory_percent >= 0
        assert sample.cpu_percent >= 0
        assert sample.disk_percent >= 0
        assert len(manager.history) == 1

    def test_check_resources(self):
        """Test resource status check"""
        manager = PredictiveResourceManager()

        status = manager.check_resources()

        assert 'current' in status
        assert 'status' in status
        assert 'warnings' in status

    def test_auto_optimize(self):
        """Test automatic optimization"""
        manager = PredictiveResourceManager()

        optimizations = manager.auto_optimize()

        assert 'actions_taken' in optimizations
        assert 'resources_freed' in optimizations


class TestMultiTrackParallel:
    """Test multi-track parallel engine"""

    def test_initialization(self):
        """Test parallel engine initializes"""
        engine = MultiTrackParallelEngine(max_tracks=3)

        assert engine.max_tracks == 3
        assert engine.stats['total_tracks'] == 0

    def test_create_track(self):
        """Test creating work track"""
        engine = MultiTrackParallelEngine()

        track = engine.create_track("track_1", "Test track")

        assert track.track_id == "track_1"
        assert len(track.tasks) == 0

    def test_add_task_to_track(self):
        """Test adding task to track"""
        engine = MultiTrackParallelEngine()

        engine.create_track("track_1", "Test")
        engine.add_task_to_track("track_1", "task_1", lambda: "result")

        track = engine.tracks["track_1"]
        assert len(track.tasks) == 1

    def test_execute_track(self):
        """Test executing single track"""
        engine = MultiTrackParallelEngine()

        track = engine.create_track("track_1", "Test")
        engine.add_task_to_track("track_1", "task_1", lambda: "done")

        result_track = engine.execute_track(track)

        assert result_track.status.value == "completed"
        assert "task_1" in result_track.results

    def test_parallel_execution(self):
        """Test executing multiple tracks in parallel"""
        engine = MultiTrackParallelEngine(max_tracks=2)

        # Create two independent tracks
        track1 = engine.create_track("track_1", "Track 1")
        track2 = engine.create_track("track_2", "Track 2")

        engine.add_task_to_track("track_1", "t1_task1", lambda: time.sleep(0.1) or "t1_done")
        engine.add_task_to_track("track_2", "t2_task1", lambda: time.sleep(0.1) or "t2_done")

        start = time.time()
        results = engine.execute_parallel([track1, track2])
        duration = time.time() - start

        # Should complete in ~0.1s (parallel), not 0.2s (sequential)
        assert duration < 0.3
        assert len(results) == 2


def test_full_integration():
    """Test full integration of all improvements"""
    error_fd, error_path = tempfile.mkstemp(suffix='_error.db')
    queue_fd, queue_path = tempfile.mkstemp(suffix='_queue.db')
    checkpoint_fd, checkpoint_path = tempfile.mkstemp(suffix='_checkpoint.db')
    os.close(error_fd)
    os.close(queue_fd)
    os.close(checkpoint_fd)

    try:
        # Initialize all systems
        phase3 = Phase3IntegratedEngine(error_path, queue_path)
        background = BackgroundProcessor(max_concurrent=2)
        checkpoint = MemoryCheckpointSystem(checkpoint_path)
        profiler = PerformanceProfiler()
        resources = PredictiveResourceManager()
        parallel = MultiTrackParallelEngine(max_tracks=2)

        # Execute work with all systems
        @profiler.profile('integrated_work')
        def do_work():
            return "work_done"

        # Save checkpoint
        checkpoint.save_checkpoint(
            task_id="integration_test",
            description="Full integration test",
            current_task="Testing all systems",
            overall_plan="Verify integration",
            completed_steps=["Initialize"],
            next_steps=["Execute", "Verify"],
            progress=0.3
        )

        # Execute action through Phase 3
        result = phase3.execute_action("test_integration", do_work)

        # Run background task
        bg_task_id = background.run_async("bg_test", "Background", lambda: "bg_done")
        bg_result = background.get_result(bg_task_id, timeout=2.0)

        # Check resources
        resource_status = resources.check_resources()

        # Get stats from all systems
        phase3_stats = phase3.get_comprehensive_stats()
        bg_stats = background.get_stats()
        checkpoint_stats = checkpoint.get_stats()
        profiler_summary = profiler.get_summary()
        parallel_stats = parallel.get_stats()

        # Verify integration
        assert result == "work_done"
        assert bg_result == "bg_done"
        assert phase3_stats['phase3']['total_actions'] > 0
        assert checkpoint_stats['total_checkpoints'] > 0
        assert profiler_summary['total_operations'] > 0

        # Cleanup
        background.shutdown(wait=False)

    finally:
        for path in [error_path, queue_path, checkpoint_path]:
            if os.path.exists(path):
                os.unlink(path)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
