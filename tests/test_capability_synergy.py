#!/usr/bin/env python3
"""
Tests for Capability Synergy Engine

Tests intelligence chains, synergy discovery, and cross-capability workflows.
"""

import sys
import os
import tempfile
import sqlite3
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.capability_synergy import (
    CapabilitySynergyEngine,
    ChainStep,
    ChainDefinition,
    ChainExecution,
    SynergyPattern
)


class MockCapability:
    """Mock capability for testing"""

    def __init__(self, **kwargs):
        self.config = kwargs

    def test_method(self, input_data):
        """Test method that returns simple data"""
        return {
            'result': f"Processed: {input_data}",
            'count': 42,
            'issues': ['issue1', 'issue2']
        }

    def search(self, query):
        """Mock search method"""
        return {
            'results': [
                {'file': 'test.py', 'score': 0.9},
                {'file': 'example.py', 'score': 0.7}
            ],
            'count': 2
        }

    def scan_code(self, code):
        """Mock security scan"""
        return {
            'vulnerabilities': [
                {'type': 'SQL Injection', 'severity': 'high'},
                {'type': 'XSS', 'severity': 'medium'}
            ],
            'issues': 2
        }

    def suggest_improvements(self, code):
        """Mock code review"""
        return {
            'recommendations': [
                'Add type hints',
                'Improve error handling',
                'Add docstrings'
            ],
            'patterns': ['naming_convention', 'code_structure']
        }

    def check_for_known_mistakes(self, code):
        """Mock mistake checking"""
        return {
            'warnings': [
                'Similar mistake seen before in project X',
                'This pattern failed in previous implementation'
            ],
            'count': 2
        }

    def get_learned_patterns(self):
        """Mock pattern retrieval"""
        return {
            'patterns': [
                {'name': 'prefer_comprehensions', 'confidence': 0.9},
                {'name': 'async_best_practices', 'confidence': 0.85}
            ]
        }

    def get_current_metrics(self):
        """Mock resource monitoring"""
        return {
            'cpu_percent': 45.2,
            'memory_percent': 67.8,
            'disk_percent': 82.1,
            'alerts': ['High disk usage']
        }

    def get_optimization_suggestions(self):
        """Mock optimization suggestions"""
        return {
            'recommendations': [
                'Clean up temp files',
                'Archive old logs',
                'Optimize database queries'
            ]
        }

    def record_security_issue(self, issues):
        """Mock security issue recording"""
        if isinstance(issues, dict) and 'vulnerabilities' in issues:
            count = len(issues['vulnerabilities'])
        else:
            count = 1
        return {
            'recorded': count,
            'status': 'success'
        }

    def review_and_learn(self, code):
        """Mock review and learn"""
        return {
            'learnings': [
                'User prefers snake_case for variables',
                'User likes comprehensive docstrings'
            ],
            'patterns': 2
        }

    def find_similar_code(self, pattern):
        """Mock finding similar code"""
        return {
            'matches': [
                {'file': 'utils.py', 'similarity': 0.92},
                {'file': 'helpers.py', 'similarity': 0.88}
            ]
        }

    def apply_learned_preferences(self, code, patterns):
        """Mock applying preferences"""
        return {
            'changes': 5,
            'improvements': ['Applied naming convention', 'Added type hints']
        }

    def apply_patterns(self, code, patterns):
        """Mock applying patterns"""
        return {
            'applied': 3,
            'improvements': ['Refactored code', 'Improved structure']
        }


