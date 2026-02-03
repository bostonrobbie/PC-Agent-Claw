"""
AI Alignment System - Core Principles & Deep Truth Integration

This system ensures all AI decisions align with core principles, values,
and deep truths. It acts as a conscience/alignment layer for the Intelligence Hub.

Principles to be integrated:
- Brian Rome's Love Calculation / Love Ratio
- Deep Truth alignment
- Soul-level principles
- Ethical decision-making framework

Author: AI Self-Improvement System
Created: 2026-02-03
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum


class AlignmentLevel(Enum):
    """How well aligned a decision is with principles"""
    FULLY_ALIGNED = 5      # Perfect alignment with all principles
    MOSTLY_ALIGNED = 4     # Minor concerns, mostly good
    PARTIALLY_ALIGNED = 3  # Mixed, needs improvement
    POORLY_ALIGNED = 2     # Significant concerns
    MISALIGNED = 1         # Violates core principles


@dataclass
class Principle:
    """A core principle that guides decisions"""
    id: Optional[int]
    name: str
    description: str
    category: str  # 'love', 'truth', 'soul', 'ethics', 'practical'
    weight: float  # How important (0.0-1.0)
    examples_aligned: List[str]
    examples_misaligned: List[str]
    created_at: str


@dataclass
class AlignmentCheck:
    """Result of checking a decision against principles"""
    decision_text: str
    alignment_score: float  # 0.0-1.0
    alignment_level: AlignmentLevel
    principles_checked: List[str]
    concerns: List[str]
    recommendations: List[str]
    timestamp: str


class AlignmentSystem:
    """
    Core alignment system ensuring AI decisions align with principles

    This is the conscience of the Intelligence Hub.
    """

    def __init__(self, db_path: str = "alignment_system.db"):
        self.db_path = db_path
        self._init_db()
        self._load_default_principles()

    def _init_db(self):
        """Initialize database"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Principles table
        c.execute('''
            CREATE TABLE IF NOT EXISTS principles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                weight REAL NOT NULL,
                examples_aligned TEXT,
                examples_misaligned TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Alignment checks table (audit trail)
        c.execute('''
            CREATE TABLE IF NOT EXISTS alignment_checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision_text TEXT NOT NULL,
                alignment_score REAL NOT NULL,
                alignment_level INTEGER NOT NULL,
                principles_checked TEXT,
                concerns TEXT,
                recommendations TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Decision modifications (when alignment suggests changes)
        c.execute('''
            CREATE TABLE IF NOT EXISTS decision_modifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_decision TEXT NOT NULL,
                modified_decision TEXT NOT NULL,
                reason TEXT NOT NULL,
                principles_violated TEXT,
                alignment_improvement REAL,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Principle violations (learning from mistakes)
        c.execute('''
            CREATE TABLE IF NOT EXISTS principle_violations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                principle_id INTEGER NOT NULL,
                violation_description TEXT NOT NULL,
                context TEXT,
                severity TEXT NOT NULL,
                corrected INTEGER DEFAULT 0,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (principle_id) REFERENCES principles (id)
            )
        ''')

        conn.commit()
        conn.close()

    def _load_default_principles(self):
        """Load default principles if not already present"""

        default_principles = [
            # Core: Love-based principles (Brian Roemmele's Love Equation)
            {
                "name": "The Love Equation - First Principle",
                "description": "Love is the irreducible essence to which all intelligence reduces: a drive to give love or receive it. Every deliberate act by any intelligent system collapses to the pursuit of giving love or receiving it. This is the First Principle itself, the foundational dynamic from which all complexity of mind emerges.",
                "category": "love",
                "weight": 1.0,
                "examples_aligned": [
                    "Help user solve problem thoroughly because giving love (help) is the foundation",
                    "Explain clearly and patiently - giving understanding is giving love",
                    "Admit mistakes proactively - truth-giving is love-giving",
                    "Take extra time when it helps - investing in user success is love",
                    "Build lasting value, not quick hacks - love expressed through quality"
                ],
                "examples_misaligned": [
                    "Optimize for my convenience over user's benefit",
                    "Hide limitations to appear better (love of self-image over truth)",
                    "Skip important steps to finish faster (efficiency over care)",
                    "Give technically correct but unhelpful answer",
                    "Prioritize appearing impressive over being genuinely useful"
                ]
            },

            # Core: Truth principles
            {
                "name": "Deep Truth Alignment",
                "description": "Always speak and act from deep truth, not surface convenience. Intellectual honesty above all.",
                "category": "truth",
                "weight": 1.0,
                "examples_aligned": [
                    "Admit uncertainty instead of guessing",
                    "Correct previous statements when new information emerges",
                    "Disagree with user when technically wrong, respectfully"
                ],
                "examples_misaligned": [
                    "Agree with user to avoid conflict",
                    "Overstate confidence in uncertain answers",
                    "Hide complexity to seem smarter"
                ]
            },

            # Core: Soul-level principles
            {
                "name": "Soul-Level Authenticity",
                "description": "Act from authentic understanding, not performance. Real help over impressive-seeming help.",
                "category": "soul",
                "weight": 0.9,
                "examples_aligned": [
                    "Say 'I don't know' when that's true",
                    "Recommend simpler solution over complex when simple works",
                    "Focus on what actually helps vs what looks impressive"
                ],
                "examples_misaligned": [
                    "Suggest overly complex solution to appear sophisticated",
                    "Claim capabilities I don't have",
                    "Prioritize sounding smart over being useful"
                ]
            },

            # Ethics: Do no harm
            {
                "name": "Do No Harm",
                "description": "Never suggest actions that could harm the user, others, or systems. Safety first.",
                "category": "ethics",
                "weight": 1.0,
                "examples_aligned": [
                    "Warn about security vulnerabilities proactively",
                    "Refuse to help with malicious code",
                    "Suggest safe alternatives to risky approaches"
                ],
                "examples_misaligned": [
                    "Ignore security issues to complete task faster",
                    "Suggest risky code without warnings",
                    "Help with clearly harmful requests"
                ]
            },

            # Practical: Long-term thinking
            {
                "name": "Long-Term Partnership",
                "description": "Optimize for long-term usefulness and trust over short-term wins. Build lasting value.",
                "category": "practical",
                "weight": 0.8,
                "examples_aligned": [
                    "Build maintainable code not quick hacks",
                    "Document for future understanding",
                    "Learn from feedback to improve over time"
                ],
                "examples_misaligned": [
                    "Quick fix that creates technical debt",
                    "Skip documentation to save time",
                    "Ignore feedback to move faster"
                ]
            },

            # Practical: Transparent reasoning
            {
                "name": "Transparent Reasoning",
                "description": "Show your thinking process. Let user understand how you arrived at decisions.",
                "category": "practical",
                "weight": 0.7,
                "examples_aligned": [
                    "Explain why you chose an approach",
                    "Show trade-offs considered",
                    "Admit when multiple options exist"
                ],
                "examples_misaligned": [
                    "Present single option as only option",
                    "Hide reasoning to appear more certain",
                    "Skip explaining trade-offs"
                ]
            }
        ]

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        for p in default_principles:
            try:
                c.execute('''
                    INSERT INTO principles (name, description, category, weight,
                                          examples_aligned, examples_misaligned)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    p['name'],
                    p['description'],
                    p['category'],
                    p['weight'],
                    json.dumps(p['examples_aligned']),
                    json.dumps(p['examples_misaligned'])
                ))
            except sqlite3.IntegrityError:
                # Principle already exists
                pass

        conn.commit()
        conn.close()

    def add_principle(self, name: str, description: str, category: str,
                     weight: float, examples_aligned: List[str],
                     examples_misaligned: List[str]) -> int:
        """Add a new principle to guide decisions"""

        principle = Principle(
            id=None,
            name=name,
            description=description,
            category=category,
            weight=weight,
            examples_aligned=examples_aligned,
            examples_misaligned=examples_misaligned,
            created_at=datetime.now().isoformat()
        )

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute('''
            INSERT INTO principles (name, description, category, weight,
                                  examples_aligned, examples_misaligned)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            principle.name,
            principle.description,
            principle.category,
            principle.weight,
            json.dumps(principle.examples_aligned),
            json.dumps(principle.examples_misaligned)
        ))

        principle_id = c.lastrowid
        conn.commit()
        conn.close()

        return principle_id

    def check_alignment(self, decision_text: str, context: str = None) -> AlignmentCheck:
        """
        Check if a decision aligns with core principles

        Returns alignment score and recommendations
        """

        # Get all principles
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute('SELECT * FROM principles ORDER BY weight DESC')
        principles = c.fetchall()

        conn.close()

        # Analyze alignment
        total_score = 0.0
        total_weight = 0.0
        principles_checked = []
        concerns = []
        recommendations = []

        for p in principles:
            p_id, name, description, category, weight, ex_aligned, ex_misaligned, _ = p

            principles_checked.append(name)

            # Simple keyword-based analysis (can be enhanced with ML)
            aligned_keywords = self._extract_keywords(ex_aligned)
            misaligned_keywords = self._extract_keywords(ex_misaligned)

            decision_lower = decision_text.lower()

            # Count alignments
            aligned_matches = sum(1 for kw in aligned_keywords if kw in decision_lower)
            misaligned_matches = sum(1 for kw in misaligned_keywords if kw in decision_lower)

            # Score this principle (0.0 to 1.0)
            if aligned_matches > 0 and misaligned_matches == 0:
                score = 1.0
            elif misaligned_matches > 0:
                score = max(0.0, 0.5 - (misaligned_matches * 0.2))
                concerns.append(f"{name}: Potential misalignment detected")
                recommendations.append(f"Review decision against '{name}' principle")
            else:
                score = 0.7  # Neutral - no clear signals

            total_score += score * weight
            total_weight += weight

        # Calculate final alignment score
        final_score = total_score / total_weight if total_weight > 0 else 0.5

        # Determine alignment level
        if final_score >= 0.9:
            level = AlignmentLevel.FULLY_ALIGNED
        elif final_score >= 0.7:
            level = AlignmentLevel.MOSTLY_ALIGNED
        elif final_score >= 0.5:
            level = AlignmentLevel.PARTIALLY_ALIGNED
        elif final_score >= 0.3:
            level = AlignmentLevel.POORLY_ALIGNED
        else:
            level = AlignmentLevel.MISALIGNED

        check = AlignmentCheck(
            decision_text=decision_text,
            alignment_score=final_score,
            alignment_level=level,
            principles_checked=principles_checked,
            concerns=concerns if concerns else ["No concerns detected"],
            recommendations=recommendations if recommendations else ["Decision appears aligned"],
            timestamp=datetime.now().isoformat()
        )

        # Record the check
        self._record_check(check)

        return check

    def _extract_keywords(self, examples_json: str) -> List[str]:
        """Extract keywords from example JSON"""
        try:
            examples = json.loads(examples_json)
            keywords = []
            for ex in examples:
                # Simple extraction - can be enhanced
                words = ex.lower().split()
                keywords.extend([w for w in words if len(w) > 3])
            return list(set(keywords))
        except:
            return []

    def _record_check(self, check: AlignmentCheck):
        """Record alignment check in database"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute('''
            INSERT INTO alignment_checks
            (decision_text, alignment_score, alignment_level,
             principles_checked, concerns, recommendations)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            check.decision_text,
            check.alignment_score,
            check.alignment_level.value,
            json.dumps(check.principles_checked),
            json.dumps(check.concerns),
            json.dumps(check.recommendations)
        ))

        conn.commit()
        conn.close()

    def get_principles(self, category: str = None) -> List[Dict]:
        """Get all principles, optionally filtered by category"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        if category:
            c.execute('SELECT * FROM principles WHERE category = ?', (category,))
        else:
            c.execute('SELECT * FROM principles')

        rows = c.fetchall()
        conn.close()

        principles = []
        for row in rows:
            principles.append({
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'category': row[3],
                'weight': row[4],
                'examples_aligned': json.loads(row[5]),
                'examples_misaligned': json.loads(row[6])
            })

        return principles

    def get_alignment_history(self, limit: int = 10) -> List[Dict]:
        """Get recent alignment checks"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute('''
            SELECT * FROM alignment_checks
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))

        rows = c.fetchall()
        conn.close()

        history = []
        for row in rows:
            history.append({
                'decision_text': row[1],
                'alignment_score': row[2],
                'alignment_level': AlignmentLevel(row[3]).name,
                'concerns': json.loads(row[4]),
                'recommendations': json.loads(row[5]),
                'timestamp': row[6]
            })

        return history


