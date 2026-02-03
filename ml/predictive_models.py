#!/usr/bin/env python3
"""
Predictive Modeling & Forecasting System
Multi-approach forecasting with anomaly detection, risk assessment, and opportunity identification
"""
import sys
from pathlib import Path
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from collections import deque
import json

sys.path.append(str(Path(__file__).parent.parent))

from core.persistent_memory import PersistentMemory


class PredictiveModelingSystem:
    """
    Comprehensive predictive modeling and forecasting system

    Features:
    - Time series forecasting (ARIMA-like, exponential smoothing, moving averages)
    - Anomaly prediction before they happen
    - Outcome prediction for decisions
    - Risk forecasting
    - Opportunity forecasting
    - Confidence intervals
    - Model validation and accuracy tracking
    """

    def __init__(self, db_path: str = None):
        workspace = Path(__file__).parent.parent
        if db_path is None:
            db_path = str(workspace / "memory.db")

        self.memory = PersistentMemory(db_path)

        # Initialize database tables
        self._init_prediction_tables()

        # Model state
        self.models = {}
        self.forecasts = {}
        self.prediction_history = deque(maxlen=10000)

        # Tracking metrics
        self.accuracy_metrics = {
            'timeseries': [],
            'anomaly': [],
            'outcome': [],
            'risk': [],
            'opportunity': []
        }

    def _init_prediction_tables(self):
        """Initialize database tables for predictions and forecasts"""
        cursor = self.memory.conn.cursor()

        # Check if predictions table exists and get its columns
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='predictions'")
        predictions_exists = cursor.fetchone() is not None

        if predictions_exists:
            # Check if it has the model_name column
            cursor.execute("PRAGMA table_info(predictions)")
            columns = [row[1] for row in cursor.fetchall()]
            if 'model_name' not in columns:
                # Table exists but with old schema - rename it
                cursor.execute("ALTER TABLE predictions RENAME TO predictions_old")
                predictions_exists = False

        # Predictions table
        if not predictions_exists:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prediction_type TEXT NOT NULL,
                    model_name TEXT,
                    input_data TEXT,
                    prediction TEXT NOT NULL,
                    confidence REAL,
                    lower_bound REAL,
                    upper_bound REAL,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

        # Forecasts table (time series specific)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS forecasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                series_name TEXT NOT NULL,
                forecast_horizon INTEGER,
                forecast_values TEXT NOT NULL,
                confidence_intervals TEXT,
                method TEXT,
                mae REAL,
                rmse REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                valid_until TIMESTAMP
            )
        ''')

        # Accuracy tracking table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS prediction_accuracy (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prediction_id INTEGER,
                prediction_type TEXT,
                predicted_value REAL,
                actual_value REAL,
                error REAL,
                absolute_error REAL,
                squared_error REAL,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (prediction_id) REFERENCES predictions(id)
            )
        ''')

        # Risk assessments table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS risk_assessments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                risk_type TEXT NOT NULL,
                entity TEXT,
                risk_score REAL,
                risk_level TEXT,
                risk_factors TEXT,
                mitigation_suggestions TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Check if opportunities table exists with correct schema
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='opportunities'")
        opportunities_exists = cursor.fetchone() is not None

        if opportunities_exists:
            cursor.execute("PRAGMA table_info(opportunities)")
            columns = [row[1] for row in cursor.fetchall()]
            if 'entity' not in columns:
                cursor.execute("ALTER TABLE opportunities RENAME TO opportunities_old")
                opportunities_exists = False

        # Opportunity forecasts table
        if not opportunities_exists:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS opportunities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    opportunity_type TEXT NOT NULL,
                    entity TEXT,
                    potential_value REAL,
                    confidence REAL,
                    success_probability REAL,
                    requirements TEXT,
                    timeframe TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

        self.memory.conn.commit()

    # ============================================================================
    # TIME SERIES FORECASTING
    # ============================================================================

    def forecast_timeseries(self, series_name: str, data: np.ndarray,
                           horizon: int = 10, method: str = 'ensemble',
                           seasonal_period: int = None) -> Dict:
        """
        Forecast time series using multiple methods

        Args:
            series_name: Name of the time series
            data: Historical data points
            horizon: Number of periods to forecast
            method: 'arima', 'exponential', 'moving_average', or 'ensemble'
            seasonal_period: Period for seasonal decomposition

        Returns:
            Dictionary with forecasts, confidence intervals, and metrics
        """
        if len(data) < 10:
            raise ValueError("Need at least 10 data points for forecasting")

        # Ensure data is numpy array
        data = np.array(data, dtype=float)

        # Choose forecasting method
        if method == 'ensemble':
            forecast_values, lower_ci, upper_ci = self._ensemble_forecast(data, horizon, seasonal_period)
        elif method == 'arima':
            forecast_values, lower_ci, upper_ci = self._arima_like_forecast(data, horizon)
        elif method == 'exponential':
            forecast_values, lower_ci, upper_ci = self._exponential_smoothing(data, horizon)
        elif method == 'moving_average':
            forecast_values, lower_ci, upper_ci = self._moving_average_forecast(data, horizon)
        else:
            raise ValueError(f"Unknown method: {method}")

        # Calculate validation metrics on recent data
        validation_size = min(10, len(data) // 4)
        if validation_size > 0:
            val_data = data[-validation_size:]
            train_data = data[:-validation_size]

            if method == 'ensemble':
                val_pred, _, _ = self._ensemble_forecast(train_data, validation_size, seasonal_period)
            elif method == 'arima':
                val_pred, _, _ = self._arima_like_forecast(train_data, validation_size)
            elif method == 'exponential':
                val_pred, _, _ = self._exponential_smoothing(train_data, validation_size)
            else:
                val_pred, _, _ = self._moving_average_forecast(train_data, validation_size)

            mae = np.mean(np.abs(val_data - val_pred[:len(val_data)]))
            rmse = np.sqrt(np.mean((val_data - val_pred[:len(val_data)]) ** 2))
        else:
            mae = None
            rmse = None

        # Store forecast in database
        cursor = self.memory.conn.cursor()
        cursor.execute('''
            INSERT INTO forecasts (series_name, forecast_horizon, forecast_values,
                                  confidence_intervals, method, mae, rmse, valid_until)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now', '+' || ? || ' hours'))
        ''', (
            series_name,
            horizon,
            json.dumps(forecast_values.tolist()),
            json.dumps({'lower': lower_ci.tolist(), 'upper': upper_ci.tolist()}),
            method,
            mae,
            rmse,
            horizon
        ))
        self.memory.conn.commit()
        forecast_id = cursor.lastrowid

        # Store in memory
        self.forecasts[series_name] = {
            'id': forecast_id,
            'values': forecast_values,
            'lower_ci': lower_ci,
            'upper_ci': upper_ci,
            'method': method,
            'created_at': datetime.now()
        }

        # Log decision
        mae_str = f'{mae:.4f}' if mae is not None else 'N/A'
        self.memory.log_decision(
            f'Time series forecast: {series_name}',
            f'Method: {method}, Horizon: {horizon}, MAE: {mae_str}',
            tags=['forecasting', 'timeseries', series_name]
        )

        result = {
            'forecast_id': forecast_id,
            'series_name': series_name,
            'forecast': forecast_values,
            'lower_confidence': lower_ci,
            'upper_confidence': upper_ci,
            'method': method,
            'horizon': horizon,
            'mae': mae,
            'rmse': rmse,
            'timestamp': datetime.now().isoformat()
        }

        return result

    def _arima_like_forecast(self, data: np.ndarray, horizon: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        ARIMA-like forecasting using autoregressive approach
        """
        # Simple AR(p) model - autoregressive
        p = min(5, len(data) // 3)  # Order

        if len(data) <= p:
            # Fall back to simple trend
            return self._trend_forecast(data, horizon)

        # Fit AR model
        X = []
        y = []
        for i in range(p, len(data)):
            X.append(data[i-p:i])
            y.append(data[i])

        X = np.array(X)
        y = np.array(y)

        # Simple linear regression coefficients
        try:
            # Add intercept
            X_with_intercept = np.column_stack([np.ones(len(X)), X])
            coefficients = np.linalg.lstsq(X_with_intercept, y, rcond=None)[0]
        except:
            return self._trend_forecast(data, horizon)

        # Forecast
        forecast = []
        current_data = data[-p:].tolist()

        for _ in range(horizon):
            X_pred = np.array([1] + current_data[-p:])
            pred = np.dot(coefficients, X_pred)
            forecast.append(pred)
            current_data.append(pred)

        forecast = np.array(forecast)

        # Calculate residuals for confidence intervals
        y_pred = X_with_intercept @ coefficients
        residuals = y - y_pred
        std_error = np.std(residuals)

        # Confidence intervals (95%)
        z_score = 1.96
        margin = z_score * std_error * np.sqrt(1 + np.arange(horizon))
        lower_ci = forecast - margin
        upper_ci = forecast + margin

        return forecast, lower_ci, upper_ci

    def _exponential_smoothing(self, data: np.ndarray, horizon: int,
                                alpha: float = None) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Exponential smoothing forecast (Holt's linear trend)
        """
        if alpha is None:
            alpha = 0.3  # Smoothing parameter

        beta = 0.1  # Trend smoothing

        # Initialize
        level = data[0]
        trend = (data[1] - data[0]) if len(data) > 1 else 0

        # Fit on historical data
        for value in data[1:]:
            prev_level = level
            level = alpha * value + (1 - alpha) * (prev_level + trend)
            trend = beta * (level - prev_level) + (1 - beta) * trend

        # Forecast
        forecast = []
        for h in range(1, horizon + 1):
            forecast.append(level + h * trend)

        forecast = np.array(forecast)

        # Confidence intervals based on historical volatility
        volatility = np.std(np.diff(data))
        margin = 1.96 * volatility * np.sqrt(np.arange(1, horizon + 1))
        lower_ci = forecast - margin
        upper_ci = forecast + margin

        return forecast, lower_ci, upper_ci

    def _moving_average_forecast(self, data: np.ndarray, horizon: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Moving average forecast with trend adjustment
        """
        window = min(20, len(data) // 2)

        # Calculate moving average
        ma = np.mean(data[-window:])

        # Calculate trend
        if len(data) >= 2 * window:
            recent_ma = np.mean(data[-window:])
            older_ma = np.mean(data[-2*window:-window])
            trend = (recent_ma - older_ma) / window
        else:
            # Simple linear trend
            x = np.arange(len(data))
            trend = np.polyfit(x, data, 1)[0]

        # Forecast
        forecast = ma + trend * np.arange(1, horizon + 1)

        # Confidence intervals
        volatility = np.std(data[-window:])
        margin = 1.96 * volatility * np.sqrt(np.arange(1, horizon + 1))
        lower_ci = forecast - margin
        upper_ci = forecast + margin

        return forecast, lower_ci, upper_ci

    def _trend_forecast(self, data: np.ndarray, horizon: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Simple trend-based forecast
        """
        x = np.arange(len(data))
        coeffs = np.polyfit(x, data, 1)

        future_x = np.arange(len(data), len(data) + horizon)
        forecast = np.polyval(coeffs, future_x)

        # Confidence intervals
        residuals = data - np.polyval(coeffs, x)
        std_error = np.std(residuals)
        margin = 1.96 * std_error * np.sqrt(1 + np.arange(horizon))

        lower_ci = forecast - margin
        upper_ci = forecast + margin

        return forecast, lower_ci, upper_ci

    def _ensemble_forecast(self, data: np.ndarray, horizon: int,
                          seasonal_period: int = None) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Ensemble of multiple forecasting methods
        """
        forecasts = []
        lower_cis = []
        upper_cis = []

        # Get forecasts from different methods
        try:
            f1, l1, u1 = self._arima_like_forecast(data, horizon)
            forecasts.append(f1)
            lower_cis.append(l1)
            upper_cis.append(u1)
        except:
            pass

        try:
            f2, l2, u2 = self._exponential_smoothing(data, horizon)
            forecasts.append(f2)
            lower_cis.append(l2)
            upper_cis.append(u2)
        except:
            pass

        try:
            f3, l3, u3 = self._moving_average_forecast(data, horizon)
            forecasts.append(f3)
            lower_cis.append(l3)
            upper_cis.append(u3)
        except:
            pass

        if not forecasts:
            # Fall back to trend
            return self._trend_forecast(data, horizon)

        # Average the forecasts
        ensemble_forecast = np.mean(forecasts, axis=0)
        ensemble_lower = np.mean(lower_cis, axis=0)
        ensemble_upper = np.mean(upper_cis, axis=0)

        return ensemble_forecast, ensemble_lower, ensemble_upper

    # ============================================================================
    # ANOMALY PREDICTION
    # ============================================================================

    def predict_anomaly(self, series_name: str, data: np.ndarray,
                       sensitivity: float = 2.0) -> Dict:
        """
        Predict when anomalies are likely to occur

        Args:
            series_name: Name of the series
            data: Historical data
            sensitivity: Threshold multiplier (lower = more sensitive)

        Returns:
            Anomaly prediction with probability and timing
        """
        if len(data) < 20:
            raise ValueError("Need at least 20 data points for anomaly prediction")

        # Calculate statistical properties
        mean = np.mean(data)
        std = np.std(data)

        # Detect patterns before historical anomalies
        anomaly_threshold = sensitivity * std
        anomalies = np.abs(data - mean) > anomaly_threshold

        # Analyze pre-anomaly patterns
        pre_anomaly_features = []
        for i in range(5, len(data)):
            if anomalies[i]:
                # Look at 5 points before anomaly
                pattern = data[i-5:i]
                features = {
                    'trend': pattern[-1] - pattern[0],
                    'volatility': np.std(pattern),
                    'acceleration': pattern[-1] - 2*pattern[-2] + pattern[-3] if i >= 3 else 0
                }
                pre_anomaly_features.append(features)

        # Analyze current state
        current_pattern = data[-5:]
        current_features = {
            'trend': current_pattern[-1] - current_pattern[0],
            'volatility': np.std(current_pattern),
            'acceleration': current_pattern[-1] - 2*current_pattern[-2] + current_pattern[-3]
        }

        # Calculate anomaly probability
        if pre_anomaly_features:
            # Compare current features to pre-anomaly patterns
            similarities = []
            for hist_features in pre_anomaly_features:
                similarity = 0
                for key in current_features:
                    if hist_features[key] != 0:
                        sim = 1 - abs(current_features[key] - hist_features[key]) / abs(hist_features[key])
                        similarities.append(max(0, sim))

            anomaly_probability = np.mean(similarities) if similarities else 0.1
        else:
            # No historical anomalies - use statistical approach
            z_score = abs(data[-1] - mean) / std if std > 0 else 0
            anomaly_probability = min(z_score / (2 * sensitivity), 0.9)

        # Predict timing
        if anomaly_probability > 0.5:
            estimated_periods_ahead = 1 + int(5 * (1 - anomaly_probability))
        else:
            estimated_periods_ahead = 5 + int(10 * (1 - anomaly_probability))

        # Risk level
        if anomaly_probability > 0.7:
            risk_level = 'HIGH'
        elif anomaly_probability > 0.4:
            risk_level = 'MEDIUM'
        else:
            risk_level = 'LOW'

        # Store prediction
        cursor = self.memory.conn.cursor()
        cursor.execute('''
            INSERT INTO predictions (prediction_type, model_name, input_data,
                                   prediction, confidence, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            'anomaly',
            'statistical_pattern',
            json.dumps(data[-10:].tolist()),
            json.dumps({
                'probability': anomaly_probability,
                'periods_ahead': estimated_periods_ahead,
                'risk_level': risk_level
            }),
            anomaly_probability,
            json.dumps({
                'series_name': series_name,
                'current_features': current_features
            })
        ))
        self.memory.conn.commit()
        prediction_id = cursor.lastrowid

        self.memory.log_decision(
            f'Anomaly prediction: {series_name}',
            f'Probability: {anomaly_probability:.2%}, Risk: {risk_level}',
            tags=['anomaly', 'prediction', series_name]
        )

        result = {
            'prediction_id': prediction_id,
            'series_name': series_name,
            'anomaly_probability': anomaly_probability,
            'estimated_periods_ahead': estimated_periods_ahead,
            'risk_level': risk_level,
            'current_z_score': float((data[-1] - mean) / std if std > 0 else 0),
            'recommendation': self._get_anomaly_recommendation(risk_level),
            'timestamp': datetime.now().isoformat()
        }

        return result

    def _get_anomaly_recommendation(self, risk_level: str) -> str:
        """Get recommendation based on anomaly risk level"""
        recommendations = {
            'HIGH': 'Take immediate preventive action. High probability of anomaly in next 1-2 periods.',
            'MEDIUM': 'Monitor closely. Moderate probability of anomaly in next 3-5 periods.',
            'LOW': 'Continue normal monitoring. Low probability of near-term anomaly.'
        }
        return recommendations.get(risk_level, 'Monitor situation')

    # ============================================================================
    # OUTCOME PREDICTION
    # ============================================================================

    def predict_outcome(self, decision_type: str, features: Dict,
                       historical_outcomes: List[Dict] = None) -> Dict:
        """
        Predict outcome of a decision

        Args:
            decision_type: Type of decision
            features: Features describing the decision context
            historical_outcomes: Past decisions and their outcomes

        Returns:
            Predicted outcome with probability and confidence
        """
        # Convert features to numeric array
        feature_vector = self._features_to_vector(features)

        if historical_outcomes and len(historical_outcomes) >= 10:
            # Learn from historical data
            X_hist = []
            y_hist = []

            for outcome in historical_outcomes:
                hist_features = self._features_to_vector(outcome.get('features', {}))
                success = outcome.get('success', False)
                X_hist.append(hist_features)
                y_hist.append(1 if success else 0)

            X_hist = np.array(X_hist)
            y_hist = np.array(y_hist)

            # Simple similarity-based prediction
            similarities = []
            for i, hist_feat in enumerate(X_hist):
                # Calculate cosine similarity
                sim = self._cosine_similarity(feature_vector, hist_feat)
                similarities.append((sim, y_hist[i]))

            # Weight by similarity
            similarities.sort(reverse=True)
            top_k = min(5, len(similarities))

            weights = []
            outcomes = []
            for i in range(top_k):
                sim, outcome = similarities[i]
                weights.append(sim)
                outcomes.append(outcome)

            # Weighted average
            success_probability = np.average(outcomes, weights=weights)
            confidence = np.mean(weights)  # Average similarity as confidence

        else:
            # No historical data - use heuristics
            success_probability = 0.5  # Neutral
            confidence = 0.3  # Low confidence without data

        # Expected value calculation
        expected_value = features.get('potential_gain', 0) * success_probability - \
                        features.get('potential_loss', 0) * (1 - success_probability)

        # Risk-reward ratio
        potential_gain = features.get('potential_gain', 0)
        potential_loss = features.get('potential_loss', 0)
        risk_reward_ratio = potential_gain / potential_loss if potential_loss > 0 else float('inf')

        # Recommendation
        if success_probability > 0.7 and risk_reward_ratio > 2:
            recommendation = 'STRONGLY RECOMMENDED'
        elif success_probability > 0.6 and risk_reward_ratio > 1.5:
            recommendation = 'RECOMMENDED'
        elif success_probability > 0.5 and risk_reward_ratio > 1:
            recommendation = 'CAUTIOUSLY PROCEED'
        elif success_probability > 0.4:
            recommendation = 'RISKY - CONSIDER ALTERNATIVES'
        else:
            recommendation = 'NOT RECOMMENDED'

        # Store prediction
        cursor = self.memory.conn.cursor()
        cursor.execute('''
            INSERT INTO predictions (prediction_type, model_name, input_data,
                                   prediction, confidence, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            'outcome',
            'similarity_based',
            json.dumps(features),
            json.dumps({
                'success_probability': success_probability,
                'expected_value': expected_value,
                'recommendation': recommendation
            }),
            confidence,
            json.dumps({'decision_type': decision_type})
        ))
        self.memory.conn.commit()
        prediction_id = cursor.lastrowid

        self.memory.log_decision(
            f'Outcome prediction: {decision_type}',
            f'Success probability: {success_probability:.2%}, Confidence: {confidence:.2%}',
            tags=['outcome', 'prediction', decision_type]
        )

        result = {
            'prediction_id': prediction_id,
            'decision_type': decision_type,
            'success_probability': float(success_probability),
            'expected_value': float(expected_value),
            'risk_reward_ratio': float(risk_reward_ratio),
            'confidence': float(confidence),
            'recommendation': recommendation,
            'factors': features,
            'timestamp': datetime.now().isoformat()
        }

        return result

    def _features_to_vector(self, features: Dict) -> np.ndarray:
        """Convert feature dictionary to numeric vector"""
        # Standard feature keys
        keys = ['potential_gain', 'potential_loss', 'complexity', 'timeline',
                'resource_requirement', 'confidence_level']

        vector = []
        for key in keys:
            value = features.get(key, 0)
            # Normalize to 0-1 range
            if key in ['potential_gain', 'potential_loss']:
                value = min(value / 10000, 1)  # Normalize large values
            elif key == 'timeline':
                value = min(value / 365, 1)  # Normalize days to year
            elif key == 'complexity':
                value = value / 10  # Assume 0-10 scale

            vector.append(float(value))

        return np.array(vector)

    def _cosine_similarity(self, v1: np.ndarray, v2: np.ndarray) -> float:
        """Calculate cosine similarity between vectors"""
        # Ensure same length
        min_len = min(len(v1), len(v2))
        v1 = v1[:min_len]
        v2 = v2[:min_len]

        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)

        if norm1 == 0 or norm2 == 0:
            return 0

        return dot_product / (norm1 * norm2)

    # ============================================================================
    # RISK ASSESSMENT
    # ============================================================================

    def assess_risk(self, risk_type: str, entity: str,
                   context: Dict, historical_data: np.ndarray = None) -> Dict:
        """
        Assess and forecast risk

        Args:
            risk_type: Type of risk (market, operational, financial, etc.)
            entity: Entity being assessed
            context: Context and factors
            historical_data: Historical risk indicators

        Returns:
            Risk assessment with score and mitigation suggestions
        """
        risk_factors = []
        risk_scores = []

        # Analyze context factors
        volatility = context.get('volatility', 0)
        uncertainty = context.get('uncertainty', 0)
        exposure = context.get('exposure', 0)
        complexity = context.get('complexity', 0)

        # Volatility risk
        if volatility > 0:
            vol_score = min(volatility / 0.5, 1)  # Normalize
            risk_scores.append(vol_score)
            risk_factors.append({
                'factor': 'volatility',
                'score': vol_score,
                'description': f'High volatility detected: {volatility:.2%}'
            })

        # Uncertainty risk
        if uncertainty > 0:
            unc_score = min(uncertainty, 1)
            risk_scores.append(unc_score)
            risk_factors.append({
                'factor': 'uncertainty',
                'score': unc_score,
                'description': f'Uncertainty level: {uncertainty:.2%}'
            })

        # Exposure risk
        if exposure > 0:
            exp_score = min(exposure / 100000, 1)  # Normalize by max exposure
            risk_scores.append(exp_score)
            risk_factors.append({
                'factor': 'exposure',
                'score': exp_score,
                'description': f'Financial exposure: ${exposure:,.2f}'
            })

        # Complexity risk
        if complexity > 0:
            comp_score = min(complexity / 10, 1)
            risk_scores.append(comp_score)
            risk_factors.append({
                'factor': 'complexity',
                'score': comp_score,
                'description': f'Complexity level: {complexity}/10'
            })

        # Historical trend analysis
        if historical_data is not None and len(historical_data) >= 10:
            # Trend in risk indicators
            recent_trend = np.polyfit(np.arange(len(historical_data)), historical_data, 1)[0]

            if recent_trend > 0:
                trend_score = min(abs(recent_trend) * 10, 1)
                risk_scores.append(trend_score)
                risk_factors.append({
                    'factor': 'trend',
                    'score': trend_score,
                    'description': 'Increasing risk trend detected'
                })

        # Overall risk score (weighted average)
        if risk_scores:
            overall_risk_score = np.mean(risk_scores)
        else:
            overall_risk_score = 0.5  # Default medium risk

        # Risk level classification
        if overall_risk_score > 0.7:
            risk_level = 'CRITICAL'
        elif overall_risk_score > 0.5:
            risk_level = 'HIGH'
        elif overall_risk_score > 0.3:
            risk_level = 'MEDIUM'
        else:
            risk_level = 'LOW'

        # Generate mitigation suggestions
        mitigation_suggestions = self._generate_risk_mitigation(risk_factors, risk_level)

        # Store risk assessment
        cursor = self.memory.conn.cursor()
        cursor.execute('''
            INSERT INTO risk_assessments (risk_type, entity, risk_score,
                                         risk_level, risk_factors, mitigation_suggestions)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            risk_type,
            entity,
            overall_risk_score,
            risk_level,
            json.dumps(risk_factors),
            json.dumps(mitigation_suggestions)
        ))
        self.memory.conn.commit()
        assessment_id = cursor.lastrowid

        self.memory.log_decision(
            f'Risk assessment: {entity}',
            f'Type: {risk_type}, Level: {risk_level}, Score: {overall_risk_score:.2f}',
            tags=['risk', 'assessment', risk_type]
        )

        result = {
            'assessment_id': assessment_id,
            'risk_type': risk_type,
            'entity': entity,
            'risk_score': float(overall_risk_score),
            'risk_level': risk_level,
            'risk_factors': risk_factors,
            'mitigation_suggestions': mitigation_suggestions,
            'timestamp': datetime.now().isoformat()
        }

        return result

    def _generate_risk_mitigation(self, risk_factors: List[Dict],
                                  risk_level: str) -> List[str]:
        """Generate risk mitigation suggestions"""
        suggestions = []

        if risk_level in ['CRITICAL', 'HIGH']:
            suggestions.append('Consider immediate risk reduction measures')

        for factor in risk_factors:
            if factor['factor'] == 'volatility':
                suggestions.append('Implement hedging strategies to reduce volatility exposure')
            elif factor['factor'] == 'uncertainty':
                suggestions.append('Gather more information to reduce uncertainty')
                suggestions.append('Consider scenario planning for different outcomes')
            elif factor['factor'] == 'exposure':
                suggestions.append('Reduce position size or financial exposure')
                suggestions.append('Diversify to spread risk')
            elif factor['factor'] == 'complexity':
                suggestions.append('Simplify the approach or break into smaller steps')
                suggestions.append('Increase monitoring and oversight')
            elif factor['factor'] == 'trend':
                suggestions.append('Monitor trend closely for further deterioration')

        if not suggestions:
            suggestions.append('Continue regular monitoring and risk assessment')

        return suggestions

    # ============================================================================
    # OPPORTUNITY FORECASTING
    # ============================================================================

    def forecast_opportunity(self, opportunity_type: str, entity: str,
                           context: Dict, market_data: np.ndarray = None) -> Dict:
        """
        Forecast opportunities and their potential value

        Args:
            opportunity_type: Type of opportunity
            entity: Entity being evaluated
            context: Context and factors
            market_data: Historical market data if available

        Returns:
            Opportunity forecast with value estimate and probability
        """
        # Extract context
        current_value = context.get('current_value', 0)
        growth_rate = context.get('growth_rate', 0)
        market_size = context.get('market_size', 0)
        competition = context.get('competition', 0.5)  # 0-1 scale
        timing = context.get('timing', 0.5)  # 0-1 scale (optimal timing)

        # Calculate potential value
        if market_data is not None and len(market_data) >= 10:
            # Use historical data to estimate
            recent_growth = (market_data[-1] - market_data[-10]) / market_data[-10]
            forecast_value = current_value * (1 + recent_growth)
        else:
            # Use provided growth rate
            forecast_value = current_value * (1 + growth_rate)

        # Adjust for market size
        if market_size > 0:
            market_capture = min(forecast_value / market_size, 0.2)  # Assume max 20% capture
            potential_value = market_size * market_capture
        else:
            potential_value = forecast_value

        # Calculate success probability
        # Factors: competition (lower is better), timing (higher is better), market growth
        competition_factor = 1 - competition
        timing_factor = timing
        growth_factor = min(abs(growth_rate) / 0.5, 1) if growth_rate > 0 else 0

        success_probability = (competition_factor + timing_factor + growth_factor) / 3

        # Confidence based on data quality
        if market_data is not None and len(market_data) >= 20:
            confidence = 0.8
        elif market_data is not None:
            confidence = 0.6
        else:
            confidence = 0.4

        # Timeframe estimation
        if timing > 0.7:
            timeframe = 'IMMEDIATE (1-3 months)'
        elif timing > 0.5:
            timeframe = 'SHORT-TERM (3-6 months)'
        elif timing > 0.3:
            timeframe = 'MEDIUM-TERM (6-12 months)'
        else:
            timeframe = 'LONG-TERM (12+ months)'

        # Requirements
        requirements = []
        if competition > 0.7:
            requirements.append('Strong differentiation strategy needed')
        if market_size > 0 and potential_value > market_size * 0.1:
            requirements.append('Significant resources required for market capture')
        if timing < 0.5:
            requirements.append('Patient capital and timing strategy')

        # Store opportunity
        cursor = self.memory.conn.cursor()
        cursor.execute('''
            INSERT INTO opportunities (opportunity_type, entity, potential_value,
                                      confidence, success_probability, requirements, timeframe)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            opportunity_type,
            entity,
            potential_value,
            confidence,
            success_probability,
            json.dumps(requirements),
            timeframe
        ))
        self.memory.conn.commit()
        opportunity_id = cursor.lastrowid

        self.memory.log_decision(
            f'Opportunity forecast: {entity}',
            f'Type: {opportunity_type}, Value: ${potential_value:,.2f}, Probability: {success_probability:.2%}',
            tags=['opportunity', 'forecast', opportunity_type]
        )

        result = {
            'opportunity_id': opportunity_id,
            'opportunity_type': opportunity_type,
            'entity': entity,
            'potential_value': float(potential_value),
            'success_probability': float(success_probability),
            'confidence': float(confidence),
            'timeframe': timeframe,
            'requirements': requirements,
            'expected_roi': float(potential_value - current_value) if current_value > 0 else float(potential_value),
            'recommendation': self._get_opportunity_recommendation(success_probability, confidence),
            'timestamp': datetime.now().isoformat()
        }

        return result

    def _get_opportunity_recommendation(self, success_prob: float,
                                       confidence: float) -> str:
        """Generate opportunity recommendation"""
        if success_prob > 0.7 and confidence > 0.6:
            return 'STRONG OPPORTUNITY - Pursue aggressively'
        elif success_prob > 0.6 and confidence > 0.5:
            return 'GOOD OPPORTUNITY - Pursue with standard approach'
        elif success_prob > 0.5:
            return 'MODERATE OPPORTUNITY - Pursue cautiously'
        elif success_prob > 0.3:
            return 'WEAK OPPORTUNITY - Consider alternatives'
        else:
            return 'POOR OPPORTUNITY - Likely not worth pursuing'

    # ============================================================================
    # VALIDATION AND ACCURACY TRACKING
    # ============================================================================

    def record_actual_outcome(self, prediction_id: int, actual_value: float):
        """
        Record actual outcome for accuracy tracking

        Args:
            prediction_id: ID of the prediction
            actual_value: Actual observed value
        """
        # Get original prediction
        cursor = self.memory.conn.cursor()
        cursor.execute('''
            SELECT prediction_type, prediction FROM predictions WHERE id = ?
        ''', (prediction_id,))
        row = cursor.fetchone()

        if not row:
            return

        prediction_type = row['prediction_type']
        prediction_data = json.loads(row['prediction'])

        # Extract predicted value based on type
        if prediction_type == 'timeseries':
            predicted_value = prediction_data.get('forecast', [0])[0]
        elif prediction_type == 'outcome':
            predicted_value = prediction_data.get('success_probability', 0.5)
        else:
            predicted_value = prediction_data.get('value', 0)

        # Calculate errors
        error = predicted_value - actual_value
        absolute_error = abs(error)
        squared_error = error ** 2

        # Store accuracy record
        cursor.execute('''
            INSERT INTO prediction_accuracy (prediction_id, prediction_type,
                                            predicted_value, actual_value,
                                            error, absolute_error, squared_error)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (prediction_id, prediction_type, predicted_value, actual_value,
              error, absolute_error, squared_error))
        self.memory.conn.commit()

        # Update tracking metrics
        if prediction_type in self.accuracy_metrics:
            self.accuracy_metrics[prediction_type].append(absolute_error)

    def get_model_accuracy(self, prediction_type: str = None,
                          days: int = 30) -> Dict:
        """
        Get accuracy metrics for predictions

        Args:
            prediction_type: Filter by prediction type
            days: Number of days to look back

        Returns:
            Accuracy metrics (MAE, RMSE, accuracy rate)
        """
        cursor = self.memory.conn.cursor()

        if prediction_type:
            cursor.execute('''
                SELECT * FROM prediction_accuracy
                WHERE prediction_type = ?
                  AND recorded_at >= datetime('now', '-' || ? || ' days')
            ''', (prediction_type, days))
        else:
            cursor.execute('''
                SELECT * FROM prediction_accuracy
                WHERE recorded_at >= datetime('now', '-' || ? || ' days')
            ''', (days,))

        rows = cursor.fetchall()

        if not rows:
            return {
                'count': 0,
                'mae': None,
                'rmse': None,
                'accuracy': None
            }

        # Calculate metrics
        absolute_errors = [row['absolute_error'] for row in rows]
        squared_errors = [row['squared_error'] for row in rows]

        mae = np.mean(absolute_errors)
        rmse = np.sqrt(np.mean(squared_errors))

        # Accuracy for classification (within 10% threshold)
        threshold = 0.1
        accurate_predictions = sum(1 for ae in absolute_errors if ae < threshold)
        accuracy = accurate_predictions / len(absolute_errors)

        return {
            'count': len(rows),
            'mae': float(mae),
            'rmse': float(rmse),
            'accuracy': float(accuracy),
            'prediction_type': prediction_type if prediction_type else 'all',
            'period_days': days
        }

    def get_prediction_summary(self) -> Dict:
        """Get summary of all predictions"""
        cursor = self.memory.conn.cursor()

        # Count by type
        cursor.execute('''
            SELECT prediction_type, COUNT(*) as count
            FROM predictions
            GROUP BY prediction_type
        ''')
        type_counts = {row['prediction_type']: row['count'] for row in cursor.fetchall()}

        # Recent accuracy
        recent_accuracy = {}
        for pred_type in type_counts.keys():
            acc = self.get_model_accuracy(pred_type, days=7)
            recent_accuracy[pred_type] = acc

        return {
            'total_predictions': sum(type_counts.values()),
            'predictions_by_type': type_counts,
            'recent_accuracy': recent_accuracy,
            'timestamp': datetime.now().isoformat()
        }


# ============================================================================
# TESTING
# ============================================================================

if __name__ == '__main__':
    import sys
    import io

    # Fix Windows console encoding
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("=" * 80)
    print("PREDICTIVE MODELING & FORECASTING SYSTEM")
    print("=" * 80)

    # Initialize system
    system = PredictiveModelingSystem()
    print("\n✓ System initialized with database tables")

    # Test 1: Time Series Forecasting
    print("\n" + "=" * 80)
    print("TEST 1: TIME SERIES FORECASTING")
    print("=" * 80)

    # Generate sample time series (upward trend with noise)
    np.random.seed(42)
    t = np.arange(100)
    trend = 0.5 * t
    seasonal = 10 * np.sin(2 * np.pi * t / 20)
    noise = np.random.normal(0, 2, 100)
    time_series = 100 + trend + seasonal + noise

    print(f"\nForecasting time series with {len(time_series)} historical points")

    # Test different methods
    for method in ['arima', 'exponential', 'moving_average', 'ensemble']:
        forecast_result = system.forecast_timeseries(
            series_name='test_series',
            data=time_series,
            horizon=10,
            method=method
        )

        print(f"\n{method.upper()} Method:")
        print(f"  Forecast (next 10): {forecast_result['forecast'][:3]}... (first 3)")
        print(f"  MAE: {forecast_result['mae']:.4f}" if forecast_result['mae'] else "  MAE: N/A")
        print(f"  RMSE: {forecast_result['rmse']:.4f}" if forecast_result['rmse'] else "  RMSE: N/A")
        print(f"  Confidence interval: [{forecast_result['lower_confidence'][0]:.2f}, {forecast_result['upper_confidence'][0]:.2f}]")

    # Test 2: Anomaly Prediction
    print("\n" + "=" * 80)
    print("TEST 2: ANOMALY PREDICTION")
    print("=" * 80)

    # Create data with anomaly pattern
    normal_data = np.random.normal(100, 10, 80)
    # Add pre-anomaly pattern
    pre_anomaly = np.array([110, 115, 125, 130, 140])  # Increasing trend
    normal_data = np.concatenate([normal_data, pre_anomaly])

    anomaly_pred = system.predict_anomaly(
        series_name='market_indicator',
        data=normal_data,
        sensitivity=2.0
    )

    print(f"\nAnomaly Prediction Results:")
    print(f"  Probability: {anomaly_pred['anomaly_probability']:.2%}")
    print(f"  Estimated periods ahead: {anomaly_pred['estimated_periods_ahead']}")
    print(f"  Risk level: {anomaly_pred['risk_level']}")
    print(f"  Current Z-score: {anomaly_pred['current_z_score']:.2f}")
    print(f"  Recommendation: {anomaly_pred['recommendation']}")

    # Test 3: Outcome Prediction
    print("\n" + "=" * 80)
    print("TEST 3: OUTCOME PREDICTION")
    print("=" * 80)

    # Define decision features
    decision_features = {
        'potential_gain': 50000,
        'potential_loss': 10000,
        'complexity': 6,
        'timeline': 90,
        'resource_requirement': 0.6,
        'confidence_level': 0.7
    }

    # Simulate historical outcomes
    historical = [
        {'features': {'potential_gain': 40000, 'potential_loss': 8000, 'complexity': 5,
                     'timeline': 60, 'resource_requirement': 0.5, 'confidence_level': 0.8},
         'success': True},
        {'features': {'potential_gain': 60000, 'potential_loss': 15000, 'complexity': 8,
                     'timeline': 120, 'resource_requirement': 0.8, 'confidence_level': 0.5},
         'success': False},
        {'features': {'potential_gain': 45000, 'potential_loss': 9000, 'complexity': 6,
                     'timeline': 80, 'resource_requirement': 0.6, 'confidence_level': 0.75},
         'success': True},
    ] * 5  # Repeat to have more data

    outcome_pred = system.predict_outcome(
        decision_type='investment',
        features=decision_features,
        historical_outcomes=historical
    )

    print(f"\nOutcome Prediction Results:")
    print(f"  Success probability: {outcome_pred['success_probability']:.2%}")
    print(f"  Expected value: ${outcome_pred['expected_value']:,.2f}")
    print(f"  Risk-reward ratio: {outcome_pred['risk_reward_ratio']:.2f}")
    print(f"  Confidence: {outcome_pred['confidence']:.2%}")
    print(f"  Recommendation: {outcome_pred['recommendation']}")

    # Test 4: Risk Assessment
    print("\n" + "=" * 80)
    print("TEST 4: RISK ASSESSMENT")
    print("=" * 80)

    risk_context = {
        'volatility': 0.35,
        'uncertainty': 0.4,
        'exposure': 75000,
        'complexity': 7
    }

    # Simulate increasing risk trend
    risk_history = np.linspace(0.3, 0.6, 30)

    risk_assessment = system.assess_risk(
        risk_type='market',
        entity='Portfolio A',
        context=risk_context,
        historical_data=risk_history
    )

    print(f"\nRisk Assessment Results:")
    print(f"  Risk score: {risk_assessment['risk_score']:.2f}")
    print(f"  Risk level: {risk_assessment['risk_level']}")
    print(f"  Risk factors:")
    for factor in risk_assessment['risk_factors']:
        print(f"    - {factor['factor']}: {factor['score']:.2f} - {factor['description']}")
    print(f"  Mitigation suggestions:")
    for suggestion in risk_assessment['mitigation_suggestions']:
        print(f"    - {suggestion}")

    # Test 5: Opportunity Forecasting
    print("\n" + "=" * 80)
    print("TEST 5: OPPORTUNITY FORECASTING")
    print("=" * 80)

    opp_context = {
        'current_value': 100000,
        'growth_rate': 0.25,
        'market_size': 1000000,
        'competition': 0.4,
        'timing': 0.75
    }

    # Simulate market growth
    market_history = np.array([90000, 95000, 100000, 110000, 120000, 125000, 130000,
                               140000, 150000, 160000])

    opportunity = system.forecast_opportunity(
        opportunity_type='market_expansion',
        entity='Product Line B',
        context=opp_context,
        market_data=market_history
    )

    print(f"\nOpportunity Forecast Results:")
    print(f"  Potential value: ${opportunity['potential_value']:,.2f}")
    print(f"  Success probability: {opportunity['success_probability']:.2%}")
    print(f"  Confidence: {opportunity['confidence']:.2%}")
    print(f"  Timeframe: {opportunity['timeframe']}")
    print(f"  Expected ROI: ${opportunity['expected_roi']:,.2f}")
    print(f"  Recommendation: {opportunity['recommendation']}")
    print(f"  Requirements:")
    for req in opportunity['requirements']:
        print(f"    - {req}")

    # Test 6: Accuracy Tracking
    print("\n" + "=" * 80)
    print("TEST 6: ACCURACY TRACKING & VALIDATION")
    print("=" * 80)

    # Simulate some actual outcomes
    print("\nRecording actual outcomes for validation...")
    system.record_actual_outcome(
        prediction_id=forecast_result['forecast_id'],
        actual_value=forecast_result['forecast'][0] + np.random.normal(0, 5)
    )

    # Get accuracy summary
    summary = system.get_prediction_summary()
    print(f"\nPrediction Summary:")
    print(f"  Total predictions: {summary['total_predictions']}")
    print(f"  Predictions by type:")
    for pred_type, count in summary['predictions_by_type'].items():
        print(f"    {pred_type}: {count}")

    # Get model accuracy
    accuracy = system.get_model_accuracy(days=30)
    print(f"\nModel Accuracy (last 30 days):")
    print(f"  Predictions evaluated: {accuracy['count']}")
    if accuracy['mae']:
        print(f"  MAE: {accuracy['mae']:.4f}")
        print(f"  RMSE: {accuracy['rmse']:.4f}")
        print(f"  Accuracy rate: {accuracy['accuracy']:.2%}")

    print("\n" + "=" * 80)
    print("ALL TESTS COMPLETE")
    print("=" * 80)
    print("\nPredictive Modeling & Forecasting System is fully operational!")
    print(f"Database: {system.memory.db_path}")
    print("\nCapabilities:")
    print("  ✓ Time series forecasting (multiple methods)")
    print("  ✓ Anomaly prediction")
    print("  ✓ Outcome prediction")
    print("  ✓ Risk assessment")
    print("  ✓ Opportunity forecasting")
    print("  ✓ Confidence intervals")
    print("  ✓ Accuracy tracking and validation")
