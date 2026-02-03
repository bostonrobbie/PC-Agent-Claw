#!/usr/bin/env python3
"""Alert System (#42) - Real-time alerts and notifications"""
import sys
from pathlib import Path
from typing import Dict, List, Callable, Optional
from datetime import datetime
import json

sys.path.append(str(Path(__file__).parent.parent))

from core.persistent_memory import PersistentMemory

class AlertSystem:
    """System for managing real-time alerts and notifications"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            workspace = Path(__file__).parent.parent
            db_path = str(workspace / "memory.db")

        self.memory = PersistentMemory(db_path)
        self.alert_handlers: Dict[str, List[Callable]] = {}
        self.alert_history: List[Dict] = []

    def register_handler(self, alert_type: str, handler: Callable):
        """Register a handler for a specific alert type"""
        if alert_type not in self.alert_handlers:
            self.alert_handlers[alert_type] = []

        self.alert_handlers[alert_type].append(handler)

        self.memory.log_decision(
            f'Alert handler registered: {alert_type}',
            f'Handler: {handler.__name__}',
            tags=['alert', 'registration', alert_type]
        )

    def send_alert(self, alert_type: str, title: str, message: str,
                  priority: str = 'medium', metadata: Dict = None):
        """Send an alert"""
        alert = {
            'type': alert_type,
            'title': title,
            'message': message,
            'priority': priority,
            'metadata': metadata or {},
            'timestamp': datetime.now().isoformat()
        }

        # Log to memory
        self.memory.log_decision(
            f'Alert: {title}',
            f'Type: {alert_type}, Priority: {priority}, Message: {message}',
            tags=['alert', alert_type, priority]
        )

        # Store in history
        self.alert_history.append(alert)

        # Call registered handlers
        if alert_type in self.alert_handlers:
            for handler in self.alert_handlers[alert_type]:
                try:
                    handler(alert)
                except Exception as e:
                    print(f"Alert handler error: {e}")

        # Call 'all' handlers
        if 'all' in self.alert_handlers:
            for handler in self.alert_handlers['all']:
                try:
                    handler(alert)
                except Exception as e:
                    print(f"Alert handler error: {e}")

        return alert

    def get_recent_alerts(self, limit: int = 10, alert_type: str = None,
                         priority: str = None) -> List[Dict]:
        """Get recent alerts with optional filters"""
        alerts = self.alert_history

        # Filter by type
        if alert_type:
            alerts = [a for a in alerts if a['type'] == alert_type]

        # Filter by priority
        if priority:
            alerts = [a for a in alerts if a['priority'] == priority]

        # Return most recent
        return alerts[-limit:]

    def clear_history(self):
        """Clear alert history"""
        self.alert_history.clear()


# Built-in alert types
class TradingAlerts:
    """Pre-defined trading alerts"""

    @staticmethod
    def price_alert(alert_system: AlertSystem, symbol: str, current_price: float,
                   target_price: float, condition: str):
        """Send price alert"""
        alert_system.send_alert(
            'price',
            f'{symbol} Price Alert',
            f'{symbol} is {condition} {target_price:.2f} (current: {current_price:.2f})',
            priority='high',
            metadata={'symbol': symbol, 'price': current_price, 'target': target_price}
        )

    @staticmethod
    def trade_execution_alert(alert_system: AlertSystem, symbol: str, side: str,
                            quantity: float, price: float, pnl: float = None):
        """Send trade execution alert"""
        msg = f'Executed {side} {quantity} {symbol} @ {price:.2f}'
        if pnl is not None:
            msg += f' | P&L: ${pnl:.2f}'

        alert_system.send_alert(
            'trade_execution',
            'Trade Executed',
            msg,
            priority='medium',
            metadata={'symbol': symbol, 'side': side, 'quantity': quantity, 'price': price}
        )

    @staticmethod
    def risk_alert(alert_system: AlertSystem, title: str, message: str, risk_level: str):
        """Send risk alert"""
        priority = 'critical' if risk_level == 'high' else 'high'

        alert_system.send_alert(
            'risk',
            title,
            message,
            priority=priority,
            metadata={'risk_level': risk_level}
        )

    @staticmethod
    def system_alert(alert_system: AlertSystem, component: str, status: str, details: str):
        """Send system status alert"""
        priority = 'critical' if status == 'error' else 'medium'

        alert_system.send_alert(
            'system',
            f'{component} {status}',
            details,
            priority=priority,
            metadata={'component': component, 'status': status}
        )


# Example handlers
def console_handler(alert: Dict):
    """Print alerts to console"""
    timestamp = alert['timestamp']
    priority = alert['priority'].upper()
    title = alert['title']
    message = alert['message']
    print(f"[{timestamp}] [{priority}] {title}: {message}")

def telegram_handler(alert: Dict):
    """Send alerts to Telegram"""
    # This would use the Telegram API
    pass

def email_handler(alert: Dict):
    """Send alerts via email"""
    # This would use SMTP
    pass


if __name__ == '__main__':
    # Test the system
    alert_system = AlertSystem()

    # Register handlers
    alert_system.register_handler('all', console_handler)

    print("Alert System ready!")

    # Send test alerts
    print("\nSending test alerts...")

    TradingAlerts.price_alert(alert_system, 'NQ', 16545.0, 16500.0, 'above')
    TradingAlerts.trade_execution_alert(alert_system, 'ES', 'BUY', 2, 4800.50, pnl=125.00)
    TradingAlerts.risk_alert(alert_system, 'Risk Limit Exceeded', 'Position size exceeds 2% risk limit', 'high')
    TradingAlerts.system_alert(alert_system, 'Database', 'connected', 'All systems operational')

    # Get recent alerts
    recent = alert_system.get_recent_alerts(limit=5)
    print(f"\nRecent alerts: {len(recent)}")
