#!/usr/bin/env python3
"""
Scalability Integration Module

Provides easy integration of all scalability features:
- Dynamic Worker Scaling
- Result Caching
- Database Connection Pooling
- Web Dashboard

This module serves as a central integration point for all systems.
"""
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import atexit

sys.path.append(str(Path(__file__).parent.parent))

from autonomous.background_tasks import BackgroundTaskManager, TaskPriority
from core.result_cache import ResultCache, get_cache
from core.db_pool import ConnectionPool, get_pool, close_all_pools


class ScalabilityManager:
    """
    Central manager for all scalability features

    Usage:
        # Initialize
        scalability = ScalabilityManager()

        # Use cached operations
        @scalability.cache.cached(ttl=300)
        def expensive_operation():
            return compute_something()

        # Use database pool
        with scalability.db_pool.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM table")

        # Queue background task
        scalability.task_manager.queue_task('task_type', 'Description')

        # Start web dashboard
        scalability.start_dashboard(port=8080)
    """

    def __init__(self, workspace_path: Optional[Path] = None,
                 cache_size: int = 1000,
                 cache_ttl: int = 3600,
                 db_pool_min: int = 2,
                 db_pool_max: int = 10,
                 worker_min: int = 1,
                 worker_max: int = 8,
                 enable_auto_scaling: bool = True,
                 enable_persistent_cache: bool = True):
        """
        Initialize scalability manager

        Args:
            workspace_path: Path to workspace (default: auto-detect)
            cache_size: Maximum cache entries
            cache_ttl: Default cache TTL in seconds
            db_pool_min: Minimum database connections
            db_pool_max: Maximum database connections
            worker_min: Minimum background workers
            worker_max: Maximum background workers
            enable_auto_scaling: Enable dynamic worker scaling
            enable_persistent_cache: Enable persistent cache storage
        """
        # Detect workspace
        if workspace_path is None:
            workspace_path = Path(__file__).parent.parent

        self.workspace = workspace_path

        # Initialize result cache
        cache_db = str(self.workspace / "result_cache.db") if enable_persistent_cache else None
        self.cache = ResultCache(
            max_size=cache_size,
            default_ttl=cache_ttl,
            enable_persistent=enable_persistent_cache,
            db_path=cache_db
        )

        # Initialize database connection pools
        self.db_pools: Dict[str, ConnectionPool] = {}
        self.db_pool_config = {
            'min_size': db_pool_min,
            'max_size': db_pool_max
        }

        # Initialize background task manager
        self.task_manager = BackgroundTaskManager(
            db_path=str(self.workspace / "background_tasks.db"),
            min_workers=worker_min,
            max_workers=worker_max,
            enable_auto_scaling=enable_auto_scaling
        )

        # Web dashboard (initialized on demand)
        self.dashboard = None

        # Register cleanup
        atexit.register(self.cleanup)

    def get_db_pool(self, db_name: str = "main") -> ConnectionPool:
        """
        Get or create database connection pool

        Args:
            db_name: Name of database (without .db extension)

        Returns:
            ConnectionPool instance
        """
        if db_name not in self.db_pools:
            db_path = str(self.workspace / f"{db_name}.db")
            self.db_pools[db_name] = get_pool(
                db_path,
                min_size=self.db_pool_config['min_size'],
                max_size=self.db_pool_config['max_size']
            )

        return self.db_pools[db_name]

    @property
    def db_pool(self) -> ConnectionPool:
        """Get default database pool"""
        return self.get_db_pool("main")

    def start_workers(self):
        """Start background task workers"""
        self.task_manager.start_workers()

    def stop_workers(self):
        """Stop background task workers"""
        self.task_manager.stop_workers()

    def start_dashboard(self, port: int = 8080, host: str = "0.0.0.0"):
        """
        Start web dashboard

        Args:
            port: Port to listen on
            host: Host to bind to
        """
        try:
            from web.dashboard import DashboardServer

            self.dashboard = DashboardServer(port=port)

            # Start in separate thread
            import threading
            dashboard_thread = threading.Thread(
                target=self.dashboard.start,
                daemon=True
            )
            dashboard_thread.start()

            print(f"[SCALABILITY] Dashboard started on http://{host}:{port}")

        except ImportError:
            print("[SCALABILITY] Dashboard not available. Install: pip install fastapi uvicorn websockets")

    def get_status(self) -> Dict[str, Any]:
        """
        Get comprehensive status of all scalability features

        Returns:
            Status dictionary
        """
        status = {
            'cache': self.cache.get_stats(),
            'workers': self.task_manager.get_worker_stats(),
            'db_pools': {}
        }

        for name, pool in self.db_pools.items():
            status['db_pools'][name] = pool.get_stats()

        return status

    def cleanup(self):
        """Cleanup all resources"""
        print("[SCALABILITY] Cleaning up resources...")

        # Stop workers
        if self.task_manager:
            self.task_manager.close()

        # Close cache
        if self.cache:
            self.cache.close()

        # Close all database pools
        for pool in self.db_pools.values():
            pool.close_all()

        # Stop dashboard
        if self.dashboard:
            self.dashboard.stop()

        print("[SCALABILITY] Cleanup complete")


