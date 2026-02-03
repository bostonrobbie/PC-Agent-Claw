#!/usr/bin/env python3
"""
Capability Synergy Engine - Demonstration

Shows how intelligence chains connect capabilities to create emergent intelligence.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.capability_synergy import CapabilitySynergyEngine


def print_header(title):
    """Print a formatted header"""
    print("\n" + "="*70)
    print(f" {title}")
    print("="*70)


def print_section(title):
    """Print a formatted section"""
    print(f"\n--- {title} ---")


def demo_predefined_chains():
    """Demo the predefined intelligence chains"""
    print_header("PREDEFINED INTELLIGENCE CHAINS")

    engine = CapabilitySynergyEngine()

    chains = [
        (1, "Code Analysis Chain"),
        (2, "Learning Chain"),
        (3, "Performance Chain"),
        (4, "Security Deep Scan"),
        (5, "Continuous Improvement")
    ]

    for chain_id, chain_name in chains:
        status = engine.get_chain_status(chain_id)
        print_section(chain_name)
        print(f"Description: {status['description']}")
        print(f"Status: {'Enabled' if status['enabled'] else 'Disabled'}")
        print(f"Executions: {status.get('executions', {})}")
        if status.get('last_executed'):
            print(f"Last Executed: {status['last_executed']}")


def demo_custom_chain():
    """Demo creating a custom intelligence chain"""
    print_header("CREATING CUSTOM INTELLIGENCE CHAIN")

    engine = CapabilitySynergyEngine()

    print("\nDefining 'security_audit_chain'...")
    print("Steps:")
    print("  1. Semantic search for authentication code")
    print("  2. Security scan for vulnerabilities")
    print("  3. Learn from any issues found")

    chain_id = engine.define_chain(
        name="security_audit_chain",
        description="Comprehensive security audit with learning",
        steps=[
            {
                'capability_name': 'SemanticSearch',
                'capability_module': 'search.semantic_search',
                'capability_class': 'SemanticCodeSearch',
                'method_name': 'search',
                'input_mapping': {'query': 'search_query'},
                'output_key': 'search_results',
                'config': {}
            },
            {
                'capability_name': 'SecurityScanner',
                'capability_module': 'security.security_monitor',
                'capability_class': 'SecurityMonitor',
                'method_name': 'scan_code',
                'input_mapping': {'code': 'code_to_scan'},
                'output_key': 'security_results',
                'config': {}
            },
            {
                'capability_name': 'MistakeLearner',
                'capability_module': 'learning.mistake_learner',
                'capability_class': 'MistakeLearner',
                'method_name': 'record_security_issue',
                'input_mapping': {'issues': 'security_results'},
                'output_key': 'learning_results',
                'config': {}
            }
        ],
        trigger_type='manual'
    )

    print(f"\n[OK] Chain created with ID: {chain_id}")

    status = engine.get_chain_status(chain_id)
    print(f"[OK] Chain '{status['name']}' ready for execution")


def demo_chain_execution():
    """Demo executing a chain"""
    print_header("EXECUTING INTELLIGENCE CHAIN")

    engine = CapabilitySynergyEngine()

    # Create a simple demo chain
    print("\nCreating demo chain...")
    chain_id = engine.define_chain(
        name="demo_execution_chain",
        description="Demo chain for execution showcase",
        steps=[
            {
                'capability_name': 'DemoStep1',
                'capability_module': 'tests.test_capability_synergy',
                'capability_class': 'MockCapability',
                'method_name': 'search',
                'input_mapping': {'query': 'search_query'},
                'output_key': 'step1_results',
                'config': {}
            },
            {
                'capability_name': 'DemoStep2',
                'capability_module': 'tests.test_capability_synergy',
                'capability_class': 'MockCapability',
                'method_name': 'scan_code',
                'input_mapping': {'code': 'code'},
                'output_key': 'step2_results',
                'config': {}
            }
        ]
    )

    print(f"[OK] Chain created (ID: {chain_id})")

    print("\nExecuting chain...")
    result = engine.execute_chain(
        chain_id,
        initial_input={
            'search_query': 'authentication patterns',
            'code': 'def login(username, password): return True'
        }
    )

    print(f"\n[OK] Execution completed!")
    print(f"  Status: {result['status']}")
    print(f"  Duration: {result['duration_seconds']:.3f}s")
    print(f"  Steps completed: {len(result['step_results'])}")
    print(f"  Insights generated: {len(result['insights'])}")

    print("\nStep Results:")
    for step in result['step_results']:
        status_icon = "[OK]" if step['status'] == 'success' else "[FAIL]"
        print(f"  {status_icon} Step {step['step']}: {step['capability']} - {step['status']}")
        if 'result_summary' in step:
            print(f"      Result: {step['result_summary']}")

    print("\nInsights:")
    for insight in result['insights']:
        print(f"  - {insight}")


def demo_synergy_discovery():
    """Demo synergy pattern discovery"""
    print_header("EMERGENT SYNERGY PATTERN DISCOVERY")

    engine = CapabilitySynergyEngine()

    # Execute some chains to create patterns
    print("\nExecuting chains to discover patterns...")

    chain_id = engine.define_chain(
        name="pattern_demo_chain",
        description="Chain for pattern discovery",
        steps=[
            {
                'capability_name': 'Search',
                'capability_module': 'tests.test_capability_synergy',
                'capability_class': 'MockCapability',
                'method_name': 'search',
                'input_mapping': {'query': 'query'},
                'output_key': 'results',
                'config': {}
            },
            {
                'capability_name': 'Analysis',
                'capability_module': 'tests.test_capability_synergy',
                'capability_class': 'MockCapability',
                'method_name': 'scan_code',
                'input_mapping': {'code': 'code'},
                'output_key': 'analysis',
                'config': {}
            }
        ]
    )

    # Execute multiple times
    for i in range(3):
        engine.execute_chain(chain_id, initial_input={'query': f'test_{i}', 'code': 'test'})
        print(f"  [OK] Execution {i+1} completed")

    print("\nDiscovering emergent patterns...")
    patterns = engine.discover_emergent_patterns()

    print(f"\n[OK] Found {len(patterns)} pattern(s):")
    for pattern in patterns:
        print(f"\n  Pattern: {pattern['pattern_name']}")
        print(f"    Capabilities: {', '.join(pattern['capabilities_involved'])}")
        print(f"    Description: {pattern['description']}")
        print(f"    Impact Score: {pattern['impact_score']:.2f}")
        print(f"    Occurrences: {pattern['occurrences']}")


def demo_insights():
    """Demo synergy insights"""
    print_header("SYNERGY INSIGHTS")

    engine = CapabilitySynergyEngine()

    # Execute a chain
    chain_id = engine.define_chain(
        name="insights_demo_chain",
        description="Chain for insights demo",
        steps=[
            {
                'capability_name': 'SecurityScanner',
                'capability_module': 'tests.test_capability_synergy',
                'capability_class': 'MockCapability',
                'method_name': 'scan_code',
                'input_mapping': {'code': 'code'},
                'output_key': 'security',
                'config': {}
            },
            {
                'capability_name': 'CodeReviewer',
                'capability_module': 'tests.test_capability_synergy',
                'capability_class': 'MockCapability',
                'method_name': 'suggest_improvements',
                'input_mapping': {'code': 'code'},
                'output_key': 'review',
                'config': {}
            }
        ]
    )

    print("\nExecuting chain to generate insights...")
    engine.execute_chain(chain_id, initial_input={'code': 'test code'})

    print("\nRetrieving synergy insights...")
    insights = engine.get_synergy_insights(limit=10)

    print(f"\n[OK] Found {len(insights)} insight(s):")
    for insight in insights[:5]:  # Show first 5
        print(f"\n  Chain: {insight['chain_name']}")
        print(f"  Type: {insight['insight_type']}")
        print(f"  Insight: {insight['insight_text']}")
        print(f"  Confidence: {insight['confidence']:.2f}")


def demo_scheduling():
    """Demo chain scheduling"""
    print_header("CHAIN SCHEDULING")

    engine = CapabilitySynergyEngine()

    print("\nScheduling chains for automatic execution...")

    # Schedule performance monitoring
    chain_id = 3  # Performance chain
    success = engine.schedule_chain(
        chain_id,
        trigger='time_interval',
        config={'interval_seconds': 3600}  # Every hour
    )

    if success:
        print("[OK] Performance chain scheduled (every hour)")

    # Schedule security scan
    chain_id = 4  # Security deep scan
    success = engine.schedule_chain(
        chain_id,
        trigger='time_interval',
        config={'interval_seconds': 7200}  # Every 2 hours
    )

    if success:
        print("[OK] Security scan scheduled (every 2 hours)")

    print("\n[Note] Scheduled chains will execute automatically based on triggers")


def demo_metrics():
    """Demo chain metrics"""
    print_header("CHAIN PERFORMANCE METRICS")

    engine = CapabilitySynergyEngine()

    # Create and execute a chain multiple times
    chain_id = engine.define_chain(
        name="metrics_demo_chain",
        description="Chain for metrics demo",
        steps=[
            {
                'capability_name': 'Test',
                'capability_module': 'tests.test_capability_synergy',
                'capability_class': 'MockCapability',
                'method_name': 'test_method',
                'input_mapping': {'input_data': 'input'},
                'output_key': 'output',
                'config': {}
            }
        ]
    )

    print(f"\nExecuting chain multiple times to collect metrics...")
    for i in range(5):
        engine.execute_chain(chain_id, initial_input={'input': f'test_{i}'})
        print(f"  [OK] Execution {i+1} completed")

    print("\nRetrieving metrics...")
    status = engine.get_chain_status(chain_id)

    print(f"\n[OK] Chain Metrics:")
    print(f"  Total Executions: {sum(status['executions'].values())}")
    print(f"  Successful: {status['executions'].get('completed', 0)}")
    print(f"  Failed: {status['executions'].get('failed', 0)}")
    print(f"  Average Duration: {status['avg_duration_seconds']:.3f}s")
    print(f"  Insights Generated: {status['insights_count']}")


def main():
    """Run all demos"""
    print("\n")
    print("="*70)
    print(" CAPABILITY SYNERGY ENGINE - COMPREHENSIVE DEMONSTRATION")
    print("="*70)
    print("\n This demo showcases the cross-capability synergy system that")
    print(" connects multiple capabilities through intelligent chains to")
    print(" create emergent intelligence and comprehensive insights.")

    try:
        demo_predefined_chains()
        demo_custom_chain()
        demo_chain_execution()
        demo_synergy_discovery()
        demo_insights()
        demo_scheduling()
        demo_metrics()

        print("\n")
        print("="*70)
        print(" DEMONSTRATION COMPLETE")
        print("="*70)
        print("\n Key Features Demonstrated:")
        print("  [OK] 5 predefined intelligence chains")
        print("  [OK] Custom chain definition")
        print("  [OK] Chain execution with multiple steps")
        print("  [OK] Emergent pattern discovery")
        print("  [OK] Synergy insights generation")
        print("  [OK] Automatic scheduling")
        print("  [OK] Performance metrics tracking")
        print("\n The Capability Synergy Engine is ready to connect your")
        print(" capabilities and unlock emergent intelligence!")
        print()

    except Exception as e:
        print(f"\n[ERROR] Demo failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
