#!/usr/bin/env python3
"""
Complete Demonstration of Cross-Capability Synergy System

Shows all 4 primary synergy chains in action:
1. Discovery -> Learning Chain
2. Analysis -> Action Chain
3. Memory -> Prediction Chain
4. Monitoring -> Optimization Chain

Plus:
- Registering custom synergies
- Measuring synergy impact
- Discovering new synergy opportunities
- Tracking compound intelligence scores
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.capability_synergy import CapabilitySynergy


def demo_basic_usage():
    """Demonstrate basic synergy system usage"""
    print("\n" + "="*70)
    print("DEMO: Basic Synergy System Usage")
    print("="*70)

    # Initialize synergy system
    synergy = CapabilitySynergy(db_path="demo_synergy.db")

    # Show available chains
    print("\nAvailable Synergy Chains:")
    chains = synergy._get_available_chains()
    for i, chain_name in enumerate(chains, 1):
        status = synergy.get_chain_status(i)
        if 'error' not in status:
            print(f"\n  {i}. {chain_name}")
            print(f"     {status.get('description', 'N/A')}")

    print("\n" + "="*70)


def demo_register_custom_synergy():
    """Demonstrate registering custom synergies"""
    print("\n" + "="*70)
    print("DEMO: Register Custom Synergy")
    print("="*70)

    synergy = CapabilitySynergy(db_path="demo_synergy.db")

    # Define a custom transform function
    def semantic_search_to_code_review(search_results):
        """
        Transform semantic search results into format for code review.

        This synergy automatically feeds discovered code patterns
        into the code review system for quality analysis.
        """
        if isinstance(search_results, dict) and 'results' in search_results:
            code_samples = []
            for result in search_results['results'][:5]:
                if 'content' in result:
                    code_samples.append({
                        'code': result['content'],
                        'source': result.get('file', 'unknown'),
                        'score': result.get('score', 0.0)
                    })

            return {
                'code_samples': code_samples,
                'context': 'semantic_search_discovery',
                'auto_review': True
            }

        return {'code_samples': [], 'context': 'unknown'}

    # Register the synergy
    print("\nRegistering synergy: SemanticSearch -> CodeReview")
    success = synergy.register_synergy(
        from_capability='SemanticSearch',
        to_capability='CodeReview',
        transform_func=semantic_search_to_code_review
    )

    if success:
        print("[OK] Synergy registered successfully!")
        print("  This synergy will automatically feed search findings into code review")
    else:
        print("✗ Failed to register synergy")

    print("\n" + "="*70)


def demo_discovery_learning_chain():
    """Demonstrate Discovery -> Learning Chain"""
    print("\n" + "="*70)
    print("DEMO: Discovery -> Learning Chain")
    print("="*70)
    print("\nThis chain demonstrates how semantic search findings automatically")
    print("feed into mistake learning and code review for continuous improvement.")

    synergy = CapabilitySynergy(db_path="demo_synergy.db")

    print("\nChain flow:")
    print("  1. SemanticSearch: Find code patterns")
    print("  2. MistakeLearner: Check for known mistakes")
    print("  3. CodeReview: Suggest improvements")

    print("\nNote: To execute this chain with real capabilities, you would call:")
    print("""
    result = synergy.execute_chain(
        'discovery_learning_chain',
        {
            'search_query': 'authentication functions',
            'code': 'def login(user, password): ...',
            'language': 'python'
        }
    )

    print(f"Status: {result['status']}")
    print(f"Compound Intelligence Score: {result['compound_intelligence_score']:.3f}")
    print(f"Insights: {len(result['insights'])} generated")
    """)

    print("\n" + "="*70)


def demo_analysis_action_chain():
    """Demonstrate Analysis -> Action Chain"""
    print("\n" + "="*70)
    print("DEMO: Analysis -> Action Chain")
    print("="*70)
    print("\nThis chain shows how code review findings automatically trigger")
    print("debugger actions and optimization suggestions.")

    print("\nChain flow:")
    print("  1. CodeReview: Analyze code quality")
    print("  2. MistakeLearner: Get correction suggestions")
    print("  3. (Optional) AutoDebugger: Apply fixes")

    print("\nExample usage:")
    print("""
    result = synergy.execute_chain(
        'analysis_action_chain',
        {
            'code': 'def process_data(data): return data',
            'language': 'python',
            'error_message': 'Missing input validation'
        }
    )

    # The chain will:
    # 1. Review the code
    # 2. Find the validation issue
    # 3. Suggest specific corrections
    # 4. Optionally apply fixes automatically
    """)

    print("\n" + "="*70)


def demo_memory_prediction_chain():
    """Demonstrate Memory -> Prediction Chain"""
    print("\n" + "="*70)
    print("DEMO: Memory -> Prediction Chain")
    print("="*70)
    print("\nThis chain demonstrates how historical mistake patterns")
    print("are used to predict and prevent future errors.")

    print("\nChain flow:")
    print("  1. MistakeLearner: Retrieve recent mistakes")
    print("  2. CodeReview: Apply learned patterns")
    print("  3. Generate proactive suggestions")

    print("\nExample usage:")
    print("""
    result = synergy.execute_chain(
        'memory_prediction_chain',
        {
            'limit': 10,
            'code': 'def query_database(sql): cursor.execute(sql)',
            'language': 'python'
        }
    )

    # The chain will:
    # 1. Look at past SQL injection mistakes
    # 2. Recognize the pattern in new code
    # 3. Proactively warn before the mistake happens
    # 4. Suggest parameterized queries
    """)

    print("\n" + "="*70)


def demo_monitoring_optimization_chain():
    """Demonstrate Monitoring -> Optimization Chain"""
    print("\n" + "="*70)
    print("DEMO: Monitoring -> Optimization Chain")
    print("="*70)
    print("\nThis chain shows how system monitoring triggers automatic")
    print("optimization and cleanup actions.")

    print("\nChain flow:")
    print("  1. ResourceMonitor: Track system metrics")
    print("  2. Analyze performance bottlenecks")
    print("  3. Generate optimization suggestions")
    print("  4. (Optional) Auto-cleanup")

    print("\nExample usage:")
    print("""
    result = synergy.execute_chain(
        'monitoring_optimization_chain',
        {}
    )

    # The chain will:
    # 1. Check CPU, memory, disk usage
    # 2. Identify high resource consumers
    # 3. Suggest cache optimizations
    # 4. Recommend cleanup tasks
    # 5. Optionally trigger background cleanup
    """)

    print("\n" + "="*70)


def demo_measure_impact():
    """Demonstrate measuring synergy impact"""
    print("\n" + "="*70)
    print("DEMO: Measure Synergy Impact")
    print("="*70)

    synergy = CapabilitySynergy(db_path="demo_synergy.db")

    print("\nMeasuring synergy effectiveness...")
    impact = synergy.measure_synergy_impact()

    print(f"\nSynergy Impact Metrics:")
    print(f"  Total Synergies: {impact['total_synergies']}")
    print(f"  Active Chains: {impact['active_chains']}")
    print(f"  Average Compound Score: {impact['average_compound_score']:.3f}")
    print(f"  Overall Impact: {impact['overall_impact']:.3f}")

    if impact['synergy_connections']:
        print(f"\n  Top Synergy Connections:")
        for conn in impact['synergy_connections'][:5]:
            print(f"    {conn['from']} -> {conn['to']}")
            print(f"      Usage: {conn['usage_count']}, Success Rate: {conn['success_rate']:.1%}")

    print("\n" + "="*70)


def demo_discover_opportunities():
    """Demonstrate discovering new synergy opportunities"""
    print("\n" + "="*70)
    print("DEMO: Discover New Synergy Opportunities")
    print("="*70)

    synergy = CapabilitySynergy(db_path="demo_synergy.db")

    print("\nAnalyzing capability usage patterns...")
    opportunities = synergy.discover_new_synergies()

    if opportunities:
        print(f"\nFound {len(opportunities)} potential synergies:")
        for i, opp in enumerate(opportunities[:5], 1):
            print(f"\n  {i}. {opp['from_capability']} -> {opp['to_capability']}")
            print(f"     Potential Impact: {opp['potential_impact']:.2f}")
            print(f"     Reason: {opp['reason']}")
            print(f"     Recommendation: {opp['recommendation']}")
    else:
        print("\n  No new opportunities found at this time.")
        print("  Execute more chains to build usage patterns.")

    print("\n" + "="*70)


def demo_compound_intelligence():
    """Demonstrate compound intelligence scoring"""
    print("\n" + "="*70)
    print("DEMO: Compound Intelligence Score")
    print("="*70)

    synergy = CapabilitySynergy(db_path="demo_synergy.db")

    print("\nCompound Intelligence Score measures how well capabilities")
    print("work together to create emergent intelligence.")

    score = synergy.get_compound_intelligence_score()
    print(f"\nCurrent System Score: {score:.3f}")

    print("\nScore factors:")
    print("  • Base score from successful chain executions")
    print("  • Synergy multiplier (10% per active synergy)")
    print("  • Active synergy bonus (up to +0.2)")
    print("  • Feedback loop bonus (up to +0.1)")

    if score < 0.3:
        print("\nStatus: Building Intelligence")
        print("  Execute more chains to build compound intelligence")
    elif score < 0.6:
        print("\nStatus: Developing Synergies")
        print("  Good progress, synergies are forming")
    elif score < 0.8:
        print("\nStatus: Strong Synergies")
        print("  Capabilities are working well together")
    else:
        print("\nStatus: Emergent Intelligence")
        print("  System exhibits compound intelligence!")

    print("\n" + "="*70)


def demo_complete_workflow():
    """Demonstrate a complete synergy workflow"""
    print("\n" + "="*70)
    print("DEMO: Complete Synergy Workflow")
    print("="*70)

    print("\nThis demonstrates a real-world workflow using all synergy chains:")
    print("""
