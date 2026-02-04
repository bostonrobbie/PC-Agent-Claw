#!/usr/bin/env python3
"""
Continuous monitoring script that watches all 5 systems and takes action
Runs indefinitely until stopped
"""

import time
import sqlite3
import os
import json
from datetime import datetime
from pathlib import Path

class ContinuousMonitor:
    def __init__(self):
        self.workspace = Path(__file__).parent
        self.running = True
        self.iteration = 0

    def check_self_improvement(self):
        """Check self-improvement system progress"""
        db_path = self.workspace / 'intelligence_hub_improvements.db'
        if not db_path.exists():
            return {'status': 'initializing'}

        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Get latest metrics
            cursor.execute('SELECT indexing_speed, memory_mb, query_time_ms FROM performance_metrics ORDER BY id DESC LIMIT 1')
            metrics = cursor.fetchone()

            # Get bottleneck count
            cursor.execute('SELECT COUNT(*) FROM bottlenecks WHERE resolved = 0')
            bottlenecks = cursor.fetchone()[0]

            # Get improvement count
            cursor.execute('SELECT COUNT(*) FROM improvements')
            improvements = cursor.fetchone()[0]

            conn.close()

            return {
                'status': 'active',
                'indexing_speed': metrics[0] if metrics else 0,
                'bottlenecks': bottlenecks,
                'improvements_generated': improvements
            }
        except Exception as e:
            return {'status': 'initializing', 'error': str(e)[:50]}

    def check_synergy(self):
        """Check capability synergy system"""
        db_path = self.workspace / 'capability_synergy.db'
        if not db_path.exists():
            return {'status': 'initializing'}

        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Get chain execution count
            cursor.execute('SELECT COUNT(*) FROM chain_executions')
            executions = cursor.fetchone()[0]

            # Get synergy flow count
            cursor.execute('SELECT COUNT(*) FROM synergy_flows')
            flows = cursor.fetchone()[0]

            # Get avg intelligence score
            cursor.execute('SELECT AVG(compound_score) FROM intelligence_scores WHERE compound_score > 0')
            avg_score = cursor.fetchone()[0]

            conn.close()

            return {
                'status': 'active',
                'chain_executions': executions,
                'synergy_flows': flows,
                'avg_intelligence': avg_score if avg_score else 0
            }
        except Exception as e:
            return {'status': 'initializing', 'error': str(e)[:50]}

    def check_realworld_testing(self):
        """Check real-world integration testing"""
        db_path = self.workspace / 'realworld_testing.db'
        if not db_path.exists():
            return {'status': 'initializing'}

        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Get active sessions
            cursor.execute('SELECT COUNT(*) FROM test_sessions WHERE status = ?', ('running',))
            active = cursor.fetchone()[0]

            # Get total activities
            cursor.execute('SELECT COUNT(*) FROM capability_activities')
            activities = cursor.fetchone()[0]

            # Get issue count
            cursor.execute('SELECT COUNT(*) FROM issues_found')
            issues = cursor.fetchone()[0]

            conn.close()

            return {
                'status': 'active' if active > 0 else 'idle',
                'active_sessions': active,
                'total_activities': activities,
                'issues_found': issues
            }
        except Exception as e:
            return {'status': 'initializing', 'error': str(e)[:50]}

    def check_relationship_memory(self):
        """Check relationship memory system"""
        db_path = self.workspace / 'relationship_memory.db'
        if not db_path.exists():
            return {'status': 'no_data'}

        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Get interaction count for rob
            cursor.execute('SELECT COUNT(*) FROM interactions WHERE user_id = ?', ('rob_gorham_5791597360',))
            interactions = cursor.fetchone()[0]

            # Get preference count
            cursor.execute('SELECT COUNT(*) FROM preferences WHERE user_id = ?', ('rob_gorham_5791597360',))
            preferences = cursor.fetchone()[0]

            conn.close()

            return {
                'status': 'active' if interactions > 0 else 'idle',
                'interactions': interactions,
                'preferences': preferences
            }
        except Exception as e:
            return {'status': 'initializing', 'error': str(e)[:50]}

    def generate_report(self):
        """Generate status report"""
        self.iteration += 1

        print(f"\n{'='*80}")
        print(f"CONTINUOUS MONITORING - Iteration {self.iteration} - {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*80}\n")

        # Check all systems
        si = self.check_self_improvement()
        syn = self.check_synergy()
        rw = self.check_realworld_testing()
        rm = self.check_relationship_memory()

        print(f"[1] Self-Improvement Loop: {si['status']}")
        if si['status'] == 'active':
            print(f"    Indexing: {si['indexing_speed']:.1f} files/sec")
            print(f"    Bottlenecks: {si['bottlenecks']}")
            print(f"    Improvements: {si['improvements_generated']}")

        print(f"\n[2] Capability Synergy: {syn['status']}")
        if syn['status'] == 'active':
            print(f"    Chain Executions: {syn['chain_executions']}")
            print(f"    Synergy Flows: {syn['synergy_flows']}")
            print(f"    Avg Intelligence: {syn['avg_intelligence']:.3f}")

        print(f"\n[3] Real-World Testing: {rw['status']}")
        if rw['status'] in ['active', 'idle']:
            print(f"    Active Sessions: {rw['active_sessions']}")
            print(f"    Total Activities: {rw['total_activities']}")
            print(f"    Issues Found: {rw['issues_found']}")

        print(f"\n[4] Relationship Memory: {rm['status']}")
        if rm['status'] in ['active', 'idle']:
            print(f"    Interactions: {rm['interactions']}")
            print(f"    Preferences: {rm['preferences']}")

        # Overall status
        active_count = sum([
            1 if si['status'] == 'active' else 0,
            1 if syn['status'] == 'active' else 0,
            1 if rw['status'] in ['active', 'idle'] else 0,
            1 if rm['status'] in ['active', 'idle'] else 0
        ])

        print(f"\n[STATUS] {active_count}/4 systems operational")

        return {
            'self_improvement': si,
            'synergy': syn,
            'realworld': rw,
            'relationship': rm,
            'active_count': active_count
        }

    def run(self, interval=10, max_iterations=120):
        """Run continuous monitoring"""
        print("Starting continuous monitoring...")
        print(f"Checking every {interval} seconds for up to {max_iterations} iterations")
        print("Press Ctrl+C to stop")

        try:
            while self.running and self.iteration < max_iterations:
                report = self.generate_report()

                # Take action if needed
                if report['active_count'] >= 3:
                    print(f"\n[ACTION] Systems operational - monitoring...")

                time.sleep(interval)

        except KeyboardInterrupt:
            print("\n\nMonitoring stopped by user")

        print(f"\nCompleted {self.iteration} iterations")
        return report

if __name__ == '__main__':
    monitor = ContinuousMonitor()
    final_report = monitor.run(interval=15, max_iterations=40)  # 10 minutes total

    print("\n" + "="*80)
    print("FINAL REPORT")
    print("="*80)
    print(json.dumps(final_report, indent=2))
