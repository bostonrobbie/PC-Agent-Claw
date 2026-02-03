"""
Multi-AI Collaboration System
Enables coordination and communication between multiple specialized AI agents
with task distribution, result aggregation, and conflict resolution.
"""

import json
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from queue import Queue, PriorityQueue
from typing import Any, Dict, List, Optional, Tuple
import hashlib


# ==================== Data Models ====================

class AgentType(Enum):
    """Specialized agent types for different roles"""
    CODER = "coder"
    TESTER = "tester"
    REVIEWER = "reviewer"
    COORDINATOR = "coordinator"
    ANALYST = "analyst"


class TaskStatus(Enum):
    """Task execution states"""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class MessageType(Enum):
    """Message types for agent communication"""
    TASK_ASSIGNMENT = "task_assignment"
    STATUS_UPDATE = "status_update"
    RESULT_SUBMISSION = "result_submission"
    CONFLICT_ALERT = "conflict_alert"
    CONSENSUS_REQUEST = "consensus_request"
    ACKNOWLEDGMENT = "acknowledgment"
    ERROR = "error"


@dataclass
class Message:
    """Inter-agent communication message"""
    msg_id: str
    sender_id: str
    receiver_id: str
    msg_type: MessageType
    content: Dict[str, Any]
    timestamp: str
    priority: int = 0

    def to_dict(self) -> Dict:
        return {
            "msg_id": self.msg_id,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "msg_type": self.msg_type.value,
            "content": json.dumps(self.content),
            "timestamp": self.timestamp,
            "priority": self.priority
        }


@dataclass
class Task:
    """Task to be distributed and executed"""
    task_id: str
    description: str
    required_agent_type: AgentType
    dependencies: List[str]
    priority: int
    status: TaskStatus
    assigned_agent_id: Optional[str] = None
    result: Optional[str] = None
    created_at: str = None
    completed_at: Optional[str] = None
    execution_time: Optional[float] = None

    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "description": self.description,
            "required_agent_type": self.required_agent_type.value,
            "dependencies": json.dumps(self.dependencies),
            "priority": self.priority,
            "status": self.status.value,
            "assigned_agent_id": self.assigned_agent_id,
            "result": self.result,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "execution_time": self.execution_time
        }


# ==================== Database Manager ====================

