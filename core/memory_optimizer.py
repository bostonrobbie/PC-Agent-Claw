"""
Memory Optimization System - MEDIUM PRIORITY IMPROVEMENT #3

Optimizes memory usage across all capabilities based on real-world testing data.
"""

import gc
import sys
import sqlite3
import psutil
from datetime import datetime
from typing import Dict, List, Optional
import weakref
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MemoryOptimizer:
    """
    Reduces memory footprint through intelligent optimization

    Based on real-world testing showing memory usage patterns.
    """

    def __init__(self, db_path: str = "memory_optimizer.db"):
        self.db_path = db_path
        self.memory_pools: Dict[str, List] = {}
        self.weak_caches: Dict[str, weakref.WeakValueDictionary] = {}
        self._init_db()

    def _init_db(self):
        """Initialize optimization tracking database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memory_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                total_mb REAL,
                available_mb REAL,
                used_percent REAL,
                process_mb REAL,
                optimization_applied TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS optimization_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_type TEXT,
                timestamp TEXT,
                memory_before_mb REAL,
                memory_after_mb REAL,
                freed_mb REAL,
                target_component TEXT
            )
        ''')

        conn.commit()
        conn.close()

    def get_memory_snapshot(self) -> Dict:
        """Get current memory usage snapshot"""
        mem = psutil.virtual_memory()
        process = psutil.Process()
        process_mem = process.memory_info().rss / 1024 / 1024

        return {
            'total_mb': mem.total / 1024 / 1024,
            'available_mb': mem.available / 1024 / 1024,
            'used_percent': mem.percent,
            'process_mb': process_mem,
            'timestamp': datetime.now().isoformat()
        }

    def record_snapshot(self, optimization_applied: Optional[str] = None):
        """Record memory snapshot to database"""
        snapshot = self.get_memory_snapshot()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO memory_snapshots
            (timestamp, total_mb, available_mb, used_percent, process_mb, optimization_applied)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            snapshot['timestamp'],
            snapshot['total_mb'],
            snapshot['available_mb'],
            snapshot['used_percent'],
            snapshot['process_mb'],
            optimization_applied or ''
        ))

        conn.commit()
        conn.close()

        return snapshot

    def optimize_databases(self) -> Dict:
        """Optimize database memory usage"""
        before = self.get_memory_snapshot()

        import glob
        db_files = glob.glob("*.db")
        optimized = 0

        for db_file in db_files:
            try:
                conn = sqlite3.connect(db_file)
                cursor = conn.cursor()

                # Vacuum to reclaim space
                cursor.execute('VACUUM')

                # Analyze to update statistics
                cursor.execute('ANALYZE')

                conn.commit()
                conn.close()

                optimized += 1

            except Exception as e:
                logger.warning(f"Could not optimize {db_file}: {e}")

        after = self.get_memory_snapshot()
        freed_mb = before['process_mb'] - after['process_mb']

        self._record_optimization(
            'database_vacuum',
            before['process_mb'],
            after['process_mb'],
            freed_mb,
            f"{optimized} databases"
        )

        return {
            'databases_optimized': optimized,
            'memory_freed_mb': freed_mb,
            'before_mb': before['process_mb'],
            'after_mb': after['process_mb']
        }

    def garbage_collect_aggressive(self) -> Dict:
        """Perform aggressive garbage collection"""
        before = self.get_memory_snapshot()

        # Run garbage collection multiple times
        for _ in range(3):
            collected = gc.collect()

        after = self.get_memory_snapshot()
        freed_mb = before['process_mb'] - after['process_mb']

        self._record_optimization(
            'garbage_collection',
            before['process_mb'],
            after['process_mb'],
            freed_mb,
            'aggressive_gc'
        )

        return {
            'memory_freed_mb': freed_mb,
            'before_mb': before['process_mb'],
            'after_mb': after['process_mb']
        }

    def create_weak_cache(self, cache_name: str) -> weakref.WeakValueDictionary:
        """
        Create a weak reference cache

        Objects are automatically removed when no longer referenced elsewhere.
        """
        cache = weakref.WeakValueDictionary()
        self.weak_caches[cache_name] = cache

        logger.info(f"Created weak cache: {cache_name}")

        return cache

    def create_memory_pool(self, pool_name: str, max_size: int = 100) -> List:
        """
        Create a memory pool for reusable objects

        Args:
            pool_name: Name of the pool
            max_size: Maximum objects to pool

        Returns:
            List to use as object pool
        """
        pool = []
        self.memory_pools[pool_name] = {
            'pool': pool,
            'max_size': max_size,
            'hits': 0,
            'misses': 0
        }

        logger.info(f"Created memory pool: {pool_name} (max: {max_size})")

        return pool

    def get_from_pool(self, pool_name: str, factory: callable):
        """Get object from pool or create new one"""
        if pool_name not in self.memory_pools:
            return factory()

        pool_data = self.memory_pools[pool_name]
        pool = pool_data['pool']

        if pool:
            pool_data['hits'] += 1
            return pool.pop()
        else:
            pool_data['misses'] += 1
            return factory()

    def return_to_pool(self, pool_name: str, obj):
        """Return object to pool for reuse"""
        if pool_name not in self.memory_pools:
            return

        pool_data = self.memory_pools[pool_name]
        pool = pool_data['pool']

        if len(pool) < pool_data['max_size']:
            pool.append(obj)

    def clear_large_objects(self, min_size_mb: float = 10.0) -> Dict:
        """Clear large objects from memory"""
        before = self.get_memory_snapshot()

        import sys
        cleared = 0

        # Find large objects
        for obj in gc.get_objects():
            try:
                size_mb = sys.getsizeof(obj) / 1024 / 1024
                if size_mb >= min_size_mb:
                    # Clear if it's a clearable container
                    if isinstance(obj, (list, dict, set)):
                        obj.clear()
                        cleared += 1
            except:
                pass

        gc.collect()

        after = self.get_memory_snapshot()
        freed_mb = before['process_mb'] - after['process_mb']

        self._record_optimization(
            'clear_large_objects',
            before['process_mb'],
            after['process_mb'],
            freed_mb,
            f"{cleared} objects"
        )

        return {
            'objects_cleared': cleared,
            'memory_freed_mb': freed_mb,
            'before_mb': before['process_mb'],
            'after_mb': after['process_mb']
        }

    def optimize_all(self) -> Dict:
        """Run all optimization strategies"""
        logger.info("Running comprehensive memory optimization...")

        before = self.get_memory_snapshot()

        # Run optimizations
        db_result = self.optimize_databases()
        gc_result = self.garbage_collect_aggressive()
        clear_result = self.clear_large_objects()

        after = self.get_memory_snapshot()

        total_freed = before['process_mb'] - after['process_mb']

        result = {
            'total_freed_mb': total_freed,
            'before_mb': before['process_mb'],
            'after_mb': after['process_mb'],
            'reduction_percent': (total_freed / before['process_mb'] * 100) if before['process_mb'] > 0 else 0,
            'database_optimization': db_result,
            'garbage_collection': gc_result,
            'large_objects_cleared': clear_result
        }

        logger.info(f"Optimization complete: {total_freed:.2f} MB freed ({result['reduction_percent']:.1f}% reduction)")

        return result

    def _record_optimization(self, action_type: str, before_mb: float,
                            after_mb: float, freed_mb: float, target: str):
        """Record optimization action"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO optimization_actions
            (action_type, timestamp, memory_before_mb, memory_after_mb, freed_mb, target_component)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            action_type,
            datetime.now().isoformat(),
            before_mb,
            after_mb,
            freed_mb,
            target
        ))

        conn.commit()
        conn.close()

    def get_optimization_stats(self) -> Dict:
        """Get optimization statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Total freed
        cursor.execute('SELECT SUM(freed_mb) FROM optimization_actions')
        total_freed = cursor.fetchone()[0] or 0

        # By action type
        cursor.execute('''
            SELECT action_type, COUNT(*), SUM(freed_mb)
            FROM optimization_actions
            GROUP BY action_type
            ORDER BY SUM(freed_mb) DESC
        ''')
        by_type = [
            {'action': row[0], 'count': row[1], 'freed_mb': row[2]}
            for row in cursor.fetchall()
        ]

        # Pool stats
        pool_stats = {}
        for name, data in self.memory_pools.items():
            hit_rate = (data['hits'] / (data['hits'] + data['misses']) * 100) if (data['hits'] + data['misses']) > 0 else 0
            pool_stats[name] = {
                'size': len(data['pool']),
                'max_size': data['max_size'],
                'hits': data['hits'],
                'misses': data['misses'],
                'hit_rate_percent': hit_rate
            }

        conn.close()

        return {
            'total_freed_mb': total_freed,
            'optimizations_by_type': by_type,
            'memory_pools': pool_stats
        }

    def auto_optimize_if_needed(self, threshold_mb: float = 1024.0):
        """Automatically optimize if memory usage exceeds threshold"""
        snapshot = self.get_memory_snapshot()

        if snapshot['process_mb'] > threshold_mb:
            logger.warning(f"Memory threshold exceeded: {snapshot['process_mb']:.1f} MB > {threshold_mb} MB")
            result = self.optimize_all()
            logger.info(f"Auto-optimization freed {result['total_freed_mb']:.2f} MB")
            return result

        return None


# Example usage
if __name__ == '__main__':
    optimizer = MemoryOptimizer()

    # Get initial snapshot
    print("Initial memory snapshot:")
    snapshot = optimizer.record_snapshot()
    print(f"  Process using: {snapshot['process_mb']:.1f} MB")
    print(f"  System: {snapshot['used_percent']:.1f}% used")

    # Create a memory pool
    connection_pool = optimizer.create_memory_pool('db_connections', max_size=10)

    # Optimize everything
    print("\nRunning comprehensive optimization...")
    result = optimizer.optimize_all()

    print(f"\nResults:")
    print(f"  Before: {result['before_mb']:.1f} MB")
    print(f"  After: {result['after_mb']:.1f} MB")
    print(f"  Freed: {result['total_freed_mb']:.1f} MB ({result['reduction_percent']:.1f}% reduction)")

    # Get stats
    print("\nOptimization statistics:")
    stats = optimizer.get_optimization_stats()
    print(f"  Total freed (lifetime): {stats['total_freed_mb']:.1f} MB")
    print(f"  Optimizations by type:")
    for opt in stats['optimizations_by_type']:
        print(f"    {opt['action']}: {opt['count']} times, {opt['freed_mb']:.1f} MB")
