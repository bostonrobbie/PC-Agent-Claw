#!/usr/bin/env python3
"""
Predictive Analytics for Business Processes
Forecast execution times, predict failures, recommend optimizations
"""
import sys
from pathlib import Path
import sqlite3
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

sys.path.append(str(Path(__file__).parent.parent))


class PredictiveAnalytics:
    """
    Predictive analytics for business processes

    Features:
    - Predict SOP execution time
    - Forecast failure probability
    - Identify risk factors
    - Recommend optimal execution times
    - Predict resource requirements
    - Trend forecasting
    """

    def __init__(self, db_path: str = None):
        workspace = Path(__file__).parent.parent
        if db_path is None:
            db_path = str(workspace / "memory.db")

        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

    # === EXECUTION TIME PREDICTION ===

    def predict_execution_time(self, sop_id: int,
                              context: Dict = None) -> Dict:
        """
        Predict execution time for SOP

        Args:
            sop_id: SOP to predict
            context: Execution context (time of day, user, etc.)

        Returns:
            Prediction with confidence intervals
        """
        cursor = self.conn.cursor()

        # Get historical executions
        cursor.execute('''
            SELECT actual_duration_minutes, started_at, executed_by
            FROM sop_executions
            WHERE sop_id = ?
            AND actual_duration_minutes IS NOT NULL
            ORDER BY started_at DESC
            LIMIT 100
        ''', (sop_id,))

        executions = [dict(row) for row in cursor.fetchall()]

        if len(executions) < 3:
            # Not enough data, use estimated duration
            cursor.execute('''
                SELECT estimated_duration_minutes
                FROM sops
                WHERE id = ?
            ''', (sop_id,))

            estimated = cursor.fetchone()
            return {
                'predicted_duration': estimated['estimated_duration_minutes'],
                'confidence': 'low',
                'min_duration': estimated['estimated_duration_minutes'] * 0.8,
                'max_duration': estimated['estimated_duration_minutes'] * 1.5,
                'sample_size': 0
            }

        # Calculate statistics
        durations = [e['actual_duration_minutes'] for e in executions]
        mean_duration = np.mean(durations)
        std_duration = np.std(durations)

        # Adjust for context
        adjusted_duration = mean_duration

        if context:
            # Time of day adjustment
            hour = context.get('hour', datetime.now().hour)
            time_factor = self._get_time_of_day_factor(sop_id, hour)
            adjusted_duration *= time_factor

            # User adjustment
            user = context.get('user')
            if user:
                user_factor = self._get_user_factor(sop_id, user)
                adjusted_duration *= user_factor

        # Confidence intervals (95%)
        confidence_interval = 1.96 * std_duration

        return {
            'predicted_duration': round(adjusted_duration, 1),
            'confidence': self._calculate_confidence(len(executions), std_duration),
            'min_duration': round(max(0, adjusted_duration - confidence_interval), 1),
            'max_duration': round(adjusted_duration + confidence_interval, 1),
            'sample_size': len(executions),
            'historical_mean': round(mean_duration, 1),
            'std_deviation': round(std_duration, 1)
        }

    def _get_time_of_day_factor(self, sop_id: int, hour: int) -> float:
        """Calculate time-of-day adjustment factor"""
        cursor = self.conn.cursor()

        # Get executions by hour
        cursor.execute('''
            SELECT
                CAST(strftime('%H', started_at) AS INTEGER) as hour,
                AVG(actual_duration_minutes) as avg_duration
            FROM sop_executions
            WHERE sop_id = ?
            AND actual_duration_minutes IS NOT NULL
            GROUP BY hour
        ''', (sop_id,))

        hourly_durations = {row['hour']: row['avg_duration'] for row in cursor.fetchall()}

        if not hourly_durations:
            return 1.0

        overall_avg = np.mean(list(hourly_durations.values()))
        hour_avg = hourly_durations.get(hour, overall_avg)

        return hour_avg / overall_avg if overall_avg > 0 else 1.0

    def _get_user_factor(self, sop_id: int, user: str) -> float:
        """Calculate user performance factor"""
        cursor = self.conn.cursor()

        # User's average vs overall average
        cursor.execute('''
            SELECT AVG(actual_duration_minutes) as user_avg
            FROM sop_executions
            WHERE sop_id = ? AND executed_by = ?
            AND actual_duration_minutes IS NOT NULL
        ''', (sop_id, user))

        user_result = cursor.fetchone()

        cursor.execute('''
            SELECT AVG(actual_duration_minutes) as overall_avg
            FROM sop_executions
            WHERE sop_id = ?
            AND actual_duration_minutes IS NOT NULL
        ''', (sop_id,))

        overall_result = cursor.fetchone()

        if user_result and overall_result:
            user_avg = user_result['user_avg']
            overall_avg = overall_result['overall_avg']

            if user_avg and overall_avg:
                return user_avg / overall_avg

        return 1.0

    def _calculate_confidence(self, sample_size: int, std_dev: float) -> str:
        """Calculate confidence level"""
        if sample_size < 5:
            return 'low'
        elif sample_size < 20:
            return 'medium'
        elif std_dev / sample_size > 0.3:  # High variance
            return 'medium'
        else:
            return 'high'

    # === FAILURE PREDICTION ===

    def predict_failure_probability(self, sop_id: int,
                                   context: Dict = None) -> Dict:
        """
        Predict probability of execution failure

        Args:
            sop_id: SOP to analyze
            context: Execution context

        Returns:
            Failure probability and risk factors
        """
        cursor = self.conn.cursor()

        # Get execution history
        cursor.execute('''
            SELECT success, executed_by, started_at
            FROM sop_executions
            WHERE sop_id = ?
            ORDER BY started_at DESC
            LIMIT 100
        ''', (sop_id,))

        executions = [dict(row) for row in cursor.fetchall()]

        if not executions:
            return {
                'failure_probability': 0.0,
                'confidence': 'low',
                'risk_factors': []
            }

        # Calculate base failure rate
        failures = sum(1 for e in executions if not e['success'])
        base_rate = failures / len(executions)

        # Identify risk factors
        risk_factors = []
        adjusted_probability = base_rate

        # Recent trend
        recent = executions[:10]
        if recent:
            recent_failures = sum(1 for e in recent if not e['success'])
            recent_rate = recent_failures / len(recent)

            if recent_rate > base_rate * 1.5:
                risk_factors.append({
                    'factor': 'Recent Trend',
                    'description': 'Increased failure rate in recent executions',
                    'impact': 'high'
                })
                adjusted_probability *= 1.3

        # User history
        if context and 'user' in context:
            user = context['user']
            user_executions = [e for e in executions if e['executed_by'] == user]

            if user_executions:
                user_failures = sum(1 for e in user_executions if not e['success'])
                user_rate = user_failures / len(user_executions)

                if user_rate > base_rate * 1.2:
                    risk_factors.append({
                        'factor': 'User Performance',
                        'description': f'User {user} has higher failure rate',
                        'impact': 'medium'
                    })
                    adjusted_probability *= 1.2

        # Time-based patterns
        if context and 'hour' in context:
            hour = context['hour']
            hour_pattern = self._analyze_hour_pattern(sop_id, hour)

            if hour_pattern['failure_rate'] > base_rate * 1.3:
                risk_factors.append({
                    'factor': 'Time of Day',
                    'description': f'Higher failure rate at hour {hour}',
                    'impact': 'medium'
                })
                adjusted_probability *= 1.15

        return {
            'failure_probability': min(1.0, round(adjusted_probability, 3)),
            'base_rate': round(base_rate, 3),
            'confidence': self._calculate_confidence(len(executions), 0),
            'risk_factors': risk_factors,
            'sample_size': len(executions)
        }

    def _analyze_hour_pattern(self, sop_id: int, hour: int) -> Dict:
        """Analyze failure patterns by hour"""
        cursor = self.conn.cursor()

        cursor.execute('''
            SELECT success
            FROM sop_executions
            WHERE sop_id = ?
            AND CAST(strftime('%H', started_at) AS INTEGER) = ?
        ''', (sop_id, hour))

        executions = cursor.fetchall()

        if not executions:
            return {'failure_rate': 0.0}

        failures = sum(1 for e in executions if not e['success'])
        return {'failure_rate': failures / len(executions)}

    # === OPTIMAL SCHEDULING ===

    def recommend_execution_time(self, sop_id: int, window_hours: int = 24) -> Dict:
        """
        Recommend optimal time to execute SOP

        Args:
            sop_id: SOP to schedule
            window_hours: Time window to consider

        Returns:
            Recommended execution times
        """
        cursor = self.conn.cursor()

        # Analyze historical performance by hour
        cursor.execute('''
            SELECT
                CAST(strftime('%H', started_at) AS INTEGER) as hour,
                AVG(actual_duration_minutes) as avg_duration,
                AVG(CASE WHEN success = 1 THEN 1.0 ELSE 0.0 END) as success_rate,
                COUNT(*) as count
            FROM sop_executions
            WHERE sop_id = ?
            GROUP BY hour
            HAVING count >= 3
            ORDER BY success_rate DESC, avg_duration ASC
        ''', (sop_id,))

        hourly_stats = [dict(row) for row in cursor.fetchall()]

        if not hourly_stats:
            return {
                'recommended_hours': [],
                'confidence': 'low',
                'reason': 'Insufficient historical data'
            }

        # Calculate score for each hour (higher is better)
        for stat in hourly_stats:
            # Success rate (60%) + Speed (40%)
            max_duration = max(s['avg_duration'] for s in hourly_stats)
            speed_score = 1 - (stat['avg_duration'] / max_duration)

            stat['score'] = (stat['success_rate'] * 0.6 + speed_score * 0.4)

        # Sort by score
        hourly_stats.sort(key=lambda x: x['score'], reverse=True)

        # Top 3 hours
        recommendations = []
        for stat in hourly_stats[:3]:
            recommendations.append({
                'hour': stat['hour'],
                'success_rate': round(stat['success_rate'], 2),
                'avg_duration': round(stat['avg_duration'], 1),
                'score': round(stat['score'], 2)
            })

        return {
            'recommended_hours': recommendations,
            'confidence': 'high' if len(hourly_stats) >= 10 else 'medium',
            'reason': 'Based on historical success rate and execution speed'
        }

    # === TREND FORECASTING ===

    def forecast_execution_trend(self, sop_id: int, days_ahead: int = 7) -> Dict:
        """
        Forecast future execution volume

        Args:
            sop_id: SOP to forecast
            days_ahead: Days to forecast

        Returns:
            Forecasted execution counts
        """
        cursor = self.conn.cursor()

        # Get historical daily counts
        cursor.execute('''
            SELECT
                DATE(started_at) as date,
                COUNT(*) as count
            FROM sop_executions
            WHERE sop_id = ?
            AND started_at >= DATE('now', '-30 days')
            GROUP BY DATE(started_at)
            ORDER BY date
        ''', (sop_id,))

        daily_counts = [dict(row) for row in cursor.fetchall()]

        if len(daily_counts) < 7:
            return {
                'forecast': [],
                'confidence': 'low',
                'method': 'insufficient_data'
            }

        # Simple moving average forecast
        counts = [d['count'] for d in daily_counts]
        moving_avg = np.mean(counts[-7:])  # Last week average

        # Calculate trend
        if len(counts) >= 14:
            recent_avg = np.mean(counts[-7:])
            prior_avg = np.mean(counts[-14:-7])
            trend = (recent_avg - prior_avg) / prior_avg if prior_avg > 0 else 0
        else:
            trend = 0

        # Forecast
        forecast = []
        for i in range(1, days_ahead + 1):
            predicted = moving_avg * (1 + trend * i / 7)
            forecast.append({
                'days_ahead': i,
                'predicted_executions': round(max(0, predicted), 1)
            })

        return {
            'forecast': forecast,
            'current_avg': round(moving_avg, 1),
            'trend': round(trend, 3),
            'confidence': 'medium' if len(counts) >= 14 else 'low',
            'method': 'moving_average_with_trend'
        }

    def close(self):
        """Close database connection"""
        self.conn.close()


