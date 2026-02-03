#!/usr/bin/env python3
"""
Business Intelligence Dashboard
Analytics and reporting for business processes
"""
import sys
from pathlib import Path
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict

sys.path.append(str(Path(__file__).parent.parent))


class BIDashboard:
    """
    Business Intelligence and Analytics Dashboard

    Features:
    - SOP performance metrics
    - Process efficiency analysis
    - Execution trends
    - Bottleneck visualization
    - ROI calculation
    - Comparative analysis
    """

    def __init__(self, db_path: str = None):
        workspace = Path(__file__).parent.parent
        if db_path is None:
            db_path = str(workspace / "memory.db")

        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

    # === OVERVIEW METRICS ===

    def get_business_overview(self) -> Dict:
        """
        Get high-level business metrics

        Returns:
            Overview dashboard data
        """
        cursor = self.conn.cursor()

        # Total SOPs
        cursor.execute('SELECT COUNT(*) as count FROM sops WHERE status != "archived"')
        total_sops = cursor.fetchone()['count']

        # Total executions (last 30 days)
        cursor.execute('''
            SELECT COUNT(*) as count FROM sop_executions
            WHERE started_at >= datetime('now', '-30 days')
        ''')
        total_executions = cursor.fetchone()['count']

        # Success rate
        cursor.execute('''
            SELECT
                AVG(CASE WHEN success = 1 THEN 1.0 ELSE 0.0 END) as success_rate
            FROM sop_executions
            WHERE started_at >= datetime('now', '-30 days')
        ''')
        success_rate = cursor.fetchone()['success_rate'] or 0

        # Average automation level
        cursor.execute('''
            SELECT AVG(automation_level) as avg_automation
            FROM sops
            WHERE status != "archived"
        ''')
        avg_automation = cursor.fetchone()['avg_automation'] or 0

        # Active processes (executions in last 24h)
        cursor.execute('''
            SELECT COUNT(DISTINCT sop_id) as count
            FROM sop_executions
            WHERE started_at >= datetime('now', '-24 hours')
        ''')
        active_processes = cursor.fetchone()['count']

        return {
            'total_sops': total_sops,
            'total_executions_30d': total_executions,
            'success_rate': round(success_rate, 2),
            'avg_automation_level': round(avg_automation, 2),
            'active_processes_24h': active_processes
        }

    # === PERFORMANCE METRICS ===

    def get_sop_performance(self, sop_id: int = None, days: int = 30) -> List[Dict]:
        """
        Get SOP performance metrics

        Args:
            sop_id: Specific SOP or None for all
            days: Days of history

        Returns:
            Performance metrics per SOP
        """
        cursor = self.conn.cursor()

        if sop_id:
            cursor.execute('''
                SELECT
                    s.id,
                    s.sop_code,
                    s.sop_title,
                    COUNT(e.id) as execution_count,
                    AVG(CASE WHEN e.success = 1 THEN 1.0 ELSE 0.0 END) as success_rate,
                    AVG(e.actual_duration_minutes) as avg_duration,
                    MIN(e.actual_duration_minutes) as min_duration,
                    MAX(e.actual_duration_minutes) as max_duration,
                    s.automation_level
                FROM sops s
                LEFT JOIN sop_executions e ON s.id = e.sop_id
                    AND e.started_at >= datetime('now', ? || ' days')
                WHERE s.id = ?
                GROUP BY s.id
            ''', (f'-{days}', sop_id))
        else:
            cursor.execute('''
                SELECT
                    s.id,
                    s.sop_code,
                    s.sop_title,
                    COUNT(e.id) as execution_count,
                    AVG(CASE WHEN e.success = 1 THEN 1.0 ELSE 0.0 END) as success_rate,
                    AVG(e.actual_duration_minutes) as avg_duration,
                    MIN(e.actual_duration_minutes) as min_duration,
                    MAX(e.actual_duration_minutes) as max_duration,
                    s.automation_level
                FROM sops s
                LEFT JOIN sop_executions e ON s.id = e.sop_id
                    AND e.started_at >= datetime('now', ? || ' days')
                WHERE s.status != "archived"
                GROUP BY s.id
                ORDER BY execution_count DESC
            ''', (f'-{days}',))

        results = []
        for row in cursor.fetchall():
            results.append({
                'sop_id': row['id'],
                'sop_code': row['sop_code'],
                'title': row['sop_title'],
                'executions': row['execution_count'],
                'success_rate': round(row['success_rate'], 2) if row['success_rate'] else 0,
                'avg_duration': round(row['avg_duration'], 1) if row['avg_duration'] else 0,
                'min_duration': row['min_duration'],
                'max_duration': row['max_duration'],
                'automation_level': round(row['automation_level'], 2)
            })

        return results

    # === TREND ANALYSIS ===

    def get_execution_trends(self, days: int = 30, granularity: str = 'day') -> Dict:
        """
        Get execution trends over time

        Args:
            days: Days of history
            granularity: 'day' or 'hour'

        Returns:
            Trend data
        """
        cursor = self.conn.cursor()

        if granularity == 'day':
            cursor.execute('''
                SELECT
                    DATE(started_at) as period,
                    COUNT(*) as total,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                    AVG(actual_duration_minutes) as avg_duration
                FROM sop_executions
                WHERE started_at >= datetime('now', ? || ' days')
                GROUP BY DATE(started_at)
                ORDER BY period
            ''', (f'-{days}',))
        else:
            cursor.execute('''
                SELECT
                    strftime('%Y-%m-%d %H:00:00', started_at) as period,
                    COUNT(*) as total,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                    AVG(actual_duration_minutes) as avg_duration
                FROM sop_executions
                WHERE started_at >= datetime('now', ? || ' hours')
                GROUP BY strftime('%Y-%m-%d %H:00:00', started_at)
                ORDER BY period
            ''', (f'-{days * 24}',))

        trends = {
            'periods': [],
            'total_executions': [],
            'successful_executions': [],
            'avg_durations': []
        }

        for row in cursor.fetchall():
            trends['periods'].append(row['period'])
            trends['total_executions'].append(row['total'])
            trends['successful_executions'].append(row['successful'])
            trends['avg_durations'].append(round(row['avg_duration'], 1) if row['avg_duration'] else 0)

        return trends

    # === EFFICIENCY ANALYSIS ===

    def get_efficiency_report(self) -> List[Dict]:
        """
        Get efficiency report for all SOPs

        Returns:
            Efficiency metrics
        """
        cursor = self.conn.cursor()

        cursor.execute('''
            SELECT
                s.id,
                s.sop_code,
                s.sop_title,
                s.estimated_duration_minutes,
                s.automation_level,
                AVG(e.actual_duration_minutes) as avg_actual_duration,
                AVG(CASE WHEN e.success = 1 THEN 1.0 ELSE 0.0 END) as success_rate,
                COUNT(e.id) as execution_count
            FROM sops s
            LEFT JOIN sop_executions e ON s.id = e.sop_id
            WHERE s.status != "archived"
            GROUP BY s.id
        ''')

        results = []
        for row in cursor.fetchall():
            # Calculate efficiency score
            duration_efficiency = 0
            if row['avg_actual_duration'] and row['estimated_duration_minutes']:
                duration_efficiency = min(
                    row['estimated_duration_minutes'] / row['avg_actual_duration'],
                    1.0
                )

            automation_efficiency = row['automation_level']
            success_efficiency = row['success_rate'] if row['success_rate'] else 0

            overall_efficiency = (
                duration_efficiency * 0.4 +
                automation_efficiency * 0.3 +
                success_efficiency * 0.3
            )

            results.append({
                'sop_id': row['id'],
                'sop_code': row['sop_code'],
                'title': row['sop_title'],
                'efficiency_score': round(overall_efficiency, 2),
                'duration_efficiency': round(duration_efficiency, 2),
                'automation_level': round(automation_efficiency, 2),
                'success_rate': round(success_efficiency, 2),
                'executions': row['execution_count']
            })

        # Sort by efficiency score
        results.sort(key=lambda x: x['efficiency_score'], reverse=True)

        return results

    # === BOTTLENECK ANALYSIS ===

    def get_bottleneck_summary(self) -> List[Dict]:
        """
        Get summary of process bottlenecks

        Returns:
            Bottleneck summary
        """
        cursor = self.conn.cursor()

        # Get slowest steps across all SOPs
        cursor.execute('''
            SELECT
                s.sop_code,
                s.sop_title,
                ss.step_number,
                ss.step_title,
                AVG(CAST((julianday(se.completed_at) - julianday(se.started_at)) * 24 * 60 AS INTEGER)) as avg_duration,
                COUNT(*) as execution_count
            FROM sop_steps ss
            JOIN sops s ON ss.sop_id = s.id
            LEFT JOIN step_executions se ON ss.id = se.step_id
            WHERE se.completed_at IS NOT NULL
            AND s.status != "archived"
            GROUP BY ss.id
            HAVING COUNT(*) >= 3
            ORDER BY avg_duration DESC
            LIMIT 20
        ''')

        bottlenecks = []
        for row in cursor.fetchall():
            bottlenecks.append({
                'sop_code': row['sop_code'],
                'sop_title': row['sop_title'],
                'step_number': row['step_number'],
                'step_title': row['step_title'],
                'avg_duration_minutes': round(row['avg_duration'], 1),
                'executions': row['execution_count']
            })

        return bottlenecks

    # === ROI CALCULATION ===

    def calculate_automation_roi(self, sop_id: int) -> Dict:
        """
        Calculate ROI for SOP automation

        Args:
            sop_id: SOP to analyze

        Returns:
            ROI metrics
        """
        cursor = self.conn.cursor()

        # Get SOP details
        cursor.execute('''
            SELECT
                sop_code,
                sop_title,
                estimated_duration_minutes,
                automation_level
            FROM sops
            WHERE id = ?
        ''', (sop_id,))

        sop = dict(cursor.fetchone())

        # Get execution stats
        cursor.execute('''
            SELECT
                COUNT(*) as execution_count,
                AVG(actual_duration_minutes) as avg_duration
            FROM sop_executions
            WHERE sop_id = ?
            AND started_at >= datetime('now', '-30 days')
        ''', (sop_id,))

        stats = dict(cursor.fetchone())

        if not stats['execution_count']:
            return {
                'sop_code': sop['sop_code'],
                'status': 'insufficient_data'
            }

        # Calculate time saved (assuming manual execution = avg_duration / automation_level)
        automated_time = stats['avg_duration']
        manual_time = automated_time / max(sop['automation_level'], 0.1)
        time_saved_per_execution = manual_time - automated_time

        # Monthly projections
        monthly_executions = (stats['execution_count'] / 30) * 30
        monthly_time_saved_hours = (time_saved_per_execution * monthly_executions) / 60

        # Cost savings (assuming $50/hour labor cost)
        hourly_rate = 50
        monthly_savings = monthly_time_saved_hours * hourly_rate
        annual_savings = monthly_savings * 12

        return {
            'sop_code': sop['sop_code'],
            'title': sop['sop_title'],
            'automation_level': round(sop['automation_level'], 2),
            'monthly_executions': round(monthly_executions, 0),
            'time_saved_per_execution_minutes': round(time_saved_per_execution, 1),
            'monthly_time_saved_hours': round(monthly_time_saved_hours, 1),
            'monthly_cost_savings': round(monthly_savings, 2),
            'annual_cost_savings': round(annual_savings, 2)
        }

    # === COMPARATIVE ANALYSIS ===

    def compare_sops(self, sop_ids: List[int]) -> Dict:
        """
        Compare multiple SOPs

        Args:
            sop_ids: List of SOP IDs to compare

        Returns:
            Comparative metrics
        """
        results = []

        for sop_id in sop_ids:
            perf = self.get_sop_performance(sop_id=sop_id)
            if perf:
                results.append(perf[0])

        return {
            'sops': results,
            'comparison': {
                'fastest': min(results, key=lambda x: x['avg_duration']) if results else None,
                'most_reliable': max(results, key=lambda x: x['success_rate']) if results else None,
                'most_automated': max(results, key=lambda x: x['automation_level']) if results else None,
                'most_executed': max(results, key=lambda x: x['executions']) if results else None
            }
        }

    # === FUNCTION ANALYSIS ===

    def get_function_performance(self) -> List[Dict]:
        """
        Get performance by business function

        Returns:
            Function-level metrics
        """
        cursor = self.conn.cursor()

        cursor.execute('''
            SELECT
                bf.function_name,
                COUNT(DISTINCT s.id) as sop_count,
                COUNT(e.id) as total_executions,
                AVG(CASE WHEN e.success = 1 THEN 1.0 ELSE 0.0 END) as success_rate,
                AVG(s.automation_level) as avg_automation
            FROM business_functions bf
            LEFT JOIN sops s ON bf.id = s.function_id
            LEFT JOIN sop_executions e ON s.id = e.sop_id
                AND e.started_at >= datetime('now', '-30 days')
            GROUP BY bf.id
            ORDER BY total_executions DESC
        ''')

        results = []
        for row in cursor.fetchall():
            results.append({
                'function': row['function_name'],
                'sop_count': row['sop_count'],
                'executions_30d': row['total_executions'],
                'success_rate': round(row['success_rate'], 2) if row['success_rate'] else 0,
                'avg_automation': round(row['avg_automation'], 2) if row['avg_automation'] else 0
            })

        return results

    def close(self):
        """Close database connection"""
        self.conn.close()


