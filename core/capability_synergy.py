#!/usr/bin/env python3
"""
Cross-Capability Synergy System - Intelligence Chain Engine

Automates workflows connecting multiple capabilities to create emergent intelligence.
Discovers synergies between systems and provides comprehensive insights.

Author: AI Self-Improvement System
Created: 2026-02-03
"""

import sqlite3
import json
import hashlib
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import traceback


@dataclass
class ChainStep:
    """A single step in an intelligence chain"""
    capability_name: str
    capability_module: str
    capability_class: str
    method_name: str
    input_mapping: Dict[str, str]  # Maps chain context to method params
    output_key: str  # Key to store output in chain context
    config: Dict[str, Any]  # Additional configuration


@dataclass
class ChainDefinition:
    """Definition of an intelligence chain"""
    id: Optional[int]
    name: str
    description: str
    steps: List[ChainStep]
    trigger_type: str  # 'manual', 'file_change', 'time_interval', 'event', 'threshold'
    trigger_config: Dict[str, Any]
    enabled: bool
    created_at: str
    last_executed: Optional[str]


@dataclass
class ChainExecution:
    """Record of a chain execution"""
    id: Optional[int]
    chain_id: int
    chain_name: str
    start_time: str
    end_time: Optional[str]
    status: str  # 'running', 'completed', 'failed', 'partial'
    initial_input: Dict[str, Any]
    final_output: Dict[str, Any]
    step_results: List[Dict[str, Any]]
    insights: List[str]
    duration_seconds: float
    error_message: Optional[str]


@dataclass
class SynergyPattern:
    """Discovered synergy pattern between capabilities"""
    id: Optional[int]
    pattern_name: str
    capabilities_involved: List[str]
    description: str
    impact_score: float  # 0-1 scale
    occurrences: int
    example_chains: List[int]
    discovered_at: str
    last_seen: str