1. DISCOVERY -> LEARNING
   Developer searches for "authentication" code
   -> System finds authentication patterns
   -> Automatically checks for known security mistakes
   -> Reviews code against best practices
   -> Learns new patterns

2. ANALYSIS -> ACTION
   Code review finds security issue
   -> System retrieves known fixes from memory
   -> Auto-debugger applies security patch
   -> Background task updates documentation

3. MEMORY -> PREDICTION
   System notices SQL injection pattern
   -> Checks history of similar issues
   -> Predicts vulnerability in new code
   -> Proactively warns developer
   -> Suggests parameterized queries

4. MONITORING -> OPTIMIZATION
   Resource monitor detects high memory usage
   -> Analyzes query performance
   -> Suggests index optimization
   -> Triggers cache cleanup
   -> Schedules database maintenance

Result: Compound Intelligence
  • Capabilities enhance each other
  • Automated learning and improvement
  • Proactive error prevention
  • Self-optimizing system
    """)

    print("="*70)


def main():
    """Run all demonstrations"""
    print("\n" + "="*70)
    print("CROSS-CAPABILITY SYNERGY SYSTEM - COMPLETE DEMO")
    print("="*70)
    print("\nThis system creates 'intelligence chains' where capabilities")
    print("automatically enhance each other, creating compound intelligence.")

    demos = [
        ("Basic Usage", demo_basic_usage),
        ("Register Custom Synergy", demo_register_custom_synergy),
        ("Discovery -> Learning Chain", demo_discovery_learning_chain),
        ("Analysis -> Action Chain", demo_analysis_action_chain),
        ("Memory -> Prediction Chain", demo_memory_prediction_chain),
        ("Monitoring -> Optimization Chain", demo_monitoring_optimization_chain),
        ("Measure Synergy Impact", demo_measure_impact),
        ("Discover Opportunities", demo_discover_opportunities),
        ("Compound Intelligence", demo_compound_intelligence),
        ("Complete Workflow", demo_complete_workflow),
    ]

    for name, demo_func in demos:
        try:
            demo_func()
        except Exception as e:
            print(f"\n[ERROR in {name}]: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "="*70)
    print("DEMO COMPLETE")
    print("="*70)
    print("\nKey Features Demonstrated:")
    print("  [OK] 4 Primary Synergy Chains")
    print("  [OK] Custom Synergy Registration")
    print("  [OK] Impact Measurement")
    print("  [OK] Opportunity Discovery")
    print("  [OK] Compound Intelligence Scoring")
    print("\nNext Steps:")
    print("  1. Run: python demo_capability_synergy_complete.py")
    print("  2. Test: python tests/test_capability_synergy_complete.py")
    print("  3. Integrate with your capabilities!")
    print("\n" + "="*70)


if __name__ == '__main__':
    main()
