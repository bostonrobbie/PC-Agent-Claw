# Capability Synergy Engine - Quick Start Guide

**Fast track to using intelligence chains**

---

## Installation

Already installed! Files are at:
- `core/capability_synergy.py` - Main engine
- `tests/test_capability_synergy.py` - Tests
- `demo_capability_synergy.py` - Demo
- `capability_synergy.db` - Database

---

## 5-Minute Quick Start

### 1. Initialize the Engine

```python
from core.capability_synergy import CapabilitySynergyEngine

engine = CapabilitySynergyEngine()
```

### 2. List Available Chains

```python
# Check predefined chains
for chain_id in range(1, 6):
    status = engine.get_chain_status(chain_id)
    print(f"{chain_id}. {status['name']}")
    print(f"   {status['description']}")
```

### 3. Execute Your First Chain

```python
# Run the Code Analysis Chain
result = engine.execute_chain(
    chain_id=1,
    initial_input={
        'search_query': 'authentication',
        'code_to_scan': 'def login(): pass',
        'code_to_review': 'def login(): pass',
        'code_to_check': 'def login(): pass'
    }
)

print(f"Status: {result['status']}")
print(f"Insights: {result['insights']}")
```

### 4. View Insights

```python
# Get latest insights
insights = engine.get_synergy_insights(limit=5)

for insight in insights:
    print(f"- {insight['insight_text']}")
```

### 5. Discover Patterns

```python
# See what patterns emerged
patterns = engine.discover_emergent_patterns()

for pattern in patterns:
    print(f"{pattern['pattern_name']}: {pattern['occurrences']} uses")
```

---

## The 5 Pre-built Chains

### Chain 1: Code Analysis Chain
**What it does**: Complete code analysis pipeline
**Use when**: You want comprehensive code insights
```python
result = engine.execute_chain(1, {
    'search_query': 'your search',
    'code_to_scan': code,
    'code_to_review': code,
    'code_to_check': code
})
```

### Chain 2: Learning Chain
**What it does**: Applies learned patterns to new code
**Use when**: You want to apply team standards
```python
result = engine.execute_chain(2, {
    'code_to_improve': code,
    'learned_patterns': patterns
})
```

### Chain 3: Performance Chain
**What it does**: System health monitoring
**Use when**: You want performance insights
```python
result = engine.execute_chain(3, {})
```

### Chain 4: Security Deep Scan
**What it does**: Security analysis with learning
**Use when**: You need security audit
```python
result = engine.execute_chain(4, {
    'code_to_scan': code,
    'security_scan': {}
})
```

### Chain 5: Continuous Improvement
**What it does**: Codebase-wide improvements
**Use when**: You want systematic refactoring
```python
result = engine.execute_chain(5, {
    'code_to_review': code,
    'pattern': pattern_to_apply
})
```

---

## Create Your Own Chain

### Simple 2-Step Chain

```python
chain_id = engine.define_chain(
    name="my_chain",
    description="What my chain does",
    steps=[
        # Step 1
        {
            'capability_name': 'Search',
            'capability_module': 'search.semantic_search',
            'capability_class': 'SemanticCodeSearch',
            'method_name': 'search',
            'input_mapping': {'query': 'search_query'},
            'output_key': 'results'
        },
        # Step 2
        {
            'capability_name': 'Security',
            'capability_module': 'security.security_monitor',
            'capability_class': 'SecurityMonitor',
            'method_name': 'scan_code',
            'input_mapping': {'code': 'code'},
            'output_key': 'security'
        }
    ]
)

# Execute it
result = engine.execute_chain(chain_id, {
    'search_query': 'auth',
    'code': 'def auth(): pass'
})
```

---

## Common Patterns

### Pattern 1: Search → Analyze
Find code, then analyze it
```python
steps=[
    {'capability': 'Search', 'method': 'search', ...},
    {'capability': 'Analyzer', 'method': 'analyze', ...}
]
```

### Pattern 2: Scan → Learn
Find issues, then learn from them
```python
steps=[
    {'capability': 'Scanner', 'method': 'scan', ...},
    {'capability': 'Learner', 'method': 'record', ...}
]
```

### Pattern 3: Learn → Apply → Measure
Learn patterns, apply them, measure impact
```python
steps=[
    {'capability': 'Learner', 'method': 'get_patterns', ...},
    {'capability': 'Applier', 'method': 'apply', ...},
    {'capability': 'Metrics', 'method': 'measure', ...}
]
```

---

## Schedule Automatic Execution

### Every Hour
```python
engine.schedule_chain(
    chain_id=3,  # Performance monitoring
    trigger='time_interval',
    config={'interval_seconds': 3600}
)
```

### Every 2 Hours
```python
engine.schedule_chain(
    chain_id=4,  # Security scan
    trigger='time_interval',
    config={'interval_seconds': 7200}
)
```

---

## Working with Results

### Check Status
```python
result = engine.execute_chain(chain_id, input)

if result['status'] == 'completed':
    print("Success!")
elif result['status'] == 'partial':
    print("Partial success")
else:
    print(f"Failed: {result['error']}")
```

### Access Step Results
```python
for step in result['step_results']:
    print(f"Step {step['step']}: {step['capability']}")
    print(f"  Status: {step['status']}")
    if 'result_summary' in step:
        print(f"  Result: {step['result_summary']}")
```

### Read Context
```python
# Context contains all step outputs
context = result['context']

# Access specific step outputs
search_results = context.get('search_results')
security_results = context.get('security_results')
```

