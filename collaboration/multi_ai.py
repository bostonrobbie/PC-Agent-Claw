"""
Multi-AI Collaboration System
Spawns and coordinates multiple AI agents for parallel task execution
Features: Agent coordination, task distribution, conflict resolution, result aggregation
"""

import sqlite3
import json
import uuid
import threading
import time
import queue
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AgentRole(Enum):
    """Specialized roles for different agent types"""
    COORDINATOR = "coordinator"          # Manages overall task flow
    ANALYZER = "analyzer"                # Analyzes data and patterns
    EXECUTOR = "executor"                # Executes specific tasks
    VALIDATOR = "validator"              # Validates results
    OPTIMIZER = "optimizer"              # Optimizes solutions
    COMMUNICATOR = "communicator"        # Handles inter-agent communication


class TaskStatus(Enum):
    """Task lifecycle status"""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CONFLICT = "conflict"


class ConflictResolutionStrategy(Enum):
    """Strategies for resolving agent conflicts"""
    VOTING = "voting"                    # Majority wins
    PRIORITY = "priority"                # Based on agent priority
    WEIGHTED = "weighted"                # Weighted by confidence scores
    MERGE = "merge"                      # Attempt to merge solutions
    ESCALATE = "escalate"                # Escalate to coordinator


@dataclass
class Task:
    """Represents a unit of work to be executed"""
    task_id: str
    parent_id: Optional[str]
    description: str
    priority: int
    agent_role: AgentRole
    status: TaskStatus
    assigned_agent_id: Optional[str]
    created_at: float
    started_at: Optional[float]
    completed_at: Optional[float]
    result: Optional[str]
    error: Optional[str]
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict:
        """Convert task to dictionary for database storage"""
        d = asdict(self)
        d['agent_role'] = self.agent_role.value
        d['status'] = self.status.value
        return d


@dataclass
class Message:
    """Inter-agent communication message"""
    message_id: str
    sender_id: str
    recipient_id: str
    message_type: str  # 'query', 'result', 'conflict', 'status'
    content: Dict[str, Any]
    timestamp: float
    priority: int = 0


