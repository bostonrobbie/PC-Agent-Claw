# Real Code Execution Sandbox - Priority 1.3

## Overview

A production-grade Docker-based code execution sandbox that provides secure, isolated execution of code with comprehensive resource limits, timeout enforcement, and multi-language support.

**Location**: `autonomous/code_sandbox.py`
**Tests**: `tests/test_code_sandbox.py`
**Status**: Complete implementation with 29 unit tests passing

## Features

### Core Capabilities
- **Docker-based Isolation**: Containers provide complete filesystem, network, and process isolation
- **Multi-Language Support**: Python, JavaScript, Bash, Ruby, Go (easily extensible)
- **Resource Limits**: CPU, memory, and process limits enforced at container level
- **Timeout Enforcement**: Maximum 30-second execution limit (configurable, max 30s)
- **Network Isolation**: Network disabled by default for security
- **Read-only Filesystem**: Code and system files are read-only by default
- **Secure Cleanup**: Automatic container removal and resource cleanup

### Advanced Features
- **Docker Python API Integration**: Native Docker API support with CLI fallback
- **Dual Execution Paths**: Docker API for better resource management, CLI fallback
- **File Management**: Create and access files within sandbox
- **Execution History**: Track all executions with metadata
- **Error Analysis**: Detailed error detection and categorization
- **AutoDebugger Integration**: Debug reports and error analysis for debugging
- **Resource Monitoring**: CPU and memory usage tracking

### Security Features
- **Capability Dropping**: All Linux capabilities dropped by default
- **Privilege Escalation Prevention**: `no-new-privileges` security option enabled
- **Read-only Root**: Root filesystem is read-only by default
- **Network Disabled**: Network access disabled by default
- **Process Limit**: Maximum process count enforced
- **Memory Limit**: Memory and swap limits enforced
- **CPU Limit**: CPU quota and shares enforced
- **No Host Access**: Complete filesystem isolation from host

## Installation

### Requirements
```bash
# Docker must be installed and running
# Docker Desktop: https://www.docker.com/products/docker-desktop
# Docker Engine (Linux): https://docs.docker.com/engine/install/

# Python dependencies
pip install docker  # For Docker Python API (optional, CLI fallback available)
```

### Docker Images (auto-pulled)
- `python:3.11-slim` - Python 3.11 with pip
- `node:18-alpine` - Node.js 18 with npm
- `ubuntu:22.04` - Ubuntu 22.04 with bash
- `ruby:3.2-alpine` - Ruby 3.2
- `golang:1.21-alpine` - Go 1.21

## Usage

### Basic Usage

#### Simple Code Execution
```python
from autonomous.code_sandbox import CodeSandbox

# Initialize sandbox
sandbox = CodeSandbox()

# Execute Python code
result = sandbox.execute(
    code="print('Hello, World!'); print(sum(range(10)))",
    language="python"
)

print(f"Success: {result.success}")
print(f"Output: {result.stdout}")
print(f"Exit code: {result.exit_code}")
print(f"Execution time: {result.execution_time}s")
```

#### JavaScript Execution
```python
js_code = """
console.log("Hello from Node.js");
const sum = Array.from({length: 100}, (_, i) => i).reduce((a, b) => a + b);
console.log("Sum:", sum);
"""

result = sandbox.execute(js_code, language="javascript")
```

#### Custom Resource Limits
```python
from autonomous.code_sandbox import ResourceLimits

limits = ResourceLimits(
    memory_limit="256m",      # Max 256MB RAM
    timeout_seconds=15,        # Max 15 seconds
    cpu_quota=50000,          # 0.5 CPU
    pids_limit=50             # Max 50 processes
)

result = sandbox.execute(code, "python", limits=limits)
```

#### File Management
```python
# Create and use files in sandbox
files = {
    "helper.py": "def greet(name): return f'Hello, {name}!'",
    "data.json": '{"key": "value"}'
}

code = """
import sys
sys.path.insert(0, '/sandbox')
from helper import greet
print(greet("Sandbox"))

import json
with open('/sandbox/data.json') as f:
    data = json.load(f)
    print(data)
"""

result = sandbox.execute(code, "python", files=files)
```

