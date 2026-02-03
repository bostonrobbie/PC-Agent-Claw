"""
Code Performance Profiler - Production Ready
Analyzes code for performance bottlenecks, memory usage, and complexity.
Stores results in SQLite database for historical tracking.
"""

import cProfile
import pstats
import io
import time
import psutil
import tracemalloc
import ast
import sqlite3
import json
import os
from typing import Callable, Any, Dict, List, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from functools import wraps
from pathlib import Path


@dataclass
class ProfileResult:
    """Container for profiling results"""
    function_name: str
    execution_time: float
    memory_used: float
    memory_peak: float
    complexity_estimate: str
    bottlenecks: List[Dict[str, Any]]
    timestamp: str
    status: str = "success"


class ComplexityAnalyzer(ast.NodeVisitor):
    """Static code analysis for time and space complexity estimation"""

    def __init__(self):
        self.loops = 0
        self.nested_depth = 0
        self.max_nested = 0
        self.function_calls = {}
        self.recursive = False

    def visit_For(self, node):
        self.loops += 1
        self.nested_depth += 1
        self.max_nested = max(self.max_nested, self.nested_depth)
        self.generic_visit(node)
        self.nested_depth -= 1

    def visit_While(self, node):
        self.loops += 1
        self.nested_depth += 1
        self.max_nested = max(self.max_nested, self.nested_depth)
        self.generic_visit(node)
        self.nested_depth -= 1

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            self.function_calls[func_name] = self.function_calls.get(func_name, 0) + 1
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        # Check for recursion by looking at calls to same function
        for item in ast.walk(node):
            if isinstance(item, ast.Call) and isinstance(item.func, ast.Name):
                if item.func.id == node.name:
                    self.recursive = True
        self.generic_visit(node)

    def estimate_complexity(self) -> str:
        """Estimate time complexity based on code structure"""
        if self.recursive:
            return "O(2^n) - Recursive (exponential)"

        if self.max_nested >= 3:
            return f"O(n^{self.max_nested}) - Highly nested loops"
        elif self.max_nested == 2:
            return "O(n^2) - Nested loops"
        elif self.max_nested == 1:
            return "O(n) - Linear"
        else:
            return "O(1) - Constant"


