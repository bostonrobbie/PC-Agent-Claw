#!/usr/bin/env python3
"""Automated Testing Framework (#6) - Test systems automatically"""
import unittest
import sys
from pathlib import Path
from typing import List, Dict, Callable
import json
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))

from core.persistent_memory import PersistentMemory

class TestFramework:
    """Framework for running automated tests on all systems"""

    def __init__(self):
        self.test_results: List[Dict] = []
        workspace = Path(__file__).parent.parent
        self.memory = PersistentMemory(str(workspace / "memory.db"))

    def register_test(self, test_name: str, test_func: Callable, category: str = "general"):
        """Register a test to run"""
        return {
            'name': test_name,
            'func': test_func,
            'category': category
        }

    def run_test(self, test_dict: Dict) -> Dict:
        """Run a single test and record results"""
        test_name = test_dict['name']
        test_func = test_dict['func']
        category = test_dict['category']

        start_time = datetime.now()

        try:
            result = test_func()
            success = True
            error = None
        except Exception as e:
            success = False
            error = str(e)
            result = None

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        test_result = {
            'name': test_name,
            'category': category,
            'success': success,
            'error': error,
            'result': result,
            'duration_seconds': duration,
            'timestamp': start_time.isoformat()
        }

        self.test_results.append(test_result)

        # Log to memory
        self.memory.log_decision(
            f'Test {"passed" if success else "failed"}: {test_name}',
            f'Category: {category}, Duration: {duration:.2f}s' + (f', Error: {error}' if error else ''),
            tags=['testing', category, 'pass' if success else 'fail']
        )

        return test_result

    def run_all_tests(self, tests: List[Dict]) -> Dict:
        """Run all registered tests"""
        print(f"\nRunning {len(tests)} tests...\n")

        for test_dict in tests:
            result = self.run_test(test_dict)
            status = "PASS" if result['success'] else "FAIL"
            print(f"[{status}] {result['name']} ({result['duration_seconds']:.2f}s)")
            if not result['success']:
                print(f"       Error: {result['error']}")

        return self.get_summary()

    def get_summary(self) -> Dict:
        """Get test summary statistics"""
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r['success'])
        failed = total - passed

        pass_rate = (passed / total * 100) if total > 0 else 0

        # Group by category
        categories = {}
        for result in self.test_results:
            cat = result['category']
            if cat not in categories:
                categories[cat] = {'total': 0, 'passed': 0, 'failed': 0}

            categories[cat]['total'] += 1
            if result['success']:
                categories[cat]['passed'] += 1
            else:
                categories[cat]['failed'] += 1

        return {
            'total_tests': total,
            'passed': passed,
            'failed': failed,
            'pass_rate': round(pass_rate, 2),
            'by_category': categories,
            'failures': [r for r in self.test_results if not r['success']]
        }

    def save_results(self, filepath: str = None):
        """Save test results to file"""
        if filepath is None:
            workspace = Path(__file__).parent.parent
            filepath = workspace / f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(filepath, 'w') as f:
            json.dump({
                'summary': self.get_summary(),
                'results': self.test_results
            }, f, indent=2)

        print(f"\nTest results saved to: {filepath}")


# Example test functions
def test_persistent_memory():
    """Test persistent memory system"""
    from core.persistent_memory import PersistentMemory
    memory = PersistentMemory()

    # Test task creation
    task_id = memory.add_task('test_task', 'Test description')
    assert task_id is not None, "Failed to create task"

    # Test task retrieval
    tasks = memory.get_tasks(status='pending')
    assert len(tasks) > 0, "Failed to retrieve tasks"

    memory.close()
    return "Persistent memory working"

def test_long_term_memory():
    """Test long-term memory system"""
    from core.long_term_memory import LongTermMemory
    ltm = LongTermMemory()

    # Test memory storage
    memory_id = ltm.remember("Test memory content", "test", importance=0.8)
    assert memory_id is not None, "Failed to store memory"

    # Test memory retrieval
    results = ltm.recall("Test memory")
    assert len(results) > 0, "Failed to recall memory"

    ltm.close()
    return "Long-term memory working"

def test_api_connector():
    """Test universal API connector"""
    from core.api_connector import UniversalAPIConnector

    # Test connector initialization
    connector = UniversalAPIConnector("https://api.example.com", api_key="test_key")
    assert connector.base_url == "https://api.example.com", "Base URL not set correctly"

    return "API connector initialized"

def test_performance_monitor():
    """Test performance monitor"""
    from monitoring.performance_monitor import PerformanceMonitor

    monitor = PerformanceMonitor()
    stats = monitor.get_system_stats()

    assert 'cpu_percent' in stats, "CPU stats missing"
    assert 'memory_percent' in stats, "Memory stats missing"
    assert stats['cpu_percent'] >= 0, "Invalid CPU stats"

    return f"System stats: CPU {stats['cpu_percent']}%, RAM {stats['memory_percent']}%"


if __name__ == '__main__':
    # Create test framework
    framework = TestFramework()

    # Register tests
    tests = [
        framework.register_test("Persistent Memory", test_persistent_memory, "core"),
        framework.register_test("Long-Term Memory", test_long_term_memory, "core"),
        framework.register_test("API Connector", test_api_connector, "integration"),
        framework.register_test("Performance Monitor", test_performance_monitor, "monitoring"),
    ]

    # Run all tests
    summary = framework.run_all_tests(tests)

    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(json.dumps(summary, indent=2))

    # Save results
    framework.save_results()

    print("\nTesting Framework ready!")
