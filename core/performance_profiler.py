"""
Performance Profiler

Track where time is spent and identify bottlenecks:
- Profile each phase/component
- Identify hot paths (20% of code taking 80% of time)
- Track operation timing
- Generate optimization recommendations

ENABLES TARGETED PERFORMANCE IMPROVEMENTS
"""
import time
import functools
from typing import Callable, Any, Dict, List, Optional
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class ProfileEntry:
    """Single profiling entry"""
    operation: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    success: bool = True
    error: Optional[str] = None
    metadata: Dict = field(default_factory=dict)


class PerformanceProfiler:
    """
    Track and analyze performance across all operations

    Identifies bottlenecks and suggests optimizations
    """

    def __init__(self):
        # Profiling data
        self.entries: List[ProfileEntry] = []
        self.operation_stats: Dict[str, Dict] = defaultdict(lambda: {
            'count': 0,
            'total_duration': 0.0,
            'min_duration': float('inf'),
            'max_duration': 0.0,
            'failures': 0
        })

        # Statistics
        self.stats = {
            'total_operations': 0,
            'total_duration': 0.0,
            'profiling_overhead': 0.0
        }

        self.enabled = True

    def profile(self, operation: str):
        """
        Decorator to profile a function

        Usage:
            @profiler.profile('my_operation')
            def my_function():
                ...
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                if not self.enabled:
                    return func(*args, **kwargs)

                entry = self.start_operation(operation)

                try:
                    result = func(*args, **kwargs)
                    self.end_operation(entry, success=True)
                    return result
                except Exception as e:
                    self.end_operation(entry, success=False, error=str(e))
                    raise

            return wrapper
        return decorator

    def start_operation(self, operation: str, metadata: Dict = None) -> ProfileEntry:
        """Start profiling an operation"""
        entry = ProfileEntry(
            operation=operation,
            start_time=time.time(),
            metadata=metadata or {}
        )

        self.entries.append(entry)
        self.stats['total_operations'] += 1

        return entry

    def end_operation(self, entry: ProfileEntry, success: bool = True,
                     error: Optional[str] = None):
        """End profiling an operation"""
        entry.end_time = time.time()
        entry.duration = entry.end_time - entry.start_time
        entry.success = success
        entry.error = error

        # Update operation stats
        stats = self.operation_stats[entry.operation]
        stats['count'] += 1
        stats['total_duration'] += entry.duration
        stats['min_duration'] = min(stats['min_duration'], entry.duration)
        stats['max_duration'] = max(stats['max_duration'], entry.duration)

        if not success:
            stats['failures'] += 1

        self.stats['total_duration'] += entry.duration

    def get_operation_stats(self, operation: str) -> Dict:
        """Get statistics for specific operation"""
        if operation not in self.operation_stats:
            return {'exists': False}

        stats = self.operation_stats[operation]

        return {
            'exists': True,
            'operation': operation,
            'count': stats['count'],
            'total_duration': stats['total_duration'],
            'average_duration': stats['total_duration'] / stats['count'],
            'min_duration': stats['min_duration'],
            'max_duration': stats['max_duration'],
            'failure_rate': stats['failures'] / stats['count'],
            'percentage_of_total': (stats['total_duration'] /
                                   max(self.stats['total_duration'], 0.001) * 100)
        }

    def get_hot_paths(self, threshold: float = 0.1) -> List[Dict]:
        """
        Get hot paths (operations taking >threshold of total time)

        Args:
            threshold: Minimum percentage (0.1 = 10%)

        Returns:
            List of hot path operations sorted by duration
        """
        hot_paths = []

        for operation in self.operation_stats.keys():
            stats = self.get_operation_stats(operation)

            if stats['percentage_of_total'] >= (threshold * 100):
                hot_paths.append(stats)

        # Sort by total duration
        hot_paths.sort(key=lambda x: x['total_duration'], reverse=True)

        return hot_paths

    def get_slowest_operations(self, limit: int = 10) -> List[Dict]:
        """Get slowest individual operations"""
        # Sort entries by duration
        sorted_entries = sorted(
            [e for e in self.entries if e.duration is not None],
            key=lambda e: e.duration,
            reverse=True
        )

        return [
            {
                'operation': e.operation,
                'duration': e.duration,
                'timestamp': e.start_time,
                'success': e.success,
                'metadata': e.metadata
            }
            for e in sorted_entries[:limit]
        ]

    def get_bottlenecks(self) -> List[Dict]:
        """
        Identify bottlenecks (80/20 rule)

        Find operations taking 80% of total time
        """
        # Get all operations sorted by total duration
        operations = []
        for op_name, stats in self.operation_stats.items():
            operations.append({
                'operation': op_name,
                'total_duration': stats['total_duration'],
                'count': stats['count'],
                'avg_duration': stats['total_duration'] / stats['count']
            })

        operations.sort(key=lambda x: x['total_duration'], reverse=True)

        # Find operations accounting for 80% of time
        total_time = self.stats['total_duration']
        target_time = total_time * 0.8
        accumulated_time = 0.0
        bottlenecks = []

        for op in operations:
            accumulated_time += op['total_duration']
            bottlenecks.append(op)

            if accumulated_time >= target_time:
                break

        return bottlenecks

    def get_optimization_recommendations(self) -> List[str]:
        """Generate optimization recommendations based on profiling data"""
        recommendations = []

        # Get bottlenecks
        bottlenecks = self.get_bottlenecks()

        if bottlenecks:
            recommendations.append(
                f"Top {len(bottlenecks)} operations account for 80% of time:"
            )
            for op in bottlenecks[:5]:
                recommendations.append(
                    f"  - {op['operation']}: {op['total_duration']:.2f}s "
                    f"({op['count']} calls, avg {op['avg_duration']:.3f}s)"
                )

        # Check for frequently called operations
        for op_name, stats in self.operation_stats.items():
            if stats['count'] > 100:
                avg_duration = stats['total_duration'] / stats['count']
                if avg_duration > 0.1:
                    recommendations.append(
                        f"Optimize {op_name}: called {stats['count']} times, "
                        f"avg {avg_duration:.3f}s per call"
                    )

        # Check for slow individual operations
        slowest = self.get_slowest_operations(limit=5)
        if slowest and slowest[0]['duration'] > 10.0:
            recommendations.append(
                f"Slowest operation: {slowest[0]['operation']} "
                f"took {slowest[0]['duration']:.2f}s"
            )

        # Check failure rates
        for op_name, stats in self.operation_stats.items():
            if stats['count'] > 10:
                failure_rate = stats['failures'] / stats['count']
                if failure_rate > 0.2:
                    recommendations.append(
                        f"High failure rate for {op_name}: {failure_rate:.1%}"
                    )

        return recommendations

    def get_summary(self) -> Dict:
        """Get comprehensive profiling summary"""
        if not self.entries:
            return {
                'total_operations': 0,
                'message': 'No profiling data'
            }

        # Calculate overall stats
        successful = sum(1 for e in self.entries if e.success)
        failed = sum(1 for e in self.entries if not e.success)

        # Get unique operations
        unique_operations = len(self.operation_stats)

        # Get time distribution
        hot_paths = self.get_hot_paths(threshold=0.1)
        bottlenecks = self.get_bottlenecks()

        return {
            'total_operations': self.stats['total_operations'],
            'total_duration': self.stats['total_duration'],
            'unique_operations': unique_operations,
            'successful_operations': successful,
            'failed_operations': failed,
            'success_rate': successful / max(len(self.entries), 1),
            'operations_per_second': (self.stats['total_operations'] /
                                     max(self.stats['total_duration'], 0.001)),
            'hot_paths': len(hot_paths),
            'bottlenecks': len(bottlenecks),
            'recommendations': self.get_optimization_recommendations()
        }

    def get_phase_breakdown(self) -> Dict:
        """
        Get breakdown by phase (Phase 1, Phase 2, Phase 3)

        Assumes operation names start with phase identifier
        """
        phases = {
            'phase1': {'count': 0, 'duration': 0.0},
            'phase2': {'count': 0, 'duration': 0.0},
            'phase3': {'count': 0, 'duration': 0.0},
            'other': {'count': 0, 'duration': 0.0}
        }

        for op_name, stats in self.operation_stats.items():
            op_lower = op_name.lower()

            if 'phase1' in op_lower or 'error_learning' in op_lower or \
               'decision_rule' in op_lower or 'flow_monitor' in op_lower:
                phases['phase1']['count'] += stats['count']
                phases['phase1']['duration'] += stats['total_duration']

            elif 'phase2' in op_lower or 'retry' in op_lower or \
                 'queue' in op_lower or 'auto_fix' in op_lower:
                phases['phase2']['count'] += stats['count']
                phases['phase2']['duration'] += stats['total_duration']

            elif 'phase3' in op_lower or 'confidence' in op_lower or \
                 'degradation' in op_lower or 'budget' in op_lower:
                phases['phase3']['count'] += stats['count']
                phases['phase3']['duration'] += stats['total_duration']

            else:
                phases['other']['count'] += stats['count']
                phases['other']['duration'] += stats['total_duration']

        # Calculate percentages
        total_duration = self.stats['total_duration']
        for phase in phases.values():
            phase['percentage'] = (phase['duration'] /
                                  max(total_duration, 0.001) * 100)
            if phase['count'] > 0:
                phase['avg_duration'] = phase['duration'] / phase['count']

        return phases

    def clear(self):
        """Clear all profiling data"""
        self.entries.clear()
        self.operation_stats.clear()
        self.stats = {
            'total_operations': 0,
            'total_duration': 0.0,
            'profiling_overhead': 0.0
        }

    def disable(self):
        """Disable profiling (reduces overhead)"""
        self.enabled = False

    def enable(self):
        """Enable profiling"""
        self.enabled = True
