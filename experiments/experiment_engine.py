#!/usr/bin/env python3
"""
Automated Experimentation Framework
Run experiments autonomously to discover improvements
"""
import sys
from pathlib import Path
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
import traceback
import threading
import time

sys.path.append(str(Path(__file__).parent.parent))


@dataclass
class Experiment:
    """Experiment definition"""
    name: str
    hypothesis: str
    control: Dict
    treatments: List[Dict]
    success_metric: str
    sample_size: int
    duration_hours: float


@dataclass
class ExperimentResult:
    """Experiment results"""
    experiment_id: int
    treatment_name: str
    metric_value: float
    sample_size: int
    confidence: float
    p_value: float
    is_significant: bool
    winner: bool


class ExperimentEngine:
    """
    Automated experimentation framework

    Features:
    - Design A/B/n tests automatically
    - Execute experiments in parallel
    - Statistical significance testing
    - Implement winners automatically (with permission)
    - Track experiment history
    """

    def __init__(self, db_path: str = None, significance_level: float = 0.05):
        workspace = Path(__file__).parent.parent
        if db_path is None:
            db_path = str(workspace / "memory.db")

        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

        self.significance_level = significance_level
        self.running_experiments = {}
        self.lock = threading.Lock()

        # Load Telegram notifier
        try:
            from telegram_notifier import TelegramNotifier
            self.notifier = TelegramNotifier()
        except Exception as e:
            print(f"[WARNING] Could not load Telegram notifier: {e}")
            self.notifier = None

    def _init_db(self):
        """Initialize database schema"""
        cursor = self.conn.cursor()

        # Experiments
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS experiments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                hypothesis TEXT,
                success_metric TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                winner_treatment TEXT,
                improvement_pct REAL,
                p_value REAL,
                confidence REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        ''')

        # Treatments
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS experiment_treatments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id INTEGER NOT NULL,
                treatment_name TEXT NOT NULL,
                configuration TEXT NOT NULL,
                is_control INTEGER DEFAULT 0,
                sample_size INTEGER DEFAULT 0,
                metric_sum REAL DEFAULT 0,
                metric_mean REAL DEFAULT 0,
                metric_variance REAL DEFAULT 0,
                FOREIGN KEY (experiment_id) REFERENCES experiments(id)
            )
        ''')

        # Observations
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS experiment_observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                treatment_id INTEGER NOT NULL,
                metric_value REAL NOT NULL,
                context TEXT,
                observed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (treatment_id) REFERENCES experiment_treatments(id)
            )
        ''')

        # Implementations
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS experiment_implementations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id INTEGER NOT NULL,
                treatment_name TEXT NOT NULL,
                implemented_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                actual_improvement REAL,
                status TEXT DEFAULT 'deployed',
                rollback_at TIMESTAMP,
                FOREIGN KEY (experiment_id) REFERENCES experiments(id)
            )
        ''')

        self.conn.commit()

    # === EXPERIMENT DESIGN ===

    def design_experiment(self, name: str, hypothesis: str,
                         control: Dict, treatments: List[Dict],
                         success_metric: str,
                         sample_size: int = 100,
                         duration_hours: float = 24) -> int:
        """
        Design new experiment

        Args:
            name: Experiment name
            hypothesis: What you're testing
            control: Control configuration
            treatments: List of treatment configurations
            success_metric: Metric to optimize
            sample_size: Samples per treatment
            duration_hours: Max duration

        Returns:
            Experiment ID
        """
        cursor = self.conn.cursor()

        # Create experiment
        cursor.execute('''
            INSERT INTO experiments
            (name, hypothesis, success_metric, status, metadata)
            VALUES (?, ?, ?, 'pending', ?)
        ''', (name, hypothesis, success_metric,
              json.dumps({'sample_size': sample_size, 'duration_hours': duration_hours})))

        experiment_id = cursor.lastrowid

        # Add control
        cursor.execute('''
            INSERT INTO experiment_treatments
            (experiment_id, treatment_name, configuration, is_control)
            VALUES (?, 'control', ?, 1)
        ''', (experiment_id, json.dumps(control)))

        # Add treatments
        for i, treatment in enumerate(treatments):
            cursor.execute('''
                INSERT INTO experiment_treatments
                (experiment_id, treatment_name, configuration, is_control)
                VALUES (?, ?, ?, 0)
            ''', (experiment_id, f"treatment_{i+1}", json.dumps(treatment)))

        self.conn.commit()

        print(f"[EXPERIMENT] Designed: {name} ({len(treatments)} treatments)")

        return experiment_id

    def start_experiment(self, experiment_id: int):
        """Start running experiment"""
        cursor = self.conn.cursor()

        cursor.execute('''
            UPDATE experiments
            SET status = 'running', started_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (experiment_id,))

        self.conn.commit()

        with self.lock:
            self.running_experiments[experiment_id] = {
                'started': datetime.now(),
                'observations': 0
            }

        if self.notifier:
            try:
                cursor.execute('SELECT name FROM experiments WHERE id = ?', (experiment_id,))
                name = cursor.fetchone()['name']
                self.notifier.send_message(
                    f"Experiment Started: {name}\nID: {experiment_id}",
                    priority="info"
                )
            except:
                pass

    # === OBSERVATION RECORDING ===

    def record_observation(self, experiment_id: int, treatment_name: str,
                          metric_value: float, context: Dict = None):
        """
        Record observation for treatment

        Args:
            experiment_id: Experiment ID
            treatment_name: Which treatment
            metric_value: Observed metric value
            context: Additional context
        """
        cursor = self.conn.cursor()

        # Get treatment ID
        cursor.execute('''
            SELECT id FROM experiment_treatments
            WHERE experiment_id = ? AND treatment_name = ?
        ''', (experiment_id, treatment_name))

        result = cursor.fetchone()
        if not result:
            raise ValueError(f"Treatment {treatment_name} not found")

        treatment_id = result['id']

        # Record observation
        cursor.execute('''
            INSERT INTO experiment_observations
            (treatment_id, metric_value, context)
            VALUES (?, ?, ?)
        ''', (treatment_id, metric_value, json.dumps(context) if context else None))

        # Update treatment statistics
        cursor.execute('''
            UPDATE experiment_treatments
            SET sample_size = sample_size + 1,
                metric_sum = metric_sum + ?
            WHERE id = ?
        ''', (metric_value, treatment_id))

        # Recalculate mean
        cursor.execute('''
            UPDATE experiment_treatments
            SET metric_mean = metric_sum / sample_size
            WHERE id = ?
        ''', (treatment_id,))

        self.conn.commit()

        # Update running stats
        with self.lock:
            if experiment_id in self.running_experiments:
                self.running_experiments[experiment_id]['observations'] += 1

    # === ANALYSIS ===

    def analyze_experiment(self, experiment_id: int) -> List[ExperimentResult]:
        """
        Analyze experiment results using statistical tests

        Args:
            experiment_id: Experiment ID

        Returns:
            List of results for each treatment
        """
        cursor = self.conn.cursor()

        # Get control metrics
        cursor.execute('''
            SELECT id, treatment_name, metric_mean, sample_size
            FROM experiment_treatments
            WHERE experiment_id = ? AND is_control = 1
        ''', (experiment_id,))

        control = cursor.fetchone()
        if not control or control['sample_size'] == 0:
            return []

        control_mean = control['metric_mean']
        control_n = control['sample_size']

        # Get control variance
        cursor.execute('''
            SELECT AVG((metric_value - ?) * (metric_value - ?)) as variance
            FROM experiment_observations
            WHERE treatment_id = ?
        ''', (control_mean, control_mean, control['id']))

        control_var = cursor.fetchone()['variance'] or 0

        # Analyze each treatment
        results = []

        cursor.execute('''
            SELECT id, treatment_name, metric_mean, sample_size
            FROM experiment_treatments
            WHERE experiment_id = ? AND is_control = 0
        ''', (experiment_id,))

        treatments = cursor.fetchall()

        for treatment in treatments:
            if treatment['sample_size'] == 0:
                continue

            treatment_mean = treatment['metric_mean']
            treatment_n = treatment['sample_size']

            # Get treatment variance
            cursor.execute('''
                SELECT AVG((metric_value - ?) * (metric_value - ?)) as variance
                FROM experiment_observations
                WHERE treatment_id = ?
            ''', (treatment_mean, treatment_mean, treatment['id']))

            treatment_var = cursor.fetchone()['variance'] or 0

            # T-test
            p_value, is_significant = self._t_test(
                control_mean, control_var, control_n,
                treatment_mean, treatment_var, treatment_n
            )

            improvement_pct = ((treatment_mean - control_mean) / control_mean * 100) if control_mean != 0 else 0

            results.append(ExperimentResult(
                experiment_id=experiment_id,
                treatment_name=treatment['treatment_name'],
                metric_value=treatment_mean,
                sample_size=treatment_n,
                confidence=1 - p_value,
                p_value=p_value,
                is_significant=is_significant,
                winner=is_significant and treatment_mean > control_mean
            ))

        return results

    def _t_test(self, mean1: float, var1: float, n1: int,
                mean2: float, var2: float, n2: int) -> tuple:
        """Simple t-test implementation"""
        if n1 < 2 or n2 < 2:
            return 1.0, False

        # Pooled standard error
        pooled_se = ((var1 / n1) + (var2 / n2)) ** 0.5

        if pooled_se == 0:
            return 1.0, False

        # T statistic
        t = abs(mean1 - mean2) / pooled_se

        # Degrees of freedom (simplified)
        df = n1 + n2 - 2

        # Approximate p-value (simplified)
        # For proper implementation, use scipy.stats
        if t > 2.0:  # Roughly corresponds to p < 0.05
            p_value = 0.04
            is_significant = True
        elif t > 1.5:
            p_value = 0.10
            is_significant = False
        else:
            p_value = 0.20
            is_significant = False

        return p_value, is_significant

    # === COMPLETION ===

    def complete_experiment(self, experiment_id: int) -> Dict:
        """
        Complete experiment and determine winner

        Args:
            experiment_id: Experiment ID

        Returns:
            Completion summary
        """
        results = self.analyze_experiment(experiment_id)

        if not results:
            return {'status': 'no_data'}

        # Find winner
        significant_winners = [r for r in results if r.winner]

        if significant_winners:
            # Best significant winner
            winner = max(significant_winners, key=lambda r: r.metric_value)

            # Update experiment
            cursor = self.conn.cursor()
            cursor.execute('''
                UPDATE experiments
                SET status = 'completed',
                    completed_at = CURRENT_TIMESTAMP,
                    winner_treatment = ?,
                    improvement_pct = ?,
                    p_value = ?,
                    confidence = ?
                WHERE id = ?
            ''', (winner.treatment_name,
                  ((winner.metric_value - results[0].metric_value) / results[0].metric_value * 100),
                  winner.p_value,
                  winner.confidence,
                  experiment_id))

            self.conn.commit()

            # Notify
            if self.notifier:
                try:
                    cursor.execute('SELECT name FROM experiments WHERE id = ?', (experiment_id,))
                    name = cursor.fetchone()['name']

                    improvement = ((winner.metric_value - results[0].metric_value) / results[0].metric_value * 100)

                    self.notifier.send_message(
                        f"Experiment Complete: {name}\n"
                        f"Winner: {winner.treatment_name}\n"
                        f"Improvement: {improvement:+.1f}%\n"
                        f"P-value: {winner.p_value:.3f}",
                        priority="success"
                    )
                except:
                    pass

            return {
                'status': 'winner_found',
                'winner': winner.treatment_name,
                'improvement_pct': ((winner.metric_value - results[0].metric_value) / results[0].metric_value * 100),
                'p_value': winner.p_value,
                'confidence': winner.confidence
            }
        else:
            # No significant winner
            cursor = self.conn.cursor()
            cursor.execute('''
                UPDATE experiments
                SET status = 'completed', completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (experiment_id,))
            self.conn.commit()

            return {
                'status': 'no_winner',
                'results': [{'treatment': r.treatment_name, 'p_value': r.p_value} for r in results]
            }

    # === IMPLEMENTATION ===

    def implement_winner(self, experiment_id: int, apply_func: Callable = None) -> bool:
        """
        Implement winning treatment

        Args:
            experiment_id: Experiment ID
            apply_func: Function to apply changes

        Returns:
            Success status
        """
        cursor = self.conn.cursor()

        cursor.execute('''
            SELECT winner_treatment, improvement_pct
            FROM experiments
            WHERE id = ?
        ''', (experiment_id,))

        result = cursor.fetchone()
        if not result or not result['winner_treatment']:
            return False

        winner = result['winner_treatment']

        # Get winner configuration
        cursor.execute('''
            SELECT configuration
            FROM experiment_treatments
            WHERE experiment_id = ? AND treatment_name = ?
        ''', (experiment_id, winner))

        config = json.loads(cursor.fetchone()['configuration'])

        # Apply if function provided
        if apply_func:
            try:
                apply_func(config)
            except Exception as e:
                print(f"[ERROR] Failed to apply winner: {e}")
                return False

        # Record implementation
        cursor.execute('''
            INSERT INTO experiment_implementations
            (experiment_id, treatment_name, actual_improvement, status)
            VALUES (?, ?, ?, 'deployed')
        ''', (experiment_id, winner, result['improvement_pct']))

        self.conn.commit()

        return True

    # === UTILITIES ===

    def get_experiment_status(self, experiment_id: int) -> Dict:
        """Get experiment status"""
        cursor = self.conn.cursor()

        cursor.execute('''
            SELECT e.*, COUNT(DISTINCT et.id) as num_treatments
            FROM experiments e
            LEFT JOIN experiment_treatments et ON e.id = et.experiment_id
            WHERE e.id = ?
            GROUP BY e.id
        ''', (experiment_id,))

        result = cursor.fetchone()
        if not result:
            return {}

        return dict(result)

    def list_experiments(self, status: str = None) -> List[Dict]:
        """List experiments"""
        cursor = self.conn.cursor()

        if status:
            cursor.execute('''
                SELECT * FROM experiments
                WHERE status = ?
                ORDER BY created_at DESC
            ''', (status,))
        else:
            cursor.execute('''
                SELECT * FROM experiments
                ORDER BY created_at DESC
            ''')

        return [dict(row) for row in cursor.fetchall()]

    def close(self):
        """Close database connection"""
        self.conn.close()


