#!/usr/bin/env python3
"""Error Dashboard - Comprehensive error analytics and visualization"""
import sys
from pathlib import Path
from typing import Dict, List
from datetime import datetime, timedelta
from collections import defaultdict
import json

sys.path.append(str(Path(__file__).parent.parent))

from core.persistent_memory import PersistentMemory

class ErrorDashboard:
    """Comprehensive error analytics dashboard"""

    def __init__(self, db_path: str = None):
        workspace = Path(__file__).parent.parent
        if db_path is None:
            db_path = str(workspace / "memory.db")

        self.memory = PersistentMemory(db_path)

    def generate_report(self, hours: int = 24) -> Dict:
        """Generate comprehensive error report"""
        report = {
            'period': f'Last {hours} hours',
            'generated_at': datetime.now().isoformat(),
            'summary': self._get_summary(hours),
            'error_breakdown': self._get_error_breakdown(hours),
            'recovery_stats': self._get_recovery_stats(hours),
            'trends': self._get_trends(hours),
            'top_errors': self._get_top_errors(hours),
            'recommendations': self._get_recommendations(hours)
        }

        return report

    def _get_summary(self, hours: int) -> Dict:
        """Get error summary"""
        cursor = self.memory.conn.cursor()

        # Total errors
        cursor.execute("""
            SELECT COUNT(*) FROM decisions
            WHERE decision LIKE '%Error occurred:%'
            AND created_at >= datetime('now', ?)
        """, (f'-{hours} hours',))
        total_errors = cursor.fetchone()[0]

        # Recovered errors
        cursor.execute("""
            SELECT COUNT(*) FROM decisions
            WHERE decision LIKE '%Error recovered:%'
            AND created_at >= datetime('now', ?)
        """, (f'-{hours} hours',))
        recovered = cursor.fetchone()[0]

        # Critical errors
        cursor.execute("""
            SELECT COUNT(*) FROM decisions
            WHERE decision LIKE '%CRITICAL ERROR%'
            AND created_at >= datetime('now', ?)
        """, (f'-{hours} hours',))
        critical = cursor.fetchone()[0]

        recovery_rate = (recovered / total_errors * 100) if total_errors > 0 else 0

        return {
            'total_errors': total_errors,
            'recovered': recovered,
            'failed_recovery': total_errors - recovered,
            'critical_errors': critical,
            'recovery_rate': round(recovery_rate, 1)
        }

    def _get_error_breakdown(self, hours: int) -> Dict:
        """Get error breakdown by type"""
        cursor = self.memory.conn.cursor()

        cursor.execute("""
            SELECT decision, COUNT(*) as count
            FROM decisions
            WHERE decision LIKE '%Error occurred:%'
            AND created_at >= datetime('now', ?)
            GROUP BY decision
            ORDER BY count DESC
        """, (f'-{hours} hours',))

        breakdown = {}
        for row in cursor.fetchall():
            decision = row['decision']
            # Extract error type
            if 'Error occurred:' in decision:
                error_type = decision.split('Error occurred:')[1].split('\n')[0].strip()
                breakdown[error_type] = row['count']

        return breakdown

    def _get_recovery_stats(self, hours: int) -> Dict:
        """Get recovery statistics"""
        cursor = self.memory.conn.cursor()

        # Recovery by strategy
        cursor.execute("""
            SELECT decision, COUNT(*) as count
            FROM decisions
            WHERE decision LIKE '%Error recovered:%'
            AND created_at >= datetime('now', ?)
            GROUP BY decision
        """, (f'-{hours} hours',))

        strategies = defaultdict(int)
        for row in cursor.fetchall():
            decision = row['decision']
            # Extract strategy
            if 'Strategy:' in decision:
                strategy = decision.split('Strategy:')[1].split(',')[0].strip()
                strategies[strategy] += row['count']

        return dict(strategies)

    def _get_trends(self, hours: int) -> Dict:
        """Get error trends"""
        cursor = self.memory.conn.cursor()

        # Hourly error counts
        cursor.execute("""
            SELECT
                strftime('%H', created_at) as hour,
                COUNT(*) as count
            FROM decisions
            WHERE decision LIKE '%Error occurred:%'
            AND created_at >= datetime('now', ?)
            GROUP BY hour
            ORDER BY hour
        """, (f'-{hours} hours',))

        hourly = {int(row['hour']): row['count'] for row in cursor.fetchall()}

        # Determine trend
        if len(hourly) >= 2:
            hours_list = sorted(hourly.keys())
            first_half = sum(hourly[h] for h in hours_list[:len(hours_list)//2])
            second_half = sum(hourly[h] for h in hours_list[len(hours_list)//2:])

            if second_half > first_half * 1.2:
                trend = 'increasing'
            elif second_half < first_half * 0.8:
                trend = 'decreasing'
            else:
                trend = 'stable'
        else:
            trend = 'insufficient_data'

        return {
            'hourly_distribution': hourly,
            'trend': trend
        }

    def _get_top_errors(self, hours: int, limit: int = 5) -> List[Dict]:
        """Get top errors"""
        breakdown = self._get_error_breakdown(hours)

        top = sorted(breakdown.items(), key=lambda x: x[1], reverse=True)[:limit]

        return [
            {'error_type': error_type, 'count': count}
            for error_type, count in top
        ]

    def _get_recommendations(self, hours: int) -> List[str]:
        """Get recommendations based on error analysis"""
        recommendations = []

        summary = self._get_summary(hours)
        trends = self._get_trends(hours)
        top_errors = self._get_top_errors(hours)

        # Recovery rate recommendations
        if summary['recovery_rate'] < 50:
            recommendations.append(
                'LOW RECOVERY RATE: Add more recovery strategies or improve existing ones'
            )

        # Critical error recommendations
        if summary['critical_errors'] > 0:
            recommendations.append(
                f'CRITICAL ERRORS DETECTED: {summary["critical_errors"]} critical errors need immediate attention'
            )

        # Trend recommendations
        if trends['trend'] == 'increasing':
            recommendations.append(
                'ERROR RATE INCREASING: Investigate recent changes and system state'
            )

        # Top error recommendations
        if top_errors:
            top_error = top_errors[0]
            if top_error['count'] > 10:
                recommendations.append(
                    f'FREQUENT ERROR: {top_error["error_type"]} occurring {top_error["count"]} times - needs fix'
                )

        if not recommendations:
            recommendations.append('System healthy - no immediate issues detected')

        return recommendations

    def export_report(self, report: Dict, filepath: str = None):
        """Export report to file"""
        if filepath is None:
            workspace = Path(__file__).parent.parent
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filepath = workspace / f'error_report_{timestamp}.json'

        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)

        return filepath

    def print_report(self, report: Dict):
        """Print formatted report"""
        print("=" * 60)
        print("ERROR DASHBOARD REPORT")
        print("=" * 60)

        print(f"\nPeriod: {report['period']}")
        print(f"Generated: {report['generated_at']}")

        # Summary
        print("\n--- SUMMARY ---")
        summary = report['summary']
        print(f"Total errors: {summary['total_errors']}")
        print(f"Recovered: {summary['recovered']} ({summary['recovery_rate']}%)")
        print(f"Failed recovery: {summary['failed_recovery']}")
        print(f"Critical errors: {summary['critical_errors']}")

        # Top errors
        print("\n--- TOP ERRORS ---")
        for i, error in enumerate(report['top_errors'], 1):
            print(f"{i}. {error['error_type']}: {error['count']} occurrences")

        # Recovery strategies
        if report['recovery_stats']:
            print("\n--- RECOVERY STRATEGIES ---")
            for strategy, count in report['recovery_stats'].items():
                print(f"  {strategy}: {count} successful recoveries")

        # Trends
        print("\n--- TRENDS ---")
        print(f"Error rate trend: {report['trends']['trend']}")

        # Recommendations
        print("\n--- RECOMMENDATIONS ---")
        for rec in report['recommendations']:
            print(f"  - {rec}")

        print("\n" + "=" * 60)


if __name__ == '__main__':
    dashboard = ErrorDashboard()

    print("Error Dashboard ready!")

    # Generate report
    print("\nGenerating error report...")
    report = dashboard.generate_report(hours=24)

    # Print report
    dashboard.print_report(report)

    # Export report
    filepath = dashboard.export_report(report)
    print(f"\nReport exported to: {filepath}")