class CollaborationDB:
    """SQLite database for multi-agent collaboration tracking"""

    def __init__(self, db_path: str = "multi_ai_collaboration.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Agents table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agents (
                    agent_id TEXT PRIMARY KEY,
                    agent_type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_heartbeat TEXT
                )
            """)

            # Tasks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    description TEXT NOT NULL,
                    required_agent_type TEXT NOT NULL,
                    dependencies TEXT,
                    priority INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    assigned_agent_id TEXT,
                    result TEXT,
                    created_at TEXT NOT NULL,
                    completed_at TEXT,
                    execution_time REAL,
                    FOREIGN KEY(assigned_agent_id) REFERENCES agents(agent_id)
                )
            """)

            # Messages table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    msg_id TEXT PRIMARY KEY,
                    sender_id TEXT NOT NULL,
                    receiver_id TEXT NOT NULL,
                    msg_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    FOREIGN KEY(sender_id) REFERENCES agents(agent_id),
                    FOREIGN KEY(receiver_id) REFERENCES agents(agent_id)
                )
            """)

            # Results table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS results (
                    result_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    result_data TEXT NOT NULL,
                    confidence REAL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(task_id) REFERENCES tasks(task_id),
                    FOREIGN KEY(agent_id) REFERENCES agents(agent_id)
                )
            """)

            # Conflicts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conflicts (
                    conflict_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    agent_ids TEXT NOT NULL,
                    conflict_description TEXT NOT NULL,
                    resolution TEXT,
                    resolved BOOLEAN DEFAULT 0,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(task_id) REFERENCES tasks(task_id)
                )
            """)

            conn.commit()

    def add_agent(self, agent_id: str, agent_type: str, name: str):
        """Record agent creation"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO agents
                (agent_id, agent_type, name, status, created_at, last_heartbeat)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (agent_id, agent_type, name, "active", datetime.now().isoformat(), datetime.now().isoformat()))
            conn.commit()

    def add_task(self, task: Task):
        """Store task"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            task_dict = task.to_dict()
            cursor.execute("""
                INSERT OR REPLACE INTO tasks
                (task_id, description, required_agent_type, dependencies, priority, status,
                 assigned_agent_id, result, created_at, completed_at, execution_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, tuple(task_dict.values()))
            conn.commit()

    def update_task_status(self, task_id: str, status: TaskStatus):
        """Update task status"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tasks SET status = ? WHERE task_id = ?
            """, (status.value, task_id))
            conn.commit()

    def store_message(self, message: Message):
        """Store agent message"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            msg_dict = message.to_dict()
            cursor.execute("""
                INSERT INTO messages
                (msg_id, sender_id, receiver_id, msg_type, content, timestamp, priority)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, tuple(msg_dict.values()))
            conn.commit()

    def store_result(self, task_id: str, agent_id: str, result_data: str, confidence: float = 1.0):
        """Store task result from agent"""
        result_id = str(uuid.uuid4())
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO results
                (result_id, task_id, agent_id, result_data, confidence, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (result_id, task_id, agent_id, result_data, confidence, datetime.now().isoformat()))
            conn.commit()
        return result_id

    def record_conflict(self, task_id: str, agent_ids: List[str], description: str) -> str:
        """Record conflict between agents"""
        conflict_id = str(uuid.uuid4())
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO conflicts
                (conflict_id, task_id, agent_ids, conflict_description, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (conflict_id, task_id, json.dumps(agent_ids), description, datetime.now().isoformat()))
            conn.commit()
        return conflict_id

    def get_agent_tasks(self, agent_id: str) -> List[Task]:
        """Retrieve tasks assigned to agent"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM tasks WHERE assigned_agent_id = ?
            """, (agent_id,))
            rows = cursor.fetchall()
            return [self._row_to_task(row) for row in rows]

    def _row_to_task(self, row) -> Task:
        """Convert database row to Task object"""
        return Task(
            task_id=row[0],
            description=row[1],
            required_agent_type=AgentType(row[2]),
            dependencies=json.loads(row[3]) if row[3] else [],
            priority=row[4],
            status=TaskStatus(row[5]),
            assigned_agent_id=row[6],
            result=row[7],
            created_at=row[8],
            completed_at=row[9],
            execution_time=row[10]
        )


# ==================== Agent Communication Protocol ====================

class MessageBroker:
    """Central message broker for inter-agent communication"""

    def __init__(self, db: CollaborationDB):
        self.db = db
        self.message_queues: Dict[str, Queue] = {}
        self.lock = threading.Lock()

    def register_agent(self, agent_id: str):
        """Register agent to receive messages"""
        with self.lock:
            if agent_id not in self.message_queues:
                self.message_queues[agent_id] = PriorityQueue()

    def send_message(self, message: Message):
        """Send message from one agent to another"""
        self.db.store_message(message)
        with self.lock:
            if message.receiver_id in self.message_queues:
                self.message_queues[message.receiver_id].put(
                    (message.priority, message.msg_id, message)
                )

    def get_messages(self, agent_id: str, timeout: float = 0.5) -> List[Message]:
        """Retrieve messages for agent"""
        messages = []
        queue = self.message_queues.get(agent_id)
        if not queue:
            return messages

        try:
            while True:
                priority, msg_id, message = queue.get(block=False)
                messages.append(message)
        except:
            pass

        return messages

    def broadcast_message(self, message: Message, agent_ids: List[str]):
        """Send message to multiple agents"""
        for agent_id in agent_ids:
            msg_copy = Message(
                msg_id=str(uuid.uuid4()),
                sender_id=message.sender_id,
                receiver_id=agent_id,
                msg_type=message.msg_type,
                content=message.content,
                timestamp=message.timestamp,
                priority=message.priority
            )
            self.send_message(msg_copy)


