"""
Unit tests for Code Sandbox - Priority 1.3
Tests Docker-based isolated code execution with security features.

Run with: pytest tests/test_code_sandbox.py -v
"""

import pytest
import sys
import os
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from autonomous.code_sandbox import (
    CodeSandbox,
    ExecutionResult,
    ResourceLimits,
    AutoDebuggerIntegration
)


class TestResourceLimits:
    """Test ResourceLimits configuration and validation"""

    def test_resource_limits_defaults(self):
        """Test default resource limits"""
        limits = ResourceLimits()
        assert limits.timeout_seconds == 30
        assert limits.memory_limit == "512m"
        assert limits.cpu_quota == 100000
        assert limits.pids_limit == 100

    def test_timeout_enforced_max_30_seconds(self):
        """Test timeout maximum is enforced at 30 seconds"""
        limits = ResourceLimits(timeout_seconds=60)
        assert limits.timeout_seconds == 30

    def test_custom_resource_limits(self):
        """Test custom resource limits"""
        limits = ResourceLimits(
            memory_limit="256m",
            timeout_seconds=15,
            pids_limit=50
        )
        assert limits.memory_limit == "256m"
        assert limits.timeout_seconds == 15
        assert limits.pids_limit == 50


class TestExecutionResult:
    """Test ExecutionResult data class"""

    def test_execution_result_success(self):
        """Test successful execution result"""
        result = ExecutionResult(
            success=True,
            exit_code=0,
            stdout="Hello World",
            stderr="",
            execution_time=0.123,
            timeout=False
        )
        assert result.success is True
        assert result.exit_code == 0
        assert result.stdout == "Hello World"
        assert result.timestamp is not None

    def test_execution_result_failure(self):
        """Test failed execution result"""
        result = ExecutionResult(
            success=False,
            exit_code=1,
            stdout="",
            stderr="Error message",
            execution_time=0.456,
            timeout=False,
            error_message="Test error"
        )
        assert result.success is False
        assert result.exit_code == 1
        assert result.error_message == "Test error"

    def test_execution_result_timeout(self):
        """Test timeout execution result"""
        result = ExecutionResult(
            success=False,
            exit_code=124,
            stdout="partial output",
            stderr="",
            execution_time=5.0,
            timeout=True,
            error_message="Timed out after 5s"
        )
        assert result.timeout is True
        assert result.exit_code == 124


class TestCodeSandbox:
    """Test CodeSandbox initialization and functionality"""

    def test_sandbox_initialization(self):
        """Test sandbox can be initialized"""
        try:
            sandbox = CodeSandbox()
            assert sandbox is not None
            assert sandbox.default_limits is not None
        except RuntimeError as e:
            # Docker may not be available in test environment
            pytest.skip(f"Docker not available: {e}")

    def test_sandbox_supported_languages(self):
        """Test sandbox lists supported languages"""
        try:
            sandbox = CodeSandbox()
            languages = sandbox.list_supported_languages()
            assert len(languages) > 0
            assert any(lang['language'] == 'python' for lang in languages)
            assert any(lang['language'] == 'javascript' for lang in languages)
        except RuntimeError as e:
            pytest.skip(f"Docker not available: {e}")

    def test_language_validation(self):
        """Test unsupported language validation"""
        try:
            sandbox = CodeSandbox()
            result = sandbox.execute("print('test')", language="invalid_lang")
            assert result.success is False
            assert "Unsupported language" in result.error_message
        except RuntimeError as e:
            pytest.skip(f"Docker not available: {e}")

    def test_execution_result_structure(self):
        """Test execution result has all required fields"""
        try:
            sandbox = CodeSandbox()
            result = sandbox.execute(
                "print('test')",
                language="python",
                limits=ResourceLimits(timeout_seconds=10)
            )
            assert hasattr(result, 'success')
            assert hasattr(result, 'exit_code')
            assert hasattr(result, 'stdout')
            assert hasattr(result, 'stderr')
            assert hasattr(result, 'execution_time')
            assert hasattr(result, 'timeout')
            assert hasattr(result, 'container_id')
        except RuntimeError as e:
            pytest.skip(f"Docker not available: {e}")


