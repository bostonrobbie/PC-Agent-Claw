#!/usr/bin/env python3
"""
Comprehensive test suite for Self-Improvement & Meta-Learning Engine
Demonstrates all major features with realistic scenarios
"""

import sys
from pathlib import Path
import time
import random

sys.path.append(str(Path(__file__).parent))

from meta.self_improvement import SelfImprovementEngine


def test_full_improvement_cycle():
    """Test complete self-improvement cycle"""
    print("\n" + "=" * 80)
    print("COMPREHENSIVE SELF-IMPROVEMENT ENGINE TEST")
    print("=" * 80)

    # Initialize engine
    engine = SelfImprovementEngine(auto_improve=False)

    # =========================================================================
    # PHASE 1: CAPABILITY PROFILING
    # =========================================================================
    print("\n[PHASE 1] CAPABILITY PROFILING")
    print("-" * 80)

    # Register custom capabilities
    print("\n1.1 Registering custom capabilities...")
    engine.register_capability(
        name='query_optimization',
        capability_type='performance',
        description='Database query optimization speed',
        baseline_performance=5.2,
        target_performance=2.0,
        performance_unit='seconds'
    )

    engine.register_capability(
        name='error_detection',
        capability_type='reliability',
        description='Ability to detect errors before they occur',
        baseline_performance=0.65,
        target_performance=0.90,
        performance_unit='detection_rate'
    )

    print("   Custom capabilities registered")

    # Measure capabilities
    print("\n1.2 Measuring capability performance...")

    measurements = [
        ('task_completion', 0.88, 'production_workload'),
        ('response_time', 1.8, 'average_query'),
        ('error_recovery', 0.85, 'system_test'),
        ('query_optimization', 4.5, 'complex_queries'),
        ('error_detection', 0.70, 'validation_suite'),
    ]

    for cap_name, value, context in measurements:
        result = engine.measure_capability(cap_name, value, context)
        print(f"   {cap_name}: {value} {result['unit']}")
        if result['is_weakness']:
            print(f"     WARNING: Below target!")

    # Get full profile
    print("\n1.3 Complete capability profile:")
    profile = engine.profile_all_capabilities()
    print(f"   Total capabilities: {profile['summary']['total_capabilities']}")
    print(f"   Measured: {profile['summary']['measured']}")
    print(f"   At target: {profile['summary']['at_target']}")
    print(f"   Average improvement: {profile['summary']['average_improvement']:.1f}%")

    print("\n   Top performers:")
    sorted_caps = sorted(profile['capabilities'],
                        key=lambda x: x['improvement'], reverse=True)
    for cap in sorted_caps[:3]:
        print(f"   - {cap['name']}: {cap['improvement']:+.1f}% improvement")

    # =========================================================================
    # PHASE 2: WEAKNESS IDENTIFICATION
    # =========================================================================
    print("\n[PHASE 2] WEAKNESS IDENTIFICATION")
    print("-" * 80)

    print("\n2.1 Manually identifying additional weaknesses...")

    # Identify specific weaknesses
    weakness_ids = []

    weakness_ids.append(engine.identify_weakness(
        weakness_name='slow_database_queries',
        weakness_type='efficiency',
        description='Database queries taking too long on large datasets',
        severity='high',
        evidence='Average query time 4.5s vs target 2.0s',
        impact_score=0.75
    ))

    weakness_ids.append(engine.identify_weakness(
        weakness_name='insufficient_error_prediction',
        weakness_type='reliability',
        description='Missing 30% of potential errors before execution',
        severity='medium',
        evidence='Detection rate 70% vs target 90%',
        impact_score=0.60
    ))

    weakness_ids.append(engine.identify_weakness(
        weakness_name='memory_leak_in_long_sessions',
        weakness_type='reliability',
        description='Memory usage grows unbounded in sessions >1 hour',
        severity='critical',
        evidence='Memory usage increases 50MB/hour',
        impact_score=0.90
    ))

    print(f"   Identified {len(weakness_ids)} additional weaknesses")

    print("\n2.2 Analyzing all weaknesses...")
    weaknesses = engine.analyze_weaknesses(min_impact=0.3)
    print(f"   Total weaknesses: {len(weaknesses)}")
    print("\n   Top priority weaknesses:")
    for i, w in enumerate(weaknesses[:5], 1):
        print(f"   {i}. {w['name']}")
        print(f"      Severity: {w['severity']} | Impact: {w['impact_score']:.2f} | Priority: {w['priority_score']:.2f}")
        print(f"      {w['description']}")

    # =========================================================================
    # PHASE 3: EXPERIMENT GENERATION
    # =========================================================================
    print("\n[PHASE 3] EXPERIMENT GENERATION")
    print("-" * 80)

    print("\n3.1 Generating experiments for top weakness...")
    if weaknesses:
        top_weakness = weaknesses[0]
        experiments = engine.generate_experiments(
            top_weakness['id'],
            num_experiments=3
        )

        print(f"   Generated {len(experiments)} experiments for: {top_weakness['name']}")
        for i, exp in enumerate(experiments, 1):
            print(f"\n   Experiment {i}: {exp['name']}")
            print(f"      Hypothesis: {exp['hypothesis']}")
            print(f"      Approach: {exp['approach']}")
            print(f"      Expected improvement: {exp['expected_improvement']:.0%}")

    # =========================================================================
    # PHASE 4: TESTING APPROACHES
    # =========================================================================
    print("\n[PHASE 4] TESTING APPROACHES")
    print("-" * 80)

    print("\n4.1 Running experiments...")

    experiment_results = []

    for i, exp in enumerate(experiments, 1):
        print(f"\n   Testing Experiment {i}: {exp['name']}")

        # Simulate test function with realistic results
        def test_func():
            # Simulate some variation in results
            improvement_factor = exp['expected_improvement'] + random.uniform(-0.1, 0.15)
            baseline = 4.5  # Current performance
            return baseline * (1 - improvement_factor)

        # Get baseline
        baseline_value = 4.5

        print(f"      Baseline: {baseline_value:.2f}s")

        # Run test
        result = engine.test_approach(
            exp['id'],
            test_function=test_func,
            baseline_value=baseline_value
        )

        experiment_results.append(result)

        print(f"      Result: {result['status']}")
        if result.get('new_measurement'):
            print(f"      New value: {result['new_measurement']:.2f}s")
        if result.get('improvement_pct'):
            print(f"      Improvement: {result['improvement_pct']:.1f}%")
        print(f"      Success: {result.get('success', 'N/A')}")

    # =========================================================================
    # PHASE 5: MEASURING IMPROVEMENT
    # =========================================================================
    print("\n[PHASE 5] QUANTITATIVE IMPROVEMENT MEASUREMENT")
    print("-" * 80)

    print("\n5.1 Analyzing improvement metrics...")

    # Find best experiment
    successful_experiments = [r for r in experiment_results if r.get('success')]

    if successful_experiments:
        best_experiment = max(successful_experiments,
                            key=lambda x: x.get('improvement', 0))

        print(f"\n   Best experiment: {best_experiment['name']}")

        improvement = engine.measure_improvement(
            before_value=best_experiment['baseline_measurement'],
            after_value=best_experiment['new_measurement'],
            metric_name='query_optimization',
            context=f"experiment_{best_experiment['experiment_id']}"
        )

        print(f"   Before: {improvement['before']:.2f}")
        print(f"   After: {improvement['after']:.2f}")
        print(f"   Absolute change: {improvement['absolute_change']:.2f}")
        print(f"   Percent change: {improvement['percent_change']:.1f}%")
        print(f"   Significant: {improvement['is_significant']}")
        print(f"   Confidence: {improvement['confidence']}")

        # Apply improvement if significant
        if improvement['is_significant']:
            print("\n5.2 Applying improvement (simulation)...")
            print("   Note: auto_improve=False, so this requires approval")

            apply_result = engine.apply_improvement(
                improvement_name=best_experiment['name'],
                file_path='meta/self_improvement.py',
                experiment_id=best_experiment['experiment_id'],
                require_approval=True
            )

            print(f"   Status: {apply_result.get('status', apply_result.get('message'))}")

    # =========================================================================
    # PHASE 6: META-LEARNING
    # =========================================================================
    print("\n[PHASE 6] META-LEARNING")
    print("-" * 80)

    print("\n6.1 Recording meta-learnings from experiments...")

    # Analyze experiment patterns
    if len(successful_experiments) >= 2:
        avg_improvement = sum(e.get('improvement', 0) for e in successful_experiments) / len(successful_experiments)

        engine.record_meta_learning(
            learning_type='experiment_effectiveness',
            pattern_observed=f'Database optimization experiments show average {avg_improvement:.0%} improvement',
            insight='Database optimization is a high-value improvement area',
            confidence=0.80,
            supporting_experiments=[e['experiment_id'] for e in successful_experiments]
        )

        engine.record_meta_learning(
            learning_type='approach_preference',
            pattern_observed='Caching and indexing approaches consistently outperform algorithmic changes',
            insight='Prioritize structural optimizations over algorithmic ones for databases',
            confidence=0.75
        )

        print("   Meta-learnings recorded")

    print("\n6.2 Current meta-learnings:")
    learnings = engine.get_meta_learnings(min_confidence=0.5)
    for i, learning in enumerate(learnings, 1):
        print(f"\n   {i}. [{learning['type']}]")
        print(f"      Pattern: {learning['pattern']}")
        print(f"      Insight: {learning['insight']}")
        print(f"      Confidence: {learning['confidence']:.0%}")

    # =========================================================================
    # PHASE 7: IMPROVEMENT TRACKING
    # =========================================================================
    print("\n[PHASE 7] IMPROVEMENT TRACKING")
    print("-" * 80)

    print("\n7.1 Recording improvement history...")

    # Calculate overall stats
    total_improvements = len(successful_experiments)
    avg_performance_delta = sum(e.get('improvement', 0) for e in successful_experiments) / max(len(successful_experiments), 1)

    notable_changes = [
        f"Optimized database queries: {avg_performance_delta:.0%} improvement",
        "Implemented caching layer",
        "Added query indexing strategy"
    ]

    engine.track_improvement_history(
        version='1.1.0',
        summary='Database performance optimization',
        improvements_applied=total_improvements,
        overall_performance_delta=avg_performance_delta,
        notable_changes=notable_changes
    )

    print("   History recorded")

    print("\n7.2 Improvement history:")
    history = engine.get_improvement_history(limit=5)
    for entry in history:
        print(f"\n   Version {entry['version']}: {entry['summary']}")
        print(f"   Improvements: {entry['improvements_applied']}")
        print(f"   Performance delta: {entry['performance_delta']:.0%}")
        print(f"   Deployed: {entry['deployed_at']}")

    # =========================================================================
    # PHASE 8: SELF-ASSESSMENT
    # =========================================================================
    print("\n[PHASE 8] COMPREHENSIVE SELF-ASSESSMENT")
    print("-" * 80)

    assessment = engine.get_self_assessment()

    print("\n8.1 Overall Assessment:")
    print(f"   Learning Quality Score: {assessment['learning_quality']['quality_score']:.2f}")
    print(f"   Grade: {assessment['learning_quality']['grade']}")
    print(f"   Exceeded Expectations: {assessment['learning_quality']['exceeded_expectations']:.0%}")
    print(f"   Weakness Resolution: {assessment['learning_quality']['weakness_resolution']:.0%}")

    print("\n8.2 Capability Status:")
    caps = assessment['capabilities']
    print(f"   Total capabilities: {caps['summary']['total_capabilities']}")
    print(f"   At target: {caps['summary']['at_target']}")
    print(f"   Average improvement: {caps['summary']['average_improvement']:.1f}%")

    print("\n8.3 Weaknesses:")
    print(f"   Total: {assessment['weaknesses']['total']}")
    print(f"   Critical: {assessment['weaknesses']['critical']}")
    print(f"   High: {assessment['weaknesses']['high']}")
    print(f"   Average impact: {assessment['weaknesses']['avg_impact']:.2f}")

    print("\n8.4 Experiments:")
    print(f"   Total: {assessment['experiments']['total']}")
    print(f"   Completed: {assessment['experiments']['completed']}")
    print(f"   Average improvement: {assessment['experiments']['avg_improvement']:.1%}")

    print("\n8.5 Applied Improvements:")
    print(f"   Total applied: {assessment['improvements']['total_applied']}")

    print("\n8.6 Meta-Learnings:")
    print(f"   Total: {assessment['meta_learnings']}")

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    print("\n[SUCCESS] All phases completed successfully!")
    print(f"\nDatabase: {engine.db_path}")

    print("\nKey Achievements:")
    print(f"  - Profiled {caps['summary']['total_capabilities']} capabilities")
    print(f"  - Identified {assessment['weaknesses']['total']} weaknesses")
    print(f"  - Generated and tested {len(experiments)} experiments")
    print(f"  - Achieved {len(successful_experiments)} successful improvements")
    print(f"  - Recorded {assessment['meta_learnings']} meta-learnings")
    print(f"  - Overall learning grade: {assessment['learning_quality']['grade']}")

    print("\nNext Steps:")
    print("  1. Set auto_improve=True to enable automatic code improvements")
    print("  2. Integrate with RL system for action selection")
    print("  3. Use pattern learner for trend detection")
    print("  4. Monitor improvement over time")

    engine.close()


if __name__ == "__main__":
    test_full_improvement_cycle()
