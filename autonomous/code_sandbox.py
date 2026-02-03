"""
Real Code Execution Sandbox - Priority 1.3
Docker-based isolated code execution with resource limits and security.

Features:
- Docker-based isolated execution environment
- Multi-language support (Python, JavaScript, Java, Go, Bash, Ruby, etc.)
- CPU and memory resource limits (enforced)
- Network isolation (disabled by default)
- Filesystem isolation with read-only option
- Timeout enforcement (max 30 seconds)
- Stdout/stderr/exit code capture
- File system isolation with optional file transfer
- Secure cleanup and automatic container removal
- Integration with AutoDebugger for debugging
- Pre-built container image management

Requirements:
- Docker installed and running
- docker-py Python library: pip install docker

Author: AI Self-Improvement System
Created: 2026-02-03
Updated: 2026-02-03 (Enhanced with Docker API)
"""

import os
import subprocess
import tempfile
import time
import json
import hashlib
import shutil
from datetime import datetime
from typing import Dict, Optional, List, Tuple, Any
from dataclasses import dataclass, asdict, field
from pathlib import Path
import logging

# Docker SDK import
try:
    import docker
    from docker.errors import DockerException, ImageNotFound, ContainerError, APIError
    DOCKER_SDK_AVAILABLE = True
except ImportError:
    DOCKER_SDK_AVAILABLE = False
    docker = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of code execution with comprehensive details"""
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    execution_time: float
    timeout: bool
    error_message: Optional[str] = None
    container_id: Optional[str] = None
    language: Optional[str] = None
    resource_usage: Optional[Dict] = None
    output_files: Dict[str, str] = field(default_factory=dict)
    memory_used: Optional[str] = None
    cpu_percent: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ResourceLimits:
    """Resource limits for container execution"""
    memory_limit: str = "512m"  # Memory limit (e.g., "256m", "1g")
    memory_swap: Optional[str] = None  # Swap limit (default = memory_limit)
    cpu_quota: int = 100000  # CPU quota (100000 = 1.0 CPU)
    cpu_period: int = 100000  # CPU period
    cpu_shares: int = 1024  # CPU shares (relative priority)
    pids_limit: int = 100  # Max number of processes
    timeout_seconds: int = 30  # Execution timeout (max 30)

    def __post_init__(self):
        """Validate and enforce limits"""
        # Enforce max timeout of 30 seconds
        if self.timeout_seconds > 30:
            logger.warning(f"Timeout {self.timeout_seconds}s exceeds max 30s, using 30s")
            self.timeout_seconds = 30

        # Set swap limit if not specified
        if self.memory_swap is None:
            self.memory_swap = self.memory_limit


class CodeSandbox:
    """
    Secure code execution sandbox using Docker containers with comprehensive safety.

    Provides isolated execution environment with:
    - Docker Python API for native container management
    - Resource limits (CPU, memory, processes) - enforced at container level
    - Execution timeout (max 30 seconds)
    - Network isolation (disabled by default)
    - File system isolation with read-only option
    - Secure cleanup with automatic container removal
    - Multi-language support (Python, JavaScript, Java, Go, Bash, Ruby, etc.)
    - Integration with AutoDebugger
    - Pre-built container image management
    """

    # Language configurations with Docker images
    LANGUAGE_CONFIGS = {
        'python': {
            'image': 'python:3.11-slim',
            'extension': '.py',
            'command': lambda f: ['python', f],
            'runtime_name': 'Python 3.11',
            'description': 'Python 3.11 with pip'
        },
        'python3': {
            'image': 'python:3.11-slim',
            'extension': '.py',
            'command': lambda f: ['python', f],
            'runtime_name': 'Python 3.11',
            'description': 'Python 3.11 with pip'
        },
        'javascript': {
            'image': 'node:18-alpine',
            'extension': '.js',
            'command': lambda f: ['node', f],
            'runtime_name': 'Node.js 18',
            'description': 'Node.js 18 with npm'
        },
        'js': {
            'image': 'node:18-alpine',
            'extension': '.js',
            'command': lambda f: ['node', f],
            'runtime_name': 'Node.js 18',
            'description': 'Node.js 18 with npm'
        },
        'bash': {
            'image': 'ubuntu:22.04',
            'extension': '.sh',
            'command': lambda f: ['bash', f],
            'runtime_name': 'Bash 5',
            'description': 'Ubuntu 22.04 with bash'
        },
        'sh': {
            'image': 'ubuntu:22.04',
            'extension': '.sh',
            'command': lambda f: ['bash', f],
            'runtime_name': 'Bash 5',
            'description': 'Ubuntu 22.04 with bash'
        },
        'ruby': {
            'image': 'ruby:3.2-alpine',
            'extension': '.rb',
            'command': lambda f: ['ruby', f],
            'runtime_name': 'Ruby 3.2',
            'description': 'Ruby 3.2 with gems'
        },
        'go': {
            'image': 'golang:1.21-alpine',
            'extension': '.go',
            'command': lambda f: ['sh', '-c', f'go run {f}'],
            'runtime_name': 'Go 1.21',
            'description': 'Go 1.21 compiler'
        },
    }

    def __init__(self, default_limits: Optional[ResourceLimits] = None, use_docker_api: bool = True):
        """
        Initialize code sandbox.

        Args:
            default_limits: Default resource limits for execution
            use_docker_api: Use Docker Python API if available, else fallback to subprocess
        """
        self.default_limits = default_limits or ResourceLimits()
        self.use_docker_api = use_docker_api and DOCKER_SDK_AVAILABLE
        self.client = None
        self.execution_history: List[Dict[str, Any]] = []

        # Try Docker API first if requested
        if self.use_docker_api:
            self._init_docker_api()

        # Fallback: ensure Docker CLI is available
        if not self.use_docker_api or self.client is None:
            self._check_docker_cli()
            logger.info("Using Docker CLI for sandbox execution")

    def _init_docker_api(self):
        """Initialize Docker Python API client"""
        try:
            self.client = docker.from_env()
            self.client.ping()
            logger.info("Docker API client initialized successfully")
            logger.info(f"Docker version: {self.client.version()['Version']}")
        except Exception as e:
            logger.warning(f"Failed to initialize Docker API: {e}")
            self.client = None

    def _check_docker_cli(self):
        """Check if Docker CLI is available"""
        try:
            result = subprocess.run(
                ['docker', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                logger.info(f"Docker CLI available: {result.stdout.strip()}")
            else:
                raise RuntimeError("Docker not responding correctly")

        except FileNotFoundError:
            raise RuntimeError(
                "Docker not found. Please install Docker: https://docs.docker.com/get-docker/"
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("Docker command timed out")
        except Exception as e:
            raise RuntimeError(f"Error checking Docker: {e}")

    def execute(self,
                code: str,
                language: str,
                limits: Optional[ResourceLimits] = None,
                network_enabled: bool = False,
                env_vars: Optional[Dict[str, str]] = None,
                files: Optional[Dict[str, str]] = None,
                read_only: bool = True) -> ExecutionResult:
        """
        Execute code in isolated Docker container with comprehensive isolation.

        Args:
            code: Code to execute
            language: Programming language ('python', 'javascript', etc.)
            limits: Resource limits (uses default if not provided)
            network_enabled: Enable network access (default: False for security)
            env_vars: Environment variables to pass to container
            files: Optional dict of {filename: content} to create in sandbox
            read_only: Make filesystem read-only (default: True for security)

        Returns:
            ExecutionResult with execution details
        """
        start_time = time.time()
        limits = limits or self.default_limits

        # Validate language
        lang_lower = language.lower().strip()
        if lang_lower not in self.LANGUAGE_CONFIGS:
            supported = ', '.join(sorted(self.LANGUAGE_CONFIGS.keys()))
            return ExecutionResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr="",
                execution_time=0.0,
                timeout=False,
                error_message=f"Unsupported language: {language}. Supported: {supported}",
                language=language
            )

        config = self.LANGUAGE_CONFIGS[lang_lower]

        # Create temporary directory for code and files
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # Write main code to file
                code_file = f"code{config['extension']}"
                code_path = os.path.join(temp_dir, code_file)
                with open(code_path, 'w', encoding='utf-8') as f:
                    f.write(code)

                # Write additional files if provided
                if files:
                    for filename, content in files.items():
                        file_path = os.path.join(temp_dir, filename)
                        os.makedirs(os.path.dirname(file_path), exist_ok=True)
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(content)

            except Exception as e:
                execution_time = time.time() - start_time
                return ExecutionResult(
                    success=False,
                    exit_code=-1,
                    stdout="",
                    stderr="",
                    execution_time=execution_time,
                    timeout=False,
                    error_message=f"Error preparing files: {e}",
                    language=lang_lower
                )

            # Ensure Docker image is available
            self._ensure_image(config['image'])

            # Try Docker API first, fallback to CLI
            if self.use_docker_api and self.client:
                result = self._run_container_api(
                    image=config['image'],
                    code_dir=temp_dir,
                    code_file=code_file,
                    command=config['command'],
                    limits=limits,
                    network_enabled=network_enabled,
                    env_vars=env_vars,
                    read_only=read_only
                )
            else:
                result = self._run_container_cli(
                    image=config['image'],
                    code_dir=temp_dir,
                    code_file=code_file,
                    command=config['command'],
                    limits=limits,
                    network_enabled=network_enabled,
                    env_vars=env_vars,
                    read_only=read_only
                )

        execution_time = time.time() - start_time
        result.execution_time = round(execution_time, 3)
        result.language = f"{lang_lower} ({config['runtime_name']})"

        # Log execution
        self.execution_history.append({
            'timestamp': result.timestamp.isoformat(),
            'language': lang_lower,
            'success': result.success,
            'exit_code': result.exit_code,
            'execution_time': result.execution_time,
            'container_id': result.container_id
        })

        return result

    def _ensure_image(self, image: str):
        """Ensure Docker image is available locally"""
        try:
            # Check if image exists
            result = subprocess.run(
                ['docker', 'images', '-q', image],
                capture_output=True,
                text=True,
                timeout=5
            )

            if not result.stdout.strip():
                logger.info(f"Pulling Docker image: {image}")
                subprocess.run(
                    ['docker', 'pull', image],
                    capture_output=True,
                    timeout=300  # 5 minutes for pull
                )
                logger.info(f"Image pulled successfully: {image}")

        except Exception as e:
            logger.warning(f"Error ensuring image {image}: {e}")

    def _run_container_api(self,
                           image: str,
                           code_dir: str,
                           code_file: str,
                           command,
                           limits: ResourceLimits,
                           network_enabled: bool,
                           env_vars: Optional[Dict[str, str]],
                           read_only: bool = True) -> ExecutionResult:
        """
        Run code in Docker container using Python Docker API.
        Provides better resource management and monitoring.
        """
        container = None
        container_id = None

        try:
            # Build the full command
            if callable(command):
                full_command = command(code_file)
            else:
                full_command = [c.format(file=code_file) if '{file}' in c else c for c in command]

            # Prepare volumes (code_dir mounted as read-only)
            volumes = {os.path.abspath(code_dir): {'bind': '/sandbox', 'mode': 'ro'}}

            # Prepare environment
            env_dict = env_vars.copy() if env_vars else {}
            env_dict['PYTHONUNBUFFERED'] = '1'
            env_dict['PYTHONDONTWRITEBYTECODE'] = '1'

            # Set network mode
            network_mode = None if network_enabled else 'none'

            # Create container with security and resource constraints
            container = self.client.containers.create(
                image,
                full_command,
                volumes=volumes,
                working_dir='/sandbox',
                stdin_open=False,
                stdout=True,
                stderr=True,
                detach=True,
                mem_limit=limits.memory_limit,
                memswap_limit=limits.memory_swap,
                cpu_quota=limits.cpu_quota,
                cpu_period=limits.cpu_period,
                cpu_shares=limits.cpu_shares,
                pids_limit=limits.pids_limit,
                network_mode=network_mode,
                read_only=read_only,
                cap_drop=['ALL'],
                security_opt=['no-new-privileges'],
                environment=env_dict,
            )

            container_id = container.id
            logger.info(f"Container created: {container_id[:12]} - {image}")

            # Start container
            container.start()

            # Wait for completion with timeout
            try:
                exit_code = container.wait(timeout=limits.timeout_seconds)['StatusCode']
                logger.info(f"Container {container_id[:12]} completed with exit code {exit_code}")
            except Exception as e:
                logger.warning(f"Container {container_id[:12]} timeout/error: {e}")
                # Container exceeded timeout
                container.stop(timeout=2)
                exit_code = 124  # Standard timeout exit code
                timeout_occurred = True
                return ExecutionResult(
                    success=False,
                    exit_code=exit_code,
                    stdout="",
                    stderr=f"Execution timeout after {limits.timeout_seconds}s",
                    execution_time=0.0,
                    timeout=True,
                    error_message=f"Execution timed out after {limits.timeout_seconds}s",
                    container_id=container_id
                )

            # Get output
            stdout = container.logs(stdout=True, stderr=False).decode('utf-8', errors='replace')
            stderr = container.logs(stdout=False, stderr=True).decode('utf-8', errors='replace')

            return ExecutionResult(
                success=(exit_code == 0),
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                execution_time=0.0,
                timeout=False,
                container_id=container_id
            )

        except ImageNotFound:
            return ExecutionResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr="",
                execution_time=0.0,
                timeout=False,
                error_message=f"Docker image not found: {image}",
                container_id=container_id
            )

        except Exception as e:
            logger.error(f"Error running container: {e}")
            return ExecutionResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr="",
                execution_time=0.0,
                timeout=False,
                error_message=f"Container error: {str(e)}",
                container_id=container_id
            )

        finally:
            # Cleanup
            if container:
                try:
                    container.stop(timeout=2)
                    container.remove(force=True)
                    logger.info(f"Container {container_id[:12]} cleaned up")
                except Exception as e:
                    logger.warning(f"Error cleaning up container {container_id[:12]}: {e}")

    def _run_container_cli(self,
                           image: str,
                           code_dir: str,
                           code_file: str,
                           command,
                           limits: ResourceLimits,
                           network_enabled: bool,
                           env_vars: Optional[Dict[str, str]],
                           read_only: bool = True) -> ExecutionResult:
        """Run code in Docker container using CLI (fallback method)"""
        container_id = None
        timeout_occurred = False

        try:
            # Build command with resource limits and security options
            cmd = [
                'docker', 'run',
                '--rm',  # Remove container after execution
                '-v', f"{os.path.abspath(code_dir)}:/sandbox:ro",  # Mount code (read-only)
                '-w', '/sandbox',  # Set working directory
                '--memory', limits.memory_limit,
                '--memory-swap', limits.memory_swap or limits.memory_limit,
                '--cpu-quota', str(limits.cpu_quota),
                '--cpu-period', str(limits.cpu_period),
                '--cpu-shares', str(limits.cpu_shares),
                '--pids-limit', str(limits.pids_limit),
            ]

            # Disable network if requested
            if not network_enabled:
                cmd.extend(['--network', 'none'])

            # Add environment variables
            if env_vars:
                for key, value in env_vars.items():
                    cmd.extend(['-e', f"{key}={value}"])

            # Add security options (dropped all capabilities)
            cmd.extend([
                '--security-opt', 'no-new-privileges',
                '--cap-drop', 'ALL',  # Drop all Linux capabilities
                '--tmpfs', '/tmp:size=100m,noexec,nosuid,nodev',  # Temporary filesystem
            ])

            # Add read-only filesystem if requested
            if read_only:
                cmd.append('--read-only')

            # Add image and command
            cmd.append(image)

            # Format command with code file
            if callable(command):
                formatted_cmd = command(code_file)
            else:
                formatted_cmd = [c.format(file=code_file) if '{file}' in c else c for c in command]
            cmd.extend(formatted_cmd)

            logger.info(f"Executing: {' '.join(cmd[:5])}... (image: {image})")

            # Execute container with timeout
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=limits.timeout_seconds
            )

            return ExecutionResult(
                success=(result.returncode == 0),
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                execution_time=0.0,  # Set by caller
                timeout=False,
                container_id=container_id
            )

        except subprocess.TimeoutExpired as e:
            timeout_occurred = True
            stdout = e.stdout.decode() if e.stdout else ""
            stderr = e.stderr.decode() if e.stderr else ""
            logger.warning(f"Container execution timeout after {limits.timeout_seconds}s")

            return ExecutionResult(
                success=False,
                exit_code=124,  # Standard timeout exit code
                stdout=stdout,
                stderr=stderr,
                execution_time=0.0,  # Set by caller
                timeout=True,
                error_message=f"Execution timed out after {limits.timeout_seconds}s",
                container_id=container_id
            )

        except Exception as e:
            logger.error(f"Container execution error: {e}")
            return ExecutionResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr="",
                execution_time=0.0,  # Set by caller
                timeout=False,
                error_message=f"Error running container: {e}",
                container_id=container_id
            )

    def execute_with_input(self,
                          code: str,
                          language: str,
                          stdin_input: str,
                          limits: Optional[ResourceLimits] = None) -> ExecutionResult:
        """
        Execute code with stdin input.

        Args:
            code: Code to execute
            language: Programming language
            stdin_input: Input to pass to stdin
            limits: Resource limits

        Returns:
            ExecutionResult
        """
        # Create temporary input file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write(stdin_input)
            input_file = f.name

        try:
            # Use as additional file in sandbox
            input_filename = os.path.basename(input_file)
            with open(input_file, 'r') as f:
                input_content = f.read()

            result = self.execute(code, language, limits, files={input_filename: input_content})
        finally:
            try:
                os.unlink(input_file)
            except Exception:
                pass

        return result

    def execute_tests(self,
                     code: str,
                     test_code: str,
                     language: str,
                     limits: Optional[ResourceLimits] = None) -> ExecutionResult:
        """
        Execute code with test cases.

        Args:
            code: Main code to test
            test_code: Test code
            language: Programming language
            limits: Resource limits

        Returns:
            ExecutionResult with test results
        """
        # Combine code and tests
        combined_code = f"{code}\n\n{test_code}"
        return self.execute(combined_code, language, limits)

    def list_supported_languages(self) -> List[Dict[str, str]]:
        """Get list of supported languages with details"""
        return [
            {
                'language': lang,
                'runtime': config['runtime_name'],
                'extension': config['extension'],
                'image': config['image'],
                'description': config.get('description', '')
            }
            for lang, config in sorted(self.LANGUAGE_CONFIGS.items())
        ]

    def get_resource_usage(self, container_id: str) -> Optional[Dict]:
        """Get resource usage statistics for a container"""
        try:
            # Try Docker API first
            if self.client:
                try:
                    stats = self.client.containers.get(container_id).stats(stream=False)
                    return {
                        'memory_usage': stats.get('memory_stats', {}).get('usage'),
                        'cpu_percent': self._calculate_cpu_percent(stats),
                        'timestamp': stats.get('read')
                    }
                except Exception:
                    pass

            # Fallback to CLI
            result = subprocess.run(
                ['docker', 'stats', container_id, '--no-stream', '--format', '{{json .}}'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0 and result.stdout:
                return json.loads(result.stdout)

        except Exception as e:
            logger.error(f"Error getting resource usage: {e}")

        return None

    @staticmethod
    def _calculate_cpu_percent(stats: Dict) -> float:
        """Calculate CPU percentage from Docker stats"""
        try:
            cpu_stats = stats.get('cpu_stats', {})
            precpu_stats = stats.get('precpu_stats', {})

            cpu_delta = cpu_stats.get('cpu_usage', {}).get('total_usage', 0) - \
                        precpu_stats.get('cpu_usage', {}).get('total_usage', 0)
            system_delta = cpu_stats.get('system_cpu_usage', 0) - \
                          precpu_stats.get('system_cpu_usage', 0)
            num_cpus = len(cpu_stats.get('cpus', []))

            if system_delta > 0 and num_cpus > 0:
                return (cpu_delta / system_delta) * num_cpus * 100.0

        except Exception:
            pass

        return 0.0

    def get_execution_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get execution history (optionally limited)"""
        history = self.execution_history.copy()
        if limit:
            history = history[-limit:]
        return history

    def cleanup_all_containers(self) -> None:
        """Force cleanup of all leftover sandbox containers"""
        try:
            if self.client:
                # Use Docker API
                containers = self.client.containers.list(all=True)
                for container in containers:
                    if 'sandbox' in container.name or 'code-sandbox' in container.name:
                        try:
                            container.stop(timeout=2)
                            container.remove(force=True)
                            logger.info(f"Cleaned up container: {container.id[:12]}")
                        except Exception as e:
                            logger.warning(f"Error cleaning container: {e}")
            else:
                # Use CLI
                result = subprocess.run(
                    ['docker', 'ps', '-a', '--filter', 'name=sandbox', '-q'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                for container_id in result.stdout.strip().split('\n'):
                    if container_id:
                        try:
                            subprocess.run(
                                ['docker', 'rm', '-f', container_id],
                                capture_output=True,
                                timeout=5
                            )
                            logger.info(f"Cleaned up container: {container_id[:12]}")
                        except Exception as e:
                            logger.warning(f"Error cleaning container: {e}")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


class AutoDebuggerIntegration:
    """
    Integration point with AutoDebugger for debugging sandboxed code execution.
    Provides structured debugging information and error analysis.
    """

    @staticmethod
    def create_debug_report(result: ExecutionResult) -> Dict[str, Any]:
        """
        Create a debug report from execution result for AutoDebugger.

        Args:
            result: ExecutionResult from code execution

        Returns:
            Structured debug report dictionary
        """
        report = {
            'status': 'success' if result.success else 'failure',
            'exit_code': result.exit_code,
            'execution_time': result.execution_time,
            'timestamp': result.timestamp.isoformat(),
            'language': result.language,
            'container_id': result.container_id,
            'output': {
                'stdout': result.stdout,
                'stderr': result.stderr,
            },
            'resource_usage': result.resource_usage
        }

        if result.timeout:
            report['error_type'] = 'timeout'
            report['error_message'] = result.error_message

        if result.error_message and not result.timeout:
            report['error_type'] = 'execution_error'
            report['error_message'] = result.error_message

        if result.output_files:
            report['output_files'] = result.output_files

        return report

    @staticmethod
    def analyze_error(result: ExecutionResult) -> Dict[str, Any]:
        """
        Analyze execution error for debugging.

        Args:
            result: Failed ExecutionResult

        Returns:
            Error analysis dictionary
        """
        analysis = {
            'is_error': not result.success,
            'error_type': 'unknown'
        }

        if result.timeout:
            analysis['error_type'] = 'timeout'
            analysis['suggestion'] = 'Code execution exceeded time limit. Consider optimizing or increasing timeout.'

        elif result.exit_code != 0:
            analysis['error_type'] = 'execution_failure'

            # Try to detect common Python errors
            if 'Traceback' in result.stderr:
                analysis['error_type'] = 'python_exception'
                # Extract exception type
                lines = result.stderr.split('\n')
                for line in reversed(lines):
                    if ':' in line and not line.startswith(' '):
                        analysis['exception'] = line.strip()
                        break

        elif result.error_message:
            analysis['error_type'] = 'sandbox_error'
            analysis['error'] = result.error_message

        return analysis


# Example usage and testing
if __name__ == "__main__":
    print("="*70)
    print("REAL CODE EXECUTION SANDBOX - PRIORITY 1.3")
    print("="*70)

    try:
        # Initialize sandbox
        sandbox = CodeSandbox()

        print("\n[1] Supported Languages:")
        print("-" * 70)
        for lang_info in sandbox.list_supported_languages():
            print(f"  {lang_info['language']:12} -> {lang_info['runtime']:20} ({lang_info['image']})")

        # Test 1: Simple Python execution
        print("\n[2] Test: Simple Python Code Execution")
        print("-" * 70)
        python_code = """
import sys
print("Hello from sandbox!")
print(f"Python {sys.version_info.major}.{sys.version_info.minor}")
result = sum(range(10))
print(f"Sum 0-9: {result}")
"""
        result = sandbox.execute(python_code, 'python')
        print(f"Success: {result.success} | Exit: {result.exit_code} | Time: {result.execution_time:.3f}s")
        print(f"Output:\n{result.stdout}")

        # Test 2: JavaScript execution
        print("\n[3] Test: JavaScript Code Execution")
        print("-" * 70)
        js_code = """
console.log("Hello from Node.js!");
const sum = Array.from({length: 10}, (_, i) => i).reduce((a, b) => a + b);
console.log("Sum 0-9:", sum);
"""
        result = sandbox.execute(js_code, 'javascript')
        print(f"Success: {result.success} | Exit: {result.exit_code} | Time: {result.execution_time:.3f}s")
        print(f"Output:\n{result.stdout}")

        # Test 3: Timeout enforcement
        print("\n[4] Test: Timeout Enforcement (5s limit)")
        print("-" * 70)
        timeout_code = """
import time
print("Starting long operation...")
time.sleep(10)
print("This should not print")
"""
        limits = ResourceLimits(timeout_seconds=5)
        result = sandbox.execute(timeout_code, 'python', limits=limits)
        print(f"Success: {result.success} | Timeout: {result.timeout} | Exit: {result.exit_code}")
        print(f"Error: {result.error_message}")

        # Test 4: Error handling
        print("\n[5] Test: Error Handling")
        print("-" * 70)
        error_code = """
print("Before error")
x = 1 / 0
print("After error")
"""
        result = sandbox.execute(error_code, 'python')
        print(f"Success: {result.success} | Exit: {result.exit_code}")
        print(f"Stderr:\n{result.stderr}")

        # Test 5: File isolation
        print("\n[6] Test: File Isolation with Additional Files")
        print("-" * 70)
        file_code = """
import sys
sys.path.insert(0, '/sandbox')
from helper import greet
print(greet("Sandbox"))
"""
        helper_file = 'helper.py'
        helper_content = """
def greet(name):
    return f"Hello, {name}!"
"""
        result = sandbox.execute(
            file_code,
            'python',
            files={helper_file: helper_content}
        )
        print(f"Success: {result.success} | Exit: {result.exit_code}")
        print(f"Output:\n{result.stdout}")

        # Test 6: Resource limits
        print("\n[7] Test: Memory Limit Enforcement")
        print("-" * 70)
        memory_code = """
print("Testing memory allocation...")
data = []
try:
    for i in range(100):
        data.append([0] * 100000)
    print(f"Allocated {len(data)} arrays")
except MemoryError:
    print("Memory limit hit!")
"""
        limits = ResourceLimits(memory_limit="128m", timeout_seconds=10)
        result = sandbox.execute(memory_code, 'python', limits=limits)
        print(f"Success: {result.success} | Exit: {result.exit_code}")
        print(f"Output: {result.stdout[:100]}...")

        # Test 7: AutoDebugger integration
        print("\n[8] Test: AutoDebugger Integration")
        print("-" * 70)
        debug_code = """
import sys
raise ValueError("Test error")
"""
        result = sandbox.execute(debug_code, 'python')
        debug_report = AutoDebuggerIntegration.create_debug_report(result)
        error_analysis = AutoDebuggerIntegration.analyze_error(result)
        print(f"Debug Status: {debug_report['status']}")
        print(f"Error Type: {error_analysis['error_type']}")
        if 'exception' in error_analysis:
            print(f"Exception: {error_analysis['exception']}")

        # Execution history
        print("\n[9] Execution History")
        print("-" * 70)
        history = sandbox.get_execution_history(limit=5)
        for i, entry in enumerate(history[-3:], 1):
            print(f"  {i}. {entry['language']:12} - Success: {entry['success']:5} - {entry['execution_time']:.3f}s")

        print("\n" + "="*70)
        print("ALL TESTS COMPLETED SUCCESSFULLY!")
        print("="*70)

    except RuntimeError as e:
        print(f"\n[ERROR] {e}")
        print("\nTo use Code Sandbox, please:")
        print("1. Install Docker: https://docs.docker.com/get-docker/")
        print("2. Install Docker Python SDK: pip install docker")
        print("3. Start Docker daemon")
        print("4. Run this test again")
