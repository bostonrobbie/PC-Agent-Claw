#!/usr/bin/env python3
"""
Quick test script for Autonomous Goal Execution System
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "execution"))

from autonomous_goal_executor import AutonomousGoalExecutor
from datetime import datetime, timedelta


def quick_test():
    """Quick functionality test"""
    print("Testing Autonomous Goal Execution System...")
    print("=" * 70)

    executor = AutonomousGoalExecutor()

    try:
        # Test 1: Create goal
        print("\n[TEST 1] Creating goal...")
        goal_id = executor.set_goal(
            goal_name="Test Goal",
            description="A test goal for verification",
            success_criteria=["Task 1", "Task 2", "Task 3"],
            priority=2
        )
        print(f"[PASS] Goal created: {goal_id}")

        # Test 2: Decompose
        print("\n[TEST 2] Decomposing goal...")
        task_ids = executor.decompose_goal(goal_id, use_reasoning=False)
        print(f"[PASS] Created {len(task_ids)} tasks")

        # Test 3: Execute task
        print("\n[TEST 3] Executing task...")
        result = executor.execute_task(task_ids[0], lambda: {"status": "ok"})
        print(f"[PASS] Task executed: {result}")

        # Test 4: Track progress
        print("\n[TEST 4] Tracking progress...")
        progress = executor.track_progress(goal_id)
        print(f"[PASS] Progress: {progress:.0%}")

        # Test 5: Get status
        print("\n[TEST 5] Getting status...")
        status = executor.get_goal_status(goal_id)
        print(f"[PASS] Status retrieved:")
        print(f"  - Goal: {status['goal_name']}")
        print(f"  - Progress: {status['progress']:.0%}")
        print(f"  - Completed: {status['completed_tasks']}/{status['total_tasks']}")
        print(f"  - Milestones: {status['achieved_milestones']}")

        # Test 6: Adapt plan
        print("\n[TEST 6] Testing plan adaptation...")
        executor.adapt_plan(goal_id, "Test adaptation", 0.2)
        status = executor.get_goal_status(goal_id)
        print(f"[PASS] Plan version: {status['plan_version']}")

        print("\n" + "=" * 70)
        print("[SUCCESS] All tests passed!")
        print("=" * 70)

        return True

    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        executor.close()


if __name__ == "__main__":
    success = quick_test()
    sys.exit(0 if success else 1)
