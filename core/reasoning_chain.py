#!/usr/bin/env python3
"""
Reasoning Chain Explainer - Log decision trees, explain thought process, show confidence
Provides transparent reasoning and explainability for all decisions
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum


class ConfidenceLevel(Enum):
    """Confidence levels for reasoning steps"""
    VERY_LOW = 0.2
    LOW = 0.4
    MEDIUM = 0.6
    HIGH = 0.8
    VERY_HIGH = 0.95


class ReasoningChain:
    """
    Reasoning chain system that logs and explains decision-making process

    Features:
    - Logs complete decision trees
    - Tracks reasoning steps with confidence scores
    - Explains thought process for transparency
    - Links decisions to outcomes
    - Provides reasoning summaries
    """

    def __init__(self, db_path: str = None):
        if db_path is None:
            workspace = Path(__file__).parent.parent
            db_path = workspace / "memory.db"

        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self._init_db()
        self.current_chain_id = None

    def _init_db(self):
        """Initialize database schema for reasoning chains"""
        cursor = self.conn.cursor()

        # Reasoning chains table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reasoning_chains (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chain_name TEXT NOT NULL,
                goal TEXT NOT NULL,
                final_decision TEXT,
                overall_confidence REAL,
                outcome TEXT,
                success INTEGER,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                metadata TEXT
            )
        ''')

        # Reasoning steps table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reasoning_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chain_id INTEGER NOT NULL,
                step_number INTEGER NOT NULL,
                step_type TEXT NOT NULL,
                description TEXT NOT NULL,
                reasoning TEXT,
                confidence REAL DEFAULT 0.5,
                evidence TEXT,
                alternatives_considered TEXT,
                chosen_option TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chain_id) REFERENCES reasoning_chains(id)
            )
        ''')

        # Decision nodes table (tree structure)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS decision_nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chain_id INTEGER NOT NULL,
                parent_node_id INTEGER,
                node_type TEXT NOT NULL,
                question TEXT,
                answer TEXT,
                confidence REAL,
                depth INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chain_id) REFERENCES reasoning_chains(id),
                FOREIGN KEY (parent_node_id) REFERENCES decision_nodes(id)
            )
        ''')

        # Assumptions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reasoning_assumptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chain_id INTEGER NOT NULL,
                assumption TEXT NOT NULL,
                validity_confidence REAL,
                verification_status TEXT,
                impact_if_wrong TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chain_id) REFERENCES reasoning_chains(id)
            )
        ''')

        self.conn.commit()

    # === CHAIN MANAGEMENT ===

    def start_chain(self, chain_name: str, goal: str, metadata: Dict = None) -> int:
        """Start a new reasoning chain"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO reasoning_chains (chain_name, goal, metadata)
            VALUES (?, ?, ?)
        ''', (chain_name, goal, json.dumps(metadata) if metadata else None))
        self.conn.commit()
        self.current_chain_id = cursor.lastrowid
        return self.current_chain_id

    def complete_chain(self, chain_id: int, final_decision: str,
                      overall_confidence: float, outcome: str = None,
                      success: bool = None):
        """Complete a reasoning chain"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE reasoning_chains
            SET final_decision = ?, overall_confidence = ?, outcome = ?,
                success = ?, completed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (final_decision, overall_confidence, outcome,
              1 if success else 0 if success is not None else None, chain_id))
        self.conn.commit()

        if self.current_chain_id == chain_id:
            self.current_chain_id = None

    # === REASONING STEPS ===

    def add_step(self, step_type: str, description: str, reasoning: str,
                confidence: float = 0.5, evidence: List[str] = None,
                alternatives: List[str] = None, chosen_option: str = None,
                chain_id: int = None) -> int:
        """Add a reasoning step to the chain"""
        if chain_id is None:
            chain_id = self.current_chain_id

        if chain_id is None:
            raise ValueError("No active chain. Call start_chain() first.")

        cursor = self.conn.cursor()

        # Get current step count
        cursor.execute('''
            SELECT COUNT(*) as count FROM reasoning_steps WHERE chain_id = ?
        ''', (chain_id,))
        step_number = cursor.fetchone()['count'] + 1

        cursor.execute('''
            INSERT INTO reasoning_steps
            (chain_id, step_number, step_type, description, reasoning,
             confidence, evidence, alternatives_considered, chosen_option)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (chain_id, step_number, step_type, description, reasoning,
              confidence, json.dumps(evidence) if evidence else None,
              json.dumps(alternatives) if alternatives else None, chosen_option))
        self.conn.commit()
        return cursor.lastrowid

    # === DECISION TREE ===

    def add_decision_node(self, node_type: str, question: str, answer: str,
                         confidence: float, parent_node_id: int = None,
                         chain_id: int = None) -> int:
        """Add a node to the decision tree"""
        if chain_id is None:
            chain_id = self.current_chain_id

        if chain_id is None:
            raise ValueError("No active chain. Call start_chain() first.")

        cursor = self.conn.cursor()

        # Calculate depth
        depth = 0
        if parent_node_id:
            cursor.execute('SELECT depth FROM decision_nodes WHERE id = ?', (parent_node_id,))
            parent = cursor.fetchone()
            if parent:
                depth = parent['depth'] + 1

        cursor.execute('''
            INSERT INTO decision_nodes
            (chain_id, parent_node_id, node_type, question, answer, confidence, depth)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (chain_id, parent_node_id, node_type, question, answer, confidence, depth))
        self.conn.commit()
        return cursor.lastrowid

    def get_decision_tree(self, chain_id: int) -> List[Dict]:
        """Get the complete decision tree for a chain"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM decision_nodes
            WHERE chain_id = ?
            ORDER BY depth ASC, id ASC
        ''', (chain_id,))
        return [dict(row) for row in cursor.fetchall()]

    # === ASSUMPTIONS ===

    def add_assumption(self, assumption: str, validity_confidence: float,
                      verification_status: str = "unverified",
                      impact_if_wrong: str = None, chain_id: int = None):
        """Add an assumption made during reasoning"""
        if chain_id is None:
            chain_id = self.current_chain_id

        if chain_id is None:
            raise ValueError("No active chain. Call start_chain() first.")

        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO reasoning_assumptions
            (chain_id, assumption, validity_confidence, verification_status, impact_if_wrong)
            VALUES (?, ?, ?, ?, ?)
        ''', (chain_id, assumption, validity_confidence, verification_status, impact_if_wrong))
        self.conn.commit()

    # === RETRIEVAL ===

    def get_chain(self, chain_id: int) -> Optional[Dict]:
        """Get a complete reasoning chain"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM reasoning_chains WHERE id = ?', (chain_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_chain_steps(self, chain_id: int) -> List[Dict]:
        """Get all steps in a reasoning chain"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM reasoning_steps
            WHERE chain_id = ?
            ORDER BY step_number ASC
        ''', (chain_id,))
        return [dict(row) for row in cursor.fetchall()]

    def get_chain_assumptions(self, chain_id: int) -> List[Dict]:
        """Get all assumptions for a chain"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM reasoning_assumptions
            WHERE chain_id = ?
            ORDER BY created_at ASC
        ''', (chain_id,))
        return [dict(row) for row in cursor.fetchall()]

    # === EXPLANATION ===

    def explain_chain(self, chain_id: int) -> str:
        """Generate a human-readable explanation of the reasoning chain"""
        chain = self.get_chain(chain_id)
        if not chain:
            return "Chain not found"

        steps = self.get_chain_steps(chain_id)
        assumptions = self.get_chain_assumptions(chain_id)
        tree = self.get_decision_tree(chain_id)

        explanation = []
        explanation.append(f"REASONING CHAIN: {chain['chain_name']}")
        explanation.append(f"Goal: {chain['goal']}")
        explanation.append(f"Started: {chain['started_at']}")
        explanation.append("")

        if assumptions:
            explanation.append("ASSUMPTIONS:")
            for i, assumption in enumerate(assumptions, 1):
                explanation.append(f"  {i}. {assumption['assumption']}")
                explanation.append(f"     Confidence: {assumption['validity_confidence']:.0%}")
                if assumption['impact_if_wrong']:
                    explanation.append(f"     Impact if wrong: {assumption['impact_if_wrong']}")
            explanation.append("")

        if steps:
            explanation.append("REASONING STEPS:")
            for step in steps:
                explanation.append(f"  Step {step['step_number']}: {step['step_type']}")
                explanation.append(f"    {step['description']}")
                explanation.append(f"    Reasoning: {step['reasoning']}")
                explanation.append(f"    Confidence: {step['confidence']:.0%}")
                if step['alternatives_considered']:
                    alts = json.loads(step['alternatives_considered'])
                    explanation.append(f"    Alternatives: {', '.join(alts)}")
                if step['chosen_option']:
                    explanation.append(f"    Chosen: {step['chosen_option']}")
                explanation.append("")

        if chain['final_decision']:
            explanation.append(f"FINAL DECISION: {chain['final_decision']}")
            explanation.append(f"Overall Confidence: {chain['overall_confidence']:.0%}")

        if chain['outcome']:
            explanation.append(f"Outcome: {chain['outcome']}")
            explanation.append(f"Success: {'Yes' if chain['success'] else 'No'}")

        return "\n".join(explanation)

    def get_recent_chains(self, limit: int = 10) -> List[Dict]:
        """Get recent reasoning chains"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM reasoning_chains
            ORDER BY started_at DESC
            LIMIT ?
        ''', (limit,))
        return [dict(row) for row in cursor.fetchall()]

    def close(self):
        """Close database connection"""
        self.conn.close()


def main():
    """Test reasoning chain system"""
    print("Testing Reasoning Chain Explainer")
    print("=" * 50)

    reasoner = ReasoningChain()

    # Start a reasoning chain
    print("\n1. Starting reasoning chain...")
    chain_id = reasoner.start_chain(
        chain_name="Choose Python Web Framework",
        goal="Select the best web framework for building a REST API",
        metadata={"project": "api_server", "constraints": ["performance", "ease_of_use"]}
    )
    print(f"   Chain ID: {chain_id}")

    # Add assumptions
    print("\n2. Adding assumptions...")
    reasoner.add_assumption(
        assumption="Team has Python experience but not web framework experience",
        validity_confidence=0.9,
        verification_status="verified",
        impact_if_wrong="May need more training time"
    )
    reasoner.add_assumption(
        assumption="API will have moderate traffic (< 1000 req/sec)",
        validity_confidence=0.7,
        verification_status="estimated",
        impact_if_wrong="May need to optimize or rewrite"
    )
    print("   Added 2 assumptions")

    # Add reasoning steps
    print("\n3. Adding reasoning steps...")
    reasoner.add_step(
        step_type="analysis",
        description="Analyze requirements",
        reasoning="Need REST API with good documentation and async support",
        confidence=0.9,
        evidence=["Project spec requires REST", "Expected high I/O operations"]
    )

    reasoner.add_step(
        step_type="evaluation",
        description="Evaluate framework options",
        reasoning="FastAPI has async support, auto docs, and type hints",
        confidence=0.85,
        evidence=["FastAPI benchmarks", "Community feedback"],
        alternatives=["Django REST Framework", "Flask", "FastAPI"],
        chosen_option="FastAPI"
    )

    reasoner.add_step(
        step_type="validation",
        description="Validate choice against constraints",
        reasoning="FastAPI meets performance needs and has gentle learning curve",
        confidence=0.8,
        evidence=["Performance benchmarks", "Documentation quality"]
    )
    print("   Added 3 reasoning steps")

    # Build decision tree
    print("\n4. Building decision tree...")
    root = reasoner.add_decision_node(
        node_type="question",
        question="Need async support?",
        answer="Yes - high I/O operations expected",
        confidence=0.9
    )

    async_branch = reasoner.add_decision_node(
        node_type="question",
        question="Need automatic API documentation?",
        answer="Yes - for team collaboration",
        confidence=0.85,
        parent_node_id=root
    )

    reasoner.add_decision_node(
        node_type="conclusion",
        question="Best framework?",
        answer="FastAPI - has async + auto docs",
        confidence=0.88,
        parent_node_id=async_branch
    )
    print("   Built decision tree with 3 nodes")

    # Complete the chain
    print("\n5. Completing reasoning chain...")
    reasoner.complete_chain(
        chain_id=chain_id,
        final_decision="Use FastAPI for REST API development",
        overall_confidence=0.85,
        outcome="Successfully implemented API with FastAPI",
        success=True
    )
    print("   Chain completed")

    # Get explanation
    print("\n6. Generated Explanation:")
    print("-" * 50)
    explanation = reasoner.explain_chain(chain_id)
    print(explanation)
    print("-" * 50)

    # Get decision tree
    print("\n7. Decision Tree:")
    tree = reasoner.get_decision_tree(chain_id)
    for node in tree:
        indent = "  " * node['depth']
        print(f"{indent}- {node['question']}")
        print(f"{indent}  Answer: {node['answer']} (confidence: {node['confidence']:.0%})")

    print(f"\n✓ Reasoning chain system working!")
    print(f"Database: {reasoner.db_path}")

    reasoner.close()


if __name__ == "__main__":
    main()
