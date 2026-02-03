#!/usr/bin/env python3
"""
Multi-Agent Coordinator - Orchestrate multiple agents working together

This system coordinates:
- Agent spawning and lifecycle management
- Task decomposition into sub-tasks
- Work coordination across agents
- Result merging and synthesis
- Parallel execution management
- Hierarchical control structures
"""

import sqlite3
import json
import time
import threading
import queue
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import traceback
import uuid


class AgentRole(Enum):
    """Roles that agents can take"""
    COORDINATOR = "coordinator"
    WORKER = "worker"
    SPECIALIST = "specialist"
    VALIDATOR = "validator"
    AGGREGATOR = "aggregator"


class TaskStatus(Enum):
    """Status of tasks in the system"""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    MERGED = "merged"


class AgentStatus(Enum):
    """Status of agents"""
    IDLE = "idle"
    BUSY = "busy"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class MultiAgentCoordinator:
    """
    Coordinate multiple agents working on decomposed tasks

    Features:
    - Spawn and manage multiple agents
    - Decompose complex tasks into sub-tasks
    - Assign work based on agent capabilities
    - Monitor agent progress
    - Merge results from multiple agents
    - Support parallel and hierarchical execution
    - Handle agent failures and recovery
    """

    def __init__(self, db_path: str = None, max_agents: int = 10):
        if db_path is None:
            workspace = Path(__file__).parent.parent
            db_path = workspace / "memory.db"

        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

        # Configuration
        self.max_agents = max_agents
        self.agents = {}  # agent_id -> agent info
        self.task_queue = queue.PriorityQueue()
        self.result_queue = queue.Queue()

        # Coordination
        self.coordinator_active = False
        self.coordinator_thread = None
        self.lock = threading.Lock()

        # Load Telegram notifier
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from telegram_notifier import TelegramNotifier
            self.notifier = TelegramNotifier()
        except Exception as e:
            print(f"[WARNING] Could not load Telegram notifier: {e}")
            self.notifier = None

        # Load persistent memory
        try:
            from core.persistent_memory import PersistentMemory
            self.memory = PersistentMemory(db_path=db_path)
        except Exception as e:
            print(f"[WARNING] Could not load persistent memory: {e}")
            self.memory = None

    def _init_db(self):
        """Initialize database schema"""
        cursor = self.conn.cursor()

        # Agents registry
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT UNIQUE NOT NULL,
                agent_name TEXT NOT NULL,
                role TEXT NOT NULL,
                capabilities TEXT,
                status TEXT DEFAULT 'idle',
                current_task_id TEXT,
                tasks_completed INTEGER DEFAULT 0,
                tasks_failed INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP,
                metadata TEXT
            )
        ''')

        # Master tasks (top-level)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS master_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT UNIQUE NOT NULL,
                task_name TEXT NOT NULL,
                description TEXT,
                total_subtasks INTEGER DEFAULT 0,
                completed_subtasks INTEGER DEFAULT 0,
                failed_subtasks INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                priority INTEGER DEFAULT 2,
                result TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                metadata TEXT
            )
        ''')

        # Sub-tasks (decomposed)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subtasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subtask_id TEXT UNIQUE NOT NULL,
                master_task_id TEXT NOT NULL,
                subtask_name TEXT NOT NULL,
                description TEXT,
                assigned_agent_id TEXT,
                status TEXT DEFAULT 'pending',
                priority INTEGER DEFAULT 2,
                dependencies TEXT,
                result TEXT,
                error TEXT,
                assigned_at TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                metadata TEXT,
                FOREIGN KEY (master_task_id) REFERENCES master_tasks(task_id)
            )
        ''')

        # Coordination events log
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS coordination_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                agent_id TEXT,
                task_id TEXT,
                details TEXT,
                logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Result merging records
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS result_merges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                master_task_id TEXT NOT NULL,
                subtask_results TEXT,
                merged_result TEXT,
                merge_strategy TEXT,
                confidence REAL,
                merged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (master_task_id) REFERENCES master_tasks(task_id)
            )
        ''')

        self.conn.commit()

    # === AGENT MANAGEMENT ===

    def spawn_agent(self, agent_name: str, role: AgentRole,
                   capabilities: List[str] = None, metadata: Dict = None) -> str:
        """Spawn a new agent"""
        agent_id = f"agent_{uuid.uuid4().hex[:8]}"

        with self.lock:
            if len(self.agents) >= self.max_agents:
                raise ValueError(f"Maximum number of agents ({self.max_agents}) reached")

            # Register in database
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO agents
                (agent_id, agent_name, role, capabilities, status, metadata)
                VALUES (?, ?, ?, ?, 'idle', ?)
            ''', (agent_id, agent_name, role.value,
                  json.dumps(capabilities) if capabilities else None,
                  json.dumps(metadata) if metadata else None))
            self.conn.commit()

            # Add to active agents
            self.agents[agent_id] = {
                'name': agent_name,
                'role': role,
                'capabilities': capabilities or [],
                'status': AgentStatus.IDLE,
                'current_task': None,
                'thread': None
            }

            self._log_coordination(
                event_type="agent_spawned",
                agent_id=agent_id,
                details=f"Spawned {role.value} agent: {agent_name}"
            )

        print(f"[COORDINATOR] Spawned agent {agent_id} ({agent_name}) with role {role.value}")
        return agent_id

    def stop_agent(self, agent_id: str):
        """Stop an agent"""
        with self.lock:
            if agent_id not in self.agents:
                raise ValueError(f"Agent {agent_id} not found")

            agent = self.agents[agent_id]
            agent['status'] = AgentStatus.STOPPED

            # Update database
            cursor = self.conn.cursor()
            cursor.execute('''
                UPDATE agents SET status = 'stopped' WHERE agent_id = ?
            ''', (agent_id,))
            self.conn.commit()

            # Remove from active agents
            del self.agents[agent_id]

            self._log_coordination(
                event_type="agent_stopped",
                agent_id=agent_id,
                details=f"Stopped agent: {agent['name']}"
            )

        print(f"[COORDINATOR] Stopped agent {agent_id}")

    def get_agent_status(self, agent_id: str) -> Dict:
        """Get status of an agent"""
        with self.lock:
            if agent_id not in self.agents:
                raise ValueError(f"Agent {agent_id} not found")
            return dict(self.agents[agent_id])

    def get_all_agents(self) -> List[Dict]:
        """Get all active agents"""
        with self.lock:
            return [
                {'agent_id': aid, **info}
                for aid, info in self.agents.items()
            ]

    def get_available_agents(self, required_capability: str = None) -> List[str]:
        """Get agents available for work"""
        available = []
        with self.lock:
            for agent_id, agent in self.agents.items():
                if agent['status'] == AgentStatus.IDLE:
                    if required_capability is None or required_capability in agent['capabilities']:
                        available.append(agent_id)
        return available

    # === TASK DECOMPOSITION ===

    def decompose_task(self, task_name: str, description: str,
                      decomposition_strategy: str = "sequential",
                      priority: int = 2, metadata: Dict = None) -> str:
        """Decompose a complex task into sub-tasks"""
        master_task_id = f"task_{uuid.uuid4().hex[:8]}"

        # Create master task
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO master_tasks
            (task_id, task_name, description, priority, metadata)
            VALUES (?, ?, ?, ?, ?)
        ''', (master_task_id, task_name, description, priority,
              json.dumps(metadata) if metadata else None))
        self.conn.commit()

        self._log_coordination(
            event_type="task_decomposition",
            task_id=master_task_id,
            details=f"Created master task: {task_name}"
        )

        print(f"[COORDINATOR] Created master task {master_task_id}: {task_name}")
        return master_task_id

    def add_subtask(self, master_task_id: str, subtask_name: str,
                   description: str, priority: int = 2,
                   dependencies: List[str] = None, metadata: Dict = None) -> str:
        """Add a sub-task to a master task"""
        subtask_id = f"subtask_{uuid.uuid4().hex[:8]}"

        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO subtasks
            (subtask_id, master_task_id, subtask_name, description, priority,
             dependencies, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (subtask_id, master_task_id, subtask_name, description, priority,
              json.dumps(dependencies) if dependencies else None,
              json.dumps(metadata) if metadata else None))

        # Update master task subtask count
        cursor.execute('''
            UPDATE master_tasks
            SET total_subtasks = total_subtasks + 1
            WHERE task_id = ?
        ''', (master_task_id,))

        self.conn.commit()

        self._log_coordination(
            event_type="subtask_added",
            task_id=subtask_id,
            details=f"Added subtask to {master_task_id}: {subtask_name}"
        )

        # Add to task queue
        self.task_queue.put((priority, subtask_id))

        print(f"[COORDINATOR] Added subtask {subtask_id}: {subtask_name}")
        return subtask_id

    def get_master_task(self, master_task_id: str) -> Optional[Dict]:
        """Get master task details"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM master_tasks WHERE task_id = ?', (master_task_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_subtasks(self, master_task_id: str, status: str = None) -> List[Dict]:
        """Get sub-tasks for a master task"""
        cursor = self.conn.cursor()
        if status:
            cursor.execute('''
                SELECT * FROM subtasks
                WHERE master_task_id = ? AND status = ?
                ORDER BY priority DESC, id ASC
            ''', (master_task_id, status))
        else:
            cursor.execute('''
                SELECT * FROM subtasks
                WHERE master_task_id = ?
                ORDER BY priority DESC, id ASC
            ''', (master_task_id,))
        return [dict(row) for row in cursor.fetchall()]

    # === WORK COORDINATION ===

    def assign_task_to_agent(self, subtask_id: str, agent_id: str):
        """Assign a sub-task to an agent"""
        with self.lock:
            if agent_id not in self.agents:
                raise ValueError(f"Agent {agent_id} not found")

            if self.agents[agent_id]['status'] != AgentStatus.IDLE:
                raise ValueError(f"Agent {agent_id} is not idle")

            # Update subtask
            cursor = self.conn.cursor()
            cursor.execute('''
                UPDATE subtasks
                SET status = 'assigned', assigned_agent_id = ?,
                    assigned_at = CURRENT_TIMESTAMP
                WHERE subtask_id = ?
            ''', (agent_id, subtask_id))

            # Update agent
            cursor.execute('''
                UPDATE agents
                SET status = 'busy', current_task_id = ?,
                    last_active = CURRENT_TIMESTAMP
                WHERE agent_id = ?
            ''', (subtask_id, agent_id))

            self.conn.commit()

            # Update in-memory state
            self.agents[agent_id]['status'] = AgentStatus.BUSY
            self.agents[agent_id]['current_task'] = subtask_id

            self._log_coordination(
                event_type="task_assigned",
                agent_id=agent_id,
                task_id=subtask_id,
                details=f"Assigned subtask {subtask_id} to agent {agent_id}"
            )

        print(f"[COORDINATOR] Assigned {subtask_id} to {agent_id}")

    def execute_subtask(self, subtask_id: str, work_function: Callable,
                       *args, **kwargs) -> Any:
        """Execute a sub-task (called by agent)"""
        cursor = self.conn.cursor()

        # Update status to in_progress
        cursor.execute('''
            UPDATE subtasks
            SET status = 'in_progress', started_at = CURRENT_TIMESTAMP
            WHERE subtask_id = ?
        ''', (subtask_id,))
        self.conn.commit()

        try:
            # Execute work
            result = work_function(*args, **kwargs)

            # Mark as completed
            cursor.execute('''
                UPDATE subtasks
                SET status = 'completed', result = ?,
                    completed_at = CURRENT_TIMESTAMP
                WHERE subtask_id = ?
            ''', (json.dumps(result), subtask_id))

            # Update master task
            cursor.execute('''
                SELECT master_task_id FROM subtasks WHERE subtask_id = ?
            ''', (subtask_id,))
            master_task_id = cursor.fetchone()['master_task_id']

            cursor.execute('''
                UPDATE master_tasks
                SET completed_subtasks = completed_subtasks + 1
                WHERE task_id = ?
            ''', (master_task_id,))

            # Update agent
            cursor.execute('''
                SELECT assigned_agent_id FROM subtasks WHERE subtask_id = ?
            ''', (subtask_id,))
            agent_id = cursor.fetchone()['assigned_agent_id']

            if agent_id:
                cursor.execute('''
                    UPDATE agents
                    SET status = 'idle', current_task_id = NULL,
                        tasks_completed = tasks_completed + 1
                    WHERE agent_id = ?
                ''', (agent_id,))

                # Update in-memory state
                with self.lock:
                    if agent_id in self.agents:
                        self.agents[agent_id]['status'] = AgentStatus.IDLE
                        self.agents[agent_id]['current_task'] = None

            self.conn.commit()

            self._log_coordination(
                event_type="task_completed",
                agent_id=agent_id,
                task_id=subtask_id,
                details=f"Completed subtask {subtask_id}"
            )

            # Add to result queue
            self.result_queue.put({
                'subtask_id': subtask_id,
                'master_task_id': master_task_id,
                'result': result,
                'status': 'completed'
            })

            return result

        except Exception as e:
            # Mark as failed
            error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"

            cursor.execute('''
                UPDATE subtasks
                SET status = 'failed', error = ?,
                    completed_at = CURRENT_TIMESTAMP
                WHERE subtask_id = ?
            ''', (error_msg, subtask_id))

            # Update master task
            cursor.execute('''
                SELECT master_task_id FROM subtasks WHERE subtask_id = ?
            ''', (subtask_id,))
            master_task_id = cursor.fetchone()['master_task_id']

            cursor.execute('''
                UPDATE master_tasks
                SET failed_subtasks = failed_subtasks + 1
                WHERE task_id = ?
            ''', (master_task_id,))

            # Update agent
            cursor.execute('''
                SELECT assigned_agent_id FROM subtasks WHERE subtask_id = ?
            ''', (subtask_id,))
            agent_id = cursor.fetchone()['assigned_agent_id']

            if agent_id:
                cursor.execute('''
                    UPDATE agents
                    SET status = 'idle', current_task_id = NULL,
                        tasks_failed = tasks_failed + 1
                    WHERE agent_id = ?
                ''', (agent_id,))

                # Update in-memory state
                with self.lock:
                    if agent_id in self.agents:
                        self.agents[agent_id]['status'] = AgentStatus.IDLE
                        self.agents[agent_id]['current_task'] = None

            self.conn.commit()

            self._log_coordination(
                event_type="task_failed",
                agent_id=agent_id,
                task_id=subtask_id,
                details=f"Failed subtask {subtask_id}: {str(e)}"
            )

            # Add to result queue
            self.result_queue.put({
                'subtask_id': subtask_id,
                'master_task_id': master_task_id,
                'result': None,
                'error': error_msg,
                'status': 'failed'
            })

            raise

    # === RESULT MERGING ===

    def merge_results(self, master_task_id: str, merge_strategy: str = "concatenate",
                     merge_function: Callable = None) -> Any:
        """Merge results from all sub-tasks"""
        # Get all completed subtasks
        subtasks = self.get_subtasks(master_task_id, status="completed")

        if not subtasks:
            raise ValueError(f"No completed subtasks for {master_task_id}")

        # Extract results
        results = []
        for subtask in subtasks:
            if subtask['result']:
                results.append(json.loads(subtask['result']))

        # Merge based on strategy
        if merge_function:
            merged_result = merge_function(results)
        elif merge_strategy == "concatenate":
            merged_result = results
        elif merge_strategy == "sum":
            merged_result = sum(results) if all(isinstance(r, (int, float)) for r in results) else results
        elif merge_strategy == "average":
            if all(isinstance(r, (int, float)) for r in results):
                merged_result = sum(results) / len(results)
            else:
                merged_result = results
        elif merge_strategy == "majority_vote":
            if results:
                merged_result = max(set(results), key=results.count)
            else:
                merged_result = None
        else:
            merged_result = results

        # Store merge record
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO result_merges
            (master_task_id, subtask_results, merged_result, merge_strategy)
            VALUES (?, ?, ?, ?)
        ''', (master_task_id, json.dumps([s['subtask_id'] for s in subtasks]),
              json.dumps(merged_result), merge_strategy))

        # Update master task
        cursor.execute('''
            UPDATE master_tasks
            SET status = 'completed', result = ?,
                completed_at = CURRENT_TIMESTAMP
            WHERE task_id = ?
        ''', (json.dumps(merged_result), master_task_id))

        self.conn.commit()

        self._log_coordination(
            event_type="results_merged",
            task_id=master_task_id,
            details=f"Merged {len(subtasks)} results using {merge_strategy}"
        )

        # Notify if important
        if self.notifier:
            try:
                master_task = self.get_master_task(master_task_id)
                self.notifier.send_message(
                    f"Task Completed: {master_task['task_name']}\n"
                    f"Subtasks: {len(subtasks)} completed\n"
                    f"Result: {str(merged_result)[:100]}...",
                    priority="success"
                )
            except Exception as e:
                print(f"[WARNING] Could not send notification: {e}")

        print(f"[COORDINATOR] Merged results for {master_task_id}")
        return merged_result

    # === PARALLEL EXECUTION ===

    def execute_parallel(self, master_task_id: str, work_function: Callable,
                        auto_merge: bool = True, merge_strategy: str = "concatenate"):
        """Execute all sub-tasks in parallel"""
        subtasks = self.get_subtasks(master_task_id, status="pending")

        if not subtasks:
            print(f"[COORDINATOR] No pending subtasks for {master_task_id}")
            return

        print(f"[COORDINATOR] Executing {len(subtasks)} subtasks in parallel")

        threads = []
        for subtask in subtasks:
            # Get available agent
            available_agents = self.get_available_agents()
            if not available_agents:
                print(f"[COORDINATOR] No available agents, waiting...")
                time.sleep(1)
                available_agents = self.get_available_agents()

            if available_agents:
                agent_id = available_agents[0]
                self.assign_task_to_agent(subtask['subtask_id'], agent_id)

                # Execute in thread
                thread = threading.Thread(
                    target=self.execute_subtask,
                    args=(subtask['subtask_id'], work_function),
                    daemon=True
                )
                thread.start()
                threads.append(thread)

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Auto-merge if requested
        if auto_merge:
            return self.merge_results(master_task_id, merge_strategy=merge_strategy)

    # === HIERARCHICAL CONTROL ===

    def create_hierarchy(self, coordinator_name: str, num_workers: int,
                        worker_capabilities: List[str] = None) -> Dict:
        """Create a hierarchical agent structure"""
        # Spawn coordinator
        coordinator_id = self.spawn_agent(
            agent_name=coordinator_name,
            role=AgentRole.COORDINATOR,
            capabilities=["coordination", "task_decomposition"]
        )

        # Spawn workers
        worker_ids = []
        for i in range(num_workers):
            worker_id = self.spawn_agent(
                agent_name=f"{coordinator_name}_worker_{i+1}",
                role=AgentRole.WORKER,
                capabilities=worker_capabilities or ["general"]
            )
            worker_ids.append(worker_id)

        hierarchy = {
            'coordinator': coordinator_id,
            'workers': worker_ids,
            'size': num_workers + 1
        }

        self._log_coordination(
            event_type="hierarchy_created",
            agent_id=coordinator_id,
            details=f"Created hierarchy with 1 coordinator and {num_workers} workers"
        )

        print(f"[COORDINATOR] Created hierarchy: {hierarchy}")
        return hierarchy

    # === LOGGING ===

    def _log_coordination(self, event_type: str, agent_id: str = None,
                         task_id: str = None, details: str = None):
        """Log coordination event"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO coordination_log
            (event_type, agent_id, task_id, details)
            VALUES (?, ?, ?, ?)
        ''', (event_type, agent_id, task_id, details))
        self.conn.commit()

    def get_coordination_log(self, limit: int = 100) -> List[Dict]:
        """Get recent coordination log"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM coordination_log
            ORDER BY logged_at DESC
            LIMIT ?
        ''', (limit,))
        return [dict(row) for row in cursor.fetchall()]

    def get_stats(self) -> Dict:
        """Get coordinator statistics"""
        cursor = self.conn.cursor()

        # Active agents
        active_agents = len(self.agents)

        # Master tasks
        cursor.execute('SELECT COUNT(*) as count FROM master_tasks WHERE status != "completed"')
        active_tasks = cursor.fetchone()['count']

        # Subtasks
        cursor.execute('SELECT COUNT(*) as count FROM subtasks WHERE status = "pending"')
        pending_subtasks = cursor.fetchone()['count']

        cursor.execute('SELECT COUNT(*) as count FROM subtasks WHERE status = "in_progress"')
        in_progress_subtasks = cursor.fetchone()['count']

        cursor.execute('SELECT COUNT(*) as count FROM subtasks WHERE status = "completed"')
        completed_subtasks = cursor.fetchone()['count']

        # Agent utilization
        with self.lock:
            busy_agents = sum(1 for a in self.agents.values() if a['status'] == AgentStatus.BUSY)
            utilization = (busy_agents / active_agents * 100) if active_agents > 0 else 0

        return {
            'active_agents': active_agents,
            'busy_agents': busy_agents,
            'idle_agents': active_agents - busy_agents,
            'agent_utilization_pct': round(utilization, 1),
            'active_tasks': active_tasks,
            'pending_subtasks': pending_subtasks,
            'in_progress_subtasks': in_progress_subtasks,
            'completed_subtasks': completed_subtasks
        }

    def close(self):
        """Close coordinator and cleanup"""
        # Stop all agents
        agent_ids = list(self.agents.keys())
        for agent_id in agent_ids:
            try:
                self.stop_agent(agent_id)
            except Exception as e:
                print(f"[WARNING] Error stopping agent {agent_id}: {e}")

        self.conn.close()