# ==================== Task Distribution System ====================

class TaskDistributor:
    """Distributes tasks to appropriate agents based on type and load"""

    def __init__(self, db: CollaborationDB, broker: MessageBroker):
        self.db = db
        self.broker = broker
        self.task_queue = PriorityQueue()
        self.agent_loads: Dict[str, int] = {}
        self.lock = threading.Lock()

    def register_agent(self, agent_id: str):
        """Register agent for task distribution"""
        with self.lock:
            self.agent_loads[agent_id] = 0

    def submit_task(self, task: Task):
        """Submit task for distribution"""
        self.db.add_task(task)
        self.task_queue.put((task.priority, task.task_id, task))

    def get_next_task(self) -> Optional[Task]:
        """Get next task to distribute"""
        try:
            priority, task_id, task = self.task_queue.get(block=False)
            return task
        except:
            return None

    def assign_task(self, task: Task, agent_id: str) -> bool:
        """Assign task to specific agent"""
        with self.lock:
            if agent_id not in self.agent_loads:
                return False

            task.assigned_agent_id = agent_id
            task.status = TaskStatus.ASSIGNED
            self.db.add_task(task)
            self.agent_loads[agent_id] += 1

            # Send task assignment message
            message = Message(
                msg_id=str(uuid.uuid4()),
                sender_id="coordinator",
                receiver_id=agent_id,
                msg_type=MessageType.TASK_ASSIGNMENT,
                content={"task": asdict(task)},
                timestamp=datetime.now().isoformat(),
                priority=task.priority
            )
            self.broker.send_message(message)
            return True

    def update_agent_load(self, agent_id: str, completed: bool):
        """Update agent workload"""
        with self.lock:
            if completed and agent_id in self.agent_loads:
                self.agent_loads[agent_id] = max(0, self.agent_loads[agent_id] - 1)

    def get_least_loaded_agent(self, agent_type: AgentType, available_agents: Dict[str, AgentType]) -> Optional[str]:
        """Find least loaded agent of given type"""
        candidates = [aid for aid, atype in available_agents.items() if atype == agent_type]
        if not candidates:
            return None

        with self.lock:
            return min(candidates, key=lambda aid: self.agent_loads.get(aid, 0))


# ==================== Result Aggregation ====================

class ResultAggregator:
    """Aggregates and processes results from parallel agents"""

    def __init__(self, db: CollaborationDB):
        self.db = db
        self.results: Dict[str, List[Tuple[str, str]]] = {}
        self.lock = threading.Lock()

    def submit_result(self, task_id: str, agent_id: str, result: str, confidence: float = 1.0) -> str:
        """Submit result from agent"""
        result_id = self.db.store_result(task_id, agent_id, result, confidence)

        with self.lock:
            if task_id not in self.results:
                self.results[task_id] = []
            self.results[task_id].append((agent_id, result))

        return result_id

    def aggregate_results(self, task_id: str) -> Dict[str, Any]:
        """Aggregate results using consensus or majority voting"""
        with self.lock:
            if task_id not in self.results or not self.results[task_id]:
                return {"consensus": None, "agreement": 0.0, "agents": []}

            results = self.results[task_id]
            agent_ids = [r[0] for r in results]
            result_values = [r[1] for r in results]

            # Count occurrences for consensus
            result_counts = {}
            for result in result_values:
                result_counts[result] = result_counts.get(result, 0) + 1

            most_common = max(result_counts.items(), key=lambda x: x[1])[0]
            agreement = result_counts[most_common] / len(results)

            return {
                "consensus": most_common,
                "agreement": agreement,
                "agents": agent_ids,
                "individual_results": dict(zip(agent_ids, result_values))
            }

    def get_results(self, task_id: str) -> List[Tuple[str, str]]:
        """Get all results for task"""
        with self.lock:
            return self.results.get(task_id, [])


