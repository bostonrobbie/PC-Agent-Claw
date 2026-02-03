#!/usr/bin/env python3
"""
Pattern Learning System
Automatically detect and learn patterns from data and interactions
"""
import sys
from pathlib import Path
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict, Counter
import traceback

sys.path.append(str(Path(__file__).parent.parent))


class PatternLearner:
    """
    Detect and learn patterns automatically

    Features:
    - Sequence pattern detection
    - Correlation discovery
    - Anomaly detection
    - Trend identification
    - Pattern-based prediction
    - Automatic rule extraction
    """

    def __init__(self, db_path: str = None, min_support: float = 0.3):
        workspace = Path(__file__).parent.parent
        if db_path is None:
            db_path = str(workspace / "memory.db")

        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

        self.min_support = min_support  # Minimum frequency for pattern
        self.patterns_cache = {}

    def _init_db(self):
        """Initialize database schema"""
        cursor = self.conn.cursor()

        # Detected patterns
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS detected_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT NOT NULL,
                pattern_name TEXT NOT NULL,
                pattern_definition TEXT,
                support REAL,
                confidence REAL,
                occurrences INTEGER DEFAULT 1,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
        ''')

        # Pattern instances
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pattern_instances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_id INTEGER NOT NULL,
                instance_data TEXT,
                context TEXT,
                observed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (pattern_id) REFERENCES detected_patterns(id)
            )
        ''')

        # Correlations
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS correlations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_a TEXT NOT NULL,
                item_b TEXT NOT NULL,
                correlation_strength REAL,
                co_occurrence_count INTEGER DEFAULT 1,
                confidence REAL,
                discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Predictions made
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prediction_type TEXT NOT NULL,
                predicted_value TEXT,
                based_on_pattern TEXT,
                confidence REAL,
                actual_value TEXT,
                was_correct INTEGER,
                predicted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                verified_at TIMESTAMP
            )
        ''')

        # Learned rules
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learned_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_type TEXT NOT NULL,
                if_condition TEXT NOT NULL,
                then_action TEXT NOT NULL,
                confidence REAL,
                support REAL,
                times_applied INTEGER DEFAULT 0,
                times_successful INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        self.conn.commit()

    # === PATTERN DETECTION ===

    def detect_sequence_pattern(self, sequence: List[Any], context: str = None) -> Optional[Dict]:
        """
        Detect repeating patterns in sequence

        Args:
            sequence: List of events/items
            context: Context for pattern

        Returns:
            Detected pattern or None
        """
        if len(sequence) < 3:
            return None

        # Look for repeating subsequences
        patterns_found = []

        for length in range(2, len(sequence) // 2 + 1):
            for start in range(len(sequence) - length + 1):
                subseq = tuple(sequence[start:start + length])

                # Count occurrences
                count = 0
                for i in range(len(sequence) - length + 1):
                    if tuple(sequence[i:i + length]) == subseq:
                        count += 1

                support = count / (len(sequence) - length + 1)

                if support >= self.min_support and count >= 2:
                    patterns_found.append({
                        'subsequence': subseq,
                        'support': support,
                        'count': count,
                        'length': length
                    })

        if not patterns_found:
            return None

        # Return strongest pattern
        best_pattern = max(patterns_found, key=lambda x: (x['support'], x['length']))

        # Store pattern
        pattern_id = self._store_pattern(
            pattern_type="sequence",
            pattern_name=f"seq_{hash(best_pattern['subsequence'])}",
            pattern_definition=json.dumps(best_pattern['subsequence']),
            support=best_pattern['support'],
            confidence=best_pattern['support']
        )

        return {
            'pattern_id': pattern_id,
            'type': 'sequence',
            'subsequence': best_pattern['subsequence'],
            'support': best_pattern['support'],
            'occurrences': best_pattern['count']
        }

    def detect_correlation(self, item_a: str, item_b: str,
                          co_occurrences: int, total_a: int, total_b: int) -> Dict:
        """
        Detect correlation between two items

        Args:
            item_a: First item
            item_b: Second item
            co_occurrences: Times they occurred together
            total_a: Total occurrences of item_a
            total_b: Total occurrences of item_b

        Returns:
            Correlation details
        """
        # Calculate lift (correlation strength)
        p_a = total_a / max(total_a + total_b, 1)
        p_b = total_b / max(total_a + total_b, 1)
        p_ab = co_occurrences / max(total_a, 1)

        if p_a * p_b > 0:
            lift = p_ab / (p_a * p_b)
        else:
            lift = 0

        # Confidence: P(B|A)
        confidence = co_occurrences / max(total_a, 1)

        # Store correlation
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO correlations
            (item_a, item_b, correlation_strength, co_occurrence_count, confidence)
            VALUES (?, ?, ?, ?, ?)
        ''', (item_a, item_b, lift, co_occurrences, confidence))
        self.conn.commit()

        return {
            'item_a': item_a,
            'item_b': item_b,
            'lift': round(lift, 3),
            'confidence': round(confidence, 3),
            'co_occurrences': co_occurrences,
            'is_correlated': lift > 1.2  # Positive correlation
        }

    def detect_anomaly(self, value: float, history: List[float],
                      threshold_std: float = 2.0) -> Dict:
        """
        Detect if value is anomalous compared to history

        Args:
            value: Current value
            history: Historical values
            threshold_std: Number of standard deviations for anomaly

        Returns:
            Anomaly detection result
        """
        if len(history) < 5:
            return {'is_anomaly': False, 'reason': 'Insufficient history'}

        # Calculate statistics
        mean = sum(history) / len(history)
        variance = sum((x - mean) ** 2 for x in history) / len(history)
        std = variance ** 0.5

        # Z-score
        if std > 0:
            z_score = (value - mean) / std
        else:
            z_score = 0

        is_anomaly = abs(z_score) > threshold_std

        return {
            'is_anomaly': is_anomaly,
            'z_score': round(z_score, 3),
            'mean': round(mean, 3),
            'std': round(std, 3),
            'deviation': round(abs(value - mean), 3),
            'severity': 'high' if abs(z_score) > 3 else 'medium' if abs(z_score) > 2 else 'low'
        }

    def detect_trend(self, values: List[Tuple[datetime, float]],
                    min_points: int = 5) -> Dict:
        """
        Detect trend in time series data

        Args:
            values: List of (timestamp, value) tuples
            min_points: Minimum points needed for trend

        Returns:
            Trend details
        """
        if len(values) < min_points:
            return {'has_trend': False, 'reason': 'Insufficient data points'}

        # Simple linear regression
        n = len(values)
        sum_x = sum(i for i in range(n))
        sum_y = sum(v[1] for v in values)
        sum_xy = sum(i * v[1] for i, v in enumerate(values))
        sum_x2 = sum(i ** 2 for i in range(n))

        # Slope
        denominator = (n * sum_x2 - sum_x ** 2)
        if denominator == 0:
            slope = 0
        else:
            slope = (n * sum_xy - sum_x * sum_y) / denominator

        # Determine trend
        if abs(slope) < 0.01:
            trend = 'flat'
        elif slope > 0:
            trend = 'increasing'
        else:
            trend = 'decreasing'

        # Calculate R-squared for trend strength
        mean_y = sum_y / n
        ss_tot = sum((v[1] - mean_y) ** 2 for v in values)
        predictions = [mean_y + slope * (i - sum_x/n) for i in range(n)]
        ss_res = sum((values[i][1] - predictions[i]) ** 2 for i in range(n))

        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        return {
            'has_trend': abs(slope) >= 0.01,
            'trend': trend,
            'slope': round(slope, 4),
            'strength': round(r_squared, 3),
            'confidence': 'high' if r_squared > 0.7 else 'medium' if r_squared > 0.4 else 'low'
        }

    # === PATTERN STORAGE ===

    def _store_pattern(self, pattern_type: str, pattern_name: str,
                      pattern_definition: str, support: float, confidence: float) -> int:
        """Store detected pattern"""
        cursor = self.conn.cursor()

        # Check if pattern exists
        cursor.execute('''
            SELECT id, occurrences FROM detected_patterns
            WHERE pattern_type = ? AND pattern_name = ?
        ''', (pattern_type, pattern_name))

        result = cursor.fetchone()

        if result:
            # Update existing pattern
            pattern_id = result['id']
            cursor.execute('''
                UPDATE detected_patterns
                SET occurrences = occurrences + 1,
                    last_seen = CURRENT_TIMESTAMP,
                    support = ?,
                    confidence = ?
                WHERE id = ?
            ''', (support, confidence, pattern_id))
        else:
            # Insert new pattern
            cursor.execute('''
                INSERT INTO detected_patterns
                (pattern_type, pattern_name, pattern_definition, support, confidence)
                VALUES (?, ?, ?, ?, ?)
            ''', (pattern_type, pattern_name, pattern_definition, support, confidence))
            pattern_id = cursor.lastrowid

        self.conn.commit()
        return pattern_id

    # === RULE LEARNING ===

    def learn_rule(self, if_condition: str, then_action: str,
                  support: float, confidence: float, rule_type: str = "general") -> int:
        """
        Learn a new rule from patterns

        Args:
            if_condition: Condition that triggers rule
            then_action: Action to take
            support: How often condition appears
            confidence: How often action succeeds when condition is true
            rule_type: Type of rule

        Returns:
            Rule ID
        """
        cursor = self.conn.cursor()

        cursor.execute('''
            INSERT INTO learned_rules
            (rule_type, if_condition, then_action, confidence, support)
            VALUES (?, ?, ?, ?, ?)
        ''', (rule_type, if_condition, then_action, confidence, support))

        self.conn.commit()
        return cursor.lastrowid

    def apply_rule(self, rule_id: int, success: bool):
        """Record rule application and outcome"""
        cursor = self.conn.cursor()

        cursor.execute('''
            UPDATE learned_rules
            SET times_applied = times_applied + 1,
                times_successful = times_successful + ?
            WHERE id = ?
        ''', (1 if success else 0, rule_id))

        self.conn.commit()

    def get_applicable_rules(self, context: str) -> List[Dict]:
        """Get rules applicable to current context"""
        cursor = self.conn.cursor()

        cursor.execute('''
            SELECT id, if_condition, then_action, confidence, times_applied, times_successful
            FROM learned_rules
            WHERE is_active = 1 AND if_condition LIKE ?
            ORDER BY confidence DESC
        ''', (f"%{context}%",))

        rules = []
        for row in cursor.fetchall():
            success_rate = row['times_successful'] / max(row['times_applied'], 1)
            rules.append({
                'rule_id': row['id'],
                'if': row['if_condition'],
                'then': row['then_action'],
                'confidence': round(row['confidence'], 3),
                'success_rate': round(success_rate, 3),
                'applications': row['times_applied']
            })

        return rules

    # === PREDICTION ===

    def predict_next(self, sequence: List[Any], based_on_pattern_id: int = None) -> Optional[Any]:
        """
        Predict next item in sequence based on learned patterns

        Args:
            sequence: Current sequence
            based_on_pattern_id: Specific pattern to use (or None to find best)

        Returns:
            Predicted next item or None
        """
        if len(sequence) < 2:
            return None

        # Find matching patterns
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id, pattern_definition, confidence
            FROM detected_patterns
            WHERE pattern_type = 'sequence' AND is_active = 1
            ORDER BY confidence DESC
        ''')

        for row in cursor.fetchall():
            pattern_seq = json.loads(row['pattern_definition'])

            # Check if current sequence ends with pattern prefix
            for i in range(len(pattern_seq) - 1):
                prefix = pattern_seq[:i+1]
                if len(sequence) >= len(prefix) and tuple(sequence[-len(prefix):]) == tuple(prefix):
                    # Predict next item
                    prediction = pattern_seq[i + 1] if i + 1 < len(pattern_seq) else None

                    if prediction:
                        # Record prediction
                        pred_id = self._record_prediction(
                            prediction_type="sequence_next",
                            predicted_value=str(prediction),
                            based_on_pattern=str(row['id']),
                            confidence=row['confidence']
                        )

                        return prediction

        return None

    def _record_prediction(self, prediction_type: str, predicted_value: str,
                          based_on_pattern: str, confidence: float) -> int:
        """Record prediction made"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO predictions
            (prediction_type, predicted_value, based_on_pattern, confidence)
            VALUES (?, ?, ?, ?)
        ''', (prediction_type, predicted_value, based_on_pattern, confidence))
        self.conn.commit()
        return cursor.lastrowid

    def verify_prediction(self, prediction_id: int, actual_value: str):
        """Verify prediction with actual outcome"""
        cursor = self.conn.cursor()

        cursor.execute('SELECT predicted_value FROM predictions WHERE id = ?', (prediction_id,))
        result = cursor.fetchone()

        if result:
            was_correct = result['predicted_value'] == actual_value

            cursor.execute('''
                UPDATE predictions
                SET actual_value = ?, was_correct = ?, verified_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (actual_value, 1 if was_correct else 0, prediction_id))

            self.conn.commit()

            return was_correct

        return None

    # === ANALYTICS ===

    def get_pattern_summary(self) -> Dict:
        """Get summary of learned patterns"""
        cursor = self.conn.cursor()

        # Count patterns by type
        cursor.execute('''
            SELECT pattern_type, COUNT(*) as count, AVG(confidence) as avg_conf
            FROM detected_patterns
            WHERE is_active = 1
            GROUP BY pattern_type
        ''')
        patterns_by_type = [dict(row) for row in cursor.fetchall()]

        # Total patterns
        cursor.execute('SELECT COUNT(*) as count FROM detected_patterns WHERE is_active = 1')
        total_patterns = cursor.fetchone()['count']

        # Prediction accuracy
        cursor.execute('''
            SELECT COUNT(*) as total,
                   SUM(was_correct) as correct
            FROM predictions
            WHERE verified_at IS NOT NULL
        ''')
        pred_result = cursor.fetchone()
        accuracy = pred_result['correct'] / max(pred_result['total'], 1) if pred_result['total'] else 0

        # Top patterns
        cursor.execute('''
            SELECT pattern_type, pattern_name, confidence, occurrences
            FROM detected_patterns
            WHERE is_active = 1
            ORDER BY occurrences DESC
            LIMIT 5
        ''')
        top_patterns = [dict(row) for row in cursor.fetchall()]

        # Learned rules
        cursor.execute('SELECT COUNT(*) as count FROM learned_rules WHERE is_active = 1')
        total_rules = cursor.fetchone()['count']

        return {
            'total_patterns': total_patterns,
            'patterns_by_type': patterns_by_type,
            'prediction_accuracy': round(accuracy, 3),
            'total_predictions': pred_result['total'],
            'top_patterns': top_patterns,
            'learned_rules': total_rules
        }

    def close(self):
        """Close database connection"""
        self.conn.close()


# === TEST CODE ===

def main():
    """Test pattern learning system"""
    print("Testing Pattern Learning System")
    print("=" * 70)

    learner = PatternLearner(min_support=0.3)

    try:
        # Test sequence pattern detection
        print("\n1. Testing sequence pattern detection...")
        sequence = ['A', 'B', 'C', 'A', 'B', 'C', 'A', 'B', 'C', 'D']
        pattern = learner.detect_sequence_pattern(sequence)

        if pattern:
            print(f"   Pattern found: {pattern['subsequence']}")
            print(f"   Support: {pattern['support']:.0%}")
            print(f"   Occurrences: {pattern['occurrences']}")

        # Test correlation detection
        print("\n2. Testing correlation detection...")
        corr = learner.detect_correlation("event_A", "event_B",
                                         co_occurrences=15, total_a=20, total_b=25)
        print(f"   Correlation: {corr['lift']:.2f}")
        print(f"   Confidence: {corr['confidence']:.0%}")
        print(f"   Correlated: {corr['is_correlated']}")

        # Test anomaly detection
        print("\n3. Testing anomaly detection...")
        history = [10.0, 11.0, 10.5, 10.8, 11.2, 10.9, 11.1]
        anomaly = learner.detect_anomaly(15.0, history)
        print(f"   Is anomaly: {anomaly['is_anomaly']}")
        print(f"   Z-score: {anomaly['z_score']}")
        print(f"   Severity: {anomaly['severity']}")

        # Test trend detection
        print("\n4. Testing trend detection...")
        from datetime import datetime, timedelta
        values = [(datetime.now() - timedelta(days=i), 100 + i * 2) for i in range(10)]
        trend = learner.detect_trend(values)
        print(f"   Trend: {trend['trend']}")
        print(f"   Slope: {trend['slope']}")
        print(f"   Confidence: {trend['confidence']}")

        # Test rule learning
        print("\n5. Testing rule learning...")
        rule_id = learner.learn_rule(
            if_condition="error_rate > 0.05",
            then_action="trigger_alert",
            support=0.7,
            confidence=0.85,
            rule_type="monitoring"
        )
        print(f"   Rule learned: ID {rule_id}")

        # Get pattern summary
        print("\n6. Pattern summary...")
        summary = learner.get_pattern_summary()
        print(f"   Total patterns: {summary['total_patterns']}")
        print(f"   Learned rules: {summary['learned_rules']}")
        print(f"   Prediction accuracy: {summary['prediction_accuracy']:.0%}")

        print(f"\n[OK] Pattern Learning System working!")
        print(f"Database: {learner.db_path}")

    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        traceback.print_exc()
    finally:
        learner.close()


if __name__ == "__main__":
    main()
