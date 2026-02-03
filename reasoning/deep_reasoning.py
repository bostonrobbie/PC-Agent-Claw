#!/usr/bin/env python3
"""
Deep Reasoning System - Advanced chain-of-thought reasoning with meta-cognition

This system provides sophisticated reasoning capabilities including:
- Chain-of-thought logging
- Plan generation with alternatives
- Outcome simulation
- Causal reasoning
- Counterfactual analysis
- Meta-cognition monitoring
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import traceback


class ReasoningType(Enum):
    """Types of reasoning processes"""
    DEDUCTIVE = "deductive"  # General to specific
    INDUCTIVE = "inductive"  # Specific to general
    ABDUCTIVE = "abductive"  # Best explanation
    CAUSAL = "causal"  # Cause and effect
    COUNTERFACTUAL = "counterfactual"  # What-if scenarios
    ANALOGICAL = "analogical"  # By similarity


class MetaCognitionLevel(Enum):
    """Levels of meta-cognitive awareness"""
    AUTOMATIC = 0  # No self-reflection
    MONITORED = 1  # Basic monitoring
    REFLECTIVE = 2  # Active reflection
    STRATEGIC = 3  # Strategic adjustment
    METACOGNITIVE = 4  # Full self-awareness


class DeepReasoning:
    """
    Advanced reasoning system with chain-of-thought and meta-cognition

    Features:
    - Multi-step reasoning chains with alternatives
    - Plan generation and outcome simulation
    - Causal reasoning and counterfactual analysis
    - Meta-cognitive monitoring and adjustment
    - Assumption tracking and verification
    - Reasoning quality assessment
    """

    def __init__(self, db_path: str = None):
        if db_path is None:
            workspace = Path(__file__).parent.parent
            db_path = workspace / "memory.db"

        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()
        self.current_reasoning_id = None

        # Load Telegram notifier
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from telegram_notifier import TelegramNotifier
            self.notifier = TelegramNotifier()
        except Exception as e:
            print(f"[WARNING] Could not load Telegram notifier: {e}")
            self.notifier = None

    def _init_db(self):
        """Initialize database schema for deep reasoning"""
        cursor = self.conn.cursor()

        # Main reasoning sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reasoning_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_name TEXT NOT NULL,
                goal TEXT NOT NULL,
                reasoning_type TEXT,
                context TEXT,
                final_conclusion TEXT,
                confidence REAL,
                quality_score REAL,
                meta_cognition_level INTEGER DEFAULT 1,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                metadata TEXT
            )
        ''')

        # Chain of thought steps
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS thought_chain (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                step_number INTEGER NOT NULL,
                thought TEXT NOT NULL,
                reasoning_type TEXT,
                confidence REAL DEFAULT 0.5,
                evidence TEXT,
                alternatives TEXT,
                chosen_path TEXT,
                why_chosen TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES reasoning_sessions(id)
            )
        ''')

        # Plans and alternatives
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                plan_name TEXT NOT NULL,
                description TEXT,
                steps TEXT NOT NULL,
                expected_outcome TEXT,
                probability_success REAL,
                cost_estimate REAL,
                time_estimate_hours REAL,
                risks TEXT,
                is_chosen INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES reasoning_sessions(id)
            )
        ''')

        # Outcome simulations
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS outcome_simulations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                plan_id INTEGER,
                scenario_name TEXT NOT NULL,
                conditions TEXT,
                predicted_outcome TEXT,
                probability REAL,
                impact_score REAL,
                timeline TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES reasoning_sessions(id),
                FOREIGN KEY (plan_id) REFERENCES plans(id)
            )
        ''')

        # Causal relationships
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS causal_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                cause TEXT NOT NULL,
                effect TEXT NOT NULL,
                mechanism TEXT,
                confidence REAL,
                evidence TEXT,
                verified INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES reasoning_sessions(id)
            )
        ''')

        # Counterfactual analysis
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS counterfactuals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                original_condition TEXT NOT NULL,
                altered_condition TEXT NOT NULL,
                predicted_outcome TEXT,
                actual_outcome TEXT,
                insight TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES reasoning_sessions(id)
            )
        ''')

        # Meta-cognition monitoring
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS metacognition_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                monitoring_type TEXT NOT NULL,
                observation TEXT,
                adjustment_made TEXT,
                improvement_noted TEXT,
                awareness_level INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES reasoning_sessions(id)
            )
        ''')

        # Assumptions tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reasoning_assumptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                assumption TEXT NOT NULL,
                criticality TEXT,
                validity_confidence REAL,
                verification_status TEXT,
                impact_if_wrong TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES reasoning_sessions(id)
            )
        ''')

        self.conn.commit()

    # === SESSION MANAGEMENT ===

    def start_reasoning_session(self, session_name: str, goal: str,
                               reasoning_type: ReasoningType = ReasoningType.DEDUCTIVE,
                               context: Dict = None, metadata: Dict = None) -> int:
        """Start a new reasoning session"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO reasoning_sessions
            (session_name, goal, reasoning_type, context, metadata)
            VALUES (?, ?, ?, ?, ?)
        ''', (session_name, goal, reasoning_type.value,
              json.dumps(context) if context else None,
              json.dumps(metadata) if metadata else None))
        self.conn.commit()
        self.current_reasoning_id = cursor.lastrowid

        # Log meta-cognition
        self._log_metacognition(
            monitoring_type="session_start",
            observation=f"Starting reasoning session: {session_name}",
            awareness_level=MetaCognitionLevel.MONITORED.value
        )

        return self.current_reasoning_id

    def complete_reasoning_session(self, session_id: int, conclusion: str,
                                  confidence: float, quality_score: float = None):
        """Complete a reasoning session"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE reasoning_sessions
            SET final_conclusion = ?, confidence = ?, quality_score = ?,
                completed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (conclusion, confidence, quality_score, session_id))
        self.conn.commit()

        # Notify if significant finding
        if confidence > 0.8 and self.notifier:
            try:
                self.notifier.send_message(
                    f"Reasoning Complete: {conclusion[:100]}...\nConfidence: {confidence:.0%}",
                    priority="success"
                )
            except Exception as e:
                print(f"[WARNING] Could not send notification: {e}")

        if self.current_reasoning_id == session_id:
            self.current_reasoning_id = None

    # === CHAIN OF THOUGHT ===

    def add_thought(self, thought: str, reasoning_type: ReasoningType = None,
                   confidence: float = 0.5, evidence: List[str] = None,
                   alternatives: List[str] = None, chosen_path: str = None,
                   why_chosen: str = None, session_id: int = None) -> int:
        """Add a thought step to the reasoning chain"""
        if session_id is None:
            session_id = self.current_reasoning_id

        if session_id is None:
            raise ValueError("No active reasoning session. Call start_reasoning_session() first.")

        cursor = self.conn.cursor()

        # Get current step count
        cursor.execute('''
            SELECT COUNT(*) as count FROM thought_chain WHERE session_id = ?
        ''', (session_id,))
        step_number = cursor.fetchone()['count'] + 1

        cursor.execute('''
            INSERT INTO thought_chain
            (session_id, step_number, thought, reasoning_type, confidence,
             evidence, alternatives, chosen_path, why_chosen)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (session_id, step_number, thought,
              reasoning_type.value if reasoning_type else None,
              confidence,
              json.dumps(evidence) if evidence else None,
              json.dumps(alternatives) if alternatives else None,
              chosen_path, why_chosen))
        self.conn.commit()

        # Meta-cognition: Monitor confidence
        if confidence < 0.3:
            self._log_metacognition(
                monitoring_type="low_confidence",
                observation=f"Low confidence ({confidence:.0%}) in step {step_number}",
                adjustment_made="Consider gathering more evidence",
                awareness_level=MetaCognitionLevel.REFLECTIVE.value
            )

        return cursor.lastrowid

    def get_thought_chain(self, session_id: int) -> List[Dict]:
        """Get complete chain of thought for a session"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM thought_chain
            WHERE session_id = ?
            ORDER BY step_number ASC
        ''', (session_id,))
        return [dict(row) for row in cursor.fetchall()]

    # === PLAN GENERATION ===

    def generate_plan(self, plan_name: str, description: str, steps: List[str],
                     expected_outcome: str, probability_success: float = 0.5,
                     cost_estimate: float = None, time_estimate_hours: float = None,
                     risks: List[str] = None, session_id: int = None) -> int:
        """Generate a plan with alternatives"""
        if session_id is None:
            session_id = self.current_reasoning_id

        if session_id is None:
            raise ValueError("No active reasoning session.")

        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO plans
            (session_id, plan_name, description, steps, expected_outcome,
             probability_success, cost_estimate, time_estimate_hours, risks)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (session_id, plan_name, description, json.dumps(steps),
              expected_outcome, probability_success, cost_estimate,
              time_estimate_hours, json.dumps(risks) if risks else None))
        self.conn.commit()
        return cursor.lastrowid

    def choose_plan(self, plan_id: int, rationale: str):
        """Mark a plan as chosen"""
        cursor = self.conn.cursor()

        # Get plan details
        cursor.execute('SELECT * FROM plans WHERE id = ?', (plan_id,))
        plan = dict(cursor.fetchone())

        # Unmark other plans
        cursor.execute('''
            UPDATE plans SET is_chosen = 0 WHERE session_id = ?
        ''', (plan['session_id'],))

        # Mark this plan as chosen
        cursor.execute('UPDATE plans SET is_chosen = 1 WHERE id = ?', (plan_id,))
        self.conn.commit()

        # Log as thought
        self.add_thought(
            thought=f"Chose plan: {plan['plan_name']}",
            reasoning_type=ReasoningType.ABDUCTIVE,
            confidence=plan['probability_success'],
            chosen_path=plan['plan_name'],
            why_chosen=rationale,
            session_id=plan['session_id']
        )

    def get_plans(self, session_id: int) -> List[Dict]:
        """Get all plans for a session"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM plans
            WHERE session_id = ?
            ORDER BY probability_success DESC
        ''', (session_id,))
        return [dict(row) for row in cursor.fetchall()]

    # === OUTCOME SIMULATION ===

    def simulate_outcome(self, scenario_name: str, conditions: Dict,
                        predicted_outcome: str, probability: float,
                        impact_score: float, timeline: str = None,
                        plan_id: int = None, session_id: int = None) -> int:
        """Simulate an outcome under specific conditions"""
        if session_id is None:
            session_id = self.current_reasoning_id

        if session_id is None:
            raise ValueError("No active reasoning session.")

        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO outcome_simulations
            (session_id, plan_id, scenario_name, conditions, predicted_outcome,
             probability, impact_score, timeline)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (session_id, plan_id, scenario_name, json.dumps(conditions),
              predicted_outcome, probability, impact_score, timeline))
        self.conn.commit()
        return cursor.lastrowid

    def get_simulations(self, session_id: int, plan_id: int = None) -> List[Dict]:
        """Get outcome simulations"""
        cursor = self.conn.cursor()
        if plan_id:
            cursor.execute('''
                SELECT * FROM outcome_simulations
                WHERE session_id = ? AND plan_id = ?
                ORDER BY probability DESC
            ''', (session_id, plan_id))
        else:
            cursor.execute('''
                SELECT * FROM outcome_simulations
                WHERE session_id = ?
                ORDER BY impact_score DESC
            ''', (session_id,))
        return [dict(row) for row in cursor.fetchall()]

    # === CAUSAL REASONING ===

    def add_causal_link(self, cause: str, effect: str, mechanism: str = None,
                       confidence: float = 0.5, evidence: List[str] = None,
                       session_id: int = None) -> int:
        """Add a causal relationship"""
        if session_id is None:
            session_id = self.current_reasoning_id

        if session_id is None:
            raise ValueError("No active reasoning session.")

        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO causal_links
            (session_id, cause, effect, mechanism, confidence, evidence)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (session_id, cause, effect, mechanism, confidence,
              json.dumps(evidence) if evidence else None))
        self.conn.commit()
        return cursor.lastrowid

    def verify_causal_link(self, link_id: int, verified: bool):
        """Mark a causal link as verified or not"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE causal_links SET verified = ? WHERE id = ?
        ''', (1 if verified else 0, link_id))
        self.conn.commit()

    def get_causal_chain(self, session_id: int) -> List[Dict]:
        """Get all causal links for a session"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM causal_links
            WHERE session_id = ?
            ORDER BY confidence DESC
        ''', (session_id,))
        return [dict(row) for row in cursor.fetchall()]

    # === COUNTERFACTUAL ANALYSIS ===

    def analyze_counterfactual(self, original_condition: str, altered_condition: str,
                              predicted_outcome: str, insight: str = None,
                              session_id: int = None) -> int:
        """Analyze what-if scenario"""
        if session_id is None:
            session_id = self.current_reasoning_id

        if session_id is None:
            raise ValueError("No active reasoning session.")

        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO counterfactuals
            (session_id, original_condition, altered_condition, predicted_outcome, insight)
            VALUES (?, ?, ?, ?, ?)
        ''', (session_id, original_condition, altered_condition, predicted_outcome, insight))
        self.conn.commit()
        return cursor.lastrowid

    def update_counterfactual_outcome(self, counterfactual_id: int, actual_outcome: str):
        """Update with actual outcome after testing"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE counterfactuals SET actual_outcome = ? WHERE id = ?
        ''', (actual_outcome, counterfactual_id))
        self.conn.commit()

    def get_counterfactuals(self, session_id: int) -> List[Dict]:
        """Get all counterfactual analyses"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM counterfactuals
            WHERE session_id = ?
            ORDER BY created_at DESC
        ''', (session_id,))
        return [dict(row) for row in cursor.fetchall()]

    # === META-COGNITION ===

    def _log_metacognition(self, monitoring_type: str, observation: str,
                          adjustment_made: str = None, improvement_noted: str = None,
                          awareness_level: int = 1, session_id: int = None):
        """Log meta-cognitive monitoring"""
        if session_id is None:
            session_id = self.current_reasoning_id

        if session_id is None:
            return  # Silent fail if no session

        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO metacognition_log
            (session_id, monitoring_type, observation, adjustment_made,
             improvement_noted, awareness_level)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (session_id, monitoring_type, observation, adjustment_made,
              improvement_noted, awareness_level))
        self.conn.commit()

    def monitor_reasoning_quality(self, session_id: int) -> Dict:
        """Assess quality of reasoning in session"""
        cursor = self.conn.cursor()

        # Get thought chain
        thoughts = self.get_thought_chain(session_id)

        # Calculate metrics
        avg_confidence = sum(t['confidence'] for t in thoughts) / len(thoughts) if thoughts else 0
        low_confidence_steps = sum(1 for t in thoughts if t['confidence'] < 0.3)
        has_alternatives = sum(1 for t in thoughts if t['alternatives'])

        # Get plans
        plans = self.get_plans(session_id)
        num_plans = len(plans)

        # Quality assessment
        quality_score = 0.0

        # Confidence factor (30%)
        quality_score += avg_confidence * 0.3

        # Alternative consideration factor (25%)
        if thoughts:
            alt_ratio = has_alternatives / len(thoughts)
            quality_score += alt_ratio * 0.25

        # Planning factor (25%)
        if num_plans > 1:
            quality_score += 0.25
        elif num_plans == 1:
            quality_score += 0.15

        # Evidence factor (20%)
        with_evidence = sum(1 for t in thoughts if t['evidence'])
        if thoughts:
            evidence_ratio = with_evidence / len(thoughts)
            quality_score += evidence_ratio * 0.2

        # Log meta-cognition
        self._log_metacognition(
            monitoring_type="quality_assessment",
            observation=f"Quality score: {quality_score:.2f}, Avg confidence: {avg_confidence:.0%}",
            awareness_level=MetaCognitionLevel.STRATEGIC.value,
            session_id=session_id
        )

        return {
            'quality_score': round(quality_score, 3),
            'avg_confidence': round(avg_confidence, 3),
            'low_confidence_steps': low_confidence_steps,
            'has_alternatives': has_alternatives,
            'total_thoughts': len(thoughts),
            'num_plans': num_plans,
            'evidence_ratio': round(with_evidence / len(thoughts), 3) if thoughts else 0
        }

    def adjust_reasoning_strategy(self, session_id: int):
        """Meta-cognitively adjust reasoning approach based on quality"""
        quality = self.monitor_reasoning_quality(session_id)

        adjustments = []

        if quality['avg_confidence'] < 0.5:
            adjustments.append("Gather more evidence before drawing conclusions")

        if quality['has_alternatives'] < quality['total_thoughts'] * 0.3:
            adjustments.append("Consider more alternative explanations")

        if quality['num_plans'] < 2:
            adjustments.append("Generate alternative plans")

        if quality['evidence_ratio'] < 0.5:
            adjustments.append("Support thoughts with more evidence")

        if adjustments:
            self._log_metacognition(
                monitoring_type="strategy_adjustment",
                observation=f"Quality issues detected: {quality}",
                adjustment_made="; ".join(adjustments),
                awareness_level=MetaCognitionLevel.METACOGNITIVE.value,
                session_id=session_id
            )

        return adjustments

    def get_metacognition_log(self, session_id: int) -> List[Dict]:
        """Get meta-cognition monitoring log"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM metacognition_log
            WHERE session_id = ?
            ORDER BY created_at ASC
        ''', (session_id,))
        return [dict(row) for row in cursor.fetchall()]

    # === ASSUMPTIONS ===

    def add_assumption(self, assumption: str, criticality: str = "medium",
                      validity_confidence: float = 0.5,
                      verification_status: str = "unverified",
                      impact_if_wrong: str = None, session_id: int = None):
        """Track an assumption made during reasoning"""
        if session_id is None:
            session_id = self.current_reasoning_id

        if session_id is None:
            raise ValueError("No active reasoning session.")

        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO reasoning_assumptions
            (session_id, assumption, criticality, validity_confidence,
             verification_status, impact_if_wrong)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (session_id, assumption, criticality, validity_confidence,
              verification_status, impact_if_wrong))
        self.conn.commit()

        # Meta-cognition for critical assumptions
        if criticality == "high" and validity_confidence < 0.7:
            self._log_metacognition(
                monitoring_type="risky_assumption",
                observation=f"High-criticality assumption with low confidence: {assumption}",
                adjustment_made="Flag for verification",
                awareness_level=MetaCognitionLevel.STRATEGIC.value,
                session_id=session_id
            )

    def get_assumptions(self, session_id: int) -> List[Dict]:
        """Get all assumptions for a session"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM reasoning_assumptions
            WHERE session_id = ?
            ORDER BY criticality DESC, validity_confidence ASC
        ''', (session_id,))
        return [dict(row) for row in cursor.fetchall()]

    # === REPORTING ===

    def generate_reasoning_report(self, session_id: int) -> str:
        """Generate comprehensive reasoning report"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM reasoning_sessions WHERE id = ?', (session_id,))
        session = dict(cursor.fetchone())

        thoughts = self.get_thought_chain(session_id)
        plans = self.get_plans(session_id)
        simulations = self.get_simulations(session_id)
        causal_links = self.get_causal_chain(session_id)
        counterfactuals = self.get_counterfactuals(session_id)
        assumptions = self.get_assumptions(session_id)
        metacog = self.get_metacognition_log(session_id)
        quality = self.monitor_reasoning_quality(session_id)

        report = []
        report.append("=" * 70)
        report.append(f"DEEP REASONING REPORT: {session['session_name']}")
        report.append("=" * 70)
        report.append(f"Goal: {session['goal']}")
        report.append(f"Type: {session['reasoning_type']}")
        report.append(f"Started: {session['started_at']}")
        report.append("")

        # Quality metrics
        report.append("QUALITY METRICS:")
        report.append(f"  Overall Score: {quality['quality_score']:.0%}")
        report.append(f"  Average Confidence: {quality['avg_confidence']:.0%}")
        report.append(f"  Total Thoughts: {quality['total_thoughts']}")
        report.append(f"  Plans Generated: {quality['num_plans']}")
        report.append(f"  Evidence Ratio: {quality['evidence_ratio']:.0%}")
        report.append("")

        # Assumptions
        if assumptions:
            report.append("ASSUMPTIONS:")
            for i, assumption in enumerate(assumptions, 1):
                report.append(f"  {i}. [{assumption['criticality'].upper()}] {assumption['assumption']}")
                report.append(f"     Confidence: {assumption['validity_confidence']:.0%}")
                report.append(f"     Status: {assumption['verification_status']}")
                if assumption['impact_if_wrong']:
                    report.append(f"     Impact if wrong: {assumption['impact_if_wrong']}")
            report.append("")

        # Chain of thought
        if thoughts:
            report.append("CHAIN OF THOUGHT:")
            for thought in thoughts:
                report.append(f"  Step {thought['step_number']}: {thought['thought']}")
                report.append(f"    Confidence: {thought['confidence']:.0%}")
                if thought['alternatives']:
                    alts = json.loads(thought['alternatives'])
                    report.append(f"    Alternatives considered: {', '.join(alts)}")
                if thought['chosen_path']:
                    report.append(f"    Chosen: {thought['chosen_path']}")
                    if thought['why_chosen']:
                        report.append(f"    Why: {thought['why_chosen']}")
                report.append("")

        # Plans
        if plans:
            report.append("PLANS GENERATED:")
            for plan in plans:
                marker = " [CHOSEN]" if plan['is_chosen'] else ""
                report.append(f"  {plan['plan_name']}{marker}")
                report.append(f"    {plan['description']}")
                report.append(f"    Success probability: {plan['probability_success']:.0%}")
                if plan['time_estimate_hours']:
                    report.append(f"    Time estimate: {plan['time_estimate_hours']} hours")
                if plan['cost_estimate']:
                    report.append(f"    Cost estimate: ${plan['cost_estimate']:,.2f}")
                steps = json.loads(plan['steps'])
                report.append(f"    Steps: {len(steps)}")
                for i, step in enumerate(steps, 1):
                    report.append(f"      {i}. {step}")
                if plan['risks']:
                    risks = json.loads(plan['risks'])
                    report.append(f"    Risks: {', '.join(risks)}")
                report.append("")

        # Outcome simulations
        if simulations:
            report.append("OUTCOME SIMULATIONS:")
            for sim in simulations:
                report.append(f"  {sim['scenario_name']}")
                report.append(f"    Probability: {sim['probability']:.0%}")
                report.append(f"    Impact: {sim['impact_score']:.1f}/10")
                report.append(f"    Outcome: {sim['predicted_outcome']}")
                report.append("")

        # Causal reasoning
        if causal_links:
            report.append("CAUSAL RELATIONSHIPS:")
            for link in causal_links:
                verified = " [VERIFIED]" if link['verified'] else ""
                report.append(f"  {link['cause']} → {link['effect']}{verified}")
                if link['mechanism']:
                    report.append(f"    Mechanism: {link['mechanism']}")
                report.append(f"    Confidence: {link['confidence']:.0%}")
                report.append("")

        # Counterfactuals
        if counterfactuals:
            report.append("COUNTERFACTUAL ANALYSIS:")
            for cf in counterfactuals:
                report.append(f"  What if: {cf['altered_condition']}")
                report.append(f"    (Instead of: {cf['original_condition']})")
                report.append(f"    Predicted: {cf['predicted_outcome']}")
                if cf['actual_outcome']:
                    report.append(f"    Actual: {cf['actual_outcome']}")
                if cf['insight']:
                    report.append(f"    Insight: {cf['insight']}")
                report.append("")

        # Meta-cognition
        if metacog:
            report.append("META-COGNITION LOG:")
            for entry in metacog:
                report.append(f"  [{entry['monitoring_type']}] {entry['observation']}")
                if entry['adjustment_made']:
                    report.append(f"    Adjustment: {entry['adjustment_made']}")
                if entry['improvement_noted']:
                    report.append(f"    Improvement: {entry['improvement_noted']}")
                report.append("")

        # Final conclusion
        if session['final_conclusion']:
            report.append("FINAL CONCLUSION:")
            report.append(f"  {session['final_conclusion']}")
            report.append(f"  Confidence: {session['confidence']:.0%}")
            if session['quality_score']:
                report.append(f"  Quality Score: {session['quality_score']:.0%}")

        report.append("=" * 70)
        return "\n".join(report)

    def close(self):
        """Close database connection"""
        self.conn.close()


# === TEST CODE ===

def main():
    """Test deep reasoning system"""
    print("Testing Deep Reasoning System")
    print("=" * 70)

    reasoner = DeepReasoning()

    try:
        # Start reasoning session
        print("\n1. Starting reasoning session...")
        session_id = reasoner.start_reasoning_session(
            session_name="Choose Database Technology",
            goal="Select the best database for a trading application",
            reasoning_type=ReasoningType.ABDUCTIVE,
            context={
                'requirements': ['high performance', 'reliability', 'easy scaling'],
                'constraints': ['budget', 'team expertise']
            }
        )
        print(f"   Session ID: {session_id}")

        # Add assumptions
        print("\n2. Adding assumptions...")
        reasoner.add_assumption(
            assumption="Trading data will exceed 10M records within 1 year",
            criticality="high",
            validity_confidence=0.8,
            verification_status="estimated",
            impact_if_wrong="May need to migrate database"
        )
        reasoner.add_assumption(
            assumption="Team has SQL experience but not NoSQL",
            criticality="medium",
            validity_confidence=0.9,
            verification_status="verified",
            impact_if_wrong="Longer learning curve"
        )
        print("   Added 2 assumptions")

        # Build chain of thought
        print("\n3. Building chain of thought...")
        reasoner.add_thought(
            thought="Need to analyze data access patterns",
            reasoning_type=ReasoningType.DEDUCTIVE,
            confidence=0.9,
            evidence=["Historical query logs", "Application requirements"]
        )

        reasoner.add_thought(
            thought="Data is primarily time-series with heavy writes",
            reasoning_type=ReasoningType.INDUCTIVE,
            confidence=0.85,
            evidence=["Trading data characteristics", "Write-heavy workload"]
        )

        reasoner.add_thought(
            thought="Consider PostgreSQL vs TimescaleDB vs MongoDB",
            reasoning_type=ReasoningType.ABDUCTIVE,
            confidence=0.7,
            alternatives=["PostgreSQL", "TimescaleDB", "MongoDB", "InfluxDB"],
            chosen_path="Compare top 3 options",
            why_chosen="These are most suitable for the use case"
        )
        print("   Added 3 thought steps")

        # Add causal reasoning
        print("\n4. Adding causal relationships...")
        reasoner.add_causal_link(
            cause="High write throughput requirement",
            effect="Need database optimized for writes",
            mechanism="Time-series data insertion rate",
            confidence=0.9,
            evidence=["Expected 1000 writes/sec", "Tick data ingestion"]
        )

        reasoner.add_causal_link(
            cause="Complex analytical queries needed",
            effect="Need SQL support",
            mechanism="Business intelligence and reporting",
            confidence=0.8,
            evidence=["Strategy backtesting queries", "Performance analysis"]
        )
        print("   Added 2 causal links")

        # Generate plans
        print("\n5. Generating alternative plans...")
        plan1_id = reasoner.generate_plan(
            plan_name="PostgreSQL with TimescaleDB Extension",
            description="Use PostgreSQL as base with TimescaleDB for time-series optimization",
            steps=[
                "Install PostgreSQL 15",
                "Add TimescaleDB extension",
                "Design hypertables for tick data",
                "Set up continuous aggregates",
                "Configure replication"
            ],
            expected_outcome="High-performance time-series database with SQL support",
            probability_success=0.85,
            cost_estimate=0,
            time_estimate_hours=16,
            risks=["Learning curve for TimescaleDB", "Migration complexity"]
        )

        plan2_id = reasoner.generate_plan(
            plan_name="MongoDB with Time-Series Collections",
            description="Use MongoDB's native time-series collection feature",
            steps=[
                "Install MongoDB 5.0+",
                "Create time-series collections",
                "Set up sharding",
                "Configure indexes",
                "Implement aggregation pipelines"
            ],
            expected_outcome="Flexible NoSQL solution with time-series support",
            probability_success=0.7,
            cost_estimate=0,
            time_estimate_hours=20,
            risks=["Team learning curve", "No SQL for complex queries", "Consistency concerns"]
        )

        print(f"   Generated 2 plans")

        # Simulate outcomes
        print("\n6. Simulating outcomes...")
        reasoner.simulate_outcome(
            scenario_name="PostgreSQL under peak load",
            conditions={'write_rate': '1500/sec', 'query_complexity': 'high'},
            predicted_outcome="Handles load well with proper indexing",
            probability=0.8,
            impact_score=9.0,
            timeline="Immediate",
            plan_id=plan1_id
        )

        reasoner.simulate_outcome(
            scenario_name="MongoDB scaling to 100M records",
            conditions={'data_size': '100M records', 'sharding': 'enabled'},
            predicted_outcome="Scales horizontally but complex queries slow",
            probability=0.75,
            impact_score=7.5,
            timeline="6 months",
            plan_id=plan2_id
        )
        print("   Simulated 2 outcomes")

        # Counterfactual analysis
        print("\n7. Counterfactual analysis...")
        reasoner.analyze_counterfactual(
            original_condition="Choose PostgreSQL",
            altered_condition="What if we chose MongoDB instead?",
            predicted_outcome="Would have faster initial development but struggle with complex analytics",
            insight="SQL is critical for our use case"
        )
        print("   Added 1 counterfactual")

        # Choose plan
        print("\n8. Choosing plan...")
        reasoner.choose_plan(
            plan_id=plan1_id,
            rationale="Best balance of performance, SQL support, and team expertise. TimescaleDB optimized for time-series data."
        )
        print("   Plan chosen")

        # Monitor quality and adjust
        print("\n9. Monitoring reasoning quality...")
        quality = reasoner.monitor_reasoning_quality(session_id)
        print(f"   Quality score: {quality['quality_score']:.0%}")

        adjustments = reasoner.adjust_reasoning_strategy(session_id)
        if adjustments:
            print(f"   Adjustments suggested: {len(adjustments)}")

        # Complete session
        print("\n10. Completing reasoning session...")
        reasoner.complete_reasoning_session(
            session_id=session_id,
            conclusion="PostgreSQL with TimescaleDB extension is the optimal choice for trading application database",
            confidence=0.85,
            quality_score=quality['quality_score']
        )
        print("   Session completed")

        # Generate report
        print("\n11. Generating reasoning report...")
        report = reasoner.generate_reasoning_report(session_id)
        print("\n" + report)

        print(f"\n✓ Deep Reasoning System working!")
        print(f"Database: {reasoner.db_path}")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        traceback.print_exc()
    finally:
        reasoner.close()


if __name__ == "__main__":
    main()