# Global instance for easy access
_global_manager: Optional[ScalabilityManager] = None


def get_manager(**kwargs) -> ScalabilityManager:
    """
    Get global scalability manager (singleton)

    Args:
        **kwargs: Configuration options (only used on first call)

    Returns:
        ScalabilityManager instance
    """
    global _global_manager

    if _global_manager is None:
        _global_manager = ScalabilityManager(**kwargs)

    return _global_manager


# Convenience functions for direct access

def cached(ttl: int = 3600, tags: list = None):
    """
    Decorator for caching function results

    Args:
        ttl: Cache TTL in seconds
        tags: Tags for invalidation

    Example:
        from core.scalability_integration import cached

        @cached(ttl=300)
        def expensive_operation(x, y):
            return x + y
    """
    manager = get_manager()
    return manager.cache.cached(ttl=ttl, tags=tags)


def with_db_pool(db_name: str = "main"):
    """
    Get database connection from pool

    Args:
        db_name: Database name

    Example:
        from core.scalability_integration import with_db_pool

        with with_db_pool() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM table")
    """
    manager = get_manager()
    return manager.get_db_pool(db_name).connection()


def queue_task(task_type: str, description: str = None,
               priority: TaskPriority = TaskPriority.MEDIUM,
               context: dict = None) -> int:
    """
    Queue a background task

    Args:
        task_type: Type of task
        description: Task description
        priority: Task priority
        context: Task context data

    Returns:
        Task ID

    Example:
        from core.scalability_integration import queue_task, TaskPriority

        task_id = queue_task('process_data', 'Process user data',
                            TaskPriority.HIGH, {'user_id': 123})
    """
    manager = get_manager()
    return manager.task_manager.queue_task(task_type, description, priority, context)


def main():
    """Demo of scalability integration"""
    print("=" * 70)
    print("Scalability Integration Demo")
    print("=" * 70)

    # Initialize manager
    manager = ScalabilityManager(
        cache_size=100,
        cache_ttl=300,
        worker_min=1,
        worker_max=4,
        enable_auto_scaling=True
    )

    print("\n1. Starting background workers...")
    manager.start_workers()

    print("\n2. Testing cached operations...")

    @manager.cache.cached(ttl=60)
    def fibonacci(n):
        if n <= 1:
            return n
        return fibonacci(n-1) + fibonacci(n-2)

    import time
    start = time.time()
    result1 = fibonacci(10)
    time1 = time.time() - start

    start = time.time()
    result2 = fibonacci(10)
    time2 = time.time() - start

    print(f"   First call: {result1} ({time1*1000:.2f}ms)")
    print(f"   Second call (cached): {result2} ({time2*1000:.2f}ms)")
    print(f"   Speedup: {time1/time2:.1f}x")

    print("\n3. Testing database pool...")
    pool = manager.get_db_pool("test")

    # Create test table
    with pool.connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS test_data (
                id INTEGER PRIMARY KEY,
                value TEXT
            )
        ''')
        conn.execute("INSERT INTO test_data (value) VALUES (?)", ("test",))
        conn.commit()

    # Query data
    with pool.connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM test_data")
        count = cursor.fetchone()['count']
        print(f"   Records in database: {count}")

    print("\n4. Testing background tasks...")

    @manager.task_manager.register_handler('demo_task')
    def demo_handler(context):
        value = context.get('value', 0)
        result = value * 2
        manager.cache.set(f'demo_result_{value}', result)
        return {'success': True, 'result': result}

    task_id = manager.task_manager.queue_task(
        'demo_task',
        'Demo task',
        TaskPriority.HIGH,
        {'value': 21}
    )
    print(f"   Queued task ID: {task_id}")

    time.sleep(2)  # Wait for task completion

    status = manager.task_manager.get_task_status(task_id)
    print(f"   Task status: {status['status']}")

    cached_result = manager.cache.get('demo_result_21')
    print(f"   Cached result: {cached_result}")

    print("\n5. System status:")
    status = manager.get_status()

    print(f"   Cache:")
    print(f"     - Size: {status['cache']['size']}/{status['cache']['max_size']}")
    print(f"     - Hit rate: {status['cache']['hit_rate']*100:.1f}%")

    print(f"   Workers:")
    print(f"     - Current: {status['workers']['current_workers']}/{status['workers']['max_workers']}")
    print(f"     - Queue depth: {status['workers']['queue_depth']}")

    for name, pool_stats in status['db_pools'].items():
        print(f"   DB Pool ({name}):")
        print(f"     - Connections: {pool_stats['current_size']} (available: {pool_stats['available']})")
        print(f"     - Acquisitions: {pool_stats['acquisitions']}")

    print("\n[OK] Scalability Integration Working!")

    # Cleanup
    manager.cleanup()


if __name__ == "__main__":
    main()
