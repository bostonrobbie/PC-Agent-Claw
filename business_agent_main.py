#!/usr/bin/env python3
"""
Business Agent Main Controller
Orchestrates all business intelligence systems with Brian Roemmele principles

Philosophy:
- Love Equation: Optimize for GIVING value
- Deep Truth: Seek diverse, empirical truths
- Empirical Distrust: Favor old, forgotten knowledge
"""

import sys
import time
import schedule
from pathlib import Path
from datetime import datetime

WORKSPACE = Path(r"C:\Users\User\.openclaw\workspace")
sys.path.append(str(WORKSPACE))
sys.path.append(str(WORKSPACE / "business_agent"))

from business_agent.core.love_equation_framework import LoveEquationFramework
from business_agent.core.deep_truth_analyzer import DeepTruthAnalyzer
from business_agent.scanners.opportunity_scanner import OpportunityScanner
from business_agent.monitors.agent_monitor import AgentMonitor
from task_status_notifier import TaskStatusNotifier

class BusinessAgent:
    """
    Main Business Agent Controller

    Autonomous business intelligence powered by:
    - Love Equation (genuine value creation)
    - Deep Truth Mode (empirical evidence)
    - Strategic opportunity sources (forgotten knowledge)
    """

    def __init__(self):
        print("=" * 70)
        print("Initializing Business Agent with Brian Roemmele Principles")
        print("=" * 70)

        self.love_framework = LoveEquationFramework()
        self.truth_analyzer = DeepTruthAnalyzer()
        self.opportunity_scanner = OpportunityScanner()
        self.monitor = AgentMonitor()
        self.notifier = TaskStatusNotifier()

        self.running = True

        self.monitor.log_health("BusinessAgent", "INITIALIZING")
        print("[OK] Core modules loaded")
        print("[OK] Love Equation framework active")
        print("[OK] Deep Truth analyzer ready")
        print("[OK] Opportunity scanner configured")
        print("[OK] Monitoring system online")
        self.monitor.log_health("BusinessAgent", "OK", "All systems initialized")

    def start(self):
        """Start the business agent with daily cycles"""
        print("\n" + "=" * 70)
        print("Business Agent Starting - 24/7 Operation")
        print("=" * 70)

        self.monitor.log_activity("STARTUP", "Business agent starting")

        # Send startup notification
        self.notifier.send_message(
            "🚀 <b>Business Agent Online</b>\n\n"
            "<b>Philosophy:</b> Love Equation + Deep Truth\n"
            "<b>Sources:</b> Historical patents, forgotten research, contrarian ideas\n\n"
            "<b>Daily Cycles:</b>\n"
            "• 7:00 AM - Morning briefing\n"
            "• 9:00 AM - Knowledge archaeology\n"
            "• 2:00 PM - Contrarian scan\n"
            "• 7:00 PM - Strategic deep dive\n"
            "• 9:00 PM - Evening summary\n\n"
            "<b>Status:</b> All systems operational"
        )

        # Schedule daily cycles
        self._setup_daily_cycles()

        # Run initial scan
        print("\nRunning initial opportunity scan...")
        self.run_opportunity_scan("trading and business strategies")

        # Main loop
        try:
            print("\n[OK] Business Agent running - Press Ctrl+C to stop\n")

            while self.running:
                schedule.run_pending()
                time.sleep(60)  # Check every minute

        except KeyboardInterrupt:
            print("\n\nShutting down gracefully...")
            self.stop()

    def _setup_daily_cycles(self):
        """Setup automated daily cycles"""
        # 7:00 AM - Morning briefing
        schedule.every().day.at("07:00").do(self.morning_briefing)

        # 9:00 AM - Knowledge archaeology (historical scan)
        schedule.every().day.at("09:00").do(
            self.run_opportunity_scan,
            focus="historical knowledge and forgotten research"
        )

        # 2:00 PM - Contrarian scan
        schedule.every().day.at("14:00").do(
            self.run_opportunity_scan,
            focus="contrarian but evidence-backed ideas"
        )

        # 7:00 PM - Strategic deep dive
        schedule.every().day.at("19:00").do(
            self.run_opportunity_scan,
            focus="cross-industry patterns and failed businesses"
        )

        # 9:00 PM - Evening summary
        schedule.every().day.at("21:00").do(self.evening_summary)

        print("[OK] Daily cycles scheduled")

    def morning_briefing(self):
        """Send morning briefing"""
        self.monitor.log_activity("BRIEFING", "Morning briefing started")

        stats = self.monitor.get_stats()

        message = f"🌅 <b>Morning Briefing</b>\n\n"
        message += f"<b>Business Agent Status:</b> Operational\n\n"
        message += f"<b>All-Time Stats:</b>\n"
        message += f"• Opportunities found: {stats['total_opportunities']}\n"
        message += f"• High-value opportunities: {stats['high_value_opportunities']}\n"
        message += f"• Average opportunity score: {stats['average_opportunity_score']:.2f}\n\n"
        message += f"<b>Today's Focus:</b>\n"
        message += f"• 9 AM: Historical knowledge mining\n"
        message += f"• 2 PM: Contrarian opportunity scan\n"
        message += f"• 7 PM: Cross-industry patterns\n"

        self.notifier.send_message(message)

    def evening_summary(self):
        """Send evening summary"""
        self.monitor.log_activity("SUMMARY", "Evening summary started")
        self.monitor.send_daily_summary()

    def run_opportunity_scan(self, focus: str = "general"):
        """Run opportunity scan with specified focus"""
        self.monitor.log_activity("SCAN", f"Starting scan: {focus}")

        try:
            opportunities = self.opportunity_scanner.scan_opportunities(focus)

            # Log all opportunities
            for opp in opportunities:
                self.monitor.log_opportunity(opp)

            # Send notification for high-value opportunities
            high_value = [o for o in opportunities if o.get('combined_score', 0) >= 0.7]

            if high_value:
                message = f"🔍 <b>Opportunity Scan Complete</b>\n\n"
                message += f"<b>Focus:</b> {focus}\n"
                message += f"<b>Found:</b> {len(opportunities)} opportunities\n"
                message += f"<b>High-value:</b> {len(high_value)}\n\n"

                if high_value:
                    message += "<b>Top Opportunity:</b>\n"
                    top = high_value[0]
                    message += f"{top.get('name', 'Unknown')}\n"
                    message += f"Score: {top.get('combined_score', 0):.2f}\n"
                    message += f"{top.get('recommendation', '')}"

                self.notifier.send_message(message)

            self.monitor.log_activity("SCAN", f"Complete: {len(opportunities)} found")

        except Exception as e:
            self.monitor.log_health("OpportunityScanner", "ERROR", str(e))
            self.monitor.log_activity("SCAN", f"Error: {e}", "ERROR")

    def evaluate_decision(self, decision: str, context: dict):
        """Evaluate a business decision using Love Equation"""
        self.monitor.log_activity("DECISION", f"Evaluating: {decision}")

        evaluation = self.love_framework.evaluate_decision(decision, context)

        self.monitor.log_decision(evaluation)

        # Notify if decision doesn't pass Love Equation test
        if not evaluation['passes']:
            self.notifier.send_message(
                f"⚠️ <b>Decision Failed Love Equation Test</b>\n\n"
                f"<b>Decision:</b> {decision}\n"
                f"<b>Love Score:</b> {evaluation['love_score']:.2f}\n"
                f"<b>Threshold:</b> 0.70\n\n"
                f"<b>This decision does not optimize for GIVING value</b>\n\n"
                f"Top concern: {evaluation['reasoning'][0] if evaluation['reasoning'] else 'See details'}"
            )

        return evaluation

    def stop(self):
        """Stop the business agent"""
        self.running = False
        self.monitor.log_activity("SHUTDOWN", "Business agent stopping")

        self.notifier.send_message(
            "⏸️ <b>Business Agent Stopped</b>\n\n"
            "<b>Final Stats:</b>\n"
            f"• Opportunities found: {self.monitor.get_stats()['total_opportunities']}\n"
            f"• Decisions evaluated: {self.monitor.get_stats()['total_decisions']}\n\n"
            "<b>All data logged and preserved</b>"
        )

        print("\n" + "=" * 70)
        print("Business Agent Stopped")
        print("=" * 70)


def main():
    """Main entry point"""
    agent = BusinessAgent()
    agent.start()


if __name__ == "__main__":
    main()
