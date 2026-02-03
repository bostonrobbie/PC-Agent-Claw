#!/usr/bin/env python3
"""Performance Dashboard Integration (#7)"""
import psutil
from datetime import datetime

class PerformanceMonitor:
    def get_system_stats(self):
        return {
            'timestamp': datetime.now().isoformat(),
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': 0
        }

if __name__ == "__main__":
    monitor = PerformanceMonitor()
    print("Stats:", monitor.get_system_stats())
