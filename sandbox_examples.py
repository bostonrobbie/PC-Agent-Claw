"""
Real Code Execution Sandbox - Usage Examples
Demonstrates practical usage of Priority 1.3 implementation

Run with: python sandbox_examples.py
"""

from autonomous.code_sandbox import (
    CodeSandbox,
    ResourceLimits,
    AutoDebuggerIntegration
)
import json


def example_1_simple_execution():
    """Example 1: Simple code execution"""
    print("\n" + "="*70)
    print("EXAMPLE 1: Simple Code Execution")
    print("="*70)

    sandbox = CodeSandbox()

    # Python execution
    python_code = """
import sys
print("Python Sandbox Example")
print(f"Python version: {sys.version_info.major}.{sys.version_info.minor}")

# Calculate fibonacci
def fib(n):
    if n <= 1:
        return n
    return fib(n-1) + fib(n-2)

result = fib(10)
print(f"Fibonacci(10) = {result}")
"""

    result = sandbox.execute(python_code, "python")
    print(f"\nResult:")
    print(f"  Success: {result.success}")
    print(f"  Exit Code: {result.exit_code}")
    print(f"  Time: {result.execution_time:.3f}s")
    print(f"  Output:\n{result.stdout}")


def example_2_javascript_execution():
    """Example 2: JavaScript execution"""
    print("\n" + "="*70)
    print("EXAMPLE 2: JavaScript Execution")
    print("="*70)

    sandbox = CodeSandbox()

    js_code = """
console.log("JavaScript Sandbox Example");
console.log(`Node.js version: ${process.version}`);

// Calculate factorial
function factorial(n) {
    if (n <= 1) return 1;
    return n * factorial(n - 1);
}

const result = factorial(10);
console.log(`Factorial(10) = ${result}`);

// JSON processing
const data = { name: "Sandbox", version: "1.3" };
console.log(JSON.stringify(data));
"""

    result = sandbox.execute(js_code, "javascript")
    print(f"\nResult:")
    print(f"  Success: {result.success}")
    print(f"  Exit Code: {result.exit_code}")
    print(f"  Time: {result.execution_time:.3f}s")
    print(f"  Output:\n{result.stdout}")


def example_3_resource_limits():
    """Example 3: Resource limit enforcement"""
    print("\n" + "="*70)
    print("EXAMPLE 3: Resource Limit Enforcement")
    print("="*70)

    sandbox = CodeSandbox()

    # Tight limits
    limits = ResourceLimits(
        memory_limit="256m",
        timeout_seconds=5,
        pids_limit=50
    )

    code = """
import time
print("Starting computation with strict limits...")
print(f"Memory limit: 256MB, Timeout: 5s, Max processes: 50")

# CPU-bound operation
result = sum(i * i for i in range(1000000))
print(f"Sum of squares: {result}")

print("Computation completed successfully!")
"""

    result = sandbox.execute(code, "python", limits=limits)
    print(f"\nResult:")
    print(f"  Success: {result.success}")
    print(f"  Exit Code: {result.exit_code}")
    print(f"  Timeout: {result.timeout}")
    print(f"  Time: {result.execution_time:.3f}s")
    print(f"  Output:\n{result.stdout}")


def example_4_file_operations():
    """Example 4: File operations in sandbox"""
    print("\n" + "="*70)
    print("EXAMPLE 4: File Operations in Sandbox")
    print("="*70)

    sandbox = CodeSandbox()

    # Create files for sandbox
    files = {
        "config.json": json.dumps({"name": "Sandbox", "version": "1.3"}),
        "helper.py": """
def process_config(config):
    return {
        "status": "processed",
        "original": config,
        "name": config.get("name", "unknown").upper()
    }
"""
    }

    code = """
import sys
import json

sys.path.insert(0, '/sandbox')
from helper import process_config

# Read config file
with open('/sandbox/config.json') as f:
    config = json.load(f)

# Process using helper
result = process_config(config)

# Output result
print("Original config:", config)
print("Processed result:", result)
print("JSON output:", json.dumps(result, indent=2))
"""

    result = sandbox.execute(code, "python", files=files)
    print(f"\nResult:")
    print(f"  Success: {result.success}")
    print(f"  Exit Code: {result.exit_code}")
    print(f"  Time: {result.execution_time:.3f}s")
    print(f"  Output:\n{result.stdout}")


