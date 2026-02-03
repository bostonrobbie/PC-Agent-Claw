#!/usr/bin/env python3
"""Online Learning System - Update models in real-time"""
import sys
from pathlib import Path
import numpy as np
from typing import Dict, List
from datetime import datetime
from collections import deque

sys.path.append(str(Path(__file__).parent.parent))

from core.persistent_memory import PersistentMemory

class OnlineLearningSystem:
    """Online learning - update models with new data in real-time"""

    def __init__(self, window_size: int = 1000, db_path: str = None):
        workspace = Path(__file__).parent.parent
        if db_path is None:
            db_path = str(workspace / "memory.db")

        self.memory = PersistentMemory(db_path)

        # Sliding window for recent data
        self.window_size = window_size
        self.X_buffer = deque(maxlen=window_size)
        self.y_buffer = deque(maxlen=window_size)

        # Model state
        self.model = None
        self.model_version = 0
        self.last_update = None

        # Performance tracking
        self.online_performance = {
            'predictions': 0,
            'correct': 0,
            'accuracy_history': deque(maxlen=100)
        }

    def update(self, X_new: np.ndarray, y_new: np.ndarray, retrain_threshold: int = 100):
        """
        Update model with new data

        Args:
            X_new: New features
            y_new: New labels
            retrain_threshold: Retrain after this many new samples
        """
        # Add to buffer
        for x, y in zip(X_new, y_new):
            self.X_buffer.append(x)
            self.y_buffer.append(y)

        # Check if we should retrain
        if len(self.X_buffer) % retrain_threshold == 0 and len(self.X_buffer) >= 100:
            self._retrain()

    def _retrain(self):
        """Retrain model on buffered data"""
        X = np.array(list(self.X_buffer))
        y = np.array(list(self.y_buffer))

        # Simple online SGD classifier
        from sklearn.linear_model import SGDClassifier

        if self.model is None:
            self.model = SGDClassifier(loss='log_loss', warm_start=True)
            self.model.fit(X, y)
        else:
            # Partial fit (online learning)
            classes = np.unique(y)
            self.model.partial_fit(X, y, classes=classes)

        self.model_version += 1
        self.last_update = datetime.now()

        self.memory.log_decision(
            f'Online model updated (v{self.model_version})',
            f'Samples in buffer: {len(self.X_buffer)}',
            tags=['online_learning', 'retrain']
        )

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make prediction"""
        if self.model is None:
            raise ValueError("Model not trained yet")

        predictions = self.model.predict(X)
        self.online_performance['predictions'] += len(predictions)

        return predictions

    def update_performance(self, y_true: np.ndarray, y_pred: np.ndarray):
        """Update performance metrics"""
        correct = np.sum(y_true == y_pred)
        self.online_performance['correct'] += correct

        accuracy = correct / len(y_true)
        self.online_performance['accuracy_history'].append(accuracy)

    def get_performance(self) -> Dict:
        """Get current performance metrics"""
        if self.online_performance['predictions'] > 0:
            overall_accuracy = (self.online_performance['correct'] /
                              self.online_performance['predictions'])
        else:
            overall_accuracy = 0

        recent_accuracy = (np.mean(self.online_performance['accuracy_history'])
                          if self.online_performance['accuracy_history'] else 0)

        return {
            'model_version': self.model_version,
            'total_predictions': self.online_performance['predictions'],
            'overall_accuracy': round(overall_accuracy, 4),
            'recent_accuracy': round(recent_accuracy, 4),
            'buffer_size': len(self.X_buffer),
            'last_update': self.last_update.isoformat() if self.last_update else None
        }


if __name__ == '__main__':
    # Test online learning
    online_system = OnlineLearningSystem(window_size=500)

    print("Online Learning System ready!")

    # Simulate streaming data
    for i in range(5):
        # Generate batch
        X_batch = np.random.randn(100, 5)
        y_batch = (X_batch[:, 0] + X_batch[:, 1] > 0).astype(int)

        # Update model
        online_system.update(X_batch, y_batch, retrain_threshold=50)

        # Make predictions
        if online_system.model is not None:
            X_test = np.random.randn(20, 5)
            y_test = (X_test[:, 0] + X_test[:, 1] > 0).astype(int)

            predictions = online_system.predict(X_test)
            online_system.update_performance(y_test, predictions)

        # Show performance
        perf = online_system.get_performance()
        print(f"\nBatch {i+1}:")
        print(f"  Model version: {perf['model_version']}")
        print(f"  Recent accuracy: {perf['recent_accuracy']:.2%}")
        print(f"  Buffer size: {perf['buffer_size']}")

    print("\nOnline Learning System operational!")