#### Network and Filesystem Control
```python
# Enable network (WARNING: reduces security)
result = sandbox.execute(
    code="import urllib.request; ...",
    language="python",
    network_enabled=True  # Default: False
)

# Writable filesystem (WARNING: reduces security)
result = sandbox.execute(
    code="with open('/sandbox/output.txt', 'w') as f: f.write('test')",
    language="python",
    read_only=False  # Default: True
)
```

### Supported Languages

```python
sandbox = CodeSandbox()
languages = sandbox.list_supported_languages()

for lang_info in languages:
    print(f"{lang_info['language']:12} -> {lang_info['runtime']:20} ({lang_info['image']})")
```

Output:
```
bash         -> Bash 5               (ubuntu:22.04)
go           -> Go 1.21              (golang:1.21-alpine)
javascript   -> Node.js 18           (node:18-alpine)
js           -> Node.js 18           (node:18-alpine)
python       -> Python 3.11          (python:3.11-slim)
python3      -> Python 3.11          (python:3.11-slim)
ruby         -> Ruby 3.2             (ruby:3.2-alpine)
sh           -> Bash 5               (ubuntu:22.04)
```

### Execution Result

The `ExecutionResult` object contains:
- `success` (bool): Execution was successful
- `exit_code` (int): Exit code from program
- `stdout` (str): Standard output
- `stderr` (str): Standard error output
- `execution_time` (float): Execution time in seconds
- `timeout` (bool): Execution timed out
- `error_message` (str): Error description if any
- `container_id` (str): Docker container ID
- `language` (str): Language and runtime info
- `resource_usage` (dict): Resource usage statistics
- `timestamp` (datetime): Execution timestamp

### Execution History

```python
# Track all executions
history = sandbox.get_execution_history()

# Limited history
recent = sandbox.get_execution_history(limit=5)

for entry in recent:
    print(f"{entry['language']:12} - Success: {entry['success']:5} - {entry['execution_time']:.3f}s")
```

### AutoDebugger Integration

```python
from autonomous.code_sandbox import AutoDebuggerIntegration

# Create debug report
result = sandbox.execute(error_code, "python")
debug_report = AutoDebuggerIntegration.create_debug_report(result)

# Analyze errors
error_analysis = AutoDebuggerIntegration.analyze_error(result)
print(f"Error Type: {error_analysis['error_type']}")
if 'suggestion' in error_analysis:
    print(f"Suggestion: {error_analysis['suggestion']}")
```

Debug report structure:
```json
{
    "status": "success|failure",
    "exit_code": 0,
    "execution_time": 0.123,
    "timestamp": "2026-02-03T12:34:56.789012",
    "language": "python",
    "container_id": "abc123def456",
    "output": {
        "stdout": "...",
        "stderr": "..."
    },
    "resource_usage": {...},
    "error_type": "timeout|execution_error|python_exception",
    "error_message": "..."
}
```

## Architecture

### Class Hierarchy

```
ResourceLimits
  - Enforces resource constraints
  - Validates timeout (max 30s)
  - Manages memory, CPU, process limits

ExecutionResult
  - Encapsulates execution outcome
  - Tracks timing and resource usage
  - Stores execution metadata

CodeSandbox
  - Main interface for code execution
  - Supports Docker API and CLI
  - Manages container lifecycle
  - Tracks execution history

AutoDebuggerIntegration
  - Creates debug reports
  - Analyzes errors
  - Categorizes failure types
```

### Execution Flow

1. **Initialization**: Create CodeSandbox instance (checks Docker availability)
2. **Validation**: Validate language and resource limits
3. **Preparation**: Create temporary directory, write code and files
4. **Container Setup**:
   - Pull Docker image if needed
   - Mount code directory (read-only)
   - Configure security options
   - Set resource limits
5. **Execution**: Run container with timeout
6. **Output Collection**: Capture stdout, stderr, exit code
7. **Cleanup**: Remove container and temporary files
8. **Result Return**: Return ExecutionResult with all metadata

## Security Design

### Defense in Depth