def example_5_error_handling():
    """Example 5: Error handling and debugging"""
    print("\n" + "="*70)
    print("EXAMPLE 5: Error Handling and Debugging")
    print("="*70)

    sandbox = CodeSandbox()

    # Code with intentional error
    error_code = """
print("Starting operation...")

def divide(a, b):
    return a / b

try:
    result = divide(10, 2)
    print(f"10 / 2 = {result}")

    # This will cause an error
    result = divide(10, 0)
    print(f"10 / 0 = {result}")
except ZeroDivisionError as e:
    print(f"Error caught: {e}")
    raise ValueError("Invalid division!")
"""

    result = sandbox.execute(error_code, "python")
    print(f"\nExecution Result:")
    print(f"  Success: {result.success}")
    print(f"  Exit Code: {result.exit_code}")
    print(f"  Output:\n{result.stdout}")
    print(f"  Errors:\n{result.stderr}")

    # Generate debug report
    debug_report = AutoDebuggerIntegration.create_debug_report(result)
    print(f"\nDebug Report:")
    print(f"  Status: {debug_report['status']}")
    print(f"  Exit Code: {debug_report['exit_code']}")
    print(f"  Execution Time: {debug_report['execution_time']:.3f}s")

    # Analyze error
    error_analysis = AutoDebuggerIntegration.analyze_error(result)
    print(f"\nError Analysis:")
    print(f"  Is Error: {error_analysis['is_error']}")
    print(f"  Error Type: {error_analysis['error_type']}")
    if 'exception' in error_analysis:
        print(f"  Exception: {error_analysis['exception']}")


def example_6_timeout_handling():
    """Example 6: Timeout enforcement"""
    print("\n" + "="*70)
    print("EXAMPLE 6: Timeout Enforcement")
    print("="*70)

    sandbox = CodeSandbox()

    # Code that will timeout
    slow_code = """
import time
print("Starting long operation...")
print("This will timeout...")

# Simulate long operation
time.sleep(10)  # Will timeout
print("This won't be printed")
"""

    # Set tight timeout limit
    limits = ResourceLimits(timeout_seconds=3)
    result = sandbox.execute(slow_code, "python", limits=limits)

    print(f"\nExecution Result:")
    print(f"  Success: {result.success}")
    print(f"  Timeout: {result.timeout}")
    print(f"  Exit Code: {result.exit_code}")
    print(f"  Execution Time: {result.execution_time:.3f}s")
    print(f"  Error: {result.error_message}")

    # Analyze timeout
    error_analysis = AutoDebuggerIntegration.analyze_error(result)
    print(f"\nError Analysis:")
    print(f"  Error Type: {error_analysis['error_type']}")
    if 'suggestion' in error_analysis:
        print(f"  Suggestion: {error_analysis['suggestion']}")


def example_7_execution_history():
    """Example 7: Execution history tracking"""
    print("\n" + "="*70)
    print("EXAMPLE 7: Execution History Tracking")
    print("="*70)

    sandbox = CodeSandbox()

    # Execute multiple operations
    operations = [
        ("print('Operation 1')", "python"),
        ("console.log('Operation 2')", "javascript"),
        ("print('Operation 3')", "python"),
    ]

    for code, language in operations:
        sandbox.execute(code, language)

    # Get execution history
    history = sandbox.get_execution_history()
    print(f"\nExecution History ({len(history)} executions):")
    for i, entry in enumerate(history[-3:], 1):
        print(f"  {i}. {entry['language']:12} - Success: {entry['success']:5} - {entry['execution_time']:.3f}s - {entry['timestamp']}")


