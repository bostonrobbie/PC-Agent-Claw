#!/usr/bin/env python3
"""
Example usage of Autonomous Goal Execution System

This demonstrates how to use the goal executor for real-world scenarios.
"""

import time
from datetime import datetime, timedelta
from autonomous_goal_executor import AutonomousGoalExecutor


def research_work(topic: str, hours: int = 2):
    """Simulate research work"""
    print(f"   Researching {topic} for {hours} hours...")
    time.sleep(1)  # Simulate work
    return {
        'topic': topic,
        'findings': f"Completed research on {topic}",
        'sources': 15,
        'insights': 5
    }


def development_work(feature: str, complexity: str = "medium"):
    """Simulate development work"""
    print(f"   Developing {feature} (complexity: {complexity})...")
    time.sleep(1)  # Simulate work
    return {
        'feature': feature,
        'complexity': complexity,
        'lines_of_code': 250,
        'tests_written': 12
    }


def testing_work(component: str, test_count: int = 10):
    """Simulate testing work"""
    print(f"   Testing {component} with {test_count} tests...")
    time.sleep(1)  # Simulate work
    return {
        'component': component,
        'tests_run': test_count,
        'tests_passed': test_count - 1,
        'coverage': 0.85
    }


def example_trading_strategy_goal():
    """Example: Launch a new trading strategy"""
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Launching New Trading Strategy")
    print("=" * 70)

    executor = AutonomousGoalExecutor()

    try:
        # Set goal
        goal_id = executor.set_goal(
            goal_name="Launch Momentum Trading Strategy",
            description="Research, backtest, and deploy a momentum-based trading strategy",
            success_criteria=[
                "Complete market research on momentum indicators",
                "Develop strategy logic with entry/exit rules",
                "Backtest on 2 years of historical data",
                "Optimize parameters for best Sharpe ratio",
                "Deploy to paper trading environment",
                "Monitor performance for 1 week",
                "Deploy to live trading if profitable"
            ],
            priority=3,
            deadline=datetime.now() + timedelta(days=14)
        )

        print(f"\nGoal created: {goal_id}")

        # Decompose
        print("\nDecomposing goal into tasks...")
        task_ids = executor.decompose_goal(goal_id, use_reasoning=True)
        print(f"Created {len(task_ids)} tasks")

        # Show initial status
        status = executor.get_goal_status(goal_id)
        print(f"\nInitial Progress: {status['progress']:.0%}")
        print(f"Total Tasks: {status['total_tasks']}")

        # Execute first few tasks with custom work functions
        print("\nExecuting research task...")
        executor.execute_task(task_ids[0], research_work, "momentum indicators", 4)

        print("\nExecuting development task...")
        executor.execute_task(task_ids[1], development_work, "entry/exit logic", "high")

        print("\nExecuting testing task...")
        executor.execute_task(task_ids[2], testing_work, "backtest engine", 25)

        # Check progress
        status = executor.get_goal_status(goal_id)
        print(f"\nCurrent Progress: {status['progress']:.0%}")
        print(f"Completed: {status['completed_tasks']}/{status['total_tasks']}")
        print(f"Milestones: {status['achieved_milestones']}")

        return goal_id

    finally:
        executor.close()


def example_product_launch_goal():
    """Example: Launch a new product"""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: New Product Launch")
    print("=" * 70)

    executor = AutonomousGoalExecutor()

    try:
        # Set goal
        goal_id = executor.set_goal(
            goal_name="Launch AI-Powered Analytics Dashboard",
            description="Build and launch an analytics dashboard product",
            success_criteria=[
                "Complete competitor analysis",
                "Design user interface mockups",
                "Develop MVP with core features",
                "Conduct user testing with 20 beta users",
                "Implement feedback and polish",
                "Create marketing materials",
                "Launch on Product Hunt",
                "Achieve 500 signups in first week"
            ],
            priority=3,
            deadline=datetime.now() + timedelta(days=30)
        )

        print(f"\nGoal created: {goal_id}")

        # Decompose
        print("\nDecomposing goal into tasks...")
        task_ids = executor.decompose_goal(goal_id, use_reasoning=False)  # Simple decomposition
        print(f"Created {len(task_ids)} tasks")

        # Simulate some execution
        print("\nExecuting planning task...")
        executor.execute_task(task_ids[0], lambda: {'status': 'planned'})

        # Show status
        status = executor.get_goal_status(goal_id)
        print(f"\nProgress: {status['progress']:.0%}")
        print(f"Status: {status['status']}")

        return goal_id

    finally:
        executor.close()