1. **Isolation Layer**: Docker containers isolate code completely
2. **Filesystem**: Read-only root filesystem, limited writable area
3. **Network**: Disabled by default, must be explicitly enabled
4. **Processes**: Limited maximum process count
5. **Resources**: CPU, memory, and swap limits enforced
6. **Capabilities**: All Linux capabilities dropped
7. **Privileges**: No privilege escalation allowed

### Attack Vectors Mitigated

- **Local Escape**: Docker isolation prevents container breakout
- **Network Access**: Network disabled by default
- **File System Access**: Read-only filesystem, no host access
- **Resource Exhaustion**: CPU, memory, process, and timeout limits
- **Privilege Escalation**: Capabilities dropped, no-new-privileges set
- **Information Leakage**: No host filesystem visible

### Security Best Practices

```python
# SAFE: Network disabled, read-only filesystem
result = sandbox.execute(code, "python")

# WARNING: Network enabled, potential for network access
result = sandbox.execute(code, "python", network_enabled=True)

# WARNING: Writable filesystem, code could write to sandbox
result = sandbox.execute(code, "python", read_only=False)

# SAFE: Strict resource limits
limits = ResourceLimits(
    memory_limit="256m",
    timeout_seconds=10,
    pids_limit=25
)
result = sandbox.execute(code, "python", limits=limits)
```

## Resource Limits

### Default Limits

```python
ResourceLimits()
# memory_limit: "512m"
# timeout_seconds: 30
# cpu_quota: 100000 (1.0 CPU)
# cpu_shares: 1024
# pids_limit: 100
```

### Memory Sizing Guidelines

- **Small scripts**: 128m - 256m
- **Data processing**: 256m - 512m
- **Complex operations**: 512m - 1g
- **Maximum**: 2g (system dependent)

### Timeout Guidelines

- **Quick operations**: 5-10 seconds
- **Normal operations**: 15-30 seconds
- **Long operations**: Max 30 seconds

### CPU Allocation

- **cpu_quota = 50000** -> 0.5 CPU
- **cpu_quota = 100000** -> 1.0 CPU
- **cpu_quota = 200000** -> 2.0 CPU

## Testing

### Run Unit Tests

```bash
# Run all tests
pytest tests/test_code_sandbox.py -v

# Run specific test class
pytest tests/test_code_sandbox.py::TestCodeSandbox -v

# Run with coverage
pytest tests/test_code_sandbox.py --cov=autonomous.code_sandbox
```

### Test Coverage

- **29 unit tests** covering:
  - Resource limits validation
  - Execution results
  - Language support
  - Security features
  - Error handling
  - AutoDebugger integration
  - Execution history
  - File handling

### Test Classes

1. **TestResourceLimits**: Resource configuration and validation
2. **TestExecutionResult**: Result object structure
3. **TestCodeSandbox**: Sandbox initialization and execution
4. **TestAutoDebuggerIntegration**: Debugging integration
5. **TestSandboxSecurity**: Security feature validation
6. **TestExecutionHistory**: History tracking
7. **TestLanguageSupport**: Multi-language support
8. **TestResourceConstraints**: Resource limit enforcement
9. **TestFileHandling**: File operations
10. **TestIntegration**: Integration tests (requires Docker)

## Error Handling

### Common Errors

```python
# Unsupported language
result = sandbox.execute(code, "unknown_lang")
# result.success = False
# result.error_message = "Unsupported language: unknown_lang..."

# Timeout
limits = ResourceLimits(timeout_seconds=1)
result = sandbox.execute("import time; time.sleep(10)", "python", limits=limits)
# result.timeout = True
# result.exit_code = 124

# Execution failure
result = sandbox.execute("raise ValueError('test')", "python")
# result.success = False
# result.exit_code = 1
# result.stderr contains traceback
```

### Error Analysis

```python
analysis = AutoDebuggerIntegration.analyze_error(result)

# error_type can be:
# - "timeout": Execution exceeded time limit
# - "execution_failure": Non-zero exit code
# - "python_exception": Python raised exception
# - "sandbox_error": Docker/sandbox error
# - "unknown": Unknown error
```

## Performance

### Execution Overhead

- **Container creation**: 100-200ms
- **Image pull (first time)**: 1-5 seconds per image
- **Code execution**: Minimal overhead
- **Cleanup**: 50-100ms

