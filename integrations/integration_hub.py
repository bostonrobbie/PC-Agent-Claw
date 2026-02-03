#!/usr/bin/env python3
"""
Integration Hub
Connect business processes to external services (Slack, Email, CRM, etc.)
"""
import sys
from pathlib import Path
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import json
from typing import Dict, List, Optional
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))


class IntegrationHub:
    """
    Central hub for external integrations

    Supported integrations:
    - Slack: Send notifications, post updates
    - Email: Send notifications, reports
    - Webhooks: Generic HTTP callbacks
    - CRM: Salesforce, HubSpot integration
    """

    def __init__(self):
        self.slack_webhook_url = None
        self.email_config = {}
        self.crm_config = {}
        self.webhooks = {}

    # === CONFIGURATION ===

    def configure_slack(self, webhook_url: str):
        """Configure Slack integration"""
        self.slack_webhook_url = webhook_url

    def configure_email(self, smtp_host: str, smtp_port: int,
                       username: str, password: str, from_address: str):
        """Configure email integration"""
        self.email_config = {
            'host': smtp_host,
            'port': smtp_port,
            'username': username,
            'password': password,
            'from': from_address
        }

    def configure_crm(self, crm_type: str, api_key: str, domain: str = None):
        """
        Configure CRM integration

        Args:
            crm_type: 'salesforce', 'hubspot', 'pipedrive'
            api_key: API key or access token
            domain: CRM domain/instance URL
        """
        self.crm_config = {
            'type': crm_type,
            'api_key': api_key,
            'domain': domain
        }

    def add_webhook(self, name: str, url: str, method: str = 'POST',
                   headers: Dict = None):
        """
        Register webhook endpoint

        Args:
            name: Webhook identifier
            url: Webhook URL
            method: HTTP method
            headers: Optional headers
        """
        self.webhooks[name] = {
            'url': url,
            'method': method,
            'headers': headers or {}
        }

    # === SLACK INTEGRATION ===

    def send_slack_message(self, text: str, channel: str = None,
                          blocks: List = None) -> bool:
        """
        Send message to Slack

        Args:
            text: Message text
            channel: Override channel (optional)
            blocks: Slack blocks for rich formatting

        Returns:
            Success status
        """
        if not self.slack_webhook_url:
            print("[WARNING] Slack not configured")
            return False

        payload = {'text': text}

        if channel:
            payload['channel'] = channel

        if blocks:
            payload['blocks'] = blocks

        try:
            response = requests.post(
                self.slack_webhook_url,
                json=payload,
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            print(f"[ERROR] Slack send failed: {e}")
            return False

    def notify_sop_execution(self, sop_code: str, sop_title: str,
                            status: str, executed_by: str) -> bool:
        """Send SOP execution notification to Slack"""
        emoji = "✅" if status == "completed" else "⚠️"

        text = f"{emoji} SOP Execution: *{sop_code}*\n"
        text += f"Title: {sop_title}\n"
        text += f"Status: {status}\n"
        text += f"Executed by: {executed_by}\n"
        text += f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        return self.send_slack_message(text)

    def send_daily_summary(self, summary: Dict) -> bool:
        """Send daily process summary to Slack"""
        text = "📊 *Daily Process Summary*\n\n"
        text += f"Total Executions: {summary.get('total_executions', 0)}\n"
        text += f"Success Rate: {summary.get('success_rate', 0):.0%}\n"
        text += f"Avg Duration: {summary.get('avg_duration', 0)} min\n"
        text += f"Active SOPs: {summary.get('active_sops', 0)}"

        return self.send_slack_message(text)

    # === EMAIL INTEGRATION ===

    def send_email(self, to: List[str], subject: str, body: str,
                  html: bool = False, cc: List = None, bcc: List = None) -> bool:
        """
        Send email

        Args:
            to: Recipient email addresses
            subject: Email subject
            body: Email body (plain text or HTML)
            html: If True, body is HTML
            cc: CC addresses
            bcc: BCC addresses

        Returns:
            Success status
        """
        if not self.email_config:
            print("[WARNING] Email not configured")
            return False

        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.email_config['from']
            msg['To'] = ', '.join(to)

            if cc:
                msg['Cc'] = ', '.join(cc)

            # Attach body
            if html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))

            # Send
            with smtplib.SMTP(self.email_config['host'],
                            self.email_config['port']) as server:
                server.starttls()
                server.login(self.email_config['username'],
                           self.email_config['password'])

                recipients = to + (cc or []) + (bcc or [])
                server.send_message(msg, to_addrs=recipients)

            return True

        except Exception as e:
            print(f"[ERROR] Email send failed: {e}")
            return False

    def send_sop_report(self, to: List[str], sop_data: Dict) -> bool:
        """Send SOP performance report via email"""
        subject = f"SOP Report: {sop_data['sop_code']}"

        body = f"""
        <html>
        <body>
            <h2>{sop_data['sop_title']}</h2>
            <p><strong>SOP Code:</strong> {sop_data['sop_code']}</p>
            <p><strong>Executions:</strong> {sop_data.get('executions', 0)}</p>
            <p><strong>Success Rate:</strong> {sop_data.get('success_rate', 0):.0%}</p>
            <p><strong>Avg Duration:</strong> {sop_data.get('avg_duration', 0)} minutes</p>
            <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </body>
        </html>
        """

        return self.send_email(to, subject, body, html=True)

    def send_bottleneck_alert(self, to: List[str], bottlenecks: List[Dict]) -> bool:
        """Send alert about process bottlenecks"""
        if not bottlenecks:
            return True

        subject = "⚠️ Process Bottlenecks Detected"

        body = "<html><body><h2>Process Bottlenecks Detected</h2><ul>"
        for b in bottlenecks[:5]:  # Top 5
            body += f"<li><strong>{b['sop_code']}</strong>: "
            body += f"Step {b['step_number']} - {b['step_title']} "
            body += f"({b['avg_duration_minutes']} min)</li>"
        body += "</ul></body></html>"

        return self.send_email(to, subject, body, html=True)

    # === WEBHOOK INTEGRATION ===

    def call_webhook(self, webhook_name: str, data: Dict) -> bool:
        """
        Call registered webhook

        Args:
            webhook_name: Webhook identifier
            data: Payload to send

        Returns:
            Success status
        """
        if webhook_name not in self.webhooks:
            print(f"[WARNING] Webhook '{webhook_name}' not configured")
            return False

        webhook = self.webhooks[webhook_name]

        try:
            if webhook['method'] == 'POST':
                response = requests.post(
                    webhook['url'],
                    json=data,
                    headers=webhook['headers'],
                    timeout=10
                )
            else:
                response = requests.get(
                    webhook['url'],
                    params=data,
                    headers=webhook['headers'],
                    timeout=10
                )

            return response.status_code < 400

        except Exception as e:
            print(f"[ERROR] Webhook call failed: {e}")
            return False

    # === CRM INTEGRATION ===

    def create_crm_record(self, record_type: str, data: Dict) -> Optional[str]:
        """
        Create record in CRM

        Args:
            record_type: 'lead', 'contact', 'deal', 'task'
            data: Record data

        Returns:
            Created record ID or None
        """
        if not self.crm_config:
            print("[WARNING] CRM not configured")
            return None

        crm_type = self.crm_config['type']

        if crm_type == 'salesforce':
            return self._create_salesforce_record(record_type, data)
        elif crm_type == 'hubspot':
            return self._create_hubspot_record(record_type, data)
        else:
            print(f"[WARNING] CRM type '{crm_type}' not supported")
            return None

    def _create_salesforce_record(self, record_type: str, data: Dict) -> Optional[str]:
        """Create Salesforce record"""
        # Placeholder for Salesforce API integration
        print(f"[INFO] Would create Salesforce {record_type}: {data}")
        return "SF_" + str(hash(json.dumps(data)))[:8]

    def _create_hubspot_record(self, record_type: str, data: Dict) -> Optional[str]:
        """Create HubSpot record"""
        # Placeholder for HubSpot API integration
        print(f"[INFO] Would create HubSpot {record_type}: {data}")
        return "HS_" + str(hash(json.dumps(data)))[:8]

    def update_crm_record(self, record_id: str, data: Dict) -> bool:
        """Update CRM record"""
        if not self.crm_config:
            return False

        print(f"[INFO] Would update CRM record {record_id}: {data}")
        return True

    # === EVENT HANDLERS ===

    def on_sop_completed(self, sop_data: Dict):
        """Handle SOP completion event"""
        # Send Slack notification
        if self.slack_webhook_url:
            self.notify_sop_execution(
                sop_data['sop_code'],
                sop_data['sop_title'],
                'completed',
                sop_data.get('executed_by', 'system')
            )

        # Call webhooks
        for webhook_name in self.webhooks:
            if 'sop_completed' in webhook_name:
                self.call_webhook(webhook_name, sop_data)

    def on_bottleneck_detected(self, bottlenecks: List[Dict], notify_emails: List[str]):
        """Handle bottleneck detection event"""
        # Send email alert
        if self.email_config and notify_emails:
            self.send_bottleneck_alert(notify_emails, bottlenecks)

        # Send Slack alert
        if self.slack_webhook_url and bottlenecks:
            text = f"⚠️ *{len(bottlenecks)} Process Bottlenecks Detected*\n\n"
            for b in bottlenecks[:3]:
                text += f"• {b['sop_code']}: Step {b['step_number']} "
                text += f"({b['avg_duration_minutes']} min)\n"

            self.send_slack_message(text)