# === TEST CODE ===

def main():
    """Test BI dashboard"""
    print("Testing Business Intelligence Dashboard")
    print("=" * 70)

    dashboard = BIDashboard()

    try:
        print("\n1. Business Overview...")
        overview = dashboard.get_business_overview()
        print(f"   Total SOPs: {overview['total_sops']}")
        print(f"   Executions (30d): {overview['total_executions_30d']}")
        print(f"   Success Rate: {overview['success_rate']:.0%}")
        print(f"   Avg Automation: {overview['avg_automation_level']:.0%}")

        print("\n2. SOP Performance...")
        performance = dashboard.get_sop_performance(days=30)
        print(f"   Analyzed {len(performance)} SOPs")
        if performance:
            top = performance[0]
            print(f"   Top SOP: {top['sop_code']} ({top['executions']} executions)")

        print("\n3. Execution Trends...")
        trends = dashboard.get_execution_trends(days=7)
        print(f"   Periods analyzed: {len(trends['periods'])}")

        print("\n4. Efficiency Report...")
        efficiency = dashboard.get_efficiency_report()
        print(f"   Analyzed {len(efficiency)} SOPs")
        if efficiency:
            best = efficiency[0]
            print(f"   Most efficient: {best['sop_code']} (score: {best['efficiency_score']})")

        print("\n5. Bottleneck Summary...")
        bottlenecks = dashboard.get_bottleneck_summary()
        print(f"   Found {len(bottlenecks)} bottlenecks")

        print("\n6. Function Performance...")
        functions = dashboard.get_function_performance()
        print(f"   Analyzed {len(functions)} business functions")

        print(f"\n[OK] BI Dashboard working!")
        print(f"Database: {dashboard.db_path}")

    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        dashboard.close()


if __name__ == "__main__":
    main()
