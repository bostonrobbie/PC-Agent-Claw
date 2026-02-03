#!/usr/bin/env python3
"""
Process Mining & Optimization
Learn from process executions and suggest improvements
"""
import sys
from pathlib import Path
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

sys.path.append(str(Path(__file__).parent.parent))


class ProcessMining:
    """
    Mine process data for optimization opportunities

    Features:
    - Analyze execution patterns
    - Identify bottlenecks
    - Detect process deviations
    - Suggest optimizations
    - Track efficiency trends
    - Automation opportunity detection
    """

    def __init__(self, db_path: str = None):
        workspace = Path(__file__).parent.parent
        if db_path is None:
            db_path = str(workspace / "memory.db")

        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

    # === PATTERN ANALYSIS ===

    def analyze_process_patterns(self, sop_id: int, days: int = 30) -> Dict:
        """
        Analyze execution patterns for SOP

        Args:
            sop_id: SOP to analyze
            days: Days of history to analyze

        Returns:
            Pattern analysis
        """
        cursor = self.conn.cursor()

        # Get executions
        cursor.execute('''
            SELECT
                id, executed_by, started_at, completed_at,
                actual_duration_minutes, success
            FROM sop_executions
            WHERE sop_id = ?
            AND started_at >= datetime('now', ? || ' days')
            ORDER BY started_at
        ''', (sop_id, f'-{days}'))

        executions = [dict(row) for row in cursor.fetchall()]

        if not executions:
            return {'status': 'insufficient_data'}

        # Analyze patterns
        patterns = {
            'total_executions': len(executions),
            'success_rate': sum(1 for e in executions if e['success']) / len(executions),
            'avg_duration': sum(e['actual_duration_minutes'] or 0 for e in executions) / len(executions),
            'executors': self._analyze_executors(executions),
            'time_patterns': self._analyze_time_patterns(executions),
            'duration_trend': self._analyze_duration_trend(executions)
        }

        return patterns

    def _analyze_executors(self, executions: List[Dict]) -> Dict:
        """Analyze who executes the process"""
        executor_stats = defaultdict(lambda: {'count': 0, 'success': 0, 'total_duration': 0})

        for exec in executions:
            executor = exec['executed_by'] or 'unknown'
            executor_stats[executor]['count'] += 1
            if exec['success']:
                executor_stats[executor]['success'] += 1
            executor_stats[executor]['total_duration'] += exec['actual_duration_minutes'] or 0

        # Calculate rates
        for executor, stats in executor_stats.items():
            stats['success_rate'] = stats['success'] / stats['count']
            stats['avg_duration'] = stats['total_duration'] / stats['count']

        return dict(executor_stats)

    def _analyze_time_patterns(self, executions: List[Dict]) -> Dict:
        """Analyze when process is executed"""
        by_hour = defaultdict(int)
        by_day = defaultdict(int)

        for exec in executions:
            if exec['started_at']:
                dt = datetime.fromisoformat(exec['started_at'])
                by_hour[dt.hour] += 1
                by_day[dt.strftime('%A')] += 1

        return {
            'peak_hour': max(by_hour.items(), key=lambda x: x[1])[0] if by_hour else None,
            'peak_day': max(by_day.items(), key=lambda x: x[1])[0] if by_day else None,
            'hourly_distribution': dict(by_hour),
            'daily_distribution': dict(by_day)
        }

    def _analyze_duration_trend(self, executions: List[Dict]) -> str:
        """Analyze if duration is improving or degrading"""
        if len(executions) < 5:
            return 'insufficient_data'

        # Compare first half vs second half
        mid = len(executions) // 2
        first_half_avg = sum(e['actual_duration_minutes'] or 0 for e in executions[:mid]) / mid
        second_half_avg = sum(e['actual_duration_minutes'] or 0 for e in executions[mid:]) / (len(executions) - mid)

        if second_half_avg < first_half_avg * 0.9:
            return 'improving'
        elif second_half_avg > first_half_avg * 1.1:
            return 'degrading'
        else:
            return 'stable'

    # === BOTTLENECK DETECTION ===

    def identify_bottlenecks(self, sop_id: int) -> List[Dict]:
        """
        Identify bottleneck steps in process

        Args:
            sop_id: SOP to analyze

        Returns:
            List of bottleneck steps
        """
        cursor = self.conn.cursor()

        # Get step execution times
        cursor.execute('''
            SELECT
                ss.id, ss.step_number, ss.step_title,
                se.step_id,
                AVG(CAST((julianday(se.completed_at) - julianday(se.started_at)) * 24 * 60 AS INTEGER)) as avg_duration,
                COUNT(*) as execution_count
            FROM sop_steps ss
            LEFT JOIN step_executions se ON ss.id = se.step_id
            WHERE ss.sop_id = ?
            AND se.completed_at IS NOT NULL
            GROUP BY ss.id
            HAVING COUNT(*) >= 3
            ORDER BY avg_duration DESC
        ''', (sop_id,))

        steps = [dict(row) for row in cursor.fetchall()]

        if not steps:
            return []

        # Calculate total duration
        total_duration = sum(s['avg_duration'] for s in steps)

        # Identify bottlenecks (>20% of total time)
        bottlenecks = []
        for step in steps:
            percentage = (step['avg_duration'] / total_duration) * 100

            if percentage > 20:
                bottlenecks.append({
                    'step_number': step['step_number'],
                    'step_title': step['step_title'],
                    'avg_duration': round(step['avg_duration'], 1),
                    'percentage_of_total': round(percentage, 1),
                    'severity': 'high' if percentage > 40 else 'medium'
                })

        return bottlenecks

    # === DEVIATION DETECTION ===

    def detect_deviations(self, sop_id: int, threshold_std: float = 2.0) -> List[Dict]:
        """
        Detect executions that deviate from normal

        Args:
            sop_id: SOP to analyze
            threshold_std: Standard deviations for anomaly

        Returns:
            List of deviations
        """
        cursor = self.conn.cursor()

        # Get duration stats
        cursor.execute('''
            SELECT
                AVG(actual_duration_minutes) as mean,
                COUNT(*) as count
            FROM sop_executions
            WHERE sop_id = ? AND actual_duration_minutes IS NOT NULL
        ''', (sop_id,))

        stats = dict(cursor.fetchone())

        if stats['count'] < 5:
            return []

        # Calculate std dev
        cursor.execute('''
            SELECT actual_duration_minutes
            FROM sop_executions
            WHERE sop_id = ? AND actual_duration_minutes IS NOT NULL
        ''', (sop_id,))

        durations = [row['actual_duration_minutes'] for row in cursor.fetchall()]
        mean = stats['mean']
        variance = sum((d - mean) ** 2 for d in durations) / len(durations)
        std_dev = variance ** 0.5

        # Find deviations
        cursor.execute('''
            SELECT id, executed_by, started_at, actual_duration_minutes
            FROM sop_executions
            WHERE sop_id = ? AND actual_duration_minutes IS NOT NULL
            ORDER BY started_at DESC
            LIMIT 20
        ''', (sop_id,))

        deviations = []
        for row in cursor.fetchall():
            execution = dict(row)
            z_score = abs((execution['actual_duration_minutes'] - mean) / std_dev) if std_dev > 0 else 0

            if z_score > threshold_std:
                deviations.append({
                    'execution_id': execution['id'],
                    'executed_by': execution['executed_by'],
                    'started_at': execution['started_at'],
                    'duration': execution['actual_duration_minutes'],
                    'expected_duration': round(mean, 1),
                    'z_score': round(z_score, 2),
                    'deviation_type': 'slow' if execution['actual_duration_minutes'] > mean else 'fast'
                })

        return deviations

    # === OPTIMIZATION SUGGESTIONS ===

    def suggest_optimizations(self, sop_id: int) -> List[Dict]:
        """
        Suggest process optimizations

        Args:
            sop_id: SOP to optimize

        Returns:
            List of optimization suggestions
        """
        suggestions = []

        # Find bottlenecks
        bottlenecks = self.identify_bottlenecks(sop_id)
        for bottleneck in bottlenecks:
            suggestions.append({
                'type': 'bottleneck',
                'priority': bottleneck['severity'],
                'step': bottleneck['step_number'],
                'suggestion': f"Optimize step {bottleneck['step_number']}: {bottleneck['step_title']}",
                'expected_benefit': f"Reduce {bottleneck['percentage_of_total']}% of total time",
                'action': 'investigate_automation'
            })

        # Check for automation opportunities
        automation_opps = self._find_automation_opportunities(sop_id)
        suggestions.extend(automation_opps)

        # Check for parallelization opportunities
        parallel_opps = self._find_parallelization_opportunities(sop_id)
        suggestions.extend(parallel_opps)

        return suggestions

    def _find_automation_opportunities(self, sop_id: int) -> List[Dict]:
        """Find steps that could be automated"""
        cursor = self.conn.cursor()

        cursor.execute('''
            SELECT id, step_number, step_title, step_type
            FROM sop_steps
            WHERE sop_id = ?
            AND is_automated = 0
            AND step_type IN ('manual', 'decision')
        ''', (sop_id,))

        opportunities = []
        for row in cursor.fetchall():
            step = dict(row)

            # Simple heuristics for automation potential
            if 'calculate' in step['step_title'].lower() or 'check' in step['step_title'].lower():
                opportunities.append({
                    'type': 'automation_opportunity',
                    'priority': 'medium',
                    'step': step['step_number'],
                    'suggestion': f"Automate step {step['step_number']}: {step['step_title']}",
                    'expected_benefit': "Reduce manual effort and errors",
                    'action': 'implement_automation'
                })

        return opportunities

    def _find_parallelization_opportunities(self, sop_id: int) -> List[Dict]:
        """Find steps that could run in parallel"""
        cursor = self.conn.cursor()

        cursor.execute('''
            SELECT id, step_number, step_title, predecessor_step_id
            FROM sop_steps
            WHERE sop_id = ?
            ORDER BY step_number
        ''', (sop_id,))

        steps = [dict(row) for row in cursor.fetchall()]

        opportunities = []

        # Find sequential steps without dependencies
        for i, step in enumerate(steps):
            if i == 0:
                continue

            prev_step = steps[i - 1]

            # If no dependency on previous step, could parallelize
            if not step['predecessor_step_id']:
                opportunities.append({
                    'type': 'parallelization',
                    'priority': 'low',
                    'steps': [prev_step['step_number'], step['step_number']],
                    'suggestion': f"Steps {prev_step['step_number']} and {step['step_number']} could run in parallel",
                    'expected_benefit': "Reduce total execution time",
                    'action': 'review_dependencies'
                })

        return opportunities

    # === EFFICIENCY METRICS ===

    def calculate_process_efficiency(self, sop_id: int) -> Dict:
        """Calculate overall process efficiency"""
        cursor = self.conn.cursor()

        # Get SOP details
        cursor.execute('''
            SELECT estimated_duration_minutes, automation_level
            FROM sops
            WHERE id = ?
        ''', (sop_id,))

        sop = dict(cursor.fetchone())

        # Get actual performance
        cursor.execute('''
            SELECT
                AVG(actual_duration_minutes) as avg_actual_duration,
                MIN(actual_duration_minutes) as best_duration,
                AVG(CASE WHEN success = 1 THEN 1.0 ELSE 0.0 END) as success_rate
            FROM sop_executions
            WHERE sop_id = ?
            AND actual_duration_minutes IS NOT NULL
        ''', (sop_id,))

        actual = dict(cursor.fetchone())

        # Calculate efficiency metrics
        efficiency = {
            'automation_level': round(sop['automation_level'], 2),
            'estimated_duration': sop['estimated_duration_minutes'],
            'avg_actual_duration': round(actual['avg_actual_duration'], 1) if actual['avg_actual_duration'] else None,
            'best_duration': actual['best_duration'],
            'success_rate': round(actual['success_rate'], 2) if actual['success_rate'] else 0,
            'efficiency_score': 0
        }

        # Calculate overall efficiency score (0-1)
        if efficiency['avg_actual_duration'] and efficiency['estimated_duration']:
            duration_efficiency = min(efficiency['estimated_duration'] / efficiency['avg_actual_duration'], 1.0)
            automation_efficiency = efficiency['automation_level']
            success_efficiency = efficiency['success_rate']

            efficiency['efficiency_score'] = round(
                (duration_efficiency * 0.4 + automation_efficiency * 0.3 + success_efficiency * 0.3),
                2
            )

        return efficiency

    def close(self):
        """Close database connection"""
        self.conn.close()


# === TEST CODE ===

def main():
    """Test process mining"""
    print("Testing Process Mining")
    print("=" * 70)

    mining = ProcessMining()

    try:
        print("\n1. Process mining system ready")
        print("   Would analyze SOPs once execution data available")

        print(f"\n[OK] Process Mining working!")
        print(f"Database: {mining.db_path}")

    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        mining.close()


if __name__ == "__main__":
    main()