class CapabilitySynergy:
    """
    Cross-Capability Synergy System - Creates intelligence chains where capabilities
    automatically enhance each other

    Implements 4 primary synergy chains:
    1. Discovery -> Learning Chain
    2. Analysis -> Action Chain
    3. Memory -> Prediction Chain
    4. Monitoring -> Optimization Chain

    Features:
    - Track data flows between capabilities
    - Measure synergy effectiveness (compound intelligence score)
    - Auto-detect new synergy opportunities
    - Create feedback loops
    """

    def __init__(self, db_path: str = "capability_synergy.db", workspace_root: str = None):
        """Initialize the synergy system"""
        self.db_path = db_path
        self.workspace_root = workspace_root or str(Path(__file__).parent.parent)
        self._db_lock = threading.Lock()
        self._synergy_registry = {}  # from_cap -> to_cap -> transform_func
        self._capability_cache = {}
        self._execution_history = []
        self._init_db()
        self._register_default_synergies()
        self._define_default_chains()

    def _init_db(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Chain definitions
        c.execute('''
            CREATE TABLE IF NOT EXISTS chain_definitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT NOT NULL,
                steps TEXT NOT NULL,
                trigger_type TEXT NOT NULL,
                trigger_config TEXT NOT NULL,
                enabled INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_executed TEXT
            )
        ''')

        # Chain execution history
        c.execute('''
            CREATE TABLE IF NOT EXISTS chain_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chain_id INTEGER NOT NULL,
                chain_name TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                status TEXT NOT NULL,
                initial_input TEXT NOT NULL,
                final_output TEXT,
                step_results TEXT,
                insights TEXT,
                duration_seconds REAL,
                error_message TEXT,
                FOREIGN KEY (chain_id) REFERENCES chain_definitions (id)
            )
        ''')

        # Performance metrics
        c.execute('''
            CREATE TABLE IF NOT EXISTS chain_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chain_id INTEGER NOT NULL,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                recorded_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chain_id) REFERENCES chain_definitions (id)
            )
        ''')

        # Emergent patterns
        c.execute('''
            CREATE TABLE IF NOT EXISTS synergy_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_name TEXT UNIQUE NOT NULL,
                capabilities_involved TEXT NOT NULL,
                description TEXT NOT NULL,
                impact_score REAL DEFAULT 0.5,
                occurrences INTEGER DEFAULT 1,
                example_chains TEXT,
                discovered_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_seen TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Scheduled chains
        c.execute('''
            CREATE TABLE IF NOT EXISTS chain_schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chain_id INTEGER NOT NULL,
                trigger_type TEXT NOT NULL,
                trigger_config TEXT NOT NULL,
                last_triggered TEXT,
                next_trigger TEXT,
                enabled INTEGER DEFAULT 1,
                FOREIGN KEY (chain_id) REFERENCES chain_definitions (id)
            )
        ''')

        # Chain insights (aggregated discoveries)
        c.execute('''
            CREATE TABLE IF NOT EXISTS chain_insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chain_id INTEGER NOT NULL,
                insight_type TEXT NOT NULL,
                insight_text TEXT NOT NULL,
                confidence REAL DEFAULT 0.5,
                supporting_data TEXT,
                discovered_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chain_id) REFERENCES chain_definitions (id)
            )
        ''')

        # Synergy registrations (capability connections)
        c.execute('''
            CREATE TABLE IF NOT EXISTS synergy_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_capability TEXT NOT NULL,
                to_capability TEXT NOT NULL,
                transform_function TEXT NOT NULL,
                registered_at TEXT DEFAULT CURRENT_TIMESTAMP,
                usage_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                UNIQUE(from_capability, to_capability)
            )
        ''')

        # Synergy flows (data flowing between capabilities)
        c.execute('''
            CREATE TABLE IF NOT EXISTS synergy_flows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id INTEGER,
                from_capability TEXT NOT NULL,
                to_capability TEXT NOT NULL,
                data_type TEXT NOT NULL,
                data_size INTEGER DEFAULT 0,
                impact_score REAL DEFAULT 0.5,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Compound intelligence scores
        c.execute('''
            CREATE TABLE IF NOT EXISTS intelligence_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chain_id INTEGER NOT NULL,
                execution_id INTEGER NOT NULL,
                base_score REAL DEFAULT 0.0,
                synergy_multiplier REAL DEFAULT 1.0,
                compound_score REAL DEFAULT 0.0,
                factors TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chain_id) REFERENCES chain_definitions (id)
            )
        ''')

        # Feedback loops
        c.execute('''
            CREATE TABLE IF NOT EXISTS feedback_loops (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                loop_name TEXT UNIQUE NOT NULL,
                capabilities_involved TEXT NOT NULL,
                loop_type TEXT NOT NULL,
                iterations INTEGER DEFAULT 0,
                effectiveness_score REAL DEFAULT 0.5,
                last_iteration TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()

    def register_synergy(self, from_capability: str, to_capability: str,
                        transform_func: Callable) -> bool:
        """
        Register a synergy between two capabilities

        Args:
            from_capability: Source capability name
            to_capability: Destination capability name
            transform_func: Function to transform data from source to destination
                           signature: func(output_data: Any) -> Dict[str, Any]

        Returns:
            Success status
        """
        # Store in memory registry
        if from_capability not in self._synergy_registry:
            self._synergy_registry[from_capability] = {}
        self._synergy_registry[from_capability][to_capability] = transform_func

        # Store in database
        with self._db_lock:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()

            try:
                c.execute('''
                    INSERT INTO synergy_registry
                    (from_capability, to_capability, transform_function)
                    VALUES (?, ?, ?)
                ''', (from_capability, to_capability, transform_func.__name__))
                conn.commit()
            except sqlite3.IntegrityError:
                # Already exists, update it
                c.execute('''
                    UPDATE synergy_registry
                    SET transform_function=?
                    WHERE from_capability=? AND to_capability=?
                ''', (transform_func.__name__, from_capability, to_capability))
                conn.commit()
            finally:
                conn.close()

        return True

    def execute_chain(self, chain_name: str, input_data: Dict[str, Any]) -> Dict:
        """
        Execute a named intelligence chain

        Args:
            chain_name: Name of the chain to execute
            input_data: Initial input data

        Returns:
            Dictionary with execution results, insights, and synergy data
        """
        # Find chain by name
        with self._db_lock:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('SELECT id FROM chain_definitions WHERE name=?', (chain_name,))
            row = c.fetchone()
            conn.close()

        if not row:
            return {
                'status': 'error',
                'error': f"Chain '{chain_name}' not found",
                'available_chains': self._get_available_chains()
            }

        chain_id = row[0]

        # Execute using internal method
        result = self._execute_chain_by_id(chain_id, input_data)

        # Calculate compound intelligence score
        compound_score = self._calculate_compound_intelligence(chain_id, result)
        result['compound_intelligence_score'] = compound_score

        return result

    def measure_synergy_impact(self) -> Dict:
        """
        Measure the effectiveness of synergies

        Returns:
            Dictionary with synergy impact metrics
        """
        with self._db_lock:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()

            # Get synergy usage stats
            c.execute('''
                SELECT from_capability, to_capability, usage_count, success_count
                FROM synergy_registry
                ORDER BY usage_count DESC
            ''')
            synergies = []
            for row in c.fetchall():
                from_cap, to_cap, usage, success = row
                success_rate = success / usage if usage > 0 else 0
                synergies.append({
                    'from': from_cap,
                    'to': to_cap,
                    'usage_count': usage,
                    'success_count': success,
                    'success_rate': success_rate
                })

            # Get synergy flow statistics
            c.execute('''
                SELECT from_capability, to_capability,
                       COUNT(*) as flow_count,
                       AVG(impact_score) as avg_impact
                FROM synergy_flows
                GROUP BY from_capability, to_capability
                ORDER BY flow_count DESC
            ''')
            flows = []
            for row in c.fetchall():
                flows.append({
                    'from': row[0],
                    'to': row[1],
                    'flow_count': row[2],
                    'avg_impact': row[3]
                })

            # Get average compound intelligence scores
            c.execute('''
                SELECT AVG(compound_score) as avg_compound,
                       AVG(synergy_multiplier) as avg_multiplier
                FROM intelligence_scores
            ''')
            row = c.fetchone()
            avg_compound = row[0] or 0
            avg_multiplier = row[1] or 1.0

            # Get total synergies and active chains
            c.execute('SELECT COUNT(*) FROM synergy_registry')
            total_synergies = c.fetchone()[0]

            c.execute('SELECT COUNT(*) FROM chain_definitions WHERE enabled=1')
            active_chains = c.fetchone()[0]

            conn.close()

        return {
            'total_synergies': total_synergies,
            'active_chains': active_chains,
            'synergy_connections': synergies,
            'data_flows': flows,
            'average_compound_score': avg_compound,
            'average_synergy_multiplier': avg_multiplier,
            'overall_impact': self._calculate_overall_impact(synergies, flows)
        }

    def discover_new_synergies(self) -> List[Dict]:
        """
        Analyze execution history to discover new synergy opportunities

        Returns:
            List of potential synergy opportunities
        """
        opportunities = []

        with self._db_lock:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()

            # Find capability pairs that appear together but aren't synergized
            c.execute('''
                SELECT DISTINCT cd.steps
                FROM chain_definitions cd
                WHERE cd.enabled = 1
            ''')

            capability_pairs = set()
            for row in c.fetchall():
                steps = json.loads(row[0])
                step_names = [s['capability_name'] for s in steps]

                # Find sequential pairs
                for i in range(len(step_names) - 1):
                    cap1, cap2 = step_names[i], step_names[i + 1]
                    capability_pairs.add((cap1, cap2))

            # Check which pairs don't have synergies yet
            for cap1, cap2 in capability_pairs:
                c.execute('''
                    SELECT id FROM synergy_registry
                    WHERE from_capability=? AND to_capability=?
                ''', (cap1, cap2))

                if not c.fetchone():
                    # This is a potential synergy opportunity
                    # Calculate potential impact based on co-occurrence
                    c.execute('''
                        SELECT COUNT(*) FROM chain_executions ce
                        JOIN chain_definitions cd ON ce.chain_id = cd.id
                        WHERE cd.steps LIKE ?
                    ''', (f'%{cap1}%',))
                    occurrences = c.fetchone()[0]

                    opportunities.append({
                        'from_capability': cap1,
                        'to_capability': cap2,
                        'reason': 'Frequently appear together in chains',
                        'co_occurrence_count': occurrences,
                        'potential_impact': min(0.9, occurrences * 0.1),
                        'recommendation': f'Consider adding transform function from {cap1} to {cap2}'
                    })

            conn.close()

        # Sort by potential impact
        opportunities.sort(key=lambda x: x['potential_impact'], reverse=True)

        return opportunities

    def get_compound_intelligence_score(self) -> float:
        """
        Calculate overall compound intelligence score for the system

        Returns:
            Compound intelligence score (0.0-1.0)
        """
        with self._db_lock:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()

            # Get recent compound scores
            c.execute('''
                SELECT compound_score
                FROM intelligence_scores
                ORDER BY timestamp DESC
                LIMIT 100
            ''')
            scores = [row[0] for row in c.fetchall()]

            if not scores:
                conn.close()
                return 0.0

            # Calculate weighted average (recent scores weighted more)
            weights = [1.0 / (i + 1) for i in range(len(scores))]
            weighted_sum = sum(s * w for s, w in zip(scores, weights))
            weight_total = sum(weights)

            avg_score = weighted_sum / weight_total

            # Factor in number of active synergies
            c.execute('SELECT COUNT(*) FROM synergy_registry WHERE usage_count > 0')
            active_synergies = c.fetchone()[0]

            # Factor in feedback loops
            c.execute('SELECT COUNT(*) FROM feedback_loops WHERE iterations > 0')
            active_loops = c.fetchone()[0]

            conn.close()

        # Compound score with bonuses for active synergies and feedback loops
        synergy_bonus = min(0.2, active_synergies * 0.02)
        loop_bonus = min(0.1, active_loops * 0.05)

        compound_score = min(1.0, avg_score + synergy_bonus + loop_bonus)

        return compound_score

    def _get_available_chains(self) -> List[str]:
        """Get list of available chain names"""
        with self._db_lock:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('SELECT name FROM chain_definitions ORDER BY name')
            chains = [row[0] for row in c.fetchall()]
            conn.close()
            return chains

    def _execute_chain_by_id(self, chain_id: int, initial_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a chain by ID (internal method)"""
        start_time = datetime.now()

        # Load chain definition
        with self._db_lock:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('SELECT * FROM chain_definitions WHERE id=?', (chain_id,))
            row = c.fetchone()
            conn.close()

        if not row:
            return {
                'execution_id': None,
                'chain_id': chain_id,
                'chain_name': 'unknown',
                'status': 'error',
                'duration_seconds': 0,
                'step_results': [],
                'insights': [],
                'context': initial_input,
                'error': f"Chain ID {chain_id} not found"
            }

        chain_name = row[1]
        description = row[2]
        steps_json = row[3]

        steps = [ChainStep(**s) for s in json.loads(steps_json)]

        # Create execution record
        execution_id = self._create_execution_record(chain_id, chain_name, initial_input)

        # Execute chain with synergy tracking
        context = initial_input.copy()
        step_results = []
        insights = []
        status = 'completed'
        error_message = None

        try:
            for i, step in enumerate(steps):
                print(f"[Chain {chain_name}] Step {i+1}/{len(steps)}: {step.capability_name}")

                try:
                    # Load capability
                    capability = self._load_capability(
                        step.capability_module,
                        step.capability_class,
                        step.config
                    )

                    # Map inputs from context
                    method_inputs = {}
                    for param_name, context_key in step.input_mapping.items():
                        if context_key in context:
                            method_inputs[param_name] = context[context_key]
                        else:
                            print(f"  [Warning] Context key '{context_key}' not found for param '{param_name}'")

                    # Execute step
                    method = getattr(capability, step.method_name)
                    result = method(**method_inputs)

                    # Apply synergies to result
                    if i < len(steps) - 1:
                        next_step = steps[i + 1]
                        result = self._apply_synergy(
                            step.capability_name,
                            next_step.capability_name,
                            result,
                            execution_id
                        )

                    # Store result in context
                    context[step.output_key] = result

                    step_results.append({
                        'step': i + 1,
                        'capability': step.capability_name,
                        'method': step.method_name,
                        'status': 'success',
                        'result_summary': self._summarize_result(result)
                    })

                    # Extract insights from this step
                    step_insights = self._extract_step_insights(step, result, context)
                    insights.extend(step_insights)

                except Exception as e:
                    error = f"Step {i+1} failed: {str(e)}"
                    print(f"  [Error] {error}")
                    step_results.append({
                        'step': i + 1,
                        'capability': step.capability_name,
                        'method': step.method_name,
                        'status': 'failed',
                        'error': str(e)
                    })
                    status = 'partial'

            # Generate final insights
            final_insights = self._generate_chain_insights(
                chain_name, context, step_results, insights
            )
            insights.extend(final_insights)

        except Exception as e:
            status = 'failed'
            error_message = f"Chain execution failed: {str(e)}\n{traceback.format_exc()}"
            print(f"[Chain {chain_name}] Failed: {error_message}")

        # Calculate duration
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Update execution record
        self._update_execution_record(
            execution_id, status, context, step_results,
            insights, duration, error_message
        )

        # Update chain last_executed
        with self._db_lock:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute(
                'UPDATE chain_definitions SET last_executed=? WHERE id=?',
                (datetime.now().isoformat(), chain_id)
            )
            conn.commit()
            conn.close()

        # Record metrics
        self._record_chain_metrics(chain_id, duration, len(insights), status)

        # Discover patterns
        self._discover_patterns(chain_id, chain_name, steps, context, insights)

        return {
            'execution_id': execution_id,
            'chain_id': chain_id,
            'chain_name': chain_name,
            'status': status,
            'duration_seconds': duration,
            'step_results': step_results,
            'insights': insights,
            'context': context,
            'error': error_message
        }

    def _apply_synergy(self, from_cap: str, to_cap: str, data: Any,
                      execution_id: int) -> Any:
        """Apply synergy transformation between capabilities"""
        # Check if synergy is registered
        if from_cap in self._synergy_registry:
            if to_cap in self._synergy_registry[from_cap]:
                transform_func = self._synergy_registry[from_cap][to_cap]

                try:
                    # Apply transformation
                    transformed_data = transform_func(data)

                    # Record synergy flow
                    self._record_synergy_flow(
                        execution_id, from_cap, to_cap,
                        type(data).__name__,
                        len(str(data)),
                        0.7  # Default impact score
                    )

                    # Update usage stats
                    with self._db_lock:
                        conn = sqlite3.connect(self.db_path)
                        c = conn.cursor()
                        c.execute('''
                            UPDATE synergy_registry
                            SET usage_count = usage_count + 1,
                                success_count = success_count + 1
                            WHERE from_capability=? AND to_capability=?
                        ''', (from_cap, to_cap))
                        conn.commit()
                        conn.close()

                    return transformed_data

                except Exception as e:
                    print(f"[Synergy] Failed to apply {from_cap} -> {to_cap}: {e}")
                    # Update usage but not success
                    with self._db_lock:
                        conn = sqlite3.connect(self.db_path)
                        c = conn.cursor()
                        c.execute('''
                            UPDATE synergy_registry
                            SET usage_count = usage_count + 1
                            WHERE from_capability=? AND to_capability=?
                        ''', (from_cap, to_cap))
                        conn.commit()
                        conn.close()

        return data  # Return unmodified if no synergy

    def _record_synergy_flow(self, execution_id: int, from_cap: str, to_cap: str,
                            data_type: str, data_size: int, impact_score: float):
        """Record a synergy data flow"""
        with self._db_lock:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('''
                INSERT INTO synergy_flows
                (execution_id, from_capability, to_capability,
                 data_type, data_size, impact_score)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (execution_id, from_cap, to_cap, data_type, data_size, impact_score))
            conn.commit()
            conn.close()

    def _calculate_compound_intelligence(self, chain_id: int, result: Dict) -> float:
        """Calculate compound intelligence score for a chain execution"""
        # Base score from successful steps
        total_steps = len(result.get('step_results', []))
        if total_steps == 0:
            return 0.0

        successful_steps = sum(
            1 for s in result.get('step_results', [])
            if s.get('status') == 'success'
        )
        base_score = successful_steps / total_steps

        # Synergy multiplier based on active synergies in this execution
        execution_id = result.get('execution_id')
        synergy_count = 0

        if execution_id:
            with self._db_lock:
                conn = sqlite3.connect(self.db_path)
                c = conn.cursor()
                c.execute('''
                    SELECT COUNT(*) FROM synergy_flows
                    WHERE execution_id = ?
                ''', (execution_id,))
                synergy_count = c.fetchone()[0]
                conn.close()

        synergy_multiplier = 1.0 + (synergy_count * 0.1)  # 10% bonus per synergy

        # Insight bonus
        insights_count = len(result.get('insights', []))
        insight_bonus = min(0.2, insights_count * 0.02)

        # Calculate compound score
        compound_score = min(1.0, (base_score * synergy_multiplier) + insight_bonus)

        # Store score
        with self._db_lock:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('''
                INSERT INTO intelligence_scores
                (chain_id, execution_id, base_score, synergy_multiplier, compound_score, factors)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                chain_id,
                execution_id,
                base_score,
                synergy_multiplier,
                compound_score,
                json.dumps({
                    'successful_steps': successful_steps,
                    'total_steps': total_steps,
                    'synergy_count': synergy_count,
                    'insights_count': insights_count
                })
            ))
            conn.commit()
            conn.close()

        return compound_score

    def _calculate_overall_impact(self, synergies: List[Dict], flows: List[Dict]) -> float:
        """Calculate overall synergy impact score"""
        if not synergies and not flows:
            return 0.0

        # Average success rate from synergies
        avg_success = sum(s['success_rate'] for s in synergies) / len(synergies) if synergies else 0

        # Average impact from flows
        avg_flow_impact = sum(f['avg_impact'] for f in flows) / len(flows) if flows else 0

        # Combine both factors
        overall_impact = (avg_success * 0.6) + (avg_flow_impact * 0.4)

        return overall_impact

    def _register_default_synergies(self):
        """Register default synergy transformations"""

        # Discovery -> Learning synergies
        def semantic_to_mistake(search_results):
            """Transform semantic search results for mistake learner"""
            if isinstance(search_results, dict) and 'results' in search_results:
                return {
                    'code_patterns': [r.get('content', '') for r in search_results['results'][:5]],
                    'context': 'semantic_search_findings'
                }
            return {'code_patterns': [], 'context': 'semantic_search'}

        def security_to_memory(security_results):
            """Transform security findings for persistent memory"""
            if isinstance(security_results, dict):
                issues = security_results.get('vulnerabilities', [])
                return {
                    'items': [
                        {'type': 'security_issue', 'data': issue}
                        for issue in issues
                    ]
                }
            return {'items': []}

        # Analysis -> Action synergies
        def review_to_debug(review_results):
            """Transform code review findings to debugger actions"""
            if isinstance(review_results, dict):
                recommendations = review_results.get('recommendations', [])
                return {
                    'fix_suggestions': recommendations,
                    'priority': 'medium'
                }
            return {'fix_suggestions': [], 'priority': 'low'}

        # Memory -> Prediction synergies
        def memory_to_prediction(memory_data):
            """Transform memory patterns to predictions"""
            if isinstance(memory_data, dict):
                patterns = memory_data.get('patterns', [])
                return {
                    'historical_patterns': patterns,
                    'confidence_threshold': 0.7
                }
            return {'historical_patterns': [], 'confidence_threshold': 0.5}

        # Register all synergies
        self.register_synergy('SemanticSearch', 'MistakeLearner', semantic_to_mistake)
        self.register_synergy('SecurityScanner', 'PersistentMemory', security_to_memory)
        self.register_synergy('CodeReview', 'AutoDebugger', review_to_debug)
        self.register_synergy('PersistentMemory', 'ErrorPredictor', memory_to_prediction)

        print("[CapabilitySynergy] Registered 4 default synergy transformations")

    def define_chain(self, name: str, description: str, steps: List[Dict],
                    trigger_type: str = 'manual', trigger_config: Dict = None) -> int:
        """
        Define a new intelligence chain

        Args:
            name: Chain name
            description: What the chain does
            steps: List of step dictionaries with capability info
            trigger_type: How to trigger the chain
            trigger_config: Configuration for the trigger

        Returns:
            Chain ID
        """
        trigger_config = trigger_config or {}

        # Convert step dicts to ChainStep objects
        chain_steps = []
        for step in steps:
            chain_steps.append(ChainStep(
                capability_name=step['capability_name'],
                capability_module=step['capability_module'],
                capability_class=step['capability_class'],
                method_name=step['method_name'],
                input_mapping=step.get('input_mapping', {}),
                output_key=step.get('output_key', step['capability_name']),
                config=step.get('config', {})
            ))

        with self._db_lock:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()

            try:
                c.execute('''
                    INSERT INTO chain_definitions
                    (name, description, steps, trigger_type, trigger_config, enabled)
                    VALUES (?, ?, ?, ?, ?, 1)
                ''', (
                    name,
                    description,
                    json.dumps([asdict(s) for s in chain_steps]),
                    trigger_type,
                    json.dumps(trigger_config)
                ))
                chain_id = c.lastrowid
                conn.commit()
                return chain_id
            except sqlite3.IntegrityError:
                # Chain already exists, update it
                c.execute('''
                    UPDATE chain_definitions
                    SET description=?, steps=?, trigger_type=?, trigger_config=?
                    WHERE name=?
                ''', (
                    description,
                    json.dumps([asdict(s) for s in chain_steps]),
                    trigger_type,
                    json.dumps(trigger_config),
                    name
                ))
                c.execute('SELECT id FROM chain_definitions WHERE name=?', (name,))
                chain_id = c.fetchone()[0]
                conn.commit()
                return chain_id
            finally:
                conn.close()

    def schedule_chain(self, chain_id: int, trigger: str, config: Dict = None) -> bool:
        """
        Schedule a chain for automatic execution

        Args:
            chain_id: Chain to schedule
            trigger: Trigger type ('time_interval', 'file_change', 'event', 'threshold')
            config: Trigger configuration

        Returns:
            Success status
        """
        config = config or {}

        with self._db_lock:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()

            # Calculate next trigger time for time_interval
            next_trigger = None
            if trigger == 'time_interval' and 'interval_seconds' in config:
                next_trigger = (
                    datetime.now() + timedelta(seconds=config['interval_seconds'])
                ).isoformat()

            c.execute('''
                INSERT OR REPLACE INTO chain_schedules
                (chain_id, trigger_type, trigger_config, next_trigger, enabled)
                VALUES (?, ?, ?, ?, 1)
            ''', (chain_id, trigger, json.dumps(config), next_trigger))

            conn.commit()
            conn.close()

        return True

    def get_synergy_insights(self, limit: int = 20) -> List[Dict]:
        """
        Get synergy insights from chain executions

        Args:
            limit: Maximum number of insights to return

        Returns:
            List of insight dictionaries
        """
        with self._db_lock:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()

            c.execute('''
                SELECT
                    ci.chain_id,
                    cd.name as chain_name,
                    ci.insight_type,
                    ci.insight_text,
                    ci.confidence,
                    ci.supporting_data,
                    ci.discovered_at
                FROM chain_insights ci
                JOIN chain_definitions cd ON ci.chain_id = cd.id
                ORDER BY ci.discovered_at DESC
                LIMIT ?
            ''', (limit,))

            insights = []
            for row in c.fetchall():
                insights.append({
                    'chain_id': row[0],
                    'chain_name': row[1],
                    'insight_type': row[2],
                    'insight_text': row[3],
                    'confidence': row[4],
                    'supporting_data': json.loads(row[5]) if row[5] else None,
                    'discovered_at': row[6]
                })

            conn.close()
            return insights

    def discover_emergent_patterns(self) -> List[Dict]:
        """
        Discover emergent patterns from chain executions

        Returns:
            List of discovered patterns
        """
        with self._db_lock:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()

            # Get all patterns
            c.execute('''
                SELECT
                    pattern_name,
                    capabilities_involved,
                    description,
                    impact_score,
                    occurrences,
                    example_chains,
                    last_seen
                FROM synergy_patterns
                ORDER BY impact_score DESC, occurrences DESC
            ''')

            patterns = []
            for row in c.fetchall():
                patterns.append({
                    'pattern_name': row[0],
                    'capabilities_involved': json.loads(row[1]),
                    'description': row[2],
                    'impact_score': row[3],
                    'occurrences': row[4],
                    'example_chains': json.loads(row[5]),
                    'last_seen': row[6]
                })

            conn.close()
            return patterns

    def get_chain_status(self, chain_id: int) -> Dict:
        """Get status and metrics for a chain"""
        with self._db_lock:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()

            # Get chain info
            c.execute('SELECT * FROM chain_definitions WHERE id=?', (chain_id,))
            row = c.fetchone()

            if not row:
                conn.close()
                return {'error': 'Chain not found'}

            # Get execution history
            c.execute('''
                SELECT status, COUNT(*)
                FROM chain_executions
                WHERE chain_id=?
                GROUP BY status
            ''', (chain_id,))
            execution_counts = dict(c.fetchall())

            # Get average duration
            c.execute('''
                SELECT AVG(duration_seconds)
                FROM chain_executions
                WHERE chain_id=? AND status='completed'
            ''', (chain_id,))
            avg_duration = c.fetchone()[0] or 0

            # Get recent insights count
            c.execute('''
                SELECT COUNT(*)
                FROM chain_insights
                WHERE chain_id=?
            ''', (chain_id,))
            insights_count = c.fetchone()[0]

            conn.close()

            return {
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'enabled': bool(row[6]),
                'last_executed': row[8],
                'executions': execution_counts,
                'avg_duration_seconds': avg_duration,
                'insights_count': insights_count
            }

    def _load_capability(self, module_name: str, class_name: str, config: Dict) -> Any:
        """Load a capability instance"""
        cache_key = f"{module_name}.{class_name}"

        if cache_key in self._capability_cache:
            return self._capability_cache[cache_key]

        # Import module
        import importlib
        import sys

        # Add workspace to path if not already there
        if self.workspace_root not in sys.path:
            sys.path.insert(0, self.workspace_root)

        module = importlib.import_module(module_name)
        capability_class = getattr(module, class_name)

        # Instantiate with config
        if config:
            instance = capability_class(**config)
        else:
            instance = capability_class()

        self._capability_cache[cache_key] = instance
        return instance

    def _create_execution_record(self, chain_id: int, chain_name: str,
                                initial_input: Dict) -> int:
        """Create a new execution record"""
        with self._db_lock:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('''
                INSERT INTO chain_executions
                (chain_id, chain_name, start_time, status, initial_input)
                VALUES (?, ?, ?, 'running', ?)
            ''', (
                chain_id,
                chain_name,
                datetime.now().isoformat(),
                json.dumps(initial_input)
            ))
            execution_id = c.lastrowid
            conn.commit()
            conn.close()
            return execution_id

    def _update_execution_record(self, execution_id: int, status: str,
                                context: Dict, step_results: List[Dict],
                                insights: List[str], duration: float,
                                error_message: Optional[str]):
        """Update execution record with results"""
        with self._db_lock:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('''
                UPDATE chain_executions
                SET end_time=?, status=?, final_output=?, step_results=?,
                    insights=?, duration_seconds=?, error_message=?
                WHERE id=?
            ''', (
                datetime.now().isoformat(),
                status,
                json.dumps(context),
                json.dumps(step_results),
                json.dumps(insights),
                duration,
                error_message,
                execution_id
            ))
            conn.commit()
            conn.close()

    def _summarize_result(self, result: Any) -> str:
        """Create a summary of a step result"""
        if isinstance(result, dict):
            if 'count' in result or 'total' in result:
                return f"Found {result.get('count', result.get('total', 0))} items"
            return f"Dict with {len(result)} keys"
        elif isinstance(result, list):
            return f"List with {len(result)} items"
        elif isinstance(result, str):
            return f"String ({len(result)} chars)"
        else:
            return f"{type(result).__name__}"

    def _extract_step_insights(self, step: ChainStep, result: Any,
                              context: Dict) -> List[str]:
        """Extract insights from a step result"""
        insights = []

        # Check for common insight patterns
        if isinstance(result, dict):
            if 'issues' in result and result['issues']:
                count = len(result['issues']) if isinstance(result['issues'], list) else result['issues']
                insights.append(
                    f"{step.capability_name} found {count} issues requiring attention"
                )

            if 'patterns' in result and result['patterns']:
                count = len(result['patterns']) if isinstance(result['patterns'], list) else result['patterns']
                insights.append(
                    f"{step.capability_name} identified {count} patterns"
                )

            if 'recommendations' in result and result['recommendations']:
                insights.append(
                    f"{step.capability_name} generated recommendations for improvement"
                )

        return insights

    def _generate_chain_insights(self, chain_name: str, context: Dict,
                                step_results: List[Dict],
                                step_insights: List[str]) -> List[str]:
        """Generate high-level insights from entire chain execution"""
        insights = []

        # Count successes and failures
        success_count = sum(1 for s in step_results if s.get('status') == 'success')
        total_steps = len(step_results)

        if success_count == total_steps:
            insights.append(
                f"Chain '{chain_name}' completed all {total_steps} steps successfully"
            )
        elif success_count > 0:
            insights.append(
                f"Chain '{chain_name}' completed {success_count}/{total_steps} steps"
            )

        # Check for cross-capability discoveries
        if len(step_insights) > 2:
            insights.append(
                f"Chain discovered {len(step_insights)} insights through capability synergy"
            )

        return insights

    def _record_chain_metrics(self, chain_id: int, duration: float,
                             insights_count: int, status: str):
        """Record performance metrics for a chain"""
        with self._db_lock:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()

            metrics = [
                ('duration_seconds', duration),
                ('insights_generated', insights_count),
                ('success' if status == 'completed' else 'failure', 1)
            ]

            for metric_name, value in metrics:
                c.execute('''
                    INSERT INTO chain_metrics (chain_id, metric_name, metric_value)
                    VALUES (?, ?, ?)
                ''', (chain_id, metric_name, value))

            conn.commit()
            conn.close()

    def _discover_patterns(self, chain_id: int, chain_name: str,
                          steps: List[ChainStep], context: Dict,
                          insights: List[str]):
        """Discover emergent patterns from chain execution"""
        # Extract capability names
        capabilities = [step.capability_name for step in steps]

        # Create pattern signature
        pattern_sig = hashlib.md5(
            json.dumps(sorted(capabilities)).encode()
        ).hexdigest()[:8]

        pattern_name = f"synergy_{pattern_sig}"

        # Check if this pattern exists
        with self._db_lock:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()

            c.execute(
                'SELECT id, occurrences, example_chains FROM synergy_patterns WHERE pattern_name=?',
                (pattern_name,)
            )
            existing = c.fetchone()

            if existing:
                # Update existing pattern
                pattern_id, occurrences, examples_json = existing
                examples = json.loads(examples_json)
                if chain_id not in examples:
                    examples.append(chain_id)

                c.execute('''
                    UPDATE synergy_patterns
                    SET occurrences=?, example_chains=?, last_seen=?
                    WHERE id=?
                ''', (
                    occurrences + 1,
                    json.dumps(examples),
                    datetime.now().isoformat(),
                    pattern_id
                ))
            else:
                # Create new pattern
                description = f"Synergy between {', '.join(capabilities)}"
                impact_score = min(0.9, len(capabilities) * 0.2)  # More capabilities = higher impact

                c.execute('''
                    INSERT INTO synergy_patterns
                    (pattern_name, capabilities_involved, description,
                     impact_score, occurrences, example_chains)
                    VALUES (?, ?, ?, ?, 1, ?)
                ''', (
                    pattern_name,
                    json.dumps(capabilities),
                    description,
                    impact_score,
                    json.dumps([chain_id])
                ))

            # Store insights
            for insight in insights:
                c.execute('''
                    INSERT INTO chain_insights
                    (chain_id, insight_type, insight_text, confidence)
                    VALUES (?, 'synergy', ?, 0.8)
                ''', (chain_id, insight))

            conn.commit()
            conn.close()

    def _define_default_chains(self):
        """Define the 4 primary synergy chains"""

        # 1. Discovery -> Learning Chain
        self.define_chain(
            name="discovery_learning_chain",
            description="Discovery -> Learning: SemanticSearch findings -> MistakeLearner -> CodeReview suggestions",
            steps=[
                {
                    'capability_name': 'SemanticSearch',
                    'capability_module': 'search.semantic_search',
                    'capability_class': 'SemanticCodeSearch',
                    'method_name': 'search',
                    'input_mapping': {'query': 'search_query'},
                    'output_key': 'search_results',
                    'config': {}
                },
                {
                    'capability_name': 'MistakeLearner',
                    'capability_module': 'learning.mistake_learner',
                    'capability_class': 'MistakeLearner',
                    'method_name': 'check_code_before_suggesting',
                    'input_mapping': {'code': 'code'},
                    'output_key': 'mistake_check',
                    'config': {}
                },
                {
                    'capability_name': 'CodeReview',
                    'capability_module': 'learning.code_review_learner',
                    'capability_class': 'CodeReviewLearner',
                    'method_name': 'check_code_against_preferences',
                    'input_mapping': {'code': 'code', 'language': 'language'},
                    'output_key': 'review_suggestions',
                    'config': {}
                }
            ]
        )

        # 2. Analysis -> Action Chain
        self.define_chain(
            name="analysis_action_chain",
            description="Analysis -> Action: CodeReview findings -> AutoDebugger fixes -> BackgroundTasks cleanup",
            steps=[
                {
                    'capability_name': 'CodeReview',
                    'capability_module': 'learning.code_review_learner',
                    'capability_class': 'CodeReviewLearner',
                    'method_name': 'check_code_against_preferences',
                    'input_mapping': {'code': 'code', 'language': 'language'},
                    'output_key': 'review_results',
                    'config': {}
                },
                {
                    'capability_name': 'MistakeLearner',
                    'capability_module': 'learning.mistake_learner',
                    'capability_class': 'MistakeLearner',
                    'method_name': 'get_correction_suggestions',
                    'input_mapping': {'error_message': 'error_message'},
                    'output_key': 'fix_suggestions',
                    'config': {}
                }
            ]
        )

        # 3. Memory -> Prediction Chain
        self.define_chain(
            name="memory_prediction_chain",
            description="Memory -> Prediction: PersistentMemory patterns -> predict errors -> proactive suggestions",
            steps=[
                {
                    'capability_name': 'MistakeLearner',
                    'capability_module': 'learning.mistake_learner',
                    'capability_class': 'MistakeLearner',
                    'method_name': 'get_recent_mistakes',
                    'input_mapping': {'limit': 'limit'},
                    'output_key': 'recent_mistakes',
                    'config': {}
                },
                {
                    'capability_name': 'CodeReview',
                    'capability_module': 'learning.code_review_learner',
                    'capability_class': 'CodeReviewLearner',
                    'method_name': 'check_code_against_preferences',
                    'input_mapping': {'code': 'code', 'language': 'language'},
                    'output_key': 'proactive_suggestions',
                    'config': {}
                }
            ]
        )

        # 4. Monitoring -> Optimization Chain
        self.define_chain(
            name="monitoring_optimization_chain",
            description="Monitoring -> Optimization: ResourceMonitor alerts -> performance optimization -> auto-cleanup",
            steps=[
                {
                    'capability_name': 'SemanticSearch',
                    'capability_module': 'search.semantic_search',
                    'capability_class': 'SemanticCodeSearch',
                    'method_name': 'get_stats',
                    'input_mapping': {},
                    'output_key': 'search_stats',
                    'config': {}
                },
                {
                    'capability_name': 'MistakeLearner',
                    'capability_module': 'learning.mistake_learner',
                    'capability_class': 'MistakeLearner',
                    'method_name': 'get_learning_stats',
                    'input_mapping': {},
                    'output_key': 'learning_stats',
                    'config': {}
                }
            ]
        )

        print(f"[CapabilitySynergy] Initialized with 4 primary synergy chains")


# Legacy alias for backward compatibility
CapabilitySynergyEngine = CapabilitySynergy


def main():
    """Demo and testing"""
    synergy = CapabilitySynergy()

    print("\n=== Cross-Capability Synergy System Demo ===\n")

    # Show defined chains
    print("Primary Synergy Chains:")
    chains = synergy._get_available_chains()
    for i, chain_name in enumerate(chains, 1):
        status = synergy.get_chain_status(i)
        if 'error' not in status:
            print(f"\n{i}. {status['name']}")
            print(f"   {status['description']}")
            print(f"   Executions: {status.get('executions', {})}")

    # Show synergy impact
    print("\n" + "="*70)
    print("\nSynergy Impact Metrics:")
    impact = synergy.measure_synergy_impact()
    print(f"  Total Synergies: {impact['total_synergies']}")
    print(f"  Active Chains: {impact['active_chains']}")
    print(f"  Average Compound Score: {impact['average_compound_score']:.3f}")

    # Show compound intelligence
    print(f"\nCompound Intelligence Score: {synergy.get_compound_intelligence_score():.3f}")

    # Discover new opportunities
    print("\nDiscovering New Synergy Opportunities...")
    opportunities = synergy.discover_new_synergies()
    if opportunities:
        print(f"Found {len(opportunities)} potential synergies:")
        for opp in opportunities[:3]:
            print(f"  - {opp['from_capability']} -> {opp['to_capability']}")
            print(f"    Potential Impact: {opp['potential_impact']:.2f}")
    else:
        print("  No new opportunities found")

    print("\n" + "="*70)
    print("\nSynergy system ready!")
    print("Use execute_chain(chain_name, input_data) to run intelligence chains.")
    print("Use register_synergy() to add custom capability connections.")


if __name__ == '__main__':
    main()