# === TEST CODE ===

def main():
    """Test predictive analytics"""
    print("=" * 70)
    print("Predictive Analytics for Business Processes")
    print("=" * 70)

    analytics = PredictiveAnalytics()

    try:
        print("\n1. Predicting execution time...")
        prediction = analytics.predict_execution_time(
            sop_id=1,
            context={'hour': 14, 'user': 'test_user'}
        )
        print(f"   Predicted: {prediction['predicted_duration']} min")
        print(f"   Range: {prediction['min_duration']}-{prediction['max_duration']} min")
        print(f"   Confidence: {prediction['confidence']}")

        print("\n2. Predicting failure probability...")
        failure = analytics.predict_failure_probability(
            sop_id=1,
            context={'hour': 22, 'user': 'test_user'}
        )
        print(f"   Failure probability: {failure['failure_probability']:.1%}")
        print(f"   Risk factors: {len(failure['risk_factors'])}")

        print("\n3. Recommending execution time...")
        recommendation = analytics.recommend_execution_time(sop_id=1)
        print(f"   Confidence: {recommendation['confidence']}")
        if recommendation['recommended_hours']:
            top = recommendation['recommended_hours'][0]
            print(f"   Best time: {top['hour']}:00 (score: {top['score']})")

        print("\n4. Forecasting execution trend...")
        forecast = analytics.forecast_execution_trend(sop_id=1, days_ahead=7)
        print(f"   Method: {forecast['method']}")
        print(f"   Current avg: {forecast.get('current_avg', 0)} executions/day")

        print(f"\n[OK] Predictive Analytics working!")

    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        analytics.close()


if __name__ == "__main__":
    main()