class DatabaseManager:
    """SQLite database for storing profiling results"""

    def __init__(self, db_path: str = "performance_profiler.db"):
        self.db_path = db_path
        self._ensure_database()

    def _ensure_database(self):
        """Create database and tables if they don't exist"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    function_name TEXT NOT NULL,
                    execution_time REAL NOT NULL,
                    memory_used REAL NOT NULL,
                    memory_peak REAL NOT NULL,
                    complexity_estimate TEXT,
                    bottlenecks TEXT,
                    timestamp TEXT NOT NULL,
                    status TEXT DEFAULT 'success'
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS benchmarks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    benchmark_name TEXT NOT NULL,
                    variation TEXT NOT NULL,
                    execution_time REAL NOT NULL,
                    memory_used REAL NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)
            conn.commit()

    def save_profile(self, result: ProfileResult):
        """Save profiling result to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO profiles
                (function_name, execution_time, memory_used, memory_peak,
                 complexity_estimate, bottlenecks, timestamp, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.function_name,
                result.execution_time,
                result.memory_used,
                result.memory_peak,
                result.complexity_estimate,
                json.dumps(result.bottlenecks),
                result.timestamp,
                result.status
            ))
            conn.commit()

    def save_benchmark(self, benchmark_name: str, variation: str,
                      execution_time: float, memory_used: float):
        """Save benchmark comparison"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO benchmarks
                (benchmark_name, variation, execution_time, memory_used, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (
                benchmark_name,
                variation,
                execution_time,
                memory_used,
                datetime.now().isoformat()
            ))
            conn.commit()

    def get_profiles(self, function_name: str = None) -> List[Dict]:
        """Retrieve profiles from database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if function_name:
                cursor = conn.execute(
                    "SELECT * FROM profiles WHERE function_name = ? ORDER BY timestamp DESC",
                    (function_name,)
                )
            else:
                cursor = conn.execute("SELECT * FROM profiles ORDER BY timestamp DESC")
            return [dict(row) for row in cursor.fetchall()]

    def get_benchmarks(self, benchmark_name: str) -> List[Dict]:
        """Retrieve benchmark comparisons"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM benchmarks WHERE benchmark_name = ? ORDER BY timestamp DESC",
                (benchmark_name,)
            )
            return [dict(row) for row in cursor.fetchall()]


class PerformanceProfiler:
    """Main profiler class"""

    def __init__(self, db_path: str = "performance_profiler.db"):
        self.db = DatabaseManager(db_path)
        self.cprofile = None

    def analyze_source_code(self, func: Callable) -> Tuple[ComplexityAnalyzer, str]:
        """Perform static analysis on function source code"""
        try:
            source = inspect.getsource(func)
            tree = ast.parse(source)
            analyzer = ComplexityAnalyzer()
            analyzer.visit(tree)
            return analyzer, source
        except Exception as e:
            return None, str(e)

    def get_bottlenecks(self, stats_data: pstats.Stats) -> List[Dict[str, Any]]:
        """Extract top bottlenecks from profiling stats"""
        bottlenecks = []
        stats_dict = stats_data.stats

        # Sort by cumulative time
        sorted_stats = sorted(
            stats_dict.items(),
            key=lambda x: x[1][3],
            reverse=True
        )

        for func_info, stats in sorted_stats[:5]:  # Top 5 bottlenecks
            filename, line, func_name = func_info
            calls, num_calls, total_time, cumulative_time = stats[0], stats[1], stats[2], stats[3]

            bottlenecks.append({
                "function": f"{func_name}",
                "file": filename,
                "line": line,
                "calls": num_calls,
                "total_time": total_time,
                "cumulative_time": cumulative_time,
                "time_per_call": cumulative_time / num_calls if num_calls > 0 else 0
            })

        return bottlenecks

    def profile_function(self, func: Callable, *args, **kwargs) -> ProfileResult:
        """Profile a function for performance and memory usage"""
        func_name = func.__name__
        timestamp = datetime.now().isoformat()

        try:
            # Start memory tracking
            tracemalloc.start()
            start_mem = psutil.Process().memory_info().rss / 1024 / 1024  # MB

            # Start CPU profiling
            pr = cProfile.Profile()
            pr.enable()

            # Execute function
            start_time = time.perf_counter()
            result = func(*args, **kwargs)
            end_time = time.perf_counter()

            pr.disable()

            # Get memory info
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            end_mem = psutil.Process().memory_info().rss / 1024 / 1024

            execution_time = end_time - start_time
            memory_used = end_mem - start_mem
            memory_peak = peak / 1024 / 1024

            # Get profiling statistics
            s = io.StringIO()
            ps = pstats.Stats(pr, stream=s).sort_stats("cumulative")
            ps.print_stats(10)

            # Extract bottlenecks
            bottlenecks = self.get_bottlenecks(ps)

            # Static complexity analysis
            analyzer, source = self.analyze_source_code(func)
            complexity = analyzer.estimate_complexity() if analyzer else "Unknown"

            profile_result = ProfileResult(
                function_name=func_name,
                execution_time=execution_time,
                memory_used=memory_used,
                memory_peak=memory_peak,
                complexity_estimate=complexity,
                bottlenecks=bottlenecks,
                timestamp=timestamp,
                status="success"
            )

            # Save to database
            self.db.save_profile(profile_result)

            return profile_result

        except Exception as e:
            tracemalloc.stop()
            return ProfileResult(
                function_name=func_name,
                execution_time=0,
                memory_used=0,
                memory_peak=0,
                complexity_estimate="Error",
                bottlenecks=[{"error": str(e)}],
                timestamp=timestamp,
                status="error"
            )

    def benchmark_variations(self, benchmark_name: str,
                            variations: Dict[str, Callable],
                            *args, **kwargs) -> Dict[str, Dict[str, float]]:
        """Compare performance of different code variations"""
        results = {}

        for variation_name, func in variations.items():
            profile = self.profile_function(func, *args, **kwargs)
            results[variation_name] = {
                "execution_time": profile.execution_time,
                "memory_used": profile.memory_used,
                "memory_peak": profile.memory_peak,
                "complexity": profile.complexity_estimate
            }
            self.db.save_benchmark(
                benchmark_name,
                variation_name,
                profile.execution_time,
                profile.memory_used
            )

        return results

    def get_optimization_suggestions(self, profile: ProfileResult) -> List[str]:
        """Generate optimization suggestions based on profile"""
        suggestions = []

        if profile.execution_time > 1.0:
            suggestions.append("Consider using algorithmic optimization - execution time > 1s")

        if profile.memory_peak > 100:
            suggestions.append("Consider implementing memory optimization - memory usage > 100MB")

        if "O(n^" in profile.complexity_estimate:
            suggestions.append("Reduce nested loops - high time complexity detected")

        if profile.bottlenecks:
            top_bottleneck = profile.bottlenecks[0]
            if top_bottleneck.get("time_per_call", 0) > 0.01:
                suggestions.append(f"Optimize {top_bottleneck['function']} - high per-call time")

        if "Recursive (exponential)" in profile.complexity_estimate:
            suggestions.append("Consider memoization or dynamic programming for recursive function")

        if not suggestions:
            suggestions.append("Code is well-optimized!")

        return suggestions

    def format_report(self, profile: ProfileResult) -> str:
        """Generate formatted profiling report"""
        suggestions = self.get_optimization_suggestions(profile)

        report = f"""
{'='*70}
PERFORMANCE PROFILING REPORT
{'='*70}
Function: {profile.function_name}
Timestamp: {profile.timestamp}
Status: {profile.status}

