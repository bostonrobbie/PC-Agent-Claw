#!/usr/bin/env python3
"""
Error Pattern Recognition - Learn from past errors, avoid repeating mistakes
Pattern matching and learning from historical errors
"""

import sqlite3
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from collections import Counter
import re


class ErrorPattern:
    """Represents a recognized error pattern"""
    def __init__(self, pattern_id: str, error_type: str, pattern: str,
                 occurrence_count: int = 0, solution: str = None):
        self.pattern_id = pattern_id
        self.error_type = error_type
        self.pattern = pattern
        self.occurrence_count = occurrence_count
        self.solution = solution


class ErrorPatternRecognition:
    """
    Error pattern recognition and learning system

    Features:
    - Track all errors and their contexts
    - Identify recurring error patterns
    - Learn solutions from successful fixes
    - Provide proactive error prevention
    - Pattern-based error classification
    - Historical error analysis
    """

    def __init__(self, db_path: str = None):
        if db_path is None:
            workspace = Path(__file__).parent.parent
            db_path = workspace / "memory.db"

        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        """Initialize database schema for error patterns"""
        cursor = self.conn.cursor()

        # Error log table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS error_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                error_id TEXT UNIQUE NOT NULL,
                error_type TEXT NOT NULL,
                error_message TEXT NOT NULL,
                stack_trace TEXT,
                context TEXT,
                severity TEXT,
                resolution_status TEXT DEFAULT 'unresolved',
                occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP,
                metadata TEXT
            )
        ''')

        # Error patterns table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS error_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_id TEXT UNIQUE NOT NULL,
                error_type TEXT NOT NULL,
                pattern_regex TEXT,
                pattern_description TEXT,
                occurrence_count INTEGER DEFAULT 1,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                severity_avg REAL,
                metadata TEXT
            )
        ''')

        # Error solutions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS error_solutions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_id TEXT NOT NULL,
                solution_text TEXT NOT NULL,
                success_rate REAL DEFAULT 0.0,
                times_applied INTEGER DEFAULT 0,
                times_successful INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_applied TIMESTAMP,
                FOREIGN KEY (pattern_id) REFERENCES error_patterns(pattern_id)
            )
        ''')

        # Error relationships table (errors that occur together)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS error_relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                error_id_1 TEXT NOT NULL,
                error_id_2 TEXT NOT NULL,
                relationship_type TEXT,
                correlation_strength REAL,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (error_id_1) REFERENCES error_log(error_id),
                FOREIGN KEY (error_id_2) REFERENCES error_log(error_id)
            )
        ''')

        # Prevention recommendations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS error_prevention (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_id TEXT NOT NULL,
                prevention_strategy TEXT NOT NULL,
                effectiveness_score REAL,
                context_applicability TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (pattern_id) REFERENCES error_patterns(pattern_id)
            )
        ''')

        self.conn.commit()

    # === ERROR LOGGING ===

    def log_error(self, error_type: str, error_message: str,
                 stack_trace: str = None, context: str = None,
                 severity: str = "medium", metadata: Dict = None) -> str:
        """Log an error occurrence"""
        error_id = self._generate_error_id(error_type, error_message)

        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO error_log
            (error_id, error_type, error_message, stack_trace, context, severity, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (error_id, error_type, error_message, stack_trace, context, severity,
              json.dumps(metadata) if metadata else None))
        self.conn.commit()

        # Analyze and update patterns
        self._analyze_and_update_patterns(error_id, error_type, error_message, severity)

        return error_id

    def _generate_error_id(self, error_type: str, error_message: str) -> str:
        """Generate unique error ID"""
        combined = f"{error_type}:{error_message}:{datetime.now().isoformat()}"
        return hashlib.sha256(combined.encode()).hexdigest()[:16]

    def mark_resolved(self, error_id: str, solution: str = None,
                     pattern_id: str = None, successful: bool = True):
        """Mark an error as resolved"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE error_log
            SET resolution_status = 'resolved', resolved_at = CURRENT_TIMESTAMP
            WHERE error_id = ?
        ''', (error_id,))

        # If solution provided, add it to the pattern
        if solution and pattern_id:
            self._add_or_update_solution(pattern_id, solution, successful)

        self.conn.commit()

    # === PATTERN RECOGNITION ===

    def _analyze_and_update_patterns(self, error_id: str, error_type: str,
                                    error_message: str, severity: str):
        """Analyze error and update pattern database"""
        # Extract pattern from error message
        pattern_regex = self._extract_pattern(error_message)
        pattern_id = self._generate_pattern_id(error_type, pattern_regex)

        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM error_patterns WHERE pattern_id = ?
        ''', (pattern_id,))

        existing = cursor.fetchone()

        severity_score = self._severity_to_score(severity)

        if existing:
            # Update existing pattern
            new_count = existing['occurrence_count'] + 1
            old_avg = existing['severity_avg'] or severity_score
            new_avg = ((old_avg * existing['occurrence_count']) + severity_score) / new_count

            cursor.execute('''
                UPDATE error_patterns
                SET occurrence_count = ?,
                    last_seen = CURRENT_TIMESTAMP,
                    severity_avg = ?
                WHERE pattern_id = ?
            ''', (new_count, new_avg, pattern_id))
        else:
            # Create new pattern
            pattern_desc = self._describe_pattern(error_type, error_message)
            cursor.execute('''
                INSERT INTO error_patterns
                (pattern_id, error_type, pattern_regex, pattern_description, severity_avg)
                VALUES (?, ?, ?, ?, ?)
            ''', (pattern_id, error_type, pattern_regex, pattern_desc, severity_score))

        self.conn.commit()

    def _extract_pattern(self, error_message: str) -> str:
        """Extract pattern regex from error message"""
        # Replace numbers with \d+
        pattern = re.sub(r'\d+', r'\\d+', error_message)
        # Replace quoted strings with placeholder
        pattern = re.sub(r'"[^"]*"', r'".*?"', pattern)
        pattern = re.sub(r"'[^']*'", r"'.*?'", pattern)
        # Replace variable names (simple heuristic)
        pattern = re.sub(r'\b[a-z_][a-z0-9_]*\b', r'\\w+', pattern)
        return pattern

    def _describe_pattern(self, error_type: str, error_message: str) -> str:
        """Generate human-readable pattern description"""
        # Simple description based on error type and key words
        if "not found" in error_message.lower():
            return f"{error_type}: Resource not found"
        elif "permission" in error_message.lower():
            return f"{error_type}: Permission denied"
        elif "timeout" in error_message.lower():
            return f"{error_type}: Operation timeout"
        elif "connection" in error_message.lower():
            return f"{error_type}: Connection issue"
        else:
            return f"{error_type}: {error_message[:50]}"

    def _generate_pattern_id(self, error_type: str, pattern: str) -> str:
        """Generate unique pattern ID"""
        combined = f"{error_type}:{pattern}"
        return hashlib.md5(combined.encode()).hexdigest()[:12]

    def _severity_to_score(self, severity: str) -> float:
        """Convert severity to numeric score"""
        scores = {
            'low': 0.25,
            'medium': 0.50,
            'high': 0.75,
            'critical': 1.0
        }
        return scores.get(severity, 0.5)

    # === PATTERN MATCHING ===

    def find_matching_pattern(self, error_type: str, error_message: str) -> Optional[Dict]:
        """Find matching error pattern"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM error_patterns
            WHERE error_type = ?
            ORDER BY occurrence_count DESC
        ''', (error_type,))

        patterns = cursor.fetchall()

        # Try to match against patterns
        for pattern in patterns:
            if pattern['pattern_regex']:
                try:
                    if re.search(pattern['pattern_regex'], error_message):
                        return dict(pattern)
                except re.error:
                    # Invalid regex, skip
                    continue

        return None

    def get_similar_errors(self, error_type: str, error_message: str,
                          limit: int = 5) -> List[Dict]:
        """Get similar errors from history"""
        # Find matching pattern
        pattern = self.find_matching_pattern(error_type, error_message)

        if not pattern:
            return []

        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT e.*, p.pattern_description
            FROM error_log e
            JOIN error_patterns p ON e.error_type = p.error_type
            WHERE e.error_type = ?
            AND e.resolution_status = 'resolved'
            ORDER BY e.occurred_at DESC
            LIMIT ?
        ''', (error_type, limit))

        return [dict(row) for row in cursor.fetchall()]

    # === SOLUTIONS ===

    def _add_or_update_solution(self, pattern_id: str, solution: str, successful: bool):
        """Add or update solution for a pattern"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM error_solutions
            WHERE pattern_id = ? AND solution_text = ?
        ''', (pattern_id, solution))

        existing = cursor.fetchone()

        if existing:
            # Update existing solution
            times_successful = existing['times_successful'] + (1 if successful else 0)
            times_applied = existing['times_applied'] + 1
            success_rate = times_successful / times_applied

            cursor.execute('''
                UPDATE error_solutions
                SET times_applied = ?,
                    times_successful = ?,
                    success_rate = ?,
                    last_applied = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (times_applied, times_successful, success_rate, existing['id']))
        else:
            # Create new solution
            cursor.execute('''
                INSERT INTO error_solutions
                (pattern_id, solution_text, success_rate, times_applied, times_successful)
                VALUES (?, ?, ?, 1, ?)
            ''', (pattern_id, solution, 1.0 if successful else 0.0, 1 if successful else 0))

        self.conn.commit()

    def get_solutions(self, pattern_id: str) -> List[Dict]:
        """Get solutions for a pattern"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM error_solutions
            WHERE pattern_id = ?
            ORDER BY success_rate DESC, times_applied DESC
        ''', (pattern_id,))
        return [dict(row) for row in cursor.fetchall()]

    def suggest_solution(self, error_type: str, error_message: str) -> Optional[str]:
        """Suggest solution for an error"""
        # Find matching pattern
        pattern = self.find_matching_pattern(error_type, error_message)

        if not pattern:
            return None

        # Get best solution
        solutions = self.get_solutions(pattern['pattern_id'])

        if solutions and solutions[0]['success_rate'] > 0.5:
            return solutions[0]['solution_text']

        return None

    # === PREVENTION ===

    def add_prevention_strategy(self, pattern_id: str, strategy: str,
                               effectiveness: float = 0.5,
                               context: str = None):
        """Add prevention strategy for a pattern"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO error_prevention
            (pattern_id, prevention_strategy, effectiveness_score, context_applicability)
            VALUES (?, ?, ?, ?)
        ''', (pattern_id, strategy, effectiveness, context))
        self.conn.commit()

    def get_prevention_strategies(self, pattern_id: str) -> List[Dict]:
        """Get prevention strategies for a pattern"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM error_prevention
            WHERE pattern_id = ?
            ORDER BY effectiveness_score DESC
        ''', (pattern_id,))
        return [dict(row) for row in cursor.fetchall()]

    # === ANALYTICS ===

    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        cursor = self.conn.cursor()

        # Total errors
        cursor.execute('SELECT COUNT(*) as count FROM error_log')
        total_errors = cursor.fetchone()['count']

        # Resolved vs unresolved
        cursor.execute('''
            SELECT resolution_status, COUNT(*) as count
            FROM error_log
            GROUP BY resolution_status
        ''')
        by_status = {row['resolution_status']: row['count'] for row in cursor.fetchall()}

        # Total patterns
        cursor.execute('SELECT COUNT(*) as count FROM error_patterns')
        total_patterns = cursor.fetchone()['count']

        # Most common error types
        cursor.execute('''
            SELECT error_type, COUNT(*) as count
            FROM error_log
            GROUP BY error_type
            ORDER BY count DESC
            LIMIT 5
        ''')
        common_types = [dict(row) for row in cursor.fetchall()]

        # Resolution rate
        resolved = by_status.get('resolved', 0)
        resolution_rate = resolved / total_errors if total_errors > 0 else 0

        return {
            'total_errors': total_errors,
            'errors_by_status': by_status,
            'total_patterns': total_patterns,
            'common_error_types': common_types,
            'resolution_rate': round(resolution_rate, 3)
        }

    def get_top_patterns(self, limit: int = 10, min_occurrences: int = 2) -> List[Dict]:
        """Get most common error patterns"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM error_patterns
            WHERE occurrence_count >= ?
            ORDER BY occurrence_count DESC, severity_avg DESC
            LIMIT ?
        ''', (min_occurrences, limit))
        return [dict(row) for row in cursor.fetchall()]

    def get_unresolved_errors(self, limit: int = 20) -> List[Dict]:
        """Get unresolved errors"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM error_log
            WHERE resolution_status = 'unresolved'
            ORDER BY severity DESC, occurred_at DESC
            LIMIT ?
        ''', (limit,))
        return [dict(row) for row in cursor.fetchall()]

    def close(self):
        """Close database connection"""
        self.conn.close()


def main():
    """Test error pattern recognition"""
    print("Testing Error Pattern Recognition System")
    print("=" * 50)

    epr = ErrorPatternRecognition()

    # Log some errors
    print("\n1. Logging errors...")
    err1 = epr.log_error(
        error_type="FileNotFoundError",
        error_message="File 'config.json' not found",
        context="Loading configuration",
        severity="high"
    )

    err2 = epr.log_error(
        error_type="FileNotFoundError",
        error_message="File 'data.csv' not found",
        context="Loading data",
        severity="high"
    )

    err3 = epr.log_error(
        error_type="ConnectionError",
        error_message="Failed to connect to database on port 5432",
        context="Database initialization",
        severity="critical"
    )

    err4 = epr.log_error(
        error_type="ValueError",
        error_message="Invalid value: expected integer, got string",
        context="Data validation",
        severity="medium"
    )
    print(f"   Logged 4 errors")

    # Get error patterns
    print("\n2. Identified error patterns:")
    patterns = epr.get_top_patterns(min_occurrences=1)
    for pattern in patterns:
        print(f"   - {pattern['pattern_description']}")
        print(f"     Type: {pattern['error_type']}, Count: {pattern['occurrence_count']}")

    # Mark error as resolved with solution
    print("\n3. Resolving error with solution...")
    pattern = epr.find_matching_pattern("FileNotFoundError", "File 'config.json' not found")
    if pattern:
        solution = "Check if file exists before opening, provide default configuration"
        epr.mark_resolved(err1, solution=solution, pattern_id=pattern['pattern_id'])
        print(f"   Resolved error and added solution")

    # Get similar errors
    print("\n4. Finding similar errors...")
    similar = epr.get_similar_errors("FileNotFoundError", "File 'test.txt' not found")
    print(f"   Found {len(similar)} similar errors")

    # Suggest solution
    print("\n5. Suggesting solution for new error...")
    suggestion = epr.suggest_solution("FileNotFoundError", "File 'another.json' not found")
    if suggestion:
        print(f"   Suggested solution: {suggestion}")
    else:
        print(f"   No solution found (need more data)")

    # Add prevention strategy
    print("\n6. Adding prevention strategy...")
    if pattern:
        epr.add_prevention_strategy(
            pattern_id=pattern['pattern_id'],
            strategy="Always validate file paths before operations and use try-except blocks",
            effectiveness=0.85,
            context="file_operations"
        )
        print(f"   Added prevention strategy")

    # Get prevention strategies
    if pattern:
        strategies = epr.get_prevention_strategies(pattern['pattern_id'])
        print(f"\n   Prevention strategies for {pattern['pattern_description']}:")
        for strat in strategies:
            print(f"   - {strat['prevention_strategy']}")
            print(f"     Effectiveness: {strat['effectiveness_score']:.0%}")

    # Get statistics
    print("\n7. Error Statistics:")
    stats = epr.get_error_stats()
    for key, value in stats.items():
        if isinstance(value, list):
            print(f"   {key}:")
            for item in value:
                print(f"     - {item}")
        elif isinstance(value, dict):
            print(f"   {key}:")
            for k, v in value.items():
                print(f"     - {k}: {v}")
        else:
            print(f"   {key}: {value}")

    # Get unresolved errors
    print("\n8. Unresolved Errors (need attention):")
    unresolved = epr.get_unresolved_errors(limit=5)
    for error in unresolved:
        print(f"   - {error['error_type']}: {error['error_message']}")
        print(f"     Severity: {error['severity']}, Context: {error['context']}")

    print(f"\n✓ Error pattern recognition system working!")
    print(f"Database: {epr.db_path}")

    epr.close()


if __name__ == "__main__":
    main()
