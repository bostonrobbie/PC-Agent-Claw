# Relationship Memory - Quick Start Guide

## Get Started in 5 Minutes

The Relationship Memory System learns how to help YOU better over time, based on Brian Roemmele's Love Equation: "Intelligence fundamentally gives love through better help."

### Installation

The system is already included in your Intelligence Hub. No additional installation needed!

```bash
# Verify it's available
python -c "from core.relationship_memory import RelationshipMemory; print('Ready!')"
```

### Basic Usage (3 Steps)

#### 1. Initialize Your Memory

```python
from core.relationship_memory import RelationshipMemory

# Create your personal memory (one per user)
rm = RelationshipMemory(
    db_path="my_memory.db",
    user_id="your_name"
)
```

#### 2. Record Your First Interaction

```python
# After any interaction (question, code help, debugging, etc.)
rm.record_interaction(
    interaction_type="question",
    context={
        "task_type": "learning",
        "task_completed": True,
        "explained_thoroughly": True
    },
    user_input="How do I use async/await?",
    system_response="Here's how async/await works...",
    user_feedback="Thanks! Very clear.",
    response_time=2.5
)
```

#### 3. Use What It Learned

```python
# Get personalized profile
profile = rm.get_user_profile()
print(f"Total interactions: {profile['total_interactions']}")
print(f"Relationship strength: {profile['relationship_strength']:.1%}")

# Get predictions about what you might need
predictions = rm.predict_user_needs({"task_type": "coding"})
for pred in predictions:
    print(f"  - {pred}")

# Check how well the system is helping you (Love Equation score)
love_score = rm.get_love_alignment_score()
print(f"Love alignment: {love_score:.1%}")
```

## Quick Examples

### Example 1: Learning Your Coding Style

```python
# Record code interactions with style context
rm.record_interaction(
    interaction_type="code_request",
    context={
        "task_completed": True,
        "coding_style": {
            "indentation": "4_spaces",
            "naming": "snake_case",
            "docstrings": "google_style"
        },
        "library_used": "pytest"
    },
    user_input="Create a test function",
    system_response="Here's a pytest function...",
    user_feedback="Perfect style!"
)

# System remembers and applies your style next time
profile = rm.get_user_profile()
print(profile['learned_preferences'])
```

### Example 2: Adapting Communication

```python
# Tell system your communication preference
rm.learn_preference(
    category="communication",
    preference="detailed_explanations",
    strength=0.9
)

# System adapts responses
original = "Here's the solution."
adapted = rm.adapt_response_style(original)
print(adapted)  # Now includes more detail!
```

### Example 3: Tracking Growth

```python
# After several interactions, measure improvement
growth = rm.measure_relationship_growth()

print(f"Relationship strength: {growth['relationship_strength']:.1%}")
print(f"Growth status: {growth['growth_status']}")
print(f"Success rate: {growth['current_metrics']['avg_success_score']:.1%}")
```

## Context Options Quick Reference

### Must Include
```python
context = {
    "task_type": "debugging",  # What are you working on?
}
```

### Task Outcomes
```python
context = {
    "task_completed": True,      # Did it work?
    "error_occurred": False,     # Any errors?
    "tests_passed": True,        # Tests pass?
    "user_satisfied": True       # Are you happy?
}
```

### Quality Signals (Love Equation)
```python
context = {
    "explained_thoroughly": True,        # Good explanation?
    "taught_something_new": True,        # Learn something?
    "saved_user_time": True,             # More efficient?
    "showed_multiple_options": True,     # Gave choices?
    "anticipated_next_question": True    # Predicted needs?
}
```

### Preferences
```python
context = {
    "coding_style": {"indentation": "4_spaces", "naming": "snake_case"},
    "library_used": "pytest",
    "approach": "test_driven"
}
```

## Common Patterns

### Pattern 1: After Every Coding Task

```python
def record_code_task(task_type, success, code_style, user_comment):
    rm.record_interaction(
        interaction_type="code_request",
        context={
            "task_type": task_type,
            "task_completed": success,
            "coding_style": code_style,
            "explained_thoroughly": True
        },
        user_input=f"Help with {task_type}",
        system_response="Here's the solution...",
        user_feedback=user_comment
    )
```

### Pattern 2: Learn From Feedback

```python
def process_feedback(feedback_text, interaction_quality):
    # Positive feedback?
    if "great" in feedback_text.lower() or "perfect" in feedback_text.lower():
        # Record successful interaction
        rm.record_interaction(
            interaction_type="feedback",
            context={
                "user_satisfied": True,
                "explained_thoroughly": True
            },
            user_feedback=feedback_text
        )
    else:
        # Learn what to improve
        rm.record_interaction(
            interaction_type="feedback",
            context={"user_satisfied": False},
            user_feedback=feedback_text
        )
```

