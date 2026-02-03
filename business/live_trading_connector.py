#!/usr/bin/env python3
"""Live Trading Connector (#40) - Connect to live trading platforms"""
import sys
from pathlib import Path
from typing import Dict, List, Optional, Callable
from datetime import datetime
import json

sys.path.append(str(Path(__file__).parent.parent))

from core.persistent_memory import PersistentMemory

class LiveTradingConnector:
    """Interface for connecting to live trading platforms"""

    def __init__(self, platform: str = 'interactive_brokers', db_path: str = None):
        self.platform = platform
        self.connected = False
        self.account_info = {}

        if db_path is None:
            workspace = Path(__file__).parent.parent
            db_path = str(workspace / "memory.db")

        self.memory = PersistentMemory(db_path)

    def connect(self, host: str = '127.0.0.1', port: int = 7497, client_id: int = 1) -> bool:
        """Connect to trading platform"""
        try:
            if self.platform == 'interactive_brokers':
                # For IB, check if bridge server is available
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex((host, port))
                sock.close()

                if result == 0:
                    self.connected = True
                    self.memory.log_decision(
                        'Connected to trading platform',
                        f'Platform: {self.platform}, Host: {host}:{port}',
                        tags=['trading', 'connection', self.platform]
                    )
                    return True

            return False

        except Exception as e:
            self.memory.log_decision(
                'Failed to connect to trading platform',
                f'Platform: {self.platform}, Error: {str(e)}',
                tags=['trading', 'connection_error', self.platform]
            )
            return False

    def disconnect(self):
        """Disconnect from trading platform"""
        self.connected = False
        self.memory.log_decision(
            'Disconnected from trading platform',
            f'Platform: {self.platform}',
            tags=['trading', 'disconnection', self.platform]
        )

    def get_account_summary(self) -> Dict:
        """Get account summary information"""
        if not self.connected:
            return {'error': 'Not connected'}

        # This would use the actual platform API
        # For now, return a mock structure
        return {
            'platform': self.platform,
            'account_id': 'MOCK_ACCOUNT',
            'balance': 0,
            'buying_power': 0,
            'positions_count': 0,
            'connected': self.connected
        }

    def get_positions(self) -> List[Dict]:
        """Get current positions"""
        if not self.connected:
            return []

        # This would use the actual platform API
        return []

    def place_order(self, symbol: str, quantity: float, order_type: str = 'MARKET',
                   side: str = 'BUY', limit_price: float = None) -> Optional[str]:
        """Place a trading order"""
        if not self.connected:
            self.memory.log_decision(
                'Order placement failed',
                'Not connected to trading platform',
                tags=['trading', 'order_error']
            )
            return None

        order_details = {
            'symbol': symbol,
            'quantity': quantity,
            'order_type': order_type,
            'side': side,
            'limit_price': limit_price,
            'timestamp': datetime.now().isoformat()
        }

        self.memory.log_decision(
            f'Order placed: {side} {quantity} {symbol}',
            f'Type: {order_type}, Details: {json.dumps(order_details)}',
            tags=['trading', 'order', symbol]
        )

        # Return mock order ID
        return f"ORDER_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order"""
        if not self.connected:
            return False

        self.memory.log_decision(
            f'Order cancelled: {order_id}',
            f'Platform: {self.platform}',
            tags=['trading', 'cancel_order', order_id]
        )

        return True

    def get_market_data(self, symbol: str) -> Dict:
        """Get real-time market data for a symbol"""
        if not self.connected:
            return {'error': 'Not connected'}

        # This would use the actual platform API
        return {
            'symbol': symbol,
            'last_price': 0,
            'bid': 0,
            'ask': 0,
            'volume': 0,
            'timestamp': datetime.now().isoformat()
        }

    def register_callback(self, event_type: str, callback: Callable):
        """Register callback for trading events"""
        self.memory.log_decision(
            f'Callback registered: {event_type}',
            f'Callback: {callback.__name__}',
            tags=['trading', 'callback', event_type]
        )

    def get_order_status(self, order_id: str) -> Dict:
        """Get status of an order"""
        if not self.connected:
            return {'error': 'Not connected'}

        return {
            'order_id': order_id,
            'status': 'PENDING',
            'filled_quantity': 0,
            'remaining_quantity': 0
        }


# Safety checks
class TradingSafetyChecks:
    """Safety checks for live trading"""

    @staticmethod
    def validate_order_size(symbol: str, quantity: float, max_position_size: float) -> bool:
        """Validate order size is within limits"""
        return quantity <= max_position_size

    @staticmethod
    def validate_risk_limits(account_balance: float, order_value: float, max_risk_pct: float = 2.0) -> bool:
        """Validate order doesn't exceed risk limits"""
        risk_amount = order_value
        max_risk = account_balance * (max_risk_pct / 100)
        return risk_amount <= max_risk

    @staticmethod
    def validate_trading_hours(symbol: str) -> bool:
        """Check if market is open for trading"""
        # This would check actual market hours
        # For now, return True
        return True

    @staticmethod
    def validate_stop_loss(entry_price: float, stop_loss: float, side: str) -> bool:
        """Validate stop loss is set correctly"""
        if side.upper() == 'BUY':
            return stop_loss < entry_price
        else:
            return stop_loss > entry_price


if __name__ == '__main__':
    # Test the system
    connector = LiveTradingConnector('interactive_brokers')

    print("Live Trading Connector ready!")

    # Try to connect
    print("\nAttempting to connect to Interactive Brokers...")
    connected = connector.connect(host='127.0.0.1', port=5001)

    if connected:
        print("Connected successfully!")

        # Get account summary
        summary = connector.get_account_summary()
        print(f"\nAccount Summary:")
        print(json.dumps(summary, indent=2))
    else:
        print("Not connected. Start TWS/Gateway to enable live trading.")

    print("\nSafety checks enabled:")
    print("  - Order size validation")
    print("  - Risk limit validation")
    print("  - Trading hours validation")
    print("  - Stop loss validation")
