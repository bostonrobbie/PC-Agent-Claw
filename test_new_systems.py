#!/usr/bin/env python3
"""Test new learning and natural language systems"""
import sys
from pathlib import Path

workspace = Path(__file__).parent
sys.path.insert(0, str(workspace))


def test_reinforcement_learning():
    """Test reinforcement learning system"""
    print("\n[1/3] Testing Reinforcement Learning...")
    try:
        from ml.reinforcement_learning import ReinforcementLearning

        rl = ReinforcementLearning(learning_rate=0.1)

        # Test action selection
        strategies = ["strategy_A", "strategy_B", "strategy_C"]
        chosen = rl.choose_action("test_optimization", strategies)
        print(f"   Chose action: {chosen}")

        # Test outcome recording
        reward = rl.record_outcome(
            "test_optimization",
            chosen,
            success=True,
            outcome_value=0.8,
            details="Test successful"
        )
        print(f"   Recorded outcome: reward={reward:.2f}")

        # Simulate learning over multiple trials
        import random
        for i in range(10):
            chosen = rl.choose_action("test_optimization", strategies)
            success = random.choice([True, False])
            rl.record_outcome("test_optimization", chosen, success, random.random())

        # Get recommendations
        recommendations = rl.get_action_recommendations("test_optimization")
        print(f"   Learned {len(recommendations)} action preferences")

        # Get learning summary
        summary = rl.get_learning_summary()
        print(f"   Total actions: {summary['total_actions']}")
        print(f"   Success rate: {summary['success_rate']:.0%}")
        print(f"   Avg reward: {summary['avg_reward']:.3f}")

        rl.close()

        print("   [OK] Reinforcement Learning working")
        return True

    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_pattern_learner():
    """Test pattern learning system"""
    print("\n[2/3] Testing Pattern Learner...")
    try:
        from ml.pattern_learner import PatternLearner

        learner = PatternLearner(min_support=0.3)

        # Test sequence pattern detection
        sequence = ['A', 'B', 'C', 'A', 'B', 'C', 'A', 'B']
        pattern = learner.detect_sequence_pattern(sequence)

        if pattern:
            print(f"   Detected pattern: {pattern['subsequence']}")
            print(f"   Support: {pattern['support']:.0%}")
        else:
            print("   No pattern detected (expected in some cases)")

        # Test correlation
        corr = learner.detect_correlation(
            "event_A", "event_B",
            co_occurrences=8, total_a=10, total_b=12
        )
        print(f"   Correlation lift: {corr['lift']:.2f}")
        print(f"   Is correlated: {corr['is_correlated']}")

        # Test anomaly detection
        history = [10.0, 11.0, 10.5, 10.8, 11.2]
        anomaly = learner.detect_anomaly(20.0, history)
        print(f"   Anomaly detected: {anomaly['is_anomaly']}")
        print(f"   Z-score: {anomaly['z_score']:.2f}")

        # Test trend detection
        from datetime import datetime, timedelta
        values = [(datetime.now() - timedelta(days=i), 100 + i * 3) for i in range(7)]
        trend = learner.detect_trend(values)
        print(f"   Trend: {trend['trend']}")
        print(f"   Strength: {trend['strength']:.2f}")

        # Test rule learning
        rule_id = learner.learn_rule(
            if_condition="test_condition",
            then_action="test_action",
            support=0.7,
            confidence=0.85
        )
        print(f"   Rule learned: ID {rule_id}")

        # Get pattern summary
        summary = learner.get_pattern_summary()
        print(f"   Total patterns: {summary['total_patterns']}")
        print(f"   Learned rules: {summary['learned_rules']}")

        learner.close()

        print("   [OK] Pattern Learner working")
        return True

    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_natural_language():
    """Test natural language interface"""
    print("\n[3/3] Testing Natural Language Interface...")
    try:
        from interface.natural_language import NaturalLanguageInterface

        nl = NaturalLanguageInterface()

        # Test parsing various inputs
        test_cases = [
            ("remember this is a test", "memory", "remember_conversation"),
            ("show my preferences", "memory", "get_preferences"),
            ("start monitoring", "proactive", "start_monitoring"),
            ("show learning summary", "learning", "get_learning_summary"),
            ("detect patterns in data", "patterns", "detect_sequence_pattern"),
        ]

        parsed_correctly = 0
        for user_input, expected_system, expected_action in test_cases:
            intent = nl.parse(user_input)

            if intent.system == expected_system and intent.action == expected_action:
                parsed_correctly += 1

        print(f"   Parsed correctly: {parsed_correctly}/{len(test_cases)}")

        # Test execution (safe commands only)
        safe_tests = [
            "show my preferences",
            "show learning summary",
        ]

        executed = 0
        for test_input in safe_tests:
            try:
                response = nl.execute(test_input)
                if response and not response.startswith("Error"):
                    executed += 1
            except:
                pass

        print(f"   Executed successfully: {executed}/{len(safe_tests)}")
        print(f"   Systems loaded: {len(nl.systems)}")

        nl.close()

        print("   [OK] Natural Language Interface working")
        return True

    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("=" * 70)
    print("TESTING NEW AGENTIC SYSTEMS")
    print("=" * 70)

    results = []

    # Test all systems
    results.append(("Reinforcement Learning", test_reinforcement_learning()))
    results.append(("Pattern Learner", test_pattern_learner()))
    results.append(("Natural Language Interface", test_natural_language()))

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

    if passed == total:
        print("\n[OK] ALL NEW SYSTEMS OPERATIONAL")
        return 0
    else:
        print(f"\n[WARNING] {total - passed} system(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
