#!/usr/bin/env python3
"""
Capability Synergy Demo - Intelligence Chains in Action

This demo showcases the cross-capability synergy system creating automatic
intelligence chains where capabilities enhance each other.

Demonstrates all 5 synergy chains:
1. Discovery -> Learning Chain
2. Analysis -> Action Chain
3. Feedback -> Improvement Chain
4. Search -> Knowledge Chain
5. Security -> Prevention Chain
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.capability_synergy import CapabilitySynergy


def demo_discovery_learning_chain(synergy: CapabilitySynergy):
    """
    Demo: Discovery -> Learning Chain

    Flow: Semantic Search findings -> Mistake Learner -> Code Review suggestions
    Shows how search results automatically feed into learning systems
    """
    print("\n" + "="*70)
    print("1. DISCOVERY -> LEARNING CHAIN")
    print("="*70)
    print("\nDemonstrates: Search findings automatically feed into learning systems")
    print("Chain flow: SemanticSearch -> MistakeLearner -> CodeReview")

    # This chain would execute if capabilities are available
    print("\nChain Steps:")
    print("  1. Semantic Search finds relevant code patterns")
    print("  2. Patterns auto-feed to Mistake Learner for analysis")
    print("  3. Learner generates code review suggestions")
    print("  4. Suggestions stored in Persistent Memory for future use")

    print("\nBenefits:")
    print("  - Automatic learning from search discoveries")
    print("  - Code patterns become learning materials")
    print("  - Future code reviews use discovered patterns")

    # Show chain status
    chains = synergy._get_available_chains()
    if 'discovery_learning_chain' in chains:
        status = synergy.get_chain_status(1)
        print(f"\nChain Status: {status['name']}")
        print(f"Description: {status['description']}")
        print(f"Executions: {status.get('executions', {})}")


def demo_analysis_action_chain(synergy: CapabilitySynergy):
    """
    Demo: Analysis -> Action Chain

    Flow: Resource Monitor detects issue -> trigger optimization -> Background Task
    Shows how analysis automatically triggers corrective actions
    """
    print("\n" + "="*70)
    print("2. ANALYSIS -> ACTION CHAIN")
    print("="*70)
    print("\nDemonstrates: Analysis results trigger automatic corrective actions")
    print("Chain flow: CodeReview -> AutoDebugger -> BackgroundTask")

    print("\nChain Steps:")
    print("  1. Code Review identifies issues in codebase")
    print("  2. Issues trigger Auto Debugger automatically")
    print("  3. Debugger generates fix suggestions")
    print("  4. Background Task schedules fixes")

    print("\nBenefits:")
    print("  - Immediate action on detected issues")
    print("  - Automated problem resolution")
    print("  - Reduces manual intervention needed")

    print("\nExample Triggers:")
    print("  - High CPU usage -> Performance optimization")
    print("  - Error pattern detected -> Auto debugger runs")
    print("  - Code issue found -> Background fix task created")


def demo_feedback_improvement_chain(synergy: CapabilitySynergy):
    """
    Demo: Feedback -> Improvement Chain

    Flow: User feedback -> Persistent Memory -> Code Review preferences -> suggestions
    Shows how feedback creates continuous improvement loops
    """
    print("\n" + "="*70)
    print("3. FEEDBACK -> IMPROVEMENT CHAIN")
    print("="*70)
    print("\nDemonstrates: User feedback creates continuous improvement loops")
    print("Chain flow: Feedback -> Memory -> Preferences -> Future Suggestions")

    print("\nChain Steps:")
    print("  1. User provides feedback on code/suggestions")
    print("  2. Feedback stored in Persistent Memory")
    print("  3. Memory patterns extracted as preferences")
    print("  4. Preferences influence future code suggestions")

    print("\nBenefits:")
    print("  - System learns from user feedback")
    print("  - Preferences evolve over time")
    print("  - Increasingly personalized suggestions")

    print("\nExample Feedback Loop:")
    print("  User prefers:")
    print("    -> snake_case naming")
    print("    -> comprehensive docstrings")
    print("    -> type hints everywhere")
    print("  System remembers and suggests accordingly")


def demo_search_knowledge_chain(synergy: CapabilitySynergy):
    """
    Demo: Search -> Knowledge Chain

    Flow: Semantic Search -> Context Manager -> Internet Search -> Verified Facts -> Memory
    Shows how search results build a verified knowledge base
    """
    print("\n" + "="*70)
    print("4. SEARCH -> KNOWLEDGE CHAIN")
    print("="*70)
    print("\nDemonstrates: Search results build verified knowledge base")
    print("Chain flow: SemanticSearch -> Context -> InternetSearch -> FactVerify -> Memory")

    print("\nChain Steps:")
    print("  1. Semantic Search finds local code patterns")
    print("  2. Context Manager tracks search context")
    print("  3. Internet Search verifies with external sources")
    print("  4. Facts verified and confidence scored")
    print("  5. Verified knowledge stored in Persistent Memory")

    print("\nBenefits:")
    print("  - Local + global knowledge integration")
    print("  - Verified facts with confidence scores")
    print("  - Growing knowledge base over time")

    print("\nKnowledge Quality:")
    print("  - Local code patterns: High confidence")
    print("  - Internet-verified facts: Medium-High confidence")
    print("  - Unverified information: Low confidence (flagged)")


def demo_security_prevention_chain(synergy: CapabilitySynergy):
    """
    Demo: Security -> Prevention Chain

    Flow: Vulnerability found -> Mistake Learner records -> Similar patterns -> Warnings -> Notifications
    Shows how security findings prevent future vulnerabilities
    """
    print("\n" + "="*70)
    print("5. SECURITY -> PREVENTION CHAIN")
    print("="*70)
    print("\nDemonstrates: Security findings prevent future vulnerabilities")
    print("Chain flow: SecurityScan -> MistakeLearner -> PatternMatch -> Warnings -> Notifications")

    print("\nChain Steps:")
    print("  1. Security scanner finds vulnerability")
    print("  2. Mistake Learner records vulnerability pattern")
    print("  3. Future code checked against pattern database")
    print("  4. Similar patterns trigger proactive warnings")
    print("  5. Smart Notifications alert developer")

    print("\nBenefits:")
    print("  - Learn from security issues")
    print("  - Prevent similar vulnerabilities")
    print("  - Proactive security awareness")

    print("\nExample Prevention:")
    print("  Found: SQL Injection in login.py")
    print("    -> Pattern recorded: unsanitized user input")
    print("    -> Future code with similar pattern -> WARNING")
    print("    -> Developer notified before commit")


def demo_emergent_behaviors(synergy: CapabilitySynergy):
    """
    Demo: Emergent Behavior Detection

    Shows how the system discovers unexpected beneficial patterns
    where capabilities work together in ways not explicitly programmed
    """
    print("\n" + "="*70)
    print("6. EMERGENT BEHAVIOR DETECTION")
    print("="*70)
    print("\nDemonstrates: System discovers unexpected beneficial patterns")

    print("\nWhat are Emergent Behaviors?")
    print("  - Patterns not explicitly programmed")
    print("  - Beneficial interactions between capabilities")
    print("  - Discovered automatically through execution analysis")

    # Discover emergent patterns
    patterns = synergy.discover_emergent_patterns()

    if patterns:
        print(f"\nDiscovered {len(patterns)} emergent patterns:")
        for pattern in patterns:
            print(f"\n  Pattern: {pattern['pattern_name']}")
            print(f"    Capabilities: {', '.join(pattern['capabilities_involved'])}")
            print(f"    Impact Score: {pattern['impact_score']:.2f}")
            print(f"    Occurrences: {pattern['occurrences']}")
            print(f"    Description: {pattern['description']}")
    else:
        print("\n  No emergent patterns detected yet")
        print("  (Patterns emerge as chains are executed)")

    print("\nExample Emergent Behaviors:")
    print("  1. Search + Review -> Better refactoring suggestions")
    print("  2. Memory + Security -> Proactive vulnerability prevention")
    print("  3. Learning + Context -> Personalized code generation")


def demo_synergy_metrics(synergy: CapabilitySynergy):
    """
    Demo: Synergy Performance Metrics

    Shows effectiveness measurements and compound intelligence scoring
    """
    print("\n" + "="*70)
    print("7. SYNERGY PERFORMANCE METRICS")
    print("="*70)
    print("\nDemonstrates: Measuring synergy effectiveness")

    # Get synergy impact metrics
    impact = synergy.measure_synergy_impact()

    print("\nSynergy System Statistics:")
    print(f"  Total Synergies Registered: {impact['total_synergies']}")
    print(f"  Active Chains: {impact['active_chains']}")
    print(f"  Average Compound Score: {impact['average_compound_score']:.3f}")
    print(f"  Average Synergy Multiplier: {impact['average_synergy_multiplier']:.3f}")
    print(f"  Overall Impact: {impact['overall_impact']:.3f}")

    # Show synergy connections
    if impact['synergy_connections']:
        print("\nActive Synergy Connections:")
        for conn in impact['synergy_connections'][:5]:
            print(f"  {conn['from']} -> {conn['to']}")
            print(f"    Usage: {conn['usage_count']}, Success Rate: {conn['success_rate']:.1%}")

    # Show data flows
    if impact['data_flows']:
        print("\nData Flow Statistics:")
        for flow in impact['data_flows'][:5]:
            print(f"  {flow['from']} -> {flow['to']}")
            print(f"    Flows: {flow['flow_count']}, Avg Impact: {flow['avg_impact']:.2f}")

    # Compound intelligence score
    compound_score = synergy.get_compound_intelligence_score()
    print(f"\nCOMPOUND INTELLIGENCE SCORE: {compound_score:.3f}")
    print("  (Measures overall system intelligence from capability synergies)")


def demo_chain_visualization(synergy: CapabilitySynergy):
    """
    Demo: Chain Visualization

    Shows active chains and their data flow
    """
    print("\n" + "="*70)
    print("8. CHAIN VISUALIZATION")
    print("="*70)
    print("\nDemonstrates: Visualizing active chains and data flows")

    chains = synergy._get_available_chains()

    print(f"\nAvailable Chains ({len(chains)}):")
    for i, chain_name in enumerate(chains, 1):
        status = synergy.get_chain_status(i)
        if 'error' not in status:
            print(f"\n{i}. {status['name']}")
            print(f"   Description: {status['description']}")
            print(f"   Enabled: {status['enabled']}")
            print(f"   Last Executed: {status.get('last_executed', 'Never')}")
            print(f"   Avg Duration: {status.get('avg_duration_seconds', 0):.3f}s")
            print(f"   Insights Generated: {status.get('insights_count', 0)}")

    print("\nChain Execution Flow Visualization:")
    print("""
    +------------------+
    | Semantic Search  |
    +--------+---------+
             | (search results)
             v
    +------------------+
    | Mistake Learner  |---+
    +--------+---------+   | (synergy: patterns)
             |              |
             v              v
    +------------------+  +-------------------+
    |  Code Review     |  | Persistent Memory |
    +------------------+  +-------------------+
    """)


def demo_new_synergy_opportunities(synergy: CapabilitySynergy):
    """
    Demo: Discovering New Synergy Opportunities

    Shows how the system analyzes execution patterns to suggest new synergies
    """
    print("\n" + "="*70)
    print("9. NEW SYNERGY OPPORTUNITIES")
    print("="*70)
    print("\nDemonstrates: Automatic discovery of potential new synergies")

    opportunities = synergy.discover_new_synergies()

    if opportunities:
        print(f"\nFound {len(opportunities)} potential synergy opportunities:")
        for i, opp in enumerate(opportunities[:5], 1):
            print(f"\n{i}. {opp['from_capability']} -> {opp['to_capability']}")
            print(f"   Reason: {opp['reason']}")
            print(f"   Co-occurrence Count: {opp['co_occurrence_count']}")
            print(f"   Potential Impact: {opp['potential_impact']:.2f}")
            print(f"   Recommendation: {opp['recommendation']}")
    else:
        print("\nNo new synergy opportunities found at this time")
        print("(Execute chains to generate data for opportunity discovery)")


def demo_insights_report(synergy: CapabilitySynergy):
    """
    Demo: Synergy Insights Report

    Shows insights generated from capability synergies
    """
    print("\n" + "="*70)
    print("10. SYNERGY INSIGHTS REPORT")
    print("="*70)
    print("\nDemonstrates: Insights discovered through capability synergies")

    insights = synergy.get_synergy_insights(limit=10)

    if insights:
        print(f"\nRecent Insights ({len(insights)}):")
        for i, insight in enumerate(insights, 1):
            print(f"\n{i}. [{insight['insight_type'].upper()}] {insight['chain_name']}")
            print(f"   {insight['insight_text']}")
            print(f"   Confidence: {insight['confidence']:.1%}")
            print(f"   Discovered: {insight['discovered_at']}")
    else:
        print("\nNo insights generated yet")
        print("(Execute chains to generate insights)")

    print("\nInsight Types:")
    print("  - Synergy: Cross-capability discoveries")
    print("  - Pattern: Recurring behavioral patterns")
    print("  - Performance: Optimization opportunities")
    print("  - Security: Vulnerability warnings")


def main():
    """Run the complete capability synergy demo"""
    print("\n" + "="*70)
    print("CAPABILITY SYNERGY SYSTEM - COMPREHENSIVE DEMO")
    print("Intelligence Chains Where Capabilities Enhance Each Other")
    print("="*70)

    # Initialize synergy system
    print("\nInitializing Capability Synergy System...")
    synergy = CapabilitySynergy(db_path="demo_synergy.db")
    print("System initialized with default chains and synergies")

    # Run all demos
    demo_discovery_learning_chain(synergy)
    demo_analysis_action_chain(synergy)
    demo_feedback_improvement_chain(synergy)
    demo_search_knowledge_chain(synergy)
    demo_security_prevention_chain(synergy)
    demo_emergent_behaviors(synergy)
    demo_synergy_metrics(synergy)
    demo_chain_visualization(synergy)
    demo_new_synergy_opportunities(synergy)
    demo_insights_report(synergy)

    # Summary
    print("\n" + "="*70)
    print("DEMO COMPLETE - KEY TAKEAWAYS")
    print("="*70)
    print("\n1. Automatic Intelligence Chains")
    print("   - Capabilities enhance each other automatically")
    print("   - Data flows seamlessly between systems")

    print("\n2. Emergent Behavior Detection")
    print("   - System discovers unexpected beneficial patterns")
    print("   - Self-improving through pattern recognition")

    print("\n3. Compound Intelligence")
    print("   - System intelligence > sum of individual capabilities")
    print("   - Synergies create multiplicative benefits")

    print("\n4. Continuous Improvement")
    print("   - Feedback loops enable learning")
    print("   - New synergies discovered automatically")

    print("\n5. Real-World Applications")
    print("   - Security: Learn from vulnerabilities, prevent future issues")
    print("   - Code Quality: Continuous improvement from feedback")
    print("   - Knowledge: Build verified knowledge base over time")
    print("   - Performance: Automatic optimization triggers")

    print("\n" + "="*70)
    print("\nNext Steps:")
    print("  1. Execute chains with: synergy.execute_chain(chain_name, input_data)")
    print("  2. Register custom synergies with: synergy.register_synergy()")
    print("  3. Define new chains with: synergy.define_chain()")
    print("  4. Monitor metrics with: synergy.measure_synergy_impact()")
    print("  5. Discover patterns with: synergy.discover_emergent_patterns()")

    print("\nThe system is now ready for production use!")
    print("="*70 + "\n")


if __name__ == '__main__':
    main()
