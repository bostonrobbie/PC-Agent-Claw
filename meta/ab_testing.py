"""
A/B Testing Everything System
Comprehensive framework for feature flagging, metrics collection, statistical analysis,
automatic rollback, and data-driven improvements measurement.
"""

import sqlite3
import json
import hashlib
import time
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
import math
import os
from pathlib import Path


class ExperimentStatus(Enum):
    """Status of an experiment."""
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ROLLED_BACK = "rolled_back"


class VariantType(Enum):
    """Types of variants."""
    CONTROL = "control"
    TREATMENT = "treatment"


@dataclass
class Variant:
    """Represents an experiment variant."""
    id: str
    name: str
    variant_type: str
    experiment_id: str
    config: Dict[str, Any]


@dataclass
class Metric:
    """Represents a metric for A/B testing."""
    id: str
    experiment_id: str
    variant_id: str
    metric_name: str
    value: float
    timestamp: str
    user_id: str


@dataclass
class Experiment:
    """Represents an A/B test experiment."""
    id: str
    name: str
    description: str
    status: str
    created_at: str
    started_at: Optional[str]
    ended_at: Optional[str]
    confidence_level: float
    min_sample_size: int
    control_variant_id: str
    variants_count: int


class ABTestDatabase:
    """Manages A/B testing database operations."""

    def __init__(self, db_path: str = "ab_testing.db"):
        """Initialize database connection."""
        self.db_path = db_path
        self.connection = None
        self.setup_database()

    def setup_database(self):
        """Create database schema."""
        self.connection = sqlite3.connect(self.db_path)
        cursor = self.connection.cursor()

        # Experiments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS experiments (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                started_at TEXT,
                ended_at TEXT,
                confidence_level REAL DEFAULT 0.95,
                min_sample_size INTEGER DEFAULT 100,
                control_variant_id TEXT,
                FOREIGN KEY (control_variant_id) REFERENCES variants(id)
            )
        """)

        # Variants table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS variants (
                id TEXT PRIMARY KEY,
                experiment_id TEXT NOT NULL,
                name TEXT NOT NULL,
                variant_type TEXT NOT NULL,
                config TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (experiment_id) REFERENCES experiments(id),
                UNIQUE(experiment_id, name)
            )
        """)

        # Metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                id TEXT PRIMARY KEY,
                experiment_id TEXT NOT NULL,
                variant_id TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                value REAL NOT NULL,
                timestamp TEXT NOT NULL,
                user_id TEXT NOT NULL,
                FOREIGN KEY (experiment_id) REFERENCES experiments(id),
                FOREIGN KEY (variant_id) REFERENCES variants(id)
            )
        """)

        # Feature flags table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feature_flags (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                experiment_id TEXT,
                enabled BOOLEAN DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (experiment_id) REFERENCES experiments(id)
            )
        """)

        # Results cache table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS results_cache (
                id TEXT PRIMARY KEY,
                experiment_id TEXT NOT NULL UNIQUE,
                results TEXT NOT NULL,
                cached_at TEXT NOT NULL,
                FOREIGN KEY (experiment_id) REFERENCES experiments(id)
            )
        """)

        # Rollback events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rollback_events (
                id TEXT PRIMARY KEY,
                experiment_id TEXT NOT NULL,
                reason TEXT NOT NULL,
                triggered_at TEXT NOT NULL,
                metrics_snapshot TEXT,
                FOREIGN KEY (experiment_id) REFERENCES experiments(id)
            )
        """)

        self.connection.commit()

    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()

    def execute_query(self, query: str, params: tuple = ()) -> List[tuple]:
        """Execute a SELECT query."""
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

    def execute_update(self, query: str, params: tuple = ()):
        """Execute an INSERT/UPDATE/DELETE query."""
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        self.connection.commit()


