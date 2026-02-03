#!/usr/bin/env python3
"""
Workflow Orchestrator
Chain and orchestrate multiple SOPs into workflows
"""
import sys
from pathlib import Path
import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional, Callable
from enum import Enum

sys.path.append(str(Path(__file__).parent.parent))


class WorkflowStatus(Enum):
    """Workflow execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class WorkflowOrchestrator:
    """
    Orchestrate complex workflows from multiple SOPs

    Features:
    - Chain multiple SOPs into workflows
    - Conditional execution paths
    - Parallel SOP execution
    - Workflow templates
    - Error handling and retry
    - State management
    - Event-driven execution
    """

    def __init__(self, db_path: str = None):
        workspace = Path(__file__).parent.parent
        if db_path is None:
            db_path = str(workspace / "memory.db")

        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

        # Event handlers
        self.event_handlers = {}

    def _init_db(self):
        """Initialize database schema"""
        cursor = self.conn.cursor()

        # Workflows
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workflows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_name TEXT NOT NULL,
                description TEXT,
                workflow_type TEXT,
                is_template INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Workflow nodes (SOPs in workflow)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workflow_nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id INTEGER NOT NULL,
                node_name TEXT NOT NULL,
                sop_id INTEGER,
                node_type TEXT DEFAULT 'sop',
                position_x INTEGER,
                position_y INTEGER,
                config TEXT,
                FOREIGN KEY (workflow_id) REFERENCES workflows(id),
                FOREIGN KEY (sop_id) REFERENCES sops(id)
            )
        ''')

        # Workflow edges (connections)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workflow_edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id INTEGER NOT NULL,
                from_node_id INTEGER NOT NULL,
                to_node_id INTEGER NOT NULL,
                condition_type TEXT,
                condition_value TEXT,
                FOREIGN KEY (workflow_id) REFERENCES workflows(id),
                FOREIGN KEY (from_node_id) REFERENCES workflow_nodes(id),
                FOREIGN KEY (to_node_id) REFERENCES workflow_nodes(id)
            )
        ''')

        # Workflow executions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workflow_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                current_node_id INTEGER,
                execution_context TEXT,
                error_message TEXT,
                FOREIGN KEY (workflow_id) REFERENCES workflows(id),
                FOREIGN KEY (current_node_id) REFERENCES workflow_nodes(id)
            )
        ''')

        # Node executions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workflow_node_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_execution_id INTEGER NOT NULL,
                node_id INTEGER NOT NULL,
                sop_execution_id INTEGER,
                status TEXT DEFAULT 'pending',
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                result TEXT,
                error_message TEXT,
                FOREIGN KEY (workflow_execution_id) REFERENCES workflow_executions(id),
                FOREIGN KEY (node_id) REFERENCES workflow_nodes(id),
                FOREIGN KEY (sop_execution_id) REFERENCES sop_executions(id)
            )
        ''')

        self.conn.commit()

    # === WORKFLOW CREATION ===

    def create_workflow(self, workflow_name: str, description: str = None,
                       workflow_type: str = "sequential", is_template: bool = False) -> int:
        """
        Create new workflow

        Args:
            workflow_name: Workflow name
            description: Description
            workflow_type: 'sequential', 'parallel', 'conditional'
            is_template: If true, can be reused

        Returns:
            Workflow ID
        """
        cursor = self.conn.cursor()

        cursor.execute('''
            INSERT INTO workflows (workflow_name, description, workflow_type, is_template)
            VALUES (?, ?, ?, ?)
        ''', (workflow_name, description, workflow_type, 1 if is_template else 0))

        self.conn.commit()
        return cursor.lastrowid

    def add_node(self, workflow_id: int, node_name: str, sop_id: int = None,
                node_type: str = 'sop', config: Dict = None,
                position: tuple = None) -> int:
        """
        Add node to workflow

        Args:
            workflow_id: Workflow ID
            node_name: Node name
            sop_id: SOP to execute (if node_type='sop')
            node_type: 'sop', 'decision', 'parallel', 'wait'
            config: Node configuration
            position: (x, y) position for visualization

        Returns:
            Node ID
        """
        cursor = self.conn.cursor()

        pos_x, pos_y = position if position else (0, 0)
        config_json = json.dumps(config) if config else None

        cursor.execute('''
            INSERT INTO workflow_nodes
            (workflow_id, node_name, sop_id, node_type, position_x, position_y, config)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (workflow_id, node_name, sop_id, node_type, pos_x, pos_y, config_json))

        self.conn.commit()
        return cursor.lastrowid

    def connect_nodes(self, workflow_id: int, from_node_id: int, to_node_id: int,
                     condition_type: str = None, condition_value: str = None) -> int:
        """
        Connect two nodes

        Args:
            workflow_id: Workflow ID
            from_node_id: Source node
            to_node_id: Target node
            condition_type: 'success', 'failure', 'always', 'custom'
            condition_value: Condition expression for custom type

        Returns:
            Edge ID
        """
        cursor = self.conn.cursor()

        cursor.execute('''
            INSERT INTO workflow_edges
            (workflow_id, from_node_id, to_node_id, condition_type, condition_value)
            VALUES (?, ?, ?, ?, ?)
        ''', (workflow_id, from_node_id, to_node_id, condition_type, condition_value))

        self.conn.commit()
        return cursor.lastrowid

    # === WORKFLOW EXECUTION ===

    def execute_workflow(self, workflow_id: int, context: Dict = None,
                        sop_executor: Callable = None) -> int:
        """
        Execute workflow

        Args:
            workflow_id: Workflow to execute
            context: Execution context/variables
            sop_executor: Function to execute SOPs (if None, uses mock)

        Returns:
            Workflow execution ID
        """
        cursor = self.conn.cursor()

        # Create execution record
        context_json = json.dumps(context) if context else None

        cursor.execute('''
            INSERT INTO workflow_executions
            (workflow_id, status, started_at, execution_context)
            VALUES (?, 'running', CURRENT_TIMESTAMP, ?)
        ''', (workflow_id, context_json))

        execution_id = cursor.lastrowid
        self.conn.commit()

        try:
            # Get workflow type
            cursor.execute('SELECT workflow_type FROM workflows WHERE id = ?', (workflow_id,))
            workflow = cursor.fetchone()

            if workflow['workflow_type'] == 'sequential':
                self._execute_sequential(execution_id, workflow_id, context or {}, sop_executor)
            elif workflow['workflow_type'] == 'parallel':
                self._execute_parallel(execution_id, workflow_id, context or {}, sop_executor)
            elif workflow['workflow_type'] == 'conditional':
                self._execute_conditional(execution_id, workflow_id, context or {}, sop_executor)

            # Mark complete
            cursor.execute('''
                UPDATE workflow_executions
                SET status = 'completed', completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (execution_id,))
            self.conn.commit()

        except Exception as e:
            # Mark failed
            cursor.execute('''
                UPDATE workflow_executions
                SET status = 'failed', completed_at = CURRENT_TIMESTAMP, error_message = ?
                WHERE id = ?
            ''', (str(e), execution_id))
            self.conn.commit()
            raise

        return execution_id

    def _execute_sequential(self, execution_id: int, workflow_id: int,
                           context: Dict, sop_executor: Callable = None):
        """Execute workflow sequentially"""
        cursor = self.conn.cursor()

        # Get nodes in order
        cursor.execute('''
            SELECT id, node_name, sop_id, node_type, config
            FROM workflow_nodes
            WHERE workflow_id = ?
            ORDER BY position_y, position_x
        ''', (workflow_id,))

        nodes = [dict(row) for row in cursor.fetchall()]

        for node in nodes:
            self._execute_node(execution_id, node, context, sop_executor)

    def _execute_parallel(self, execution_id: int, workflow_id: int,
                         context: Dict, sop_executor: Callable = None):
        """Execute workflow nodes in parallel"""
        cursor = self.conn.cursor()

        # Get all nodes
        cursor.execute('''
            SELECT id, node_name, sop_id, node_type, config
            FROM workflow_nodes
            WHERE workflow_id = ?
        ''', (workflow_id,))

        nodes = [dict(row) for row in cursor.fetchall()]

        # Execute all nodes (in real implementation, use threading/async)
        for node in nodes:
            self._execute_node(execution_id, node, context, sop_executor)

    def _execute_conditional(self, execution_id: int, workflow_id: int,
                            context: Dict, sop_executor: Callable = None):
        """Execute workflow with conditional paths"""
        cursor = self.conn.cursor()

        # Start from first node (no incoming edges)
        cursor.execute('''
            SELECT n.id, n.node_name, n.sop_id, n.node_type, n.config
            FROM workflow_nodes n
            WHERE n.workflow_id = ?
            AND NOT EXISTS (
                SELECT 1 FROM workflow_edges e WHERE e.to_node_id = n.id
            )
        ''', (workflow_id,))

        current_node = cursor.fetchone()

        if not current_node:
            raise ValueError("No starting node found")

        # Execute nodes following edges
        while current_node:
            node_dict = dict(current_node)
            result = self._execute_node(execution_id, node_dict, context, sop_executor)

            # Find next node based on result
            cursor.execute('''
                SELECT n.id, n.node_name, n.sop_id, n.node_type, n.config
                FROM workflow_nodes n
                JOIN workflow_edges e ON e.to_node_id = n.id
                WHERE e.from_node_id = ?
                AND (
                    e.condition_type = 'always'
                    OR (e.condition_type = 'success' AND ?)
                    OR (e.condition_type = 'failure' AND NOT ?)
                )
                LIMIT 1
            ''', (node_dict['id'], result.get('success', True), result.get('success', True)))

            current_node = cursor.fetchone()

    def _execute_node(self, execution_id: int, node: Dict, context: Dict,
                     sop_executor: Callable = None) -> Dict:
        """Execute single workflow node"""
        cursor = self.conn.cursor()

        # Create node execution record
        cursor.execute('''
            INSERT INTO workflow_node_executions
            (workflow_execution_id, node_id, status, started_at)
            VALUES (?, ?, 'running', CURRENT_TIMESTAMP)
        ''', (execution_id, node['id']))

        node_execution_id = cursor.lastrowid
        self.conn.commit()

        result = {'success': True}

        try:
            # Execute based on node type
            if node['node_type'] == 'sop':
                if sop_executor and node['sop_id']:
                    # Execute actual SOP
                    sop_result = sop_executor(node['sop_id'], context)
                    result = sop_result
                else:
                    # Mock execution
                    result = {'success': True, 'message': f"Executed SOP {node['sop_id']}"}

            elif node['node_type'] == 'decision':
                # Evaluate decision
                config = json.loads(node['config']) if node['config'] else {}
                result = self._evaluate_decision(config, context)

            elif node['node_type'] == 'wait':
                # Wait/pause
                config = json.loads(node['config']) if node['config'] else {}
                result = {'success': True, 'message': f"Waited {config.get('duration', 0)}s"}

            # Update node execution
            cursor.execute('''
                UPDATE workflow_node_executions
                SET status = 'completed', completed_at = CURRENT_TIMESTAMP, result = ?
                WHERE id = ?
            ''', (json.dumps(result), node_execution_id))
            self.conn.commit()

        except Exception as e:
            result = {'success': False, 'error': str(e)}

            cursor.execute('''
                UPDATE workflow_node_executions
                SET status = 'failed', completed_at = CURRENT_TIMESTAMP, error_message = ?
                WHERE id = ?
            ''', (str(e), node_execution_id))
            self.conn.commit()

        return result

    def _evaluate_decision(self, config: Dict, context: Dict) -> Dict:
        """Evaluate decision node"""
        # Simple decision evaluation
        condition = config.get('condition', '')

        # Basic evaluation (in production, use safe expression evaluator)
        try:
            result = eval(condition, {"__builtins__": {}}, context)
            return {'success': bool(result), 'decision': result}
        except:
            return {'success': False, 'decision': None}

    # === WORKFLOW TEMPLATES ===

    def save_as_template(self, workflow_id: int, template_name: str = None) -> int:
        """
        Save workflow as reusable template

        Args:
            workflow_id: Workflow to save
            template_name: Template name

        Returns:
            Template workflow ID
        """
        cursor = self.conn.cursor()

        # Get workflow
        cursor.execute('SELECT * FROM workflows WHERE id = ?', (workflow_id,))
        workflow = dict(cursor.fetchone())

        # Create template
        cursor.execute('''
            INSERT INTO workflows (workflow_name, description, workflow_type, is_template)
            VALUES (?, ?, ?, 1)
        ''', (template_name or f"{workflow['workflow_name']}_template",
              workflow['description'], workflow['workflow_type']))

        template_id = cursor.lastrowid

        # Copy nodes
        cursor.execute('SELECT * FROM workflow_nodes WHERE workflow_id = ?', (workflow_id,))
        nodes = [dict(row) for row in cursor.fetchall()]

        node_mapping = {}
        for node in nodes:
            cursor.execute('''
                INSERT INTO workflow_nodes
                (workflow_id, node_name, sop_id, node_type, position_x, position_y, config)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (template_id, node['node_name'], node['sop_id'], node['node_type'],
                  node['position_x'], node['position_y'], node['config']))

            node_mapping[node['id']] = cursor.lastrowid

        # Copy edges
        cursor.execute('SELECT * FROM workflow_edges WHERE workflow_id = ?', (workflow_id,))
        edges = [dict(row) for row in cursor.fetchall()]

        for edge in edges:
            cursor.execute('''
                INSERT INTO workflow_edges
                (workflow_id, from_node_id, to_node_id, condition_type, condition_value)
                VALUES (?, ?, ?, ?, ?)
            ''', (template_id, node_mapping[edge['from_node_id']],
                  node_mapping[edge['to_node_id']], edge['condition_type'],
                  edge['condition_value']))

        self.conn.commit()
        return template_id

    def instantiate_template(self, template_id: int, workflow_name: str) -> int:
        """
        Create workflow from template

        Args:
            template_id: Template workflow ID
            workflow_name: New workflow name

        Returns:
            New workflow ID
        """
        return self.save_as_template(template_id, workflow_name)

    # === WORKFLOW STATUS ===

    def get_workflow_status(self, execution_id: int) -> Dict:
        """
        Get workflow execution status

        Args:
            execution_id: Workflow execution ID

        Returns:
            Status information
        """
        cursor = self.conn.cursor()

        cursor.execute('''
            SELECT
                we.*,
                w.workflow_name,
                w.workflow_type
            FROM workflow_executions we
            JOIN workflows w ON we.workflow_id = w.id
            WHERE we.id = ?
        ''', (execution_id,))

        execution = dict(cursor.fetchone())

        # Get node executions
        cursor.execute('''
            SELECT
                wne.*,
                wn.node_name,
                wn.node_type
            FROM workflow_node_executions wne
            JOIN workflow_nodes wn ON wne.node_id = wn.id
            WHERE wne.workflow_execution_id = ?
            ORDER BY wne.started_at
        ''', (execution_id,))

        node_executions = [dict(row) for row in cursor.fetchall()]

        return {
            'execution_id': execution_id,
            'workflow_name': execution['workflow_name'],
            'workflow_type': execution['workflow_type'],
            'status': execution['status'],
            'started_at': execution['started_at'],
            'completed_at': execution['completed_at'],
            'error_message': execution['error_message'],
            'node_executions': node_executions
        }

    def close(self):
        """Close database connection"""
        self.conn.close()


# === TEST CODE ===

def main():
    """Test workflow orchestrator"""
    print("Testing Workflow Orchestrator")
    print("=" * 70)

    orchestrator = WorkflowOrchestrator()

    try:
        print("\n1. Creating workflow...")
        workflow_id = orchestrator.create_workflow(
            "Test Workflow",
            "Sequential test workflow",
            workflow_type="sequential"
        )
        print(f"   Workflow created: ID {workflow_id}")

        print("\n2. Adding nodes...")
        node1 = orchestrator.add_node(workflow_id, "Step 1", node_type='sop', position=(0, 0))
        node2 = orchestrator.add_node(workflow_id, "Step 2", node_type='sop', position=(0, 100))
        node3 = orchestrator.add_node(workflow_id, "Step 3", node_type='sop', position=(0, 200))
        print(f"   Added 3 nodes")

        print("\n3. Connecting nodes...")
        orchestrator.connect_nodes(workflow_id, node1, node2, condition_type='always')
        orchestrator.connect_nodes(workflow_id, node2, node3, condition_type='always')
        print(f"   Nodes connected")

        print("\n4. Executing workflow...")
        execution_id = orchestrator.execute_workflow(workflow_id, context={'test': True})
        print(f"   Execution ID: {execution_id}")

        print("\n5. Getting status...")
        status = orchestrator.get_workflow_status(execution_id)
        print(f"   Status: {status['status']}")
        print(f"   Nodes executed: {len(status['node_executions'])}")

        print("\n6. Creating template...")
        template_id = orchestrator.save_as_template(workflow_id, "Test Template")
        print(f"   Template ID: {template_id}")

        print(f"\n[OK] Workflow Orchestrator working!")
        print(f"Database: {orchestrator.db_path}")

    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        orchestrator.close()


if __name__ == "__main__":
    main()
