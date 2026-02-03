#!/usr/bin/env python3
"""
Business Agent Monitor - Track all agent activity
Logs decisions, opportunities, and system health
"""

import json
import sys
from pathlib import Path
from datetime import datetime

WORKSPACE = Path(r"C:\Users\User\.openclaw\workspace")
sys.path.append(str(WORKSPACE))

from task_status_notifier import TaskStatusNotifier

class AgentMonitor:
    """Monitor and log all business agent activity"""

    def __init__(self):
        self.notifier = TaskStatusNotifier()
        self.log_dir = WORKSPACE / "business_agent" / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.activity_log = self.log_dir / "activity.log"
        self.opportunities_log = self.log_dir / "opportunities.json"
        self.decisions_log = self.log_dir / "decisions.json"
        self.health_log = self.log_dir / "health.log"

    def log_activity(self, activity_type: str, message: str, level: str = "INFO"):
        """Log general activity"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] [{activity_type}] {message}\n"

        with open(self.activity_log, 'a', encoding='utf-8') as f:
            f.write(log_entry)

        print(log_entry.strip())

    def log_opportunity(self, opportunity: dict):
        """Log discovered opportunity"""
        opportunities = self._load_json_log(self.opportunities_log)

        opportunities.append({
            'timestamp': datetime.now().isoformat(),
            **opportunity
        })

        self._save_json_log(self.opportunities_log, opportunities)

        # Notify if high-value opportunity
        if opportunity.get('combined_score', 0) >= 0.7:
            self.notifier.send_message(
                f"💎 <b>High-Value Opportunity Found</b>\n\n"
                f"<b>Name:</b> {opportunity.get('name', 'Unknown')}\n"
                f"<b>Score:</b> {opportunity.get('combined_score', 0):.2f}\n"
                f"<b>Type:</b> {opportunity.get('source_type', 'Unknown')}\n\n"
                f"<b>Recommendation:</b> {opportunity.get('recommendation', 'See details')}"
            )

        self.log_activity("OPPORTUNITY", f"Found: {opportunity.get('name', 'Unknown')}")

    def log_decision(self, decision: dict):
        """Log business decision"""
        decisions = self._load_json_log(self.decisions_log)

        decisions.append({
            'timestamp': datetime.now().isoformat(),
            **decision
        })

        self._save_json_log(self.decisions_log, decisions)

        self.log_activity("DECISION", f"Evaluated: {decision.get('decision', 'Unknown')}")

    def log_health(self, component: str, status: str, details: str = ""):
        """Log system health"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        health_entry = f"[{timestamp}] [{component}] {status}"
        if details:
            health_entry += f" - {details}"
        health_entry += "\n"

        with open(self.health_log, 'a', encoding='utf-8') as f:
            f.write(health_entry)

        if status != "OK":
            self.notifier.send_message(
                f"⚠️ <b>System Health Alert</b>\n\n"
                f"<b>Component:</b> {component}\n"
                f"<b>Status:</b> {status}\n"
                f"<b>Details:</b> {details}"
            )

    def send_daily_summary(self):
        """Send daily summary via Telegram"""
        # Load today's data
        opportunities = self._load_json_log(self.opportunities_log)
        decisions = self._load_json_log(self.decisions_log)

        today = datetime.now().date().isoformat()

        today_opps = [o for o in opportunities if o.get('timestamp', '').startswith(today)]
        today_decisions = [d for d in decisions if d.get('timestamp', '').startswith(today)]

        high_value_opps = [o for o in today_opps if o.get('combined_score', 0) >= 0.7]

        message = f"📊 <b>Daily Business Agent Summary</b>\n\n"
        message += f"<b>Date:</b> {today}\n\n"
        message += f"<b>Opportunities Found:</b> {len(today_opps)}\n"
        message += f"<b>High-Value Opportunities:</b> {len(high_value_opps)}\n"
        message += f"<b>Decisions Evaluated:</b> {len(today_decisions)}\n\n"

        if high_value_opps:
            message += "<b>Top Opportunities:</b>\n"
            for opp in high_value_opps[:3]:
                message += f"• {opp.get('name', 'Unknown')} ({opp.get('combined_score', 0):.2f})\n"

        self.notifier.send_message(message)

        self.log_activity("SUMMARY", f"Daily summary sent: {len(today_opps)} opportunities, {len(today_decisions)} decisions")

    def _load_json_log(self, file_path: Path) -> list:
        """Load JSON log file"""
        if not file_path.exists():
            return []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []

    def _save_json_log(self, file_path: Path, data: list):
        """Save JSON log file"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_stats(self) -> dict:
        """Get current statistics"""
        opportunities = self._load_json_log(self.opportunities_log)
        decisions = self._load_json_log(self.decisions_log)

        return {
            'total_opportunities': len(opportunities),
            'total_decisions': len(decisions),
            'high_value_opportunities': len([o for o in opportunities if o.get('combined_score', 0) >= 0.7]),
            'average_opportunity_score': sum(o.get('combined_score', 0) for o in opportunities) / len(opportunities) if opportunities else 0,
            'average_decision_score': sum(d.get('love_score', 0) for d in decisions) / len(decisions) if decisions else 0
        }


if __name__ == "__main__":
    monitor = AgentMonitor()
    stats = monitor.get_stats()

    print("=" * 70)
    print("Business Agent Monitor - Statistics")
    print("=" * 70)
    for key, value in stats.items():
        print(f"{key}: {value}")
    print("=" * 70)
