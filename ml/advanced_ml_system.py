#!/usr/bin/env python3
"""Advanced ML System - GPU-accelerated machine learning"""
import sys
from pathlib import Path
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import json
import pickle

sys.path.append(str(Path(__file__).parent.parent))

from core.persistent_memory import PersistentMemory
from dual_gpu_manager import DualGPUManager

class AdvancedMLSystem:
    """Advanced machine learning with GPU acceleration"""

    def __init__(self, db_path: str = None):
        workspace = Path(__file__).parent.parent
        if db_path is None:
            db_path = str(workspace / "memory.db")

        self.memory = PersistentMemory(db_path)
        self.gpu_manager = DualGPUManager()

        # Model registry
        self.models = {}
        self.model_versions = {}
        self.model_performance = {}

        # Feature engineering
        self.feature_transformers = {}
        self.feature_importance = {}

        # Training history
        self.training_history = []

    def create_features(self, data: Dict, feature_config: Dict) -> np.ndarray:
        """
        Create features from raw data

        Args:
            data: Raw market/trading data
            feature_config: Configuration for feature generation

        Returns:
            Feature matrix
        """
        features = []

        # Price-based features
        if 'prices' in data:
            prices = np.array(data['prices'])

            # Returns
            returns = np.diff(prices) / prices[:-1]
            features.append(returns[-1] if len(returns) > 0 else 0)

            # Moving averages
            if len(prices) >= 10:
                ma10 = np.mean(prices[-10:])
                ma20 = np.mean(prices[-20:]) if len(prices) >= 20 else ma10
                features.append((prices[-1] - ma10) / ma10)  # Distance from MA10
                features.append((ma10 - ma20) / ma20 if ma20 != 0 else 0)  # MA crossover

            # Volatility
            if len(returns) >= 20:
                volatility = np.std(returns[-20:])
                features.append(volatility)

            # Momentum
            if len(prices) >= 5:
                momentum = (prices[-1] - prices[-5]) / prices[-5]
                features.append(momentum)

        # Volume-based features
        if 'volume' in data:
            volume = np.array(data['volume'])
            if len(volume) >= 20:
                volume_ma = np.mean(volume[-20:])
                volume_ratio = volume[-1] / volume_ma if volume_ma != 0 else 1
                features.append(volume_ratio)

        # Time-based features
        if 'timestamp' in data:
            timestamp = data['timestamp']
            if isinstance(timestamp, datetime):
                features.append(timestamp.hour / 24)  # Hour of day normalized
                features.append(timestamp.weekday() / 7)  # Day of week normalized

        return np.array(features)

    def train_model(self, X_train: np.ndarray, y_train: np.ndarray,
                   model_name: str, model_type: str = 'random_forest',
                   hyperparameters: Dict = None) -> Dict:
        """
        Train a machine learning model

        Args:
            X_train: Training features
            y_train: Training labels
            model_name: Name for the model
            model_type: Type of model (random_forest, neural_network, etc.)
            hyperparameters: Model hyperparameters

        Returns:
            Training results
        """
        start_time = datetime.now()

        try:
            if model_type == 'random_forest':
                model = self._train_random_forest(X_train, y_train, hyperparameters)

            elif model_type == 'neural_network':
                model = self._train_neural_network(X_train, y_train, hyperparameters)

            elif model_type == 'gradient_boosting':
                model = self._train_gradient_boosting(X_train, y_train, hyperparameters)

            else:
                raise ValueError(f"Unknown model type: {model_type}")

            # Store model
            version = self.model_versions.get(model_name, 0) + 1
            self.models[model_name] = model
            self.model_versions[model_name] = version

            # Calculate training metrics
            y_pred = model.predict(X_train)
            train_accuracy = np.mean(y_pred == y_train) if y_train.dtype == int else None

            if train_accuracy is None:
                # Regression metrics
                mse = np.mean((y_pred - y_train) ** 2)
                r2 = 1 - (np.sum((y_train - y_pred) ** 2) / np.sum((y_train - np.mean(y_train)) ** 2))
                train_metrics = {'mse': float(mse), 'r2': float(r2)}
            else:
                # Classification metrics
                train_metrics = {'accuracy': float(train_accuracy)}

            duration = (datetime.now() - start_time).total_seconds()

            result = {
                'model_name': model_name,
                'version': version,
                'model_type': model_type,
                'train_metrics': train_metrics,
                'training_duration': duration,
                'samples': len(X_train),
                'features': X_train.shape[1],
                'timestamp': start_time.isoformat()
            }

            # Log to memory
            self.memory.log_decision(
                f'Model trained: {model_name} v{version}',
                f'Type: {model_type}, Metrics: {json.dumps(train_metrics)}',
                tags=['ml', 'training', model_name]
            )

            # Store in history
            self.training_history.append(result)

            return result

        except Exception as e:
            self.memory.log_decision(
                f'Model training failed: {model_name}',
                f'Error: {str(e)}',
                tags=['ml', 'training_error', model_name]
            )
            raise

    def _train_random_forest(self, X, y, params):
        """Train Random Forest model"""
        from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor

        if params is None:
            params = {'n_estimators': 100, 'max_depth': 10}

        if y.dtype == int or len(np.unique(y)) < 10:
            model = RandomForestClassifier(**params)
        else:
            model = RandomForestRegressor(**params)

        model.fit(X, y)
        return model

    def _train_neural_network(self, X, y, params):
        """Train Neural Network (placeholder for GPU-accelerated training)"""
        # This would use PyTorch with GPU acceleration
        # For now, use sklearn MLPClassifier as placeholder

        from sklearn.neural_network import MLPClassifier, MLPRegressor

        if params is None:
            params = {'hidden_layer_sizes': (100, 50), 'max_iter': 200}

        if y.dtype == int or len(np.unique(y)) < 10:
            model = MLPClassifier(**params)
        else:
            model = MLPRegressor(**params)

        model.fit(X, y)
        return model

    def _train_gradient_boosting(self, X, y, params):
        """Train Gradient Boosting model"""
        from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor

        if params is None:
            params = {'n_estimators': 100, 'learning_rate': 0.1}

        if y.dtype == int or len(np.unique(y)) < 10:
            model = GradientBoostingClassifier(**params)
        else:
            model = GradientBoostingRegressor(**params)

        model.fit(X, y)
        return model

    def predict(self, model_name: str, X: np.ndarray) -> np.ndarray:
        """Make predictions with a trained model"""
        if model_name not in self.models:
            raise ValueError(f"Model not found: {model_name}")

        model = self.models[model_name]
        predictions = model.predict(X)

        return predictions

    def predict_with_confidence(self, model_name: str, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Make predictions with confidence scores"""
        if model_name not in self.models:
            raise ValueError(f"Model not found: {model_name}")

        model = self.models[model_name]
        predictions = model.predict(X)

        # Get confidence scores if available
        if hasattr(model, 'predict_proba'):
            probabilities = model.predict_proba(X)
            confidence = np.max(probabilities, axis=1)
        else:
            confidence = np.ones(len(predictions))  # No confidence available

        return predictions, confidence

    def evaluate_model(self, model_name: str, X_test: np.ndarray,
                      y_test: np.ndarray) -> Dict:
        """Evaluate model on test data"""
        if model_name not in self.models:
            raise ValueError(f"Model not found: {model_name}")

        model = self.models[model_name]
        y_pred = model.predict(X_test)

        # Calculate metrics
        if y_test.dtype == int or len(np.unique(y_test)) < 10:
            # Classification
            accuracy = np.mean(y_pred == y_test)
            metrics = {'accuracy': float(accuracy)}

            # Confusion matrix
            from sklearn.metrics import confusion_matrix
            cm = confusion_matrix(y_test, y_pred)
            metrics['confusion_matrix'] = cm.tolist()

        else:
            # Regression
            mse = np.mean((y_pred - y_test) ** 2)
            mae = np.mean(np.abs(y_pred - y_test))
            r2 = 1 - (np.sum((y_test - y_pred) ** 2) / np.sum((y_test - np.mean(y_test)) ** 2))

            metrics = {
                'mse': float(mse),
                'mae': float(mae),
                'r2': float(r2)
            }

        # Store performance
        self.model_performance[model_name] = metrics

        self.memory.log_decision(
            f'Model evaluated: {model_name}',
            f'Metrics: {json.dumps(metrics)}',
            tags=['ml', 'evaluation', model_name]
        )

        return metrics

    def optimize_hyperparameters(self, X: np.ndarray, y: np.ndarray,
                                 model_type: str, param_grid: Dict,
                                 n_trials: int = 20) -> Dict:
        """Optimize hyperparameters using random search"""
        best_score = -np.inf
        best_params = None
        results = []

        for trial in range(n_trials):
            # Sample random parameters
            params = {}
            for param_name, param_values in param_grid.items():
                if isinstance(param_values, list):
                    params[param_name] = np.random.choice(param_values)
                elif isinstance(param_values, tuple) and len(param_values) == 2:
                    # Range (min, max)
                    if isinstance(param_values[0], int):
                        params[param_name] = np.random.randint(param_values[0], param_values[1])
                    else:
                        params[param_name] = np.random.uniform(param_values[0], param_values[1])

            # Train with these parameters
            try:
                result = self.train_model(X, y, f'trial_{trial}', model_type, params)

                # Get score (use first metric)
                score = list(result['train_metrics'].values())[0]

                results.append({
                    'params': params,
                    'score': score,
                    'metrics': result['train_metrics']
                })

                if score > best_score:
                    best_score = score
                    best_params = params

            except Exception as e:
                print(f"Trial {trial} failed: {e}")
                continue

        self.memory.log_decision(
            f'Hyperparameter optimization complete',
            f'Best score: {best_score}, Best params: {json.dumps(best_params)}',
            tags=['ml', 'optimization', model_type]
        )

        return {
            'best_params': best_params,
            'best_score': best_score,
            'all_results': results
        }

    def save_model(self, model_name: str, filepath: str = None):
        """Save model to disk"""
        if model_name not in self.models:
            raise ValueError(f"Model not found: {model_name}")

        if filepath is None:
            workspace = Path(__file__).parent.parent
            filepath = workspace / f"models/{model_name}_v{self.model_versions[model_name]}.pkl"

        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, 'wb') as f:
            pickle.dump(self.models[model_name], f)

        return filepath

    def load_model(self, model_name: str, filepath: str):
        """Load model from disk"""
        with open(filepath, 'rb') as f:
            model = pickle.load(f)

        self.models[model_name] = model

        self.memory.log_decision(
            f'Model loaded: {model_name}',
            f'From: {filepath}',
            tags=['ml', 'load', model_name]
        )

    def get_model_info(self, model_name: str = None) -> Dict:
        """Get information about models"""
        if model_name:
            if model_name not in self.models:
                return {}

            return {
                'name': model_name,
                'version': self.model_versions.get(model_name, 0),
                'performance': self.model_performance.get(model_name, {})
            }
        else:
            return {
                'models': list(self.models.keys()),
                'total_trained': len(self.training_history),
                'performance': self.model_performance
            }


if __name__ == '__main__':
    # Test the system
    ml_system = AdvancedMLSystem()

    print("Advanced ML System ready!")

    # Generate sample data
    np.random.seed(42)
    X_train = np.random.randn(1000, 10)
    y_train = (X_train[:, 0] + X_train[:, 1] > 0).astype(int)

    X_test = np.random.randn(200, 10)
    y_test = (X_test[:, 0] + X_test[:, 1] > 0).astype(int)

    # Train model
    print("\nTraining Random Forest model...")
    result = ml_system.train_model(X_train, y_train, 'test_model', 'random_forest')
    print(f"Training complete: {result['train_metrics']}")

    # Evaluate
    print("\nEvaluating model...")
    metrics = ml_system.evaluate_model('test_model', X_test, y_test)
    print(f"Test metrics: {metrics}")

    # Predict with confidence
    predictions, confidence = ml_system.predict_with_confidence('test_model', X_test[:5])
    print(f"\nPredictions: {predictions}")
    print(f"Confidence: {confidence}")

    print("\nAdvanced ML System operational!")
