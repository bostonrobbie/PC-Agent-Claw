# Real-World Testing System - Quick Start Guide

Get started with autonomous Intelligence Hub testing in 5 minutes.

## What Is This?

The Real-World Testing System runs the Intelligence Hub autonomously on real codebases, measuring performance and finding issues automatically.

**Think of it as:** Your AI running itself, measuring how well it performs, and telling you exactly what to improve.

## Quick Start

### 1. Run the Demo (Easiest)

```bash
python examples/demo_realworld_tester.py
```

This runs a 5-minute test with live monitoring and generates a full report.

### 2. Basic Python Usage

```python
from autonomous.realworld_tester import RealWorldTester

# Create tester
tester = RealWorldTester()

# Run 5-minute test
session_id = tester.start_test_session(
    project_path=".",  # Current directory
    duration_minutes=5
)

# Test runs automatically...
# When done, get the report:
import time
time.sleep(5 * 60 + 10)  # Wait for completion

report = tester.generate_improvement_report(session_id)
print(report)
```

### 3. With Monitoring

```python
from autonomous.realworld_tester import RealWorldTester
import time

tester = RealWorldTester()
session_id = tester.start_test_session(".", duration_minutes=5)

# Monitor progress
for i in range(10):  # 10 updates over 5 minutes
    time.sleep(30)
    status = tester.monitor_activities()
    print(f"Activities: {status['total_activities']}, "
          f"Errors: {status['total_errors']}")

# Get final report
final_stats = tester.stop_session(session_id)
report = tester.generate_improvement_report(session_id)
print(report)
```

## What You'll Get

After the test completes, you'll receive:

### 1. Real-Time Console Output
```
[Test-test_20260203_121500] Workspace analysis: 245ms, 7 insights
[Test-test_20260203_121500] Code assistance: 189ms, 3 capabilities
[Test-test_20260203_121500] Security scan: 2345ms, 2 vulnerabilities
[Test-test_20260203_121500] Code indexing: 567ms, 15 files
```

### 2. Performance Metrics
- Response times for each capability
- CPU and memory usage
- Success/failure rates
- Cache hit rates

### 3. Issues Found
- Security vulnerabilities
- Performance problems
- Reliability issues
- UX quality problems

### 4. Improvement Report
```
========================= ACTIONABLE IMPROVEMENTS ==============================

1. [HIGH] Fix error handling in security_scanner
   Category: reliability
   Why: Success rate is only 60.0%
   Impact: Could improve success rate to 95%+

2. [MEDIUM] Optimize security_scanner - response time is too slow
   Category: performance
   Why: Average response time is 2345ms
   Impact: Could improve response time by 1172ms
```

## Understanding the Results

### Overall Score

- **90-100**: Excellent - production ready
- **70-89**: Good - minor tweaks needed
- **50-69**: Acceptable - needs improvement
- **0-49**: Poor - major issues

### What Worked Well

Capabilities with:
- 90%+ success rate
- Sub-5s response times
- Low resource usage

### What Worked Poorly

Capabilities with:
- <70% success rate
- >10s response times
- High error rates

## Common Use Cases

### 1. Pre-Release Validation

Test before deploying to production:
```python
tester = RealWorldTester()
session = tester.start_test_session(".", duration_minutes=10)
# ... wait for completion ...
stats = tester.stop_session(session)
if stats['overall_score'] < 80:
    print("FAIL: Score too low for production")
    exit(1)
```

### 2. Performance Regression Detection

Compare current vs. previous test:
```python
# Run test
session_id = tester.start_test_session(".", 5)
# ... wait ...
analysis = tester.analyze_session_results(session_id)

# Compare to baseline
baseline_avg_time = 250  # ms
current_avg_time = analysis['summary']['avg_response_time']

if current_avg_time > baseline_avg_time * 1.2:  # 20% slower
    print("WARNING: Performance regression detected")
```

### 3. Stress Testing

Run extended test to find stability issues:
```python
# 2-hour endurance test
session_id = tester.start_test_session(".", duration_minutes=120)
```

### 4. Capability Benchmarking

Test specific capabilities:
```python
session_id = tester.start_test_session(".", 5)
# ... wait ...
analysis = tester.analyze_session_results(session_id)

for cap in analysis['activities_by_capability']:
    print(f"{cap['capability']}: {cap['avg_response']:.0f}ms avg")
```

## Database Queries

All data is stored in SQLite. Explore it:

```bash
sqlite3 realworld_testing.db
```

Useful queries:

```sql
-- All test sessions
SELECT session_id, status, overall_score
FROM test_sessions
ORDER BY start_time DESC;

-- Top slow capabilities
SELECT capability, AVG(response_time_ms) as avg_ms
FROM activities
GROUP BY capability
ORDER BY avg_ms DESC
LIMIT 10;

-- Critical issues
SELECT capability, description, suggested_fix
FROM issues
WHERE severity = 'critical'
ORDER BY timestamp DESC;
```

## Tips & Tricks

### 1. Start Small

Your first test? Use 1-2 minutes:
```python
session_id = tester.start_test_session(".", duration_minutes=2)
```

### 2. Stop Early

Press Ctrl+C to stop a running test:
```python
try:
    session_id = tester.start_test_session(".", 60)
    time.sleep(60 * 60)  # 60 minutes
except KeyboardInterrupt:
    tester.stop_session(session_id)
```

### 3. Custom Database

Keep tests separate:
```python
tester = RealWorldTester(db_path="my_test.db")
```

### 4. Monitor Resources

Check system impact:
```python
metrics = tester.collect_metrics()
print(f"CPU: {metrics['system_resources']['cpu_percent']}%")
print(f"Memory: {metrics['system_resources']['memory_percent']}%")
```

## What Happens During a Test?

The system continuously:

1. **Analyzes workspace** - Scans code structure and patterns
2. **Performs security scans** - Checks for vulnerabilities
3. **Indexes code** - Builds semantic search index
4. **Assists with code** - Simulates coding help requests
5. **Recovers from errors** - Tests error handling
6. **Monitors resources** - Tracks CPU/memory

All while collecting detailed metrics on:
- Response times
- Success rates
- Resource usage
- Issues encountered

## Troubleshooting

**Problem**: "Intelligence Hub dependencies not found"
**Solution**: Install all hub components first

**Problem**: Test runs but no activities logged
**Solution**: Check that Intelligence Hub started successfully

**Problem**: Very high CPU usage
**Solution**: Reduce test duration or adjust resource limits:
```python
tester.resource_limits['cpu_percent_max'] = 70.0
```

**Problem**: Database locked errors
**Solution**: Close any SQLite browsers viewing the database

## Next Steps

1. ✅ Run the demo (`examples/demo_realworld_tester.py`)
2. ✅ Review the generated report
3. ✅ Fix top 3 issues identified
4. ✅ Run another test to verify improvements
5. ✅ Set up regular automated testing

## More Information

- Full documentation: `docs/REALWORLD_TESTING_SYSTEM.md`
- Test suite: `tests/test_realworld.py`
- Source code: `autonomous/realworld_tester.py`

---

**You now have autonomous testing of your AI system. Use it to continuously improve!**