METRICS:
  Execution Time: {profile.execution_time:.6f}s
  Memory Used: {profile.memory_used:.2f}MB
  Peak Memory: {profile.memory_peak:.2f}MB
  Complexity: {profile.complexity_estimate}

TOP BOTTLENECKS:
"""
        for i, bottleneck in enumerate(profile.bottlenecks[:5], 1):
            if "error" not in bottleneck:
                report += f"\n  {i}. {bottleneck['function']} ({bottleneck['file']}:{bottleneck['line']})"
                report += f"\n     Calls: {bottleneck['calls']}, Total Time: {bottleneck['total_time']:.4f}s"
                report += f"\n     Time/Call: {bottleneck['time_per_call']:.6f}s"

        report += "\n\nOPTIMIZATION SUGGESTIONS:\n"
        for suggestion in suggestions:
            report += f"  • {suggestion}\n"

        report += f"{'='*70}\n"
        return report


# Import at module level for static analysis
import inspect


# ============================================================================
# WORKING TEST CODE
# ============================================================================

def test_performance_profiler():
    """Comprehensive test suite for profiler"""
    print("\n" + "="*70)
    print("PERFORMANCE PROFILER TEST SUITE")
    print("="*70 + "\n")

    # Initialize profiler
    profiler = PerformanceProfiler(db_path="performance_profiler.db")

    # Test 1: Simple linear function
    def linear_search(data: list, target: int) -> bool:
        """Linear search - O(n)"""
        for item in data:
            if item == target:
                return True
        return False

    print("TEST 1: Linear Search (O(n))")
    data = list(range(10000))
    profile = profiler.profile_function(linear_search, data, 5000)
    print(profiler.format_report(profile))

    # Test 2: Quadratic function
    def bubble_sort(arr: list) -> list:
        """Bubble sort - O(n^2)"""
        n = len(arr)
        for i in range(n):
            for j in range(0, n - i - 1):
                if arr[j] > arr[j + 1]:
                    arr[j], arr[j + 1] = arr[j + 1], arr[j]
        return arr

    print("\nTEST 2: Bubble Sort (O(n^2))")
    data = list(range(100, 0, -1))
    profile = profiler.profile_function(bubble_sort, data)
    print(profiler.format_report(profile))

    # Test 3: Recursive function
    def fibonacci(n: int) -> int:
        """Fibonacci - O(2^n)"""
        if n <= 1:
            return n
        return fibonacci(n - 1) + fibonacci(n - 2)

    print("\nTEST 3: Fibonacci (O(2^n))")
    profile = profiler.profile_function(fibonacci, 25)
    print(profiler.format_report(profile))

    # Test 4: Memory intensive function
    def create_large_list(size: int) -> list:
        """Creates large list - memory intensive"""
        return [i * i for i in range(size)]

    print("\nTEST 4: Memory Intensive Operation")
    profile = profiler.profile_function(create_large_list, 1000000)
    print(profiler.format_report(profile))

    # Test 5: Benchmark variations
    print("\nTEST 5: Benchmarking Algorithm Variations")
    print("-" * 70)

    def list_sum_v1(data: list) -> int:
        """Using loop"""
        result = 0
        for item in data:
            result += item
        return result

    def list_sum_v2(data: list) -> int:
        """Using built-in sum"""
        return sum(data)

    def list_sum_v3(data: list) -> int:
        """Using reduce"""
        from functools import reduce
        return reduce(lambda x, y: x + y, data)

    data = list(range(100000))
    results = profiler.benchmark_variations(
        "sum_benchmark",
        {
            "manual_loop": list_sum_v1,
            "builtin_sum": list_sum_v2,
            "reduce_func": list_sum_v3
        },
        data
    )

    print("\nBenchmark Results:")
    for variation, metrics in results.items():
        print(f"\n  {variation}:")
        print(f"    Execution Time: {metrics['execution_time']:.6f}s")
        print(f"    Memory Used: {metrics['memory_used']:.2f}MB")
        print(f"    Complexity: {metrics['complexity']}")

    # Test 6: Database retrieval
    print("\n\nTEST 6: Database History")
    print("-" * 70)
    profiles = profiler.db.get_profiles()
    print(f"Total profiles in database: {len(profiles)}")
    if profiles:
        latest = profiles[0]
        print(f"Latest profile: {latest['function_name']} at {latest['timestamp']}")
        print(f"Execution time: {latest['execution_time']:.6f}s")

    print("\n" + "="*70)
    print("TESTS COMPLETED SUCCESSFULLY")
    print("="*70)
    print(f"\nDatabase: {os.path.abspath('performance_profiler.db')}")


if __name__ == "__main__":
    test_performance_profiler()
