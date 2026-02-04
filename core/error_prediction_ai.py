"""
Error Prediction AI - HIGH PRIORITY ENHANCEMENT #1

Detects error conditions BEFORE they trigger, preventing failures proactively.

Uses ML patterns and heuristics to predict:
- Resource exhaustion before it happens
- Invalid state transitions
- Likely failure conditions
- Performance degradation leading to errors
"""

import sqlite3
import time
import psutil
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ErrorPrediction:
    """Predicted error condition"""
    error_type: str
    confidence: float  # 0.0-1.0
    predicted_in_seconds: int
    indicators: List[str]
    prevention_suggestions: List[str]
    severity: str  # low, medium, high, critical


class ErrorPredictionAI:
    """
    Predicts errors before they happen using ML patterns and heuristics

    Monitors:
    - Resource trends (memory/CPU trending to limits)
    - Error patterns (similar past failures)
    - System state (invalid configurations)
    - Performance degradation (slowdown before crash)
    """

    def __init__(self, db_path: str = "error_prediction.db"):
        self.db_path = db_path
        self._init_db()

        # Prediction thresholds
        self.thresholds = {
            'memory_warning_percent': 80,
            'memory_critical_percent': 90,
            'cpu_warning_percent': 80,
            'cpu_critical_percent': 95,
            'disk_warning_percent': 85,
            'disk_critical_percent': 95,
            'response_time_warning_ms': 1000,
            'response_time_critical_ms': 5000
        }

    def _init_db(self):
        """Initialize prediction database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                error_type TEXT,
                confidence REAL,
                predicted_in_seconds INTEGER,
                indicators TEXT,
                prevention_suggestions TEXT,
                severity TEXT,
                actually_occurred INTEGER DEFAULT 0,
                prevented INTEGER DEFAULT 0
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS prediction_accuracy (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prediction_id INTEGER,
                actual_error_time TEXT,
                prediction_was_correct INTEGER,
                time_difference_seconds INTEGER,
                FOREIGN KEY (prediction_id) REFERENCES predictions(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_metrics_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                cpu_percent REAL,
                memory_percent REAL,
                disk_percent REAL,
                response_time_ms REAL,
                active_connections INTEGER
            )
        ''')

        conn.commit()
        conn.close()

    def predict_errors(self) -> List[ErrorPrediction]:
        """
        Analyze current state and predict upcoming errors

        Returns:
            List of predicted errors with confidence levels
        """
        predictions = []

        # Record current metrics
        self._record_metrics()

        # Check various prediction sources
        predictions.extend(self._predict_resource_exhaustion())
        predictions.extend(self._predict_performance_degradation())
        predictions.extend(self._predict_pattern_based_errors())
        predictions.extend(self._predict_state_errors())

        # Store predictions
        for pred in predictions:
            self._store_prediction(pred)

        return predictions

    def _predict_resource_exhaustion(self) -> List[ErrorPrediction]:
        """Predict resource exhaustion errors"""
        predictions = []

        # Memory prediction
        mem = psutil.virtual_memory()
        if mem.percent > self.thresholds['memory_critical_percent']:
            predictions.append(ErrorPrediction(
                error_type='MemoryError',
                confidence=0.95,
                predicted_in_seconds=30,
                indicators=[
                    f'Memory at {mem.percent:.1f}% (critical threshold)',
                    f'Only {mem.available / 1024 / 1024:.0f} MB available'
                ],
                prevention_suggestions=[
                    'Run garbage collection immediately',
                    'Clear caches',
                    'Reduce memory-intensive operations',
                    'Enable memory optimization'
                ],
                severity='critical'
            ))
        elif mem.percent > self.thresholds['memory_warning_percent']:
            # Predict trend
            trend = self._predict_resource_trend('memory_percent', 300)
            if trend and trend > self.thresholds['memory_critical_percent']:
                predictions.append(ErrorPrediction(
                    error_type='MemoryError',
                    confidence=0.70,
                    predicted_in_seconds=300,
                    indicators=[
                        f'Memory at {mem.percent:.1f}% and trending up',
                        f'Predicted to reach {trend:.1f}% in 5 minutes'
                    ],
                    prevention_suggestions=[
                        'Monitor memory usage closely',
                        'Prepare for optimization',
                        'Consider clearing non-essential data'
                    ],
                    severity='high'
                ))

        # CPU prediction
        cpu = psutil.cpu_percent(interval=0.1)
        if cpu > self.thresholds['cpu_critical_percent']:
            predictions.append(ErrorPrediction(
                error_type='PerformanceError',
                confidence=0.90,
                predicted_in_seconds=60,
                indicators=[
                    f'CPU at {cpu:.1f}% (critical threshold)',
                    'System may become unresponsive'
                ],
                prevention_suggestions=[
                    'Reduce concurrent operations',
                    'Cancel non-essential tasks',
                    'Enable CPU throttling'
                ],
                severity='critical'
            ))

        # Disk prediction
        disk = psutil.disk_usage('.')
        if disk.percent > self.thresholds['disk_critical_percent']:
            predictions.append(ErrorPrediction(
                error_type='DiskFullError',
                confidence=0.98,
                predicted_in_seconds=120,
                indicators=[
                    f'Disk at {disk.percent:.1f}% capacity',
                    f'Only {disk.free / 1024 / 1024 / 1024:.1f} GB free'
                ],
                prevention_suggestions=[
                    'Clean up temporary files immediately',
                    'Delete old database files',
                    'Clear caches',
                    'Stop file-intensive operations'
                ],
                severity='critical'
            ))

        return predictions

    def _predict_performance_degradation(self) -> List[ErrorPrediction]:
        """Predict errors from performance degradation"""
        predictions = []

        # Get recent response times
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT AVG(response_time_ms)
            FROM system_metrics_history
            WHERE datetime(timestamp) > datetime('now', '-5 minutes')
        ''')

        row = cursor.fetchone()
        conn.close()

        if row and row[0]:
            avg_response = row[0]

            if avg_response > self.thresholds['response_time_critical_ms']:
                predictions.append(ErrorPrediction(
                    error_type='TimeoutError',
                    confidence=0.85,
                    predicted_in_seconds=180,
                    indicators=[
                        f'Average response time: {avg_response:.0f}ms',
                        'System significantly slower than normal',
                        'Timeouts likely to occur soon'
                    ],
                    prevention_suggestions=[
                        'Investigate slow operations',
                        'Enable caching',
                        'Reduce concurrent requests',
                        'Restart slow services'
                    ],
                    severity='high'
                ))

        return predictions

    def _predict_pattern_based_errors(self) -> List[ErrorPrediction]:
        """Predict errors based on historical patterns"""
        predictions = []

        # Check for recurring error patterns
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Look for predictions that actually occurred
        cursor.execute('''
            SELECT error_type, COUNT(*) as occurrences
            FROM predictions
            WHERE actually_occurred = 1
            AND datetime(timestamp) > datetime('now', '-1 day')
            GROUP BY error_type
            HAVING COUNT(*) > 2
            ORDER BY COUNT(*) DESC
        ''')

        patterns = cursor.fetchall()
        conn.close()

        for error_type, count in patterns:
            predictions.append(ErrorPrediction(
                error_type=error_type,
                confidence=min(0.60 + (count * 0.05), 0.90),
                predicted_in_seconds=600,
                indicators=[
                    f'{error_type} occurred {count} times today',
                    'Pattern suggests recurrence likely'
                ],
                prevention_suggestions=[
                    f'Review past {error_type} fixes',
                    'Apply preventive measures',
                    'Monitor for early warning signs'
                ],
                severity='medium'
            ))

        return predictions

    def _predict_state_errors(self) -> List[ErrorPrediction]:
        """Predict errors from invalid system state"""
        predictions = []

        # Check database connections
        try:
            import glob
            db_files = glob.glob("*.db")
            if len(db_files) > 100:
                predictions.append(ErrorPrediction(
                    error_type='TooManyDatabasesError',
                    confidence=0.75,
                    predicted_in_seconds=300,
                    indicators=[
                        f'{len(db_files)} database files found',
                        'May cause file handle exhaustion'
                    ],
                    prevention_suggestions=[
                        'Clean up unused databases',
                        'Consolidate database files',
                        'Implement database pooling'
                    ],
                    severity='medium'
                ))
        except Exception as e:
            logger.error(f"State check error: {e}")

        return predictions

    def _predict_resource_trend(self, metric: str, seconds_ahead: int) -> Optional[float]:
        """
        Predict future resource level based on trend

        Args:
            metric: Metric name (memory_percent, cpu_percent, etc)
            seconds_ahead: How far ahead to predict

        Returns:
            Predicted value or None
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get recent values
        cursor.execute(f'''
            SELECT {metric}, timestamp
            FROM system_metrics_history
            WHERE datetime(timestamp) > datetime('now', '-10 minutes')
            ORDER BY timestamp DESC
            LIMIT 20
        ''')

        values = cursor.fetchall()
        conn.close()

        if len(values) < 5:
            return None

        # Simple linear regression
        try:
            from datetime import datetime as dt

            # Convert to numeric timestamps
            data = [(dt.fromisoformat(ts).timestamp(), val) for val, ts in values]

            # Calculate slope
            n = len(data)
            sum_x = sum(x for x, y in data)
            sum_y = sum(y for x, y in data)
            sum_xy = sum(x * y for x, y in data)
            sum_x2 = sum(x * x for x, y in data)

            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)

            # Predict
            current_time = time.time()
            future_time = current_time + seconds_ahead
            current_value = values[0][0]

            predicted = current_value + (slope * seconds_ahead)

            return max(0, min(100, predicted))  # Clamp to valid range

        except Exception as e:
            logger.error(f"Trend prediction error: {e}")
            return None

    def _record_metrics(self):
        """Record current system metrics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO system_metrics_history
            (timestamp, cpu_percent, memory_percent, disk_percent, response_time_ms, active_connections)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            psutil.cpu_percent(interval=0.1),
            psutil.virtual_memory().percent,
            psutil.disk_usage('.').percent,
            0,  # Would measure actual response time
            len(psutil.Process().connections())
        ))

        conn.commit()
        conn.close()

    def _store_prediction(self, prediction: ErrorPrediction):
        """Store prediction in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO predictions
            (timestamp, error_type, confidence, predicted_in_seconds, indicators,
             prevention_suggestions, severity)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            prediction.error_type,
            prediction.confidence,
            prediction.predicted_in_seconds,
            json.dumps(prediction.indicators),
            json.dumps(prediction.prevention_suggestions),
            prediction.severity
        ))

        conn.commit()
        conn.close()

    def mark_prediction_occurred(self, error_type: str):
        """Mark that a predicted error actually occurred"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Find recent prediction
        cursor.execute('''
            SELECT id, timestamp, predicted_in_seconds
            FROM predictions
            WHERE error_type = ?
            AND actually_occurred = 0
            AND datetime(timestamp) > datetime('now', '-1 hour')
            ORDER BY confidence DESC
            LIMIT 1
        ''')

        row = cursor.fetchone()

        if row:
            pred_id, pred_time, predicted_seconds = row

            # Mark as occurred
            cursor.execute('''
                UPDATE predictions
                SET actually_occurred = 1
                WHERE id = ?
            ''', (pred_id,))

            # Record accuracy
            actual_time = datetime.now()
            predicted_time = datetime.fromisoformat(pred_time)
            diff = (actual_time - predicted_time).total_seconds()

            was_correct = abs(diff - predicted_seconds) < predicted_seconds * 0.5  # Within 50%

            cursor.execute('''
                INSERT INTO prediction_accuracy
                (prediction_id, actual_error_time, prediction_was_correct, time_difference_seconds)
                VALUES (?, ?, ?, ?)
            ''', (pred_id, actual_time.isoformat(), 1 if was_correct else 0, int(diff)))

        conn.commit()
        conn.close()

    def get_prediction_accuracy(self) -> Dict:
        """Get accuracy statistics for predictions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT
                COUNT(*) as total_predictions,
                SUM(CASE WHEN prediction_was_correct = 1 THEN 1 ELSE 0 END) as correct,
                AVG(time_difference_seconds) as avg_time_diff
            FROM prediction_accuracy
        ''')

        row = cursor.fetchone()
        conn.close()

        if row and row[0]:
            return {
                'total_predictions': row[0],
                'correct_predictions': row[1],
                'accuracy_percent': (row[1] / row[0] * 100) if row[0] > 0 else 0,
                'avg_time_difference_seconds': row[2] or 0
            }

        return {'total_predictions': 0, 'accuracy_percent': 0}


# Example usage
if __name__ == '__main__':
    predictor = ErrorPredictionAI()

    print("Error Prediction AI - Running Analysis...")
    print("="*80)

    # Get predictions
    predictions = predictor.predict_errors()

    if predictions:
        print(f"\n⚠️  {len(predictions)} POTENTIAL ERRORS PREDICTED\n")

        for i, pred in enumerate(predictions, 1):
            print(f"{i}. {pred.error_type} [{pred.severity.upper()}]")
            print(f"   Confidence: {pred.confidence*100:.0f}%")
            print(f"   Predicted in: {pred.predicted_in_seconds}s")
            print(f"   Indicators:")
            for indicator in pred.indicators:
                print(f"     • {indicator}")
            print(f"   Prevention:")
            for suggestion in pred.prevention_suggestions[:2]:
                print(f"     → {suggestion}")
            print()
    else:
        print("\n✓ No errors predicted - system healthy\n")

    # Show accuracy
    accuracy = predictor.get_prediction_accuracy()
    if accuracy['total_predictions'] > 0:
        print(f"Prediction Accuracy: {accuracy['accuracy_percent']:.1f}%")
        print(f"Total Predictions: {accuracy['total_predictions']}")

    print("="*80)
