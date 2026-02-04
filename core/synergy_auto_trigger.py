"""
Synergy Auto-Trigger System - HIGH PRIORITY IMPROVEMENT #1

Automatically triggers high-impact synergy patterns when conditions are met.
Based on real data showing "Synergy between DemoStep1, DemoStep2" with 40% efficiency boost.
"""

import sqlite3
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Callable
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SynergyAutoTrigger:
    """
    Automatically executes synergy patterns when conditions met

    Monitors for pattern conditions and auto-triggers chains for maximum efficiency.
    """

    def __init__(self, synergy_system, db_path: str = "synergy_auto_trigger.db"):
        self.synergy = synergy_system
        self.db_path = db_path
        self.running = False
        self.monitor_thread = None
        self.triggers: Dict[str, Dict] = {}

        self._init_db()
        self._register_default_triggers()

    def _init_db(self):
        """Initialize auto-trigger database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS auto_triggers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_name TEXT,
                chain_name TEXT,
                condition_type TEXT,
                condition_config TEXT,
                enabled INTEGER DEFAULT 1,
                trigger_count INTEGER DEFAULT 0,
                last_triggered TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trigger_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trigger_id INTEGER,
                pattern_name TEXT,
                chain_name TEXT,
                triggered_at TEXT,
                execution_result TEXT,
                success INTEGER,
                FOREIGN KEY (trigger_id) REFERENCES auto_triggers(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pattern_conditions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_name TEXT,
                condition_type TEXT,
                condition_value TEXT,
                last_checked TEXT,
                condition_met INTEGER DEFAULT 0
            )
        ''')

        conn.commit()
        conn.close()

    def _register_default_triggers(self):
        """Register default auto-triggers based on discovered patterns"""

        # Trigger for top synergy pattern (from real data analysis)
        self.register_trigger(
            pattern_name="DemoStep1_DemoStep2_synergy",
            chain_name="discovery_learning_chain",
            condition_type="impact_threshold",
            condition_config={
                "min_impact_score": 0.3,
                "check_interval_seconds": 60
            },
            enabled=True
        )

        # Trigger for search-analysis synergy
        self.register_trigger(
            pattern_name="Search_Analysis_synergy",
            chain_name="analysis_action_chain",
            condition_type="activity_detected",
            condition_config={
                "activity_type": "semantic_search",
                "min_results": 5
            },
            enabled=True
        )

    def register_trigger(self, pattern_name: str, chain_name: str,
                        condition_type: str, condition_config: Dict,
                        enabled: bool = True) -> int:
        """
        Register a new auto-trigger

        Args:
            pattern_name: Name of synergy pattern to trigger
            chain_name: Chain to execute when triggered
            condition_type: Type of condition to check
            condition_config: Configuration for condition checking
            enabled: Whether trigger is active

        Returns:
            Trigger ID
        """
        import json

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO auto_triggers
            (pattern_name, chain_name, condition_type, condition_config, enabled)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            pattern_name,
            chain_name,
            condition_type,
            json.dumps(condition_config),
            1 if enabled else 0
        ))

        trigger_id = cursor.lastrowid

        conn.commit()
        conn.close()

        # Store in memory for fast access
        self.triggers[pattern_name] = {
            'id': trigger_id,
            'chain_name': chain_name,
            'condition_type': condition_type,
            'condition_config': condition_config,
            'enabled': enabled
        }

        logger.info(f"Registered auto-trigger: {pattern_name} -> {chain_name}")

        return trigger_id

    def check_conditions(self, pattern_name: str) -> bool:
        """
        Check if conditions are met for a pattern

        Args:
            pattern_name: Pattern to check

        Returns:
            True if conditions met, False otherwise
        """
        if pattern_name not in self.triggers:
            return False

        trigger = self.triggers[pattern_name]

        if not trigger['enabled']:
            return False

        condition_type = trigger['condition_type']
        config = trigger['condition_config']

        # Check different condition types
        if condition_type == "impact_threshold":
            return self._check_impact_threshold(pattern_name, config)

        elif condition_type == "activity_detected":
            return self._check_activity_detected(config)

        elif condition_type == "time_interval":
            return self._check_time_interval(pattern_name, config)

        elif condition_type == "resource_threshold":
            return self._check_resource_threshold(config)

        return False

    def _check_impact_threshold(self, pattern_name: str, config: Dict) -> bool:
        """Check if pattern impact score is above threshold"""
        min_impact = config.get('min_impact_score', 0.3)

        # Query synergy database for pattern impact
        try:
            conn = sqlite3.connect(self.synergy.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT impact_score FROM synergy_patterns
                WHERE pattern_name = ? OR description LIKE ?
                ORDER BY impact_score DESC
                LIMIT 1
            ''', (pattern_name, f'%{pattern_name}%'))

            row = cursor.fetchone()
            conn.close()

            if row and row[0] >= min_impact:
                logger.info(f"Impact threshold met: {pattern_name} (score: {row[0]:.2f})")
                return True

        except Exception as e:
            logger.error(f"Error checking impact threshold: {e}")

        return False

    def _check_activity_detected(self, config: Dict) -> bool:
        """Check if specific activity was detected"""
        activity_type = config.get('activity_type')
        min_results = config.get('min_results', 1)

        # Check recent activity in synergy flows
        try:
            conn = sqlite3.connect(self.synergy.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT COUNT(*) FROM synergy_flows
                WHERE source_capability LIKE ? OR target_capability LIKE ?
                AND datetime(timestamp) > datetime('now', '-5 minutes')
            ''', (f'%{activity_type}%', f'%{activity_type}%'))

            count = cursor.fetchone()[0]
            conn.close()

            if count >= min_results:
                logger.info(f"Activity detected: {activity_type} ({count} occurrences)")
                return True

        except Exception as e:
            logger.error(f"Error checking activity: {e}")

        return False

    def _check_time_interval(self, pattern_name: str, config: Dict) -> bool:
        """Check if enough time has passed since last trigger"""
        interval_seconds = config.get('interval_seconds', 300)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT last_triggered FROM auto_triggers
            WHERE pattern_name = ?
        ''', (pattern_name,))

        row = cursor.fetchone()
        conn.close()

        if not row or not row[0]:
            return True

        from datetime import datetime
        last_triggered = datetime.fromisoformat(row[0])
        elapsed = (datetime.now() - last_triggered).total_seconds()

        return elapsed >= interval_seconds

    def _check_resource_threshold(self, config: Dict) -> bool:
        """Check if resource usage is below threshold"""
        import psutil

        max_cpu = config.get('max_cpu_percent', 70)
        max_memory_mb = config.get('max_memory_mb', 1024)

        cpu = psutil.cpu_percent(interval=0.1)
        mem_mb = psutil.virtual_memory().used / 1024 / 1024

        return cpu < max_cpu and mem_mb < max_memory_mb

    def trigger_if_ready(self, pattern_name: str, input_data: Optional[Dict] = None) -> Optional[Dict]:
        """
        Check conditions and trigger if ready

        Args:
            pattern_name: Pattern to check
            input_data: Optional input data for chain execution

        Returns:
            Execution result if triggered, None if not triggered
        """
        if not self.check_conditions(pattern_name):
            return None

        trigger = self.triggers.get(pattern_name)
        if not trigger:
            return None

        logger.info(f"AUTO-TRIGGERING: {pattern_name} -> {trigger['chain_name']}")

        # Execute the chain
        try:
            result = self.synergy.execute_chain(
                trigger['chain_name'],
                input_data or {}
            )

            # Record successful trigger
            self._record_trigger_execution(
                trigger['id'],
                pattern_name,
                trigger['chain_name'],
                result,
                success=True
            )

            # Update trigger count
            self._update_trigger_count(trigger['id'])

            return result

        except Exception as e:
            logger.error(f"Auto-trigger execution failed: {e}")

            # Record failed trigger
            self._record_trigger_execution(
                trigger['id'],
                pattern_name,
                trigger['chain_name'],
                {'error': str(e)},
                success=False
            )

            return None

    def _record_trigger_execution(self, trigger_id: int, pattern_name: str,
                                  chain_name: str, result: Dict, success: bool):
        """Record that a trigger was executed"""
        import json

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO trigger_executions
            (trigger_id, pattern_name, chain_name, triggered_at, execution_result, success)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            trigger_id,
            pattern_name,
            chain_name,
            datetime.now().isoformat(),
            json.dumps(result),
            1 if success else 0
        ))

        conn.commit()
        conn.close()

    def _update_trigger_count(self, trigger_id: int):
        """Update trigger count and last triggered time"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE auto_triggers
            SET trigger_count = trigger_count + 1,
                last_triggered = ?
            WHERE id = ?
        ''', (datetime.now().isoformat(), trigger_id))

        conn.commit()
        conn.close()

    def start_monitoring(self, check_interval: int = 60):
        """Start background monitoring for auto-triggers"""
        if self.running:
            logger.warning("Monitoring already running")
            return

        self.running = True
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(check_interval,),
            daemon=True
        )
        self.monitor_thread.start()

        logger.info(f"Auto-trigger monitoring started (interval: {check_interval}s)")

    def _monitoring_loop(self, check_interval: int):
        """Background loop checking for trigger conditions"""
        while self.running:
            try:
                for pattern_name in list(self.triggers.keys()):
                    self.trigger_if_ready(pattern_name)

            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")

            time.sleep(check_interval)

    def stop_monitoring(self):
        """Stop background monitoring"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)

        logger.info("Auto-trigger monitoring stopped")

    def get_stats(self) -> Dict:
        """Get auto-trigger statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Total triggers
        cursor.execute('SELECT COUNT(*) FROM auto_triggers WHERE enabled = 1')
        total_triggers = cursor.fetchone()[0]

        # Total executions
        cursor.execute('SELECT COUNT(*) FROM trigger_executions')
        total_executions = cursor.fetchone()[0]

        # Success rate
        cursor.execute('SELECT COUNT(*) FROM trigger_executions WHERE success = 1')
        successful = cursor.fetchone()[0]
        success_rate = (successful / total_executions * 100) if total_executions > 0 else 0

        # Top patterns
        cursor.execute('''
            SELECT pattern_name, trigger_count
            FROM auto_triggers
            WHERE enabled = 1
            ORDER BY trigger_count DESC
            LIMIT 5
        ''')
        top_patterns = [{'pattern': row[0], 'count': row[1]} for row in cursor.fetchall()]

        conn.close()

        return {
            'total_triggers': total_triggers,
            'total_executions': total_executions,
            'success_rate_percent': success_rate,
            'top_patterns': top_patterns
        }


# Example usage
if __name__ == '__main__':
    # This would normally import CapabilitySynergy
    # from core.capability_synergy import CapabilitySynergy
    # synergy = CapabilitySynergy()

    class MockSynergy:
        def __init__(self):
            self.db_path = "capability_synergy.db"

        def execute_chain(self, chain_name, input_data):
            return {'status': 'completed', 'chain': chain_name}

    synergy = MockSynergy()
    auto_trigger = SynergyAutoTrigger(synergy)

    # Manually check conditions
    result = auto_trigger.trigger_if_ready("DemoStep1_DemoStep2_synergy")
    if result:
        print(f"Auto-triggered successfully: {result}")
    else:
        print("Conditions not met, trigger not executed")

    # Get stats
    stats = auto_trigger.get_stats()
    print(f"\nStats: {stats}")

    # Start monitoring (would run continuously in production)
    # auto_trigger.start_monitoring(check_interval=30)
    # time.sleep(300)  # Monitor for 5 minutes
    # auto_trigger.stop_monitoring()