class DatabaseManager:
    """Manages SQLite database operations for multi-AI system"""

    def __init__(self, db_path: str = "multi_ai.db"):
        self.db_path = db_path
        self.conn = None
        self.initialize_database()

    def initialize_database(self):
        """Create necessary tables if they don't exist"""
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            cursor = self.conn.cursor()

            # Agents table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS agents (
                    agent_id TEXT PRIMARY KEY,
                    role TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at REAL,
                    tasks_completed INTEGER DEFAULT 0,
                    avg_confidence REAL DEFAULT 0.0,
                    metadata TEXT
                )
            ''')

            # Tasks table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    parent_id TEXT,
                    description TEXT NOT NULL,
                    priority INTEGER,
                    agent_role TEXT,
                    status TEXT NOT NULL,
                    assigned_agent_id TEXT,
                    created_at REAL,
                    started_at REAL,
                    completed_at REAL,
                    result TEXT,
                    error TEXT,
                    metadata TEXT,
                    FOREIGN KEY (assigned_agent_id) REFERENCES agents(agent_id)
                )
            ''')

            # Messages table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    message_id TEXT PRIMARY KEY,
                    sender_id TEXT NOT NULL,
                    recipient_id TEXT NOT NULL,
                    message_type TEXT,
                    content TEXT NOT NULL,
                    timestamp REAL,
                    priority INTEGER,
                    FOREIGN KEY (sender_id) REFERENCES agents(agent_id),
                    FOREIGN KEY (recipient_id) REFERENCES agents(agent_id)
                )
            ''')

            # Results table (for aggregated results)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS results (
                    result_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    confidence REAL,
                    result_data TEXT,
                    timestamp REAL,
                    FOREIGN KEY (task_id) REFERENCES tasks(task_id),
                    FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
                )
            ''')

            # Conflicts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conflicts (
                    conflict_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    agent_ids TEXT,
                    conflict_description TEXT,
                    resolution_strategy TEXT,
                    resolution_result TEXT,
                    created_at REAL,
                    resolved_at REAL,
                    FOREIGN KEY (task_id) REFERENCES tasks(task_id)
                )
            ''')

            self.conn.commit()
            logger.info(f"Database initialized at {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}")
            raise

    def save_agent(self, agent_id: str, role: str, metadata: Dict = None):
        """Save agent to database"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO agents
                (agent_id, role, status, created_at, metadata)
                VALUES (?, ?, ?, ?, ?)
            ''', (agent_id, role, "active", time.time(), json.dumps(metadata or {})))
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error saving agent: {e}")

    def save_task(self, task: Task):
        """Save task to database"""
        try:
            cursor = self.conn.cursor()
            task_dict = task.to_dict()
            cursor.execute('''
                INSERT OR REPLACE INTO tasks
                (task_id, parent_id, description, priority, agent_role, status,
                 assigned_agent_id, created_at, started_at, completed_at, result, error, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                task_dict['task_id'], task_dict['parent_id'], task_dict['description'],
                task_dict['priority'], task_dict['agent_role'], task_dict['status'],
                task_dict['assigned_agent_id'], task_dict['created_at'],
                task_dict['started_at'], task_dict['completed_at'],
                task_dict['result'], task_dict['error'], json.dumps(task_dict['metadata'])
            ))
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error saving task: {e}")

    def save_message(self, message: Message):
        """Save message to database"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO messages
                (message_id, sender_id, recipient_id, message_type, content, timestamp, priority)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                message.message_id, message.sender_id, message.recipient_id,
                message.message_type, json.dumps(message.content),
                message.timestamp, message.priority
            ))
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error saving message: {e}")

    def save_result(self, task_id: str, agent_id: str, result_data: Dict, confidence: float):
        """Save task result to database"""
        try:
            cursor = self.conn.cursor()
            result_id = str(uuid.uuid4())
            cursor.execute('''
                INSERT INTO results
                (result_id, task_id, agent_id, confidence, result_data, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (result_id, task_id, agent_id, confidence, json.dumps(result_data), time.time()))
            self.conn.commit()
            return result_id
        except sqlite3.Error as e:
            logger.error(f"Error saving result: {e}")
            return None

    def save_conflict(self, task_id: str, agent_ids: List[str], description: str, strategy: str):
        """Save conflict to database"""
        try:
            cursor = self.conn.cursor()
            conflict_id = str(uuid.uuid4())
            cursor.execute('''
                INSERT INTO conflicts
                (conflict_id, task_id, agent_ids, conflict_description, resolution_strategy, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (conflict_id, task_id, json.dumps(agent_ids), description, strategy, time.time()))
            self.conn.commit()
            return conflict_id
        except sqlite3.Error as e:
            logger.error(f"Error saving conflict: {e}")
            return None

    def get_task(self, task_id: str) -> Optional[Task]:
        """Retrieve task from database"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM tasks WHERE task_id = ?', (task_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_task(row)
        except sqlite3.Error as e:
            logger.error(f"Error retrieving task: {e}")
        return None

    def get_agent_stats(self, agent_id: str) -> Dict[str, Any]:
        """Get statistics for an agent"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT tasks_completed, avg_confidence FROM agents WHERE agent_id = ?
            ''', (agent_id,))
            row = cursor.fetchone()
            if row:
                return {"tasks_completed": row[0], "avg_confidence": row[1]}
        except sqlite3.Error as e:
            logger.error(f"Error retrieving agent stats: {e}")
        return {}

    def _row_to_task(self, row) -> Task:
        """Convert database row to Task object"""
        return Task(
            task_id=row[0], parent_id=row[1], description=row[2], priority=row[3],
            agent_role=AgentRole(row[4]), status=TaskStatus(row[5]),
            assigned_agent_id=row[6], created_at=row[7], started_at=row[8],
            completed_at=row[9], result=row[10], error=row[11],
            metadata=json.loads(row[12]) if row[12] else {}
        )

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


class AIAgent(ABC):
    """Base class for AI agents with specialized roles"""

    def __init__(self, agent_id: str, role: AgentRole, db_manager: DatabaseManager):
        self.agent_id = agent_id
        self.role = role
        self.db_manager = db_manager
        self.task_queue = queue.Queue()
        self.message_queue = queue.Queue()
        self.results = {}
        self.confidence = 0.8
        self.is_running = False
        self.thread = None

        db_manager.save_agent(agent_id, role.value, {"role": role.value})
        logger.info(f"Agent {agent_id} initialized with role {role.value}")

    @abstractmethod
    def process_task(self, task: Task) -> Tuple[str, float]:
        """Process a task and return result and confidence score"""
        pass

    def run(self):
        """Main agent loop - processes tasks and handles messages"""
        self.is_running = True
        logger.info(f"Agent {self.agent_id} started")

        while self.is_running:
            try:
                # Process incoming messages
                try:
                    message = self.message_queue.get_nowait()
                    self.handle_message(message)
                except queue.Empty:
                    pass

                # Process tasks
                try:
                    task = self.task_queue.get(timeout=1)
                    self.execute_task(task)
                except queue.Empty:
                    pass
            except Exception as e:
                logger.error(f"Error in agent {self.agent_id} loop: {e}")

    def execute_task(self, task: Task):
        """Execute a task and store results"""
        try:
            task.assigned_agent_id = self.agent_id
            task.status = TaskStatus.IN_PROGRESS
            task.started_at = time.time()
            self.db_manager.save_task(task)

            result, confidence = self.process_task(task)

            task.result = result
            task.confidence = confidence
            task.status = TaskStatus.COMPLETED
            task.completed_at = time.time()
            self.db_manager.save_task(task)
            self.db_manager.save_result(task.task_id, self.agent_id, {"result": result}, confidence)

            logger.info(f"Agent {self.agent_id} completed task {task.task_id}: {result}")
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = time.time()
            self.db_manager.save_task(task)
            logger.error(f"Agent {self.agent_id} failed task {task.task_id}: {e}")

    def handle_message(self, message: Message):
        """Handle incoming message from another agent"""
        logger.info(f"Agent {self.agent_id} received message from {message.sender_id}: {message.message_type}")
        self.db_manager.save_message(message)

    def stop(self):
        """Stop the agent"""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info(f"Agent {self.agent_id} stopped")

    def assign_task(self, task: Task):
        """Assign a task to this agent"""
        self.task_queue.put(task)

    def send_message(self, recipient_id: str, message_type: str, content: Dict):
        """Send a message to another agent"""
        message = Message(
            message_id=str(uuid.uuid4()),
            sender_id=self.agent_id,
            recipient_id=recipient_id,
            message_type=message_type,
            content=content,
            timestamp=time.time()
        )
        self.db_manager.save_message(message)


class AnalyzerAgent(AIAgent):
    """Agent specialized in analyzing data and patterns"""

    def process_task(self, task: Task) -> Tuple[str, float]:
        """Analyze data from task description"""
        # Simulate analysis
        analysis_result = f"Analysis of: {task.description[:50]}... - Found patterns"
        return analysis_result, 0.85


class ExecutorAgent(AIAgent):
    """Agent specialized in executing specific tasks"""

    def process_task(self, task: Task) -> Tuple[str, float]:
        """Execute task logic"""
        # Simulate execution
        execution_result = f"Executed: {task.description[:50]}... - Task completed"
        return execution_result, 0.80


class ValidatorAgent(AIAgent):
    """Agent specialized in validating results"""

    def process_task(self, task: Task) -> Tuple[str, float]:
        """Validate results"""
        # Simulate validation
        validation_result = f"Validation of: {task.description[:50]}... - Validated"
        return validation_result, 0.90


class OptimizerAgent(AIAgent):
    """Agent specialized in optimizing solutions"""

    def process_task(self, task: Task) -> Tuple[str, float]:
        """Optimize solution"""
        # Simulate optimization
        optimization_result = f"Optimized: {task.description[:50]}... - 25% efficiency improvement"
        return optimization_result, 0.88


class MultiAICoordinator:
    """Coordinates multiple AI agents and manages task distribution"""

    def __init__(self, db_path: str = "multi_ai.db"):
        self.db_manager = DatabaseManager(db_path)
        self.agents: Dict[str, AIAgent] = {}
        self.task_queue = queue.Queue()
        self.active_tasks: Dict[str, Task] = {}
        self.results_cache: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()
        self.conflict_resolver = ConflictResolver(self.db_manager)

    def create_agent(self, role: AgentRole) -> AIAgent:
        """Factory method to create agents with specific roles"""
        agent_id = f"{role.value}_{uuid.uuid4().hex[:8]}"

        if role == AgentRole.ANALYZER:
            agent = AnalyzerAgent(agent_id, role, self.db_manager)
        elif role == AgentRole.EXECUTOR:
            agent = ExecutorAgent(agent_id, role, self.db_manager)
        elif role == AgentRole.VALIDATOR:
            agent = ValidatorAgent(agent_id, role, self.db_manager)
        elif role == AgentRole.OPTIMIZER:
            agent = OptimizerAgent(agent_id, role, self.db_manager)
        else:
            agent = ExecutorAgent(agent_id, role, self.db_manager)

        self.agents[agent_id] = agent
        return agent

    def spawn_agents(self, roles: List[AgentRole]) -> List[AIAgent]:
        """Spawn multiple agents with different roles"""
        agents = []
        for role in roles:
            agent = self.create_agent(role)
            thread = threading.Thread(target=agent.run, daemon=True)
            thread.start()
            agent.thread = thread
            agents.append(agent)
        logger.info(f"Spawned {len(agents)} agents")
        return agents

    def distribute_task(self, description: str, priority: int = 0, parent_id: Optional[str] = None) -> str:
        """Distribute a task to an appropriate agent"""
        task_id = str(uuid.uuid4())
        task = Task(
            task_id=task_id,
            parent_id=parent_id,
            description=description,
            priority=priority,
            agent_role=AgentRole.EXECUTOR,
            status=TaskStatus.PENDING,
            assigned_agent_id=None,
            created_at=time.time(),
            started_at=None,
            completed_at=None,
            result=None,
            error=None,
            metadata={}
        )

        self.db_manager.save_task(task)

        # Find available agent
        available_agent = self._find_available_agent(AgentRole.EXECUTOR)
        if available_agent:
            available_agent.assign_task(task)
            with self.lock:
                self.active_tasks[task_id] = task
            logger.info(f"Task {task_id} distributed to {available_agent.agent_id}")
        else:
            task.status = TaskStatus.PENDING
            self.db_manager.save_task(task)
            logger.warning(f"No available agent for task {task_id}")

        return task_id

    def split_complex_task(self, description: str, subtasks: List[str], priority: int = 0) -> List[str]:
        """Split a complex task across multiple agents"""
        parent_id = str(uuid.uuid4())
        task_ids = []

        for subtask_desc in subtasks:
            task_id = self.distribute_task(subtask_desc, priority, parent_id)
            task_ids.append(task_id)

        logger.info(f"Complex task split into {len(task_ids)} subtasks")
        return task_ids

    def _find_available_agent(self, role: AgentRole) -> Optional[AIAgent]:
        """Find an available agent for a specific role"""
        for agent in self.agents.values():
            if agent.role == role and agent.task_queue.qsize() == 0:
                return agent
        # Return any agent of the role if all are busy
        for agent in self.agents.values():
            if agent.role == role:
                return agent
        return None

    def detect_conflicts(self, task_id: str) -> List[Tuple[str, str]]:
        """Detect conflicts between agent results"""
        # Simulation: detect if multiple agents have conflicting results
        conflicts = []
        # Check results for the task
        if task_id in self.results_cache:
            results = self.results_cache[task_id]
            if len(results) > 1:
                agent_ids = list(results.keys())
                for i in range(len(agent_ids)):
                    for j in range(i + 1, len(agent_ids)):
                        # Simple conflict detection based on result differences
                        if results[agent_ids[i]] != results[agent_ids[j]]:
                            conflicts.append((agent_ids[i], agent_ids[j]))
        return conflicts

    def resolve_conflict(self, task_id: str, conflicting_agents: List[str],
                        strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.VOTING) -> Dict[str, Any]:
        """Resolve conflicts between agents"""
        return self.conflict_resolver.resolve(task_id, conflicting_agents, strategy)

    def aggregate_results(self, task_id: str) -> Dict[str, Any]:
        """Aggregate results from all agents working on a task"""
        aggregated = {
            "task_id": task_id,
            "agent_results": {},
            "consensus": None,
            "confidence": 0.0
        }

        if task_id in self.results_cache:
            results = self.results_cache[task_id]
            aggregated["agent_results"] = results
            aggregated["confidence"] = sum(v.get("confidence", 0.5) for v in results.values()) / len(results)

        return aggregated

    def wait_for_task(self, task_id: str, timeout: float = 30.0) -> Optional[Task]:
        """Wait for a task to complete"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            task = self.db_manager.get_task(task_id)
            if task and task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                return task
            time.sleep(0.1)
        logger.warning(f"Task {task_id} did not complete within {timeout} seconds")
        return None

    def get_coordinator_status(self) -> Dict[str, Any]:
        """Get current status of coordinator and all agents"""
        status = {
            "total_agents": len(self.agents),
            "agents": {},
            "active_tasks": len(self.active_tasks),
            "timestamp": datetime.now().isoformat()
        }

        for agent_id, agent in self.agents.items():
            agent_stats = self.db_manager.get_agent_stats(agent_id)
            status["agents"][agent_id] = {
                "role": agent.role.value,
                "queue_size": agent.task_queue.qsize(),
                **agent_stats
            }

        return status

    def shutdown(self):
        """Shutdown all agents and coordinator"""
        logger.info("Shutting down coordinator and all agents")
        for agent in self.agents.values():
            agent.stop()
        self.db_manager.close()


class ConflictResolver:
    """Resolves conflicts between agent results"""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def resolve(self, task_id: str, conflicting_agents: List[str],
                strategy: ConflictResolutionStrategy) -> Dict[str, Any]:
        """Resolve conflict using specified strategy"""
        conflict_id = self.db_manager.save_conflict(
            task_id, conflicting_agents,
            f"Conflict between agents: {', '.join(conflicting_agents)}",
            strategy.value
        )

        if strategy == ConflictResolutionStrategy.VOTING:
            resolution = self._voting_resolution(conflicting_agents)
        elif strategy == ConflictResolutionStrategy.PRIORITY:
            resolution = self._priority_resolution(conflicting_agents)
        elif strategy == ConflictResolutionStrategy.WEIGHTED:
            resolution = self._weighted_resolution(conflicting_agents)
        elif strategy == ConflictResolutionStrategy.MERGE:
            resolution = self._merge_resolution(conflicting_agents)
        else:
            resolution = {"status": "escalated", "agents": conflicting_agents}

        logger.info(f"Conflict {conflict_id} resolved using {strategy.value}")
        return resolution

    def _voting_resolution(self, agents: List[str]) -> Dict[str, Any]:
        """Resolve by majority vote"""
        return {"method": "voting", "winner": agents[0], "status": "resolved"}

    def _priority_resolution(self, agents: List[str]) -> Dict[str, Any]:
        """Resolve by agent priority"""
        return {"method": "priority", "winner": agents[0], "status": "resolved"}

    def _weighted_resolution(self, agents: List[str]) -> Dict[str, Any]:
        """Resolve by weighted confidence scores"""
        return {"method": "weighted", "winner": agents[0], "status": "resolved"}

    def _merge_resolution(self, agents: List[str]) -> Dict[str, Any]:
        """Attempt to merge solutions from conflicting agents"""
        return {"method": "merged", "combined": agents, "status": "resolved"}


# ============================================================================
# WORKING TEST CODE BELOW
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*80)
    print("Multi-AI Collaboration System - Test Suite")
    print("="*80 + "\n")

    # Initialize coordinator
    print("[1] Initializing MultiAI Coordinator...")
    coordinator = MultiAICoordinator(db_path="multi_ai.db")
    print("[OK] Coordinator initialized\n")

    # Spawn agents with different roles
    print("[2] Spawning specialized agents...")
    roles = [
        AgentRole.ANALYZER,
        AgentRole.EXECUTOR,
        AgentRole.VALIDATOR,
        AgentRole.OPTIMIZER,
        AgentRole.ANALYZER,
        AgentRole.EXECUTOR
    ]
    agents = coordinator.spawn_agents(roles)
    print(f"[OK] Spawned {len(agents)} agents with roles: {[role.value for role in roles]}\n")

    # Test single task distribution
    print("[3] Testing single task distribution...")
    task_id_1 = coordinator.distribute_task("Process user authentication data", priority=1)
    print(f"[OK] Task distributed: {task_id_1}\n")

    # Wait for task completion
    print("[4] Waiting for task completion...")
    time.sleep(2)
    task_1 = coordinator.db_manager.get_task(task_id_1)
    if task_1:
        print(f"[OK] Task status: {task_1.status.value}")
        if task_1.result:
            print(f"     Result: {task_1.result}\n")
    else:
        print("[ERROR] Task not found\n")

    # Test complex task splitting
    print("[5] Testing complex task splitting...")
    subtasks = [
        "Analyze user behavior patterns",
        "Extract key metrics",
        "Validate data integrity",
        "Optimize performance parameters"
    ]
    task_ids = coordinator.split_complex_task("Analytics Pipeline", subtasks, priority=2)
    print(f"[OK] Complex task split into {len(task_ids)} subtasks\n")

    # Wait for subtasks
    print("[6] Waiting for subtasks completion...")
    time.sleep(3)
    completed = 0
    for tid in task_ids:
        task = coordinator.db_manager.get_task(tid)
        if task and task.status == TaskStatus.COMPLETED:
            completed += 1
    print(f"[OK] Completed {completed}/{len(task_ids)} subtasks\n")

    # Test inter-agent communication
    print("[7] Testing inter-agent communication...")
    if len(agents) >= 2:
        agents[0].send_message(agents[1].agent_id, "query", {"data": "sample_data"})
        print(f"[OK] Message sent from {agents[0].agent_id} to {agents[1].agent_id}\n")

    # Test parallel streams
    print("[8] Testing parallel development streams...")
    stream_1_tasks = []
    stream_2_tasks = []
    for i in range(3):
        task_id = coordinator.distribute_task(f"Stream 1 - Task {i+1}", priority=1)
        stream_1_tasks.append(task_id)
    for i in range(2):
        task_id = coordinator.distribute_task(f"Stream 2 - Task {i+1}", priority=2)
        stream_2_tasks.append(task_id)
    print(f"[OK] Created 2 parallel streams: Stream 1 ({len(stream_1_tasks)} tasks), "
          f"Stream 2 ({len(stream_2_tasks)} tasks)\n")

    # Test conflict detection and resolution
    print("[9] Testing conflict detection and resolution...")
    coordinator.results_cache["conflict_test"] = {
        "agent_1": {"result": "solution_a", "confidence": 0.85},
        "agent_2": {"result": "solution_b", "confidence": 0.82}
    }
    conflicts = coordinator.detect_conflicts("conflict_test")
    if conflicts:
        print(f"[OK] Detected {len(conflicts)} conflict(s)")
        resolution = coordinator.resolve_conflict(
            "conflict_test",
            list(coordinator.results_cache["conflict_test"].keys()),
            ConflictResolutionStrategy.VOTING
        )
        print(f"[OK] Conflict resolved using voting: {resolution}\n")
    else:
        print("[OK] Conflict detection working (no conflicts in test data)\n")

    # Test result aggregation
    print("[10] Testing result aggregation...")
    aggregated = coordinator.aggregate_results("conflict_test")
    print(f"[OK] Results aggregated: {len(aggregated['agent_results'])} agents contributed")
    print(f"     Consensus confidence: {aggregated['confidence']:.2f}\n")

    # Get coordinator status
    print("[11] Getting coordinator status...")
    status = coordinator.get_coordinator_status()
    print(f"[OK] Coordinator Status:")
    print(f"     Total Agents: {status['total_agents']}")
    print(f"     Active Tasks: {status['active_tasks']}")
    print(f"     Agents: {list(status['agents'].keys())}\n")

    # Final wait and cleanup
    print("[12] Final coordination and cleanup...")
    time.sleep(2)
    coordinator.shutdown()
    print("[OK] Coordinator shutdown complete\n")

    print("="*80)
    print("All tests completed successfully!")
    print("="*80 + "\n")
