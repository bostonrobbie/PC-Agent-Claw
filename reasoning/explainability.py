#!/usr/bin/env python3
"""
Explainability & Transparency Engine
Explain all decisions and reasoning
"""
import sys
from pathlib import Path
import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Any

sys.path.append(str(Path(__file__).parent.parent))


class ExplainabilityEngine:
    """
    Explain decisions and reasoning

    Features:
    - Explain why decisions were made
    - Show factors that influenced decisions
    - List alternatives considered
    - Provide confidence breakdowns
    - Generate decision reports
    - Track decision history
    """

    def __init__(self, db_path: str = None):
        workspace = Path(__file__).parent.parent
        if db_path is None:
            db_path = str(workspace / "memory.db")

        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        """Initialize database schema"""
        cursor = self.conn.cursor()

        # Decisions made
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS explainable_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision_name TEXT NOT NULL,
                decision_made TEXT NOT NULL,
                confidence REAL,
                made_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                context TEXT
            )
        ''')

        # Decision factors
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS decision_factors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision_id INTEGER NOT NULL,
                factor_name TEXT NOT NULL,
                factor_value TEXT,
                weight REAL,
                influence_direction TEXT,
                FOREIGN KEY (decision_id) REFERENCES explainable_decisions(id)
            )
        ''')

        # Alternatives considered
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS decision_alternatives (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision_id INTEGER NOT NULL,
                alternative_name TEXT NOT NULL,
                score REAL,
                rejected_reason TEXT,
                FOREIGN KEY (decision_id) REFERENCES explainable_decisions(id)
            )
        ''')

        # Decision rules applied
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS decision_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision_id INTEGER NOT NULL,
                rule_description TEXT NOT NULL,
                rule_applied INTEGER DEFAULT 1,
                FOREIGN KEY (decision_id) REFERENCES explainable_decisions(id)
            )
        ''')

        self.conn.commit()

    # === RECORD DECISIONS ===

    def record_decision(self, decision_name: str, decision_made: str,
                       confidence: float, factors: List[Dict],
                       alternatives: List[Dict] = None,
                       context: Dict = None) -> int:
        """
        Record explainable decision

        Args:
            decision_name: Name of decision
            decision_made: What was decided
            confidence: Confidence level (0-1)
            factors: Factors that influenced decision
            alternatives: Alternatives considered
            context: Additional context

        Returns:
            Decision ID
        """
        cursor = self.conn.cursor()

        # Record decision
        cursor.execute('''
            INSERT INTO explainable_decisions
            (decision_name, decision_made, confidence, context)
            VALUES (?, ?, ?, ?)
        ''', (decision_name, decision_made, confidence,
              json.dumps(context) if context else None))

        decision_id = cursor.lastrowid

        # Record factors
        for factor in factors:
            cursor.execute('''
                INSERT INTO decision_factors
                (decision_id, factor_name, factor_value, weight, influence_direction)
                VALUES (?, ?, ?, ?, ?)
            ''', (decision_id,
                  factor['name'],
                  str(factor.get('value', '')),
                  factor.get('weight', 0.5),
                  factor.get('direction', 'positive')))

        # Record alternatives
        if alternatives:
            for alt in alternatives:
                cursor.execute('''
                    INSERT INTO decision_alternatives
                    (decision_id, alternative_name, score, rejected_reason)
                    VALUES (?, ?, ?, ?)
                ''', (decision_id, alt['name'], alt.get('score', 0), alt.get('reason', '')))

        self.conn.commit()
        return decision_id

    # === EXPLAIN DECISIONS ===

    def explain_decision(self, decision_id: int) -> str:
        """
        Generate natural language explanation of decision

        Args:
            decision_id: Decision to explain

        Returns:
            Natural language explanation
        """
        cursor = self.conn.cursor()

        # Get decision
        cursor.execute('SELECT * FROM explainable_decisions WHERE id = ?', (decision_id,))
        decision = cursor.fetchone()

        if not decision:
            return "Decision not found"

        # Get factors
        cursor.execute('''
            SELECT * FROM decision_factors
            WHERE decision_id = ?
            ORDER BY weight DESC
        ''', (decision_id,))
        factors = cursor.fetchall()

        # Get alternatives
        cursor.execute('''
            SELECT * FROM decision_alternatives
            WHERE decision_id = ?
            ORDER BY score DESC
        ''', (decision_id,))
        alternatives = cursor.fetchall()

        # Build explanation
        explanation = []
        explanation.append(f"Decision: {decision['decision_name']}")
        explanation.append(f"Chose: {decision['decision_made']}")
        explanation.append(f"Confidence: {decision['confidence']:.0%}")
        explanation.append("")

        # Explain factors
        if factors:
            explanation.append("Why this decision:")
            for i, factor in enumerate(factors[:5], 1):  # Top 5 factors
                direction = "✓" if factor['influence_direction'] == 'positive' else "✗"
                explanation.append(
                    f"  {i}. {direction} {factor['factor_name']}: {factor['factor_value']} "
                    f"(weight: {factor['weight']:.0%})"
                )
            explanation.append("")

        # Explain alternatives
        if alternatives:
            explanation.append("Alternatives considered:")
            for alt in alternatives:
                explanation.append(f"  - {alt['alternative_name']}: score {alt['score']:.2f}")
                if alt['rejected_reason']:
                    explanation.append(f"    Rejected because: {alt['rejected_reason']}")
            explanation.append("")

        # Context
        if decision['context']:
            context = json.loads(decision['context'])
            explanation.append(f"Context: {context}")

        return "\n".join(explanation)

    def explain_recent_decisions(self, count: int = 5) -> List[str]:
        """Explain recent decisions"""
        cursor = self.conn.cursor()

        cursor.execute('''
            SELECT id FROM explainable_decisions
            ORDER BY made_at DESC
            LIMIT ?
        ''', (count,))

        explanations = []
        for row in cursor.fetchall():
            explanations.append(self.explain_decision(row['id']))

        return explanations

    # === DECISION ANALYSIS ===

    def analyze_decision_quality(self, decision_id: int) -> Dict:
        """
        Analyze quality of decision

        Args:
            decision_id: Decision to analyze

        Returns:
            Quality metrics
        """
        cursor = self.conn.cursor()

        # Get decision
        cursor.execute('SELECT * FROM explainable_decisions WHERE id = ?', (decision_id,))
        decision = cursor.fetchone()

        if not decision:
            return {}

        # Get factors
        cursor.execute('''
            SELECT COUNT(*) as count, AVG(weight) as avg_weight
            FROM decision_factors
            WHERE decision_id = ?
        ''', (decision_id,))
        factors_stats = cursor.fetchone()

        # Get alternatives
        cursor.execute('''
            SELECT COUNT(*) as count FROM decision_alternatives WHERE decision_id = ?
        ''', (decision_id,))
        alternatives_count = cursor.fetchone()['count']

        # Calculate quality score
        quality_score = 0.0

        # Confidence contribution (30%)
        quality_score += decision['confidence'] * 0.3

        # Factors contribution (30%)
        if factors_stats['count'] > 0:
            # More factors with good weights = better
            factor_quality = min(factors_stats['count'] / 5, 1.0) * factors_stats['avg_weight']
            quality_score += factor_quality * 0.3

        # Alternatives contribution (20%)
        if alternatives_count > 0:
            # Considering alternatives = better
            alt_quality = min(alternatives_count / 3, 1.0)
            quality_score += alt_quality * 0.2

        # Context contribution (20%)
        if decision['context']:
            quality_score += 0.2

        return {
            'decision_id': decision_id,
            'quality_score': round(quality_score, 3),
            'confidence': decision['confidence'],
            'factors_count': factors_stats['count'],
            'alternatives_count': alternatives_count,
            'has_context': bool(decision['context']),
            'assessment': 'high' if quality_score > 0.7 else 'medium' if quality_score > 0.4 else 'low'
        }

    # === REPORTING ===

    def generate_decision_report(self, decision_id: int) -> str:
        """
        Generate comprehensive decision report

        Args:
            decision_id: Decision to report on

        Returns:
            Formatted report
        """
        cursor = self.conn.cursor()

        # Get decision
        cursor.execute('SELECT * FROM explainable_decisions WHERE id = ?', (decision_id,))
        decision = cursor.fetchone()

        if not decision:
            return "Decision not found"

        # Get all related data
        cursor.execute('''
            SELECT * FROM decision_factors WHERE decision_id = ? ORDER BY weight DESC
        ''', (decision_id,))
        factors = cursor.fetchall()

        cursor.execute('''
            SELECT * FROM decision_alternatives WHERE decision_id = ? ORDER BY score DESC
        ''', (decision_id,))
        alternatives = cursor.fetchall()

        quality = self.analyze_decision_quality(decision_id)

        # Build report
        report = []
        report.append("=" * 70)
        report.append(f"DECISION REPORT")
        report.append("=" * 70)
        report.append(f"Decision: {decision['decision_name']}")
        report.append(f"Made: {decision['made_at']}")
        report.append(f"Result: {decision['decision_made']}")
        report.append(f"Confidence: {decision['confidence']:.0%}")
        report.append(f"Quality Score: {quality['quality_score']:.0%} ({quality['assessment']})")
        report.append("")

        # Factors
        report.append("INFLUENCING FACTORS:")
        for factor in factors:
            direction_symbol = "+" if factor['influence_direction'] == 'positive' else "-"
            report.append(
                f"  {direction_symbol} {factor['factor_name']}: {factor['factor_value']} "
                f"(weight: {factor['weight']:.0%})"
            )
        report.append("")

        # Alternatives
        if alternatives:
            report.append("ALTERNATIVES CONSIDERED:")
            for alt in alternatives:
                report.append(f"  - {alt['alternative_name']} (score: {alt['score']:.2f})")
                if alt['rejected_reason']:
                    report.append(f"    Reason: {alt['rejected_reason']}")
            report.append("")

        # Context
        if decision['context']:
            report.append("CONTEXT:")
            context = json.loads(decision['context'])
            for key, value in context.items():
                report.append(f"  {key}: {value}")
            report.append("")

        report.append("=" * 70)

        return "\n".join(report)

    def get_decision_history(self, decision_name: str = None, limit: int = 10) -> List[Dict]:
        """Get decision history"""
        cursor = self.conn.cursor()

        if decision_name:
            cursor.execute('''
                SELECT * FROM explainable_decisions
                WHERE decision_name = ?
                ORDER BY made_at DESC
                LIMIT ?
            ''', (decision_name, limit))
        else:
            cursor.execute('''
                SELECT * FROM explainable_decisions
                ORDER BY made_at DESC
                LIMIT ?
            ''', (limit,))

        return [dict(row) for row in cursor.fetchall()]

    def close(self):
        """Close database connection"""
        self.conn.close()


