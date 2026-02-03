#!/usr/bin/env python3
"""
Real-World Integration Testing System - Flexible Test Runner

Run customizable real-world tests on any project with full control over:
- Test duration
- Project path
- Monitoring frequency
- Report generation

Usage:
    # Quick 2-minute test on current workspace
    python examples/run_realworld_test.py

    # 10-minute test on specific project
    python examples/run_realworld_test.py --project /path/to/project --duration 10

    # Extended 60-minute stress test
    python examples/run_realworld_test.py --duration 60 --monitor-interval 60

    # Custom database location
    python examples/run_realworld_test.py --db /custom/path/testing.db

Author: AI Self-Improvement System
Created: 2026-02-03
"""

import os
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime

# Add workspace to path
workspace = Path(__file__).parent.parent
sys.path.append(str(workspace))

from autonomous.realworld_tester import RealWorldTester


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Run real-world integration tests on the Intelligence Hub',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Quick 2-minute test
  %(prog)s

  # 10-minute test on specific project
  %(prog)s --project /path/to/project --duration 10

  # Extended stress test
  %(prog)s --duration 60 --monitor-interval 60

  # Custom database
  %(prog)s --db /custom/testing.db
        """
    )

    parser.add_argument(
        '--project',
        type=str,
        default=str(workspace),
        help='Path to project to test (default: current workspace)'
    )

    parser.add_argument(
        '--duration',
        type=int,
        default=2,
        help='Test duration in minutes (default: 2)'
    )

    parser.add_argument(
        '--db',
        type=str,
        default=None,
        help='Path to database file (default: workspace/realworld_testing.db)'
    )

    parser.add_argument(
        '--monitor-interval',
        type=int,
        default=30,
        help='Monitoring update interval in seconds (default: 30)'
    )

    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Minimal output (only final report)'
    )

    parser.add_argument(
        '--no-report',
        action='store_true',
        help='Skip generating improvement report'
    )

    parser.add_argument(
        '--save-report',
        type=str,
        default=None,
        help='Save report to specific file (default: auto-generated name)'
    )

    return parser.parse_args()


def print_header(text, quiet=False):
    """Print formatted header"""
    if not quiet:
        print("\n" + "=" * 80)
        print(text.center(80))
        print("=" * 80 + "\n")


def print_section(text, quiet=False):
    """Print section divider"""
    if not quiet:
        print(f"\n{text:=^80}\n")


def run_test(args):
    """Run the real-world test with given arguments"""

    if not args.quiet:
        print_header("REAL-WORLD INTEGRATION TESTING SYSTEM")
        print(f"""