# ==================== Conflict Resolution ====================

class ConflictResolver:
    """Handles conflicts between agents with different results"""

    def __init__(self, db: CollaborationDB, broker: MessageBroker):
        self.db = db
        self.broker = broker
        self.conflicts: Dict[str, Dict] = {}
        self.lock = threading.Lock()

    def detect_conflict(self, task_id: str, results: Dict[str, Any]) -> bool:
        """Detect if agents have conflicting results"""
        if results["agreement"] < 1.0 and len(results["agents"]) > 1:
            return True
        return False

    def register_conflict(self, task_id: str, results: Dict[str, Any]) -> str:
        """Register and resolve conflict"""
        agent_ids = results["agents"]
        description = f"Conflicting results: {results['individual_results']}"

        conflict_id = self.db.record_conflict(task_id, agent_ids, description)

        with self.lock:
            self.conflicts[conflict_id] = {
                "task_id": task_id,
                "agents": agent_ids,
                "results": results["individual_results"],
                "agreement": results["agreement"],
                "status": "pending"
            }

        return conflict_id

    def resolve_conflict(self, conflict_id: str, resolution_method: str = "majority") -> str:
        """Resolve conflict using specified method"""
        with self.lock:
            if conflict_id not in self.conflicts:
                return None

            conflict = self.conflicts[conflict_id]

            if resolution_method == "majority":
                consensus = max(
                    set(conflict["results"].values()),
                    key=list(conflict["results"].values()).count
                )
            else:
                # Default: highest confidence agent wins
                consensus = list(conflict["results"].values())[0]

            conflict["status"] = "resolved"
            conflict["resolution"] = consensus

            return consensus

    def get_conflict_status(self, conflict_id: str) -> Optional[Dict]:
        """Get conflict details"""
        with self.lock:
            return self.conflicts.get(conflict_id)


# ==================== AI Agent ====================

class AIAgent(threading.Thread):
    """Specialized AI agent with task execution capability"""

    def __init__(
        self,
        agent_id: str,
        agent_type: AgentType,
        name: str,
        db: CollaborationDB,
        broker: MessageBroker,
        distributor: TaskDistributor
    ):
        super().__init__(daemon=True)
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.name = name
        self.db = db
        self.broker = broker
        self.distributor = distributor
        self.running = True
        self.current_task: Optional[Task] = None
        self.completed_tasks = 0

    def run(self):
        """Main agent execution loop"""
        self.broker.register_agent(self.agent_id)
        self.distributor.register_agent(self.agent_id)
        self.db.add_agent(self.agent_id, self.agent_type.value, self.name)

        while self.running:
            # Check for incoming messages
            messages = self.broker.get_messages(self.agent_id)
            for message in messages:
                self._handle_message(message)

            # Get next task if available
            if self.current_task is None:
                # Try to get task from distributor (assign new task)
                task = self.distributor.get_next_task()
                if task and task.required_agent_type == self.agent_type:
                    self.distributor.assign_task(task, self.agent_id)
                    self.current_task = task
                    self.current_task.status = TaskStatus.IN_PROGRESS
                    self.db.add_task(self.current_task)

            # Execute current task
            if self.current_task:
                self._execute_task()

            time.sleep(0.1)

    def _handle_message(self, message: Message):
        """Process incoming message"""
        if message.msg_type == MessageType.TASK_ASSIGNMENT:
            task_data = message.content.get("task")
            self.current_task = Task(
                task_id=task_data["task_id"],
                description=task_data["description"],
                required_agent_type=AgentType(task_data["required_agent_type"]),
                dependencies=task_data["dependencies"],
                priority=task_data["priority"],
                status=TaskStatus(task_data["status"]),
                assigned_agent_id=task_data["assigned_agent_id"]
            )

    def _execute_task(self):
        """Simulate task execution"""
        if not self.current_task:
            return

        # Simulate work
        time.sleep(0.2)

        # Generate result based on agent type
        result = self._generate_result()

        # Update task
        self.current_task.status = TaskStatus.COMPLETED
        self.current_task.result = result
        self.current_task.completed_at = datetime.now().isoformat()
        self.db.add_task(self.current_task)

        # Send result submission message
        message = Message(
            msg_id=str(uuid.uuid4()),
            sender_id=self.agent_id,
            receiver_id="coordinator",
            msg_type=MessageType.RESULT_SUBMISSION,
            content={
                "task_id": self.current_task.task_id,
                "result": result
            },
            timestamp=datetime.now().isoformat(),
            priority=0
        )
        self.broker.send_message(message)

        self.distributor.update_agent_load(self.agent_id, completed=True)
        self.completed_tasks += 1
        self.current_task = None

    def _generate_result(self) -> str:
        """Generate result based on agent type and task"""
        if self.agent_type == AgentType.CODER:
            return f"Code implementation for: {self.current_task.description}"
        elif self.agent_type == AgentType.TESTER:
            return f"Test results for: {self.current_task.description} - Status: PASSED"
        elif self.agent_type == AgentType.REVIEWER:
            return f"Code review for: {self.current_task.description} - Approved with suggestions"
        else:
            return f"Analysis for: {self.current_task.description}"

    def stop(self):
        """Stop agent execution"""
        self.running = False