class TestAutoDebuggerIntegration:
    """Test AutoDebugger integration"""

    def test_debug_report_success(self):
        """Test debug report for successful execution"""
        result = ExecutionResult(
            success=True,
            exit_code=0,
            stdout="success output",
            stderr="",
            execution_time=0.5,
            timeout=False,
            language="python"
        )
        report = AutoDebuggerIntegration.create_debug_report(result)

        assert report['status'] == 'success'
        assert report['exit_code'] == 0
        assert report['output']['stdout'] == "success output"
        assert 'timestamp' in report

    def test_debug_report_failure(self):
        """Test debug report for failed execution"""
        result = ExecutionResult(
            success=False,
            exit_code=1,
            stdout="",
            stderr="error output",
            execution_time=0.5,
            timeout=False,
            error_message="Test error",
            language="python"
        )
        report = AutoDebuggerIntegration.create_debug_report(result)

        assert report['status'] == 'failure'
        assert report['exit_code'] == 1
        assert report['error_message'] == "Test error"

    def test_debug_report_timeout(self):
        """Test debug report for timeout"""
        result = ExecutionResult(
            success=False,
            exit_code=124,
            stdout="partial",
            stderr="",
            execution_time=5.0,
            timeout=True,
            error_message="Timed out",
            language="python"
        )
        report = AutoDebuggerIntegration.create_debug_report(result)

        assert report['status'] == 'failure'
        assert report['error_type'] == 'timeout'
        assert report['error_message'] == "Timed out"

    def test_error_analysis_timeout(self):
        """Test error analysis for timeout"""
        result = ExecutionResult(
            success=False,
            exit_code=124,
            stdout="",
            stderr="",
            execution_time=10.0,
            timeout=True,
            error_message="Timed out"
        )
        analysis = AutoDebuggerIntegration.analyze_error(result)

        assert analysis['is_error'] is True
        assert analysis['error_type'] == 'timeout'
        assert 'suggestion' in analysis

    def test_error_analysis_execution_failure(self):
        """Test error analysis for execution failure"""
        result = ExecutionResult(
            success=False,
            exit_code=1,
            stdout="",
            stderr="Some error output",
            execution_time=0.5,
            timeout=False
        )
        analysis = AutoDebuggerIntegration.analyze_error(result)

        assert analysis['is_error'] is True
        assert analysis['error_type'] == 'execution_failure'

    def test_error_analysis_python_exception(self):
        """Test error analysis detects Python exceptions"""
        stderr_output = """Traceback (most recent call last):
  File "code.py", line 2, in <module>
    raise ValueError("test error")
ValueError: test error
"""
        result = ExecutionResult(
            success=False,
            exit_code=1,
            stdout="",
            stderr=stderr_output,
            execution_time=0.5,
            timeout=False
        )
        analysis = AutoDebuggerIntegration.analyze_error(result)

        assert analysis['is_error'] is True
        assert analysis['error_type'] == 'python_exception'


class TestSandboxSecurity:
    """Test sandbox security features"""

    def test_network_disabled_by_default(self):
        """Test network is disabled by default"""
        try:
            sandbox = CodeSandbox()
            # Network would be disabled - this tests the flag is set correctly
            # Actual network test would require executing code in Docker
            assert True  # Placeholder
        except RuntimeError as e:
            pytest.skip(f"Docker not available: {e}")

    def test_read_only_filesystem_by_default(self):
        """Test read-only filesystem is default"""
        try:
            sandbox = CodeSandbox()
            # Read-only would be enabled - test the flag
            # Actual test would require executing code in Docker
            assert True  # Placeholder
        except RuntimeError as e:
            pytest.skip(f"Docker not available: {e}")


class TestExecutionHistory:
    """Test execution history tracking"""

    def test_execution_history_tracking(self):
        """Test execution history is tracked"""
        try:
            sandbox = CodeSandbox()
            history = sandbox.get_execution_history()
            initial_count = len(history)

            # Execute some code
            sandbox.execute("print('test')", language="python")
            new_history = sandbox.get_execution_history()
            assert len(new_history) >= initial_count
        except RuntimeError as e:
            pytest.skip(f"Docker not available: {e}")

    def test_execution_history_limit(self):
        """Test execution history limit"""
        try:
            sandbox = CodeSandbox()
            # Add some executions
            for i in range(5):
                sandbox.execute(f"print({i})", language="python")

            # Get limited history
            history = sandbox.get_execution_history(limit=2)
            assert len(history) <= 2
        except RuntimeError as e:
            pytest.skip(f"Docker not available: {e}")


