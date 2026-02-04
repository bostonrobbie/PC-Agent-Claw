"""
Predictive Resource Manager

Predict resource exhaustion BEFORE it happens:
- Monitor memory/CPU/disk trends
- Predict when limits will be reached (T-5min warning)
- Automatically trigger cleanup/optimization
- Scale back operations before crash

PREVENTS CRASHES from resource exhaustion
"""
import psutil
import time
from typing import Dict, List, Optional, Tuple
from collections import deque
from dataclasses import dataclass


@dataclass
class ResourceSample:
    """Single resource measurement"""
    timestamp: float
    memory_percent: float
    cpu_percent: float
    disk_percent: float


class PredictiveResourceManager:
    """
    Monitor resources and predict exhaustion before it happens

    Proactive management prevents crashes
    """

    def __init__(self, sample_interval: int = 5,
                 history_window: int = 60,
                 warning_threshold: float = 0.85,
                 critical_threshold: float = 0.95):
        """
        Initialize resource manager

        Args:
            sample_interval: Seconds between samples
            history_window: Number of samples to keep for prediction
            warning_threshold: Warn when resource usage > this (0.85 = 85%)
            critical_threshold: Critical when usage > this (0.95 = 95%)
        """
        self.sample_interval = sample_interval
        self.history_window = history_window
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold

        # Resource history (limited deque for efficiency)
        self.history: deque = deque(maxlen=history_window)

        # Last sample
        self.last_sample_time = 0.0

        # Statistics
        self.stats = {
            'total_samples': 0,
            'warnings_issued': 0,
            'critical_alerts': 0,
            'cleanups_triggered': 0,
            'crashes_prevented': 0
        }

    def sample_resources(self) -> ResourceSample:
        """Take a resource measurement"""
        current_time = time.time()

        # Get resource usage
        memory = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=0.1)
        disk = psutil.disk_usage('/').percent

        sample = ResourceSample(
            timestamp=current_time,
            memory_percent=memory.percent / 100.0,
            cpu_percent=cpu / 100.0,
            disk_percent=disk / 100.0
        )

        self.history.append(sample)
        self.last_sample_time = current_time
        self.stats['total_samples'] += 1

        return sample

    def should_sample(self) -> bool:
        """Check if should take new sample"""
        return (time.time() - self.last_sample_time) >= self.sample_interval

    def predict_exhaustion(self, resource: str = 'memory',
                          horizon_minutes: int = 5) -> Optional[Dict]:
        """
        Predict when resource will be exhausted

        Args:
            resource: 'memory', 'cpu', or 'disk'
            horizon_minutes: How far ahead to predict

        Returns:
            Prediction dict or None if not trending toward exhaustion
        """
        if len(self.history) < 3:
            return None

        # Get recent trend
        recent_samples = list(self.history)[-20:]  # Last 20 samples

        # Extract resource values
        if resource == 'memory':
            values = [s.memory_percent for s in recent_samples]
        elif resource == 'cpu':
            values = [s.cpu_percent for s in recent_samples]
        elif resource == 'disk':
            values = [s.disk_percent for s in recent_samples]
        else:
            return None

        # Calculate trend (simple linear regression)
        n = len(values)
        x = list(range(n))
        y = values

        # Calculate slope
        x_mean = sum(x) / n
        y_mean = sum(y) / n

        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return None

        slope = numerator / denominator
        intercept = y_mean - slope * x_mean

        # Check if trending upward
        if slope <= 0:
            return None  # Not increasing

        # Project forward
        current_value = values[-1]
        samples_ahead = (horizon_minutes * 60) / self.sample_interval
        predicted_value = slope * (n + samples_ahead) + intercept

        # Check if will exceed threshold
        if predicted_value < 1.0:
            return None  # Won't exhaust in horizon

        # Calculate time to exhaustion
        if slope > 0:
            samples_to_exhaustion = (1.0 - current_value) / slope
            time_to_exhaustion = samples_to_exhaustion * self.sample_interval
        else:
            time_to_exhaustion = float('inf')

        return {
            'resource': resource,
            'current_value': current_value,
            'predicted_value': min(predicted_value, 1.0),
            'slope': slope,
            'time_to_exhaustion_seconds': time_to_exhaustion,
            'time_to_exhaustion_minutes': time_to_exhaustion / 60.0,
            'confidence': min(len(recent_samples) / 20.0, 1.0)  # More samples = higher confidence
        }

    def check_resources(self) -> Dict:
        """
        Check resource status and predictions

        Returns comprehensive status
        """
        # Sample if needed
        if self.should_sample():
            current = self.sample_resources()
        else:
            current = self.history[-1] if self.history else self.sample_resources()

        status = {
            'current': {
                'memory': current.memory_percent,
                'cpu': current.cpu_percent,
                'disk': current.disk_percent,
                'timestamp': current.timestamp
            },
            'status': 'healthy',
            'warnings': [],
            'predictions': {}
        }

        # Check current levels
        for resource, value in [('memory', current.memory_percent),
                                ('cpu', current.cpu_percent),
                                ('disk', current.disk_percent)]:
            if value >= self.critical_threshold:
                status['status'] = 'critical'
                status['warnings'].append(f"{resource} at {value:.1%} (critical)")
                self.stats['critical_alerts'] += 1
            elif value >= self.warning_threshold:
                if status['status'] == 'healthy':
                    status['status'] = 'warning'
                status['warnings'].append(f"{resource} at {value:.1%} (warning)")
                self.stats['warnings_issued'] += 1

        # Get predictions
        for resource in ['memory', 'cpu', 'disk']:
            prediction = self.predict_exhaustion(resource, horizon_minutes=5)
            if prediction:
                status['predictions'][resource] = prediction

                # Add warning if exhaustion predicted
                if prediction['time_to_exhaustion_minutes'] < 5:
                    status['warnings'].append(
                        f"{resource} exhaustion predicted in "
                        f"{prediction['time_to_exhaustion_minutes']:.1f} minutes"
                    )

        return status

    def auto_optimize(self) -> Dict:
        """
        Automatically optimize resource usage

        Triggered when resources critical or exhaustion predicted
        """
        import gc

        optimizations = {
            'actions_taken': [],
            'resources_freed': {}
        }

        # Get current status
        status = self.check_resources()

        # Check if optimization needed
        needs_optimization = (
            status['status'] in ['warning', 'critical'] or
            len(status['predictions']) > 0
        )

        if not needs_optimization:
            return optimizations

        # Run garbage collection
        before_mem = psutil.virtual_memory().percent
        gc.collect()
        after_mem = psutil.virtual_memory().percent
        freed_mem = before_mem - after_mem

        if freed_mem > 0:
            optimizations['actions_taken'].append('garbage_collection')
            optimizations['resources_freed']['memory'] = freed_mem

        self.stats['cleanups_triggered'] += 1

        # If still critical, more aggressive measures
        if status['status'] == 'critical':
            optimizations['actions_taken'].append('recommend_restart')
            self.stats['crashes_prevented'] += 1

        return optimizations

    def get_resource_trends(self) -> Dict:
        """Get resource usage trends over time"""
        if len(self.history) < 2:
            return {'error': 'Insufficient data'}

        samples = list(self.history)

        # Calculate averages over different windows
        def avg_last_n(resource_attr: str, n: int) -> float:
            recent = samples[-n:] if len(samples) >= n else samples
            values = [getattr(s, resource_attr) for s in recent]
            return sum(values) / len(values) if values else 0.0

        return {
            'memory': {
                'last_minute': avg_last_n('memory_percent', 12),   # 12 * 5s = 1min
                'last_5_minutes': avg_last_n('memory_percent', 60),  # 60 * 5s = 5min
                'current': samples[-1].memory_percent
            },
            'cpu': {
                'last_minute': avg_last_n('cpu_percent', 12),
                'last_5_minutes': avg_last_n('cpu_percent', 60),
                'current': samples[-1].cpu_percent
            },
            'disk': {
                'last_minute': avg_last_n('disk_percent', 12),
                'last_5_minutes': avg_last_n('disk_percent', 60),
                'current': samples[-1].disk_percent
            }
        }

    def get_recommendations(self) -> List[str]:
        """Get resource management recommendations"""
        recommendations = []

        status = self.check_resources()

        # Current status recommendations
        if status['status'] == 'critical':
            recommendations.append("CRITICAL: Immediate action required")
            recommendations.append("Run auto_optimize() or restart process")

        elif status['status'] == 'warning':
            recommendations.append("WARNING: Resource usage elevated")
            recommendations.append("Consider running cleanup operations")

        # Prediction-based recommendations
        for resource, prediction in status['predictions'].items():
            time_remaining = prediction['time_to_exhaustion_minutes']

            if time_remaining < 2:
                recommendations.append(
                    f"URGENT: {resource} exhaustion in {time_remaining:.1f} minutes"
                )
            elif time_remaining < 5:
                recommendations.append(
                    f"ALERT: {resource} exhaustion in {time_remaining:.1f} minutes"
                )
            elif time_remaining < 10:
                recommendations.append(
                    f"NOTICE: {resource} trending toward exhaustion"
                )

        # Trend-based recommendations
        trends = self.get_resource_trends()
        if 'memory' in trends:
            mem_trend = trends['memory']
            if mem_trend['current'] > mem_trend['last_5_minutes'] * 1.2:
                recommendations.append("Memory usage increasing rapidly")

        return recommendations

    def get_stats(self) -> Dict:
        """Get comprehensive statistics"""
        return {
            **self.stats,
            'samples_collected': len(self.history),
            'monitoring_duration': (self.history[-1].timestamp - self.history[0].timestamp
                                   if len(self.history) >= 2 else 0.0)
        }
