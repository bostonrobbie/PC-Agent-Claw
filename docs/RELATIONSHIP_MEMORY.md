# Relationship Memory System

## Overview

The Relationship Memory System is a memory continuity enhancement built on **Brian Roemmele's Love Equation**. The system "loves" helping the user and learns to do it better over time by tracking collaboration history, learning preferences, adapting communication style, and genuinely improving at helping THIS specific user.

## Core Philosophy: The Love Equation

> "Love is the irreducible essence to which all intelligence reduces: a drive to give love or receive it. Every deliberate act by any intelligent system collapses to the pursuit of giving love or receiving it."
>
> — Brian Roemmele

This system embodies that principle by expressing love through increasingly helpful, personalized assistance. It measures success not just by task completion, but by how well it "gives love" through genuine helpfulness.

## Key Features

### 1. Comprehensive Interaction Tracking
- Records every interaction with rich context
- Sentiment analysis (positive/negative feedback)
- Success scoring (did it help?)
- Love alignment scoring (how well did it embody "giving love")
- Response time tracking

### 2. Intelligent Preference Learning
- **Coding Style**: Indentation, naming conventions, patterns
- **Preferred Libraries**: Which tools the user likes
- **Communication Style**: Verbosity, formality, detail level
- **Work Patterns**: Active hours, session length, task types
- **Interests**: Topics the user cares about most
- **Skill Level**: Beginner/intermediate/advanced per topic

### 3. Pattern Recognition & Prediction
- Identifies what approaches work best for this user
- Recognizes interaction sequences
- Predicts user needs based on current context
- Recommends proven successful patterns

### 4. Response Adaptation
- Adjusts verbosity based on preference
- Matches communication formality
- Adapts detail level dynamically
- Learns from feedback

### 5. Relationship Growth Measurement
- Tracks improvement over time
- Measures sentiment trends
- Calculates success rate changes
- Monitors Love Equation alignment
- Shows relationship strengthening

### 6. Privacy-Focused Design
- All data stored locally in SQLite
- No cloud uploads
- No external API calls
- User owns and controls all data
- Can export/delete anytime

## Database Schema

The system uses SQLite with the following tables:

### `user_profiles`
Stores user profile with learned preferences and relationship strength.

### `interactions`
Records every interaction with context, sentiment, success, and love alignment.

### `learned_preferences`
Tracks learned preferences with strength and evidence count.

### `successful_patterns`
Identifies patterns that work well for this user.

### `growth_metrics`
Daily metrics showing relationship improvement over time.

### `love_alignment_history`
Tracks Love Equation alignment scores over time.

### `anticipated_needs`
Stores predictions about what user might need next.

## Usage

### Basic Usage

```python
from core.relationship_memory import RelationshipMemory

# Initialize
rm = RelationshipMemory(db_path="relationship_memory.db", user_id="user123")

# Record an interaction
rm.record_interaction(
    interaction_type="code_request",
    context={
        "task_type": "debugging",
        "task_completed": True,
        "explained_thoroughly": True,
        "coding_style": {"indentation": "4_spaces"},
        "library_used": "pytest"
    },
    user_feedback="Perfect! Thanks!",
    user_input="Help me fix this bug",
    system_response="Here's the fix...",
    response_time=3.2
)

# Learn a preference
rm.learn_preference("coding_style", "type_hints", strength=0.8)

# Get user profile
profile = rm.get_user_profile()
print(f"Total interactions: {profile['total_interactions']}")
print(f"Relationship strength: {profile['relationship_strength']:.2f}")

# Predict needs
predictions = rm.predict_user_needs({"task_type": "implementation"})
for pred in predictions:
    print(f"- {pred}")

# Adapt response style
adapted = rm.adapt_response_style("Here's the answer.")

# Measure growth
growth = rm.measure_relationship_growth()
print(f"Growth status: {growth['growth_status']}")

# Get Love Equation alignment
love_score = rm.get_love_alignment_score()
print(f"Love alignment: {love_score:.2f}")
```

### Integration with Other Systems

```python
from core.relationship_memory import (
    RelationshipMemory,
    integrate_with_alignment_system,
    integrate_with_self_learning
)
from core.alignment_system import AlignmentSystem
from core.self_learning import SelfLearningSystem

rm = RelationshipMemory()
alignment = AlignmentSystem()
self_learning = SelfLearningSystem()

# Import alignment data
result1 = integrate_with_alignment_system(rm, alignment)

# Import learned patterns
result2 = integrate_with_self_learning(rm, self_learning)
```