# === TEST CODE ===

def main():
    """Test explainability engine"""
    print("Testing Explainability Engine")
    print("=" * 70)

    engine = ExplainabilityEngine()

    try:
        # Record decision
        print("\n1. Recording explainable decision...")
        decision_id = engine.record_decision(
            decision_name="Choose Trading Strategy",
            decision_made="Strategy B (Moderate Risk)",
            confidence=0.85,
            factors=[
                {'name': 'Historical Win Rate', 'value': '78%', 'weight': 0.9, 'direction': 'positive'},
                {'name': 'Volatility Tolerance', 'value': 'Medium', 'weight': 0.7, 'direction': 'positive'},
                {'name': 'Max Drawdown', 'value': '12%', 'weight': 0.8, 'direction': 'positive'},
                {'name': 'Execution Speed', 'value': 'Fast', 'weight': 0.6, 'direction': 'positive'}
            ],
            alternatives=[
                {'name': 'Strategy A (Conservative)', 'score': 0.65, 'reason': 'Lower returns'},
                {'name': 'Strategy C (Aggressive)', 'score': 0.72, 'reason': 'Too much risk'}
            ],
            context={'market_condition': 'volatile', 'account_size': 'medium'}
        )
        print(f"   Decision ID: {decision_id}")

        # Explain decision
        print("\n2. Explaining decision...")
        explanation = engine.explain_decision(decision_id)
        print(explanation)

        # Analyze quality
        print("\n3. Analyzing decision quality...")
        quality = engine.analyze_decision_quality(decision_id)
        print(f"   Quality Score: {quality['quality_score']:.0%}")
        print(f"   Assessment: {quality['assessment']}")
        print(f"   Factors: {quality['factors_count']}")
        print(f"   Alternatives: {quality['alternatives_count']}")

        # Generate report
        print("\n4. Generating decision report...")
        report = engine.generate_decision_report(decision_id)
        print("\n" + report)

        # Get history
        print("\n5. Getting decision history...")
        history = engine.get_decision_history(limit=5)
        print(f"   Total decisions: {len(history)}")

        print(f"\n[OK] Explainability Engine working!")
        print(f"Database: {engine.db_path}")

    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        engine.close()


if __name__ == "__main__":
    main()
