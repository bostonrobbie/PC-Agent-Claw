#!/usr/bin/env python3
"""
SOP (Standard Operating Procedure) Management System
Capture, manage, and automate all business processes
"""
import sys
from pathlib import Path
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum

sys.path.append(str(Path(__file__).parent.parent))


class SOPStatus(Enum):
    """SOP lifecycle status"""
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class StepType(Enum):
    """Types of process steps"""
    MANUAL = "manual"
    AUTOMATED = "automated"
    DECISION = "decision"
    APPROVAL = "approval"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"


class SOPManager:
    """
    Manage all business SOPs and processes

    Features:
    - Store SOPs by department/role/function
    - Version control for SOPs
    - Step-by-step procedures
    - Automated vs manual steps
    - Dependencies and prerequisites
    - Checklists and validation
    - Execution tracking
    - Performance metrics
    - Continuous improvement
    """

    def __init__(self, db_path: str = None):
        workspace = Path(__file__).parent.parent
        if db_path is None:
            db_path = str(workspace / "memory.db")

        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

        # Load Telegram notifier
        try:
            from telegram_notifier import TelegramNotifier
            self.notifier = TelegramNotifier()
        except Exception as e:
            print(f"[WARNING] Could not load Telegram notifier: {e}")
            self.notifier = None

    def _init_db(self):
        """Initialize database schema"""
        cursor = self.conn.cursor()

        # Business functions/departments
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS business_functions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                function_name TEXT UNIQUE NOT NULL,
                description TEXT,
                parent_function_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_function_id) REFERENCES business_functions(id)
            )
        ''')

        # Roles
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS business_roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role_name TEXT UNIQUE NOT NULL,
                function_id INTEGER NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (function_id) REFERENCES business_functions(id)
            )
        ''')

        # SOPs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sops (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sop_code TEXT UNIQUE NOT NULL,
                sop_title TEXT NOT NULL,
                function_id INTEGER NOT NULL,
                role_id INTEGER,
                description TEXT,
                purpose TEXT,
                scope TEXT,
                status TEXT DEFAULT 'draft',
                version INTEGER DEFAULT 1,
                frequency TEXT,
                estimated_duration_minutes INTEGER,
                automation_level REAL DEFAULT 0.0,
                created_by TEXT,
                approved_by TEXT,
                approved_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (function_id) REFERENCES business_functions(id),
                FOREIGN KEY (role_id) REFERENCES business_roles(id)
            )
        ''')

        # SOP versions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sop_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sop_id INTEGER NOT NULL,
                version INTEGER NOT NULL,
                content TEXT NOT NULL,
                changes_description TEXT,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sop_id) REFERENCES sops(id),
                UNIQUE(sop_id, version)
            )
        ''')

        # Process steps
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sop_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sop_id INTEGER NOT NULL,
                step_number INTEGER NOT NULL,
                step_title TEXT NOT NULL,
                step_description TEXT,
                step_type TEXT NOT NULL,
                is_automated INTEGER DEFAULT 0,
                automation_script TEXT,
                required_inputs TEXT,
                expected_outputs TEXT,
                validation_criteria TEXT,
                estimated_duration_minutes INTEGER,
                predecessor_step_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sop_id) REFERENCES sops(id),
                FOREIGN KEY (predecessor_step_id) REFERENCES sop_steps(id)
            )
        ''')

        # SOP executions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sop_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sop_id INTEGER NOT NULL,
                executed_by TEXT,
                status TEXT DEFAULT 'in_progress',
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                actual_duration_minutes INTEGER,
                success INTEGER,
                notes TEXT,
                FOREIGN KEY (sop_id) REFERENCES sops(id)
            )
        ''')

        # Step executions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS step_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id INTEGER NOT NULL,
                step_id INTEGER NOT NULL,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                status TEXT DEFAULT 'pending',
                result TEXT,
                notes TEXT,
                FOREIGN KEY (execution_id) REFERENCES sop_executions(id),
                FOREIGN KEY (step_id) REFERENCES sop_steps(id)
            )
        ''')

        # Checklists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS step_checklists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                step_id INTEGER NOT NULL,
                checklist_item TEXT NOT NULL,
                is_required INTEGER DEFAULT 1,
                display_order INTEGER,
                FOREIGN KEY (step_id) REFERENCES sop_steps(id)
            )
        ''')

        # SOP dependencies
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sop_dependencies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sop_id INTEGER NOT NULL,
                depends_on_sop_id INTEGER NOT NULL,
                dependency_type TEXT,
                FOREIGN KEY (sop_id) REFERENCES sops(id),
                FOREIGN KEY (depends_on_sop_id) REFERENCES sops(id)
            )
        ''')

        # Improvement suggestions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sop_improvements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sop_id INTEGER NOT NULL,
                suggested_by TEXT,
                improvement_description TEXT,
                expected_benefit TEXT,
                status TEXT DEFAULT 'proposed',
                implemented_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sop_id) REFERENCES sops(id)
            )
        ''')

        self.conn.commit()

        # Create default business functions
        self._create_default_structure()

    def _create_default_structure(self):
        """Create default business structure"""
        default_functions = [
            ('Trading Operations', 'Core trading activities'),
            ('Risk Management', 'Risk monitoring and control'),
            ('Technology', 'System development and maintenance'),
            ('Operations', 'Daily operational tasks'),
            ('Compliance', 'Regulatory and compliance tasks')
        ]

        cursor = self.conn.cursor()

        for func_name, description in default_functions:
            cursor.execute('''
                INSERT OR IGNORE INTO business_functions (function_name, description)
                VALUES (?, ?)
            ''', (func_name, description))

        self.conn.commit()

    # === FUNCTION & ROLE MANAGEMENT ===

    def create_function(self, function_name: str, description: str = None,
                       parent_function_id: int = None) -> int:
        """Create business function"""
        cursor = self.conn.cursor()

        cursor.execute('''
            INSERT INTO business_functions (function_name, description, parent_function_id)
            VALUES (?, ?, ?)
        ''', (function_name, description, parent_function_id))

        self.conn.commit()
        return cursor.lastrowid

    def create_role(self, role_name: str, function_id: int, description: str = None) -> int:
        """Create business role"""
        cursor = self.conn.cursor()

        cursor.execute('''
            INSERT INTO business_roles (role_name, function_id, description)
            VALUES (?, ?, ?)
        ''', (role_name, function_id, description))

        self.conn.commit()
        return cursor.lastrowid

    # === SOP MANAGEMENT ===

    def create_sop(self, sop_code: str, title: str, function_id: int,
                   description: str = None, purpose: str = None,
                   scope: str = None, role_id: int = None,
                   frequency: str = None, estimated_duration: int = None,
                   created_by: str = None) -> int:
        """
        Create new SOP

        Args:
            sop_code: Unique SOP identifier (e.g., "SOP-TRADE-001")
            title: SOP title
            function_id: Business function
            description: Detailed description
            purpose: Why this SOP exists
            scope: What this SOP covers
            role_id: Primary role responsible
            frequency: How often (daily, weekly, monthly, etc.)
            estimated_duration: Minutes
            created_by: Creator

        Returns:
            SOP ID
        """
        cursor = self.conn.cursor()

        cursor.execute('''
            INSERT INTO sops
            (sop_code, sop_title, function_id, role_id, description, purpose,
             scope, frequency, estimated_duration_minutes, created_by, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft')
        ''', (sop_code, title, function_id, role_id, description, purpose,
              scope, frequency, estimated_duration, created_by))

        sop_id = cursor.lastrowid

        # Create initial version
        cursor.execute('''
            INSERT INTO sop_versions (sop_id, version, content, created_by)
            VALUES (?, 1, ?, ?)
        ''', (sop_id, json.dumps({'description': description, 'purpose': purpose}), created_by))

        self.conn.commit()

        print(f"[SOP] Created: {sop_code} - {title}")

        return sop_id

    def add_step(self, sop_id: int, step_number: int, title: str,
                description: str, step_type: str = 'manual',
                is_automated: bool = False, automation_script: str = None,
                required_inputs: List[str] = None, expected_outputs: List[str] = None,
                validation_criteria: str = None, estimated_duration: int = None,
                predecessor_step_id: int = None) -> int:
        """
        Add step to SOP

        Args:
            sop_id: SOP ID
            step_number: Step sequence number
            title: Step title
            description: Detailed instructions
            step_type: Type of step (manual, automated, decision, etc.)
            is_automated: Can be automated
            automation_script: Script/function for automation
            required_inputs: List of required inputs
            expected_outputs: List of expected outputs
            validation_criteria: How to validate completion
            estimated_duration: Minutes
            predecessor_step_id: Previous step dependency

        Returns:
            Step ID
        """
        cursor = self.conn.cursor()

        cursor.execute('''
            INSERT INTO sop_steps
            (sop_id, step_number, step_title, step_description, step_type,
             is_automated, automation_script, required_inputs, expected_outputs,
             validation_criteria, estimated_duration_minutes, predecessor_step_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (sop_id, step_number, title, description, step_type,
              1 if is_automated else 0, automation_script,
              json.dumps(required_inputs) if required_inputs else None,
              json.dumps(expected_outputs) if expected_outputs else None,
              validation_criteria, estimated_duration, predecessor_step_id))

        self.conn.commit()

        # Update automation level
        self._update_automation_level(sop_id)

        return cursor.lastrowid

    def add_checklist_item(self, step_id: int, item: str, required: bool = True,
                          display_order: int = None) -> int:
        """Add checklist item to step"""
        cursor = self.conn.cursor()

        if display_order is None:
            cursor.execute('SELECT COUNT(*) as count FROM step_checklists WHERE step_id = ?',
                          (step_id,))
            display_order = cursor.fetchone()['count'] + 1

        cursor.execute('''
            INSERT INTO step_checklists (step_id, checklist_item, is_required, display_order)
            VALUES (?, ?, ?, ?)
        ''', (step_id, item, 1 if required else 0, display_order))

        self.conn.commit()
        return cursor.lastrowid

    def _update_automation_level(self, sop_id: int):
        """Calculate and update SOP automation level"""
        cursor = self.conn.cursor()

        cursor.execute('''
            SELECT
                COUNT(*) as total_steps,
                SUM(is_automated) as automated_steps
            FROM sop_steps
            WHERE sop_id = ?
        ''', (sop_id,))

        result = cursor.fetchone()

        if result['total_steps'] > 0:
            automation_level = result['automated_steps'] / result['total_steps']

            cursor.execute('''
                UPDATE sops SET automation_level = ? WHERE id = ?
            ''', (automation_level, sop_id))

            self.conn.commit()

    # === SOP EXECUTION ===

    def start_execution(self, sop_id: int, executed_by: str = None) -> int:
        """Start SOP execution"""
        cursor = self.conn.cursor()

        cursor.execute('''
            INSERT INTO sop_executions (sop_id, executed_by, status)
            VALUES (?, ?, 'in_progress')
        ''', (sop_id, executed_by))

        execution_id = cursor.lastrowid

        # Create step execution records
        cursor.execute('''
            INSERT INTO step_executions (execution_id, step_id, status)
            SELECT ?, id, 'pending'
            FROM sop_steps
            WHERE sop_id = ?
            ORDER BY step_number
        ''', (execution_id, sop_id))

        self.conn.commit()

        # Get SOP details
        cursor.execute('SELECT sop_code, sop_title FROM sops WHERE id = ?', (sop_id,))
        sop = cursor.fetchone()

        print(f"[SOP] Execution started: {sop['sop_code']} - {sop['sop_title']}")

        return execution_id

    def complete_step(self, execution_id: int, step_number: int,
                     result: str = None, notes: str = None) -> bool:
        """Mark step as complete"""
        cursor = self.conn.cursor()

        # Get step ID
        cursor.execute('''
            SELECT se.id, ss.step_title
            FROM step_executions se
            JOIN sop_steps ss ON se.step_id = ss.id
            WHERE se.execution_id = ? AND ss.step_number = ?
        ''', (execution_id, step_number))

        step_exec = cursor.fetchone()

        if not step_exec:
            return False

        # Mark complete
        cursor.execute('''
            UPDATE step_executions
            SET status = 'completed',
                completed_at = CURRENT_TIMESTAMP,
                result = ?,
                notes = ?
            WHERE id = ?
        ''', (result, notes, step_exec['id']))

        self.conn.commit()

        print(f"[SOP] Step {step_number} completed: {step_exec['step_title']}")

        return True

    def complete_execution(self, execution_id: int, success: bool = True,
                          notes: str = None) -> bool:
        """Complete SOP execution"""
        cursor = self.conn.cursor()

        # Calculate duration
        cursor.execute('''
            SELECT
                CAST((julianday(CURRENT_TIMESTAMP) - julianday(started_at)) * 24 * 60 AS INTEGER) as duration
            FROM sop_executions
            WHERE id = ?
        ''', (execution_id,))

        duration = cursor.fetchone()['duration']

        # Mark complete
        cursor.execute('''
            UPDATE sop_executions
            SET status = 'completed',
                completed_at = CURRENT_TIMESTAMP,
                actual_duration_minutes = ?,
                success = ?,
                notes = ?
            WHERE id = ?
        ''', (duration, 1 if success else 0, notes, execution_id))

        self.conn.commit()

        print(f"[SOP] Execution completed: Duration {duration} minutes, Success: {success}")

        return True

    # === ANALYTICS ===

    def get_sop_performance(self, sop_id: int) -> Dict:
        """Get SOP performance metrics"""
        cursor = self.conn.cursor()

        # Execution stats
        cursor.execute('''
            SELECT
                COUNT(*) as total_executions,
                SUM(success) as successful,
                AVG(actual_duration_minutes) as avg_duration,
                MIN(actual_duration_minutes) as min_duration,
                MAX(actual_duration_minutes) as max_duration
            FROM sop_executions
            WHERE sop_id = ? AND completed_at IS NOT NULL
        ''', (sop_id,))

        stats = dict(cursor.fetchone())

        # Calculate success rate
        if stats['total_executions'] > 0:
            stats['success_rate'] = stats['successful'] / stats['total_executions']
        else:
            stats['success_rate'] = 0

        # Recent executions
        cursor.execute('''
            SELECT executed_by, started_at, actual_duration_minutes, success
            FROM sop_executions
            WHERE sop_id = ?
            ORDER BY started_at DESC
            LIMIT 10
        ''', (sop_id,))

        stats['recent_executions'] = [dict(row) for row in cursor.fetchall()]

        return stats

    def get_function_sops(self, function_id: int) -> List[Dict]:
        """Get all SOPs for a function"""
        cursor = self.conn.cursor()

        cursor.execute('''
            SELECT
                s.*,
                bf.function_name,
                br.role_name,
                (SELECT COUNT(*) FROM sop_steps WHERE sop_id = s.id) as step_count
            FROM sops s
            JOIN business_functions bf ON s.function_id = bf.id
            LEFT JOIN business_roles br ON s.role_id = br.id
            WHERE s.function_id = ?
            ORDER BY s.sop_code
        ''', (function_id,))

        return [dict(row) for row in cursor.fetchall()]

    def suggest_improvement(self, sop_id: int, description: str,
                           expected_benefit: str, suggested_by: str = None) -> int:
        """Suggest SOP improvement"""
        cursor = self.conn.cursor()

        cursor.execute('''
            INSERT INTO sop_improvements
            (sop_id, suggested_by, improvement_description, expected_benefit)
            VALUES (?, ?, ?, ?)
        ''', (sop_id, suggested_by, description, expected_benefit))

        self.conn.commit()

        return cursor.lastrowid

    def get_all_sops(self, status: str = None) -> List[Dict]:
        """Get all SOPs"""
        cursor = self.conn.cursor()

        if status:
            cursor.execute('''
                SELECT s.*, bf.function_name
                FROM sops s
                JOIN business_functions bf ON s.function_id = bf.id
                WHERE s.status = ?
                ORDER BY bf.function_name, s.sop_code
            ''', (status,))
        else:
            cursor.execute('''
                SELECT s.*, bf.function_name
                FROM sops s
                JOIN business_functions bf ON s.function_id = bf.id
                ORDER BY bf.function_name, s.sop_code
            ''')

        return [dict(row) for row in cursor.fetchall()]

    def close(self):
        """Close database connection"""
        self.conn.close()


# === TEST CODE ===

def main():
    """Test SOP manager"""
    print("Testing SOP Manager")
    print("=" * 70)

    manager = SOPManager()

    try:
        # Create function and role
        print("\n1. Creating business structure...")
        func_id = manager.create_function("Trading", "Trading operations")
        role_id = manager.create_role("Lead Trader", func_id, "Executes trades")
        print(f"   Function ID: {func_id}, Role ID: {role_id}")

        # Create SOP
        print("\n2. Creating SOP...")
        sop_id = manager.create_sop(
            "SOP-TRADE-001",
            "Execute Market Order",
            func_id,
            description="Process for executing market orders",
            purpose="Ensure consistent trade execution",
            scope="All market orders",
            role_id=role_id,
            frequency="As needed",
            estimated_duration=5,
            created_by="system"
        )
        print(f"   SOP ID: {sop_id}")

        # Add steps
        print("\n3. Adding SOP steps...")
        step1_id = manager.add_step(
            sop_id, 1,
            "Verify Market Conditions",
            "Check market is open and liquid",
            step_type="manual",
            estimated_duration=1
        )

        step2_id = manager.add_step(
            sop_id, 2,
            "Calculate Position Size",
            "Calculate based on risk parameters",
            step_type="automated",
            is_automated=True,
            automation_script="calculate_position_size()",
            estimated_duration=1,
            predecessor_step_id=step1_id
        )

        manager.add_checklist_item(step1_id, "Market is open")
        manager.add_checklist_item(step1_id, "Sufficient liquidity")

        print(f"   Added 2 steps with checklists")

        # Execute SOP
        print("\n4. Executing SOP...")
        exec_id = manager.start_execution(sop_id, "test_user")
        manager.complete_step(exec_id, 1, result="Market verified")
        manager.complete_step(exec_id, 2, result="Position: 100 shares")
        manager.complete_execution(exec_id, success=True)
        print(f"   Execution completed: {exec_id}")

        # Get performance
        print("\n5. Getting performance metrics...")
        perf = manager.get_sop_performance(sop_id)
        print(f"   Executions: {perf['total_executions']}")
        print(f"   Success rate: {perf['success_rate']:.0%}")
        print(f"   Avg duration: {perf['avg_duration']:.1f} minutes")

        # List SOPs
        print("\n6. Listing SOPs...")
        sops = manager.get_all_sops(status='draft')
        print(f"   Total SOPs: {len(sops)}")

        print(f"\n[OK] SOP Manager working!")
        print(f"Database: {manager.db_path}")

    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        manager.close()


if __name__ == "__main__":
    main()