### Optimization Tips

1. **Reuse sandbox instance** (avoid repeated initialization)
2. **Pre-pull Docker images** (use Docker daemon, not container)
3. **Set appropriate timeouts** (don't use max 30s for quick scripts)
4. **Use strict resource limits** (reduces container overhead)
5. **Monitor execution history** (helps identify patterns)

## Troubleshooting

### Docker Not Found

```
Error: Docker not found. Please install Docker
```

**Solution**: Install Docker from https://docs.docker.com/get-docker/

### Docker Daemon Not Running

```
Error: Cannot connect to Docker daemon
```

**Solution**: Start Docker daemon:
- **Linux**: `sudo systemctl start docker`
- **macOS**: Start Docker Desktop
- **Windows**: Start Docker Desktop

### Image Pull Timeout

```
Error: Timeout pulling Docker image
```

**Solution**:
- Check internet connection
- Manually pull image: `docker pull python:3.11-slim`
- Increase pull timeout

### Out of Memory

```
Cannot allocate memory
```

**Solution**:
- Reduce memory_limit
- Close other applications
- Check system resources

### Timeout Too Strict

```
Code executes successfully outside sandbox but times out inside
```

**Solution**:
- Increase timeout: `ResourceLimits(timeout_seconds=20)`
- Profile code to find bottlenecks
- Optimize code execution

## Integration Examples

### With Auto Debugger

```python
from autonomous.code_sandbox import CodeSandbox, AutoDebuggerIntegration

sandbox = CodeSandbox()
result = sandbox.execute(code, "python")

# Create debug report for AutoDebugger
debug_report = AutoDebuggerIntegration.create_debug_report(result)
# Send to debugger: debugger.analyze(debug_report)

# Analyze errors
if not result.success:
    analysis = AutoDebuggerIntegration.analyze_error(result)
    # Use analysis for debugging: debugger.fix(analysis)
```

### With Code Review System

```python
# Review code before execution
if security_scanner.is_safe(code):
    result = sandbox.execute(code, "python")
    if result.success:
        # Code executed successfully
        history.record(result)
```

### With Learning System

```python
# Execute and learn from results
result = sandbox.execute(code, "python")

if result.success:
    learning_system.record_success(code, result.stdout)
else:
    learning_system.record_failure(code, result.stderr)

# Improve based on execution patterns
improvements = learning_system.analyze_patterns(sandbox.get_execution_history())
```

## Limitations

1. **Maximum 30-second timeout**: Configurable up to 30s, not beyond
2. **Docker dependency**: Requires Docker installed and running
3. **Container overhead**: Each execution creates a new container (~100-200ms)
4. **Language support**: Limited to pre-built images (easily extended)
5. **No interactive I/O**: Cannot read from stdin during execution
6. **Windows WSL limitation**: Network isolation may not work on some WSL setups

## Future Enhancements

1. **Container pooling**: Reuse containers for multiple executions
2. **Custom base images**: Support user-provided Docker images
3. **Streaming output**: Real-time output capture during execution
4. **Multi-stage execution**: Execute multiple code blocks sequentially
5. **Performance profiling**: Built-in CPU/memory profiling
6. **Cache management**: Cache frequently used images
7. **Distributed execution**: Execute across multiple machines
8. **GPU support**: Optional GPU resource allocation

## Contributing

To add a new language:

1. **Add language config** to `LANGUAGE_CONFIGS`
2. **Choose Docker image** (search DockerHub)
3. **Test execution** with sample code
4. **Add unit tests** for the language
5. **Update documentation**

Example:
```python
'java': {
    'image': 'openjdk:17-alpine',
    'extension': '.java',
    'command': lambda f: ['sh', '-c', f'javac {f} && java Code'],
    'runtime_name': 'Java 17',
    'description': 'Java 17 compiler'
}
```

## License

Part of the AI Self-Improvement System (Priority 1.3 implementation)

## References

- Docker Documentation: https://docs.docker.com/
- Docker Python SDK: https://docker-py.readthedocs.io/
- Container Security: https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html
- Code Execution Isolation: https://en.wikipedia.org/wiki/Sandbox_(computer_security)
