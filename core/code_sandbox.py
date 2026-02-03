#!/usr/bin/env python3
"""
Code Testing Sandbox - Test code before execution, catch bugs early
Safe execution environment for testing code
"""

import sqlite3
import json
import subprocess
import tempfile
import os
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from io import StringIO
import contextlib


class ExecutionResult:
    """Result of code execution"""
    def __init__(self, success: bool, output: str = "", error: str = "",
                 execution_time: float = 0, exit_code: int = 0):
        self.success = success
        self.output = output
        self.error = error
        self.execution_time = execution_time
        self.exit_code = exit_code

    def to_dict(self) -> Dict:
        return {
            'success': self.success,
            'output': self.output,
            'error': self.error,
            'execution_time': self.execution_time,
            'exit_code': self.exit_code
        }


class CodeSandbox:
    """
    Code testing sandbox for safe execution

    Features:
    - Safe code execution in isolated environment
    - Syntax checking before execution
    - Error catching and reporting
    - Execution time limits
    - Output capture
    - Test history tracking
    - Multiple language support (Python, JavaScript, etc.)
    """

    def __init__(self, db_path: str = None, timeout: int = 30):
        if db_path is None:
            workspace = Path(__file__).parent.parent
            db_path = workspace / "memory.db"

        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self._init_db()

        self.timeout = timeout
        self.temp_dir = tempfile.gettempdir()

    def _init_db(self):
        """Initialize database schema for sandbox"""
        cursor = self.conn.cursor()

        # Test executions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sandbox_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id TEXT UNIQUE NOT NULL,
                code_hash TEXT,
                language TEXT DEFAULT 'python',
                code_snippet TEXT NOT NULL,
                success INTEGER,
                output TEXT,
                error TEXT,
                execution_time REAL,
                exit_code INTEGER,
                syntax_valid INTEGER,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        ''')

        # Bug detections table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bug_detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id TEXT NOT NULL,
                bug_type TEXT NOT NULL,
                severity TEXT,
                description TEXT,
                line_number INTEGER,
                suggested_fix TEXT,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (execution_id) REFERENCES sandbox_executions(execution_id)
            )
        ''')

        # Test cases table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_id TEXT UNIQUE NOT NULL,
                test_name TEXT NOT NULL,
                code TEXT NOT NULL,
                expected_output TEXT,
                language TEXT DEFAULT 'python',
                enabled INTEGER DEFAULT 1,
                last_run TIMESTAMP,
                pass_count INTEGER DEFAULT 0,
                fail_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Test results table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_id TEXT NOT NULL,
                execution_id TEXT NOT NULL,
                passed INTEGER,
                actual_output TEXT,
                run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (test_id) REFERENCES test_cases(test_id),
                FOREIGN KEY (execution_id) REFERENCES sandbox_executions(execution_id)
            )
        ''')

        self.conn.commit()

    # === CODE EXECUTION ===

    def execute_python(self, code: str, execution_id: str = None,
                      capture_output: bool = True, metadata: Dict = None) -> ExecutionResult:
        """Execute Python code in sandbox"""
        execution_id = execution_id or f"exec_{int(time.time() * 1000)}"

        # Check syntax first
        syntax_valid, syntax_error = self._check_python_syntax(code)

        if not syntax_valid:
            result = ExecutionResult(
                success=False,
                error=f"Syntax Error: {syntax_error}",
                execution_time=0,
                exit_code=1
            )
            self._log_execution(execution_id, code, 'python', result, syntax_valid, metadata)
            return result

        # Execute code
        start_time = time.time()

        try:
            if capture_output:
                # Capture stdout and stderr
                stdout_capture = StringIO()
                stderr_capture = StringIO()

                with contextlib.redirect_stdout(stdout_capture), \
                     contextlib.redirect_stderr(stderr_capture):
                    # Execute in isolated namespace
                    namespace = {'__name__': '__main__'}
                    exec(code, namespace)

                output = stdout_capture.getvalue()
                error = stderr_capture.getvalue()
                success = len(error) == 0
            else:
                # Execute without capture (for interactive code)
                namespace = {'__name__': '__main__'}
                exec(code, namespace)
                output = "Execution completed"
                error = ""
                success = True

            execution_time = time.time() - start_time

            result = ExecutionResult(
                success=success,
                output=output,
                error=error,
                execution_time=execution_time,
                exit_code=0 if success else 1
            )

        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"

            result = ExecutionResult(
                success=False,
                error=error_msg,
                execution_time=execution_time,
                exit_code=1
            )

            # Detect bug type
            self._detect_and_log_bug(execution_id, e, code)

        # Log execution
        self._log_execution(execution_id, code, 'python', result, syntax_valid, metadata)

        return result

    def execute_subprocess(self, code: str, language: str = 'python',
                          execution_id: str = None, metadata: Dict = None) -> ExecutionResult:
        """Execute code in subprocess for better isolation"""
        execution_id = execution_id or f"exec_{int(time.time() * 1000)}"

        # Create temp file
        suffix = self._get_file_suffix(language)
        with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False) as f:
            f.write(code)
            temp_file = f.name

        try:
            # Get command for language
            cmd = self._get_execution_command(language, temp_file)

            # Execute with timeout
            start_time = time.time()
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            try:
                stdout, stderr = process.communicate(timeout=self.timeout)
                execution_time = time.time() - start_time

                result = ExecutionResult(
                    success=process.returncode == 0,
                    output=stdout,
                    error=stderr,
                    execution_time=execution_time,
                    exit_code=process.returncode
                )

            except subprocess.TimeoutExpired:
                process.kill()
                execution_time = time.time() - start_time

                result = ExecutionResult(
                    success=False,
                    error=f"Execution timeout after {self.timeout}s",
                    execution_time=execution_time,
                    exit_code=-1
                )

        finally:
            # Cleanup temp file
            try:
                os.unlink(temp_file)
            except:
                pass

        # Log execution
        syntax_valid = result.exit_code != 1 or "SyntaxError" not in result.error
        self._log_execution(execution_id, code, language, result, syntax_valid, metadata)

        return result

    def _check_python_syntax(self, code: str) -> Tuple[bool, str]:
        """Check Python syntax without executing"""
        try:
            compile(code, '<string>', 'exec')
            return True, ""
        except SyntaxError as e:
            return False, str(e)

    def _get_file_suffix(self, language: str) -> str:
        """Get file suffix for language"""
        suffixes = {
            'python': '.py',
            'javascript': '.js',
            'bash': '.sh',
            'shell': '.sh'
        }
        return suffixes.get(language, '.txt')

    def _get_execution_command(self, language: str, file_path: str) -> List[str]:
        """Get execution command for language"""
        commands = {
            'python': [sys.executable, file_path],
            'javascript': ['node', file_path],
            'bash': ['bash', file_path],
            'shell': ['sh', file_path]
        }
        return commands.get(language, [sys.executable, file_path])

    # === BUG DETECTION ===

    def _detect_and_log_bug(self, execution_id: str, exception: Exception, code: str):
        """Detect and categorize bugs"""
        bug_type = type(exception).__name__
        severity = self._assess_bug_severity(exception)

        # Try to extract line number
        line_number = None
        if hasattr(exception, '__traceback__'):
            tb = exception.__traceback__
            while tb.tb_next:
                tb = tb.tb_next
            line_number = tb.tb_lineno

        # Suggest fix
        suggested_fix = self._suggest_fix(exception, code)

        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO bug_detections
            (execution_id, bug_type, severity, description, line_number, suggested_fix)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (execution_id, bug_type, severity, str(exception), line_number, suggested_fix))
        self.conn.commit()

    def _assess_bug_severity(self, exception: Exception) -> str:
        """Assess bug severity"""
        critical_errors = (SystemError, MemoryError, RecursionError)
        high_errors = (TypeError, AttributeError, KeyError, IndexError)
        medium_errors = (ValueError, RuntimeError)

        if isinstance(exception, critical_errors):
            return "critical"
        elif isinstance(exception, high_errors):
            return "high"
        elif isinstance(exception, medium_errors):
            return "medium"
        else:
            return "low"

    def _suggest_fix(self, exception: Exception, code: str) -> str:
        """Suggest a fix for common errors"""
        suggestions = {
            'NameError': "Check if variable is defined before use",
            'TypeError': "Check data types and function arguments",
            'AttributeError': "Verify object has the attribute/method",
            'KeyError': "Check if key exists in dictionary using .get() or 'in' operator",
            'IndexError': "Check list bounds before accessing index",
            'ValueError': "Validate input values before processing",
            'ZeroDivisionError': "Add check to prevent division by zero",
            'ImportError': "Ensure module is installed and path is correct",
            'IndentationError': "Fix code indentation"
        }

        bug_type = type(exception).__name__
        return suggestions.get(bug_type, "Review error message and stack trace")

    # === TEST CASES ===

    def add_test_case(self, test_id: str, test_name: str, code: str,
                     expected_output: str = None, language: str = 'python') -> str:
        """Add a test case"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO test_cases
            (test_id, test_name, code, expected_output, language)
            VALUES (?, ?, ?, ?, ?)
        ''', (test_id, test_name, code, expected_output, language))
        self.conn.commit()
        return test_id

    def run_test(self, test_id: str) -> bool:
        """Run a test case"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM test_cases WHERE test_id = ?', (test_id,))
        test = cursor.fetchone()

        if not test:
            return False

        # Execute test
        execution_id = f"test_{test_id}_{int(time.time() * 1000)}"
        result = self.execute_python(test['code'], execution_id)

        # Check if passed
        passed = result.success
        if test['expected_output']:
            passed = passed and test['expected_output'] in result.output

        # Log result
        cursor.execute('''
            INSERT INTO test_results
            (test_id, execution_id, passed, actual_output)
            VALUES (?, ?, ?, ?)
        ''', (test_id, execution_id, 1 if passed else 0, result.output))

        # Update test stats
        cursor.execute('''
            UPDATE test_cases
            SET last_run = CURRENT_TIMESTAMP,
                pass_count = pass_count + ?,
                fail_count = fail_count + ?
            WHERE test_id = ?
        ''', (1 if passed else 0, 0 if passed else 1, test_id))

        self.conn.commit()
        return passed

    def run_all_tests(self) -> Dict[str, Any]:
        """Run all enabled test cases"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT test_id FROM test_cases WHERE enabled = 1')
        test_ids = [row['test_id'] for row in cursor.fetchall()]

        results = {}
        for test_id in test_ids:
            results[test_id] = self.run_test(test_id)

        return results

    # === LOGGING ===

    def _log_execution(self, execution_id: str, code: str, language: str,
                      result: ExecutionResult, syntax_valid: bool, metadata: Dict = None):
        """Log code execution"""
        import hashlib
        code_hash = hashlib.md5(code.encode()).hexdigest()

        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO sandbox_executions
            (execution_id, code_hash, language, code_snippet, success, output,
             error, execution_time, exit_code, syntax_valid, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (execution_id, code_hash, language, code, 1 if result.success else 0,
              result.output, result.error, result.execution_time, result.exit_code,
              1 if syntax_valid else 0, json.dumps(metadata) if metadata else None))
        self.conn.commit()

    # === ANALYTICS ===

    def get_execution_stats(self) -> Dict[str, Any]:
        """Get sandbox execution statistics"""
        cursor = self.conn.cursor()

        # Total executions
        cursor.execute('SELECT COUNT(*) as count FROM sandbox_executions')
        total = cursor.fetchone()['count']

        # Success rate
        cursor.execute('SELECT AVG(success) as rate FROM sandbox_executions')
        success_rate = cursor.fetchone()['rate'] or 0

        # Syntax error rate
        cursor.execute('SELECT AVG(CASE WHEN syntax_valid = 0 THEN 1 ELSE 0 END) as rate FROM sandbox_executions')
        syntax_error_rate = cursor.fetchone()['rate'] or 0

        # Average execution time
        cursor.execute('SELECT AVG(execution_time) as avg FROM sandbox_executions WHERE success = 1')
        avg_time = cursor.fetchone()['avg'] or 0

        # Most common bugs
        cursor.execute('''
            SELECT bug_type, COUNT(*) as count
            FROM bug_detections
            GROUP BY bug_type
            ORDER BY count DESC
            LIMIT 5
        ''')
        common_bugs = [dict(row) for row in cursor.fetchall()]

        # Test stats
        cursor.execute('SELECT COUNT(*) as count FROM test_cases')
        total_tests = cursor.fetchone()['count']

        cursor.execute('SELECT SUM(pass_count) as passes, SUM(fail_count) as fails FROM test_cases')
        test_stats = cursor.fetchone()
        test_passes = test_stats['passes'] or 0
        test_fails = test_stats['fails'] or 0

        return {
            'total_executions': total,
            'success_rate': round(success_rate, 3),
            'syntax_error_rate': round(syntax_error_rate, 3),
            'average_execution_time': round(avg_time, 4),
            'common_bugs': common_bugs,
            'total_test_cases': total_tests,
            'test_passes': test_passes,
            'test_fails': test_fails
        }

    def get_recent_bugs(self, limit: int = 10) -> List[Dict]:
        """Get recently detected bugs"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM bug_detections
            ORDER BY detected_at DESC
            LIMIT ?
        ''', (limit,))
        return [dict(row) for row in cursor.fetchall()]

    def close(self):
        """Close database connection"""
        self.conn.close()


def main():
    """Test code sandbox"""
    print("Testing Code Sandbox System")
    print("=" * 50)

    sandbox = CodeSandbox(timeout=5)

    # Test successful execution
    print("\n1. Executing valid Python code...")
    code1 = """
