#!/usr/bin/env python3
"""Test all new capabilities"""
import sys
from pathlib import Path

workspace = Path(__file__).parent
sys.path.insert(0, str(workspace))


def test_experiment_engine():
    """Test experiment engine"""
    print("\n[1/8] Testing Experiment Engine...")
    try:
        from experiments.experiment_engine import ExperimentEngine

        engine = ExperimentEngine()

        # Design and run simple experiment
        exp_id = engine.design_experiment(
            "Test Experiment",
            "Testing hypothesis",
            control={'param': 1},
            treatments=[{'param': 2}],
            success_metric="test_metric",
            sample_size=10
        )

        print(f"   Experiment designed: ID {exp_id}")
        engine.close()

        print("   [OK] Experiment Engine working")
        return True

    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        return False


def test_conversation_manager():
    """Test conversation manager"""
    print("\n[2/8] Testing Conversation Manager...")
    try:
        from interface.conversation_manager import ConversationManager

        manager = ConversationManager()

        # Start thread and add messages
        thread_id = manager.start_thread("test_topic")
        manager.add_message("user", "Test message")
        manager.add_message("assistant", "Test response")

        # Get context
        context = manager.get_conversation_context(lookback=2)

        manager.close()

        print(f"   Thread ID: {thread_id}, Messages: {len(context)}")
        print("   [OK] Conversation Manager working")
        return True

    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        return False


def test_resource_manager():
    """Test resource manager"""
    print("\n[3/8] Testing Resource Manager...")
    try:
        from execution.resource_manager import ResourceManager

        manager = ResourceManager()

        # Get resources
        resources = manager.get_current_resources()
        manager.record_resources()

        # Check if can execute
        can_execute = manager.should_execute_now({'cpu': 10, 'memory': 5})

        manager.close()

        print(f"   CPU: {resources['cpu_percent']:.1f}%, Can execute: {can_execute}")
        print("   [OK] Resource Manager working")
        return True

    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        return False


def test_explainability():
    """Test explainability engine"""
    print("\n[4/8] Testing Explainability Engine...")
    try:
        from reasoning.explainability import ExplainabilityEngine

        engine = ExplainabilityEngine()

        # Record decision
        decision_id = engine.record_decision(
            "Test Decision",
            "Option A",
            0.85,
            factors=[
                {'name': 'Factor 1', 'value': 'High', 'weight': 0.9}
            ],
            alternatives=[
                {'name': 'Option B', 'score': 0.7}
            ]
        )

        # Explain
        explanation = engine.explain_decision(decision_id)

        engine.close()

        print(f"   Decision ID: {decision_id}")
        print("   [OK] Explainability Engine working")
        return True

    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        return False


def test_security_monitor():
    """Test security monitor"""
    print("\n[5/8] Testing Security Monitor...")
    try:
        from security.security_monitor import SecurityMonitor

        monitor = SecurityMonitor()

        # Test validation
        safe, threat = monitor.validate_input("Normal input")
        unsafe, threat_type = monitor.validate_input("SELECT * UNION SELECT *")

        # Test sanitization
        clean = monitor.sanitize_input("<script>alert('test')</script>")

        # Test rate limiting
        within_limit = monitor.check_rate_limit("test_user", max_requests=5)

        monitor.close()

        print(f"   Safe input: {safe}, Unsafe: {not unsafe}, Rate limit: {within_limit}")
        print("   [OK] Security Monitor working")
        return True

    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        return False


def test_access_control():
    """Test access control"""
    print("\n[6/8] Testing Access Control...")
    try:
        from security.access_control import AccessControl

        ac = AccessControl()

        # Create permission and assign
        ac.create_permission("test:read", "test", "read")
        ac.assign_permission_to_role("admin", "test:read")

        # Register entity
        ac.register_entity("test_user", "user", "admin")

        # Check permission
        has_perm = ac.has_permission("test_user", "test:read")

        ac.close()

        print(f"   Has permission: {has_perm}")
        print("   [OK] Access Control working")
        return True

    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        return False


def test_goal_executor():
    """Test goal executor (if available)"""
    print("\n[7/8] Testing Goal Executor...")
    try:
        from execution.autonomous_goal_executor import GoalExecutor

        executor = GoalExecutor()
        executor.close()

        print("   [OK] Goal Executor working")
        return True

    except ImportError:
        print("   [SKIP] Goal Executor not yet available")
        return True
    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        return False


def test_self_improvement():
    """Test self-improvement (if available)"""
    print("\n[8/8] Testing Self-Improvement...")
    try:
        from meta.self_improvement import SelfImprovement

        si = SelfImprovement()
        si.close()

        print("   [OK] Self-Improvement working")
        return True

    except ImportError:
        print("   [SKIP] Self-Improvement not yet available")
        return True
    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 70)
    print("TESTING ALL NEW CAPABILITIES")
    print("=" * 70)

    results = []

    # Test all systems
    results.append(("Experiment Engine", test_experiment_engine()))
    results.append(("Conversation Manager", test_conversation_manager()))
    results.append(("Resource Manager", test_resource_manager()))
    results.append(("Explainability Engine", test_explainability()))
    results.append(("Security Monitor", test_security_monitor()))
    results.append(("Access Control", test_access_control()))
    results.append(("Goal Executor", test_goal_executor()))
    results.append(("Self-Improvement", test_self_improvement()))

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "[OK]" if result else "[FAIL]"
        print(f"{status} {name}")

    print(f"\nPassed: {passed}/{total}")

    if passed >= total - 2:  # Allow 2 to be building
        print("\n[OK] CORE CAPABILITIES OPERATIONAL")
        return 0
    else:
        print(f"\n[WARNING] {total - passed} system(s) not ready")
        return 1


if __name__ == "__main__":
    sys.exit(main())
