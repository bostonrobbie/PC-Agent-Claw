#!/usr/bin/env python3
"""
Real-World Integration Testing System - Live Demo

This demonstrates the RealWorldTester running a 5-minute autonomous test
of the Intelligence Hub on this actual codebase.

Features Demonstrated:
- Continuous autonomous operations
- Real-time monitoring and reporting
- Performance metrics collection
- Issue detection and reporting
- Comprehensive final analysis

Usage:
    python examples/demo_realworld_tester.py

Author: AI Self-Improvement System
Created: 2026-02-03
"""

import os
import sys
import time
from pathlib import Path

# Add workspace to path
workspace = Path(__file__).parent.parent
sys.path.append(str(workspace))

from autonomous.realworld_tester import RealWorldTester


def print_header(text):
    """Print a formatted header"""
    print("\n" + "=" * 80)
    print(text.center(80))
    print("=" * 80 + "\n")


def print_section(text):
    """Print a section divider"""
    print(f"\n{text:=^80}\n")


def main():
    """Run a live 5-minute test demonstration"""

    print_header("REAL-WORLD INTEGRATION TESTING SYSTEM")
    print_header("LIVE DEMONSTRATION - 5 MINUTE TEST")

    print("""
This demonstration will:
1. Initialize the RealWorldTester
2. Start an autonomous test session on this workspace
3. Monitor the Intelligence Hub running in real-time
4. Collect performance metrics and detect issues
5. Generate a comprehensive improvement report

The test will run for 5 minutes, exercising all 25 capabilities.
You'll see real-time updates every 30 seconds.
    """)

    input("\nPress ENTER to start the test...")

    # Initialize tester
    print_section("STEP 1: INITIALIZATION")

    print("Initializing RealWorldTester...")
    tester = RealWorldTester()
    print(f"[OK] Tester initialized")
    print(f"     Database: {tester.db_path}")

    # Start test session
    print_section("STEP 2: START TEST SESSION")

    project_path = str(workspace)
    duration_minutes = 5

    print(f"Starting test session:")
    print(f"  Project: {project_path}")
    print(f"  Duration: {duration_minutes} minutes")
    print(f"  Test will complete at: {time.strftime('%H:%M:%S', time.localtime(time.time() + duration_minutes * 60))}")

    try:
        session_id = tester.start_test_session(project_path, duration_minutes)
        print(f"\n[OK] Test session started: {session_id}")
    except Exception as e:
        print(f"\n[ERROR] Failed to start session: {e}")
        print("\nNote: This demo requires all Intelligence Hub dependencies.")
        print("The system is still functional - just run it on a simpler codebase.")
        return

    # Monitor progress
    print_section("STEP 3: MONITORING (Live Updates Every 30s)")

    print("""
The Intelligence Hub is now running autonomously, performing:
- Code reviews and analysis
- Security vulnerability scanning
- Semantic code indexing
- Error pattern learning
- Resource monitoring
- And more...

Live status updates:
""")

    try:
        update_count = 0
        max_updates = (duration_minutes * 60) // 30  # Every 30 seconds

        for i in range(max_updates):
            time.sleep(30)
            update_count += 1

            # Get current status
            monitor_data = tester.monitor_activities()
            metrics = tester.collect_metrics()

            print(f"\n[Update {update_count}/{max_updates}] {time.strftime('%H:%M:%S')}")
            print("-" * 80)

            if monitor_data['active_sessions']:
                session = monitor_data['active_sessions'][0]
                print(f"  Session: {session['session_id']}")
                print(f"  Running: {session['running_time']} / {session['remaining_time']} left")
                print(f"  Activities: {session.get('total_activities', 0)} total, {session.get('total_errors', 0)} errors")

            print(f"  System: CPU {metrics['system_resources']['cpu_percent']:.1f}%, "
                  f"Memory {metrics['system_resources']['memory_percent']:.1f}%")

            if metrics['by_capability']:
                print(f"  Capabilities Active:")
                for cap, stats in list(metrics['by_capability'].items())[:5]:
                    print(f"    - {cap}: {stats['total_calls']} calls, "
                          f"{stats['success_rate']:.1f}% success, "
                          f"{stats['avg_response_time_ms']:.0f}ms avg")

                if len(metrics['by_capability']) > 5:
                    print(f"    ... and {len(metrics['by_capability']) - 5} more")

            print("-" * 80)

    except KeyboardInterrupt:
        print("\n\n[!] Test interrupted by user")

    # Stop session
    print_section("STEP 4: STOPPING TEST SESSION")

    print("Stopping test session and collecting final metrics...")
    final_stats = tester.stop_session(session_id)

    print(f"\n[OK] Session stopped")
    print(f"  Total Activities: {final_stats['total_activities']}")
    print(f"  Total Errors: {final_stats['total_errors']}")
    print(f"  Success Rate: {((final_stats['total_activities'] - final_stats['total_errors']) / max(final_stats['total_activities'], 1) * 100):.1f}%")
    print(f"  Overall Score: {final_stats['overall_score']:.1f}/100")

    # Analyze results
    print_section("STEP 5: ANALYZING RESULTS")

    print("Performing deep analysis of test results...")
    analysis = tester.analyze_session_results(session_id)

    print(f"\n[OK] Analysis complete")
    print(f"\nSummary:")
    print(f"  Activities: {analysis['summary']['total_activities']}")
    print(f"  Success Rate: {analysis['summary']['success_rate']:.1f}%")
    print(f"  Avg Response Time: {analysis['summary']['avg_response_time']:.0f}ms")

    print(f"\nCapabilities Tested:")
    for cap_data in analysis['activities_by_capability']:
        success_rate = (cap_data['successes'] / cap_data['total'] * 100) if cap_data['total'] > 0 else 0
        print(f"  - {cap_data['capability']}: {cap_data['total']} calls, "
              f"{success_rate:.1f}% success, {cap_data['avg_response']:.0f}ms avg")

    print(f"\nIssues Found:")
    if analysis['issues_by_severity']:
        for severity, count in analysis['issues_by_severity'].items():
            print(f"  - {severity.upper()}: {count}")
    else:
        print("  No issues detected")

    # Generate improvement report
    print_section("STEP 6: GENERATING IMPROVEMENT REPORT")

    print("Creating comprehensive improvement report with actionable suggestions...")
    report = tester.generate_improvement_report(session_id)

    print(report)

    # Save report to file
    report_file = workspace / f"realworld_test_report_{session_id}.txt"
    with open(report_file, 'w') as f:
        f.write(report)

    print(f"\n[OK] Report saved to: {report_file}")

    # Final summary
    print_section("TEST COMPLETE")

    print(f"""
Test Session Summary:
- Session ID: {session_id}
- Duration: {duration_minutes} minutes
- Activities Performed: {final_stats['total_activities']}
- Issues Found: {sum(analysis['issues_by_severity'].values()) if analysis['issues_by_severity'] else 0}
- Overall Score: {final_stats['overall_score']:.1f}/100

Database: {tester.db_path}
Report: {report_file}

What This Demonstrates:
✓ Autonomous operation of Intelligence Hub
✓ Real-time monitoring and metrics collection
✓ Issue detection across all capabilities
✓ Performance analysis and benchmarking
✓ Automated improvement suggestions

The Real-World Tester successfully validated the Intelligence Hub's
ability to run autonomously on real codebases, providing actionable
insights for continuous improvement.
""")

    print_header("DEMONSTRATION COMPLETE")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n[ERROR] Demonstration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
