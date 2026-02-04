"""
Flow State Monitor - PHASE 1 CRITICAL

Detects productive flow and actively protects it.
"""
import time
from datetime import datetime, timedelta
from typing import List

class FlowStateMonitor:
    def __init__(self):
        self.actions = []
        self.errors = []
        self.in_flow = False
        self.flow_start = None
    
    def record_action(self, action: str):
        """Record an action"""
        self.actions.append({
            'action': action,
            'timestamp': time.time()
        })
        self._check_flow_state()
    
    def record_error(self, error: str):
        """Record an error"""
        self.errors.append({
            'error': error,
            'timestamp': time.time()
        })
        self._check_flow_state()
    
    def _check_flow_state(self):
        """Detect if in productive flow"""
        now = time.time()
        recent_window = 60  # 1 minute
        
        # Count recent actions
        recent_actions = [a for a in self.actions if now - a['timestamp'] < recent_window]
        recent_errors = [e for e in self.errors if now - e['timestamp'] < recent_window]
        
        actions_per_min = len(recent_actions)
        error_rate = len(recent_errors) / max(len(recent_actions), 1)
        
        # Flow = >5 actions/min, <10% errors
        was_in_flow = self.in_flow
        self.in_flow = actions_per_min >= 5 and error_rate < 0.1
        
        if self.in_flow and not was_in_flow:
            self.flow_start = datetime.now()
        elif not self.in_flow and was_in_flow:
            duration = (datetime.now() - self.flow_start).total_seconds()
            print(f"[Flow] Maintained for {duration:.0f}s")
    
    def is_in_flow(self) -> bool:
        """Check if currently in flow"""
        return self.in_flow
    
    def should_protect_flow(self) -> bool:
        """Whether to suppress interruptions"""
        return self.in_flow
    
    def get_stats(self) -> dict:
        now = time.time()
        recent = [a for a in self.actions if now - a['timestamp'] < 300]
        
        return {
            'in_flow': self.in_flow,
            'actions_last_5min': len(recent),
            'flow_duration': (datetime.now() - self.flow_start).total_seconds() if self.flow_start else 0
        }
