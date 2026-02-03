"""
Example: Integrating Self-Improvement Loop with Intelligence Hub

This example demonstrates how to use the Self-Improvement Loop system
to enable the Intelligence Hub to analyze and improve itself autonomously.

Usage:
    python examples/self_improvement_integration.py

Author: AI Self-Improvement System
Created: 2026-02-03
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from autonomous.self_improvement import SelfImprovementLoop
from intelligence_hub import IntelligenceHub


def main():
    """Demonstrate self-improvement integration with Intelligence Hub"""
    print("="*80)
    print("SELF-IMPROVEMENT LOOP - INTELLIGENCE HUB INTEGRATION")
    print("="*80)
    print("\nThis example shows how Intelligence Hub can improve itself autonomously.\n")

    # Initialize Intelligence Hub
    print("[Step 1] Initializing Intelligence Hub...")
    hub = IntelligenceHub()
    hub.start()
    print("[OK] Intelligence Hub initialized\n")

    # Initialize Self-Improvement Loop
    print("[Step 2] Initializing Self-Improvement Loop...")
    improvement_loop = SelfImprovementLoop(
        db_path="intelligence_hub_improvements.db",
        workspace_path=hub.workspace_path
    )
    print("[OK] Self-Improvement Loop ready\n")

    # Step 3: Analyze current performance
    print("[Step 3] Analyzing Intelligence Hub Performance...")
    print("-"*80)
    performance = improvement_loop.analyze_own_performance(session_id=hub.session_id)

    print("\nCurrent Performance:")
    metrics = performance['metrics']
    for metric, value in metrics.items():
        if metric not in ['timestamp', 'session_id']:
            target = improvement_loop.TARGET_METRICS.get(metric, 'N/A')
            status = "✓" if isinstance(target, (int, float)) and value <= target else "⚠"
            print(f"  {status} {metric:20} : {value:>10} (target: {target})")

    # Step 4: Identify bottlenecks
    print(f"\n[Step 4] Identifying Performance Bottlenecks...")
    print("-"*80)
    bottlenecks = improvement_loop.identify_bottlenecks()

    if bottlenecks:
        print(f"\nFound {len(bottlenecks)} bottlenecks:\n")
        for i, bottleneck in enumerate(bottlenecks[:5], 1):
            severity_icon = {
                'low': '⚡',
                'medium': '⚠',
                'high': '🔴',
                'critical': '🚨'
            }
            icon = severity_icon.get(bottleneck['severity'], '•')
            print(f"{i}. {icon} {bottleneck['metric_name']} [{bottleneck['severity'].upper()}]")
            print(f"   Impact: {bottleneck['impact_score']:.1f}/100")
            print(f"   {bottleneck['description']}\n")
    else:
        print("\nNo significant bottlenecks found! System is performing well.\n")

    # Step 5: Generate improvements
    print(f"[Step 5] Generating Improvement Suggestions...")
    print("-"*80)
    improvements = improvement_loop.generate_improvements(max_suggestions=3)

    if improvements:
        print(f"\nGenerated {len(improvements)} improvement suggestions:\n")
        for i, improvement in enumerate(improvements, 1):
            print(f"{i}. {improvement['description']}")
            print(f"   Type: {improvement['suggestion_type']}")
            print(f"   Expected improvement: +{improvement['expected_improvement']:.1f}%")
            print(f"   Confidence: {improvement['confidence']:.0%}")
            print(f"   Status: {improvement['status']}\n")

        # Step 6: Test first improvement
        print(f"[Step 6] Testing Improvement #{improvements[0]['id']} in Sandbox...")
        print("-"*80)
        test_result = improvement_loop.test_improvement(improvements[0]['id'])

        print(f"\nTest Results:")
        print(f"  Success: {test_result.get('success', False)}")
        print(f"  Performance change: {test_result.get('performance_change_percent', 0):+.1f}%")
        print(f"  Execution time: {test_result.get('execution_time', 0):.3f}s")

        if test_result.get('errors'):
            print(f"  Errors: {len(test_result['errors'])}")
            for error in test_result['errors'][:2]:
                print(f"    - {error[:100]}...")

        # If test was successful and approved, optionally apply
        improved_improvement = improvement_loop._get_improvement(improvements[0]['id'])
        if improved_improvement['status'] == 'approved':
            print(f"\n[Step 7] Improvement approved! Ready to apply.")
            print("-"*80)
            print("\nTo apply this improvement, uncomment the following line:")
            print(f"# improvement_loop.apply_improvement({improvements[0]['id']})")
            print("\nNote: Applying improvements modifies the codebase.")
            print("      Always review changes before applying in production.")

    else:
        print("\nNo improvements needed at this time.\n")

    # Step 8: Show statistics
    print(f"\n[Step 8] Self-Improvement Statistics")
    print("-"*80)
    stats = improvement_loop.get_stats()

    print(f"\nOverall Statistics:")
    print(f"  Performance snapshots: {stats['total_performance_snapshots']}")
    print(f"  Unresolved bottlenecks: {stats['unresolved_bottlenecks']}")
    print(f"  Resolved bottlenecks: {stats['resolved_bottlenecks']}")
    print(f"  Successfully applied improvements: {stats['successfully_applied']}")
    print(f"  Rolled back improvements: {stats['rolled_back']}")
    print(f"  Overall success rate: {stats['success_rate']:.1f}%")

    # Step 9: Show improvement history
    print(f"\n[Step 9] Recent Improvement History")
    print("-"*80)
    history = improvement_loop.get_improvement_history(limit=5)

    if history:
        print("\nRecent improvements:")
        for item in history:
            print(f"  • ID {item['id']:3} [{item['status']:10}] {item['description'][:60]}")
            if item.get('applied_at'):
                print(f"          Applied: {item['applied_at'][:19]}")
            if item.get('rolled_back'):
                print(f"          Rolled back: {item['rolled_back_at'][:19]}")
    else:
        print("\nNo improvement history yet.")

    # Clean up
    print(f"\n[Step 10] Shutting down...")
    print("-"*80)
    hub.stop()

    print("\n" + "="*80)
    print("[SUCCESS] Self-Improvement Integration Complete!")
    print("="*80)
    print("\nKey Takeaways:")
    print("  1. Intelligence Hub can analyze its own performance")
    print("  2. System automatically identifies bottlenecks")
    print("  3. AI generates targeted improvement suggestions")
    print("  4. Improvements are tested safely before application")
    print("  5. Complete audit trail maintained in database")
    print(f"\nDatabase: intelligence_hub_improvements.db")
    print("="*80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Shutting down gracefully...")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