# === TEST CODE ===

def main():
    """Test experiment engine"""
    print("Testing Experiment Engine")
    print("=" * 70)

    engine = ExperimentEngine(significance_level=0.05)

    try:
        # Design experiment
        print("\n1. Designing experiment...")
        exp_id = engine.design_experiment(
            name="Test Strategy Optimization",
            hypothesis="Strategy B will improve win rate",
            control={'strategy': 'A', 'params': {'risk': 0.02}},
            treatments=[
                {'strategy': 'B', 'params': {'risk': 0.02}},
                {'strategy': 'C', 'params': {'risk': 0.03}}
            ],
            success_metric="win_rate",
            sample_size=50
        )
        print(f"   Experiment ID: {exp_id}")

        # Start experiment
        print("\n2. Starting experiment...")
        engine.start_experiment(exp_id)

        # Simulate observations
        print("\n3. Simulating observations...")
        import random
        for i in range(50):
            # Control: 55% win rate
            engine.record_observation(exp_id, 'control', random.gauss(0.55, 0.05))

            # Treatment 1: 62% win rate (winner)
            engine.record_observation(exp_id, 'treatment_1', random.gauss(0.62, 0.05))

            # Treatment 2: 57% win rate
            engine.record_observation(exp_id, 'treatment_2', random.gauss(0.57, 0.05))

        print(f"   Recorded 150 observations")

        # Analyze
        print("\n4. Analyzing results...")
        results = engine.analyze_experiment(exp_id)

        for result in results:
            print(f"   {result.treatment_name}:")
            print(f"     Mean: {result.metric_value:.3f}")
            print(f"     P-value: {result.p_value:.3f}")
            print(f"     Significant: {result.is_significant}")
            print(f"     Winner: {result.winner}")

        # Complete
        print("\n5. Completing experiment...")
        summary = engine.complete_experiment(exp_id)

        if summary['status'] == 'winner_found':
            print(f"   Winner: {summary['winner']}")
            print(f"   Improvement: {summary['improvement_pct']:.1f}%")
            print(f"   P-value: {summary['p_value']:.3f}")

        # List experiments
        print("\n6. Listing experiments...")
        experiments = engine.list_experiments()
        print(f"   Total experiments: {len(experiments)}")

        print(f"\n[OK] Experiment Engine working!")
        print(f"Database: {engine.db_path}")

    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        traceback.print_exc()
    finally:
        engine.close()


if __name__ == "__main__":
    main()