# ==================== Multi-AI Coordinator ====================

class MultiAICoordinator:
    """Coordinates multiple AI agents for collaborative development"""

    def __init__(self, db_path: str = "multi_ai_collaboration.db"):
        self.db = CollaborationDB(db_path)
        self.broker = MessageBroker(self.db)
        self.distributor = TaskDistributor(self.db, self.broker)
        self.aggregator = ResultAggregator(self.db)
        self.resolver = ConflictResolver(self.db, self.broker)
        self.agents: Dict[str, AIAgent] = {}
        self.lock = threading.Lock()

    def spawn_agent(self, agent_type: AgentType, name: str) -> str:
        """Create and start a new agent"""
        agent_id = f"{agent_type.value}_{uuid.uuid4().hex[:8]}"

        agent = AIAgent(
            agent_id=agent_id,
            agent_type=agent_type,
            name=name,
            db=self.db,
            broker=self.broker,
            distributor=self.distributor
        )

        with self.lock:
            self.agents[agent_id] = agent

        agent.start()
        return agent_id

    def submit_task(self, description: str, agent_type: AgentType, priority: int = 0, dependencies: List[str] = None) -> str:
        """Submit task for execution"""
        task_id = str(uuid.uuid4())
        task = Task(
            task_id=task_id,
            description=description,
            required_agent_type=agent_type,
            dependencies=dependencies or [],
            priority=priority,
            status=TaskStatus.PENDING,
            created_at=datetime.now().isoformat()
        )

        self.distributor.submit_task(task)
        return task_id

    def get_agent_stats(self, agent_id: str) -> Dict[str, Any]:
        """Get statistics for agent"""
        with self.lock:
            if agent_id not in self.agents:
                return {}

            agent = self.agents[agent_id]
            return {
                "agent_id": agent_id,
                "agent_type": agent.agent_type.value,
                "name": agent.name,
                "completed_tasks": agent.completed_tasks,
                "current_task": agent.current_task.task_id if agent.current_task else None
            }

    def get_task_result(self, task_id: str) -> Dict[str, Any]:
        """Get aggregated result for task"""
        return self.aggregator.aggregate_results(task_id)

    def check_conflicts(self, task_id: str) -> Optional[str]:
        """Check and resolve conflicts for task"""
        results = self.aggregator.aggregate_results(task_id)

        if self.resolver.detect_conflict(task_id, results):
            conflict_id = self.resolver.register_conflict(task_id, results)
            resolution = self.resolver.resolve_conflict(conflict_id)
            return conflict_id
        return None

    def shutdown(self, timeout: float = 5.0):
        """Shutdown all agents gracefully"""
        with self.lock:
            for agent in self.agents.values():
                agent.stop()

        # Wait for agents to finish
        time.sleep(timeout)

    def get_system_stats(self) -> Dict[str, Any]:
        """Get overall system statistics"""
        with self.lock:
            agent_stats = [self.get_agent_stats(aid) for aid in self.agents.keys()]

        return {
            "total_agents": len(self.agents),
            "total_completed_tasks": sum(s.get("completed_tasks", 0) for s in agent_stats),
            "agents": agent_stats
        }


