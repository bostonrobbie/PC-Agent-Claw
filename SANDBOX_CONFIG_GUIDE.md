# Code Sandbox Configuration Guide

## Resource Limit Profiles

### Profile 1: Lightweight (Quick Scripts)
```python
from autonomous.code_sandbox import ResourceLimits

limits = ResourceLimits(
    memory_limit="128m",      # 128MB
    timeout_seconds=5,        # 5 seconds
    cpu_quota=50000,          # 0.5 CPU
    cpu_shares=512,           # Low priority
    pids_limit=25             # Few processes
)

# Use for: Simple calculations, data validation, quick tests
# Typical execution time: < 1 second
# Memory usage: < 50MB
```

### Profile 2: Standard (Typical Tasks)
```python
limits = ResourceLimits(
    memory_limit="512m",      # 512MB (default)
    timeout_seconds=15,       # 15 seconds
    cpu_quota=100000,         # 1.0 CPU (default)
    cpu_shares=1024,          # Standard priority
    pids_limit=100            # Normal processes
)

# Use for: Data processing, API calls, typical workloads
# Typical execution time: 5-10 seconds
# Memory usage: 50-200MB
```

### Profile 3: Heavy (Complex Operations)
```python
limits = ResourceLimits(
    memory_limit="1g",        # 1GB
    timeout_seconds=30,       # Max 30 seconds
    cpu_quota=200000,         # 2.0 CPUs
    cpu_shares=2048,          # High priority
    pids_limit=200            # Many processes
)

# Use for: Machine learning, large dataset processing
# Typical execution time: 15-30 seconds
# Memory usage: 200MB-1GB
```

### Profile 4: Sandbox Safe (Untrusted Code)
```python
limits = ResourceLimits(
    memory_limit="256m",      # Limited memory
    timeout_seconds=10,       # Strict timeout
    cpu_quota=50000,          # Limited CPU
    pids_limit=25             # Few processes
)

# Security features enabled:
# - Network disabled
# - Read-only filesystem
# - All capabilities dropped
# - Process isolation

# Use for: Running untrusted or unknown code
```

## Language Configuration

### Adding a New Language

```python
# 1. Choose a Docker image from DockerHub
# Example: Java 17
image = "openjdk:17-alpine"

# 2. Define the configuration
LANGUAGE_CONFIGS['java'] = {
    'image': 'openjdk:17-alpine',
    'extension': '.java',
    'command': lambda f: ['sh', '-c', f'javac {f} && java Code'],
    'runtime_name': 'Java 17',
    'description': 'Java 17 compiler with standard library'
}

# 3. Test with sample code
code = """
public class Code {
    public static void main(String[] args) {
        System.out.println("Hello from Java!");
    }
}
"""

sandbox.execute(code, "java")
```

### Recommended Docker Images

```python
# Python
'python:3.11-slim'          # Small, minimal Python
'python:3.11-slim-bullseye' # Debian-based Python
'python:3.11-alpine'        # Alpine-based Python

# JavaScript/Node.js
'node:18-slim'              # Slim Node.js 18
'node:18-alpine'            # Alpine Node.js 18
'node:20-alpine'            # Alpine Node.js 20

# Shell/Bash
'ubuntu:22.04'              # Ubuntu with bash
'alpine:latest'             # Alpine with sh
'busybox:latest'            # Minimal busybox

# Ruby
'ruby:3.2-slim'             # Slim Ruby 3.2
'ruby:3.2-alpine'           # Alpine Ruby 3.2

# Go
'golang:1.21-alpine'        # Alpine Go 1.21

# Java
'openjdk:17-alpine'         # Alpine OpenJDK 17
'eclipse-temurin:17'        # Eclipse Temurin JDK 17

# Rust
'rust:latest'               # Official Rust image

# C/C++
'gcc:latest'                # GCC compiler
'clang:latest'              # Clang compiler
```

## Network Configuration

### Network Disabled (Secure, Default)
```python
# No network access to external resources
result = sandbox.execute(code, "python", network_enabled=False)

# Code cannot:
# - Connect to external APIs
# - Access DNS
# - Make HTTP requests
# - Connect to databases outside container

# Example: This will fail
code = """
import urllib.request
urllib.request.urlopen("https://example.com")
"""
```