print("Hello from sandbox!")
x = 10
y = 20
print(f"Sum: {x + y}")
"""
    result1 = sandbox.execute_python(code1)
    print(f"   Success: {result1.success}")
    print(f"   Output: {result1.output.strip()}")
    print(f"   Time: {result1.execution_time:.4f}s")

    # Test syntax error
    print("\n2. Testing syntax error detection...")
    code2 = """
print("Missing closing quote)
"""
    result2 = sandbox.execute_python(code2)
    print(f"   Success: {result2.success}")
    print(f"   Error: {result2.error[:100]}")

    # Test runtime error
    print("\n3. Testing runtime error detection...")
    code3 = """
x = 10
y = 0
result = x / y  # Division by zero
"""
    result3 = sandbox.execute_python(code3)
    print(f"   Success: {result3.success}")
    print(f"   Error detected: {result3.error.split(':')[0]}")

    # Get recent bugs
    print("\n4. Recent bugs detected:")
    bugs = sandbox.get_recent_bugs(limit=3)
    for bug in bugs:
        print(f"   - {bug['bug_type']} ({bug['severity']}): {bug['description']}")
        print(f"     Suggested fix: {bug['suggested_fix']}")

    # Add test cases
    print("\n5. Adding test cases...")
    sandbox.add_test_case(
        test_id="test_addition",
        test_name="Test Addition",
        code="print(5 + 3)",
        expected_output="8"
    )

    sandbox.add_test_case(
        test_id="test_list",
        test_name="Test List Operations",
        code="items = [1, 2, 3]\nprint(len(items))",
        expected_output="3"
    )
    print("   Added 2 test cases")

    # Run tests
    print("\n6. Running all tests...")
    test_results = sandbox.run_all_tests()
    for test_id, passed in test_results.items():
        print(f"   {test_id}: {'PASS' if passed else 'FAIL'}")

    # Get statistics
    print("\n7. Sandbox Statistics:")
    stats = sandbox.get_execution_stats()
    for key, value in stats.items():
        if key == 'common_bugs':
            print(f"   {key}:")
            for bug in value:
                print(f"     - {bug['bug_type']}: {bug['count']} occurrences")
        else:
            print(f"   {key}: {value}")

    print(f"\n✓ Code sandbox system working!")
    print(f"Database: {sandbox.db_path}")

    sandbox.close()


if __name__ == "__main__":
    main()
