#!/usr/bin/env python3
"""
Self-Improvement & Meta-Learning Engine
Autonomous system for analyzing weaknesses, generating experiments, and improving capabilities

This system enables the agent to:
- Profile its own capabilities and performance
- Identify weaknesses and areas for improvement
- Design and run experiments to test new approaches
- Measure improvement quantitatively
- Update its own code (with permission)
- Track improvement history and learn meta-patterns
"""

import sys
from pathlib import Path
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Callable
from collections import defaultdict, Counter
import traceback
import inspect
import ast
import hashlib

sys.path.append(str(Path(__file__).parent.parent))

try:
    from ml.reinforcement_learning import ReinforcementLearning
except ImportError:
    ReinforcementLearning = None

try:
    from ml.pattern_learner import PatternLearner
except ImportError:
    PatternLearner = None


class SelfImprovementEngine:
    """
    Meta-learning engine for autonomous self-improvement

    Core Features:
    - Capability profiling and benchmarking
    - Weakness identification through performance analysis
    - Experiment generation and execution
    - Quantitative improvement measurement
    - Code modification (with permission)
    - Meta-learning from improvement patterns
    - Integration with RL and pattern detection
    """

    def __init__(self, db_path: str = None, auto_improve: bool = False):
        """
        Initialize self-improvement engine

        Args:
            db_path: Path to database (None for default)
            auto_improve: Whether to automatically apply improvements (requires permission)
        """
        workspace = Path(__file__).parent.parent
        if db_path is None:
            db_path = str(workspace / "meta_learning.db")

        self.db_path = db_path
        self.workspace = workspace
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

        self.auto_improve = auto_improve
        self.improvement_threshold = 0.15  # 15% improvement to be significant

        # Load subsystems
        self.rl_system = None
        self.pattern_learner = None
        self._load_subsystems()

        # Capability registry
        self.capabilities = {}
        self._register_core_capabilities()

    def _init_db(self):
        """Initialize database schema for self-improvement"""
        cursor = self.conn.cursor()

        # Capability profiles - what the agent can do
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS capability_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                capability_name TEXT UNIQUE NOT NULL,
                capability_type TEXT NOT NULL,
                description TEXT,
                baseline_performance REAL,
                current_performance REAL,
                target_performance REAL,
                performance_unit TEXT,
                last_measured TIMESTAMP,
                times_measured INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Weaknesses identified
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS identified_weaknesses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                weakness_name TEXT NOT NULL,
                weakness_type TEXT NOT NULL,
                capability_id INTEGER,
                severity TEXT,
                description TEXT,
                evidence TEXT,
                impact_score REAL,
                identified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved INTEGER DEFAULT 0,
                resolved_at TIMESTAMP,
                FOREIGN KEY (capability_id) REFERENCES capability_profiles(id)
            )
        ''')

        # Improvement experiments
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS improvement_experiments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_name TEXT NOT NULL,
                hypothesis TEXT NOT NULL,
                weakness_id INTEGER,
                approach_description TEXT,
                test_methodology TEXT,
                expected_improvement REAL,
                actual_improvement REAL,
                baseline_measurement REAL,
                new_measurement REAL,
                measurement_unit TEXT,
                status TEXT DEFAULT 'planned',
                result TEXT,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (weakness_id) REFERENCES identified_weaknesses(id)
            )
        ''')

        # Code improvements (applied changes)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS code_improvements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                improvement_name TEXT NOT NULL,
                experiment_id INTEGER,
                file_path TEXT NOT NULL,
                function_name TEXT,
                old_code_hash TEXT,
                new_code_hash TEXT,
                diff_summary TEXT,
                approval_status TEXT DEFAULT 'pending',
                approved_by TEXT,
                applied INTEGER DEFAULT 0,
                rolled_back INTEGER DEFAULT 0,
                performance_before REAL,
                performance_after REAL,
                applied_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (experiment_id) REFERENCES improvement_experiments(id)
            )
        ''')

        # Performance metrics tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                metric_category TEXT,
                metric_value REAL NOT NULL,
                measurement_context TEXT,
                capability_id INTEGER,
                experiment_id INTEGER,
                measured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (capability_id) REFERENCES capability_profiles(id),
                FOREIGN KEY (experiment_id) REFERENCES improvement_experiments(id)
            )
        ''')

        # Meta-learnings (patterns about improvement itself)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS meta_learnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                learning_type TEXT NOT NULL,
                pattern_observed TEXT NOT NULL,
                insight TEXT NOT NULL,
                confidence REAL,
                supporting_experiments TEXT,
                times_validated INTEGER DEFAULT 1,
                learned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Improvement history
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS improvement_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version TEXT NOT NULL,
                summary TEXT,
                improvements_applied INTEGER DEFAULT 0,
                overall_performance_delta REAL,
                notable_changes TEXT,
                deployed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        self.conn.commit()

    def _load_subsystems(self):
        """Load reinforcement learning and pattern detection subsystems"""
        try:
            if ReinforcementLearning:
                self.rl_system = ReinforcementLearning()
        except Exception as e:
            print(f"[WARNING] Could not load RL system: {e}")

        try:
            if PatternLearner:
                self.pattern_learner = PatternLearner()
        except Exception as e:
            print(f"[WARNING] Could not load Pattern Learner: {e}")

    def _register_core_capabilities(self):
        """Register core capabilities that can be measured"""
        core_capabilities = [
            {
                'name': 'task_completion',
                'type': 'execution',
                'description': 'Ability to complete assigned tasks successfully',
                'unit': 'success_rate',
                'target': 0.95
            },
            {
                'name': 'response_time',
                'type': 'performance',
                'description': 'Speed of generating responses',
                'unit': 'seconds',
                'target': 2.0
            },
            {
                'name': 'error_recovery',
                'type': 'reliability',
                'description': 'Ability to recover from errors',
                'unit': 'recovery_rate',
                'target': 0.90
            },
            {
                'name': 'learning_speed',
                'type': 'meta',
                'description': 'How quickly agent learns from mistakes',
                'unit': 'trials_to_master',
                'target': 5.0
            },
            {
                'name': 'code_quality',
                'type': 'output',
                'description': 'Quality of generated code',
                'unit': 'quality_score',
                'target': 0.85
            },
            {
                'name': 'resource_efficiency',
                'type': 'optimization',
                'description': 'Efficient use of compute resources',
                'unit': 'efficiency_score',
                'target': 0.80
            }
        ]

        for cap in core_capabilities:
            self.register_capability(
                cap['name'], cap['type'], cap['description'],
                target_performance=cap['target'],
                performance_unit=cap['unit']
            )

    # === CAPABILITY PROFILING ===

    def register_capability(self, name: str, capability_type: str,
                           description: str = None, baseline_performance: float = None,
                           target_performance: float = None,
                           performance_unit: str = None) -> int:
        """
        Register a capability that can be measured and improved

        Args:
            name: Capability name
            capability_type: Type (execution, performance, reliability, etc.)
            description: What this capability does
            baseline_performance: Initial performance level
            target_performance: Desired performance level
            performance_unit: Unit of measurement

        Returns:
            Capability ID
        """
        cursor = self.conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO capability_profiles
            (capability_name, capability_type, description, baseline_performance,
             current_performance, target_performance, performance_unit)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (name, capability_type, description, baseline_performance,
              baseline_performance, target_performance, performance_unit))

        self.conn.commit()
        capability_id = cursor.lastrowid

        self.capabilities[name] = {
            'id': capability_id,
            'type': capability_type,
            'baseline': baseline_performance,
            'target': target_performance
        }

        return capability_id

    def measure_capability(self, capability_name: str, performance_value: float,
                          context: str = None) -> Dict:
        """
        Measure current performance of a capability

        Args:
            capability_name: Name of capability
            performance_value: Measured performance
            context: Measurement context

        Returns:
            Measurement results with improvement tracking
        """
        cursor = self.conn.cursor()

        # Get capability
        cursor.execute('''
            SELECT id, baseline_performance, current_performance, target_performance,
                   performance_unit, times_measured
            FROM capability_profiles
            WHERE capability_name = ?
        ''', (capability_name,))

        cap = cursor.fetchone()
        if not cap:
            raise ValueError(f"Capability '{capability_name}' not registered")

        cap_id = cap['id']
        baseline = cap['baseline_performance'] or performance_value
        current = cap['current_performance'] or baseline
        target = cap['target_performance']
        times_measured = cap['times_measured']

        # Calculate improvement
        baseline_delta = ((performance_value - baseline) / baseline * 100) if baseline else 0
        current_delta = ((performance_value - current) / current * 100) if current else 0

        # Update capability
        cursor.execute('''
            UPDATE capability_profiles
            SET current_performance = ?,
                last_measured = CURRENT_TIMESTAMP,
                times_measured = times_measured + 1
            WHERE id = ?
        ''', (performance_value, cap_id))

        # Record metric
        cursor.execute('''
            INSERT INTO performance_metrics
            (metric_name, metric_category, metric_value, measurement_context, capability_id)
            VALUES (?, 'capability_measurement', ?, ?, ?)
        ''', (capability_name, performance_value, context, cap_id))

        self.conn.commit()

        # Check if below target (potential weakness)
        is_weakness = False
        if target and performance_value < target:
            gap = ((target - performance_value) / target * 100)
            if gap > 20:  # More than 20% below target
                is_weakness = True
                self._auto_identify_weakness(
                    capability_name,
                    f"Performance {gap:.1f}% below target",
                    cap_id,
                    performance_value,
                    target
                )

        return {
            'capability': capability_name,
            'value': performance_value,
            'unit': cap['performance_unit'],
            'baseline_delta': round(baseline_delta, 2),
            'current_delta': round(current_delta, 2),
            'target': target,
            'at_target': performance_value >= target if target else None,
            'is_weakness': is_weakness,
            'measurements': times_measured + 1
        }

    def profile_all_capabilities(self) -> Dict[str, Any]:
        """
        Get comprehensive profile of all capabilities

        Returns:
            Complete capability profile with performance data
        """
        cursor = self.conn.cursor()

        cursor.execute('''
            SELECT capability_name, capability_type, baseline_performance,
                   current_performance, target_performance, performance_unit,
                   times_measured, last_measured
            FROM capability_profiles
            WHERE is_active = 1
        ''')

        capabilities = []
        for row in cursor.fetchall():
            baseline = row['baseline_performance'] or 0
            current = row['current_performance'] or 0
            target = row['target_performance']

            improvement = ((current - baseline) / baseline * 100) if baseline else 0

            capabilities.append({
                'name': row['capability_name'],
                'type': row['capability_type'],
                'baseline': baseline,
                'current': current,
                'target': target,
                'unit': row['performance_unit'],
                'improvement': round(improvement, 2),
                'at_target': current >= target if target else None,
                'measurements': row['times_measured'],
                'last_measured': row['last_measured']
            })

        # Overall statistics
        total_caps = len(capabilities)
        measured_caps = sum(1 for c in capabilities if c['measurements'] > 0)
        at_target = sum(1 for c in capabilities if c['at_target'])
        avg_improvement = sum(c['improvement'] for c in capabilities) / max(total_caps, 1)

        return {
            'capabilities': capabilities,
            'summary': {
                'total_capabilities': total_caps,
                'measured': measured_caps,
                'at_target': at_target,
                'average_improvement': round(avg_improvement, 2)
            }
        }

    # === WEAKNESS IDENTIFICATION ===

    def _auto_identify_weakness(self, capability_name: str, evidence: str,
                               cap_id: int, current_value: float, target_value: float):
        """Automatically identify weakness from performance measurement"""
        gap_pct = ((target_value - current_value) / target_value * 100)

        if gap_pct > 50:
            severity = 'critical'
            impact = 0.9
        elif gap_pct > 30:
            severity = 'high'
            impact = 0.7
        elif gap_pct > 20:
            severity = 'medium'
            impact = 0.5
        else:
            severity = 'low'
            impact = 0.3

        self.identify_weakness(
            weakness_name=f"{capability_name}_underperformance",
            weakness_type='capability_gap',
            capability_id=cap_id,
            severity=severity,
            description=f"{capability_name} is {gap_pct:.1f}% below target",
            evidence=evidence,
            impact_score=impact
        )

    def identify_weakness(self, weakness_name: str, weakness_type: str,
                         description: str, severity: str = 'medium',
                         capability_id: int = None, evidence: str = None,
                         impact_score: float = 0.5) -> int:
        """
        Identify a weakness that needs improvement

        Args:
            weakness_name: Name of weakness
            weakness_type: Type (capability_gap, reliability, efficiency, etc.)
            description: What is the weakness
            severity: critical, high, medium, low
            capability_id: Related capability
            evidence: Evidence for this weakness
            impact_score: Impact on overall performance (0-1)

        Returns:
            Weakness ID
        """
        cursor = self.conn.cursor()

        # Check if weakness already exists
        cursor.execute('''
            SELECT id FROM identified_weaknesses
            WHERE weakness_name = ? AND resolved = 0
        ''', (weakness_name,))

        existing = cursor.fetchone()
        if existing:
            return existing['id']

        cursor.execute('''
            INSERT INTO identified_weaknesses
            (weakness_name, weakness_type, capability_id, severity,
             description, evidence, impact_score)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (weakness_name, weakness_type, capability_id, severity,
              description, evidence, impact_score))

        self.conn.commit()
        weakness_id = cursor.lastrowid

        # Integrate with RL system
        if self.rl_system:
            try:
                self.rl_system.record_outcome(
                    action_type='weakness_detection',
                    action_name=weakness_name,
                    success=True,
                    outcome_value=impact_score,
                    context={'severity': severity, 'type': weakness_type}
                )
            except:
                pass

        return weakness_id

    def analyze_weaknesses(self, min_impact: float = 0.3) -> List[Dict]:
        """
        Analyze identified weaknesses and prioritize

        Args:
            min_impact: Minimum impact score to include

        Returns:
            List of weaknesses with analysis
        """
        cursor = self.conn.cursor()

        cursor.execute('''
            SELECT w.id, w.weakness_name, w.weakness_type, w.severity,
                   w.description, w.evidence, w.impact_score, w.identified_at,
                   c.capability_name, c.current_performance, c.target_performance
            FROM identified_weaknesses w
            LEFT JOIN capability_profiles c ON w.capability_id = c.id
            WHERE w.resolved = 0 AND w.impact_score >= ?
            ORDER BY w.impact_score DESC, w.identified_at ASC
        ''', (min_impact,))

        weaknesses = []
        for row in cursor.fetchall():
            # Calculate priority score
            severity_weights = {'critical': 1.0, 'high': 0.8, 'medium': 0.5, 'low': 0.3}
            severity_weight = severity_weights.get(row['severity'], 0.5)

            priority_score = row['impact_score'] * severity_weight

            weaknesses.append({
                'id': row['id'],
                'name': row['weakness_name'],
                'type': row['weakness_type'],
                'severity': row['severity'],
                'description': row['description'],
                'evidence': row['evidence'],
                'impact_score': row['impact_score'],
                'priority_score': round(priority_score, 3),
                'capability': row['capability_name'],
                'identified_at': row['identified_at']
            })

        return weaknesses

    # === EXPERIMENT GENERATION ===

    def generate_experiments(self, weakness_id: int,
                            num_experiments: int = 3) -> List[Dict]:
        """
        Generate improvement experiments for a weakness

        Args:
            weakness_id: ID of weakness to address
            num_experiments: Number of experiments to generate

        Returns:
            List of experiment designs
        """
        cursor = self.conn.cursor()

        # Get weakness details
        cursor.execute('''
            SELECT w.*, c.capability_name, c.current_performance, c.target_performance
            FROM identified_weaknesses w
            LEFT JOIN capability_profiles c ON w.capability_id = c.id
            WHERE w.id = ?
        ''', (weakness_id,))

        weakness = cursor.fetchone()
        if not weakness:
            raise ValueError(f"Weakness {weakness_id} not found")

        # Generate experiments based on weakness type
        experiments = []

        if weakness['weakness_type'] == 'capability_gap':
            experiments.extend(self._generate_capability_experiments(weakness, num_experiments))
        elif weakness['weakness_type'] == 'reliability':
            experiments.extend(self._generate_reliability_experiments(weakness, num_experiments))
        elif weakness['weakness_type'] == 'efficiency':
            experiments.extend(self._generate_efficiency_experiments(weakness, num_experiments))
        else:
            experiments.extend(self._generate_general_experiments(weakness, num_experiments))

        # Store experiments
        experiment_ids = []
        for exp in experiments[:num_experiments]:
            exp_id = self._create_experiment(
                experiment_name=exp['name'],
                hypothesis=exp['hypothesis'],
                weakness_id=weakness_id,
                approach_description=exp['approach'],
                test_methodology=exp['test'],
                expected_improvement=exp['expected_improvement']
            )
            exp['id'] = exp_id
            experiment_ids.append(exp_id)

        return experiments[:num_experiments]

    def _generate_capability_experiments(self, weakness: Dict, num: int) -> List[Dict]:
        """Generate experiments for capability gaps"""
        return [
            {
                'name': f"Optimize_{weakness['capability_name']}_v1",
                'hypothesis': f"Improving algorithm efficiency will boost {weakness['capability_name']}",
                'approach': "Optimize core algorithm with better data structures and caching",
                'test': "Measure performance on benchmark suite before/after",
                'expected_improvement': 0.25
            },
            {
                'name': f"Enhance_{weakness['capability_name']}_v2",
                'hypothesis': f"Adding parallel processing will improve {weakness['capability_name']}",
                'approach': "Implement concurrent execution for independent operations",
                'test': "Compare execution time on large workloads",
                'expected_improvement': 0.35
            },
            {
                'name': f"Learn_{weakness['capability_name']}_v3",
                'hypothesis': f"Training on more examples will improve {weakness['capability_name']}",
                'approach': "Collect and learn from additional training examples",
                'test': "Measure accuracy on validation set",
                'expected_improvement': 0.20
            }
        ]

    def _generate_reliability_experiments(self, weakness: Dict, num: int) -> List[Dict]:
        """Generate experiments for reliability issues"""
        return [
            {
                'name': "Add_Error_Handling",
                'hypothesis': "Better error handling will improve reliability",
                'approach': "Add comprehensive try-catch blocks and graceful degradation",
                'test': "Measure error recovery rate in failure scenarios",
                'expected_improvement': 0.30
            },
            {
                'name': "Implement_Retry_Logic",
                'hypothesis': "Automatic retries will reduce failure rate",
                'approach': "Add exponential backoff retry mechanism",
                'test': "Test resilience under intermittent failures",
                'expected_improvement': 0.25
            }
        ]

    def _generate_efficiency_experiments(self, weakness: Dict, num: int) -> List[Dict]:
        """Generate experiments for efficiency issues"""
        return [
            {
                'name': "Implement_Caching",
                'hypothesis': "Caching will reduce redundant computation",
                'approach': "Add LRU cache for expensive operations",
                'test': "Measure resource usage before/after",
                'expected_improvement': 0.40
            },
            {
                'name': "Optimize_Database_Queries",
                'hypothesis': "Query optimization will improve efficiency",
                'approach': "Add indexes and optimize query patterns",
                'test': "Measure query execution time",
                'expected_improvement': 0.35
            }
        ]

    def _generate_general_experiments(self, weakness: Dict, num: int) -> List[Dict]:
        """Generate general improvement experiments"""
        return [
            {
                'name': f"Improve_{weakness['weakness_name']}",
                'hypothesis': f"Targeted optimization will address {weakness['weakness_name']}",
                'approach': "Analyze root cause and apply targeted fix",
                'test': "Measure relevant metrics before/after",
                'expected_improvement': 0.20
            }
        ]

    def _create_experiment(self, experiment_name: str, hypothesis: str,
                          weakness_id: int, approach_description: str,
                          test_methodology: str, expected_improvement: float) -> int:
        """Create experiment record"""
        cursor = self.conn.cursor()

        cursor.execute('''
            INSERT INTO improvement_experiments
            (experiment_name, hypothesis, weakness_id, approach_description,
             test_methodology, expected_improvement, status)
            VALUES (?, ?, ?, ?, ?, ?, 'planned')
        ''', (experiment_name, hypothesis, weakness_id, approach_description,
              test_methodology, expected_improvement))

        self.conn.commit()
        return cursor.lastrowid

    # === TESTING APPROACHES ===

    def test_approach(self, experiment_id: int,
                     test_function: Callable = None,
                     baseline_value: float = None) -> Dict:
        """
        Test an experimental approach

        Args:
            experiment_id: ID of experiment
            test_function: Function to run test (returns performance value)
            baseline_value: Baseline measurement for comparison

        Returns:
            Test results with improvement measurement
        """
        cursor = self.conn.cursor()

        # Get experiment
        cursor.execute('''
            SELECT * FROM improvement_experiments WHERE id = ?
        ''', (experiment_id,))

        exp = cursor.fetchone()
        if not exp:
            raise ValueError(f"Experiment {experiment_id} not found")

        # Update status
        cursor.execute('''
            UPDATE improvement_experiments
            SET status = 'running', started_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (experiment_id,))
        self.conn.commit()

        # Run test
        result = {
            'experiment_id': experiment_id,
            'name': exp['experiment_name'],
            'status': 'completed',
            'error': None
        }

        try:
            if test_function:
                new_value = test_function()
                result['new_measurement'] = new_value
                result['baseline_measurement'] = baseline_value

                if baseline_value:
                    improvement = ((new_value - baseline_value) / baseline_value)
                    result['improvement'] = improvement
                    result['improvement_pct'] = round(improvement * 100, 2)
                    result['success'] = improvement > self.improvement_threshold
                else:
                    result['improvement'] = None
                    result['success'] = True
            else:
                result['status'] = 'manual_testing_required'
                result['success'] = None

        except Exception as e:
            result['status'] = 'failed'
            result['error'] = str(e)
            result['success'] = False

        # Update experiment
        cursor.execute('''
            UPDATE improvement_experiments
            SET status = ?, completed_at = CURRENT_TIMESTAMP,
                result = ?, baseline_measurement = ?, new_measurement = ?,
                actual_improvement = ?
            WHERE id = ?
        ''', (result['status'], result.get('error') or 'Success',
              baseline_value, result.get('new_measurement'),
              result.get('improvement'), experiment_id))
        self.conn.commit()

        # Learn from experiment
        if self.rl_system and result['success'] is not None:
            try:
                self.rl_system.record_outcome(
                    action_type='improvement_experiment',
                    action_name=exp['experiment_name'],
                    success=result['success'],
                    outcome_value=result.get('improvement', 0),
                    context={'weakness_id': exp['weakness_id']}
                )
            except:
                pass

        return result

    # === IMPROVEMENT MEASUREMENT ===

    def measure_improvement(self, before_value: float, after_value: float,
                           metric_name: str, context: str = None) -> Dict:
        """
        Quantitatively measure improvement

        Args:
            before_value: Performance before improvement
            after_value: Performance after improvement
            metric_name: Name of metric
            context: Context for measurement

        Returns:
            Improvement analysis
        """
        # Calculate improvement metrics
        absolute_change = after_value - before_value

        if before_value != 0:
            relative_change = (absolute_change / abs(before_value))
            percent_change = relative_change * 100
        else:
            relative_change = float('inf') if absolute_change > 0 else 0
            percent_change = float('inf') if absolute_change > 0 else 0

        # Determine if improvement is significant
        is_significant = abs(relative_change) >= self.improvement_threshold
        is_improvement = absolute_change > 0  # Assumes higher is better

        # Calculate confidence based on magnitude
        if abs(relative_change) >= 0.5:
            confidence = 'high'
        elif abs(relative_change) >= 0.15:
            confidence = 'medium'
        else:
            confidence = 'low'

        # Record metric
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO performance_metrics
            (metric_name, metric_category, metric_value, measurement_context)
            VALUES (?, 'improvement_measurement', ?, ?)
        ''', (metric_name, after_value, context))
        self.conn.commit()

        return {
            'metric': metric_name,
            'before': before_value,
            'after': after_value,
            'absolute_change': round(absolute_change, 4),
            'relative_change': round(relative_change, 4),
            'percent_change': round(percent_change, 2),
            'is_significant': is_significant,
            'is_improvement': is_improvement,
            'confidence': confidence,
            'context': context
        }

    # === CODE IMPROVEMENT (WITH PERMISSION) ===

    def apply_improvement(self, improvement_name: str, file_path: str,
                         function_name: str = None, new_code: str = None,
                         experiment_id: int = None,
                         require_approval: bool = True) -> Dict:
        """
        Apply code improvement (requires approval unless auto_improve is True)

        Args:
            improvement_name: Name of improvement
            file_path: Path to file to modify
            function_name: Function to modify (None for entire file)
            new_code: New code to apply
            experiment_id: Related experiment
            require_approval: Whether approval is required

        Returns:
            Improvement application result
        """
        # Read current code
        full_path = self.workspace / file_path

        if not full_path.exists():
            return {
                'success': False,
                'error': f"File not found: {file_path}"
            }

        with open(full_path, 'r', encoding='utf-8') as f:
            old_code = f.read()

        old_hash = hashlib.md5(old_code.encode()).hexdigest()

        # Check approval
        approval_status = 'approved' if (self.auto_improve or not require_approval) else 'pending'

        # Create improvement record
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO code_improvements
            (improvement_name, experiment_id, file_path, function_name,
             old_code_hash, approval_status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (improvement_name, experiment_id, file_path, function_name,
              old_hash, approval_status))

        self.conn.commit()
        improvement_id = cursor.lastrowid

        if approval_status == 'pending':
            return {
                'success': False,
                'improvement_id': improvement_id,
                'status': 'pending_approval',
                'message': f"Improvement '{improvement_name}' requires approval. Set auto_improve=True or approve manually."
            }

        # Apply improvement
        try:
            if new_code:
                # Write new code
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(new_code)

                new_hash = hashlib.md5(new_code.encode()).hexdigest()

                # Update record
                cursor.execute('''
                    UPDATE code_improvements
                    SET new_code_hash = ?, applied = 1, applied_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (new_hash, improvement_id))
                self.conn.commit()

                return {
                    'success': True,
                    'improvement_id': improvement_id,
                    'file_path': str(full_path),
                    'old_hash': old_hash,
                    'new_hash': new_hash,
                    'message': f"Applied improvement '{improvement_name}'"
                }
            else:
                return {
                    'success': False,
                    'error': "No new code provided"
                }

        except Exception as e:
            cursor.execute('''
                UPDATE code_improvements
                SET applied = 0
                WHERE id = ?
            ''', (improvement_id,))
            self.conn.commit()

            return {
                'success': False,
                'error': str(e)
            }

    # === IMPROVEMENT TRACKING ===

    def track_improvement_history(self, version: str, summary: str,
                                  improvements_applied: int,
                                  overall_performance_delta: float,
                                  notable_changes: List[str]) -> int:
        """
        Track improvement history for version

        Args:
            version: Version identifier
            summary: Summary of improvements
            improvements_applied: Number of improvements
            overall_performance_delta: Overall performance change
            notable_changes: List of notable changes

        Returns:
            History entry ID
        """
        cursor = self.conn.cursor()

        cursor.execute('''
            INSERT INTO improvement_history
            (version, summary, improvements_applied, overall_performance_delta, notable_changes)
            VALUES (?, ?, ?, ?, ?)
        ''', (version, summary, improvements_applied, overall_performance_delta,
              json.dumps(notable_changes)))

        self.conn.commit()
        return cursor.lastrowid

    def get_improvement_history(self, limit: int = 10) -> List[Dict]:
        """Get improvement history"""
        cursor = self.conn.cursor()

        cursor.execute('''
            SELECT * FROM improvement_history
            ORDER BY deployed_at DESC
            LIMIT ?
        ''', (limit,))

        history = []
        for row in cursor.fetchall():
            history.append({
                'version': row['version'],
                'summary': row['summary'],
                'improvements_applied': row['improvements_applied'],
                'performance_delta': row['overall_performance_delta'],
                'notable_changes': json.loads(row['notable_changes']) if row['notable_changes'] else [],
                'deployed_at': row['deployed_at']
            })

        return history

    # === META-LEARNING ===

    def record_meta_learning(self, learning_type: str, pattern_observed: str,
                            insight: str, confidence: float = 0.7,
                            supporting_experiments: List[int] = None):
        """
        Record meta-learning (learning about the learning process itself)

        Args:
            learning_type: Type of meta-learning
            pattern_observed: What pattern was observed
            insight: Insight gained
            confidence: Confidence in insight
            supporting_experiments: Experiment IDs that support this
        """
        cursor = self.conn.cursor()

        cursor.execute('''
            INSERT INTO meta_learnings
            (learning_type, pattern_observed, insight, confidence, supporting_experiments)
            VALUES (?, ?, ?, ?, ?)
        ''', (learning_type, pattern_observed, insight, confidence,
              json.dumps(supporting_experiments) if supporting_experiments else None))

        self.conn.commit()

    def get_meta_learnings(self, min_confidence: float = 0.5) -> List[Dict]:
        """Get meta-learnings with minimum confidence"""
        cursor = self.conn.cursor()

        cursor.execute('''
            SELECT * FROM meta_learnings
            WHERE confidence >= ?
            ORDER BY times_validated DESC, confidence DESC
        ''', (min_confidence,))

        learnings = []
        for row in cursor.fetchall():
            learnings.append({
                'type': row['learning_type'],
                'pattern': row['pattern_observed'],
                'insight': row['insight'],
                'confidence': row['confidence'],
                'validations': row['times_validated'],
                'learned_at': row['learned_at']
            })

        return learnings

    # === ANALYTICS ===

    def get_self_assessment(self) -> Dict[str, Any]:
        """
        Generate comprehensive self-assessment report

        Returns:
            Complete self-assessment with all metrics
        """
        cursor = self.conn.cursor()

        # Capability summary
        capabilities = self.profile_all_capabilities()

        # Weakness summary
        cursor.execute('''
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN severity = 'critical' THEN 1 ELSE 0 END) as critical,
                   SUM(CASE WHEN severity = 'high' THEN 1 ELSE 0 END) as high,
                   AVG(impact_score) as avg_impact
            FROM identified_weaknesses
            WHERE resolved = 0
        ''')
        weakness_stats = dict(cursor.fetchone())

        # Experiment summary
        cursor.execute('''
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                   AVG(actual_improvement) as avg_improvement
            FROM improvement_experiments
        ''')
        experiment_stats = dict(cursor.fetchone())

        # Applied improvements
        cursor.execute('''
            SELECT COUNT(*) as total,
                   AVG(performance_after - performance_before) as avg_gain
            FROM code_improvements
            WHERE applied = 1
        ''')
        improvement_stats = dict(cursor.fetchone())

        # Overall learning quality
        learning_quality = self._calculate_overall_learning_quality()

        return {
            'timestamp': datetime.now().isoformat(),
            'capabilities': capabilities,
            'weaknesses': {
                'total': weakness_stats['total'],
                'critical': weakness_stats['critical'],
                'high': weakness_stats['high'],
                'avg_impact': round(weakness_stats['avg_impact'] or 0, 3)
            },
            'experiments': {
                'total': experiment_stats['total'],
                'completed': experiment_stats['completed'],
                'avg_improvement': round(experiment_stats['avg_improvement'] or 0, 3)
            },
            'improvements': {
                'total_applied': improvement_stats['total'],
                'avg_performance_gain': round(improvement_stats['avg_gain'] or 0, 3)
            },
            'learning_quality': learning_quality,
            'meta_learnings': len(self.get_meta_learnings())
        }

    def _calculate_overall_learning_quality(self) -> Dict:
        """Calculate overall learning quality metrics"""
        cursor = self.conn.cursor()

        # Improvement rate
        cursor.execute('''
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN actual_improvement > expected_improvement THEN 1 ELSE 0 END) as exceeded
            FROM improvement_experiments
            WHERE status = 'completed' AND actual_improvement IS NOT NULL
        ''')
        exp_result = cursor.fetchone()
        exceeded_rate = exp_result['exceeded'] / max(exp_result['total'], 1) if exp_result['total'] else 0

        # Weakness resolution rate
        cursor.execute('''
            SELECT
                (SELECT COUNT(*) FROM identified_weaknesses WHERE resolved = 1) as resolved,
                (SELECT COUNT(*) FROM identified_weaknesses) as total
        ''')
        weak_result = cursor.fetchone()
        resolution_rate = weak_result['resolved'] / max(weak_result['total'], 1) if weak_result['total'] else 0

        # Overall quality score
        quality_score = (exceeded_rate * 0.6 + resolution_rate * 0.4)

        return {
            'quality_score': round(quality_score, 3),
            'exceeded_expectations': round(exceeded_rate, 3),
            'weakness_resolution': round(resolution_rate, 3),
            'grade': 'A' if quality_score > 0.8 else 'B' if quality_score > 0.6 else 'C' if quality_score > 0.4 else 'D'
        }

    def close(self):
        """Close database connections"""
        self.conn.close()
        if self.rl_system:
            self.rl_system.close()
        if self.pattern_learner:
            self.pattern_learner.close()


