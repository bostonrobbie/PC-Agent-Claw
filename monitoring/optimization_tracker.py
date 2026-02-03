#!/usr/bin/env python3
"""Optimization Tracker (#44) - Track optimization experiments and results"""
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import json
import sys

sys.path.append(str(Path(__file__).parent.parent))

class OptimizationTracker:
    """Track optimization experiments and their results"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            workspace = Path(__file__).parent.parent
            db_path = str(workspace / "optimization.db")

        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        """Initialize database schema"""
        cursor = self.conn.cursor()

        # Experiments table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS experiments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                target_metric TEXT NOT NULL,
                optimization_type TEXT,
                status TEXT DEFAULT 'running',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        ''')

        # Trials table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id INTEGER NOT NULL,
                parameters TEXT NOT NULL,
                metric_value REAL,
                status TEXT DEFAULT 'pending',
                runtime_seconds REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (experiment_id) REFERENCES experiments (id)
            )
        ''')

        # Best results table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS best_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id INTEGER NOT NULL,
                trial_id INTEGER NOT NULL,
                parameters TEXT NOT NULL,
                metric_value REAL NOT NULL,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (experiment_id) REFERENCES experiments (id),
                FOREIGN KEY (trial_id) REFERENCES trials (id)
            )
        ''')

        self.conn.commit()

    def create_experiment(self, name: str, target_metric: str, description: str = None,
                         optimization_type: str = 'maximize') -> int:
        """Create a new optimization experiment"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO experiments (name, description, target_metric, optimization_type)
            VALUES (?, ?, ?, ?)
        ''', (name, description, target_metric, optimization_type))
        self.conn.commit()
        return cursor.lastrowid

    def add_trial(self, experiment_id: int, parameters: Dict, metric_value: float = None,
                 status: str = 'completed', runtime_seconds: float = None) -> int:
        """Add a trial to an experiment"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO trials (experiment_id, parameters, metric_value, status, runtime_seconds, completed_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (experiment_id, json.dumps(parameters), metric_value, status, runtime_seconds,
              datetime.now().isoformat() if status == 'completed' else None))
        self.conn.commit()

        trial_id = cursor.lastrowid

        # Check if this is a new best result
        if metric_value is not None and status == 'completed':
            self._update_best_result(experiment_id, trial_id, parameters, metric_value)

        return trial_id

    def _update_best_result(self, experiment_id: int, trial_id: int, parameters: Dict, metric_value: float):
        """Update best result if this trial is better"""
        cursor = self.conn.cursor()

        # Get experiment info
        cursor.execute('SELECT optimization_type FROM experiments WHERE id = ?', (experiment_id,))
        exp = cursor.fetchone()

        if not exp:
            return

        optimization_type = exp['optimization_type']

        # Get current best
        cursor.execute('''
            SELECT metric_value FROM best_results
            WHERE experiment_id = ?
            ORDER BY id DESC LIMIT 1
        ''', (experiment_id,))

        current_best = cursor.fetchone()

        # Check if this is better
        is_better = False
        if current_best is None:
            is_better = True
        elif optimization_type == 'maximize':
            is_better = metric_value > current_best['metric_value']
        else:  # minimize
            is_better = metric_value < current_best['metric_value']

        # Save if better
        if is_better:
            cursor.execute('''
                INSERT INTO best_results (experiment_id, trial_id, parameters, metric_value)
                VALUES (?, ?, ?, ?)
            ''', (experiment_id, trial_id, json.dumps(parameters), metric_value))
            self.conn.commit()

    def get_best_result(self, experiment_id: int) -> Optional[Dict]:
        """Get best result for an experiment"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM best_results
            WHERE experiment_id = ?
            ORDER BY id DESC LIMIT 1
        ''', (experiment_id,))

        row = cursor.fetchone()
        if row:
            result = dict(row)
            result['parameters'] = json.loads(result['parameters'])
            return result

        return None

    def get_experiment_trials(self, experiment_id: int, limit: int = 100) -> List[Dict]:
        """Get all trials for an experiment"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM trials
            WHERE experiment_id = ?
            ORDER BY metric_value DESC
            LIMIT ?
        ''', (experiment_id, limit))

        trials = []
        for row in cursor.fetchall():
            trial = dict(row)
            trial['parameters'] = json.loads(trial['parameters'])
            trials.append(trial)

        return trials

    def complete_experiment(self, experiment_id: int):
        """Mark experiment as completed"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE experiments
            SET status = 'completed', completed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (experiment_id,))
        self.conn.commit()

    def get_experiment_statistics(self, experiment_id: int) -> Dict:
        """Get statistics for an experiment"""
        cursor = self.conn.cursor()

        # Get experiment info
        cursor.execute('SELECT * FROM experiments WHERE id = ?', (experiment_id,))
        exp = dict(cursor.fetchone())

        # Get trial count
        cursor.execute('SELECT COUNT(*) as count FROM trials WHERE experiment_id = ?', (experiment_id,))
        trial_count = cursor.fetchone()['count']

        # Get best result
        best = self.get_best_result(experiment_id)

        # Get metric statistics
        cursor.execute('''
            SELECT
                AVG(metric_value) as avg_value,
                MIN(metric_value) as min_value,
                MAX(metric_value) as max_value
            FROM trials
            WHERE experiment_id = ? AND status = 'completed' AND metric_value IS NOT NULL
        ''', (experiment_id,))
        stats = dict(cursor.fetchone())

        return {
            'experiment_name': exp['name'],
            'target_metric': exp['target_metric'],
            'optimization_type': exp['optimization_type'],
            'status': exp['status'],
            'total_trials': trial_count,
            'best_value': best['metric_value'] if best else None,
            'best_parameters': best['parameters'] if best else None,
            'avg_value': stats['avg_value'],
            'min_value': stats['min_value'],
            'max_value': stats['max_value']
        }

    def close(self):
        """Close database connection"""
        self.conn.close()


if __name__ == '__main__':
    # Test the system
    tracker = OptimizationTracker()

    print("Optimization Tracker ready!")

    # Create an experiment
    exp_id = tracker.create_experiment(
        "Strategy Parameter Optimization",
        target_metric="sharpe_ratio",
        description="Optimize moving average periods for best Sharpe ratio",
        optimization_type="maximize"
    )

    print(f"\nCreated experiment: {exp_id}")

    # Add some trials
    print("\nRunning optimization trials...")
    for fast_period in [5, 10, 15, 20]:
        for slow_period in [20, 30, 40, 50]:
            if slow_period > fast_period:
                # Simulate optimization
                sharpe = 0.5 + (fast_period * 0.01) + (slow_period * 0.005)

                tracker.add_trial(
                    exp_id,
                    parameters={'fast_period': fast_period, 'slow_period': slow_period},
                    metric_value=sharpe,
                    runtime_seconds=2.5
                )

    # Get results
    stats = tracker.get_experiment_statistics(exp_id)
    print("\nExperiment Statistics:")
    print(json.dumps(stats, indent=2))

    # Complete experiment
    tracker.complete_experiment(exp_id)

    tracker.close()