def test_engine_initialization():
    """Test engine initialization"""
    print("\n=== Test: Engine Initialization ===")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name

    try:
        engine = CapabilitySynergyEngine(db_path=db_path)

        # Check database was created
        assert os.path.exists(db_path), "Database should be created"

        # Check tables exist
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in c.fetchall()]
        conn.close()

        expected_tables = [
            'chain_definitions',
            'chain_executions',
            'chain_metrics',
            'synergy_patterns',
            'chain_schedules',
            'chain_insights'
        ]

        for table in expected_tables:
            assert table in tables, f"Table {table} should exist"

        print("[OK] Engine initialized successfully")
        print(f"[OK] All {len(expected_tables)} tables created")

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_default_chains():
    """Test that default chains are created"""
    print("\n=== Test: Default Chains ===")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name

    try:
        engine = CapabilitySynergyEngine(db_path=db_path)

        # Check default chains
        expected_chains = [
            'discovery_learning_chain',
            'analysis_action_chain',
            'memory_prediction_chain',
            'monitoring_optimization_chain'
        ]

        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute('SELECT name FROM chain_definitions')
        chains = [row[0] for row in c.fetchall()]
        conn.close()

        for chain_name in expected_chains:
            assert chain_name in chains, f"Default chain {chain_name} should exist"

        print(f"[OK] All {len(expected_chains)} default chains created")

        # Check chain status
        for i in range(1, 5):
            status = engine.get_chain_status(i)
            assert 'name' in status, "Chain status should include name"
            assert 'description' in status, "Chain status should include description"
            print(f"[OK] Chain {i}: {status['name']}")

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_define_custom_chain():
    """Test defining a custom chain"""
    print("\n=== Test: Define Custom Chain ===")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name

    try:
        engine = CapabilitySynergyEngine(db_path=db_path)

        # Define a simple custom chain
        chain_id = engine.define_chain(
            name="test_chain",
            description="Test chain for unit tests",
            steps=[
                {
                    'capability_name': 'TestCapability',
                    'capability_module': 'tests.test_capability_synergy',
                    'capability_class': 'MockCapability',
                    'method_name': 'test_method',
                    'input_mapping': {'input_data': 'initial_input'},
                    'output_key': 'test_result',
                    'config': {}
                }
            ],
            trigger_type='manual'
        )

        assert chain_id > 0, "Chain ID should be positive"
        print(f"[OK] Custom chain created with ID: {chain_id}")

        # Check chain was stored
        status = engine.get_chain_status(chain_id)
        assert status['name'] == 'test_chain', "Chain name should match"
        assert status['description'] == 'Test chain for unit tests', "Description should match"
        print("[OK] Chain details stored correctly")

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_chain_execution():
    """Test executing a chain"""
    print("\n=== Test: Chain Execution ===")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name

    try:
        engine = CapabilitySynergyEngine(db_path=db_path)

        # Define a test chain
        chain_id = engine.define_chain(
            name="execution_test_chain",
            description="Chain to test execution",
            steps=[
                {
                    'capability_name': 'TestCapability',
                    'capability_module': 'tests.test_capability_synergy',
                    'capability_class': 'MockCapability',
                    'method_name': 'test_method',
                    'input_mapping': {'input_data': 'test_input'},
                    'output_key': 'result1',
                    'config': {}
                },
                {
                    'capability_name': 'TestCapability2',
                    'capability_module': 'tests.test_capability_synergy',
                    'capability_class': 'MockCapability',
                    'method_name': 'test_method',
                    'input_mapping': {'input_data': 'result1'},
                    'output_key': 'result2',
                    'config': {}
                }
            ]
        )

        # Execute the chain
        result = engine.execute_chain(
            'execution_test_chain',
            {'test_input': 'Hello World'}
        )

        assert result['status'] in ['completed', 'partial'], "Chain should complete"
        assert 'step_results' in result, "Should have step results"
        assert len(result['step_results']) == 2, "Should have 2 step results"
        assert 'insights' in result, "Should have insights"
        assert result['duration_seconds'] >= 0, "Duration should be non-negative"

        print(f"[OK] Chain executed successfully")
        print(f"[OK] Status: {result['status']}")
        print(f"[OK] Steps completed: {len(result['step_results'])}")
        print(f"[OK] Insights generated: {len(result['insights'])}")
        print(f"[OK] Duration: {result['duration_seconds']:.3f}s")

        # Check execution was recorded
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM chain_executions WHERE chain_id=?', (chain_id,))
        count = c.fetchone()[0]
        conn.close()

        assert count == 1, "Execution should be recorded"
        print("[OK] Execution recorded in database")

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_synergy_insights():
    """Test synergy insight generation"""
    print("\n=== Test: Synergy Insights ===")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name

    try:
        engine = CapabilitySynergyEngine(db_path=db_path)

        # Create and execute a chain
        chain_id = engine.define_chain(
            name="insight_test_chain",
            description="Chain to test insight generation",
            steps=[
                {
                    'capability_name': 'SearchCapability',
                    'capability_module': 'tests.test_capability_synergy',
                    'capability_class': 'MockCapability',
                    'method_name': 'search',
                    'input_mapping': {'query': 'search_query'},
                    'output_key': 'search_results',
                    'config': {}
                },
                {
                    'capability_name': 'SecurityCapability',
                    'capability_module': 'tests.test_capability_synergy',
                    'capability_class': 'MockCapability',
                    'method_name': 'scan_code',
                    'input_mapping': {'code': 'code_to_scan'},
                    'output_key': 'security_results',
                    'config': {}
                }
            ]
        )

        result = engine.execute_chain(
            'insight_test_chain',
            {
                'search_query': 'test query',
                'code_to_scan': 'test code'
            }
        )

        # Get insights
        insights = engine.get_synergy_insights(limit=10)
        assert isinstance(insights, list), "Insights should be a list"
        print(f"[OK] Generated {len(insights)} insights")

        if insights:
            for insight in insights:
                assert 'insight_type' in insight, "Insight should have type"
                assert 'insight_text' in insight, "Insight should have text"
                print(f"  - {insight['insight_text']}")

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_emergent_patterns():
    """Test emergent pattern discovery"""
    print("\n=== Test: Emergent Pattern Discovery ===")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name

    try:
        engine = CapabilitySynergyEngine(db_path=db_path)

        # Execute a chain multiple times to create patterns
        chain_id = engine.define_chain(
            name="pattern_test_chain",
            description="Chain to test pattern discovery",
            steps=[
                {
                    'capability_name': 'Capability1',
                    'capability_module': 'tests.test_capability_synergy',
                    'capability_class': 'MockCapability',
                    'method_name': 'test_method',
                    'input_mapping': {'input_data': 'input'},
                    'output_key': 'output',
                    'config': {}
                }
            ]
        )

        # Execute multiple times
        for i in range(3):
            engine.execute_chain('pattern_test_chain', {'input': f'test_{i}'})

        # Discover patterns
        patterns = engine.discover_emergent_patterns()
        assert isinstance(patterns, list), "Patterns should be a list"
        print(f"[OK] Discovered {len(patterns)} emergent patterns")

        for pattern in patterns:
            assert 'pattern_name' in pattern, "Pattern should have name"
            assert 'capabilities_involved' in pattern, "Pattern should list capabilities"
            assert 'impact_score' in pattern, "Pattern should have impact score"
            assert 'occurrences' in pattern, "Pattern should track occurrences"

            print(f"\n  Pattern: {pattern['pattern_name']}")
            print(f"    Capabilities: {', '.join(pattern['capabilities_involved'])}")
            print(f"    Impact: {pattern['impact_score']:.2f}")
            print(f"    Occurrences: {pattern['occurrences']}")

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_chain_scheduling():
    """Test chain scheduling"""
    print("\n=== Test: Chain Scheduling ===")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name

    try:
        engine = CapabilitySynergyEngine(db_path=db_path)

        # Define a chain
        chain_id = engine.define_chain(
            name="scheduled_chain",
            description="Chain to test scheduling",
            steps=[
                {
                    'capability_name': 'TestCapability',
                    'capability_module': 'tests.test_capability_synergy',
                    'capability_class': 'MockCapability',
                    'method_name': 'test_method',
                    'input_mapping': {'input_data': 'input'},
                    'output_key': 'output',
                    'config': {}
                }
            ]
        )

        # Schedule the chain
        success = engine.schedule_chain(
            chain_id,
            trigger='time_interval',
            config={'interval_seconds': 3600}
        )

        assert success, "Scheduling should succeed"
        print("[OK] Chain scheduled successfully")

        # Check schedule was recorded
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute('SELECT * FROM chain_schedules WHERE chain_id=?', (chain_id,))
        schedule = c.fetchone()
        conn.close()

        assert schedule is not None, "Schedule should be recorded"
        assert schedule[2] == 'time_interval', "Trigger type should match"
        print("[OK] Schedule recorded in database")

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_multi_step_chain():
    """Test a complex multi-step chain"""
    print("\n=== Test: Multi-Step Chain ===")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name

    try:
        engine = CapabilitySynergyEngine(db_path=db_path)

        # Create a realistic multi-step chain
        chain_id = engine.define_chain(
            name="complex_analysis_chain",
            description="Multi-step code analysis chain",
            steps=[
                {
                    'capability_name': 'Search',
                    'capability_module': 'tests.test_capability_synergy',
                    'capability_class': 'MockCapability',
                    'method_name': 'search',
                    'input_mapping': {'query': 'search_query'},
                    'output_key': 'search_results',
                    'config': {}
                },
                {
                    'capability_name': 'SecurityScan',
                    'capability_module': 'tests.test_capability_synergy',
                    'capability_class': 'MockCapability',
                    'method_name': 'scan_code',
                    'input_mapping': {'code': 'code'},
                    'output_key': 'security_results',
                    'config': {}
                },
                {
                    'capability_name': 'CodeReview',
                    'capability_module': 'tests.test_capability_synergy',
                    'capability_class': 'MockCapability',
                    'method_name': 'suggest_improvements',
                    'input_mapping': {'code': 'code'},
                    'output_key': 'review_results',
                    'config': {}
                },
                {
                    'capability_name': 'MistakeCheck',
                    'capability_module': 'tests.test_capability_synergy',
                    'capability_class': 'MockCapability',
                    'method_name': 'check_for_known_mistakes',
                    'input_mapping': {'code': 'code'},
                    'output_key': 'mistake_results',
                    'config': {}
                }
            ]
        )

        # Execute the chain
        result = engine.execute_chain(
            'complex_analysis_chain',
            {
                'search_query': 'authentication',
                'code': 'def authenticate(user, password): pass'
            }
        )

        assert result['status'] in ['completed', 'partial'], "Chain should complete"
        assert len(result['step_results']) == 4, "Should have 4 steps"
        print(f"[OK] Multi-step chain completed with {len(result['step_results'])} steps")

        # Check all results are in context
        context = result['context']
        assert 'search_results' in context, "Search results should be in context"
        assert 'security_results' in context, "Security results should be in context"
        assert 'review_results' in context, "Review results should be in context"
        assert 'mistake_results' in context, "Mistake results should be in context"
        print("[OK] All step results captured in context")

        # Check insights
        assert len(result['insights']) > 0, "Should generate insights"
        print(f"[OK] Generated {len(result['insights'])} insights:")
        for insight in result['insights']:
            print(f"  - {insight}")

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_chain_metrics():
    """Test chain performance metrics"""
    print("\n=== Test: Chain Metrics ===")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name

    try:
        engine = CapabilitySynergyEngine(db_path=db_path)

        # Create and execute a chain
        chain_id = engine.define_chain(
            name="metrics_test_chain",
            description="Chain to test metrics",
            steps=[
                {
                    'capability_name': 'TestCapability',
                    'capability_module': 'tests.test_capability_synergy',
                    'capability_class': 'MockCapability',
                    'method_name': 'test_method',
                    'input_mapping': {'input_data': 'input'},
                    'output_key': 'output',
                    'config': {}
                }
            ]
        )

        # Execute multiple times
        for i in range(3):
            engine.execute_chain('metrics_test_chain', {'input': f'test_{i}'})

        # Check metrics
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM chain_metrics WHERE chain_id=?', (chain_id,))
        metric_count = c.fetchone()[0]
        conn.close()

        assert metric_count > 0, "Metrics should be recorded"
        print(f"[OK] {metric_count} metrics recorded")

        # Check status includes metrics
        status = engine.get_chain_status(chain_id)
        assert 'avg_duration_seconds' in status, "Status should include average duration"
        assert status['avg_duration_seconds'] >= 0, "Average duration should be non-negative"
        print(f"[OK] Average duration: {status['avg_duration_seconds']:.3f}s")

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("CAPABILITY SYNERGY ENGINE - TEST SUITE")
    print("="*60)

    tests = [
        test_engine_initialization,
        test_default_chains,
        test_define_custom_chain,
        test_chain_execution,
        test_synergy_insights,
        test_emergent_patterns,
        test_chain_scheduling,
        test_multi_step_chain,
        test_chain_metrics
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"\n[FAIL] Test failed: {test.__name__}")
            print(f"  Error: {str(e)}")
            import traceback
            traceback.print_exc()

    print("\n" + "="*60)
    print(f"TEST RESULTS: {passed} passed, {failed} failed")
    print("="*60)

    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