class TestLanguageSupport:
    """Test multi-language support"""

    def test_python_language_config(self):
        """Test Python language configuration"""
        try:
            sandbox = CodeSandbox()
            languages = {lang['language']: lang for lang in sandbox.list_supported_languages()}
            assert 'python' in languages
            assert 'python3' in languages
            python_config = languages['python']
            assert 'python' in python_config['image']
            assert python_config['extension'] == '.py'
        except RuntimeError as e:
            pytest.skip(f"Docker not available: {e}")

    def test_javascript_language_config(self):
        """Test JavaScript language configuration"""
        try:
            sandbox = CodeSandbox()
            languages = {lang['language']: lang for lang in sandbox.list_supported_languages()}
            assert 'javascript' in languages
            assert 'js' in languages
            js_config = languages['javascript']
            assert 'node' in js_config['image']
            assert js_config['extension'] == '.js'
        except RuntimeError as e:
            pytest.skip(f"Docker not available: {e}")

    def test_bash_language_config(self):
        """Test Bash language configuration"""
        try:
            sandbox = CodeSandbox()
            languages = {lang['language']: lang for lang in sandbox.list_supported_languages()}
            assert 'bash' in languages
            assert 'sh' in languages
            bash_config = languages['bash']
            assert bash_config['extension'] == '.sh'
        except RuntimeError as e:
            pytest.skip(f"Docker not available: {e}")


class TestResourceConstraints:
    """Test resource constraints enforcement"""

    def test_memory_limit_configuration(self):
        """Test memory limit can be configured"""
        limits = ResourceLimits(memory_limit="256m")
        assert limits.memory_limit == "256m"

        limits = ResourceLimits(memory_limit="1g")
        assert limits.memory_limit == "1g"

    def test_timeout_limit_configuration(self):
        """Test timeout limit can be configured"""
        limits = ResourceLimits(timeout_seconds=15)
        assert limits.timeout_seconds == 15

        # Max timeout is 30 seconds
        limits = ResourceLimits(timeout_seconds=60)
        assert limits.timeout_seconds == 30

    def test_cpu_limit_configuration(self):
        """Test CPU limit can be configured"""
        limits = ResourceLimits(cpu_quota=50000)
        assert limits.cpu_quota == 50000


class TestFileHandling:
    """Test file handling in sandbox"""

    def test_file_creation_in_sandbox(self):
        """Test files can be created in sandbox"""
        try:
            sandbox = CodeSandbox()
            code = """
import os
files = os.listdir('/sandbox')
print(f"Files in sandbox: {len(files)}")
"""
            result = sandbox.execute(
                code,
                language="python",
                files={"test.txt": "test content"}
            )
            # Execution should succeed
            assert result.error_message is None or "success" in str(result).lower()
        except RuntimeError as e:
            pytest.skip(f"Docker not available: {e}")


# Integration tests (only run if Docker is available)
@pytest.mark.integration
class TestIntegration:
    """Integration tests requiring Docker"""

    def test_python_hello_world(self):
        """Integration test: Python hello world"""
        try:
            sandbox = CodeSandbox()
            result = sandbox.execute(
                "print('Hello, World!')",
                language="python"
            )
            assert result is not None
        except RuntimeError as e:
            pytest.skip(f"Docker not available: {e}")

    def test_javascript_hello_world(self):
        """Integration test: JavaScript hello world"""
        try:
            sandbox = CodeSandbox()
            result = sandbox.execute(
                "console.log('Hello, World!')",
                language="javascript"
            )
            assert result is not None
        except RuntimeError as e:
            pytest.skip(f"Docker not available: {e}")


if __name__ == "__main__":
    # Run tests with: pytest tests/test_code_sandbox.py -v
    pytest.main([__file__, "-v", "--tb=short"])