class FeatureFlagManager:
    """Manages feature flags for experiments."""

    def __init__(self, db: ABTestDatabase):
        """Initialize with database."""
        self.db = db

    def create_flag(self, name: str, experiment_id: Optional[str] = None, enabled: bool = False) -> str:
        """Create a new feature flag."""
        flag_id = hashlib.md5(f"{name}-{time.time()}".encode()).hexdigest()
        now = datetime.now().isoformat()

        self.db.execute_update(
            """INSERT INTO feature_flags (id, name, experiment_id, enabled, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (flag_id, name, experiment_id, enabled, now, now)
        )
        return flag_id

    def is_enabled(self, name: str) -> bool:
        """Check if a feature flag is enabled."""
        result = self.db.execute_query(
            "SELECT enabled FROM feature_flags WHERE name = ?", (name,)
        )
        return result[0][0] if result else False

    def set_enabled(self, name: str, enabled: bool):
        """Enable or disable a feature flag."""
        now = datetime.now().isoformat()
        self.db.execute_update(
            "UPDATE feature_flags SET enabled = ?, updated_at = ? WHERE name = ?",
            (enabled, now, name)
        )

    def get_flag_status(self, name: str) -> Dict[str, Any]:
        """Get detailed status of a feature flag."""
        result = self.db.execute_query(
            """SELECT id, name, experiment_id, enabled, created_at, updated_at
               FROM feature_flags WHERE name = ?""",
            (name,)
        )
        if result:
            row = result[0]
            return {
                "id": row[0],
                "name": row[1],
                "experiment_id": row[2],
                "enabled": bool(row[3]),
                "created_at": row[4],
                "updated_at": row[5]
            }
        return {}


class ExperimentManager:
    """Manages A/B test experiments."""

    def __init__(self, db: ABTestDatabase):
        """Initialize with database."""
        self.db = db
        self.flag_manager = FeatureFlagManager(db)

    def create_experiment(self, name: str, description: str = "",
                         confidence_level: float = 0.95,
                         min_sample_size: int = 100) -> str:
        """Create a new A/B test experiment."""
        experiment_id = hashlib.md5(f"{name}-{time.time()}".encode()).hexdigest()
        now = datetime.now().isoformat()

        self.db.execute_update(
            """INSERT INTO experiments
               (id, name, description, status, created_at, confidence_level, min_sample_size)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (experiment_id, name, description, ExperimentStatus.DRAFT.value, now, confidence_level, min_sample_size)
        )

        # Create feature flag for the experiment
        self.flag_manager.create_flag(f"exp-{name}", experiment_id)

        return experiment_id

    def add_variant(self, experiment_id: str, name: str, variant_type: str, config: Dict[str, Any]) -> str:
        """Add a variant to an experiment."""
        variant_id = hashlib.md5(f"{experiment_id}-{name}-{time.time()}".encode()).hexdigest()
        now = datetime.now().isoformat()

        self.db.execute_update(
            """INSERT INTO variants (id, experiment_id, name, variant_type, config, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (variant_id, experiment_id, name, variant_type, json.dumps(config), now)
        )

        # Set control variant
        if variant_type == VariantType.CONTROL.value:
            self.db.execute_update(
                "UPDATE experiments SET control_variant_id = ? WHERE id = ?",
                (variant_id, experiment_id)
            )

        return variant_id

    def start_experiment(self, experiment_id: str):
        """Start an experiment."""
        now = datetime.now().isoformat()
        self.db.execute_update(
            """UPDATE experiments
               SET status = ?, started_at = ?
               WHERE id = ?""",
            (ExperimentStatus.RUNNING.value, now, experiment_id)
        )

        # Enable the feature flag
        experiment = self.get_experiment(experiment_id)
        if experiment:
            self.flag_manager.set_enabled(f"exp-{experiment['name']}", True)

    def stop_experiment(self, experiment_id: str):
        """Stop an experiment."""
        now = datetime.now().isoformat()
        self.db.execute_update(
            """UPDATE experiments
               SET status = ?, ended_at = ?
               WHERE id = ?""",
            (ExperimentStatus.COMPLETED.value, now, experiment_id)
        )

    def get_experiment(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve experiment details."""
        result = self.db.execute_query(
            """SELECT id, name, description, status, created_at, started_at, ended_at,
                      confidence_level, min_sample_size, control_variant_id
               FROM experiments WHERE id = ?""",
            (experiment_id,)
        )
        if result:
            row = result[0]
            return {
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "status": row[3],
                "created_at": row[4],
                "started_at": row[5],
                "ended_at": row[6],
                "confidence_level": row[7],
                "min_sample_size": row[8],
                "control_variant_id": row[9]
            }
        return None

    def list_experiments(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List experiments, optionally filtered by status."""
        if status:
            result = self.db.execute_query(
                """SELECT id, name, description, status, created_at, started_at, ended_at,
                          confidence_level, min_sample_size, control_variant_id
                   FROM experiments WHERE status = ?""",
                (status,)
            )
        else:
            result = self.db.execute_query(
                """SELECT id, name, description, status, created_at, started_at, ended_at,
                          confidence_level, min_sample_size, control_variant_id
                   FROM experiments"""
            )

        experiments = []
        for row in result:
            experiments.append({
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "status": row[3],
                "created_at": row[4],
                "started_at": row[5],
                "ended_at": row[6],
                "confidence_level": row[7],
                "min_sample_size": row[8],
                "control_variant_id": row[9]
            })
        return experiments


class MetricsCollector:
    """Collects and aggregates metrics for A/B tests."""

    def __init__(self, db: ABTestDatabase):
        """Initialize with database."""
        self.db = db

    def record_metric(self, experiment_id: str, variant_id: str, metric_name: str,
                     value: float, user_id: str) -> str:
        """Record a metric for a variant."""
        metric_id = hashlib.md5(f"{variant_id}-{metric_name}-{time.time()}".encode()).hexdigest()
        now = datetime.now().isoformat()

        self.db.execute_update(
            """INSERT INTO metrics (id, experiment_id, variant_id, metric_name, value, timestamp, user_id)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (metric_id, experiment_id, variant_id, metric_name, value, now, user_id)
        )
        return metric_id

    def get_variant_metrics(self, variant_id: str, metric_name: str,
                           hours: int = 24) -> List[Dict[str, Any]]:
        """Get metrics for a variant within a time window."""
        cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()

        result = self.db.execute_query(
            """SELECT id, value, timestamp, user_id FROM metrics
               WHERE variant_id = ? AND metric_name = ? AND timestamp >= ?
               ORDER BY timestamp DESC""",
            (variant_id, metric_name, cutoff_time)
        )

        metrics = []
        for row in result:
            metrics.append({
                "id": row[0],
                "value": row[1],
                "timestamp": row[2],
                "user_id": row[3]
            })
        return metrics

    def get_aggregate_metrics(self, experiment_id: str, metric_name: str) -> Dict[str, Any]:
        """Get aggregated metrics for all variants in an experiment."""
        result = self.db.execute_query(
            """SELECT v.id, v.name, COUNT(*) as count,
                      AVG(m.value) as mean,
                      SQRT(AVG(m.value * m.value) - AVG(m.value) * AVG(m.value)) as stddev,
                      MIN(m.value) as min_val, MAX(m.value) as max_val
               FROM variants v
               LEFT JOIN metrics m ON v.id = m.variant_id AND m.metric_name = ?
               WHERE v.experiment_id = ?
               GROUP BY v.id""",
            (metric_name, experiment_id)
        )

        variants_stats = {}
        for row in result:
            variants_stats[row[1]] = {
                "variant_id": row[0],
                "count": row[2] or 0,
                "mean": row[3] or 0.0,
                "stddev": row[4] or 0.0,
                "min": row[5] or 0.0,
                "max": row[6] or 0.0
            }
        return variants_stats


class StatisticalAnalysis:
    """Performs statistical significance testing."""

    @staticmethod
    def t_test(control_values: List[float], treatment_values: List[float]) -> Dict[str, Any]:
        """Perform independent samples t-test."""
        if len(control_values) < 2 or len(treatment_values) < 2:
            return {"significant": False, "p_value": 1.0, "reason": "Insufficient samples"}

        control_mean = sum(control_values) / len(control_values)
        treatment_mean = sum(treatment_values) / len(treatment_values)

        control_var = sum((x - control_mean) ** 2 for x in control_values) / (len(control_values) - 1)
        treatment_var = sum((x - treatment_mean) ** 2 for x in treatment_values) / (len(treatment_values) - 1)

        pooled_se = math.sqrt((control_var / len(control_values)) + (treatment_var / len(treatment_values)))

        if pooled_se == 0:
            return {"significant": False, "p_value": 1.0, "reason": "Zero variance"}

        t_stat = (treatment_mean - control_mean) / pooled_se
        df = len(control_values) + len(treatment_values) - 2

        # Approximate p-value using normal distribution
        p_value = 2 * (1 - StatisticalAnalysis._norm_cdf(abs(t_stat)))

        return {
            "significant": p_value < 0.05,
            "p_value": p_value,
            "t_statistic": t_stat,
            "control_mean": control_mean,
            "treatment_mean": treatment_mean,
            "effect_size": (treatment_mean - control_mean) / control_mean if control_mean != 0 else 0
        }

    @staticmethod
    def chi_square_test(control_successes: int, control_total: int,
                       treatment_successes: int, treatment_total: int) -> Dict[str, Any]:
        """Perform chi-square test for proportions."""
        if control_total < 1 or treatment_total < 1:
            return {"significant": False, "p_value": 1.0, "reason": "Invalid sample sizes"}

        control_failures = control_total - control_successes
        treatment_failures = treatment_total - treatment_successes

        chi_square = ((control_successes * treatment_failures - control_failures * treatment_successes) ** 2 *
                     (control_total + treatment_total)) / (
                     control_total * treatment_total * (control_successes + treatment_successes) *
                     (control_failures + treatment_failures))

        if (control_successes + treatment_successes) == 0 or (control_failures + treatment_failures) == 0:
            return {"significant": False, "p_value": 1.0, "reason": "Invalid contingency table"}

        # Approximate p-value using chi-square distribution with 1 df
        p_value = 1 - StatisticalAnalysis._chi_square_cdf(chi_square, df=1)

        control_rate = control_successes / control_total
        treatment_rate = treatment_successes / treatment_total

        return {
            "significant": p_value < 0.05,
            "p_value": p_value,
            "chi_square": chi_square,
            "control_rate": control_rate,
            "treatment_rate": treatment_rate,
            "relative_lift": (treatment_rate - control_rate) / control_rate if control_rate != 0 else 0
        }

    @staticmethod
    def _norm_cdf(x: float) -> float:
        """Approximate CDF of standard normal distribution."""
        return (1 + math.erf(x / math.sqrt(2))) / 2

    @staticmethod
    def _chi_square_cdf(x: float, df: int = 1) -> float:
        """Approximate CDF of chi-square distribution."""
        if x <= 0:
            return 0
        if df == 1:
            return 2 * StatisticalAnalysis._norm_cdf(math.sqrt(x)) - 1
        return min(1.0, x / (x + df))


class AutomaticRollback:
    """Manages automatic rollback on regression."""

    def __init__(self, db: ABTestDatabase, metrics_collector: MetricsCollector):
        """Initialize with database and metrics collector."""
        self.db = db
        self.metrics_collector = metrics_collector
        self.regression_threshold = 0.10  # 10% regression threshold

    def check_regression(self, experiment_id: str, metric_name: str) -> Tuple[bool, Dict[str, Any]]:
        """Check for regression in key metrics."""
        agg_metrics = self.metrics_collector.get_aggregate_metrics(experiment_id, metric_name)

        if len(agg_metrics) < 2:
            return False, {"reason": "Insufficient variants"}

        control_variant = None
        treatment_variant = None

        experiment = self.db.execute_query(
            "SELECT control_variant_id FROM experiments WHERE id = ?",
            (experiment_id,)
        )

        if experiment:
            control_id = experiment[0][0]
            for variant_name, stats in agg_metrics.items():
                if stats["variant_id"] == control_id:
                    control_variant = stats
                else:
                    treatment_variant = stats

        if not control_variant or not treatment_variant:
            return False, {"reason": "Control or treatment variant not found"}

        if control_variant["mean"] == 0:
            return False, {"reason": "Control mean is zero"}

        regression_pct = (treatment_variant["mean"] - control_variant["mean"]) / control_variant["mean"]

        is_regression = regression_pct < -self.regression_threshold

        return is_regression, {
            "control_mean": control_variant["mean"],
            "treatment_mean": treatment_variant["mean"],
            "regression_pct": regression_pct,
            "is_regression": is_regression
        }

    def trigger_rollback(self, experiment_id: str, reason: str):
        """Trigger rollback of an experiment."""
        rollback_id = hashlib.md5(f"{experiment_id}-{time.time()}".encode()).hexdigest()
        now = datetime.now().isoformat()

        # Get current metrics snapshot
        agg_metrics = self.db.execute_query(
            """SELECT metric_name, COUNT(*) FROM metrics
               WHERE experiment_id = ? GROUP BY metric_name""",
            (experiment_id,)
        )

        self.db.execute_update(
            """INSERT INTO rollback_events (id, experiment_id, reason, triggered_at, metrics_snapshot)
               VALUES (?, ?, ?, ?, ?)""",
            (rollback_id, experiment_id, reason, now, json.dumps([dict(zip(["metric", "count"], row)) for row in agg_metrics]))
        )

        # Update experiment status
        self.db.execute_update(
            "UPDATE experiments SET status = ? WHERE id = ?",
            (ExperimentStatus.ROLLED_BACK.value, experiment_id)
        )


class ABTestReporter:
    """Generates reports on A/B test results."""

    def __init__(self, db: ABTestDatabase, metrics_collector: MetricsCollector):
        """Initialize with database and metrics collector."""
        self.db = db
        self.metrics_collector = metrics_collector

    def generate_experiment_report(self, experiment_id: str, metric_names: List[str]) -> Dict[str, Any]:
        """Generate comprehensive report for an experiment."""
        experiment = self.db.execute_query(
            """SELECT id, name, status, created_at, started_at, ended_at, confidence_level
               FROM experiments WHERE id = ?""",
            (experiment_id,)
        )

        if not experiment:
            return {"error": "Experiment not found"}

        exp = experiment[0]
        report = {
            "experiment_id": exp[0],
            "name": exp[1],
            "status": exp[2],
            "created_at": exp[3],
            "started_at": exp[4],
            "ended_at": exp[5],
            "confidence_level": exp[6],
            "metric_analyses": {}
        }

        for metric_name in metric_names:
            agg_metrics = self.metrics_collector.get_aggregate_metrics(experiment_id, metric_name)

            if len(agg_metrics) >= 2:
                variants_list = list(agg_metrics.items())
                first_name, first_stats = variants_list[0]
                second_name, second_stats = variants_list[1]

                control_values = [m["value"] for m in self.metrics_collector.get_variant_metrics(
                    first_stats["variant_id"], metric_name)]
                treatment_values = [m["value"] for m in self.metrics_collector.get_variant_metrics(
                    second_stats["variant_id"], metric_name)]

                t_test_result = StatisticalAnalysis.t_test(control_values, treatment_values)

                report["metric_analyses"][metric_name] = {
                    "variants": agg_metrics,
                    "statistical_test": t_test_result
                }

        return report

    def get_rollback_history(self, experiment_id: str) -> List[Dict[str, Any]]:
        """Get rollback history for an experiment."""
        result = self.db.execute_query(
            """SELECT id, reason, triggered_at, metrics_snapshot
               FROM rollback_events WHERE experiment_id = ?
               ORDER BY triggered_at DESC""",
            (experiment_id,)
        )

        rollbacks = []
        for row in result:
            rollbacks.append({
                "id": row[0],
                "reason": row[1],
                "triggered_at": row[2],
                "metrics_snapshot": json.loads(row[3]) if row[3] else {}
            })
        return rollbacks


# ============================================================================
# WORKING TEST CODE
# ============================================================================

def test_ab_testing_system():
    """Comprehensive test of the A/B testing system."""

    # Clean up old database
    db_path = "ab_testing.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    print("=" * 80)
    print("A/B TESTING SYSTEM - COMPREHENSIVE TEST")
    print("=" * 80)

    # Initialize components
    db = ABTestDatabase(db_path)
    exp_manager = ExperimentManager(db)
    metrics_collector = MetricsCollector(db)
    rollback_manager = AutomaticRollback(db, metrics_collector)
    reporter = ABTestReporter(db, metrics_collector)

    # Test 1: Create experiment
    print("\n[TEST 1] Creating A/B Test Experiment")
    exp_id = exp_manager.create_experiment(
        name="Homepage_Button_Color",
        description="Test impact of button color on conversion rate",
        confidence_level=0.95,
        min_sample_size=100
    )
    print(f"[OK] Experiment created: {exp_id}")

    # Test 2: Add variants
    print("\n[TEST 2] Adding Variants")
    control_id = exp_manager.add_variant(
        exp_id, "Blue_Button", VariantType.CONTROL.value, {"color": "blue"}
    )
    treatment_id = exp_manager.add_variant(
        exp_id, "Red_Button", VariantType.TREATMENT.value, {"color": "red"}
    )
    print(f"[OK] Control variant (Blue): {control_id}")
    print(f"[OK] Treatment variant (Red): {treatment_id}")

    # Test 3: Start experiment
    print("\n[TEST 3] Starting Experiment")
    exp_manager.start_experiment(exp_id)
    exp = exp_manager.get_experiment(exp_id)
    print(f"[OK] Experiment status: {exp['status']}")

    # Test 4: Collect metrics
    print("\n[TEST 4] Collecting Metrics (Simulated Data)")
    import random
    random.seed(42)

    # Control metrics (baseline)
    for i in range(150):
        value = random.gauss(0.15, 0.05)  # 15% conversion, 5% stddev
        metrics_collector.record_metric(exp_id, control_id, "conversion_rate", max(0, value), f"user_{i}")

    # Treatment metrics (improved)
    for i in range(150):
        value = random.gauss(0.18, 0.05)  # 18% conversion (20% improvement)
        metrics_collector.record_metric(exp_id, treatment_id, "conversion_rate", max(0, value), f"user_{150+i}")

    print(f"[OK] Recorded metrics for 300 users (150 per variant)")

    # Test 5: Aggregate metrics
    print("\n[TEST 5] Analyzing Metrics")
    agg = metrics_collector.get_aggregate_metrics(exp_id, "conversion_rate")
    for variant_name, stats in agg.items():
        print(f"\n  {variant_name}:")
        print(f"    - Sample size: {stats['count']}")
        print(f"    - Mean: {stats['mean']:.4f}")
        print(f"    - StdDev: {stats['stddev']:.4f}")

    # Test 6: Statistical significance testing
    print("\n[TEST 6] Statistical Significance Testing")
    control_values = [m["value"] for m in metrics_collector.get_variant_metrics(control_id, "conversion_rate")]
    treatment_values = [m["value"] for m in metrics_collector.get_variant_metrics(treatment_id, "conversion_rate")]

    t_test_result = StatisticalAnalysis.t_test(control_values, treatment_values)
    print(f"  T-Test Result:")
    print(f"    - Significant: {t_test_result['significant']}")
    print(f"    - P-value: {t_test_result['p_value']:.6f}")
    print(f"    - Control mean: {t_test_result['control_mean']:.4f}")
    print(f"    - Treatment mean: {t_test_result['treatment_mean']:.4f}")
    print(f"    - Effect size: {t_test_result['effect_size']:.4f}")

    # Test 7: Chi-square test
    print("\n[TEST 7] Chi-Square Test (Conversions vs Non-conversions)")
    control_successes = sum(1 for v in control_values if v > 0.15)
    treatment_successes = sum(1 for v in treatment_values if v > 0.15)

    chi_sq_result = StatisticalAnalysis.chi_square_test(
        control_successes, len(control_values),
        treatment_successes, len(treatment_values)
    )
    print(f"  Chi-Square Result:")
    print(f"    - Significant: {chi_sq_result['significant']}")
    print(f"    - P-value: {chi_sq_result['p_value']:.6f}")
    print(f"    - Control rate: {chi_sq_result['control_rate']:.4f}")
    print(f"    - Treatment rate: {chi_sq_result['treatment_rate']:.4f}")
    print(f"    - Relative lift: {chi_sq_result['relative_lift']:.2%}")

    # Test 8: Regression detection
    print("\n[TEST 8] Regression Detection")
    is_regression, regression_info = rollback_manager.check_regression(exp_id, "conversion_rate")
    print(f"  Regression detected: {is_regression}")
    print(f"  Control mean: {regression_info['control_mean']:.4f}")
    print(f"  Treatment mean: {regression_info['treatment_mean']:.4f}")
    print(f"  Change: {regression_info['regression_pct']:.2%}")

    # Test 9: Feature flags
    print("\n[TEST 9] Feature Flags")
    flag_status = db.execute_query("SELECT enabled FROM feature_flags WHERE name = ?", (f"exp-Homepage_Button_Color",))
    print(f"  Feature flag 'exp-Homepage_Button_Color' enabled: {bool(flag_status[0][0])}")

    # Test 10: Reporting
    print("\n[TEST 10] Generating Report")
    report = reporter.generate_experiment_report(exp_id, ["conversion_rate"])
    print(f"  Experiment: {report['name']}")
    print(f"  Status: {report['status']}")
    print(f"  Metrics analyzed: {list(report['metric_analyses'].keys())}")

    # Test 11: Rollback event
    print("\n[TEST 11] Triggering Rollback")
    rollback_manager.trigger_rollback(exp_id, "Unexpected user engagement drop detected")
    rollback_history = reporter.get_rollback_history(exp_id)
    print(f"  Rollback events: {len(rollback_history)}")
    print(f"  Latest reason: {rollback_history[0]['reason']}")

    # Test 12: Complete experiment
    print("\n[TEST 12] Completing Experiment")
    exp_manager.stop_experiment(exp_id)
    exp = exp_manager.get_experiment(exp_id)
    print(f"  Final status: {exp['status']}")

    # Test 13: List all experiments
    print("\n[TEST 13] Listing All Experiments")
    all_exps = exp_manager.list_experiments()
    print(f"  Total experiments: {len(all_exps)}")
    for e in all_exps:
        print(f"    - {e['name']}: {e['status']}")

    # Clean up
    db.close()

    print("\n" + "=" * 80)
    print("ALL TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    test_ab_testing_system()
