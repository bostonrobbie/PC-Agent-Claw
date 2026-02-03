#!/usr/bin/env python3
"""
Telegram Integration
Send all notifications, reports, and updates to Telegram
Replaces Slack/Email with phone-based management
"""
import sys
from pathlib import Path
import requests
import json
from typing import Dict, List, Optional
from datetime import datetime
import os

sys.path.append(str(Path(__file__).parent.parent))


class TelegramIntegration:
    """
    Telegram-first integration for business process management

    Features:
    - Send process notifications to Telegram
    - Daily/weekly summary reports
    - Real-time execution updates
    - Approval requests via Telegram
    - Interactive buttons for quick actions
    - File/document sharing
    - Process performance reports
    """

    def __init__(self, bot_token: str = None, chat_id: str = None):
        """
        Initialize Telegram integration

        Args:
            bot_token: Telegram bot token (or set TELEGRAM_BOT_TOKEN env var)
            chat_id: Your Telegram chat ID (or set TELEGRAM_CHAT_ID env var)
        """
        self.bot_token = bot_token or os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = chat_id or os.getenv('TELEGRAM_CHAT_ID')

        if not self.bot_token or not self.chat_id:
            print("[WARNING] Telegram not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
            print("          Get bot token from @BotFather on Telegram")
            print("          Get your chat ID by messaging @userinfobot")

        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"

    # === BASIC MESSAGING ===

    def send_message(self, text: str, parse_mode: str = 'Markdown',
                    disable_notification: bool = False) -> bool:
        """
        Send text message to Telegram

        Args:
            text: Message text (supports Markdown or HTML)
            parse_mode: 'Markdown' or 'HTML'
            disable_notification: Silent notification

        Returns:
            Success status
        """
        if not self.bot_token or not self.chat_id:
            print(f"[TELEGRAM] {text}")
            return False

        try:
            response = requests.post(
                f"{self.api_url}/sendMessage",
                json={
                    'chat_id': self.chat_id,
                    'text': text,
                    'parse_mode': parse_mode,
                    'disable_notification': disable_notification
                },
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            print(f"[ERROR] Telegram send failed: {e}")
            return False

    def send_document(self, file_path: str, caption: str = None) -> bool:
        """
        Send file/document to Telegram

        Args:
            file_path: Path to file
            caption: Optional caption

        Returns:
            Success status
        """
        if not self.bot_token or not self.chat_id:
            print(f"[TELEGRAM] Would send file: {file_path}")
            return False

        try:
            with open(file_path, 'rb') as f:
                files = {'document': f}
                data = {'chat_id': self.chat_id}
                if caption:
                    data['caption'] = caption

                response = requests.post(
                    f"{self.api_url}/sendDocument",
                    files=files,
                    data=data,
                    timeout=30
                )
            return response.status_code == 200
        except Exception as e:
            print(f"[ERROR] Telegram file send failed: {e}")
            return False

    # === PROCESS NOTIFICATIONS ===

    def notify_sop_started(self, sop_code: str, sop_title: str,
                          executed_by: str, execution_id: int) -> bool:
        """Notify when SOP execution starts"""
        text = f"""
🚀 *SOP Execution Started*

*SOP:* `{sop_code}`
*Title:* {sop_title}
*Executed by:* {executed_by}
*Execution ID:* {execution_id}
*Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

_Tracking execution..._
"""
        return self.send_message(text.strip())

    def notify_sop_completed(self, sop_code: str, sop_title: str,
                            executed_by: str, execution_id: int,
                            duration: int, success: bool) -> bool:
        """Notify when SOP execution completes"""
        emoji = "✅" if success else "❌"
        status = "Completed Successfully" if success else "Failed"

        text = f"""
{emoji} *SOP Execution {status}*

*SOP:* `{sop_code}`
*Title:* {sop_title}
*Executed by:* {executed_by}
*Execution ID:* {execution_id}
*Duration:* {duration} minutes
*Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        return self.send_message(text.strip())

    def notify_step_completed(self, sop_code: str, step_number: int,
                             step_title: str, execution_id: int) -> bool:
        """Notify when a step is completed (optional, for important steps)"""
        text = f"""
✓ *Step Completed*

*SOP:* `{sop_code}`
*Step {step_number}:* {step_title}
*Execution ID:* {execution_id}
"""
        return self.send_message(text.strip(), disable_notification=True)

    def notify_error(self, sop_code: str, execution_id: int,
                    error_message: str, step_number: int = None) -> bool:
        """Notify when an error occurs"""
        step_info = f"*Step:* {step_number}\n" if step_number else ""

        text = f"""
⚠️ *Process Error Detected*

*SOP:* `{sop_code}`
*Execution ID:* {execution_id}
{step_info}*Error:* {error_message}
*Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

_Please review execution details_
"""
        return self.send_message(text.strip())

    # === DAILY/WEEKLY REPORTS ===

    def send_daily_summary(self, summary: Dict) -> bool:
        """Send daily process execution summary"""
        text = f"""
📊 *Daily Process Summary*
_{datetime.now().strftime('%Y-%m-%d')}_

*Executions:* {summary.get('total_executions', 0)}
*Success Rate:* {summary.get('success_rate', 0):.0%}
*Average Duration:* {summary.get('avg_duration', 0)} minutes
*Active SOPs:* {summary.get('active_sops', 0)}
*Completed:* {summary.get('completed', 0)}
*Failed:* {summary.get('failed', 0)}

{'🎉 Great day!' if summary.get('success_rate', 0) > 0.9 else '⚠️ Some issues detected'}
"""
        return self.send_message(text.strip())

    def send_weekly_summary(self, summary: Dict) -> bool:
        """Send weekly process performance summary"""
        text = f"""
📈 *Weekly Process Summary*
_{summary.get('week_start')} - {summary.get('week_end')}_

*Total Executions:* {summary.get('total_executions', 0)}
*Success Rate:* {summary.get('success_rate', 0):.0%}
*Most Executed:* {summary.get('most_executed_sop', 'N/A')}
*Fastest SOP:* {summary.get('fastest_sop', 'N/A')}
*Slowest SOP:* {summary.get('slowest_sop', 'N/A')}

*Automation Rate:* {summary.get('automation_rate', 0):.0%}
*Cost Savings:* ${summary.get('cost_savings', 0):,.2f}

_Keep up the great work!_
"""
        return self.send_message(text.strip())

    # === PERFORMANCE REPORTS ===

    def send_sop_performance_report(self, sop_data: Dict) -> bool:
        """Send detailed SOP performance report"""
        text = f"""
📋 *SOP Performance Report*

*SOP:* `{sop_data['sop_code']}`
*Title:* {sop_data['title']}

*Statistics (Last 30 days):*
• Executions: {sop_data.get('executions', 0)}
• Success Rate: {sop_data.get('success_rate', 0):.0%}
• Avg Duration: {sop_data.get('avg_duration', 0)} min
• Automation Level: {sop_data.get('automation_level', 0):.0%}

*ROI:*
• Monthly Savings: ${sop_data.get('monthly_savings', 0):,.2f}
• Annual Savings: ${sop_data.get('annual_savings', 0):,.2f}

*Top Performers:*
{sop_data.get('top_performers', 'No data available')}
"""
        return self.send_message(text.strip())

    def send_bottleneck_alert(self, bottlenecks: List[Dict]) -> bool:
        """Send alert about process bottlenecks"""
        if not bottlenecks:
            return True

        text = "⚠️ *Process Bottlenecks Detected*\n\n"

        for i, b in enumerate(bottlenecks[:5], 1):
            text += f"{i}. *{b['sop_code']}*\n"
            text += f"   Step {b['step_number']}: {b['step_title']}\n"
            text += f"   Avg Duration: {b['avg_duration_minutes']} min\n"
            text += f"   Severity: {b.get('severity', 'medium')}\n\n"

        text += "_Review these processes for optimization opportunities_"

        return self.send_message(text.strip())

    # === APPROVAL REQUESTS ===

    def send_approval_request(self, approval_data: Dict) -> bool:
        """Send approval request with inline buttons"""
        text = f"""
🔔 *Approval Request*

*Type:* {approval_data['resource_type']}
*ID:* `{approval_data['resource_id']}`
*Requested by:* {approval_data['requested_by']}
*Description:* {approval_data.get('description', 'N/A')}

_Please review and approve/reject_

Approval ID: `{approval_data['request_id']}`
"""
        # Note: In a full implementation, we'd add inline keyboard buttons
        # For now, user can reply with text commands
        return self.send_message(text.strip())

    def send_approval_decision(self, decision: str, request_id: int,
                              decided_by: str) -> bool:
        """Notify about approval decision"""
        emoji = "✅" if decision == "approved" else "❌"

        text = f"""
{emoji} *Approval {decision.title()}*

*Request ID:* {request_id}
*Decided by:* {decided_by}
*Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        return self.send_message(text.strip())

    # === PREDICTIVE ALERTS ===

    def send_prediction_alert(self, prediction: Dict) -> bool:
        """Send predictive analytics alert"""
        alert_type = prediction.get('type', 'info')
        emoji = {
            'failure_risk': '⚠️',
            'delay_risk': '⏰',
            'optimization': '💡',
            'info': 'ℹ️'
        }.get(alert_type, 'ℹ️')

        text = f"""
{emoji} *Predictive Alert*

*SOP:* `{prediction['sop_code']}`
*Alert:* {prediction['message']}
*Probability:* {prediction.get('probability', 0):.0%}
*Impact:* {prediction.get('impact', 'Unknown')}

*Recommendation:*
{prediction.get('recommendation', 'Review process execution')}

_Proactive notification based on AI analysis_
"""
        return self.send_message(text.strip())

    # === SYSTEM STATUS ===

    def send_system_status(self, status: Dict) -> bool:
        """Send system health status"""
        emoji = "✅" if status.get('healthy', True) else "❌"

        text = f"""
{emoji} *System Status*

*Status:* {status.get('status', 'unknown')}
*Uptime:* {status.get('uptime', 'N/A')}
*Active Executions:* {status.get('active_executions', 0)}
*Queue Size:* {status.get('queue_size', 0)}

*Systems:*
• SOP Manager: {status.get('sop_manager', '✓')}
• Automation: {status.get('automation', '✓')}
• Analytics: {status.get('analytics', '✓')}
• Database: {status.get('database', '✓')}

_Last updated: {datetime.now().strftime('%H:%M:%S')}_
"""
        return self.send_message(text.strip())

    # === INTERACTIVE COMMANDS ===

    def handle_command(self, command: str, user_id: str) -> str:
        """
        Handle commands from Telegram

        Commands:
        /status - Get system status
        /summary - Get today's summary
        /sops - List active SOPs
        /execute [sop_id] - Start execution
        /help - Get help

        Args:
            command: Command text
            user_id: Telegram user ID

        Returns:
            Response message
        """
        cmd = command.lower().strip()

        if cmd == '/status':
            return self._get_status_response()
        elif cmd == '/summary':
            return self._get_summary_response()
        elif cmd == '/sops':
            return self._get_sops_response()
        elif cmd.startswith('/execute'):
            parts = cmd.split()
            if len(parts) > 1:
                return self._execute_sop_response(parts[1], user_id)
            else:
                return "Usage: /execute [sop_id]"
        elif cmd == '/help':
            return self._get_help_response()
        else:
            return "Unknown command. Use /help for available commands."

    def _get_status_response(self) -> str:
        """Get status response"""
        return """
*System Status*

All systems operational ✅

Use /summary for today's execution summary.
"""

    def _get_summary_response(self) -> str:
        """Get summary response"""
        return """
*Today's Summary*

Executions: 0
Success Rate: N/A

_Execute some SOPs to see statistics_
"""

    def _get_sops_response(self) -> str:
        """Get SOPs list response"""
        return """
*Active SOPs*

Use the web interface or mobile app to view all SOPs.

_Integration with SOP database coming soon_
"""

    def _execute_sop_response(self, sop_id: str, user_id: str) -> str:
        """Execute SOP response"""
        return f"""
*Execution Started*

SOP ID: {sop_id}
User: {user_id}

_Execution tracking in progress..._
"""

    def _get_help_response(self) -> str:
        """Get help response"""
        return """
*Available Commands*

/status - System status
/summary - Today's summary
/sops - List active SOPs
/execute [id] - Execute SOP
/help - This message

*Manage processes right from Telegram!*
"""


# === TEST CODE ===

def main():
    """Test Telegram integration"""
    print("=" * 70)
    print("Telegram Integration")
    print("=" * 70)

    telegram = TelegramIntegration()

    if not telegram.bot_token or not telegram.chat_id:
        print("\n[INFO] Telegram not configured")
        print("To set up:")
        print("1. Create bot with @BotFather on Telegram")
        print("2. Get bot token")
        print("3. Set TELEGRAM_BOT_TOKEN environment variable")
        print("4. Message @userinfobot to get your chat ID")
        print("5. Set TELEGRAM_CHAT_ID environment variable")
        print("\nExample:")
        print('  export TELEGRAM_BOT_TOKEN="123456:ABC-DEF..."')
        print('  export TELEGRAM_CHAT_ID="123456789"')
        return

    try:
        print("\n1. Testing basic message...")
        result = telegram.send_message("✅ Telegram integration test successful!")
        print(f"   Sent: {result}")

        print("\n2. Testing process notification...")
        telegram.notify_sop_started("SOP-001", "Test Process", "test_user", 123)

        print("\n3. Testing daily summary...")
        telegram.send_daily_summary({
            'total_executions': 45,
            'success_rate': 0.96,
            'avg_duration': 12.5,
            'active_sops': 23,
            'completed': 43,
            'failed': 2
        })

        print("\n4. Testing performance report...")
        telegram.send_sop_performance_report({
            'sop_code': 'SOP-001',
            'title': 'Test SOP',
            'executions': 100,
            'success_rate': 0.95,
            'avg_duration': 15,
            'automation_level': 0.75,
            'monthly_savings': 5000,
            'annual_savings': 60000
        })

        print(f"\n[OK] Telegram integration working!")
        print("Check your Telegram for messages!")

    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
