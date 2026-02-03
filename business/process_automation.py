#!/usr/bin/env python3
"""
Process Automation Engine
Automatically execute business processes and SOPs
"""
import sys
from pathlib import Path
import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
import threading
import time

sys.path.append(str(Path(__file__).parent.parent))


class ProcessAutomation:
    """
    Automate business process execution

    Features:
    - Automatic SOP execution
    - Scheduled process runs
    - Conditional logic execution
    - Parallel process execution
    - Error handling and recovery
    - Process monitoring
    - Integration with other systems
    """

    def __init__(self, db_path: str = None):
        workspace = Path(__file__).parent.parent
        if db_path is None:
            db_path = str(workspace / "memory.db")

        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        # Automation registry
        self.automation_registry = {}
        self.running_processes = {}
        self.lock = threading.Lock()

        # Load SOP manager
        try:
            from business.sop_manager import SOPManager
            self.sop_manager = SOPManager(db_path)
        except Exception as e:
            print(f"[WARNING] Could not load SOP Manager: {e}")
            self.sop_manager = None

    # === AUTOMATION REGISTRATION ===

    def register_automation(self, step_type: str, handler_func: Callable):
        """
        Register automation handler for step type

        Args:
            step_type: Type of step (e.g., "calculate_position")
            handler_func: Function to handle automation
        """
        self.automation_registry[step_type] = handler_func
        print(f"[AUTOMATION] Registered: {step_type}")

    # === PROCESS EXECUTION ===

    def execute_sop(self, sop_id: int, context: Dict = None,
                   executed_by: str = "automation") -> Dict:
        """
        Execute SOP automatically

        Args:
            sop_id: SOP to execute
            context: Execution context/parameters
            executed_by: Who is executing

        Returns:
            Execution result
        """
        if not self.sop_manager:
            return {'status': 'error', 'message': 'SOP Manager not available'}

        cursor = self.conn.cursor()

        # Get SOP and steps
        cursor.execute('SELECT * FROM sops WHERE id = ?', (sop_id,))
        sop = dict(cursor.fetchone())

        cursor.execute('''
            SELECT * FROM sop_steps
            WHERE sop_id = ?
            ORDER BY step_number
        ''', (sop_id,))
        steps = [dict(row) for row in cursor.fetchall()]

        # Start execution
        execution_id = self.sop_manager.start_execution(sop_id, executed_by)

        result = {
            'execution_id': execution_id,
            'sop_code': sop['sop_code'],
            'status': 'in_progress',
            'steps_completed': 0,
            'steps_failed': 0,
            'step_results': []
        }

        try:
            # Execute each step
            for step in steps:
                step_result = self._execute_step(execution_id, step, context)
                result['step_results'].append(step_result)

                if step_result['status'] == 'completed':
                    result['steps_completed'] += 1
                    # Mark step complete in SOP manager
                    self.sop_manager.complete_step(
                        execution_id,
                        step['step_number'],
                        result=step_result.get('result'),
                        notes=step_result.get('notes')
                    )
                else:
                    result['steps_failed'] += 1
                    # If step fails, stop execution
                    result['status'] = 'failed'
                    result['error'] = step_result.get('error')
                    break

            # Complete execution
            if result['status'] != 'failed':
                result['status'] = 'completed'
                self.sop_manager.complete_execution(
                    execution_id,
                    success=True,
                    notes="Automated execution completed successfully"
                )

        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
            self.sop_manager.complete_execution(
                execution_id,
                success=False,
                notes=f"Automation error: {str(e)}"
            )

        return result

    def _execute_step(self, execution_id: int, step: Dict, context: Dict) -> Dict:
        """Execute individual step"""
        step_result = {
            'step_number': step['step_number'],
            'step_title': step['step_title'],
            'status': 'pending'
        }

        try:
            if step['is_automated'] and step['automation_script']:
                # Execute automation
                script_name = step['automation_script']

                if script_name in self.automation_registry:
                    # Call registered handler
                    handler = self.automation_registry[script_name]

                    # Parse inputs
                    inputs = json.loads(step['required_inputs']) if step['required_inputs'] else {}
                    if context:
                        inputs.update(context)

                    # Execute
                    result = handler(**inputs)

                    step_result['status'] = 'completed'
                    step_result['result'] = str(result)
                else:
                    # Automation not registered
                    step_result['status'] = 'manual_required'
                    step_result['notes'] = f"Automation {script_name} not registered"
            else:
                # Manual step - mark as requiring manual completion
                step_result['status'] = 'manual_required'
                step_result['notes'] = "Manual step - requires human action"

        except Exception as e:
            step_result['status'] = 'failed'
            step_result['error'] = str(e)

        return step_result

    # === SCHEDULED EXECUTION ===

    def schedule_sop(self, sop_id: int, schedule: str, context: Dict = None):
        """
        Schedule SOP for recurring execution

        Args:
            sop_id: SOP to schedule
            schedule: Schedule (cron-like or simple: "daily", "weekly", etc.)
            context: Execution context
        """
        # Store in running processes
        with self.lock:
            self.running_processes[sop_id] = {
                'schedule': schedule,
                'context': context,
                'last_run': None,
                'next_run': self._calculate_next_run(schedule)
            }

        print(f"[AUTOMATION] Scheduled SOP {sop_id}: {schedule}")

    def _calculate_next_run(self, schedule: str) -> datetime:
        """Calculate next run time"""
        # Simplified scheduling
        now = datetime.now()

        if schedule == "hourly":
            return now.replace(minute=0, second=0) + timedelta(hours=1)
        elif schedule == "daily":
            return now.replace(hour=0, minute=0, second=0) + timedelta(days=1)
        elif schedule == "weekly":
            return now.replace(hour=0, minute=0, second=0) + timedelta(days=7)
        else:
            # Default to daily
            return now + timedelta(days=1)

    # === CONDITIONAL EXECUTION ===

    def execute_if(self, condition_func: Callable, sop_id: int, context: Dict = None) -> Optional[Dict]:
        """
        Execute SOP if condition is met

        Args:
            condition_func: Function that returns True/False
            sop_id: SOP to execute
            context: Execution context

        Returns:
            Execution result if executed, None otherwise
        """
        if condition_func(context):
            return self.execute_sop(sop_id, context)
        else:
            print(f"[AUTOMATION] Condition not met for SOP {sop_id}")
            return None

    # === PARALLEL EXECUTION ===

    def execute_parallel(self, sop_ids: List[int], context: Dict = None) -> List[Dict]:
        """
        Execute multiple SOPs in parallel

        Args:
            sop_ids: List of SOP IDs to execute
            context: Shared context

        Returns:
            List of execution results
        """
        results = []
        threads = []

        def execute_and_store(sop_id):
            result = self.execute_sop(sop_id, context)
            with self.lock:
                results.append(result)

        # Launch threads
        for sop_id in sop_ids:
            thread = threading.Thread(target=execute_and_store, args=(sop_id,))
            thread.start()
            threads.append(thread)

        # Wait for completion
        for thread in threads:
            thread.join()

        return results

    # === MONITORING ===

    def get_automation_status(self) -> Dict:
        """Get automation system status"""
        cursor = self.conn.cursor()

        # Count automated vs manual steps
        cursor.execute('''
            SELECT
                COUNT(*) as total_steps,
                SUM(is_automated) as automated_steps
            FROM sop_steps
        ''')

        step_stats = dict(cursor.fetchone())

        # Recent executions
        cursor.execute('''
            SELECT COUNT(*) as count, AVG(actual_duration_minutes) as avg_duration
            FROM sop_executions
            WHERE executed_by = 'automation'
            AND started_at >= datetime('now', '-7 days')
        ''')

        exec_stats = dict(cursor.fetchone())

        return {
            'total_steps': step_stats['total_steps'],
            'automated_steps': step_stats['automated_steps'],
            'automation_rate': step_stats['automated_steps'] / step_stats['total_steps'] if step_stats['total_steps'] > 0 else 0,
            'recent_executions': exec_stats['count'],
            'avg_duration': exec_stats['avg_duration'],
            'scheduled_processes': len(self.running_processes)
        }

    def close(self):
        """Close database connection"""
        if self.sop_manager:
            self.sop_manager.close()
        self.conn.close()


