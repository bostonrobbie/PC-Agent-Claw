#!/usr/bin/env python3
"""Webhook System (#93) - Receive and process webhooks from external services"""
import json
from pathlib import Path
from flask import Flask, request, jsonify
from typing import Dict, Callable, List
import threading
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from core.persistent_memory import PersistentMemory

class WebhookSystem:
    def __init__(self, port: int = 5050, db_path: str = None):
        self.port = port
        self.app = Flask(__name__)
        self.handlers: Dict[str, List[Callable]] = {}

        if db_path is None:
            workspace = Path(__file__).parent.parent
            db_path = str(workspace / "memory.db")
        self.memory = PersistentMemory(db_path)

        # Register routes
        self._setup_routes()

    def _setup_routes(self):
        """Setup Flask routes"""
        @self.app.route('/webhook/<path:endpoint>', methods=['POST', 'GET'])
        def handle_webhook(endpoint):
            try:
                # Get webhook data
                if request.method == 'POST':
                    data = request.get_json() or {}
                else:
                    data = dict(request.args)

                # Log webhook receipt
                self.memory.log_decision(
                    f'Webhook received: {endpoint}',
                    f'Data: {json.dumps(data)[:500]}',
                    tags=['webhook', endpoint]
                )

                # Call registered handlers
                results = []
                if endpoint in self.handlers:
                    for handler in self.handlers[endpoint]:
                        try:
                            result = handler(data)
                            results.append(result)
                        except Exception as e:
                            results.append(f"Handler error: {str(e)}")

                return jsonify({
                    'status': 'success',
                    'endpoint': endpoint,
                    'handlers_executed': len(results),
                    'results': results
                })

            except Exception as e:
                return jsonify({
                    'status': 'error',
                    'error': str(e)
                }), 500

        @self.app.route('/health', methods=['GET'])
        def health():
            return jsonify({'status': 'healthy', 'handlers': list(self.handlers.keys())})

    def register_handler(self, endpoint: str, handler: Callable):
        """Register a handler function for a webhook endpoint"""
        if endpoint not in self.handlers:
            self.handlers[endpoint] = []
        self.handlers[endpoint].append(handler)

        self.memory.log_decision(
            f'Webhook handler registered',
            f'Endpoint: {endpoint}, Handler: {handler.__name__}',
            tags=['webhook', 'registration', endpoint]
        )

    def start(self):
        """Start the webhook server in a background thread"""
        thread = threading.Thread(target=lambda: self.app.run(host='0.0.0.0', port=self.port, debug=False))
        thread.daemon = True
        thread.start()
        print(f"Webhook server started on port {self.port}")
        return thread


# Example handlers
def github_webhook_handler(data: Dict) -> str:
    """Example handler for GitHub webhooks"""
    event_type = data.get('action', 'unknown')
    repo = data.get('repository', {}).get('name', 'unknown')
    return f"GitHub {event_type} in {repo}"

def trading_alert_handler(data: Dict) -> str:
    """Example handler for trading alerts"""
    alert_type = data.get('type', 'unknown')
    symbol = data.get('symbol', 'unknown')
    return f"Trading alert: {alert_type} for {symbol}"


if __name__ == '__main__':
    # Create webhook system
    webhook_system = WebhookSystem(port=5050)

    # Register example handlers
    webhook_system.register_handler('github', github_webhook_handler)
    webhook_system.register_handler('trading', trading_alert_handler)

    # Start server
    webhook_system.start()

    print("Webhook system running...")
    print("Endpoints:")
    print("  - POST http://localhost:5050/webhook/github")
    print("  - POST http://localhost:5050/webhook/trading")
    print("  - GET  http://localhost:5050/health")

    # Keep running
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