# === TEST CODE ===

def main():
    """Test self-improvement engine"""
    print("Testing Self-Improvement & Meta-Learning Engine")
    print("=" * 70)

    engine = SelfImprovementEngine(auto_improve=False)

    try:
        # 1. Profile capabilities
        print("\n1. Profiling capabilities...")
        profile = engine.profile_all_capabilities()
        print(f"   Capabilities registered: {profile['summary']['total_capabilities']}")
        print(f"   Average improvement: {profile['summary']['average_improvement']:.1f}%")

        # 2. Measure a capability
        print("\n2. Measuring capability performance...")
        result = engine.measure_capability('task_completion', 0.82, context='test_run')
        print(f"   Measured: {result['capability']}")
        print(f"   Value: {result['value']:.2f} {result['unit']}")
        print(f"   Is weakness: {result['is_weakness']}")

        # 3. Analyze weaknesses
        print("\n3. Analyzing weaknesses...")
        weaknesses = engine.analyze_weaknesses()
        print(f"   Weaknesses found: {len(weaknesses)}")
        for w in weaknesses[:3]:
            print(f"   - {w['name']} ({w['severity']}): Impact {w['impact_score']:.2f}")

        # 4. Generate experiments
        if weaknesses:
            print("\n4. Generating improvement experiments...")
            experiments = engine.generate_experiments(weaknesses[0]['id'], num_experiments=3)
            print(f"   Generated {len(experiments)} experiments:")
            for exp in experiments:
                print(f"   - {exp['name']}: {exp['hypothesis']}")
                print(f"     Expected improvement: {exp['expected_improvement']:.0%}")

        # 5. Test an approach
        if weaknesses:
            print("\n5. Testing experimental approach...")

            # Simulate test function
            def test_func():
                return 0.90  # Simulated improved performance

            test_result = engine.test_approach(
                experiments[0]['id'],
                test_function=test_func,
                baseline_value=0.82
            )

            print(f"   Test result: {test_result['status']}")
            if test_result.get('improvement'):
                print(f"   Improvement: {test_result['improvement_pct']:.1f}%")
                print(f"   Success: {test_result['success']}")

        # 6. Measure improvement
        print("\n6. Measuring improvement quantitatively...")
        improvement = engine.measure_improvement(
            before_value=0.82,
            after_value=0.90,
            metric_name='task_completion',
            context='post_experiment'
        )
        print(f"   Absolute change: {improvement['absolute_change']:.4f}")
        print(f"   Percent change: {improvement['percent_change']:.1f}%")
        print(f"   Significant: {improvement['is_significant']}")
        print(f"   Confidence: {improvement['confidence']}")

        # 7. Record meta-learning
        print("\n7. Recording meta-learning...")
        engine.record_meta_learning(
            learning_type='experiment_design',
            pattern_observed='Parallel processing experiments consistently show 30%+ improvement',
            insight='Prioritize parallelization for performance improvements',
            confidence=0.85
        )
        print("   Meta-learning recorded")

        # 8. Get self-assessment
        print("\n8. Generating self-assessment...")
        assessment = engine.get_self_assessment()
        print(f"   Learning quality: {assessment['learning_quality']['quality_score']:.2f}")
        print(f"   Grade: {assessment['learning_quality']['grade']}")
        print(f"   Weaknesses: {assessment['weaknesses']['total']}")
        print(f"   Experiments completed: {assessment['experiments']['completed']}")
        print(f"   Improvements applied: {assessment['improvements']['total_applied']}")

        # 9. Get improvement history
        print("\n9. Improvement history...")
        history = engine.get_improvement_history(limit=5)
        print(f"   History entries: {len(history)}")

        # 10. Meta-learnings
        print("\n10. Meta-learnings...")
        learnings = engine.get_meta_learnings()
        print(f"   Meta-learnings: {len(learnings)}")
        for learning in learnings[:3]:
            print(f"   - {learning['pattern']}")
            print(f"     Insight: {learning['insight']}")

        print(f"\n[OK] Self-Improvement Engine working!")
        print(f"Database: {engine.db_path}")
        print(f"\nKey Features Implemented:")
        print("  - Capability profiling and measurement")
        print("  - Automatic weakness identification")
        print("  - Experiment generation and testing")
        print("  - Quantitative improvement measurement")
        print("  - Code improvement tracking (with approval)")
        print("  - Meta-learning system")
        print("  - Integration with RL and pattern detection")
        print("  - Comprehensive self-assessment")

    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        traceback.print_exc()
    finally:
        engine.close()


if __name__ == "__main__":
    main()
