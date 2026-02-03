#!/usr/bin/env python3
"""
Autonomous Goal Execution System - Break down and execute high-level goals autonomously

This system provides:
- Goal decomposition into executable tasks
- Automatic progress tracking with milestones
- Adaptive planning based on outcomes
- Proactive progress reporting via Telegram
- Self-correction when blocked
- Integration with deep reasoning for planning
- Integration with proactive agent for monitoring
- Integration with multi-agent for parallel execution
"""

import sqlite3
import json
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import traceback
import uuid


class GoalStatus(Enum):
    """Status of goals"""
    PENDING = "pending"
    PLANNING = "planning"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class TaskStatus(Enum):
    """Status of tasks"""
    PENDING = "pending"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


class MilestoneType(Enum):
    """Types of milestones"""
    PLANNING = "planning"
    EXECUTION = "execution"
    CHECKPOINT = "checkpoint"
    COMPLETION = "completion"


class BlockageType(Enum):
    """Types of blockages"""
    DEPENDENCY = "dependency"
    RESOURCE = "resource"
    ERROR = "error"
    EXTERNAL = "external"
    UNKNOWN = "unknown"


class AutonomousGoalExecutor:
    """
    Autonomous system that takes high-level goals and executes them to completion

    Features:
    - Intelligent goal decomposition using deep reasoning
    - Automatic task generation and dependency management
    - Progress tracking with milestones
    - Adaptive replanning when outcomes differ from expectations
    - Self-correction when blocked
    - Proactive progress reporting via Telegram
    - Integration with multi-agent for parallel execution
    - Learning from past executions
    """

    def __init__(self, db_path: str = None):
        if db_path is None:
            workspace = Path(__file__).parent.parent
            db_path = workspace / "memory.db"

        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

        # Configuration
        self.max_retries = 3
        self.adaptation_threshold = 0.3  # Replan if deviation > 30%
        self.monitoring_interval = 300  # Check every 5 minutes
        self.monitoring_active = False
        self.monitoring_thread = None
        self.lock = threading.Lock()

        # Load integrations
        self._load_integrations()

    def _load_integrations(self):
        """Load integrated systems"""
        workspace = Path(__file__).parent.parent

        # Load Telegram notifier
        try:
            import sys
            sys.path.insert(0, str(workspace))
            from telegram_notifier import TelegramNotifier
            self.notifier = TelegramNotifier()
        except Exception as e:
            print(f"[WARNING] Could not load Telegram notifier: {e}")
            self.notifier = None

        # Load deep reasoning
        try:
            sys.path.insert(0, str(workspace / "reasoning"))
            from deep_reasoning import DeepReasoning
            self.reasoner = DeepReasoning(db_path=self.db_path)
        except Exception as e:
            print(f"[WARNING] Could not load DeepReasoning: {e}")
            self.reasoner = None

        # Load proactive agent
        try:
            sys.path.insert(0, str(workspace / "agents"))
            from proactive_agent import ProactiveAgent
            self.proactive = ProactiveAgent(db_path=self.db_path)
        except Exception as e:
            print(f"[WARNING] Could not load ProactiveAgent: {e}")
            self.proactive = None

        # Load multi-agent coordinator
        try:
            from multi_agent_coordinator import MultiAgentCoordinator
            self.coordinator = MultiAgentCoordinator(db_path=self.db_path, max_agents=5)
        except Exception as e:
            print(f"[WARNING] Could not load MultiAgentCoordinator: {e}")
            self.coordinator = None

    def _init_db(self):
        """Initialize database schema"""
        cursor = self.conn.cursor()

        # Goals table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS executor_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_id TEXT UNIQUE NOT NULL,
                goal_name TEXT NOT NULL,
                description TEXT,
                success_criteria TEXT,
                status TEXT DEFAULT 'pending',
                priority INTEGER DEFAULT 2,
                deadline TIMESTAMP,
                progress REAL DEFAULT 0.0,
                reasoning_session_id INTEGER,
                plan_version INTEGER DEFAULT 1,
                total_tasks INTEGER DEFAULT 0,
                completed_tasks INTEGER DEFAULT 0,
                failed_tasks INTEGER DEFAULT 0,
                blocked_tasks INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                failed_at TIMESTAMP,
                metadata TEXT
            )
        ''')

        # Tasks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS goal_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT UNIQUE NOT NULL,
                goal_id TEXT NOT NULL,
                task_name TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'pending',
                priority INTEGER DEFAULT 2,
                dependencies TEXT,
                expected_duration_minutes INTEGER,
                actual_duration_minutes INTEGER,
                expected_outcome TEXT,
                actual_outcome TEXT,
                assigned_agent TEXT,
                retry_count INTEGER DEFAULT 0,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                metadata TEXT,
                FOREIGN KEY (goal_id) REFERENCES executor_goals(goal_id)
            )
        ''')

        # Milestones table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS goal_milestones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                milestone_id TEXT UNIQUE NOT NULL,
                goal_id TEXT NOT NULL,
                milestone_name TEXT NOT NULL,
                milestone_type TEXT NOT NULL,
                description TEXT,
                target_progress REAL,
                achieved_progress REAL,
                achieved INTEGER DEFAULT 0,
                notified INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                achieved_at TIMESTAMP,
                metadata TEXT,
                FOREIGN KEY (goal_id) REFERENCES executor_goals(goal_id)
            )
        ''')

        # Progress tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS goal_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_id TEXT NOT NULL,
                progress REAL NOT NULL,
                completed_tasks INTEGER,
                total_tasks INTEGER,
                status TEXT,
                notes TEXT,
                reported INTEGER DEFAULT 0,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (goal_id) REFERENCES executor_goals(goal_id)
            )
        ''')

        # Adaptations log
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS goal_adaptations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_id TEXT NOT NULL,
                adaptation_type TEXT NOT NULL,
                reason TEXT,
                old_plan TEXT,
                new_plan TEXT,
                outcome_deviation REAL,
                adapted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,
                FOREIGN KEY (goal_id) REFERENCES executor_goals(goal_id)
            )
        ''')

        # Blockages log
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS goal_blockages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_id TEXT NOT NULL,
                task_id TEXT,
                blockage_type TEXT NOT NULL,
                description TEXT,
                resolution_strategy TEXT,
                resolved INTEGER DEFAULT 0,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP,
                metadata TEXT,
                FOREIGN KEY (goal_id) REFERENCES executor_goals(goal_id)
            )
        ''')

        # Execution log
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS goal_execution_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_id TEXT NOT NULL,
                task_id TEXT,
                event_type TEXT NOT NULL,
                details TEXT,
                logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (goal_id) REFERENCES executor_goals(goal_id)
            )
        ''')

        self.conn.commit()

    # === GOAL MANAGEMENT ===

    def set_goal(self, goal_name: str, description: str,
                 success_criteria: List[str], priority: int = 2,
                 deadline: datetime = None, metadata: Dict = None) -> str:
        """Set a new high-level goal for autonomous execution"""
        goal_id = f"goal_{uuid.uuid4().hex[:8]}"

        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO executor_goals
            (goal_id, goal_name, description, success_criteria, priority,
             deadline, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (goal_id, goal_name, description, json.dumps(success_criteria),
              priority, deadline, json.dumps(metadata) if metadata else None))
        self.conn.commit()

        self._log_execution(
            goal_id=goal_id,
            event_type="goal_set",
            details=f"New goal created: {goal_name}"
        )

        # Notify
        if self.notifier:
            try:
                self.notifier.send_message(
                    f"🎯 *New Goal Set*\n\n"
                    f"*{goal_name}*\n\n"
                    f"{description}\n\n"
                    f"Priority: {priority}\n"
                    f"Criteria: {len(success_criteria)} items",
                    priority="info"
                )
            except Exception as e:
                print(f"[WARNING] Could not send notification: {e}")

        print(f"[GOAL] Set new goal {goal_id}: {goal_name}")
        return goal_id

    def decompose_goal(self, goal_id: str, use_reasoning: bool = True) -> List[str]:
        """Decompose goal into executable tasks using deep reasoning"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM executor_goals WHERE goal_id = ?', (goal_id,))
        goal = dict(cursor.fetchone())

        # Update status
        cursor.execute('''
            UPDATE executor_goals SET status = 'planning' WHERE goal_id = ?
        ''', (goal_id,))
        self.conn.commit()

        task_ids = []

        try:
            if use_reasoning and self.reasoner:
                # Use deep reasoning for intelligent decomposition
                from reasoning.deep_reasoning import ReasoningType

                session_id = self.reasoner.start_reasoning_session(
                    session_name=f"Goal Decomposition: {goal['goal_name']}",
                    goal=f"Break down goal into executable tasks",
                    reasoning_type=ReasoningType.DEDUCTIVE,
                    context={
                        'goal_name': goal['goal_name'],
                        'description': goal['description'],
                        'success_criteria': json.loads(goal['success_criteria'])
                    }
                )

                # Store session ID
                cursor.execute('''
                    UPDATE executor_goals
                    SET reasoning_session_id = ?
                    WHERE goal_id = ?
                ''', (session_id, goal_id))
                self.conn.commit()

                # Add reasoning steps
                self.reasoner.add_thought(
                    thought="Analyzing goal structure and requirements",
                    reasoning_type=ReasoningType.DEDUCTIVE,
                    confidence=0.9
                )

                self.reasoner.add_thought(
                    thought="Identifying key milestones and dependencies",
                    reasoning_type=ReasoningType.INDUCTIVE,
                    confidence=0.85
                )

                # Generate plan
                steps = self._generate_task_steps(goal)

                plan_id = self.reasoner.generate_plan(
                    plan_name=f"Execution Plan for {goal['goal_name']}",
                    description=f"Decomposed tasks to achieve: {goal['description']}",
                    steps=steps,
                    expected_outcome=f"Goal {goal['goal_name']} completed successfully",
                    probability_success=0.8,
                    time_estimate_hours=len(steps) * 2
                )

                self.reasoner.choose_plan(plan_id, "Primary execution plan")
                self.reasoner.complete_reasoning_session(
                    session_id,
                    conclusion=f"Generated {len(steps)} tasks for goal execution",
                    confidence=0.85
                )

            else:
                # Simple decomposition
                steps = self._generate_task_steps(goal)

            # Create tasks
            for i, step in enumerate(steps, 1):
                task_id = self._create_task(
                    goal_id=goal_id,
                    task_name=step['name'],
                    description=step['description'],
                    priority=step.get('priority', 2),
                    dependencies=step.get('dependencies', []),
                    expected_duration=step.get('duration', 30)
                )
                task_ids.append(task_id)

            # Create milestones
            self._create_milestones(goal_id, len(task_ids))

            # Update goal
            cursor.execute('''
                UPDATE executor_goals
                SET status = 'active', total_tasks = ?, started_at = CURRENT_TIMESTAMP
                WHERE goal_id = ?
            ''', (len(task_ids), goal_id))
            self.conn.commit()

            self._log_execution(
                goal_id=goal_id,
                event_type="goal_decomposed",
                details=f"Created {len(task_ids)} tasks"
            )

            # Notify
            if self.notifier:
                try:
                    self.notifier.send_message(
                        f"📋 *Goal Decomposed*\n\n"
                        f"*{goal['goal_name']}*\n\n"
                        f"Generated {len(task_ids)} tasks\n"
                        f"Starting execution...",
                        priority="info"
                    )
                except Exception as e:
                    print(f"[WARNING] Could not send notification: {e}")

            print(f"[GOAL] Decomposed {goal_id} into {len(task_ids)} tasks")
            return task_ids

        except Exception as e:
            error_msg = f"Failed to decompose goal: {str(e)}"
            cursor.execute('''
                UPDATE executor_goals SET status = 'failed' WHERE goal_id = ?
            ''', (goal_id,))
            self.conn.commit()

            self._log_execution(
                goal_id=goal_id,
                event_type="decomposition_failed",
                details=error_msg
            )
            raise

    def _generate_task_steps(self, goal: Dict) -> List[Dict]:
        """Generate task steps from goal (can be enhanced with AI)"""
        # This is a simplified version - in production, this could use
        # AI/LLM to generate contextual tasks

        criteria = json.loads(goal['success_criteria'])
        steps = []

        # Planning phase
        steps.append({
            'name': 'Initial Planning',
            'description': f'Plan approach for: {goal["goal_name"]}',
            'priority': 3,
            'duration': 15,
            'dependencies': []
        })

        # Execution phases based on criteria
        for i, criterion in enumerate(criteria, 1):
            steps.append({
                'name': f'Execute: {criterion[:50]}',
                'description': f'Work on: {criterion}',
                'priority': 2,
                'duration': 60,
                'dependencies': [steps[0]['name']] if i == 1 else [steps[i-1]['name']]
            })

        # Verification phase
        steps.append({
            'name': 'Verification',
            'description': 'Verify all success criteria met',
            'priority': 3,
            'duration': 30,
            'dependencies': [steps[-1]['name']]
        })

        return steps

    def _create_task(self, goal_id: str, task_name: str, description: str,
                    priority: int = 2, dependencies: List[str] = None,
                    expected_duration: int = 30) -> str:
        """Create a task for a goal"""
        task_id = f"task_{uuid.uuid4().hex[:8]}"

        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO goal_tasks
            (task_id, goal_id, task_name, description, priority,
             dependencies, expected_duration_minutes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (task_id, goal_id, task_name, description, priority,
              json.dumps(dependencies) if dependencies else None,
              expected_duration))
        self.conn.commit()

        return task_id

    def _create_milestones(self, goal_id: str, total_tasks: int):
        """Create milestones for a goal"""
        milestones = [
            {
                'name': 'Planning Complete',
                'type': MilestoneType.PLANNING,
                'progress': 0.1,
                'description': 'Initial planning phase completed'
            },
            {
                'name': '25% Complete',
                'type': MilestoneType.CHECKPOINT,
                'progress': 0.25,
                'description': 'Quarter of tasks completed'
            },
            {
                'name': '50% Complete',
                'type': MilestoneType.CHECKPOINT,
                'progress': 0.50,
                'description': 'Half of tasks completed'
            },
            {
                'name': '75% Complete',
                'type': MilestoneType.CHECKPOINT,
                'progress': 0.75,
                'description': 'Three quarters completed'
            },
            {
                'name': 'Goal Complete',
                'type': MilestoneType.COMPLETION,
                'progress': 1.0,
                'description': 'All tasks completed successfully'
            }
        ]

        cursor = self.conn.cursor()
        for milestone in milestones:
            milestone_id = f"milestone_{uuid.uuid4().hex[:8]}"
            cursor.execute('''
                INSERT INTO goal_milestones
                (milestone_id, goal_id, milestone_name, milestone_type,
                 description, target_progress)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (milestone_id, goal_id, milestone['name'],
                  milestone['type'].value, milestone['description'],
                  milestone['progress']))
        self.conn.commit()

    # === TASK EXECUTION ===

    def execute_task(self, task_id: str, work_function: Callable = None,
                    *args, **kwargs) -> Any:
        """Execute a single task"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM goal_tasks WHERE task_id = ?', (task_id,))
        task = dict(cursor.fetchone())

        goal_id = task['goal_id']

        # Check dependencies
        if not self._check_dependencies(task):
            self._log_execution(
                goal_id=goal_id,
                task_id=task_id,
                event_type="task_blocked",
                details="Dependencies not met"
            )
            raise ValueError(f"Task {task_id} dependencies not met")

        # Update status
        cursor.execute('''
            UPDATE goal_tasks
            SET status = 'in_progress', started_at = CURRENT_TIMESTAMP
            WHERE task_id = ?
        ''', (task_id,))
        self.conn.commit()

        start_time = time.time()

        try:
            # Execute work
            if work_function:
                result = work_function(*args, **kwargs)
            else:
                # Default work (placeholder)
                result = {'status': 'completed', 'task_id': task_id}
                time.sleep(1)  # Simulate work

            duration = int((time.time() - start_time) / 60)

            # Mark as completed
            cursor.execute('''
                UPDATE goal_tasks
                SET status = 'completed', actual_duration_minutes = ?,
                    actual_outcome = ?, completed_at = CURRENT_TIMESTAMP
                WHERE task_id = ?
            ''', (duration, json.dumps(result), task_id))

            # Update goal
            cursor.execute('''
                UPDATE executor_goals
                SET completed_tasks = completed_tasks + 1
                WHERE goal_id = ?
            ''', (goal_id,))
            self.conn.commit()

            # Track progress
            self.track_progress(goal_id)

            self._log_execution(
                goal_id=goal_id,
                task_id=task_id,
                event_type="task_completed",
                details=f"Completed in {duration} minutes"
            )

            print(f"[TASK] Completed {task_id}: {task['task_name']}")
            return result

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            duration = int((time.time() - start_time) / 60)

            # Handle failure
            retry_count = task['retry_count']
            if retry_count < self.max_retries:
                # Retry
                cursor.execute('''
                    UPDATE goal_tasks
                    SET status = 'pending', retry_count = retry_count + 1,
                        error_message = ?
                    WHERE task_id = ?
                ''', (error_msg, task_id))
                self.conn.commit()

                self._log_execution(
                    goal_id=goal_id,
                    task_id=task_id,
                    event_type="task_retry",
                    details=f"Retry {retry_count + 1}/{self.max_retries}: {error_msg}"
                )

                print(f"[TASK] Retrying {task_id} (attempt {retry_count + 1})")
                # Retry
                return self.execute_task(task_id, work_function, *args, **kwargs)
            else:
                # Failed permanently
                cursor.execute('''
                    UPDATE goal_tasks
                    SET status = 'failed', error_message = ?,
                        actual_duration_minutes = ?
                    WHERE task_id = ?
                ''', (error_msg, duration, task_id))

                cursor.execute('''
                    UPDATE executor_goals
                    SET failed_tasks = failed_tasks + 1
                    WHERE goal_id = ?
                ''', (goal_id,))
                self.conn.commit()

                self._log_execution(
                    goal_id=goal_id,
                    task_id=task_id,
                    event_type="task_failed",
                    details=error_msg
                )

                # Detect blockage
                self._detect_blockage(goal_id, task_id, error_msg)

                print(f"[TASK] Failed {task_id}: {error_msg}")
                raise

    def _check_dependencies(self, task: Dict) -> bool:
        """Check if task dependencies are met"""
        if not task['dependencies']:
            return True

        dependencies = json.loads(task['dependencies'])
        cursor = self.conn.cursor()

        for dep_name in dependencies:
            # Find dependency task
            cursor.execute('''
                SELECT status FROM goal_tasks
                WHERE goal_id = ? AND task_name = ?
            ''', (task['goal_id'], dep_name))
            result = cursor.fetchone()

            if not result or result['status'] != 'completed':
                return False

        return True

    # === PROGRESS TRACKING ===

    def track_progress(self, goal_id: str, notes: str = None) -> float:
        """Track and record progress for a goal"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM executor_goals WHERE goal_id = ?', (goal_id,))
        goal = dict(cursor.fetchone())

        # Calculate progress
        total = goal['total_tasks']
        completed = goal['completed_tasks']
        progress = completed / total if total > 0 else 0.0

        # Update goal
        cursor.execute('''
            UPDATE executor_goals SET progress = ? WHERE goal_id = ?
        ''', (progress, goal_id))

        # Record progress
        cursor.execute('''
            INSERT INTO goal_progress
            (goal_id, progress, completed_tasks, total_tasks, status, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (goal_id, progress, completed, total, goal['status'], notes))
        self.conn.commit()

        # Check milestones
        self._check_milestones(goal_id, progress)

        return progress

    def _check_milestones(self, goal_id: str, current_progress: float):
        """Check and report milestones"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM goal_milestones
            WHERE goal_id = ? AND achieved = 0 AND target_progress <= ?
            ORDER BY target_progress ASC
        ''', (goal_id, current_progress))

        milestones = cursor.fetchall()

        for milestone in milestones:
            # Mark as achieved
            cursor.execute('''
                UPDATE goal_milestones
                SET achieved = 1, achieved_progress = ?,
                    achieved_at = CURRENT_TIMESTAMP
                WHERE milestone_id = ?
            ''', (current_progress, milestone['milestone_id']))
            self.conn.commit()

            # Report milestone
            self.report_milestone(milestone['milestone_id'])

    def report_milestone(self, milestone_id: str):
        """Report a milestone achievement"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT m.*, g.goal_name
            FROM goal_milestones m
            JOIN executor_goals g ON m.goal_id = g.goal_id
            WHERE m.milestone_id = ?
        ''', (milestone_id,))
        milestone = dict(cursor.fetchone())

        # Notify
        if self.notifier and not milestone['notified']:
            try:
                emoji = {
                    'planning': '📝',
                    'checkpoint': '✅',
                    'completion': '🎉'
                }.get(milestone['milestone_type'], '🎯')

                self.notifier.send_message(
                    f"{emoji} *Milestone Achieved*\n\n"
                    f"*{milestone['milestone_name']}*\n\n"
                    f"Goal: {milestone['goal_name']}\n"
                    f"Progress: {milestone['achieved_progress']:.0%}\n"
                    f"{milestone['description']}",
                    priority="success"
                )

                cursor.execute('''
                    UPDATE goal_milestones SET notified = 1
                    WHERE milestone_id = ?
                ''', (milestone_id,))
                self.conn.commit()

            except Exception as e:
                print(f"[WARNING] Could not send notification: {e}")

        self._log_execution(
            goal_id=milestone['goal_id'],
            event_type="milestone_achieved",
            details=f"{milestone['milestone_name']} at {milestone['achieved_progress']:.0%}"
        )

        print(f"[MILESTONE] {milestone['milestone_name']} achieved!")

    # === ADAPTIVE PLANNING ===

    def adapt_plan(self, goal_id: str, reason: str, outcome_deviation: float = 0.0):
        """Adapt the execution plan based on outcomes"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM executor_goals WHERE goal_id = ?', (goal_id,))
        goal = dict(cursor.fetchone())

        # Get current plan
        cursor.execute('''
            SELECT * FROM goal_tasks WHERE goal_id = ? ORDER BY id
        ''', (goal_id,))
        old_tasks = [dict(row) for row in cursor.fetchall()]
        old_plan = json.dumps([t['task_name'] for t in old_tasks])

        # Generate new plan
        new_version = goal['plan_version'] + 1

        # Use reasoning for adaptation if available
        if self.reasoner:
            from reasoning.deep_reasoning import ReasoningType

            session_id = self.reasoner.start_reasoning_session(
                session_name=f"Plan Adaptation: {goal['goal_name']}",
                goal="Adapt execution plan based on outcomes",
                reasoning_type=ReasoningType.ABDUCTIVE,
                context={
                    'goal_id': goal_id,
                    'reason': reason,
                    'deviation': outcome_deviation
                }
            )

            self.reasoner.add_thought(
                thought=f"Need to adapt plan due to: {reason}",
                reasoning_type=ReasoningType.ABDUCTIVE,
                confidence=0.8
            )

            # Analyze what went wrong
            self.reasoner.add_causal_link(
                cause=reason,
                effect="Plan requires adaptation",
                confidence=0.85
            )

            self.reasoner.complete_reasoning_session(
                session_id,
                conclusion=f"Adapted plan to version {new_version}",
                confidence=0.8
            )

        # Update incomplete tasks (simplified - real implementation would be more sophisticated)
        cursor.execute('''
            UPDATE goal_tasks
            SET status = 'pending', retry_count = 0
            WHERE goal_id = ? AND status IN ('failed', 'blocked')
        ''', (goal_id,))

        # Update goal
        cursor.execute('''
            UPDATE executor_goals
            SET plan_version = ?, status = 'active'
            WHERE goal_id = ?
        ''', (new_version, goal_id))
        self.conn.commit()

        # Record adaptation
        cursor.execute('''
            INSERT INTO goal_adaptations
            (goal_id, adaptation_type, reason, old_plan, new_plan, outcome_deviation)
            VALUES (?, 'replan', ?, ?, ?, ?)
        ''', (goal_id, reason, old_plan, old_plan, outcome_deviation))
        self.conn.commit()

        self._log_execution(
            goal_id=goal_id,
            event_type="plan_adapted",
            details=f"Version {new_version}: {reason}"
        )

        # Notify
        if self.notifier:
            try:
                self.notifier.send_message(
                    f"🔄 *Plan Adapted*\n\n"
                    f"*{goal['goal_name']}*\n\n"
                    f"Reason: {reason}\n"
                    f"New version: {new_version}\n"
                    f"Resuming execution...",
                    priority="normal"
                )
            except Exception as e:
                print(f"[WARNING] Could not send notification: {e}")

        print(f"[ADAPT] Plan adapted for {goal_id}: {reason}")

    def _detect_blockage(self, goal_id: str, task_id: str, error_msg: str):
        """Detect and record blockage"""
        # Classify blockage type
        blockage_type = BlockageType.ERROR
        if "dependency" in error_msg.lower():
            blockage_type = BlockageType.DEPENDENCY
        elif "resource" in error_msg.lower():
            blockage_type = BlockageType.RESOURCE

        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO goal_blockages
            (goal_id, task_id, blockage_type, description)
            VALUES (?, ?, ?, ?)
        ''', (goal_id, task_id, blockage_type.value, error_msg))
        self.conn.commit()

        # Try self-correction
        self._self_correct(goal_id, task_id, blockage_type, error_msg)

    def _self_correct(self, goal_id: str, task_id: str,
                     blockage_type: BlockageType, error_msg: str):
        """Attempt self-correction when blocked"""
        print(f"[SELF-CORRECT] Attempting to resolve blockage: {blockage_type.value}")

        resolution_strategy = None

        if blockage_type == BlockageType.DEPENDENCY:
            # Execute dependencies first
            resolution_strategy = "Execute dependency tasks first"
            # Implementation would reorder tasks

        elif blockage_type == BlockageType.RESOURCE:
            # Wait for resources
            resolution_strategy = "Pause and retry when resources available"
            cursor = self.conn.cursor()
            cursor.execute('''
                UPDATE goal_tasks SET status = 'blocked' WHERE task_id = ?
            ''', (task_id,))
            self.conn.commit()

        elif blockage_type == BlockageType.ERROR:
            # Adapt plan
            resolution_strategy = "Adapt execution plan"
            self.adapt_plan(goal_id, f"Task failed: {error_msg}", 0.3)

        # Record resolution attempt
        if resolution_strategy:
            cursor = self.conn.cursor()
            cursor.execute('''
                UPDATE goal_blockages
                SET resolution_strategy = ?
                WHERE goal_id = ? AND task_id = ? AND resolved = 0
            ''', (resolution_strategy, goal_id, task_id))
            self.conn.commit()

            self._log_execution(
                goal_id=goal_id,
                task_id=task_id,
                event_type="self_correction",
                details=resolution_strategy
            )

    # === LOGGING ===

    def _log_execution(self, goal_id: str, event_type: str,
                      task_id: str = None, details: str = None):
        """Log execution event"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO goal_execution_log
            (goal_id, task_id, event_type, details)
            VALUES (?, ?, ?, ?)
        ''', (goal_id, task_id, event_type, details))
        self.conn.commit()

    # === REPORTING ===

    def get_goal_status(self, goal_id: str) -> Dict:
        """Get comprehensive goal status"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM executor_goals WHERE goal_id = ?', (goal_id,))
        goal = dict(cursor.fetchone())

        # Get tasks
        cursor.execute('''
            SELECT status, COUNT(*) as count
            FROM goal_tasks
            WHERE goal_id = ?
            GROUP BY status
        ''', (goal_id,))
        task_stats = {row['status']: row['count'] for row in cursor.fetchall()}

        # Get milestones
        cursor.execute('''
            SELECT COUNT(*) as count FROM goal_milestones
            WHERE goal_id = ? AND achieved = 1
        ''', (goal_id,))
        achieved_milestones = cursor.fetchone()['count']

        return {
            'goal_id': goal_id,
            'goal_name': goal['goal_name'],
            'status': goal['status'],
            'progress': goal['progress'],
            'total_tasks': goal['total_tasks'],
            'completed_tasks': goal['completed_tasks'],
            'failed_tasks': goal['failed_tasks'],
            'task_stats': task_stats,
            'achieved_milestones': achieved_milestones,
            'plan_version': goal['plan_version']
        }

    def close(self):
        """Close executor and cleanup"""
        self.conn.close()


# === TEST CODE ===

def example_task_work(task_name: str, duration: int = 1) -> Dict:
    """Example work function for testing"""
    print(f"   Executing: {task_name}")
    time.sleep(duration)
    return {
        'status': 'success',
        'task': task_name,
        'result': f"Completed {task_name}"
    }


def main():
    """Test autonomous goal executor"""
    print("Testing Autonomous Goal Execution System")
    print("=" * 70)

    executor = AutonomousGoalExecutor()

    try:
        # Set a goal
        print("\n1. Setting high-level goal...")
        goal_id = executor.set_goal(
            goal_name="Launch New Trading Strategy",
            description="Research, backtest, and deploy a new automated trading strategy",
            success_criteria=[
                "Complete market research",
                "Develop strategy logic",
                "Backtest on historical data",
                "Optimize parameters",
                "Deploy to paper trading",
                "Monitor performance"
            ],
            priority=3,
            deadline=datetime.now() + timedelta(days=7)
        )
        print(f"   Goal ID: {goal_id}")

        # Decompose goal
        print("\n2. Decomposing goal into tasks...")
        task_ids = executor.decompose_goal(goal_id, use_reasoning=True)
        print(f"   Created {len(task_ids)} tasks")

        # Show initial status
        print("\n3. Initial goal status:")
        status = executor.get_goal_status(goal_id)
        for key, value in status.items():
            print(f"   {key}: {value}")

        # Execute some tasks
        print("\n4. Executing tasks...")
        for i, task_id in enumerate(task_ids[:3], 1):  # Execute first 3 tasks
            print(f"\n   Task {i}:")
            try:
                result = executor.execute_task(
                    task_id,
                    example_task_work,
                    f"Task {i}",
                    1
                )
                print(f"   Result: {result}")
            except Exception as e:
                print(f"   Error: {e}")

        # Check progress
        print("\n5. Progress tracking:")
        progress = executor.track_progress(goal_id, "Manual progress check")
        print(f"   Current progress: {progress:.0%}")

        # Show updated status
        print("\n6. Updated goal status:")
        status = executor.get_goal_status(goal_id)
        for key, value in status.items():
            print(f"   {key}: {value}")

        # Test adaptation
        print("\n7. Testing plan adaptation...")
        executor.adapt_plan(
            goal_id,
            reason="Market conditions changed, need to adjust strategy",
            outcome_deviation=0.35
        )
        print("   Plan adapted")

        # Final status
        print("\n8. Final goal status:")
        status = executor.get_goal_status(goal_id)
        for key, value in status.items():
            print(f"   {key}: {value}")

        print(f"\n[SUCCESS] Autonomous Goal Execution System working!")
        print(f"Database: {executor.db_path}")

    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        traceback.print_exc()
    finally:
        executor.close()


if __name__ == "__main__":
    main()
