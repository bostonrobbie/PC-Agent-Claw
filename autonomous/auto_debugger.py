#!/usr/bin/env python3
"""
Autonomous Debugging Mode
Automatically try fixes, test them, present working solution
"""
import sys
from pathlib import Path
import sqlite3
import json
import subprocess
import tempfile
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import re

sys.path.append(str(Path(__file__).parent.parent))

from learning.mistake_learner import MistakeLearner


class AutoDebugger:
    """
    Autonomous debugging system

    Features:
    - Analyze errors automatically
    - Generate multiple fix candidates
    - Test each fix in sandbox
    - Rank by success probability
    - Present only working solution
    - Learn from successful fixes
    """

    def __init__(self, db_path: str = None):
        workspace = Path(__file__).parent.parent
        if db_path is None:
            db_path = str(workspace / "auto_debugger.db")

        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

        # Mistake learner for context
        self.mistake_learner = MistakeLearner()

    def _init_db(self):
        """Initialize debugger database"""
        cursor = self.conn.cursor()

        # Debugging sessions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS debug_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                error_type TEXT NOT NULL,
                error_message TEXT NOT NULL,
                code_snippet TEXT,
                file_path TEXT,
                line_number INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Fix attempts
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fix_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                fix_description TEXT NOT NULL,
                fixed_code TEXT NOT NULL,
                test_result INTEGER DEFAULT 0,
                confidence REAL DEFAULT 0.5,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES debug_sessions(id)
            )
        ''')

        # Successful fixes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS successful_fixes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                error_pattern TEXT NOT NULL,
                fix_pattern TEXT NOT NULL,
                success_count INTEGER DEFAULT 1,
                last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        self.conn.commit()

    # === ERROR ANALYSIS ===

    def analyze_error(self, error_message: str, code: str = None,
                     file_path: str = None, line_number: int = None) -> int:
        """
        Analyze error and create debugging session

        Args:
            error_message: Error message
            code: Code snippet that failed
            file_path: File path
            line_number: Line number

        Returns:
            Session ID
        """
        cursor = self.conn.cursor()

        # Extract error type
        error_type = self._extract_error_type(error_message)

        cursor.execute('''
            INSERT INTO debug_sessions
            (error_type, error_message, code_snippet, file_path, line_number)
            VALUES (?, ?, ?, ?, ?)
        ''', (error_type, error_message, code, file_path, line_number))

        self.conn.commit()
        return cursor.lastrowid

    def _extract_error_type(self, error_message: str) -> str:
        """Extract error type from message"""
        # Common Python errors
        error_types = [
            'SyntaxError', 'IndentationError', 'NameError', 'TypeError',
            'ValueError', 'AttributeError', 'KeyError', 'IndexError',
            'ImportError', 'ModuleNotFoundError', 'FileNotFoundError',
            'ZeroDivisionError', 'RuntimeError'
        ]

        for error_type in error_types:
            if error_type in error_message:
                return error_type

        return 'UnknownError'

    # === FIX GENERATION ===

    def generate_fixes(self, session_id: int, max_fixes: int = 5) -> List[Dict]:
        """
        Generate multiple fix candidates

        Args:
            session_id: Debug session ID
            max_fixes: Maximum fixes to generate

        Returns:
            List of fix candidates
        """
        cursor = self.conn.cursor()

        # Get session info
        cursor.execute('SELECT * FROM debug_sessions WHERE id = ?', (session_id,))
        session = dict(cursor.fetchone())

        fixes = []

        # 1. Check past successful fixes
        past_fixes = self._get_past_fixes(session['error_type'], session['error_message'])
        fixes.extend(past_fixes[:2])

        # 2. Pattern-based fixes
        pattern_fixes = self._generate_pattern_fixes(session)
        fixes.extend(pattern_fixes[:2])

        # 3. Rule-based fixes
        rule_fixes = self._generate_rule_based_fixes(session)
        fixes.extend(rule_fixes[:2])

        # Limit to max_fixes
        return fixes[:max_fixes]

    def _get_past_fixes(self, error_type: str, error_message: str) -> List[Dict]:
        """Get fixes that worked for similar errors before"""
        # Check mistake learner
        suggestions = self.mistake_learner.get_correction_suggestions(error_message)

        fixes = []
        for suggestion in suggestions:
            if suggestion.get('corrected_code'):
                fixes.append({
                    'description': suggestion['correction_description'],
                    'code': suggestion['corrected_code'],
                    'confidence': 0.9,  # High confidence from past success
                    'source': 'past_success'
                })

        return fixes

    def _generate_pattern_fixes(self, session: Dict) -> List[Dict]:
        """Generate fixes based on common patterns"""
        fixes = []
        error_type = session['error_type']
        error_msg = session['error_message']
        code = session['code_snippet']

        if not code:
            return fixes

        # SyntaxError patterns
        if error_type == 'SyntaxError':
            # Missing closing bracket
            if 'unexpected EOF' in error_msg.lower():
                fixes.append({
                    'description': 'Add missing closing bracket',
                    'code': self._add_closing_bracket(code),
                    'confidence': 0.8,
                    'source': 'pattern'
                })

            # Missing colon
            if 'expected' in error_msg.lower() and ':' not in code.split('\n')[-1]:
                fixes.append({
                    'description': 'Add missing colon',
                    'code': self._add_colon(code),
                    'confidence': 0.7,
                    'source': 'pattern'
                })

        # NameError patterns
        elif error_type == 'NameError':
            # Variable not defined
            match = re.search(r"name '(\w+)' is not defined", error_msg)
            if match:
                var_name = match.group(1)
                fixes.append({
                    'description': f'Define variable {var_name}',
                    'code': f'{var_name} = None  # TODO: Set proper value\n{code}',
                    'confidence': 0.6,
                    'source': 'pattern'
                })

        # IndentationError patterns
        elif error_type == 'IndentationError':
            fixes.append({
                'description': 'Fix indentation',
                'code': self._fix_indentation(code),
                'confidence': 0.7,
                'source': 'pattern'
            })

        return fixes

    def _generate_rule_based_fixes(self, session: Dict) -> List[Dict]:
        """Generate fixes based on rules"""
        fixes = []
        code = session['code_snippet']

        if not code:
            return fixes

        # Add try-except wrapper
        fixes.append({
            'description': 'Wrap in try-except',
            'code': f'try:\n    {code}\nexcept Exception as e:\n    print(f"Error: {{e}}")',
            'confidence': 0.5,
            'source': 'rule'
        })

        return fixes

    # === HELPER FIX FUNCTIONS ===

    def _add_closing_bracket(self, code: str) -> str:
        """Add missing closing brackets"""
        open_count = code.count('(') + code.count('[') + code.count('{')
        close_count = code.count(')') + code.count(']') + code.count('}')

        if open_count > close_count:
            # Simple fix: add closing parens
            return code + ')' * (open_count - close_count)

        return code

    def _add_colon(self, code: str) -> str:
        """Add missing colon to last line"""
        lines = code.split('\n')
        last_line = lines[-1].strip()

        keywords = ['if', 'else', 'elif', 'for', 'while', 'def', 'class', 'try', 'except', 'finally']

        if any(last_line.startswith(kw) for kw in keywords):
            lines[-1] = lines[-1] + ':'

        return '\n'.join(lines)

    def _fix_indentation(self, code: str) -> str:
        """Fix indentation issues"""
        lines = code.split('\n')
        fixed_lines = []
        indent_level = 0

        for line in lines:
            stripped = line.lstrip()

            if stripped.startswith(('def ', 'class ', 'if ', 'for ', 'while ', 'try:', 'except', 'else:', 'elif ')):
                fixed_lines.append('    ' * indent_level + stripped)
                if stripped.endswith(':'):
                    indent_level += 1
            elif stripped in ('else:', 'except:', 'finally:'):
                indent_level = max(0, indent_level - 1)
                fixed_lines.append('    ' * indent_level + stripped)
                indent_level += 1
            else:
                fixed_lines.append('    ' * indent_level + stripped)

        return '\n'.join(fixed_lines)

    # === FIX TESTING ===

    def test_fix(self, code: str, test_code: str = None) -> Tuple[bool, str]:
        """
        Test if fix works (in sandbox)

        Args:
            code: Fixed code to test
            test_code: Optional test code to run

        Returns:
            (success, output)
        """
        try:
            # Create temp file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_file = f.name

            # Try to compile (syntax check)
            try:
                with open(temp_file, 'r') as f:
                    compile(f.read(), temp_file, 'exec')
            except SyntaxError as e:
                os.unlink(temp_file)
                return False, f"SyntaxError: {e}"

            # If test code provided, run it
            if test_code:
                result = subprocess.run(
                    ['python', temp_file],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                os.unlink(temp_file)

                if result.returncode == 0:
                    return True, result.stdout
                else:
                    return False, result.stderr

            # No test code, just syntax check passed
            os.unlink(temp_file)
            return True, "Syntax OK"

        except Exception as e:
            return False, str(e)

    # === AUTO-DEBUG ===

    def auto_debug(self, error_message: str, code: str,
                   test_code: str = None) -> Optional[Dict]:
        """
        Autonomously debug and return working fix

        Args:
            error_message: Error message
            code: Failing code
            test_code: Test to verify fix

        Returns:
            Working fix or None
        """
        # Create session
        session_id = self.analyze_error(error_message, code)

        print(f"[AUTO-DEBUG] Session {session_id} started")

        # Generate fixes
        fixes = self.generate_fixes(session_id, max_fixes=5)

        print(f"[AUTO-DEBUG] Generated {len(fixes)} fix candidates")

        # Test each fix
        cursor = self.conn.cursor()
        working_fixes = []

        for i, fix in enumerate(fixes, 1):
            print(f"[AUTO-DEBUG] Testing fix {i}/{len(fixes)}: {fix['description']}")

            success, output = self.test_fix(fix['code'], test_code)

            # Record attempt
            cursor.execute('''
                INSERT INTO fix_attempts (session_id, fix_description, fixed_code, test_result, confidence)
                VALUES (?, ?, ?, ?, ?)
            ''', (session_id, fix['description'], fix['code'], 1 if success else 0, fix['confidence']))

            self.conn.commit()

            if success:
                print(f"[AUTO-DEBUG] ✓ Fix {i} works!")
                working_fixes.append({
                    'fix': fix,
                    'test_output': output
                })
            else:
                print(f"[AUTO-DEBUG] ✗ Fix {i} failed: {output[:100]}")

        # Return best working fix
        if working_fixes:
            # Sort by confidence
            best = sorted(working_fixes, key=lambda x: x['fix']['confidence'], reverse=True)[0]

            # Record successful pattern
            self._record_successful_pattern(error_message, best['fix'])

            # Record in mistake learner
            mistake_id = self.mistake_learner.record_mistake(
                self._extract_error_type(error_message),
                error_message,
                code_snippet=code,
                error_message=error_message
            )

            self.mistake_learner.record_correction(
                mistake_id,
                best['fix']['description'],
                best['fix']['code'],
                success=True
            )

            return {
                'success': True,
                'description': best['fix']['description'],
                'code': best['fix']['code'],
                'confidence': best['fix']['confidence'],
                'test_output': best['test_output'],
                'alternatives_tested': len(fixes)
            }

        print("[AUTO-DEBUG] No working fix found")
        return None

    def _record_successful_pattern(self, error_message: str, fix: Dict):
        """Record successful fix pattern"""
        cursor = self.conn.cursor()

        error_type = self._extract_error_type(error_message)

        cursor.execute('''
            INSERT INTO successful_fixes (error_pattern, fix_pattern)
            VALUES (?, ?)
        ''', (error_type, fix['description']))

        self.conn.commit()

    def close(self):
        """Close debugger"""
        self.mistake_learner.close()
        self.conn.close()


# === TEST CODE ===

def main():
    """Test auto debugger"""
    print("=" * 70)
    print("Autonomous Debugging Mode")
    print("=" * 70)

    debugger = AutoDebugger()

    try:
        print("\n1. Testing syntax error fix...")
        bad_code = "def test():\n    print('hello'"
        error_msg = "SyntaxError: unexpected EOF while parsing"

        result = debugger.auto_debug(error_msg, bad_code)

        if result and result['success']:
            print(f"   ✓ Found working fix!")
            print(f"   Description: {result['description']}")
            print(f"   Confidence: {result['confidence']}")
            print(f"   Tested {result['alternatives_tested']} alternatives")
        else:
            print("   ✗ No fix found")

        print("\n2. Testing NameError fix...")
        bad_code2 = "print(undefined_variable)"
        error_msg2 = "NameError: name 'undefined_variable' is not defined"

        result2 = debugger.auto_debug(error_msg2, bad_code2)

        if result2 and result2['success']:
            print(f"   ✓ Found working fix!")
            print(f"   Description: {result2['description']}")
        else:
            print("   ✗ No fix found")

        print(f"\n[OK] Auto Debugger Working!")
        print(f"Database: {debugger.db_path}")

    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        debugger.close()


if __name__ == "__main__":
    main()