Test Configuration:
  Project: {args.project}
  Duration: {args.duration} minutes
  Database: {args.db or 'default'}
  Monitor Interval: {args.monitor_interval} seconds
  End Time: {time.strftime('%H:%M:%S', time.localtime(time.time() + args.duration * 60))}
        """)

    # Initialize tester
    if not args.quiet:
        print_section("INITIALIZING TESTER")
        print("Creating RealWorldTester instance...")

    tester = RealWorldTester(db_path=args.db)

    if not args.quiet:
        print(f"[OK] Tester initialized")
        print(f"     Database: {tester.db_path}")

    # Start test session
    if not args.quiet:
        print_section("STARTING TEST SESSION")
        print(f"Starting autonomous test on: {args.project}")

    try:
        session_id = tester.start_test_session(args.project, args.duration)

        if not args.quiet:
            print(f"[OK] Session started: {session_id}")
        elif args.quiet:
            print(f"Test session started: {session_id}")

    except Exception as e:
        print(f"\n[ERROR] Failed to start test session: {e}")
        print("\nPossible issues:")
        print("  - Project path does not exist")
        print("  - Intelligence Hub dependencies missing")
        print("  - Database file cannot be created")
        return None, None

    # Monitor progress
    if not args.quiet:
        print_section("MONITORING TEST EXECUTION")
        print("The Intelligence Hub is running autonomously...")
        print("Live updates will appear below.\n")

    try:
        updates_sent = 0
        max_updates = (args.duration * 60) // args.monitor_interval

        while session_id in tester.active_sessions:
            time.sleep(args.monitor_interval)
            updates_sent += 1

            # Get status
            monitor_data = tester.monitor_activities()
            metrics = tester.collect_metrics()

            if not args.quiet:
                print(f"\n[Update {updates_sent}/{max_updates}] {time.strftime('%H:%M:%S')}")
                print("-" * 80)

                if monitor_data['active_sessions']:
                    session = monitor_data['active_sessions'][0]
                    print(f"  Session: {session['session_id']}")
                    print(f"  Running: {session['running_time']} / Remaining: {session['remaining_time']}")
                    print(f"  Activities: {session.get('total_activities', 0)}, Errors: {session.get('total_errors', 0)}")

                print(f"  System: CPU {metrics['system_resources']['cpu_percent']:.1f}%, "
                      f"Memory {metrics['system_resources']['memory_percent']:.1f}%")

                if metrics['by_capability']:
                    print(f"  Active Capabilities ({len(metrics['by_capability'])}):")
                    for cap, stats in list(metrics['by_capability'].items())[:3]:
                        print(f"    • {cap}: {stats['total_calls']} calls, "
                              f"{stats['success_rate']:.1f}% success")

                    if len(metrics['by_capability']) > 3:
                        print(f"    ... and {len(metrics['by_capability']) - 3} more")

                print("-" * 80)

            # Check if session ended naturally
            if updates_sent >= max_updates:
                break

    except KeyboardInterrupt:
        print("\n\n[!] Test interrupted by user")
        if not args.quiet:
            print("Stopping session gracefully...")

    # Stop session if still running
    if session_id in tester.active_sessions:
        if not args.quiet:
            print_section("STOPPING TEST SESSION")
            print("Collecting final metrics and stopping session...")

        final_stats = tester.stop_session(session_id)
    else:
        # Session already stopped (timeout)
        if not args.quiet:
            print_section("TEST SESSION COMPLETED")
            print("Session ended naturally after duration.")

        # Get final stats from database
        analysis = tester.analyze_session_results(session_id)
        final_stats = analysis['session']

    if not args.quiet:
        print(f"\n[OK] Test session complete")
        print(f"  Activities: {final_stats['total_activities']}")
        print(f"  Errors: {final_stats['total_errors']}")
        print(f"  Score: {final_stats['overall_score']:.1f}/100")

    return tester, session_id


def analyze_and_report(tester, session_id, args):
    """Analyze results and generate reports"""

    if not args.quiet:
        print_section("ANALYZING RESULTS")
        print("Performing comprehensive analysis...")

    analysis = tester.analyze_session_results(session_id)

    if not args.quiet:
        print(f"\n[OK] Analysis complete")
        print(f"\nPerformance Summary:")
        print(f"  Total Activities: {analysis['summary']['total_activities']}")
        print(f"  Success Rate: {analysis['summary']['success_rate']:.1f}%")
        print(f"  Avg Response Time: {analysis['summary']['avg_response_time']:.0f}ms")
        print(f"  Avg CPU Usage: {analysis['summary']['avg_cpu_usage']:.1f}%")
        print(f"  Avg Memory Usage: {analysis['summary']['avg_memory_usage']:.1f}MB")

        print(f"\nCapabilities Tested ({len(analysis['activities_by_capability'])}):")
        for cap_data in analysis['activities_by_capability'][:5]:
            success_rate = (cap_data['successes'] / cap_data['total'] * 100) if cap_data['total'] > 0 else 0
            print(f"  • {cap_data['capability']}: {cap_data['total']} calls, "
                  f"{success_rate:.1f}% success, {cap_data['avg_response']:.0f}ms")

        if len(analysis['activities_by_capability']) > 5:
            print(f"  ... and {len(analysis['activities_by_capability']) - 5} more")

        print(f"\nIssues Detected:")
        if analysis['issues_by_severity']:
            for severity, count in sorted(analysis['issues_by_severity'].items()):
                print(f"  • {severity.upper()}: {count}")
        else:
            print("  No issues detected - excellent!")

        print(f"\nWhat Worked Well ({len(analysis['worked_well'])}):")
        for item in analysis['worked_well'][:3]:
            print(f"  ✓ {item['capability']}: {item['reason']}")

        print(f"\nWhat Worked Poorly ({len(analysis['worked_poorly'])}):")
        for item in analysis['worked_poorly'][:3]:
            print(f"  ✗ {item['capability']}: {item['reason']}")

    # Generate improvement report
    if not args.no_report:
        if not args.quiet:
            print_section("GENERATING IMPROVEMENT REPORT")
            print("Creating actionable improvement suggestions...")

        report = tester.generate_improvement_report(session_id)

        # Save report
        if args.save_report:
            report_file = args.save_report
        else:
            report_file = workspace / f"realworld_test_report_{session_id}.txt"

        with open(report_file, 'w') as f:
            f.write(report)

        if args.quiet:
            print(f"\nReport saved: {report_file}")
        else:
            print(f"[OK] Report generated and saved\n")
            print(report)
            print(f"\nReport saved to: {report_file}")

    return analysis


def main():
    """Main entry point"""
    args = parse_args()

    # Validate project path
    if not os.path.exists(args.project):
        print(f"[ERROR] Project path does not exist: {args.project}")
        return 1

    # Run test
    tester, session_id = run_test(args)

    if not tester or not session_id:
        print("\n[ERROR] Test failed to run")
        return 1

    # Analyze and report
    try:
        analysis = analyze_and_report(tester, session_id, args)

        if not args.quiet:
            print_header("TEST COMPLETE")
            print(f"""
Session ID: {session_id}
Database: {tester.db_path}
Overall Score: {analysis['session']['overall_score']:.1f}/100

The Real-World Integration Testing System successfully:
✓ Ran autonomously for {args.duration} minutes
✓ Exercised {len(analysis['activities_by_capability'])} capabilities
✓ Performed {analysis['summary']['total_activities']} activities
✓ Detected {sum(analysis['issues_by_severity'].values()) if analysis['issues_by_severity'] else 0} issues
✓ Generated actionable improvement suggestions

Use this data to continuously improve the Intelligence Hub!
            """)

        # Exit with appropriate code based on score
        score = analysis['session']['overall_score']
        if score >= 90:
            return 0  # Excellent
        elif score >= 70:
            return 0  # Good enough
        else:
            return 1  # Needs improvement

    except Exception as e:
        print(f"\n[ERROR] Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n[!] Interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n[FATAL ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
