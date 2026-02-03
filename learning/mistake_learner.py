#!/usr/bin/env python3
"""
Automatic Mistake Learning System
Learn from errors and never repeat them
"""
import sys
from pathlib import Path
import sqlite3
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Optional

sys.path.append(str(Path(__file__).parent.parent))


class MistakeLearner:
    """
    Automatic mistake learning and prevention

    Tracks:
    - Errors made and their corrections
    - Code that failed and why
    - Suggestions that were rejected
    - Patterns that led to failures
    - Successful corrections

    Prevents:
    - Repeating same mistakes
    - Suggesting known-bad approaches
    - Making similar errors
    """

    def __init__(self, db_path: str = None):
        workspace = Path(__file__).parent.parent
        if db_path is None:
            db_path = str(workspace / "mistake_learning.db")

        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        """Initialize mistake learning database"""
        cursor = self.conn.cursor()

        # Mistakes made
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mistakes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mistake_type TEXT NOT NULL,
                description TEXT NOT NULL,
                context TEXT,
                code_snippet TEXT,
                error_message TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                severity TEXT DEFAULT 'medium'
            )
        ''')

        # Corrections applied
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS corrections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mistake_id INTEGER NOT NULL,
                correction_description TEXT NOT NULL,
                corrected_code TEXT,
                success INTEGER DEFAULT 1,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (mistake_id) REFERENCES mistakes(id)
            )
        ''')

        # Rejected suggestions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rejections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                suggestion TEXT NOT NULL,
                context TEXT,
                reason TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Patterns that fail
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS failure_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_description TEXT NOT NULL,
                pattern_signature TEXT NOT NULL,
                failure_count INTEGER DEFAULT 1,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                examples TEXT,
                UNIQUE(pattern_signature)
            )
        ''')

        # Success patterns
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS success_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_description TEXT NOT NULL,
                pattern_code TEXT,
                success_count INTEGER DEFAULT 1,
                last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                context TEXT
            )
        ''')

        self.conn.commit()

    # === MISTAKE RECORDING ===

    def record_mistake(self, mistake_type: str, description: str,
                      context: str = None, code_snippet: str = None,
                      error_message: str = None, severity: str = 'medium') -> int:
        """
        Record a mistake made

        Args:
            mistake_type: Type of mistake (syntax, logic, approach, etc.)
            description: What went wrong
            context: Situation where it happened
            code_snippet: The bad code
            error_message: Error received
            severity: low/medium/high/critical

        Returns:
            Mistake ID
        """
        cursor = self.conn.cursor()

        cursor.execute('''
            INSERT INTO mistakes (mistake_type, description, context, code_snippet, error_message, severity)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (mistake_type, description, context, code_snippet, error_message, severity))

        self.conn.commit()
        mistake_id = cursor.lastrowid

        # Extract pattern
        if code_snippet:
            self._extract_failure_pattern(code_snippet, description)

        return mistake_id

    def record_correction(self, mistake_id: int, correction: str,
                         corrected_code: str = None, success: bool = True):
        """Record how mistake was corrected"""
        cursor = self.conn.cursor()

        cursor.execute('''
            INSERT INTO corrections (mistake_id, correction_description, corrected_code, success)
            VALUES (?, ?, ?, ?)
        ''', (mistake_id, correction, corrected_code, 1 if success else 0))

        self.conn.commit()

        # If successful correction, record success pattern
        if success and corrected_code:
            self._record_success_pattern(corrected_code, correction)

    def _extract_failure_pattern(self, code: str, description: str):
        """Extract and record failure pattern"""
        # Create signature (hash of pattern)
        # In production, use AST or semantic analysis
        pattern_sig = hashlib.md5(code.encode()).hexdigest()[:16]

        cursor = self.conn.cursor()

        cursor.execute('''
            INSERT INTO failure_patterns (pattern_description, pattern_signature, examples)
            VALUES (?, ?, ?)
            ON CONFLICT(pattern_signature) DO UPDATE SET
                failure_count = failure_count + 1,
                last_seen = CURRENT_TIMESTAMP
        ''', (description, pattern_sig, code))

        self.conn.commit()

    def _record_success_pattern(self, code: str, description: str):
        """Record successful pattern"""
        cursor = self.conn.cursor()

        cursor.execute('''
            INSERT INTO success_patterns (pattern_description, pattern_code)
            VALUES (?, ?)
        ''', (description, code))

        self.conn.commit()

    # === REJECTION TRACKING ===

    def record_rejection(self, suggestion: str, context: str = None, reason: str = None):
        """Record when user rejects a suggestion"""
        cursor = self.conn.cursor()

        cursor.execute('''
            INSERT INTO rejections (suggestion, context, reason)
            VALUES (?, ?, ?)
        ''', (suggestion, context, reason))

        self.conn.commit()

    def check_if_rejected_before(self, suggestion: str) -> bool:
        """Check if similar suggestion was rejected before"""
        cursor = self.conn.cursor()

        # Simple keyword matching
        keywords = suggestion.lower().split()[:5]

        for keyword in keywords:
            cursor.execute('''
                SELECT COUNT(*) as count FROM rejections
                WHERE suggestion LIKE ?
            ''', (f'%{keyword}%',))

            if cursor.fetchone()['count'] > 0:
                return True

        return False

    # === MISTAKE PREVENTION ===

    def check_code_before_suggesting(self, code: str) -> Dict:
        """
        Check if code similar to known mistakes

        Returns:
            {
                'is_safe': bool,
                'warnings': list of warnings,
                'similar_mistakes': list of similar past mistakes
            }
        """
        cursor = self.conn.cursor()

        result = {
            'is_safe': True,
            'warnings': [],
            'similar_mistakes': []
        }

        # Check against failure patterns
        code_sig = hashlib.md5(code.encode()).hexdigest()[:16]

        cursor.execute('''
            SELECT * FROM failure_patterns
            WHERE pattern_signature = ?
        ''', (code_sig,))

        pattern = cursor.fetchone()
        if pattern:
            result['is_safe'] = False
            result['warnings'].append(f"Similar pattern failed {pattern['failure_count']} times before")
            result['warnings'].append(f"Known issue: {pattern['pattern_description']}")

        # Check for similar code in mistakes
        cursor.execute('''
            SELECT * FROM mistakes
            WHERE code_snippet IS NOT NULL
            ORDER BY timestamp DESC
            LIMIT 100
        ''')

        for mistake in cursor.fetchall():
            if mistake['code_snippet'] and self._is_similar_code(code, mistake['code_snippet']):
                result['similar_mistakes'].append(dict(mistake))
                result['warnings'].append(f"Similar to mistake: {mistake['description']}")

        return result

    def _is_similar_code(self, code1: str, code2: str) -> bool:
        """Check if two code snippets are similar"""
        # Simple similarity check (can be enhanced with AST comparison)
        code1_clean = code1.lower().replace(' ', '').replace('\n', '')
        code2_clean = code2.lower().replace(' ', '').replace('\n', '')

        # Check if 80% similar
        if len(code1_clean) == 0 or len(code2_clean) == 0:
            return False

        matches = sum(c1 == c2 for c1, c2 in zip(code1_clean, code2_clean))
        similarity = matches / max(len(code1_clean), len(code2_clean))

        return similarity > 0.8

    def get_correction_suggestions(self, error_message: str) -> List[Dict]:
        """
        Get suggestions based on past corrections for similar errors

        Args:
            error_message: Error message received

        Returns:
            List of past successful corrections
        """
        cursor = self.conn.cursor()

        # Find mistakes with similar error messages
        keywords = error_message.lower().split()[:5]

        suggestions = []
        for keyword in keywords:
            cursor.execute('''
                SELECT m.*, c.correction_description, c.corrected_code
                FROM mistakes m
                JOIN corrections c ON m.id = c.mistake_id
                WHERE m.error_message LIKE ?
                AND c.success = 1
                ORDER BY c.timestamp DESC
                LIMIT 3
            ''', (f'%{keyword}%',))

            for row in cursor.fetchall():
                suggestions.append(dict(row))

        return suggestions

    # === LEARNING STATS ===

    def get_learning_stats(self) -> Dict:
        """Get statistics about learning"""
        cursor = self.conn.cursor()

        stats = {}

        # Total mistakes
        cursor.execute('SELECT COUNT(*) as count FROM mistakes')
        stats['total_mistakes'] = cursor.fetchone()['count']

        # Mistakes by type
        cursor.execute('''
            SELECT mistake_type, COUNT(*) as count
            FROM mistakes
            GROUP BY mistake_type
            ORDER BY count DESC
        ''')
        stats['mistakes_by_type'] = {row['mistake_type']: row['count']
                                    for row in cursor.fetchall()}

        # Correction success rate
        cursor.execute('''
            SELECT
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as success_rate
            FROM corrections
        ''')
        result = cursor.fetchone()
        stats['correction_success_rate'] = result['success_rate'] if result['success_rate'] else 0

        # Top failure patterns
        cursor.execute('''
            SELECT pattern_description, failure_count
            FROM failure_patterns
            ORDER BY failure_count DESC
            LIMIT 5
        ''')
        stats['top_failure_patterns'] = [
            {'description': row['pattern_description'], 'count': row['failure_count']}
            for row in cursor.fetchall()
        ]

        # Total rejections
        cursor.execute('SELECT COUNT(*) as count FROM rejections')
        stats['total_rejections'] = cursor.fetchone()['count']

        return stats

    def get_recent_mistakes(self, limit: int = 10) -> List[Dict]:
        """Get recent mistakes"""
        cursor = self.conn.cursor()

        cursor.execute('''
            SELECT * FROM mistakes
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))

        return [dict(row) for row in cursor.fetchall()]

    def close(self):
        """Close database connection"""
        self.conn.close()