def example_learning_goal():
    """Example: Learning goal"""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Master Deep Learning")
    print("=" * 70)

    executor = AutonomousGoalExecutor()

    try:
        # Set goal
        goal_id = executor.set_goal(
            goal_name="Master Deep Learning",
            description="Become proficient in deep learning and neural networks",
            success_criteria=[
                "Complete Andrew Ng's Deep Learning course",
                "Read Deep Learning book by Goodfellow",
                "Implement CNN from scratch",
                "Implement RNN/LSTM from scratch",
                "Build transformer model",
                "Complete 5 Kaggle competitions",
                "Publish research paper or blog posts",
                "Build production ML system"
            ],
            priority=2,
            deadline=datetime.now() + timedelta(days=180)
        )

        print(f"\nGoal created: {goal_id}")

        # Decompose with reasoning
        print("\nDecomposing goal into tasks (using deep reasoning)...")
        task_ids = executor.decompose_goal(goal_id, use_reasoning=True)
        print(f"Created {len(task_ids)} tasks")

        # Show the plan
        status = executor.get_goal_status(goal_id)
        print(f"\nGoal: {status['goal_name']}")
        print(f"Tasks: {status['total_tasks']}")
        print(f"Progress: {status['progress']:.0%}")
        print(f"Plan Version: {status['plan_version']}")

        return goal_id

    finally:
        executor.close()


def example_adaptation():
    """Example: Plan adaptation when things change"""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Adaptive Planning")
    print("=" * 70)

    executor = AutonomousGoalExecutor()

    try:
        # Create goal
        goal_id = executor.set_goal(
            goal_name="Build Mobile App",
            description="Develop and launch mobile application",
            success_criteria=[
                "Design app architecture",
                "Build backend API",
                "Develop iOS app",
                "Develop Android app",
                "Test and deploy"
            ],
            priority=3
        )

        # Decompose
        task_ids = executor.decompose_goal(goal_id, use_reasoning=True)
        print(f"\nCreated {len(task_ids)} tasks (Plan v1)")

        # Execute some tasks
        executor.execute_task(task_ids[0], lambda: {'status': 'done'})
        executor.execute_task(task_ids[1], lambda: {'status': 'done'})

        print(f"\nProgress: {executor.track_progress(goal_id):.0%}")

        # Simulate need for adaptation
        print("\n--- Market conditions changed! ---")
        print("Customer feedback: Need web app before mobile")

        # Adapt the plan
        executor.adapt_plan(
            goal_id,
            reason="Customer feedback prioritizes web app over mobile",
            outcome_deviation=0.5
        )

        status = executor.get_goal_status(goal_id)
        print(f"\nPlan adapted to version {status['plan_version']}")
        print(f"Status: {status['status']}")
        print(f"Progress maintained: {status['progress']:.0%}")

        return goal_id

    finally:
        executor.close()


def main():
    """Run all examples"""
    print("\nAUTONOMOUS GOAL EXECUTION SYSTEM - EXAMPLES")
    print("=" * 70)

    # Example 1: Trading strategy
    example_trading_strategy_goal()

    # Example 2: Product launch
    example_product_launch_goal()

    # Example 3: Learning goal
    example_learning_goal()

    # Example 4: Adaptive planning
    example_adaptation()

    print("\n" + "=" * 70)
    print("All examples completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    main()