### Network Enabled (Reduced Security)
```python
# WARNING: Reduces security, only use for trusted code
result = sandbox.execute(code, "python", network_enabled=True)

# Code can:
# - Make HTTP/HTTPS requests
# - Connect to external services
# - Access DNS
# - Download files

# Example: This will succeed
code = """
import urllib.request
response = urllib.request.urlopen("https://example.com")
print(response.status)
"""
```

## Filesystem Configuration

### Read-Only Filesystem (Secure, Default)
```python
# Root filesystem is read-only
result = sandbox.execute(code, "python", read_only=True)

# Code can only:
# - Read system files
# - Write to /tmp
# - Read mounted code directory
# - Modify /tmp files

# Example: Write will fail
code = """
try:
    with open('/etc/test.txt', 'w') as f:
        f.write('test')
    print("Write succeeded")
except Exception as e:
    print(f"Write failed: {type(e).__name__}")
"""
```

### Writable Filesystem (Reduced Security)
```python
# WARNING: Reduces security, only use for trusted code
result = sandbox.execute(code, "python", read_only=False)

# Code can:
# - Modify system files
# - Write anywhere except protected paths
# - Create files permanently

# Use only when necessary for:
# - File system testing
# - Log generation
# - Temporary persistent storage
```

## Performance Tuning

### Optimize for Speed
```python
# Use minimal resources for quick execution
limits = ResourceLimits(
    memory_limit="128m",
    timeout_seconds=5,
    cpu_quota=100000,
    pids_limit=25
)

sandbox = CodeSandbox(default_limits=limits)

# Reuse sandbox instance
for code_snippet in code_snippets:
    result = sandbox.execute(code_snippet, "python")
```

### Optimize for Throughput
```python
# Pre-warm Docker images
images_to_warm = [
    'python:3.11-slim',
    'node:18-alpine',
    'ubuntu:22.04'
]

for image in images_to_warm:
    subprocess.run(['docker', 'pull', image], capture_output=True)

# Use standard limits
sandbox = CodeSandbox()

# Execute multiple in parallel
import concurrent.futures
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    futures = [
        executor.submit(sandbox.execute, code, "python")
        for code in codes
    ]
    results = [f.result() for f in futures]
```

### Optimize for Safety
```python
# Use strict limits
limits = ResourceLimits(
    memory_limit="256m",
    timeout_seconds=10,
    cpu_quota=50000,
    pids_limit=25
)

sandbox = CodeSandbox(default_limits=limits)

# Always use with network disabled (default)
result = sandbox.execute(code, "python")

# Always use with read-only filesystem (default)
result = sandbox.execute(code, "python", read_only=True)
```

## Troubleshooting Configuration

### Issue: Memory Limit Too Strict
```python
# Symptom: MemoryError even for simple code
# Solution: Increase memory limit

# Before
limits = ResourceLimits(memory_limit="128m")

# After
limits = ResourceLimits(memory_limit="512m")
```

### Issue: Timeout Too Strict
```python
# Symptom: Code times out but completes outside sandbox
# Solution: Profile and increase timeout

import time
start = time.time()
# Run code normally
elapsed = time.time() - start

# Set timeout to 2x the normal execution time
limits = ResourceLimits(timeout_seconds=int(elapsed * 2) + 5)
```

### Issue: CPU Quota Too Low
```python
# Symptom: Code runs slower in sandbox than outside
# Solution: Increase CPU quota

# Before
limits = ResourceLimits(cpu_quota=50000)  # 0.5 CPU

# After
limits = ResourceLimits(cpu_quota=100000)  # 1.0 CPU
```

### Issue: Process Limit Exceeded
```python
# Symptom: "Cannot fork: resource temporarily unavailable"
# Solution: Increase process limit

# Before
limits = ResourceLimits(pids_limit=25)

# After
limits = ResourceLimits(pids_limit=100)
```

## Security Hardening

### Maximum Security Configuration
```python
from autonomous.code_sandbox import CodeSandbox, ResourceLimits

# Strict resource limits
limits = ResourceLimits(
    memory_limit="256m",
    timeout_seconds=10,
    cpu_quota=50000,
    cpu_shares=512,
    pids_limit=25
)

# Create sandbox
sandbox = CodeSandbox(default_limits=limits)

# Execute with maximum isolation
result = sandbox.execute(
    code,
    language="python",
    network_enabled=False,     # No network
    read_only=True,            # Read-only filesystem
    files={}                   # No extra files
)

# Verify result
assert result.success
assert result.exit_code == 0
```