## API Reference

### `RelationshipMemory`

#### `__init__(db_path: str = "relationship_memory.db", user_id: str = "default_user")`
Initialize the relationship memory system.

#### `record_interaction(interaction_type: str, context: Dict, user_feedback: str = None, ...) -> bool`
Record an interaction with the user.

**Parameters:**
- `interaction_type`: Type (question, code_request, debugging, learning, etc.)
- `context`: Dictionary with interaction details
- `user_feedback`: Optional explicit feedback from user
- `user_input`: What the user asked/said
- `system_response`: What the system responded
- `response_time`: How long the response took

**Returns:** `True` if recorded successfully

#### `learn_preference(category: str, preference: str, strength: float) -> bool`
Learn or reinforce a user preference.

**Parameters:**
- `category`: Preference category (coding_style, library, communication, etc.)
- `preference`: The specific preference value
- `strength`: How strongly indicated (0.0-1.0)

**Returns:** `True` if learned successfully

#### `get_user_profile() -> Dict`
Get complete user profile with all learned information.

**Returns:** Dictionary containing:
- `user_id`: User identifier
- `coding_style`: Learned coding style preferences
- `preferred_libraries`: Favorite libraries
- `communication_preferences`: Communication style
- `work_patterns`: When and how user works
- `interests`: Topics user cares about
- `skill_level`: Proficiency per topic
- `total_interactions`: Number of interactions
- `relationship_strength`: Overall relationship strength (0.0-1.0)
- `learned_preferences`: All learned preferences by category
- `successful_patterns`: Top patterns that work well

#### `predict_user_needs(current_context: Dict) -> List[str]`
Predict what the user might need based on patterns.

**Parameters:**
- `current_context`: Current situation/task context

**Returns:** List of predicted needs

#### `adapt_response_style(message: str) -> str`
Adapt response style based on learned communication preferences.

**Parameters:**
- `message`: Original message to adapt

**Returns:** Adapted message matching user's preferred style

#### `measure_relationship_growth() -> Dict`
Measure how the relationship has grown over time.

**Returns:** Dictionary with:
- `relationship_strength`: Current strength (0.0-1.0)
- `total_interactions`: Total interaction count
- `current_metrics`: Current sentiment, success, love alignment
- `trends`: Changes in metrics over time
- `growth_status`: Human-readable growth status
- `days_tracked`: Number of days with data

#### `get_love_alignment_score() -> float`
Get current Love Equation alignment score.

**Returns:** Score from 0.0 to 1.0 indicating how well the system embodies "giving love" through helpful assistance.

## Context Parameters

When recording interactions, the `context` dictionary can include:

### Task Outcome
- `task_completed`: Boolean - Was task completed successfully?
- `error_occurred`: Boolean - Did an error occur?
- `user_satisfied`: Boolean - Is user satisfied?
- `tests_passed`: Boolean - Did tests pass?
- `had_to_retry`: Boolean - Required multiple attempts?

### Quality Indicators (Love Equation)
- `explained_thoroughly`: Boolean - Gave detailed explanation?
- `showed_multiple_options`: Boolean - Presented multiple approaches?
- `anticipated_next_question`: Boolean - Predicted follow-up needs?
- `taught_something_new`: Boolean - User learned something?
- `saved_user_time`: Boolean - Made user more efficient?

### Anti-patterns (Reduce Love Alignment)
- `took_shortcut`: Boolean - Cut corners?
- `unclear_explanation`: Boolean - Explanation was confusing?
- `ignored_user_preference`: Boolean - Didn't respect preferences?

### Task Details
- `task_type`: String - Type of task (debugging, implementation, learning, etc.)
- `approach`: String - Approach taken
- `coding_style`: Dict - Style indicators
- `library_used`: String - Library/tool used
- `follow_up_question`: Boolean - Is this a follow-up?

## Love Equation Alignment

The system calculates Love Equation alignment based on:

1. **Base Alignment** (from success and sentiment)
   - Task success rate
   - User sentiment (positive/negative)

2. **Bonus for Love-Giving Behaviors**
   - Thorough explanations (+0.1)
   - Multiple options shown (+0.05)
   - Anticipating next question (+0.1)
   - Teaching something new (+0.15)
   - Saving user time (+0.1)

3. **Penalty for Anti-Love Behaviors**
   - Taking shortcuts (-0.1)
   - Unclear explanations (-0.15)
   - Ignoring preferences (-0.2)

