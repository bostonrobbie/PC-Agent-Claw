#!/usr/bin/env python3
"""
Weekly Summary Report - Automated report generation
"""

from pathlib import Path
from datetime import datetime, timedelta
import json

WORKSPACE = Path(r"C:\Users\User\.openclaw\workspace")

def generate_weekly_summary():
    """Generate weekly summary of activities and progress"""

    print("=" * 60)
    print("Weekly Summary Report")
    print("=" * 60)
    print()

    now = datetime.now()
    week_ago = now - timedelta(days=7)

    summary = {
        'week_ending': now.strftime('%Y-%m-%d'),
        'period': f"{week_ago.strftime('%Y-%m-%d')} to {now.strftime('%Y-%m-%d')}",
        'sections': {}
    }

    # Check metrics
    metrics_file = WORKSPACE / "iterations" / "metrics.json"
    if metrics_file.exists():
        with open(metrics_file, 'r') as f:
            metrics = json.load(f)

        summary['sections']['performance'] = {
            'sessions_completed': metrics.get('sessions_completed', 0),
            'tasks_completed': metrics.get('tasks_completed', 0),
            'success_rate': f"{metrics.get('success_rate', 0):.1f}%",
            'capabilities_added': len(metrics.get('capabilities_added', []))
        }

    # Check git commits
    try:
        import subprocess
        result = subprocess.run(
            ['git', 'log', '--since=7.days', '--oneline'],
            cwd=str(WORKSPACE),
            capture_output=True,
            text=True
        )
        commit_count = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
        summary['sections']['git'] = {
            'commits_this_week': commit_count
        }
    except:
        pass

    # Check backups
    backup_dir = WORKSPACE / "backups" / "daily"
    if backup_dir.exists():
        recent_backups = [d for d in backup_dir.iterdir() if d.is_dir()]
        recent_backups = [d for d in recent_backups if datetime.strptime(d.name, '%Y-%m-%d') >= week_ago]
        summary['sections']['backups'] = {
            'backups_created': len(recent_backups)
        }

    # Check memory/learnings
    learnings_dir = WORKSPACE / "memory" / "learnings"
    if learnings_dir.exists():
        mistakes_file = learnings_dir / "mistakes.md"
        successes_file = learnings_dir / "successes.md"

        mistakes_count = 0
        successes_count = 0

        if mistakes_file.exists():
            with open(mistakes_file, 'r', encoding='utf-8') as f:
                mistakes_count = f.read().count('## Mistake')

        if successes_file.exists():
            with open(successes_file, 'r', encoding='utf-8') as f:
                successes_count = f.read().count('## Success')

        summary['sections']['learnings'] = {
            'mistakes_documented': mistakes_count,
            'successes_documented': successes_count
        }

    # Generate markdown report
    report_file = WORKSPACE / f"weekly_summary_{now.strftime('%Y-%m-%d')}.md"

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"# Weekly Summary Report\n\n")
        f.write(f"**Week Ending:** {summary['week_ending']}\n")
        f.write(f"**Period:** {summary['period']}\n\n")
        f.write("---\n\n")

        if 'performance' in summary['sections']:
            perf = summary['sections']['performance']
            f.write("## Performance\n\n")
            f.write(f"- Sessions Completed: {perf['sessions_completed']}\n")
            f.write(f"- Tasks Completed: {perf['tasks_completed']}\n")
            f.write(f"- Success Rate: {perf['success_rate']}\n")
            f.write(f"- New Capabilities: {perf['capabilities_added']}\n\n")

        if 'git' in summary['sections']:
            f.write("## Version Control\n\n")
            f.write(f"- Commits This Week: {summary['sections']['git']['commits_this_week']}\n\n")

        if 'backups' in summary['sections']:
            f.write("## Backups\n\n")
            f.write(f"- Backups Created: {summary['sections']['backups']['backups_created']}\n\n")

        if 'learnings' in summary['sections']:
            learn = summary['sections']['learnings']
            f.write("## Learning & Improvement\n\n")
            f.write(f"- Mistakes Documented: {learn['mistakes_documented']}\n")
            f.write(f"- Successes Documented: {learn['successes_documented']}\n\n")

        f.write("---\n\n")
        f.write("*Generated automatically by Claude AI Agent*\n")

    print(f"Report generated: {report_file}")
    print()
    print("Summary:")
    print(json.dumps(summary, indent=2))

    return report_file

if __name__ == "__main__":
    generate_weekly_summary()