# === TEST CODE ===

def main():
    """Test mistake learner"""
    print("=" * 70)
    print("Automatic Mistake Learning System")
    print("=" * 70)

    learner = MistakeLearner()

    try:
        print("\n1. Recording a mistake...")
        mistake_id = learner.record_mistake(
            mistake_type="syntax_error",
            description="Forgot to close bracket",
            context="Writing Python function",
            code_snippet="def test():\n    print('hello'",
            error_message="SyntaxError: unexpected EOF while parsing",
            severity="low"
        )
        print(f"   Mistake ID: {mistake_id}")

        print("\n2. Recording correction...")
        learner.record_correction(
            mistake_id,
            correction="Added closing parenthesis",
            corrected_code="def test():\n    print('hello')",
            success=True
        )
        print("   Correction recorded")

        print("\n3. Recording a rejection...")
        learner.record_rejection(
            "Use global variables",
            context="Managing state",
            reason="Bad practice"
        )
        print("   Rejection recorded")

        print("\n4. Checking code safety...")
        bad_code = "def test():\n    print('hello'"
        safety = learner.check_code_before_suggesting(bad_code)
        print(f"   Is safe: {safety['is_safe']}")
        print(f"   Warnings: {len(safety['warnings'])}")

        print("\n5. Getting learning stats...")
        stats = learner.get_learning_stats()
        print(f"   Total mistakes: {stats['total_mistakes']}")
        print(f"   Correction success rate: {stats['correction_success_rate']:.1f}%")
        print(f"   Total rejections: {stats['total_rejections']}")

        print("\n6. Testing error-based suggestions...")
        suggestions = learner.get_correction_suggestions("SyntaxError: unexpected EOF")
        print(f"   Found {len(suggestions)} similar past corrections")

        print(f"\n[OK] Mistake Learning System Working!")
        print(f"Database: {learner.db_path}")

    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        learner.close()


if __name__ == "__main__":
    main()