# === TEST CODE ===

def example_work_function(task_id: str, work_amount: int) -> Dict:
    """Example work function for testing"""
    time.sleep(work_amount * 0.1)  # Simulate work
    return {
        'task_id': task_id,
        'result': work_amount * 10,
        'work_done': work_amount
    }


def main():
    """Test multi-agent coordinator"""
    print("Testing Multi-Agent Coordinator")
    print("=" * 70)

    coordinator = MultiAgentCoordinator(max_agents=5)

    try:
        # Create a hierarchy of agents
        print("\n1. Creating agent hierarchy...")
        hierarchy = coordinator.create_hierarchy(
            coordinator_name="MasterCoordinator",
            num_workers=3,
            worker_capabilities=["compute", "analysis"]
        )
        print(f"   Created hierarchy with {hierarchy['size']} agents")

        # Decompose a complex task
        print("\n2. Decomposing complex task...")
        master_task_id = coordinator.decompose_task(
            task_name="Process Large Dataset",
            description="Process a large dataset by splitting into chunks",
            priority=3
        )

        # Add sub-tasks
        subtasks = []
        for i in range(5):
            subtask_id = coordinator.add_subtask(
                master_task_id=master_task_id,
                subtask_name=f"Process chunk {i+1}",
                description=f"Process data chunk {i+1} of 5",
                priority=3,
                metadata={'chunk_id': i+1}
            )
            subtasks.append(subtask_id)

        print(f"   Added {len(subtasks)} subtasks")

        # Show agent status
        print("\n3. Agent status:")
        agents = coordinator.get_all_agents()
        for agent in agents:
            print(f"   {agent['agent_id']}: {agent['status'].value} ({agent['role'].value})")

        # Execute subtasks in parallel
        print("\n4. Executing subtasks in parallel...")

        # Manually assign and execute tasks
        for i, subtask_id in enumerate(subtasks):
            available_agents = coordinator.get_available_agents()
            if available_agents:
                agent_id = available_agents[0]
                coordinator.assign_task_to_agent(subtask_id, agent_id)

                # Execute in background
                def execute_task(st_id, work_amt):
                    try:
                        coordinator.execute_subtask(
                            st_id,
                            example_work_function,
                            st_id,
                            work_amt
                        )
                    except Exception as e:
                        print(f"   Task {st_id} failed: {e}")

                thread = threading.Thread(
                    target=execute_task,
                    args=(subtask_id, i+1),
                    daemon=True
                )
                thread.start()

        # Wait for completion
        print("   Waiting for tasks to complete...")
        time.sleep(3)

        # Check master task status
        print("\n5. Master task status:")
        master_task = coordinator.get_master_task(master_task_id)
        print(f"   Total subtasks: {master_task['total_subtasks']}")
        print(f"   Completed: {master_task['completed_subtasks']}")
        print(f"   Failed: {master_task['failed_subtasks']}")

        # Merge results
        print("\n6. Merging results...")
        try:
            merged = coordinator.merge_results(
                master_task_id,
                merge_strategy="concatenate"
            )
            print(f"   Merged result: {merged}")
        except Exception as e:
            print(f"   Could not merge (may still be in progress): {e}")

        # Get statistics
        print("\n7. Coordinator Statistics:")
        stats = coordinator.get_stats()
        for key, value in stats.items():
            print(f"   {key}: {value}")

        # Get coordination log
        print("\n8. Recent coordination events:")
        log = coordinator.get_coordination_log(limit=10)
        for entry in log[:5]:  # Show first 5
            print(f"   [{entry['event_type']}] {entry['details']}")

        print(f"\n✓ Multi-Agent Coordinator working!")
        print(f"Database: {coordinator.db_path}")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        traceback.print_exc()
    finally:
        coordinator.close()


if __name__ == "__main__":
    main()
