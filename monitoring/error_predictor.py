#!/usr/bin/env python3
"""Error Predictor - Predict errors before they happen"""
import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import json

sys.path.append(str(Path(__file__).parent.parent))

from core.persistent_memory import PersistentMemory
from core.telegram_connector import TelegramConnector

class ErrorPredictor:
    """Predict and prevent errors before they occur"""

    def __init__(self, db_path: str = None):
        workspace = Path(__file__).parent.parent
        if db_path is None:
            db_path = str(workspace / "memory.db")

        self.memory = PersistentMemory(db_path)
        self.telegram = TelegramConnector()

        # Pattern tracking
        self.error_sequences = []  # Track error sequences
        self.precursor_patterns = {}  # event -> likely_errors
        self.time_patterns = {}  # hour -> error_counts

    def analyze_error_history(self, hours: int = 24) -> Dict:
        """Analyze error history for patterns"""
        cursor = self.memory.conn.cursor()

        # Get recent errors
        cursor.execute("""
            SELECT decision, created_at
            FROM decisions
            WHERE (decision LIKE '%Error occurred:%' OR decision LIKE '%error%')
            AND created_at >= datetime('now', ?)
            ORDER BY created_at DESC
        """, (f'-{hours} hours',))

        errors = cursor.fetchall()

        # Analyze patterns
        patterns = {
            'total_errors': len(errors),
            'error_types': defaultdict(int),
            'hourly_distribution': defaultdict(int),
            'error_rate_trend': 'stable'
        }

        for error in errors:
            decision = error['decision']
            timestamp = datetime.fromisoformat(error['created_at'])

            # Extract error type
            if 'Error occurred:' in decision:
                error_type = decision.split('Error occurred:')[1].split('\n')[0].strip()
                patterns['error_types'][error_type] += 1

            # Hourly distribution
            hour = timestamp.hour
            patterns['hourly_distribution'][hour] += 1

        # Determine trend
        if len(errors) >= 2:
            recent_count = sum(1 for e in errors if
                              datetime.fromisoformat(e['created_at']) >=
                              datetime.now() - timedelta(hours=1))

            older_count = len(errors) - recent_count

            if recent_count > older_count * 1.5:
                patterns['error_rate_trend'] = 'increasing'
            elif recent_count < older_count * 0.5:
                patterns['error_rate_trend'] = 'decreasing'

        return dict(patterns)

    def detect_precursors(self, event: str) -> List[str]:
        """Detect if an event is a precursor to errors"""
        precursors = {
            'high_memory_usage': ['MemoryError', 'SlowPerformance'],
            'connection_timeout': ['ConnectionError', 'TimeoutError'],
            'disk_full': ['IOError', 'WriteError'],
            'high_cpu': ['TimeoutError', 'SlowPerformance'],
            'database_lock': ['DatabaseError', 'OperationalError']
        }

        return precursors.get(event, [])

    def predict_likely_errors(self, context: Dict) -> List[Dict]:
        """Predict likely errors based on context"""
        predictions = []

        # Check system resources
        if 'memory_percent' in context and context['memory_percent'] > 90:
            predictions.append({
                'error_type': 'MemoryError',
                'probability': 0.7,
                'reason': 'Memory usage >90%',
                'recommendation': 'Free memory or restart processes'
            })

        if 'disk_percent' in context and context['disk_percent'] > 95:
            predictions.append({
                'error_type': 'IOError',
                'probability': 0.8,
                'reason': 'Disk usage >95%',
                'recommendation': 'Clean up disk space immediately'
            })

        # Check error history
        history = self.analyze_error_history(hours=1)

        if history['error_rate_trend'] == 'increasing':
            predictions.append({
                'error_type': 'SystemInstability',
                'probability': 0.6,
                'reason': 'Error rate increasing',
                'recommendation': 'Review recent changes and logs'
            })

        # Check time patterns
        current_hour = datetime.now().hour
        if current_hour in history.get('hourly_distribution', {}):
            error_count = history['hourly_distribution'][current_hour]
            if error_count > 5:
                predictions.append({
                    'error_type': 'TimeBasedError',
                    'probability': 0.5,
                    'reason': f'Hour {current_hour} has high error rate historically',
                    'recommendation': 'Monitor closely during this hour'
                })

        return predictions

    def recommend_preventive_actions(self, predictions: List[Dict]) -> List[str]:
        """Recommend preventive actions based on predictions"""
        actions = []

        for pred in predictions:
            error_type = pred['error_type']

            if error_type == 'MemoryError':
                actions.append('Clear caches and free memory')
                actions.append('Restart memory-intensive processes')

            elif error_type == 'IOError':
                actions.append('Clean up temporary files')
                actions.append('Archive old logs')
                actions.append('Remove unnecessary data')

            elif error_type == 'ConnectionError':
                actions.append('Check network connectivity')
                actions.append('Verify service availability')
                actions.append('Reduce connection timeout settings')

            elif error_type == 'SystemInstability':
                actions.append('Review recent code changes')
                actions.append('Check system logs')
                actions.append('Consider rollback if needed')

        return list(set(actions))  # Remove duplicates

    def monitor_and_alert(self, check_interval: int = 300):
        """Monitor system and alert on predicted errors"""
        import time
        import psutil

        while True:
            try:
                # Gather context
                context = {
                    'memory_percent': psutil.virtual_memory().percent,
                    'disk_percent': psutil.disk_usage('C:\\').percent,
                    'cpu_percent': psutil.cpu_percent(interval=1)
                }

                # Predict errors
                predictions = self.predict_likely_errors(context)

                # Alert if high probability errors predicted
                high_risk = [p for p in predictions if p['probability'] > 0.7]

                if high_risk:
                    self._send_prediction_alert(high_risk, context)

                    self.memory.log_decision(
                        f'Error prediction alert sent',
                        f'Predicted {len(high_risk)} high-risk errors',
                        tags=['error_predictor', 'alert', 'prediction']
                    )

                time.sleep(check_interval)

            except Exception as e:
                print(f"Monitor error: {e}")
                time.sleep(check_interval)

    def _send_prediction_alert(self, predictions: List[Dict], context: Dict):
        """Send alert about predicted errors"""
        message = "[ERROR PREDICTION]\n"

        for pred in predictions[:3]:  # Top 3
            message += (
                f"\n{pred['error_type']}: {int(pred['probability']*100)}% likely\n"
                f"Reason: {pred['reason']}\n"
                f"Action: {pred['recommendation']}\n"
            )

        message += f"\nCurrent state:\n"
        message += f"Memory: {context.get('memory_percent', 0):.1f}%\n"
        message += f"Disk: {context.get('disk_percent', 0):.1f}%\n"
        message += f"CPU: {context.get('cpu_percent', 0):.1f}%"

        self.telegram.send_message(message)


if __name__ == '__main__':
    import psutil

    predictor = ErrorPredictor()

    print("Error Predictor ready!")

    # Analyze recent errors
    print("\nAnalyzing error history...")
    history = predictor.analyze_error_history(hours=24)
    print(f"Total errors (24h): {history['total_errors']}")
    print(f"Error rate trend: {history['error_rate_trend']}")

    # Predict errors based on current system state
    print("\nPredicting errors...")
    context = {
        'memory_percent': psutil.virtual_memory().percent,
        'disk_percent': psutil.disk_usage('C:\\').percent,
        'cpu_percent': psutil.cpu_percent(interval=1)
    }

    predictions = predictor.predict_likely_errors(context)

    if predictions:
        print(f"\nPredicted {len(predictions)} potential errors:")
        for pred in predictions:
            print(f"  - {pred['error_type']}: {int(pred['probability']*100)}% likely")
            print(f"    Reason: {pred['reason']}")
            print(f"    Action: {pred['recommendation']}")

        # Get preventive actions
        actions = predictor.recommend_preventive_actions(predictions)
        print(f"\nRecommended preventive actions:")
        for action in actions:
            print(f"  - {action}")
    else:
        print("\nNo errors predicted - system looks healthy!")

    print("\nError Predictor operational!")