### Medium Security Configuration
```python
# Balanced security and functionality
limits = ResourceLimits(
    memory_limit="512m",
    timeout_seconds=15,
    cpu_quota=100000,
    pids_limit=100
)

sandbox = CodeSandbox(default_limits=limits)

result = sandbox.execute(
    code,
    language="python",
    network_enabled=False,     # No network
    read_only=True,            # Read-only filesystem
    files=helper_files         # Allow helper files
)
```

### Custom Security Rules
```python
def is_code_safe(code: str) -> bool:
    """Custom security validation"""
    # Check for dangerous imports
    dangerous = ['os.system', 'subprocess', 'eval', '__import__']
    for item in dangerous:
        if item in code:
            return False

    # Check for suspicious patterns
    if 'open(' in code and 'w' in code:
        return False

    return True

# Use in execution
if is_code_safe(user_code):
    result = sandbox.execute(user_code, "python")
else:
    print("Code failed security check")
```

## Monitoring and Logging

### Monitor Execution
```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

sandbox = CodeSandbox()
result = sandbox.execute(code, "python")

# Get execution history
history = sandbox.get_execution_history()
for entry in history:
    print(f"  {entry['timestamp']}: {entry['language']} - {entry['success']}")
```

### Track Resource Usage
```python
result = sandbox.execute(code, "python")

# Check resource usage
if result.resource_usage:
    print(f"Memory: {result.memory_used}")
    print(f"CPU: {result.cpu_percent}%")

# Get container stats
stats = sandbox.get_resource_usage(result.container_id)
if stats:
    print(f"Memory usage: {stats.get('memory_usage')}")
    print(f"CPU percent: {stats.get('cpu_percent')}")
```

## Integration Examples

### With FastAPI
```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from autonomous.code_sandbox import CodeSandbox, ResourceLimits

app = FastAPI()
sandbox = CodeSandbox()

class CodeRequest(BaseModel):
    code: str
    language: str = "python"

@app.post("/execute")
async def execute_code(request: CodeRequest):
    limits = ResourceLimits(
        memory_limit="256m",
        timeout_seconds=10
    )

    result = sandbox.execute(
        request.code,
        request.language,
        limits=limits
    )

    return {
        "success": result.success,
        "output": result.stdout,
        "error": result.stderr,
        "time": result.execution_time
    }
```

### With Flask
```python
from flask import Flask, request, jsonify
from autonomous.code_sandbox import CodeSandbox, ResourceLimits

app = Flask(__name__)
sandbox = CodeSandbox()

@app.route('/execute', methods=['POST'])
def execute():
    data = request.json
    code = data.get('code')
    language = data.get('language', 'python')

    result = sandbox.execute(code, language)

    return jsonify({
        "success": result.success,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.exit_code,
        "time": result.execution_time
    })
```

## Cheat Sheet

```python
# Quick reference

# Basic execution
sandbox = CodeSandbox()
result = sandbox.execute("print('Hello')", "python")

# With custom limits
limits = ResourceLimits(memory_limit="256m", timeout_seconds=10)
result = sandbox.execute(code, "python", limits=limits)

# With files
result = sandbox.execute(code, "python", files={"helper.py": helper_code})

# Insecure (network enabled)
result = sandbox.execute(code, "python", network_enabled=True)

# Writable filesystem
result = sandbox.execute(code, "python", read_only=False)

# Error analysis
from autonomous.code_sandbox import AutoDebuggerIntegration
analysis = AutoDebuggerIntegration.analyze_error(result)

# Execution history
history = sandbox.get_execution_history(limit=10)
```

## Best Practices

1. **Always use defaults for security**: Network disabled, read-only filesystem
2. **Set appropriate timeouts**: 5-10s for quick tasks, 15-30s for heavy tasks
3. **Reuse sandbox instances**: Create once, use many times
4. **Monitor execution history**: Detect patterns and anomalies
5. **Pre-warm Docker images**: Pull images before execution
6. **Validate input code**: Use custom security checks
7. **Handle errors gracefully**: Check result.success and result.error_message
8. **Log executions**: Use execution history for debugging
9. **Test resource limits**: Ensure limits work for your use case
10. **Keep Docker updated**: Regular updates for security patches
