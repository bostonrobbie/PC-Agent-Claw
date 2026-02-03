# Self-Improvement & Meta-Learning Engine

A comprehensive autonomous system for analyzing weaknesses, generating experiments, and improving agent capabilities.

## Overview

The Self-Improvement Engine enables the agent to:

- **Profile Capabilities**: Track and measure performance across multiple capability domains
- **Identify Weaknesses**: Automatically detect performance gaps and areas needing improvement
- **Generate Experiments**: Design improvement experiments based on identified weaknesses
- **Test Approaches**: Run experiments and measure results quantitatively
- **Apply Improvements**: Update code with beneficial changes (with approval)
- **Meta-Learn**: Learn patterns about the improvement process itself
- **Self-Assess**: Generate comprehensive performance reports

## Quick Start

```python
from meta.self_improvement import SelfImprovementEngine

# Initialize engine
engine = SelfImprovementEngine(auto_improve=False)

# Register a capability
engine.register_capability(
    name='task_completion',
    capability_type='execution',
    description='Success rate of task completion',
    baseline_performance=0.80,
    target_performance=0.95,
    performance_unit='success_rate'
)

# Measure performance
result = engine.measure_capability('task_completion', 0.85)

# Analyze weaknesses
weaknesses = engine.analyze_weaknesses()

# Generate experiments
experiments = engine.generate_experiments(weakness_id=weaknesses[0]['id'])

# Test approach
test_result = engine.test_approach(
    experiments[0]['id'],
    test_function=your_test_function,
    baseline_value=0.85
)

# Get self-assessment
assessment = engine.get_self_assessment()
```

## Key Features

### 1. Capability Profiling

Track and measure performance across different capability domains:

- **Execution**: Task completion, accuracy, success rates
- **Performance**: Speed, latency, throughput
- **Reliability**: Error recovery, uptime, consistency
- **Efficiency**: Resource usage, optimization
- **Output Quality**: Code quality, result accuracy

```python
# Measure a capability
result = engine.measure_capability(
    capability_name='response_time',
    performance_value=1.8,
    context='production_workload'
)

# Get complete profile
profile = engine.profile_all_capabilities()
```

### 2. Weakness Identification

Automatically identify and prioritize weaknesses:

```python
# Manual identification
weakness_id = engine.identify_weakness(
    weakness_name='slow_queries',
    weakness_type='efficiency',
    description='Database queries taking too long',
    severity='high',  # critical, high, medium, low
    impact_score=0.75
)

# Analyze all weaknesses
weaknesses = engine.analyze_weaknesses(min_impact=0.3)
```

Weaknesses are automatically detected when performance falls below target thresholds.

### 3. Experiment Generation

Generate improvement experiments for identified weaknesses:

```python
experiments = engine.generate_experiments(
    weakness_id=weakness_id,
    num_experiments=3
)

# Each experiment includes:
# - Hypothesis
# - Approach description
# - Test methodology
# - Expected improvement
```

The engine generates different experiment types based on weakness category:
- **Capability gaps**: Optimization, parallelization, training
- **Reliability issues**: Error handling, retry logic
- **Efficiency problems**: Caching, query optimization

### 4. Testing Approaches

Run experiments and measure results:

```python
def test_function():
    # Your test implementation
    return performance_value

result = engine.test_approach(
    experiment_id=exp_id,
    test_function=test_function,
    baseline_value=baseline
)

# Returns:
# - improvement percentage
# - success/failure
# - measurements
```

### 5. Improvement Measurement

Quantitatively measure improvements:

```python
improvement = engine.measure_improvement(
    before_value=0.80,
    after_value=0.92,
    metric_name='task_completion',
    context='post_optimization'
)

# Returns:
# - absolute_change
# - percent_change
# - is_significant (>15% improvement threshold)
# - confidence level
```

### 6. Code Improvement

Apply code changes with approval mechanism:

```python
result = engine.apply_improvement(
    improvement_name='optimize_queries',
    file_path='core/database.py',
    function_name='query_handler',
    new_code=improved_code,
    experiment_id=exp_id,
    require_approval=True
)

# Set auto_improve=True to auto-apply improvements
engine = SelfImprovementEngine(auto_improve=True)
```

### 7. Meta-Learning

Learn patterns about the improvement process itself:

```python
engine.record_meta_learning(
    learning_type='experiment_effectiveness',
    pattern_observed='Caching experiments show 40%+ improvement',
    insight='Prioritize caching optimizations',
    confidence=0.85
)

# Get meta-learnings
learnings = engine.get_meta_learnings(min_confidence=0.7)
```

### 8. Self-Assessment

Generate comprehensive performance reports:

```python
assessment = engine.get_self_assessment()

# Includes:
# - Learning quality score (0-1)
# - Grade (A-D)
# - Capability status
# - Weakness summary
# - Experiment results
# - Applied improvements
# - Meta-learnings count
```

## Database Schema

The engine maintains comprehensive tracking across 8 tables:

1. **capability_profiles**: Registered capabilities and current performance
2. **identified_weaknesses**: Detected weaknesses with severity and impact
3. **improvement_experiments**: Generated experiments with results
4. **code_improvements**: Applied code changes with approval status
5. **performance_metrics**: Time-series performance measurements
6. **meta_learnings**: Patterns about improvement process
7. **improvement_history**: Version history with changes
8. **Database**: `meta_learning.db`

## Integration

### With Reinforcement Learning

```python
# Engine automatically integrates with RL system
# Records outcomes for action selection learning
# Uses RL recommendations for experiment prioritization
```

### With Pattern Detection

```python
# Detects patterns in:
# - Successful experiment types
# - Improvement trends over time
# - Weakness correlations
# - Meta-learning validation
```

## Configuration

```python
engine = SelfImprovementEngine(
    db_path='custom_path.db',        # Default: workspace/meta_learning.db
    auto_improve=False               # Require approval for code changes
)

# Set improvement threshold (default 15%)
engine.improvement_threshold = 0.20  # 20% improvement required
```

## Workflow Example

Complete improvement cycle:

```python
# 1. Profile capabilities
profile = engine.profile_all_capabilities()

# 2. Identify weaknesses
weaknesses = engine.analyze_weaknesses()

# 3. Generate experiments for top weakness
experiments = engine.generate_experiments(weaknesses[0]['id'])

# 4. Test each experiment
for exp in experiments:
    result = engine.test_approach(
        exp['id'],
        test_function=your_test,
        baseline_value=baseline
    )

    if result['success']:
        # 5. Apply improvement
        engine.apply_improvement(
            improvement_name=exp['name'],
            file_path='target/file.py',
            experiment_id=exp['id']
        )

# 6. Record meta-learning
engine.record_meta_learning(
    learning_type='effectiveness',
    pattern_observed='Pattern X works best',
    insight='Use pattern X for similar problems'
)

# 7. Track in history
engine.track_improvement_history(
    version='1.2.0',
    summary='Performance improvements',
    improvements_applied=len(experiments),
    overall_performance_delta=0.25,
    notable_changes=['Optimized X', 'Fixed Y']
)

# 8. Get assessment
assessment = engine.get_self_assessment()
print(f"Learning grade: {assessment['learning_quality']['grade']}")
```

## Best Practices

1. **Regular Measurement**: Measure capabilities frequently to detect degradation
2. **Prioritize Weaknesses**: Focus on high-impact, high-severity weaknesses first
3. **Validate Experiments**: Always use test functions with proper baselines
4. **Record Meta-Learnings**: Document patterns for future reference
5. **Track History**: Maintain version history for rollback capability
6. **Review Improvements**: Keep auto_improve=False until confidence is high
7. **Monitor Trends**: Use assessment reports to track long-term progress

## Testing

Run the comprehensive test suite:

```bash
python test_self_improvement.py
```

Or use the built-in test:

```bash
python meta/self_improvement.py
```

## Performance Metrics

The engine tracks:

- **Learning Quality Score**: Overall improvement effectiveness (0-1)
- **Exceeded Expectations Rate**: Experiments beating expected improvement
- **Weakness Resolution Rate**: Percentage of weaknesses resolved
- **Average Improvement**: Mean improvement across all experiments
- **Grade**: A (>80%), B (>60%), C (>40%), D (≤40%)

## Security

- Code improvements require approval by default
- All changes are tracked with before/after hashes
- Rollback capability for applied improvements
- Audit trail in database

## Future Enhancements

- Automatic experiment scheduling
- Multi-agent improvement coordination
- A/B testing framework integration
- Continuous improvement monitoring
- Predictive weakness detection
- Improvement recommendation engine

## License

Part of the autonomous agent system.