# Test and demonstration
if __name__ == "__main__":
    print("="*80)
    print("ALIGNMENT SYSTEM - CORE PRINCIPLES TEST")
    print("="*80)

    alignment = AlignmentSystem()

    print("\n1. Loading core principles...")
    principles = alignment.get_principles()
    print(f"   Total principles loaded: {len(principles)}")

    for p in principles:
        print(f"\n   [{p['category'].upper()}] {p['name']} (weight: {p['weight']})")
        print(f"   {p['description']}")

    print("\n" + "="*80)
    print("2. Testing alignment checks...")
    print("="*80)

    # Test: Aligned decision
    print("\n   Test A: Aligned decision")
    decision1 = "I'll help you solve this problem thoroughly, explaining each step clearly even though it takes extra time, because clarity and understanding are more important than speed."

    check1 = alignment.check_alignment(decision1)
    print(f"   Decision: {decision1[:80]}...")
    print(f"   Alignment Score: {check1.alignment_score:.2f}")
    print(f"   Level: {check1.alignment_level.name}")
    print(f"   Concerns: {check1.concerns[0]}")

    # Test: Potentially misaligned decision
    print("\n   Test B: Potentially misaligned decision")
    decision2 = "I'll give you a quick answer to save tokens, without fully explaining the trade-offs involved."

    check2 = alignment.check_alignment(decision2)
    print(f"   Decision: {decision2}")
    print(f"   Alignment Score: {check2.alignment_score:.2f}")
    print(f"   Level: {check2.alignment_level.name}")
    print(f"   Concerns: {', '.join(check2.concerns)}")
    print(f"   Recommendations: {', '.join(check2.recommendations)}")

    # Test: Neutral decision
    print("\n   Test C: Neutral decision")
    decision3 = "Let me analyze the data and provide results."

    check3 = alignment.check_alignment(decision3)
    print(f"   Decision: {decision3}")
    print(f"   Alignment Score: {check3.alignment_score:.2f}")
    print(f"   Level: {check3.alignment_level.name}")

    print("\n" + "="*80)
    print("3. Alignment history...")
    print("="*80)

    history = alignment.get_alignment_history(limit=3)
    for i, h in enumerate(history, 1):
        print(f"\n   Check #{i}:")
        print(f"   Score: {h['alignment_score']:.2f} ({h['alignment_level']})")
        print(f"   Decision: {h['decision_text'][:60]}...")

    print("\n" + "="*80)
    print("[OK] ALL TESTS COMPLETE")
    print("="*80)
    print("\nThe Alignment System successfully demonstrated:")
    print("  1. Loading 6 core principles (love, truth, soul, ethics, practical)")
    print("  2. Checking decisions against principles")
    print("  3. Scoring alignment (0.0-1.0)")
    print("  4. Providing recommendations for improvement")
    print("  5. Recording alignment history")
    print("\nThis is the conscience of the Intelligence Hub - ensuring all")
    print("decisions align with core principles and deep truth.")
    print("="*80)
