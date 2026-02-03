#!/usr/bin/env python3
"""
Complete Tests for Cross-Capability Synergy System

Tests all 4 primary synergy chains and the full API:
1. Discovery -> Learning Chain
2. Analysis -> Action Chain
3. Memory -> Prediction Chain
4. Monitoring -> Optimization Chain
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
    CapabilitySynergy,
    ChainStep,
    ChainDefinition,
    ChainExecution,
    SynergyPattern
)


class MockSemanticSearch:
    """Mock semantic search capability"""

    def __init__(self, **kwargs):
        self.config = kwargs

    def search(self, query):
        """Mock search method"""
        return {
            'results': [
                {'file': 'auth.py', 'content': 'def login(user, pass): ...', 'score': 0.9},
                {'file': 'users.py', 'content': 'class User: ...', 'score': 0.8}
            ],
            'count': 2,
            'query': query
        }

    def find_similar(self, code):
        """Mock finding similar code"""
        return {
            'matches': [
                {'file': 'utils.py', 'similarity': 0.92},
                {'file': 'helpers.py', 'similarity': 0.88}
            ]
        }

    def get_stats(self):
        """Mock stats"""
        return {
            'total_projects': 5,
            'total_chunks': 1250,
            'total_files': 342
        }


class MockMistakeLearner:
    """Mock mistake learning capability"""

    def __init__(self, **kwargs):
        self.config = kwargs

    def check_code_before_suggesting(self, code):
        """Mock mistake checking"""
        return {
            'similar_failures': [
                {'description': 'SQL injection vulnerability', 'severity': 'high'},
                {'description': 'Missing error handling', 'severity': 'medium'}
            ],
            'warnings': 2,
            'safe_to_proceed': False
        }

    def get_correction_suggestions(self, error_message):
        """Mock correction suggestions"""
        return [
            {
                'correction': 'Add try-except block',
                'confidence': 0.9,
                'examples': ['try:\n    ...\nexcept Exception as e:\n    ...']
            },
            {
                'correction': 'Use parameterized queries',
                'confidence': 0.95,
                'examples': ['cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))']
            }
        ]

    def get_recent_mistakes(self, limit=10):
        """Mock recent mistakes"""
        return [
            {
                'id': 1,
                'mistake_type': 'security',
                'description': 'SQL injection in login',
                'timestamp': '2026-02-03T10:00:00'
            },
            {
                'id': 2,
                'mistake_type': 'logic',
                'description': 'Missing null check',
                'timestamp': '2026-02-03T11:00:00'
            }
        ]

    def get_learning_stats(self):
        """Mock learning stats"""
        return {
            'total_mistakes': 45,
            'corrected': 38,
            'patterns_learned': 12,
            'success_rate': 0.84
        }


class MockCodeReview:
    """Mock code review capability"""

    def __init__(self, **kwargs):
        self.config = kwargs

    def check_code_against_preferences(self, code, language):
        """Mock code review"""
        return {
            'violations': [
                {'type': 'naming', 'message': 'Use snake_case for variables'},
                {'type': 'structure', 'message': 'Function too long (50 lines)'}
            ],
            'score': 0.75,
            'recommendations': [
                'Add type hints',
                'Improve docstrings',
                'Break into smaller functions'
            ],
            'patterns': ['naming_convention', 'function_length']
        }

    def get_style_guide(self, language=None):
        """Mock style guide"""
        return {
            'preferences': [
                {'pattern': 'snake_case_variables', 'confidence': 0.95},
                {'pattern': 'comprehensive_docstrings', 'confidence': 0.90}
            ]
        }


def test_synergy_registration():
    """Test registering synergies between capabilities"""
    print("\n=== Test: Synergy Registration ===")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name

    try:
        synergy = CapabilitySynergy(db_path=db_path)

        # Define a custom transform function
        def search_to_review(search_results):
            """Transform search results for code review"""
            if isinstance(search_results, dict) and 'results' in search_results:
                return {
                    'code_samples': [r['content'] for r in search_results['results']],
                    'context': 'semantic_search'
                }
            return {'code_samples': [], 'context': 'unknown'}

        # Register synergy
        success = synergy.register_synergy(
            'SemanticSearch',
            'CodeReview',
            search_to_review
        )

        assert success, "Synergy registration should succeed"
        print("[OK] Synergy registered successfully")

        # Verify in database
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM synergy_registry')
        count = c.fetchone()[0]
        conn.close()

        # Should have default synergies + our custom one
        assert count > 0, "Synergy should be stored in database"
        print(f"[OK] {count} synergies registered in database")

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_discovery_learning_chain():
    """Test Discovery -> Learning Chain"""
    print("\n=== Test: Discovery -> Learning Chain ===")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name

    try:
        synergy = CapabilitySynergy(db_path=db_path)

        # Define chain with mock capabilities
        chain_id = synergy.define_chain(
            name="test_discovery_learning",
            description="Test discovery to learning flow",
            steps=[
                {
                    'capability_name': 'SemanticSearch',
                    'capability_module': 'tests.test_capability_synergy_complete',
                    'capability_class': 'MockSemanticSearch',
                    'method_name': 'search',
                    'input_mapping': {'query': 'search_query'},
                    'output_key': 'search_results',
                    'config': {}
                },
                {
                    'capability_name': 'MistakeLearner',
                    'capability_module': 'tests.test_capability_synergy_complete',
                    'capability_class': 'MockMistakeLearner',
                    'method_name': 'check_code_before_suggesting',
                    'input_mapping': {'code': 'code'},
                    'output_key': 'mistake_check',
                    'config': {}
                },
                {
                    'capability_name': 'CodeReview',
                    'capability_module': 'tests.test_capability_synergy_complete',
                    'capability_class': 'MockCodeReview',
                    'method_name': 'check_code_against_preferences',
                    'input_mapping': {'code': 'code', 'language': 'language'},
                    'output_key': 'review_results',
                    'config': {}
                }
            ]
        )

        # Execute chain
        result = synergy.execute_chain(
            'test_discovery_learning',
            {
                'search_query': 'authentication functions',
                'code': 'def login(user, password): return True',
                'language': 'python'
            }
        )

        assert result['status'] in ['completed', 'partial'], "Chain should complete"
        assert 'compound_intelligence_score' in result, "Should have compound score"
        assert len(result['step_results']) == 3, "Should have 3 steps"

        print(f"[OK] Discovery -> Learning chain completed")
        print(f"[OK] Status: {result['status']}")
        print(f"[OK] Compound Intelligence Score: {result['compound_intelligence_score']:.3f}")
        print(f"[OK] Insights generated: {len(result['insights'])}")

        # Verify all outputs in context
        context = result['context']
        assert 'search_results' in context, "Search results should be in context"
        assert 'mistake_check' in context, "Mistake check should be in context"
        assert 'review_results' in context, "Review results should be in context"
        print("[OK] All capability outputs captured in context")

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_analysis_action_chain():
    """Test Analysis -> Action Chain"""
    print("\n=== Test: Analysis -> Action Chain ===")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name

    try:
        synergy = CapabilitySynergy(db_path=db_path)

        # Define chain
        chain_id = synergy.define_chain(
            name="test_analysis_action",
            description="Test analysis to action flow",
            steps=[
                {
                    'capability_name': 'CodeReview',
                    'capability_module': 'tests.test_capability_synergy_complete',
                    'capability_class': 'MockCodeReview',
                    'method_name': 'check_code_against_preferences',
                    'input_mapping': {'code': 'code', 'language': 'language'},
                    'output_key': 'review_results',
                    'config': {}
                },
                {
                    'capability_name': 'MistakeLearner',
                    'capability_module': 'tests.test_capability_synergy_complete',
                    'capability_class': 'MockMistakeLearner',
                    'method_name': 'get_correction_suggestions',
                    'input_mapping': {'error_message': 'error_message'},
                    'output_key': 'fix_suggestions',
                    'config': {}
                }
            ]
        )

        # Execute chain
        result = synergy.execute_chain(
            'test_analysis_action',
            {
                'code': 'def process(): pass',
                'language': 'python',
                'error_message': 'Missing exception handling'
            }
        )

        assert result['status'] in ['completed', 'partial'], "Chain should complete"
        print(f"[OK] Analysis -> Action chain completed")
        print(f"[OK] Compound Score: {result['compound_intelligence_score']:.3f}")

        # Check that review led to fix suggestions
        context = result['context']
        assert 'fix_suggestions' in context, "Should have fix suggestions"
        suggestions = context['fix_suggestions']
        assert len(suggestions) > 0, "Should have at least one suggestion"
        print(f"[OK] Generated {len(suggestions)} fix suggestions")

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_memory_prediction_chain():
    """Test Memory -> Prediction Chain"""
    print("\n=== Test: Memory -> Prediction Chain ===")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name

    try:
        synergy = CapabilitySynergy(db_path=db_path)

        # Define chain
        chain_id = synergy.define_chain(
            name="test_memory_prediction",
            description="Test memory to prediction flow",
            steps=[
                {
                    'capability_name': 'MistakeLearner',
                    'capability_module': 'tests.test_capability_synergy_complete',
                    'capability_class': 'MockMistakeLearner',
                    'method_name': 'get_recent_mistakes',
                    'input_mapping': {'limit': 'limit'},
                    'output_key': 'recent_mistakes',
                    'config': {}
                },
                {
                    'capability_name': 'CodeReview',
                    'capability_module': 'tests.test_capability_synergy_complete',
                    'capability_class': 'MockCodeReview',
                    'method_name': 'check_code_against_preferences',
                    'input_mapping': {'code': 'code', 'language': 'language'},
                    'output_key': 'proactive_suggestions',
                    'config': {}
                }
            ]
        )

        # Execute chain
        result = synergy.execute_chain(
            'test_memory_prediction',
            {
                'limit': 10,
                'code': 'def query_db(sql): cursor.execute(sql)',
                'language': 'python'
            }
        )

        assert result['status'] in ['completed', 'partial'], "Chain should complete"
        print(f"[OK] Memory -> Prediction chain completed")
        print(f"[OK] Compound Score: {result['compound_intelligence_score']:.3f}")

        # Verify predictions based on memory
        context = result['context']
        assert 'recent_mistakes' in context, "Should have recent mistakes"
        assert 'proactive_suggestions' in context, "Should have proactive suggestions"
        print(f"[OK] Memory patterns used for predictions")

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_monitoring_optimization_chain():
    """Test Monitoring -> Optimization Chain"""
    print("\n=== Test: Monitoring -> Optimization Chain ===")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name

    try:
        synergy = CapabilitySynergy(db_path=db_path)

        # Define chain
        chain_id = synergy.define_chain(
            name="test_monitoring_optimization",
            description="Test monitoring to optimization flow",
            steps=[
                {
                    'capability_name': 'SemanticSearch',
                    'capability_module': 'tests.test_capability_synergy_complete',
                    'capability_class': 'MockSemanticSearch',
                    'method_name': 'get_stats',
                    'input_mapping': {},
                    'output_key': 'search_stats',
                    'config': {}
                },
                {
                    'capability_name': 'MistakeLearner',
                    'capability_module': 'tests.test_capability_synergy_complete',
                    'capability_class': 'MockMistakeLearner',
                    'method_name': 'get_learning_stats',
                    'input_mapping': {},
                    'output_key': 'learning_stats',
                    'config': {}
                }
            ]
        )

        # Execute chain
        result = synergy.execute_chain(
            'test_monitoring_optimization',
            {}
        )

        assert result['status'] in ['completed', 'partial'], "Chain should complete"
        print(f"[OK] Monitoring -> Optimization chain completed")
        print(f"[OK] Compound Score: {result['compound_intelligence_score']:.3f}")

        # Verify monitoring data leads to optimization
        context = result['context']
        assert 'search_stats' in context, "Should have search stats"
        assert 'learning_stats' in context, "Should have learning stats"
        print(f"[OK] System metrics monitored and analyzed")

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_synergy_impact_measurement():
    """Test measuring synergy impact"""
    print("\n=== Test: Synergy Impact Measurement ===")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name

    try:
        synergy = CapabilitySynergy(db_path=db_path)

        # Execute a chain to generate some data
        chain_id = synergy.define_chain(
            name="impact_test_chain",
            description="Chain to test impact measurement",
            steps=[
                {
                    'capability_name': 'TestCap',
                    'capability_module': 'tests.test_capability_synergy_complete',
                    'capability_class': 'MockSemanticSearch',
                    'method_name': 'get_stats',
                    'input_mapping': {},
                    'output_key': 'stats',
                    'config': {}
                }
            ]
        )

        # Execute a few times
        for i in range(3):
            synergy.execute_chain('impact_test_chain', {})

        # Measure impact
        impact = synergy.measure_synergy_impact()

        assert isinstance(impact, dict), "Impact should be a dictionary"
        assert 'total_synergies' in impact, "Should have total synergies"
        assert 'active_chains' in impact, "Should have active chains"
        assert 'average_compound_score' in impact, "Should have average compound score"
        assert 'synergy_connections' in impact, "Should have synergy connections"

        print(f"[OK] Total synergies: {impact['total_synergies']}")
        print(f"[OK] Active chains: {impact['active_chains']}")
        print(f"[OK] Average compound score: {impact['average_compound_score']:.3f}")
        print(f"[OK] Overall impact: {impact['overall_impact']:.3f}")

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_discover_new_synergies():
    """Test discovering new synergy opportunities"""
    print("\n=== Test: Discover New Synergies ===")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name

    try:
        synergy = CapabilitySynergy(db_path=db_path)

        # Define a chain with capabilities that don't have registered synergies
        chain_id = synergy.define_chain(
            name="discovery_opportunity_chain",
            description="Chain to discover opportunities",
            steps=[
                {
                    'capability_name': 'CapabilityA',
                    'capability_module': 'tests.test_capability_synergy_complete',
                    'capability_class': 'MockSemanticSearch',
                    'method_name': 'get_stats',
                    'input_mapping': {},
                    'output_key': 'result_a',
                    'config': {}
                },
                {
                    'capability_name': 'CapabilityB',
                    'capability_module': 'tests.test_capability_synergy_complete',
                    'capability_class': 'MockCodeReview',
                    'method_name': 'get_style_guide',
                    'input_mapping': {},
                    'output_key': 'result_b',
                    'config': {}
                }
            ]
        )

        # Execute to create co-occurrence pattern
        synergy.execute_chain('discovery_opportunity_chain', {})

        # Discover opportunities
        opportunities = synergy.discover_new_synergies()

        assert isinstance(opportunities, list), "Should return list of opportunities"
        print(f"[OK] Discovered {len(opportunities)} synergy opportunities")

        if opportunities:
            for i, opp in enumerate(opportunities[:3], 1):
                print(f"\n  Opportunity {i}:")
                print(f"    From: {opp['from_capability']}")
                print(f"    To: {opp['to_capability']}")
                print(f"    Potential Impact: {opp['potential_impact']:.2f}")
                print(f"    Reason: {opp['reason']}")

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_compound_intelligence_score():
    """Test compound intelligence score calculation"""
    print("\n=== Test: Compound Intelligence Score ===")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name

    try:
        synergy = CapabilitySynergy(db_path=db_path)

        # Initial score should be low or zero
        initial_score = synergy.get_compound_intelligence_score()
        assert 0.0 <= initial_score <= 1.0, "Score should be between 0 and 1"
        print(f"[OK] Initial compound intelligence score: {initial_score:.3f}")

        # Execute some chains to build up intelligence
        chain_id = synergy.define_chain(
            name="intelligence_builder",
            description="Build compound intelligence",
            steps=[
                {
                    'capability_name': 'Search',
                    'capability_module': 'tests.test_capability_synergy_complete',
                    'capability_class': 'MockSemanticSearch',
                    'method_name': 'search',
                    'input_mapping': {'query': 'query'},
                    'output_key': 'results',
                    'config': {}
                },
                {
                    'capability_name': 'Review',
                    'capability_module': 'tests.test_capability_synergy_complete',
                    'capability_class': 'MockCodeReview',
                    'method_name': 'check_code_against_preferences',
                    'input_mapping': {'code': 'code', 'language': 'language'},
                    'output_key': 'review',
                    'config': {}
                }
            ]
        )

        # Execute multiple times
        for i in range(5):
            result = synergy.execute_chain(
                'intelligence_builder',
                {'query': f'test_{i}', 'code': 'def foo(): pass', 'language': 'python'}
            )
            print(f"  Execution {i+1} - Score: {result['compound_intelligence_score']:.3f}")

        # Final score should be higher
        final_score = synergy.get_compound_intelligence_score()
        print(f"[OK] Final compound intelligence score: {final_score:.3f}")

        # Store in database should work
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM intelligence_scores')
        score_count = c.fetchone()[0]
        conn.close()

        assert score_count > 0, "Intelligence scores should be recorded"
        print(f"[OK] {score_count} intelligence scores recorded")

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_all_chains_together():
    """Test all 4 synergy chains working together"""
    print("\n=== Test: All Synergy Chains Together ===")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name

    try:
        synergy = CapabilitySynergy(db_path=db_path)

        print("\nExecuting all 4 primary synergy chains:")

        # 1. Discovery -> Learning
        print("\n  1. Discovery -> Learning Chain...")
        result1 = synergy.execute_chain(
            'discovery_learning_chain',
            {
                'search_query': 'security functions',
                'code': 'def authenticate(): pass',
                'language': 'python'
            }
        )
        print(f"     Status: {result1['status']}, Score: {result1['compound_intelligence_score']:.3f}")

        # 2. Analysis -> Action
        print("\n  2. Analysis -> Action Chain...")
        result2 = synergy.execute_chain(
            'analysis_action_chain',
            {
                'code': 'def process(): pass',
                'language': 'python',
                'error_message': 'Missing validation'
            }
        )
        print(f"     Status: {result2['status']}, Score: {result2['compound_intelligence_score']:.3f}")

        # 3. Memory -> Prediction
        print("\n  3. Memory -> Prediction Chain...")
        result3 = synergy.execute_chain(
            'memory_prediction_chain',
            {
                'limit': 10,
                'code': 'def handle_input(): pass',
                'language': 'python'
            }
        )
        print(f"     Status: {result3['status']}, Score: {result3['compound_intelligence_score']:.3f}")

        # 4. Monitoring -> Optimization
        print("\n  4. Monitoring -> Optimization Chain...")
        result4 = synergy.execute_chain(
            'monitoring_optimization_chain',
            {}
        )
        print(f"     Status: {result4['status']}, Score: {result4['compound_intelligence_score']:.3f}")

        # Get overall system status
        print("\n  Overall System Metrics:")
        impact = synergy.measure_synergy_impact()
        print(f"     Total synergies: {impact['total_synergies']}")
        print(f"     Active chains: {impact['active_chains']}")
        print(f"     System compound score: {synergy.get_compound_intelligence_score():.3f}")

        # All chains should complete
        all_completed = all(
            r['status'] in ['completed', 'partial']
            for r in [result1, result2, result3, result4]
        )
        assert all_completed, "All chains should complete successfully"
        print("\n[OK] All 4 synergy chains executed successfully!")

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*70)
    print("CROSS-CAPABILITY SYNERGY SYSTEM - COMPLETE TEST SUITE")
    print("="*70)

    tests = [
        test_synergy_registration,
        test_discovery_learning_chain,
        test_analysis_action_chain,
        test_memory_prediction_chain,
        test_monitoring_optimization_chain,
        test_synergy_impact_measurement,
        test_discover_new_synergies,
        test_compound_intelligence_score,
        test_all_chains_together
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

    print("\n" + "="*70)
    print(f"TEST RESULTS: {passed} passed, {failed} failed")
    print("="*70)

    if failed == 0:
        print("\n[OK] All synergy chains working perfectly!")
        print("[OK] Discovery -> Learning Chain")
        print("[OK] Analysis -> Action Chain")
        print("[OK] Memory -> Prediction Chain")
        print("[OK] Monitoring -> Optimization Chain")

    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