---

## Monitoring & Metrics

### Check Chain Status
```python
status = engine.get_chain_status(chain_id)

print(f"Name: {status['name']}")
print(f"Executions: {status['executions']}")
print(f"Average Duration: {status['avg_duration_seconds']}s")
print(f"Insights: {status['insights_count']}")
```

### View All Insights
```python
insights = engine.get_synergy_insights(limit=20)

for insight in insights:
    print(f"[{insight['chain_name']}] {insight['insight_text']}")
```

### Discover Patterns
```python
patterns = engine.discover_emergent_patterns()

for pattern in patterns:
    print(f"\n{pattern['pattern_name']}")
    print(f"  Capabilities: {', '.join(pattern['capabilities_involved'])}")
    print(f"  Impact: {pattern['impact_score']:.2f}")
    print(f"  Used: {pattern['occurrences']} times")
```

---

## Troubleshooting

### Chain Not Executing?
1. Check capability module/class names are correct
2. Verify input_mapping keys exist in initial_input
3. Ensure capabilities are installed/accessible

### Missing Context Values?
1. Check output_key matches what you're looking for
2. Verify previous step completed successfully
3. Review step_results for errors

### No Insights?
1. Execute chains multiple times
2. Check that steps return insight-triggering data
3. Review result structure

### Slow Execution?
1. Check step_results for slow steps
2. Profile individual capability methods
3. Consider caching expensive operations

---

## Code Examples

### Example 1: Security Audit
```python
from core.capability_synergy import CapabilitySynergyEngine

engine = CapabilitySynergyEngine()

# Run security deep scan
result = engine.execute_chain(4, {
    'code_to_scan': open('app.py').read()
})

# Check results
if result['status'] == 'completed':
    insights = result['insights']
    print(f"Found {len(insights)} security insights")
    for insight in insights:
        print(f"- {insight}")
```

### Example 2: Performance Monitoring
```python
engine = CapabilitySynergyEngine()

# Schedule performance monitoring
engine.schedule_chain(
    chain_id=3,
    trigger='time_interval',
    config={'interval_seconds': 3600}
)

# Check current performance
result = engine.execute_chain(3, {})
print(f"System health: {result['context'].get('resource_metrics')}")
```

### Example 3: Learning from Reviews
```python
engine = CapabilitySynergyEngine()

# Apply learned patterns to new code
result = engine.execute_chain(2, {
    'code_to_improve': new_code,
    'patterns': {'prefer_async': True}
})

improvements = result['context'].get('improvements', [])
print(f"Applied {len(improvements)} improvements")
```

---

## Testing

### Run All Tests
```bash
python tests/test_capability_synergy.py
```

### Run Demo
```bash
python demo_capability_synergy.py
```

### Quick Test
```python
from core.capability_synergy import CapabilitySynergyEngine

engine = CapabilitySynergyEngine()
status = engine.get_chain_status(1)
print(f"Engine working! Found chain: {status['name']}")
```

---

## Best Practices

### 1. Start Simple
Begin with predefined chains before creating custom ones

### 2. Map Inputs Carefully
Ensure each step's input_mapping matches available context keys

### 3. Handle Failures Gracefully
Check result['status'] and handle partial completions

### 4. Monitor Performance
Regularly review chain metrics to identify slow spots

### 5. Act on Insights
Use generated insights to improve code and processes

### 6. Iterate and Refine
Adjust chains based on results and discovered patterns

---

## Common Use Cases

### Pre-Commit Check
```python
result = engine.execute_chain(1, {
    'search_query': 'similar code',
    'code_to_scan': changes,
    'code_to_review': changes,
    'code_to_check': changes
})
# Check insights before committing
```

### Security Audit
```python
result = engine.execute_chain(4, {
    'code_to_scan': codebase
})
# Review security findings
```

### Performance Tuning
```python
result = engine.execute_chain(3, {})
optimizations = result['context'].get('optimizations', [])
# Apply suggested optimizations
```

### Code Quality Gate
```python
result = engine.execute_chain(5, {
    'code_to_review': pr_changes
})
# Ensure quality standards met
```

---

## Quick Reference

### Initialize
```python
from core.capability_synergy import CapabilitySynergyEngine
engine = CapabilitySynergyEngine()
```

### Execute
```python
result = engine.execute_chain(chain_id, initial_input)
```

### Define
```python
chain_id = engine.define_chain(name, description, steps)
```

### Schedule
```python
engine.schedule_chain(chain_id, trigger, config)
```

### Insights
```python
insights = engine.get_synergy_insights(limit)
```

### Patterns
```python
patterns = engine.discover_emergent_patterns()
```

### Status
```python
status = engine.get_chain_status(chain_id)
```

---

## Getting Help

1. **Read the docs**: `CAPABILITY_SYNERGY_README.md`
2. **Check examples**: `demo_capability_synergy.py`
3. **Review tests**: `tests/test_capability_synergy.py`
4. **Examine chains**: Look at predefined chain definitions

---

## Next Steps

1. ✅ Run the demo
2. ✅ Execute a predefined chain
3. ✅ Create a custom chain
4. ✅ Schedule automatic execution
5. ✅ Review insights and patterns

---

**You're ready to use the Capability Synergy Engine!**

For detailed documentation, see `CAPABILITY_SYNERGY_README.md`
For implementation details, see `CAPABILITY_SYNERGY_IMPLEMENTATION.md`
