"""
Automated Code Review Learning

Learn from code reviews - track what gets approved/rejected/modified.
Build a personalized code quality model based on user's preferences.

Author: AI Self-Improvement System
Created: 2026-02-03
"""

import sqlite3
import json
import difflib
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict


@dataclass
class CodeReview:
    """A code review event"""
    id: Optional[int]
    original_code: str
    modified_code: Optional[str]
    review_type: str  # 'approved', 'rejected', 'modified'
    language: str
    context: str
    feedback: Optional[str]
    patterns_learned: List[str]
    timestamp: str


class CodeReviewLearner:
    """Learn from code reviews to match user's style"""

    def __init__(self, db_path: str = "code_review_learner.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Code reviews table
        c.execute('''
            CREATE TABLE IF NOT EXISTS code_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_code TEXT NOT NULL,
                modified_code TEXT,
                review_type TEXT NOT NULL,
                language TEXT NOT NULL,
                context TEXT,
                feedback TEXT,
                patterns_learned TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Style preferences (learned patterns)
        c.execute('''
            CREATE TABLE IF NOT EXISTS style_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_name TEXT UNIQUE NOT NULL,
                pattern_type TEXT NOT NULL,
                preferred_style TEXT NOT NULL,
                avoided_style TEXT NOT NULL,
                confidence REAL DEFAULT 0.5,
                occurrences INTEGER DEFAULT 1,
                language TEXT,
                description TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Quality metrics (what makes "good code" for this user)
        c.execute('''
            CREATE TABLE IF NOT EXISTS quality_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                language TEXT,
                context TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Architectural preferences
        c.execute('''
            CREATE TABLE IF NOT EXISTS architecture_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                preference_type TEXT NOT NULL,
                description TEXT NOT NULL,
                examples TEXT,
                confidence REAL DEFAULT 0.5,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()

    def record_review(self, original_code: str, modified_code: Optional[str],
                     review_type: str, language: str, context: str = None,
                     feedback: str = None) -> int:
        """
        Record a code review event.

        Args:
            original_code: The code I wrote
            modified_code: The code after user's modifications (if any)
            review_type: 'approved', 'rejected', 'modified'
            language: Programming language
            context: What the code does
            feedback: User's feedback or comments
        """
        # Analyze patterns if code was modified
        patterns = []
        if review_type == 'modified' and modified_code:
            patterns = self._analyze_modifications(original_code, modified_code, language)

        review = CodeReview(
            id=None,
            original_code=original_code,
            modified_code=modified_code,
            review_type=review_type,
            language=language,
            context=context,
            feedback=feedback,
            patterns_learned=patterns,
            timestamp=datetime.now().isoformat()
        )

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute('''
            INSERT INTO code_reviews
            (original_code, modified_code, review_type, language, context, feedback, patterns_learned)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            review.original_code, review.modified_code, review.review_type,
            review.language, review.context, review.feedback,
            json.dumps(review.patterns_learned)
        ))

        review_id = c.lastrowid

        # Learn from patterns
        for pattern in patterns:
            self._update_style_preference(conn, pattern, language)

        conn.commit()
        conn.close()

        return review_id

    def _analyze_modifications(self, original: str, modified: str, language: str) -> List[str]:
        """
        Analyze what changed and extract patterns.

        Returns list of pattern names that were learned.
        """
        patterns = []

        # Get diff
        diff = list(difflib.unified_diff(
            original.splitlines(),
            modified.splitlines(),
            lineterm=''
        ))

        # Analyze naming conventions
        patterns.extend(self._analyze_naming_changes(original, modified))

        # Analyze formatting changes
        patterns.extend(self._analyze_formatting_changes(original, modified))

        # Analyze structural changes
        patterns.extend(self._analyze_structural_changes(original, modified, language))

        # Analyze comment/doc changes
        patterns.extend(self._analyze_comment_changes(original, modified))

        return patterns

    def _analyze_naming_changes(self, original: str, modified: str) -> List[str]:
        """Analyze variable/function naming changes"""
        patterns = []

        # Extract identifiers
        orig_names = set(re.findall(r'\b[a-z_][a-z0-9_]*\b', original))
        mod_names = set(re.findall(r'\b[a-z_][a-z0-9_]*\b', modified))

        # Check for snake_case vs camelCase
        orig_snake = any('_' in name for name in orig_names)
        mod_snake = any('_' in name for name in mod_names)
        orig_camel = any(re.match(r'[a-z]+[A-Z]', name) for name in orig_names)
        mod_camel = any(re.match(r'[a-z]+[A-Z]', name) for name in mod_names)

        if orig_snake and not mod_snake and mod_camel:
            patterns.append('naming_camelCase_preferred')
        elif orig_camel and not mod_camel and mod_snake:
            patterns.append('naming_snake_case_preferred')

        # Check for verbosity
        avg_orig_len = sum(len(n) for n in orig_names) / len(orig_names) if orig_names else 0
        avg_mod_len = sum(len(n) for n in mod_names) / len(mod_names) if mod_names else 0

        if avg_mod_len > avg_orig_len * 1.3:
            patterns.append('naming_verbose_preferred')
        elif avg_mod_len < avg_orig_len * 0.7:
            patterns.append('naming_concise_preferred')

        return patterns

    def _analyze_formatting_changes(self, original: str, modified: str) -> List[str]:
        """Analyze formatting/style changes"""
        patterns = []

        # Indentation
        orig_spaces = len(re.findall(r'^\s+', original, re.MULTILINE))
        mod_spaces = len(re.findall(r'^\s+', modified, re.MULTILINE))

        if '\t' in original and '\t' not in modified:
            patterns.append('formatting_spaces_over_tabs')
        elif '\t' not in original and '\t' in modified:
            patterns.append('formatting_tabs_over_spaces')

        # Line length
        orig_long_lines = sum(1 for line in original.split('\n') if len(line) > 80)
        mod_long_lines = sum(1 for line in modified.split('\n') if len(line) > 80)

        if orig_long_lines > mod_long_lines:
            patterns.append('formatting_line_length_80')

        # Blank lines
        orig_blanks = original.count('\n\n')
        mod_blanks = modified.count('\n\n')

        if mod_blanks > orig_blanks * 1.5:
            patterns.append('formatting_more_blank_lines')

        # String quotes
        orig_single = original.count("'")
        orig_double = original.count('"')
        mod_single = modified.count("'")
        mod_double = modified.count('"')

        if orig_single > orig_double and mod_double > mod_single:
            patterns.append('formatting_double_quotes_preferred')
        elif orig_double > orig_single and mod_single > mod_double:
            patterns.append('formatting_single_quotes_preferred')

        return patterns

    def _analyze_structural_changes(self, original: str, modified: str, language: str) -> List[str]:
        """Analyze structural changes"""
        patterns = []

        if language == 'python':
            # List comprehensions vs loops
            if 'for ' in original and '[' in modified and 'for ' in modified:
                patterns.append('structure_list_comprehension_preferred')

            # Type hints
            orig_hints = len(re.findall(r':\s*\w+\s*[=)]', original))
            mod_hints = len(re.findall(r':\s*\w+\s*[=)]', modified))
            if mod_hints > orig_hints:
                patterns.append('structure_type_hints_preferred')

            # f-strings vs format
            if '.format(' in original and 'f"' in modified:
                patterns.append('structure_f_strings_preferred')

        # Error handling
        orig_try = original.count('try:')
        mod_try = modified.count('try:')
        if mod_try > orig_try:
            patterns.append('structure_explicit_error_handling')

        # Early returns
        orig_early = len(re.findall(r'^\s+return\b', original, re.MULTILINE))
        mod_early = len(re.findall(r'^\s+return\b', modified, re.MULTILINE))
        if mod_early > orig_early * 1.5:
            patterns.append('structure_early_returns_preferred')

        return patterns

    def _analyze_comment_changes(self, original: str, modified: str) -> List[str]:
        """Analyze comment/documentation changes"""
        patterns = []

        orig_comments = len(re.findall(r'#.*$', original, re.MULTILINE))
        mod_comments = len(re.findall(r'#.*$', modified, re.MULTILINE))

        orig_docstrings = len(re.findall(r'"""[\s\S]*?"""', original))
        mod_docstrings = len(re.findall(r'"""[\s\S]*?"""', modified))

        if mod_comments > orig_comments * 1.5:
            patterns.append('comments_more_inline_comments')

        if mod_docstrings > orig_docstrings:
            patterns.append('comments_docstrings_required')

        return patterns

    def _update_style_preference(self, conn: sqlite3.Connection, pattern: str, language: str):
        """Update or create a style preference"""
        c = conn.cursor()

        # Parse pattern name
        parts = pattern.split('_', 1)
        pattern_type = parts[0] if len(parts) > 0 else 'unknown'
        description = pattern.replace('_', ' ').title()

        # Determine preferred vs avoided style
        preferred = pattern
        avoided = self._get_opposite_pattern(pattern)

        c.execute('''
            INSERT INTO style_preferences
            (pattern_name, pattern_type, preferred_style, avoided_style, language, description, occurrences)
            VALUES (?, ?, ?, ?, ?, ?, 1)
            ON CONFLICT(pattern_name) DO UPDATE SET
                confidence = MIN(1.0, confidence + 0.1),
                occurrences = occurrences + 1,
                updated_at = CURRENT_TIMESTAMP
        ''', (pattern, pattern_type, preferred, avoided, language, description))

        conn.commit()

    def _get_opposite_pattern(self, pattern: str) -> str:
        """Get the opposite/avoided pattern"""
        opposites = {
            'camelCase': 'snake_case',
            'snake_case': 'camelCase',
            'verbose': 'concise',
            'concise': 'verbose',
            'spaces': 'tabs',
            'tabs': 'spaces',
            'double_quotes': 'single_quotes',
            'single_quotes': 'double_quotes',
        }

        for key, value in opposites.items():
            if key in pattern:
                return pattern.replace(key, value)

        return pattern

    def get_style_guide(self, language: Optional[str] = None) -> Dict:
        """
        Get personalized style guide based on learned preferences.

        Returns dictionary of preferences with confidence scores.
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        if language:
            c.execute('''
                SELECT pattern_type, preferred_style, confidence, occurrences, description
                FROM style_preferences
                WHERE language = ? OR language IS NULL
                ORDER BY confidence DESC, occurrences DESC
            ''', (language,))
        else:
            c.execute('''
                SELECT pattern_type, preferred_style, confidence, occurrences, description
                FROM style_preferences
                ORDER BY confidence DESC, occurrences DESC
            ''')

        rows = c.fetchall()
        conn.close()

        # Group by pattern type
        guide = defaultdict(list)
        for pattern_type, preferred, confidence, occurrences, description in rows:
            guide[pattern_type].append({
                'preference': preferred,
                'confidence': confidence,
                'occurrences': occurrences,
                'description': description
            })

        return dict(guide)

    def check_code_against_preferences(self, code: str, language: str) -> Dict:
        """
        Check code against learned preferences.

        Returns suggestions for improvement.
        """
        suggestions = []
        score = 100.0

        preferences = self.get_style_guide(language)

        # Check naming
        if 'naming' in preferences:
            for pref in preferences['naming']:
                if 'snake_case' in pref['preference']:
                    camel_count = len(re.findall(r'\b[a-z]+[A-Z][a-z]*\b', code))
                    if camel_count > 0:
                        suggestions.append({
                            'type': 'naming',
                            'message': 'Consider using snake_case instead of camelCase',
                            'confidence': pref['confidence'],
                            'impact': -5 * camel_count
                        })
                        score -= 5 * camel_count

        # Check formatting
        if 'formatting' in preferences:
            for pref in preferences['formatting']:
                if 'spaces_over_tabs' in pref['preference'] and '\t' in code:
                    suggestions.append({
                        'type': 'formatting',
                        'message': 'Use spaces instead of tabs for indentation',
                        'confidence': pref['confidence'],
                        'impact': -10
                    })
                    score -= 10

                if 'line_length_80' in pref['preference']:
                    long_lines = [i for i, line in enumerate(code.split('\n'), 1) if len(line) > 80]
                    if long_lines:
                        suggestions.append({
                            'type': 'formatting',
                            'message': f'Lines {long_lines[:3]} exceed 80 characters',
                            'confidence': pref['confidence'],
                            'impact': -2 * len(long_lines)
                        })
                        score -= 2 * len(long_lines)

        # Check structure
        if 'structure' in preferences:
            for pref in preferences['structure']:
                if 'type_hints' in pref['preference'] and language == 'python':
                    func_matches = re.findall(r'def\s+\w+\([^)]*\)', code)
                    untyped = sum(1 for m in func_matches if ':' not in m)
                    if untyped > 0:
                        suggestions.append({
                            'type': 'structure',
                            'message': f'{untyped} functions missing type hints',
                            'confidence': pref['confidence'],
                            'impact': -3 * untyped
                        })
                        score -= 3 * untyped

        score = max(0, min(100, score))

        return {
            'score': score,
            'suggestions': sorted(suggestions, key=lambda x: -x['impact']),
            'total_issues': len(suggestions)
        }

    def get_review_stats(self) -> Dict:
        """Get statistics about code reviews"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute('SELECT review_type, COUNT(*) FROM code_reviews GROUP BY review_type')
        review_counts = dict(c.fetchall())

        c.execute('SELECT COUNT(*) FROM code_reviews')
        total_reviews = c.fetchone()[0]

        c.execute('SELECT COUNT(*) FROM style_preferences WHERE confidence > 0.7')
        high_confidence_prefs = c.fetchone()[0]

        c.execute('SELECT AVG(confidence) FROM style_preferences')
        avg_confidence = c.fetchone()[0] or 0.0

        conn.close()

        approval_rate = review_counts.get('approved', 0) / total_reviews * 100 if total_reviews > 0 else 0
        modification_rate = review_counts.get('modified', 0) / total_reviews * 100 if total_reviews > 0 else 0

        return {
            'total_reviews': total_reviews,
            'approved': review_counts.get('approved', 0),
            'modified': review_counts.get('modified', 0),
            'rejected': review_counts.get('rejected', 0),
            'approval_rate': approval_rate,
            'modification_rate': modification_rate,
            'high_confidence_preferences': high_confidence_prefs,
            'avg_confidence': avg_confidence
        }


# Example usage and testing
if __name__ == "__main__":
    print("Testing Code Review Learner...")

    learner = CodeReviewLearner()

    # Simulate code reviews
    print("\n1. Recording approved code...")
    original = '''
def getUserData(userId):
    data = db.query(userId)
    return data
'''
    learner.record_review(original, None, 'approved', 'python', 'Fetch user data')

    print("2. Recording modified code...")
    original = '''
def processData(data):
    result = []
    for item in data:
        if item.valid:
            result.append(item.value)
    return result
'''
    modified = '''
def process_data(data: list) -> list:
    """Process and filter valid data items."""
    return [item.value for item in data if item.valid]
'''
    learner.record_review(original, modified, 'modified', 'python',
                         'Process data items', 'Use list comprehension and add type hints')

    print("3. Recording another modification...")
    original2 = '''
def formatString(name, age):
    return "Name: {}, Age: {}".format(name, age)
'''
    modified2 = '''
def format_string(name: str, age: int) -> str:
    """Format name and age into a string."""
    return f"Name: {name}, Age: {age}"
'''
    learner.record_review(original2, modified2, 'modified', 'python', 'Format string')

    # Get learned style guide
    print("\n4. Learned style guide...")
    guide = learner.get_style_guide('python')
    for category, prefs in guide.items():
        print(f"\n   {category.upper()}:")
        for pref in prefs:
            print(f"   - {pref['description']} (confidence: {pref['confidence']:.2f})")

    # Check code against preferences
    print("\n5. Checking new code against preferences...")
    test_code = '''
def getUserInfo(userId):
    data = database.query(userId)
    return data
'''
    result = learner.check_code_against_preferences(test_code, 'python')
    print(f"   Code quality score: {result['score']:.1f}/100")
    print(f"   Issues found: {result['total_issues']}")
    for suggestion in result['suggestions']:
        print(f"   - {suggestion['message']} (confidence: {suggestion['confidence']:.2f})")

    # Get stats
    print("\n6. Review statistics...")
    stats = learner.get_review_stats()
    print(f"   Total reviews: {stats['total_reviews']}")
    print(f"   Approved: {stats['approved']}")
    print(f"   Modified: {stats['modified']}")
    print(f"   Approval rate: {stats['approval_rate']:.1f}%")
    print(f"   High confidence preferences: {stats['high_confidence_preferences']}")

    print("\n[SUCCESS] Code Review Learner testing complete!")
    print(f"   Database: {learner.db_path}")