def example_8_language_support():
    """Example 8: Multi-language support"""
    print("\n" + "="*70)
    print("EXAMPLE 8: Multi-Language Support")
    print("="*70)

    sandbox = CodeSandbox()

    # Show supported languages
    languages = sandbox.list_supported_languages()
    print(f"\nSupported Languages ({len(languages)}):")
    for lang_info in languages:
        print(f"  {lang_info['language']:12} -> {lang_info['runtime']:20} ({lang_info['image']})")

    # Execute in different languages
    print(f"\nMulti-Language Execution:")

    # Python
    py_result = sandbox.execute("print('Hello from Python')", "python")
    print(f"  Python: {py_result.stdout.strip()}")

    # JavaScript
    js_result = sandbox.execute("console.log('Hello from JavaScript')", "javascript")
    print(f"  JavaScript: {js_result.stdout.strip()}")

    # Bash
    bash_result = sandbox.execute("echo 'Hello from Bash'", "bash")
    print(f"  Bash: {bash_result.stdout.strip()}")


def example_9_security_features():
    """Example 9: Security features demonstration"""
    print("\n" + "="*70)
    print("EXAMPLE 9: Security Features")
    print("="*70)

    sandbox = CodeSandbox()

    # Test 1: Network isolation (network_enabled=False by default)
    print("\n1. Network Isolation (disabled by default):")
    network_code = """
import socket
try:
    socket.create_connection(("google.com", 80), timeout=1)
    print("Network access successful!")
except Exception as e:
    print(f"Network access blocked: {type(e).__name__}")
"""
    result = sandbox.execute(network_code, "python")
    print(f"   Result: {result.stdout.strip()}")

    # Test 2: Read-only filesystem
    print("\n2. Read-only Filesystem (enabled by default):")
    write_code = """
try:
    with open('/etc/test.txt', 'w') as f:
        f.write('test')
    print("Write successful!")
except Exception as e:
    print(f"Write failed: {type(e).__name__}")
"""
    result = sandbox.execute(write_code, "python")
    print(f"   Result: {result.stdout.strip()}")

    # Test 3: Process limits
    print("\n3. Process Limits (max 100 by default):")
    process_code = """
import subprocess
print(f"Creating processes with limit...")
try:
    # Normal process
    result = subprocess.run(['echo', 'test'], capture_output=True)
    print(f"Process execution: OK")
except Exception as e:
    print(f"Process execution failed: {e}")
"""
    result = sandbox.execute(process_code, "python")
    print(f"   Result: {result.stdout.strip()}")


def example_10_advanced_workflow():
    """Example 10: Advanced workflow"""
    print("\n" + "="*70)
    print("EXAMPLE 10: Advanced Workflow")
    print("="*70)

    sandbox = CodeSandbox()

    # Complex workflow: Data processing pipeline
    data_code = """
import json
from statistics import mean, stdev

# Sample data
data = {
    "measurements": [10.5, 11.2, 9.8, 10.1, 11.0, 10.3, 10.2],
    "experiment": "temperature_test"
}

# Process data
measurements = data["measurements"]
stats = {
    "count": len(measurements),
    "mean": round(mean(measurements), 2),
    "stdev": round(stdev(measurements), 2),
    "min": min(measurements),
    "max": max(measurements),
}

# Output
result = {
    "experiment": data["experiment"],
    "original_count": len(measurements),
    "statistics": stats,
    "status": "success"
}

print(json.dumps(result, indent=2))
"""

    # Execute with moderate limits
    limits = ResourceLimits(
        memory_limit="512m",
        timeout_seconds=10,
        cpu_quota=100000
    )

    result = sandbox.execute(data_code, "python", limits=limits)
    print(f"\nData Processing Result:")
    print(f"  Success: {result.success}")
    print(f"  Time: {result.execution_time:.3f}s")
    print(f"  Output:\n{result.stdout}")


def main():
    """Run all examples"""
    print("\n" + "="*70)
    print("REAL CODE EXECUTION SANDBOX - USAGE EXAMPLES")
    print("Priority 1.3 Implementation")
    print("="*70)

    try:
        example_1_simple_execution()
        example_2_javascript_execution()
        example_3_resource_limits()
        example_4_file_operations()
        example_5_error_handling()
        example_6_timeout_handling()
        example_7_execution_history()
        example_8_language_support()
        example_9_security_features()
        example_10_advanced_workflow()

        print("\n" + "="*70)
        print("ALL EXAMPLES COMPLETED")
        print("="*70 + "\n")

    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