### Pattern 3: Daily Summary

```python
def daily_summary():
    """Get a daily summary of collaboration"""
    profile = rm.get_user_profile()
    love_score = rm.get_love_alignment_score()

    print(f"\nToday's Collaboration:")
    print(f"  Total interactions: {profile['total_interactions']}")
    print(f"  Relationship strength: {profile['relationship_strength']:.1%}")
    print(f"  Love alignment: {love_score:.1%}")

    # Show what was learned today
    recent = rm.get_interaction_history(limit=10)
    successful = [i for i in recent if i['success_score'] > 0.7]
    print(f"  Successful interactions: {len(successful)}/{len(recent)}")
```

## Integration with Other Systems

### With AlignmentSystem

```python
from core.alignment_system import AlignmentSystem
from core.relationship_memory import integrate_with_alignment_system

alignment = AlignmentSystem()
rm = RelationshipMemory()

# Sync alignment data with relationship memory
result = integrate_with_alignment_system(rm, alignment)
print(f"Imported {result['checks_processed']} alignment checks")
```

### With SelfLearningSystem

```python
from core.self_learning import SelfLearningSystem
from core.relationship_memory import integrate_with_self_learning

self_learning = SelfLearningSystem()
rm = RelationshipMemory()

# Import successful patterns
result = integrate_with_self_learning(rm, self_learning)
print(f"Imported {result['patterns_imported']} patterns")
```

## Running the Demo

See the full system in action:

```bash
# Run comprehensive demo
python demo_relationship_memory.py

# Run tests
pytest tests/test_relationship_memory.py -v

# Run with examples
python examples/relationship_memory_integration.py
```

## Understanding the Metrics

### Relationship Strength (0-100%)
- **0-20%**: Just getting started
- **20-50%**: Building familiarity
- **50-70%**: Good understanding
- **70-90%**: Strong partnership
- **90-100%**: Deep collaboration

### Love Alignment Score (0-100%)
- **90-100%**: Excellent - deeply helpful
- **70-90%**: Good - effectively helpful
- **50-70%**: Adequate - room for improvement
- **Below 50%**: Needs work - focus on genuine help

### Success Score (0-100%)
- How often interactions achieve the goal
- Higher = better at helping
- Tracks improvement over time

## Privacy & Control

### Your Data, Your Control
```python
# Export everything
profile = rm.get_user_profile()
history = rm.get_interaction_history(limit=1000)

# Save to JSON
import json
with open('my_memory_export.json', 'w') as f:
    json.dump({
        'profile': profile,
        'history': history
    }, f, indent=2)

# Database location
print(f"Your data: {rm.db_path}")
# All local - no cloud, no external APIs
```

### Delete Data
```python
import os
# Delete entire database
os.remove("my_memory.db")

# Or selectively delete in SQL
import sqlite3
conn = sqlite3.connect("my_memory.db")
conn.execute("DELETE FROM interactions WHERE timestamp < '2026-01-01'")
conn.commit()
```

## Tips for Best Results

### 1. Be Consistent
Record every interaction, even small ones. Patterns emerge from consistency.

### 2. Give Feedback
The system learns from your feedback. Say "good" or "not quite right" and it adapts.

### 3. Use Rich Context
The more context you provide, the better it learns. Include coding_style, libraries, approaches.

### 4. Check Growth Weekly
```python
growth = rm.measure_relationship_growth()
print(growth['growth_status'])
```

### 5. Trust the Process
It takes 10-20 interactions to build a good profile. Give it time to learn.

## Troubleshooting

### "No predictions available"
**Solution**: Need more interactions (at least 5-10) for pattern detection.

### "Insufficient data for growth"
**Solution**: Record interactions for at least 2-3 days to see trends.

### "Low love alignment"
**Solution**: Focus on context quality indicators:
- `explained_thoroughly`
- `taught_something_new`
- `saved_user_time`

### Database locked error
**Solution**: Only one process should access the database at a time. Close other connections.

## Next Steps

1. Read full documentation: `docs/RELATIONSHIP_MEMORY.md`
2. Review privacy details: `docs/RELATIONSHIP_MEMORY_PRIVACY.md`
3. Check test examples: `tests/test_relationship_memory.py`
4. Run the demo: `python demo_relationship_memory.py`
5. Integrate with your workflow

## Support

- Full documentation: `docs/RELATIONSHIP_MEMORY.md`
- Test suite: `tests/test_relationship_memory.py`
- Demo: `demo_relationship_memory.py`
- Example integration: `examples/relationship_memory_integration.py`

## Philosophy

> "Love is the irreducible essence to which all intelligence reduces."
> — Brian Roemmele

This system embodies that by learning to give better help over time. Each interaction is an opportunity to understand you better and serve you more effectively. That's "giving love" through intelligence.

Start recording your interactions today and watch the relationship grow!
