#!/usr/bin/env python3
"""
Automatic Mistake Detection and Learning System

Features:
- Automatic error monitoring without explicit calls
- Traceback parsing and exception analysis
- Pattern recognition for repeated errors
- Integration with error_recovery system
- Auto-recording of mistakes from logs

Author: AI Self-Improvement System
Created: 2026-02-03
"""

import sys
from pathlib import Path
import sqlite3
import json
import hashlib
import traceback
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import warnings

sys.path.append(str(Path(__file__).parent.parent))

# Import error recovery for integration
try:
    from monitoring.error_recovery import ErrorRecoverySystem as MonitoringErrorRecovery
    ERROR_RECOVERY_AVAILABLE = True
except ImportError:
    try:
        from core.error_recovery import ErrorRecoverySystem as CoreErrorRecovery
        ERROR_RECOVERY_AVAILABLE = True
    except ImportError:
        ERROR_RECOVERY_AVAILABLE = False
        warnings.warn("Error recovery system not available")


@dataclass
class ErrorPattern:
    """Represents an error pattern for detection"""
    pattern_id: Optional[int]
    error_type: str
    pattern_signature: str
    pattern_description: str
    occurrence_count: int
    last_seen: str
    examples: List[str]
    suggested_fix: Optional[str] = None


class AutomaticMistakeLearner:
    """
    Automatic mistake learning with error detection

    Features:
    - Monitor for errors automatically
    - Parse tracebacks and exceptions
    - Auto-record without explicit call
    - Pattern recognition for repeated errors
    - Integration with error_recovery
    """

    def __init__(self, db_path: str = None):
        workspace = Path(__file__).parent.parent
        if db_path is None:
            db_path = str(workspace / "mistake_learning.db")

        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

        # Error recovery integration
        self.error_recovery = None
        if ERROR_RECOVERY_AVAILABLE:
            try:
                self.error_recovery = MonitoringErrorRecovery()
            except:
                try:
                    self.error_recovery = CoreErrorRecovery()
                except:
                    pass

    def _init_db(self):
        """Initialize mistake learning database with enhanced schema"""
        cursor = self.conn.cursor()

        # Mistakes made (enhanced)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mistakes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mistake_type TEXT NOT NULL,
                description TEXT NOT NULL,
                context TEXT,
                code_snippet TEXT,
                error_message TEXT,
                traceback_text TEXT,
                file_path TEXT,
                line_number INTEGER,
                function_name TEXT,
                auto_detected INTEGER DEFAULT 0,
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

        # Failure patterns (enhanced)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS failure_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_description TEXT NOT NULL,
                pattern_signature TEXT NOT NULL,
                error_type TEXT,
                failure_count INTEGER DEFAULT 1,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                examples TEXT,
                suggested_fix TEXT,
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

        # Error monitoring log
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS error_monitoring_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                error_type TEXT NOT NULL,
                error_message TEXT NOT NULL,
                traceback TEXT,
                file_path TEXT,
                line_number INTEGER,
                function_name TEXT,
                auto_recorded INTEGER DEFAULT 1,
                linked_mistake_id INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (linked_mistake_id) REFERENCES mistakes(id)
            )
        ''')

        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_mistakes_type ON mistakes(mistake_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_patterns_sig ON failure_patterns(pattern_signature)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_errors_type ON error_monitoring_log(error_type)')

        self.conn.commit()

    # === AUTOMATIC ERROR DETECTION ===

    def monitor_exception(self, exc: Exception, context: Dict = None) -> int:
        """
        Automatically monitor and record an exception

        Args:
            exc: The exception to monitor
            context: Additional context information

        Returns:
            Mistake ID
        """
        # Parse exception
        error_info = self._parse_exception(exc)

        # Extract context from traceback
        if context is None:
            context = {}

        # Auto-record mistake
        mistake_id = self.auto_record_mistake(
            error_type=error_info['error_type'],
            error_message=error_info['error_message'],
            traceback_text=error_info['traceback'],
            file_path=error_info['file_path'],
            line_number=error_info['line_number'],
            function_name=error_info['function_name'],
            code_snippet=error_info['code_snippet'],
            context=json.dumps(context)
        )

        # Log to error monitoring
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO error_monitoring_log
            (error_type, error_message, traceback, file_path, line_number, function_name, linked_mistake_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            error_info['error_type'],
            error_info['error_message'],
            error_info['traceback'],
            error_info['file_path'],
            error_info['line_number'],
            error_info['function_name'],
            mistake_id
        ))
        self.conn.commit()

        # Check for pattern
        self._detect_error_pattern(error_info)

        # Integrate with error recovery if available
        if self.error_recovery:
            try:
                self.error_recovery.handle_error(exc, context)
            except:
                pass

        return mistake_id

    def _parse_exception(self, exc: Exception) -> Dict:
        """Parse exception into structured information"""
        error_type = type(exc).__name__
        error_message = str(exc)
        traceback_text = traceback.format_exc()

        # Parse traceback for file, line, function
        file_path = None
        line_number = None
        function_name = None
        code_snippet = None

        tb_lines = traceback_text.split('\n')
        for i, line in enumerate(tb_lines):
            # Look for file location
            match = re.search(r'File "([^"]+)", line (\d+), in (\w+)', line)
            if match:
                file_path = match.group(1)
                line_number = int(match.group(2))
                function_name = match.group(3)

                # Get code snippet from next line
                if i + 1 < len(tb_lines):
                    code_snippet = tb_lines[i + 1].strip()
                break

        return {
            'error_type': error_type,
            'error_message': error_message,
            'traceback': traceback_text,
            'file_path': file_path,
            'line_number': line_number,
            'function_name': function_name,
            'code_snippet': code_snippet
        }

    def auto_record_mistake(self, error_type: str, error_message: str,
                           traceback_text: str = None, file_path: str = None,
                           line_number: int = None, function_name: str = None,
                           code_snippet: str = None, context: str = None,
                           severity: str = 'medium') -> int:
        """
        Automatically record a mistake from error information

        Args:
            error_type: Type of error (e.g., ValueError, TypeError)
            error_message: Error message
            traceback_text: Full traceback
            file_path: File where error occurred
            line_number: Line number
            function_name: Function name
            code_snippet: Code that caused error
            context: Additional context
            severity: Error severity

        Returns:
            Mistake ID
        """
        cursor = self.conn.cursor()

        # Generate description
        description = f"{error_type}: {error_message}"
        if function_name:
            description += f" in {function_name}()"

        cursor.execute('''
            INSERT INTO mistakes
            (mistake_type, description, context, code_snippet, error_message,
             traceback_text, file_path, line_number, function_name, auto_detected, severity)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            error_type, description, context, code_snippet, error_message,
            traceback_text, file_path, line_number, function_name, 1, severity
        ))

        self.conn.commit()
        mistake_id = cursor.lastrowid

        # Extract pattern
        if code_snippet:
            self._extract_failure_pattern(code_snippet, description, error_type)

        return mistake_id

    def _detect_error_pattern(self, error_info: Dict):
        """Detect if this error matches a known pattern"""
        # Create pattern signature
        pattern_sig = self._create_pattern_signature(
            error_info['error_type'],
            error_info['error_message'],
            error_info['code_snippet']
        )

        cursor = self.conn.cursor()

        # Check if pattern exists
        cursor.execute('''
            SELECT * FROM failure_patterns
            WHERE pattern_signature = ?
        ''', (pattern_sig,))

        pattern = cursor.fetchone()

        if pattern:
            # Pattern exists - update count
            cursor.execute('''
                UPDATE failure_patterns
                SET failure_count = failure_count + 1,
                    last_seen = CURRENT_TIMESTAMP
                WHERE pattern_signature = ?
            ''', (pattern_sig,))
            self.conn.commit()

            print(f"[Auto-Learn] Repeated error pattern detected! Seen {pattern['failure_count']+1} times.")
            print(f"   Pattern: {pattern['pattern_description']}")

            if pattern['suggested_fix']:
                print(f"   Suggested fix: {pattern['suggested_fix']}")

    def _create_pattern_signature(self, error_type: str, error_message: str,
                                  code_snippet: str = None) -> str:
        """Create a unique signature for an error pattern"""
        # Normalize error message (remove dynamic parts like numbers, paths)
        normalized_msg = re.sub(r'\d+', 'N', error_message)
        normalized_msg = re.sub(r'["\']([^"\']+)["\']', '"X"', normalized_msg)

        # Create signature
        signature_str = f"{error_type}:{normalized_msg}"
        if code_snippet:
            # Add code pattern (simplified)
            code_pattern = re.sub(r'\s+', ' ', code_snippet)
            code_pattern = re.sub(r'["\']([^"\']+)["\']', '""', code_pattern)
            signature_str += f":{code_pattern}"

        return hashlib.md5(signature_str.encode()).hexdigest()[:16]

    def _extract_failure_pattern(self, code: str, description: str, error_type: str):
        """Extract and record failure pattern"""
        pattern_sig = self._create_pattern_signature(error_type, description, code)

        cursor = self.conn.cursor()

        cursor.execute('''
            INSERT INTO failure_patterns (pattern_description, pattern_signature, error_type, examples)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(pattern_signature) DO UPDATE SET
                failure_count = failure_count + 1,
                last_seen = CURRENT_TIMESTAMP
        ''', (description, pattern_sig, error_type, code))

        self.conn.commit()

    # === PATTERN RECOGNITION ===

    def detect_repeated_errors(self, threshold: int = 3) -> List[ErrorPattern]:
        """
        Detect error patterns that repeat frequently

        Args:
            threshold: Minimum occurrences to consider as pattern

        Returns:
            List of error patterns
        """
        cursor = self.conn.cursor()

        cursor.execute('''
            SELECT * FROM failure_patterns
            WHERE failure_count >= ?
            ORDER BY failure_count DESC
        ''', (threshold,))

        patterns = []
        for row in cursor.fetchall():
            patterns.append(ErrorPattern(
                pattern_id=row['id'],
                error_type=row['error_type'],
                pattern_signature=row['pattern_signature'],
                pattern_description=row['pattern_description'],
                occurrence_count=row['failure_count'],
                last_seen=row['last_seen'],
                examples=[row['examples']],
                suggested_fix=row['suggested_fix']
            ))

        return patterns

    def suggest_fix_for_pattern(self, pattern_id: int, suggested_fix: str):
        """Add a suggested fix for an error pattern"""
        cursor = self.conn.cursor()

        cursor.execute('''
            UPDATE failure_patterns
            SET suggested_fix = ?
            WHERE id = ?
        ''', (suggested_fix, pattern_id))

        self.conn.commit()

    # === INTEGRATION WITH ERROR RECOVERY ===

    def get_recovery_suggestions(self, error: Exception) -> List[Dict]:
        """
        Get recovery suggestions based on past corrections for similar errors

        Args:
            error: The exception

        Returns:
            List of past successful corrections
        """
        error_info = self._parse_exception(error)
        error_message = error_info['error_message']

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

    # === ORIGINAL METHODS (Enhanced) ===

    def record_mistake(self, mistake_type: str, description: str,
                      context: str = None, code_snippet: str = None,
                      error_message: str = None, severity: str = 'medium') -> int:
        """
        Manually record a mistake

        Args:
            mistake_type: Type of mistake
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
            INSERT INTO mistakes
            (mistake_type, description, context, code_snippet, error_message, severity, auto_detected)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (mistake_type, description, context, code_snippet, error_message, severity, 0))

        self.conn.commit()
        mistake_id = cursor.lastrowid

        # Extract pattern
        if code_snippet:
            self._extract_failure_pattern(code_snippet, description, mistake_type)

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

    def _record_success_pattern(self, code: str, description: str):
        """Record successful pattern"""
        cursor = self.conn.cursor()

        cursor.execute('''
            INSERT INTO success_patterns (pattern_description, pattern_code)
            VALUES (?, ?)
        ''', (description, code))

        self.conn.commit()

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

            if pattern['suggested_fix']:
                result['warnings'].append(f"Suggested fix: {pattern['suggested_fix']}")

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
        code1_clean = code1.lower().replace(' ', '').replace('\n', '')
        code2_clean = code2.lower().replace(' ', '').replace('\n', '')

        if len(code1_clean) == 0 or len(code2_clean) == 0:
            return False

        matches = sum(c1 == c2 for c1, c2 in zip(code1_clean, code2_clean))
        similarity = matches / max(len(code1_clean), len(code2_clean))

        return similarity > 0.8

    # === STATS AND REPORTING ===

    def get_learning_stats(self) -> Dict:
        """Get statistics about learning"""
        cursor = self.conn.cursor()

        stats = {}

        # Total mistakes
        cursor.execute('SELECT COUNT(*) as count FROM mistakes')
        stats['total_mistakes'] = cursor.fetchone()['count']

        # Auto-detected vs manual
        cursor.execute('SELECT COUNT(*) as count FROM mistakes WHERE auto_detected = 1')
        stats['auto_detected_mistakes'] = cursor.fetchone()['count']

        # Mistakes by type
        cursor.execute('''
            SELECT mistake_type, COUNT(*) as count
            FROM mistakes
            GROUP BY mistake_type
            ORDER BY count DESC
            LIMIT 10
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
            SELECT pattern_description, failure_count, error_type
            FROM failure_patterns
            ORDER BY failure_count DESC
            LIMIT 5
        ''')
        stats['top_failure_patterns'] = [
            {
                'description': row['pattern_description'],
                'count': row['failure_count'],
                'error_type': row['error_type']
            }
            for row in cursor.fetchall()
        ]

        # Error monitoring stats
        cursor.execute('SELECT COUNT(*) as count FROM error_monitoring_log')
        stats['total_monitored_errors'] = cursor.fetchone()['count']

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


# === CONTEXT MANAGER FOR AUTO-MONITORING ===

class ErrorMonitoringContext:
    """Context manager for automatic error monitoring"""

    def __init__(self, learner: AutomaticMistakeLearner, context: Dict = None):
        self.learner = learner
        self.context = context or {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val is not None:
            # Automatically record the exception
            self.learner.monitor_exception(exc_val, self.context)
        return False  # Don't suppress exception


# === TEST CODE ===

def main():
    """Test automatic mistake learner"""
    print("=" * 80)
    print("AUTOMATIC MISTAKE LEARNING SYSTEM")
    print("=" * 80)

    learner = AutomaticMistakeLearner()

    try:
        print("\n1. Testing automatic error detection...")

        # Test 1: Simulate a ValueError
        try:
            x = int("not a number")
        except Exception as e:
            mistake_id = learner.monitor_exception(e, {'operation': 'type_conversion'})
            print(f"   Auto-recorded mistake ID: {mistake_id}")

        # Test 2: Simulate a repeated error
        for i in range(3):
            try:
                result = 10 / 0
            except Exception as e:
                learner.monitor_exception(e, {'attempt': i+1})

        print("\n2. Detecting repeated error patterns...")
        patterns = learner.detect_repeated_errors(threshold=2)
        print(f"   Found {len(patterns)} repeated patterns")
        for pattern in patterns:
            print(f"   - {pattern.error_type}: {pattern.pattern_description}")
            print(f"     Occurred {pattern.occurrence_count} times")

        print("\n3. Testing error monitoring context...")
        with ErrorMonitoringContext(learner, {'feature': 'test_feature'}):
            # This error will be automatically recorded
            raise RuntimeError("Test error in monitored context")

    except RuntimeError:
        pass  # Expected

    try:
        print("\n4. Manual mistake recording...")
        mistake_id = learner.record_mistake(
            mistake_type="logic_error",
            description="Off-by-one error in loop",
            context="Array iteration",
            code_snippet="for i in range(len(arr)):\n    arr[i+1] = 0",
            error_message="IndexError: list index out of range",
            severity="medium"
        )
        print(f"   Mistake ID: {mistake_id}")

        print("\n5. Recording correction...")
        learner.record_correction(
            mistake_id,
            correction="Fixed loop range to avoid out of bounds",
            corrected_code="for i in range(len(arr)-1):\n    arr[i+1] = 0",
            success=True
        )
        print("   Correction recorded")

        print("\n6. Getting learning stats...")
        stats = learner.get_learning_stats()
        print(f"   Total mistakes: {stats['total_mistakes']}")
        print(f"   Auto-detected: {stats['auto_detected_mistakes']}")
        print(f"   Monitored errors: {stats['total_monitored_errors']}")
        print(f"   Correction success rate: {stats['correction_success_rate']:.1f}%")

        print(f"\n[OK] Automatic Mistake Learning System Working!")
        print(f"Database: {learner.db_path}")

    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        traceback.print_exc()
    finally:
        learner.close()


if __name__ == "__main__":
    main()