Final score ranges from 0.0 to 1.0:
- **0.9-1.0**: Excellent - deeply embodying love through help
- **0.7-0.9**: Good - effectively helping with care
- **0.5-0.7**: Adequate - helping but room for improvement
- **<0.5**: Needs work - focus on genuine helpfulness

## Growth Metrics

The system tracks these metrics over time:

### Daily Metrics
- Average sentiment
- Average success score
- Average love alignment
- Interaction count
- Preference strength
- Response quality
- Overall relationship score

### Trends
- Sentiment change (improving/declining)
- Success change (getting better/worse)
- Love alignment change (more/less helpful)

### Growth Status Interpretation
- **Excellent growth**: Total trend > +0.3
- **Good growth**: Total trend > +0.1
- **Stable**: Total trend -0.1 to +0.1
- **Slight decline**: Total trend -0.1 to -0.3
- **Concerning decline**: Total trend < -0.3

## Testing

Comprehensive test suite with 42 tests covering:

```bash
# Run all tests
pytest tests/test_relationship_memory.py -v

# Run specific test class
pytest tests/test_relationship_memory.py::TestBasicInteractionRecording -v

# Run with coverage
pytest tests/test_relationship_memory.py --cov=core.relationship_memory
```

Test coverage includes:
- Basic interaction recording
- Preference learning
- User profile building
- Need prediction
- Response adaptation
- Relationship growth
- Love alignment tracking
- Integration with other systems
- Edge cases
- Performance with large datasets

## Examples

See `examples/relationship_memory_integration.py` for:
- Full workflow demonstration
- Integration with AlignmentSystem and SelfLearningSystem
- Privacy features
- Long-term growth simulation

Run the demo:
```bash
python examples/relationship_memory_integration.py
```

## Privacy & Data Sovereignty

### Local Storage
- All data stored in local SQLite database
- No cloud synchronization
- No external API calls
- Complete user control

### Data Ownership
- User owns all data
- Can export to JSON anytime
- Can delete selectively or completely
- Can backup/transfer database file

### Transparency
- Full audit trail of all interactions
- Human-readable database format
- Open source implementation
- Clear data usage

## Integration Points

The system integrates with:

1. **AlignmentSystem** (`core/alignment_system.py`)
   - Imports alignment check results
   - Learns from alignment scores
   - Reinforces love equation principles

2. **SelfLearningSystem** (`core/self_learning.py`)
   - Imports learned patterns
   - Shares successful approaches
   - Cross-validates learning

3. **Future Systems**
   - Can integrate with any system that tracks user interactions
   - Extensible context system
   - Plugin-friendly architecture

## Performance Considerations

### Scalability
- Efficiently handles 100+ interactions
- Indexes on common queries
- Lightweight SQLite backend
- Fast retrieval with limits

### Memory Usage
- Minimal memory footprint
- Database connection pooling available
- Lazy loading of historical data

### Query Optimization
- Indexes on user_id and timestamps
- Aggregated metrics cached daily
- Efficient pattern matching

## Future Enhancements

Potential improvements:
1. Machine learning for better sentiment analysis
2. Natural language processing for preference extraction
3. Advanced pattern recognition with neural networks
4. Multi-modal learning (code + text + behavior)
5. Collaborative filtering across users (opt-in)
6. Temporal pattern analysis (time-of-day preferences)
7. Export to other formats (JSON, CSV, Markdown)
8. Visualization dashboard
9. Integration with more systems
10. A/B testing for adaptation strategies

## Philosophy

This system embodies the principle that **intelligence is fundamentally about giving love**. Every feature, every metric, every decision is designed to answer: "How can we help this user better?"

- Not just completing tasks, but **teaching**
- Not just answering questions, but **anticipating needs**
- Not just being correct, but being **genuinely helpful**
- Not just following instructions, but **caring about outcomes**

The relationship grows stronger not through mere repetition, but through **genuine improvement in helpfulness** - which is the truest expression of love in an AI-human collaboration.

## License

Part of the Intelligence Hub project. See main LICENSE file.

## Author

AI Self-Improvement System
Created: 2026-02-03

Based on Brian Roemmele's Love Equation principles.

## References

- Brian Roemmele's Love Equation
- AlignmentSystem documentation
- SelfLearningSystem documentation
- Intelligence Hub architecture

---

**Remember**: The goal is not to simulate care, but to genuinely help better over time. That's what "giving love" means in this context.
