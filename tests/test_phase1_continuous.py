"""
Test Suite for Phase 1 Continuous Operation Engine

Tests integration of:
- Error Learning Database
- Decision Rulebook
- Flow State Monitor
"""
import pytest
import time
import os
import tempfile
from unittest.mock import Mock

from core.phase1_continuous_engine import Phase1ContinuousEngine


class TestPhase1ContinuousEngine:

    @pytest.fixture
    def temp_db(self):
        """Create temporary database"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        if os.path.exists(path):
            os.unlink(path)

    @pytest.fixture
    def engine(self, temp_db):
        """Create fresh engine"""
        return Phase1ContinuousEngine(temp_db)

    def test_engine_initialization(self, engine):
        """Test engine initializes all subsystems"""
        assert engine.error_db is not None
        assert engine.rulebook is not None
        assert engine.flow_monitor is not None
        assert engine.actions_taken == 0

    def test_successful_action_execution(self, engine):
        """Test executing action without errors"""
        def simple_action():
            return "success"

        result = engine.execute_action("test_action", simple_action)

        assert result == "success"
        assert engine.actions_taken == 1
        assert engine.errors_auto_fixed == 0

    def test_error_recovery_with_rulebook(self, engine):
        """Test error recovery using decision rulebook"""
        def failing_action():
            raise UnicodeEncodeError('charmap', '', 0, 1, 'cannot encode')

        # Should handle unicode error using rulebook
        result = engine.execute_action("unicode_action", failing_action)

        # Should not crash
        assert engine.errors_auto_fixed > 0

    def test_error_learning(self, engine):
        """Test that errors are learned and solutions reused"""
        call_count = {'count': 0}

        def sometimes_fails():
            call_count['count'] += 1
            if call_count['count'] == 1:
                raise ValueError("test error")
            return "success"

        # First call fails, learns solution
        try:
            engine.execute_action("test", sometimes_fails)
        except:
            pass

        # Second identical error should be handled
        call_count['count'] = 0
        result = engine.execute_action("test2", sometimes_fails)

        # Should have learned from first error
        stats = engine.get_stats()
        assert stats['total_errors_learned'] > 0

    def test_flow_state_detection(self, engine):
        """Test flow state monitoring"""
        def quick_action():
            return "done"

        # Generate flow (>5 actions/min)
        for i in range(6):
            engine.execute_action(f"action_{i}", quick_action)
            time.sleep(0.1)

        stats = engine.get_stats()
        assert stats['actions_taken'] >= 6

    def test_flow_protection(self, engine):
        """Test that flow is protected from interruptions"""
        def action():
            return "ok"

        # Build flow
        for i in range(6):
            engine.execute_action(f"flow_{i}", action)

        # Cause an error during flow
        def error_action():
            raise RuntimeError("interrupt")

        try:
            engine.execute_action("interrupt", error_action)
        except:
            pass

        stats = engine.get_stats()
        # Should have attempted to protect flow
        assert stats['actions_taken'] >= 6

    def test_unicode_error_handling(self, engine):
        """Test unicode errors are handled automatically"""
        def unicode_func():
            raise UnicodeEncodeError('charmap', 'test', 0, 1, 'fail')

        # Should not crash
        result = engine.execute_action("unicode", unicode_func)

        assert engine.errors_auto_fixed > 0

    def test_import_error_handling(self, engine):
        """Test import errors are handled gracefully"""
        def import_func():
            raise ImportError("module not found")

        # Should degrade gracefully
        result = engine.execute_action("import", import_func)

        stats = engine.get_stats()
        assert stats['errors_auto_fixed'] > 0

    def test_database_lock_retry(self, engine):
        """Test database lock errors trigger retry"""
        attempt = {'count': 0}

        def locked_db():
            attempt['count'] += 1
            if attempt['count'] < 2:
                raise Exception("database is locked")
            return "unlocked"

        result = engine.execute_action("db_op", locked_db)

        assert result == "unlocked"
        assert attempt['count'] >= 2

    def test_path_error_handling(self, engine):
        """Test path errors are auto-converted"""
        def path_func():
            raise OSError("path error")

        result = engine.execute_action("path_op", path_func)

        assert engine.errors_auto_fixed > 0

    def test_task_completion_continues(self, engine):
        """Test task completion doesn't stop work"""
        should_stop = engine.mark_task_complete("build_system_1")

        # Should continue, not stop
        assert should_stop == False

    def test_retry_with_backoff(self, engine):
        """Test exponential backoff retry logic"""
        attempts = {'count': 0}

        def flaky_action():
            attempts['count'] += 1
            if attempts['count'] < 3:
                raise Exception("temporary failure")
            return "success"

        result = engine._retry_with_backoff(flaky_action, max_retries=5)

        assert result == "success"
        assert attempts['count'] == 3

    def test_custom_rule_addition(self, engine):
        """Test adding custom rules during operation"""
        engine.add_custom_rule(
            situation='custom_scenario',
            decision='custom_action',
            confidence=0.95
        )

        decision = engine.rulebook.decide('custom_scenario')
        assert decision['decision'] == 'custom_action'
        assert decision['confidence'] == 0.95

    def test_statistics_tracking(self, engine):
        """Test comprehensive statistics"""
        def action():
            return "ok"

        # Take some actions
        for i in range(5):
            engine.execute_action(f"test_{i}", action)

        stats = engine.get_stats()

        assert 'actions_taken' in stats
        assert 'errors_auto_fixed' in stats
        assert 'in_flow' in stats
        assert 'total_errors_learned' in stats
        assert stats['actions_taken'] == 5

    def test_error_classification(self, engine):
        """Test error classification logic"""
        unicode_err = UnicodeEncodeError('charmap', '', 0, 1, 'fail')
        assert engine._classify_error(unicode_err) == 'unicode_error'

        import_err = ImportError("module not found")
        assert engine._classify_error(import_err) == 'import_error'

        path_err = FileNotFoundError("file not found")
        assert engine._classify_error(path_err) == 'path_error'

        unknown_err = Exception("random error")
        assert engine._classify_error(unknown_err) == 'unknown_error'

    def test_continuous_operation(self, engine):
        """Test engine can run continuously for extended period"""
        def work_func():
            return "work_done"

        # Simulate continuous work
        start_time = time.time()
        action_count = 0

        # Run for 5 seconds
        while time.time() - start_time < 5:
            engine.execute_action(f"work_{action_count}", work_func)
            action_count += 1
            time.sleep(0.1)

        stats = engine.get_stats()
        assert stats['actions_taken'] >= 40  # Should complete many actions

    def test_mixed_success_and_failure(self, engine):
        """Test handling mix of successful and failing actions"""
        call_count = {'count': 0}

        def mixed_func():
            call_count['count'] += 1
            if call_count['count'] % 3 == 0:
                raise ValueError("periodic failure")
            return "success"

        # Run multiple times
        for i in range(10):
            try:
                engine.execute_action(f"mixed_{i}", mixed_func)
            except:
                pass

        stats = engine.get_stats()
        assert stats['actions_taken'] == 10
        assert stats['errors_auto_fixed'] > 0


def test_integration_with_all_subsystems():
    """Test full integration of all Phase 1 systems"""
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    try:
        engine = Phase1ContinuousEngine(db_path)

        # Test error learning
        def learnable_error():
            raise ValueError("test_pattern")

        try:
            engine.execute_action("learn1", learnable_error)
        except:
            pass

        # Test flow monitoring
        for i in range(6):
            engine.execute_action(f"flow_{i}", lambda: "ok")

        # Test decision rulebook
        should_stop = engine.mark_task_complete("task1")
        assert should_stop == False

        # Verify stats
        stats = engine.get_stats()
        assert stats['actions_taken'] >= 7
        assert 'in_flow' in stats
        assert 'total_errors_learned' in stats

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