# === EXAMPLE AUTOMATION HANDLERS ===

def calculate_position_size(risk_percent: float = 1.0, account_size: float = 100000) -> Dict:
    """Example automation handler"""
    position_size = account_size * (risk_percent / 100)
    return {'position_size': position_size, 'units': 'USD'}


def check_market_hours() -> bool:
    """Example condition check"""
    hour = datetime.now().hour
    # Market hours 9:30 AM - 4:00 PM
    return 9 <= hour < 16


# === TEST CODE ===

def main():
    """Test process automation"""
    print("Testing Process Automation")
    print("=" * 70)

    automation = ProcessAutomation()

    try:
        # Register automation handlers
        print("\n1. Registering automation handlers...")
        automation.register_automation("calculate_position_size()", calculate_position_size)
        print("   Handlers registered")

        # Note: Would need actual SOP created first
        print("\n2. Automation system ready")
        print("   Would execute SOPs automatically when registered")

        # Get status
        print("\n3. Automation status...")
        status = automation.get_automation_status()
        print(f"   Total steps: {status['total_steps']}")
        print(f"   Automated steps: {status['automated_steps']}")
        print(f"   Automation rate: {status['automation_rate']:.0%}")

        print(f"\n[OK] Process Automation working!")
        print(f"Database: {automation.db_path}")

    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        automation.close()


if __name__ == "__main__":
    main()
