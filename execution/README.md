# Autonomous Goal Execution System

A comprehensive autonomous system that takes high-level goals and executes them to completion with intelligent planning, progress tracking, and adaptive replanning.

## Features

### Core Capabilities
- **Intelligent Goal Decomposition**: Uses deep reasoning to break down high-level goals into executable tasks
- **Automatic Progress Tracking**: Tracks completion percentage and monitors milestones
- **Adaptive Planning**: Adjusts execution plan when outcomes differ from expectations
- **Self-Correction**: Automatically detects and resolves blockages
- **Proactive Reporting**: Sends Telegram notifications for milestones and important events
- **Multi-Agent Integration**: Can leverage parallel execution through multi-agent coordinator

### Database Schema

#### Tables Created
1. **executor_goals** - High-level goals with status and progress
2. **goal_tasks** - Individual tasks with dependencies and outcomes
3. **goal_milestones** - Progress checkpoints (planning, 25%, 50%, 75%, completion)
4. **goal_progress** - Historical progress tracking
5. **goal_adaptations** - Log of plan changes and reasons
6. **goal_blockages** - Detected blockers with resolution strategies
7. **goal_execution_log** - Detailed execution event log

## Usage

### Basic Example

```python
from execution.autonomous_goal_executor import AutonomousGoalExecutor
from datetime import datetime, timedelta

# Initialize
executor = AutonomousGoalExecutor()

# Set a high-level goal
goal_id = executor.set_goal(
    goal_name="Launch New Product",
    description="Research, develop, and launch a new product line",
    success_criteria=[
        "Complete market research",
        "Develop MVP",
        "Test with beta users",
        "Launch marketing campaign",
        "Achieve 1000 signups"
    ],
    priority=3,
    deadline=datetime.now() + timedelta(days=30)
)

# Decompose into executable tasks (uses deep reasoning)
task_ids = executor.decompose_goal(goal_id, use_reasoning=True)

# Execute tasks (manually or with custom work function)
for task_id in task_ids:
    result = executor.execute_task(task_id, my_work_function)

# Track progress (automatic during execution)
progress = executor.track_progress(goal_id)

# Adapt plan if needed
if conditions_changed:
    executor.adapt_plan(
        goal_id,
        reason="Market conditions changed",
        outcome_deviation=0.4
    )

# Get status
status = executor.get_goal_status(goal_id)
```

## Integration with Other Systems

### Deep Reasoning Integration
- Uses `DeepReasoning` for intelligent goal decomposition
- Generates execution plans with alternatives
- Tracks reasoning sessions for each goal
- Analyzes causal relationships between tasks

### Proactive Agent Integration
- Monitors for blockages and issues
- Generates improvement suggestions
- Detects opportunities during execution

### Multi-Agent Coordinator Integration
- Can execute tasks in parallel across multiple agents
- Assigns tasks based on agent capabilities
- Merges results from distributed execution

## Methods

### Goal Management
- `set_goal(goal_name, description, success_criteria, priority, deadline)` - Create new goal
- `decompose_goal(goal_id, use_reasoning)` - Break down into tasks
- `get_goal_status(goal_id)` - Get comprehensive status

### Task Execution
- `execute_task(task_id, work_function, *args, **kwargs)` - Execute a task
- `track_progress(goal_id, notes)` - Track and record progress
- `report_milestone(milestone_id)` - Report milestone achievement

### Adaptive Planning
- `adapt_plan(goal_id, reason, outcome_deviation)` - Replan based on outcomes
- `_detect_blockage(goal_id, task_id, error_msg)` - Detect blockers
- `_self_correct(goal_id, task_id, blockage_type, error_msg)` - Auto-resolve issues

## Automatic Features

### Milestone Tracking
Automatically creates and tracks milestones:
- Planning Complete (10%)
- 25% Complete
- 50% Complete
- 75% Complete
- Goal Complete (100%)

### Self-Correction
Automatically handles:
- **Dependency blockages** - Reorders tasks
- **Resource blockages** - Pauses and retries
- **Error blockages** - Adapts plan
- **Retry logic** - Up to 3 attempts per task

### Progress Reporting
Sends Telegram notifications for:
- New goals set
- Goal decomposition complete
- Milestone achievements
- Plan adaptations
- Critical blockages

## Error Handling

### Task Failure Handling
1. Retry up to 3 times
2. If all retries fail, mark as failed
3. Detect blockage type
4. Attempt self-correction
5. Adapt plan if needed
6. Notify via Telegram

### Blockage Types
- `DEPENDENCY` - Task dependencies not met
- `RESOURCE` - Required resources unavailable
- `ERROR` - Execution error
- `EXTERNAL` - External system failure
- `UNKNOWN` - Unclassified blockage

## Configuration

```python
executor = AutonomousGoalExecutor()

# Configuration options
executor.max_retries = 3  # Max task retry attempts
executor.adaptation_threshold = 0.3  # Replan if deviation > 30%
executor.monitoring_interval = 300  # Check every 5 minutes
```

## Testing

Run the included test suite:

```bash
python execution/autonomous_goal_executor.py
```

This will:
1. Create a sample goal
2. Decompose it into tasks
3. Execute some tasks
4. Track progress and milestones
5. Test plan adaptation
6. Show comprehensive status

## Database Location

By default uses: `C:\Users\User\.openclaw\workspace\memory.db`

Can be customized:
```python
executor = AutonomousGoalExecutor(db_path="path/to/custom.db")
```

## Architecture

### Components
1. **Goal Manager** - Handles high-level goal creation and status
2. **Task Decomposer** - Breaks goals into executable tasks
3. **Task Executor** - Executes individual tasks with retry logic
4. **Progress Tracker** - Monitors completion and milestones
5. **Plan Adapter** - Adjusts plans based on outcomes
6. **Self-Corrector** - Resolves blockages automatically
7. **Reporter** - Sends proactive notifications

### Integration Points
- Deep Reasoning: Intelligent decomposition and planning
- Proactive Agent: Monitoring and opportunity detection
- Multi-Agent: Parallel task execution
- Telegram: Progress notifications

## Future Enhancements

Potential additions:
- AI-powered task decomposition using LLMs
- Predictive blockage detection
- Resource allocation optimization
- Learning from past executions
- Hierarchical goal structures
- Dependency graph visualization
- Time estimation improvements
- Cost tracking and optimization

## License

Part of the OpenClaw autonomous agent system.