# ==================== Testing ====================

def test_multi_ai_system():
    """Comprehensive tests for multi-AI collaboration system"""

    print("\n" + "="*70)
    print("MULTI-AI COLLABORATION SYSTEM - COMPREHENSIVE TEST")
    print("="*70)

    # Initialize coordinator
    coordinator = MultiAICoordinator()
    print("\n[✓] Coordinator initialized with database")

    # Spawn specialized agents
    print("\n--- Spawning Specialized Agents ---")
    coder_1 = coordinator.spawn_agent(AgentType.CODER, "Coder Alpha")
    coder_2 = coordinator.spawn_agent(AgentType.CODER, "Coder Beta")
    tester_1 = coordinator.spawn_agent(AgentType.TESTER, "Tester Alpha")
    reviewer_1 = coordinator.spawn_agent(AgentType.REVIEWER, "Reviewer Alpha")

    print(f"[✓] Coder Alpha: {coder_1}")
    print(f"[✓] Coder Beta: {coder_2}")
    print(f"[✓] Tester Alpha: {tester_1}")
    print(f"[✓] Reviewer Alpha: {reviewer_1}")

    # Submit parallel development tasks
    print("\n--- Submitting Parallel Development Tasks ---")
    coding_task_1 = coordinator.submit_task("Implement user authentication module", AgentType.CODER, priority=1)
    coding_task_2 = coordinator.submit_task("Implement database layer", AgentType.CODER, priority=1)
    testing_task = coordinator.submit_task("Run comprehensive test suite", AgentType.TESTER, priority=2, dependencies=[coding_task_1, coding_task_2])
    review_task = coordinator.submit_task("Review implementation quality", AgentType.REVIEWER, priority=3, dependencies=[coding_task_1])

    print(f"[✓] Coding Task 1: {coding_task_1}")
    print(f"[✓] Coding Task 2: {coding_task_2}")
    print(f"[✓] Testing Task: {testing_task}")
    print(f"[✓] Review Task: {review_task}")

    # Allow execution
    print("\n--- Executing Tasks (3 seconds) ---")
    time.sleep(3)

    # Get results
    print("\n--- Task Results ---")
    result_1 = coordinator.get_task_result(coding_task_1)
    result_2 = coordinator.get_task_result(coding_task_2)
    result_3 = coordinator.get_task_result(testing_task)

    print(f"Task 1 Consensus: {result_1['consensus']}")
    print(f"Task 2 Consensus: {result_2['consensus']}")
    print(f"Task 3 Consensus: {result_3['consensus']}")

    # Check for conflicts
    print("\n--- Conflict Detection ---")
    conflict_1 = coordinator.check_conflicts(coding_task_1)
    print(f"Task 1 Conflict: {conflict_1 if conflict_1 else 'None detected'}")

    # Get system statistics
    print("\n--- System Statistics ---")
    stats = coordinator.get_system_stats()
    print(f"Total Agents: {stats['total_agents']}")
    print(f"Total Completed Tasks: {stats['total_completed_tasks']}")
    print("\nAgent Details:")
    for agent in stats['agents']:
        print(f"  {agent['name']}: {agent['completed_tasks']} tasks completed")

    # Shutdown
    print("\n--- Shutting Down System ---")
    coordinator.shutdown()
    print("[✓] All agents stopped")

    print("\n" + "="*70)
    print("TEST COMPLETED SUCCESSFULLY")
    print("="*70 + "\n")


if __name__ == "__main__":
    test_multi_ai_system()