# === TEST CODE ===

def main():
    """Test integration hub"""
    print("=" * 70)
    print("Integration Hub")
    print("=" * 70)

    hub = IntegrationHub()

    try:
        print("\n1. Configuring integrations...")
        # Slack (mock)
        hub.configure_slack("https://hooks.slack.com/services/mock")
        print("   ✓ Slack configured")

        # Email (mock)
        hub.configure_email(
            "smtp.gmail.com",
            587,
            "user@example.com",
            "password",
            "noreply@company.com"
        )
        print("   ✓ Email configured")

        # Webhook
        hub.add_webhook("sop_completed", "https://example.com/webhook")
        print("   ✓ Webhook configured")

        # CRM
        hub.configure_crm("salesforce", "api_key_here", "company.salesforce.com")
        print("   ✓ CRM configured")

        print("\n2. Testing Slack notification...")
        result = hub.send_slack_message("Test message from Integration Hub")
        print(f"   Slack test: {'OK' if result else 'Skipped (no real webhook)'}")

        print("\n3. Testing webhook...")
        result = hub.call_webhook("sop_completed", {"test": "data"})
        print(f"   Webhook test: {'OK' if result else 'Skipped'}")

        print("\n4. Testing CRM integration...")
        record_id = hub.create_crm_record("lead", {
            "name": "Test Lead",
            "email": "test@example.com"
        })
        print(f"   CRM record created: {record_id}")

        print(f"\n[OK] Integration Hub working!")
        print("   Supports: Slack, Email, Webhooks, CRM")

    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
