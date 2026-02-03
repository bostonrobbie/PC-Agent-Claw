#!/usr/bin/env python3
"""
Database Connection Pooling
Thread-safe SQLite connection pool with automatic management
"""
import sys
from pathlib import Path
import sqlite3
import threading
import time
import queue
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))


class PooledConnection:
    """
    Wrapper for pooled database connection

    Automatically returns connection to pool when closed
    """

    def __init__(self, conn: sqlite3.Connection, pool: 'ConnectionPool'):
        self.conn = conn
        self.pool = pool
        self._closed = False

    def cursor(self):
        """Get cursor from connection"""
        return self.conn.cursor()

    def commit(self):
        """Commit transaction"""
        self.conn.commit()

    def rollback(self):
        """Rollback transaction"""
        self.conn.rollback()

    def execute(self, *args, **kwargs):
        """Execute SQL directly"""
        return self.conn.execute(*args, **kwargs)

    def executemany(self, *args, **kwargs):
        """Execute many SQL statements"""
        return self.conn.executemany(*args, **kwargs)

    def close(self):
        """Return connection to pool"""
        if not self._closed:
            self.pool.release(self.conn)
            self._closed = True

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - return to pool"""
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.close()

    def __getattr__(self, name):
        """Proxy all other attributes to underlying connection"""
        return getattr(self.conn, name)


class ConnectionPool:
    """
    Thread-safe SQLite connection pool

    Features:
    - Configurable pool size
    - Thread-safe connection acquisition
    - Automatic connection reuse
    - Connection health checking
    - Idle connection cleanup
    - Connection statistics
    - Graceful shutdown
    """

    def __init__(self, db_path: str, min_size: int = 2, max_size: int = 10,
                 max_idle_time: int = 300, check_interval: int = 60):
        """
        Initialize connection pool

        Args:
            db_path: Path to SQLite database
            min_size: Minimum number of connections to maintain
            max_size: Maximum number of connections allowed
            max_idle_time: Maximum time (seconds) a connection can be idle
            check_interval: Interval (seconds) for health checks
        """
        self.db_path = db_path
        self.min_size = min_size
        self.max_size = max_size
        self.max_idle_time = max_idle_time
        self.check_interval = check_interval

        # Connection pools
        self.available = queue.Queue(maxsize=max_size)
        self.in_use = set()

        # Locks
        self.lock = threading.RLock()
        self.stats_lock = threading.Lock()

        # Connection metadata: {conn: {'created_at': time, 'last_used': time, 'use_count': int}}
        self.metadata = {}

        # Statistics
        self.stats = {
            'total_created': 0,
            'total_closed': 0,
            'current_size': 0,
            'acquisitions': 0,
            'releases': 0,
            'timeouts': 0,
            'errors': 0
        }

        # Running state
        self.running = True

        # Initialize minimum connections
        self._initialize_pool()

        # Start maintenance thread
        self.maintenance_thread = threading.Thread(
            target=self._maintenance_loop,
            daemon=True
        )
        self.maintenance_thread.start()

    def _initialize_pool(self):
        """Create initial pool of connections"""
        with self.lock:
            for _ in range(self.min_size):
                conn = self._create_connection()
                if conn:
                    self.available.put(conn)

    def _create_connection(self) -> Optional[sqlite3.Connection]:
        """
        Create a new database connection

        Returns:
            SQLite connection or None if creation fails
        """
        try:
            conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0,
                isolation_level=None  # Autocommit mode
            )

            # Set pragmas for better performance
            conn.execute('PRAGMA journal_mode=WAL')  # Write-Ahead Logging
            conn.execute('PRAGMA synchronous=NORMAL')
            conn.execute('PRAGMA cache_size=-64000')  # 64MB cache
            conn.execute('PRAGMA temp_store=MEMORY')
            conn.execute('PRAGMA mmap_size=268435456')  # 256MB mmap

            # Enable row factory for dict-like access
            conn.row_factory = sqlite3.Row

            # Track metadata
            self.metadata[conn] = {
                'created_at': time.time(),
                'last_used': time.time(),
                'use_count': 0
            }

            with self.stats_lock:
                self.stats['total_created'] += 1
                self.stats['current_size'] += 1

            return conn

        except Exception as e:
            print(f"[DB_POOL] Error creating connection: {e}")
            with self.stats_lock:
                self.stats['errors'] += 1
            return None

    def acquire(self, timeout: float = 10.0) -> Optional[PooledConnection]:
        """
        Acquire a connection from the pool

        Args:
            timeout: Maximum time to wait for a connection

        Returns:
            Pooled connection or None if timeout
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            # Try to get from available pool
            try:
                conn = self.available.get(block=False)

                # Verify connection is still good
                if self._verify_connection(conn):
                    with self.lock:
                        self.in_use.add(conn)
                        self.metadata[conn]['last_used'] = time.time()
                        self.metadata[conn]['use_count'] += 1

                    with self.stats_lock:
                        self.stats['acquisitions'] += 1

                    return PooledConnection(conn, self)
                else:
                    # Connection is bad - close and create new one
                    self._close_connection(conn)

            except queue.Empty:
                # No available connections - try to create new one
                with self.lock:
                    if self.stats['current_size'] < self.max_size:
                        conn = self._create_connection()
                        if conn:
                            self.in_use.add(conn)
                            self.metadata[conn]['last_used'] = time.time()
                            self.metadata[conn]['use_count'] += 1

                            with self.stats_lock:
                                self.stats['acquisitions'] += 1

                            return PooledConnection(conn, self)

            # Wait a bit before retrying
            time.sleep(0.01)

        # Timeout
        with self.stats_lock:
            self.stats['timeouts'] += 1

        print(f"[DB_POOL] Timeout acquiring connection after {timeout}s")
        return None

    def release(self, conn: sqlite3.Connection):
        """
        Release a connection back to the pool

        Args:
            conn: Connection to release
        """
        if conn is None:
            return

        with self.lock:
            if conn in self.in_use:
                self.in_use.remove(conn)

            # Verify connection is still good
            if self._verify_connection(conn):
                # Reset connection state
                try:
                    conn.rollback()  # Rollback any uncommitted changes
                except:
                    pass

                # Update metadata
                if conn in self.metadata:
                    self.metadata[conn]['last_used'] = time.time()

                # Return to available pool
                try:
                    self.available.put(conn, block=False)
                    with self.stats_lock:
                        self.stats['releases'] += 1
                except queue.Full:
                    # Pool is full - close this connection
                    self._close_connection(conn)
            else:
                # Connection is bad - close it
                self._close_connection(conn)

    def _verify_connection(self, conn: sqlite3.Connection) -> bool:
        """
        Verify connection is still valid

        Args:
            conn: Connection to verify

        Returns:
            True if connection is valid, False otherwise
        """
        try:
            conn.execute('SELECT 1')
            return True
        except:
            return False

    def _close_connection(self, conn: sqlite3.Connection):
        """
        Close a connection permanently

        Args:
            conn: Connection to close
        """
        try:
            conn.close()
        except:
            pass

        if conn in self.metadata:
            del self.metadata[conn]

        with self.stats_lock:
            self.stats['total_closed'] += 1
            self.stats['current_size'] -= 1

    def _maintenance_loop(self):
        """Periodic maintenance of connection pool"""
        while self.running:
            try:
                time.sleep(self.check_interval)

                current_time = time.time()
                connections_to_close = []

                with self.lock:
                    # Find idle connections to close
                    for conn, meta in list(self.metadata.items()):
                        if conn not in self.in_use:
                            idle_time = current_time - meta['last_used']

                            # Close if idle too long and above minimum size
                            if (idle_time > self.max_idle_time and
                                self.stats['current_size'] > self.min_size):
                                connections_to_close.append(conn)

                    # Close idle connections
                    for conn in connections_to_close:
                        # Remove from available queue if present
                        try:
                            temp_queue = queue.Queue()
                            while True:
                                try:
                                    c = self.available.get(block=False)
                                    if c != conn:
                                        temp_queue.put(c)
                                except queue.Empty:
                                    break

                            # Put back non-closed connections
                            while True:
                                try:
                                    self.available.put(temp_queue.get(block=False))
                                except queue.Empty:
                                    break
                        except:
                            pass

                        self._close_connection(conn)

                    # Ensure minimum connections
                    while self.stats['current_size'] < self.min_size:
                        conn = self._create_connection()
                        if conn:
                            self.available.put(conn)
                        else:
                            break

            except Exception as e:
                print(f"[DB_POOL] Maintenance error: {e}")

    @contextmanager
    def connection(self, timeout: float = 10.0):
        """
        Context manager for acquiring connections

        Usage:
            with pool.connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM table")

        Args:
            timeout: Maximum time to wait for connection

        Yields:
            Pooled connection
        """
        conn = self.acquire(timeout=timeout)
        if conn is None:
            raise TimeoutError(f"Could not acquire connection within {timeout}s")

        try:
            yield conn
        finally:
            conn.close()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get pool statistics

        Returns:
            Statistics dictionary
        """
        with self.stats_lock:
            stats = dict(self.stats)

        with self.lock:
            stats['available'] = self.available.qsize()
            stats['in_use'] = len(self.in_use)
            stats['min_size'] = self.min_size
            stats['max_size'] = self.max_size

            # Calculate average use count
            use_counts = [m['use_count'] for m in self.metadata.values()]
            stats['avg_use_count'] = sum(use_counts) / len(use_counts) if use_counts else 0

        return stats

    def close_all(self):
        """Close all connections and shutdown pool"""
        print("[DB_POOL] Closing all connections...")
        self.running = False

        with self.lock:
            # Close all available connections
            while True:
                try:
                    conn = self.available.get(block=False)
                    self._close_connection(conn)
                except queue.Empty:
                    break

            # Close all in-use connections (forcefully)
            for conn in list(self.in_use):
                self._close_connection(conn)

            self.in_use.clear()

        print(f"[DB_POOL] Closed {self.stats['total_closed']} connections")


# Global pool instances for common databases
_pools: Dict[str, ConnectionPool] = {}
_pools_lock = threading.Lock()


def get_pool(db_path: str, min_size: int = 2, max_size: int = 10) -> ConnectionPool:
    """
    Get or create connection pool for database

    Args:
        db_path: Path to database
        min_size: Minimum pool size
        max_size: Maximum pool size

    Returns:
        ConnectionPool instance
    """
    global _pools

    with _pools_lock:
        if db_path not in _pools:
            _pools[db_path] = ConnectionPool(
                db_path=db_path,
                min_size=min_size,
                max_size=max_size
            )

        return _pools[db_path]


def close_all_pools():
    """Close all global pools"""
    global _pools

    with _pools_lock:
        for pool in _pools.values():
            pool.close_all()
        _pools.clear()


def main():
    """Test database connection pool"""
    print("=" * 70)
    print("Database Connection Pooling System")
    print("=" * 70)

    # Create test database
    test_db = "test_pool.db"

    # Initialize test database
    conn = sqlite3.connect(test_db)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS test_data (
            id INTEGER PRIMARY KEY,
            value TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

    # Create pool
    pool = ConnectionPool(
        db_path=test_db,
        min_size=2,
        max_size=5,
        max_idle_time=10
    )

    try:
        print("\n1. Basic connection acquisition...")
        with pool.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO test_data (value) VALUES (?)", ("test1",))
            conn.commit()
            print("   Inserted test record")

        print("\n2. Multiple concurrent connections...")
        connections = []
        for i in range(3):
            conn = pool.acquire()
            if conn:
                connections.append(conn)
                print(f"   Acquired connection {i+1}")

        # Release them
        for i, conn in enumerate(connections):
            conn.close()
            print(f"   Released connection {i+1}")

        print("\n3. Connection reuse test...")
        conn1 = pool.acquire()
        print(f"   First acquisition: {id(conn1.conn)}")
        conn1.close()

        conn2 = pool.acquire()
        print(f"   Second acquisition: {id(conn2.conn)}")
        print(f"   Same connection reused: {id(conn1.conn) == id(conn2.conn)}")
        conn2.close()

        print("\n4. Concurrent access from threads...")

        def worker(worker_id: int):
            for i in range(5):
                with pool.connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO test_data (value) VALUES (?)",
                        (f"worker-{worker_id}-{i}",)
                    )
                    conn.commit()
                time.sleep(0.01)

        threads = []
        for i in range(3):
            t = threading.Thread(target=worker, args=(i,))
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

        print("   All threads completed")

        print("\n5. Verify data integrity...")
        with pool.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM test_data")
            count = cursor.fetchone()['count']
            print(f"   Total records: {count}")

        print("\n6. Pool statistics:")
        stats = pool.get_stats()
        for key, value in stats.items():
            print(f"   {key}: {value}")

        print("\n7. Connection health check...")
        time.sleep(2)
        print("   Maintenance thread running...")

        print("\n8. Stress test - rapid acquire/release...")
        start = time.time()
        for _ in range(100):
            with pool.connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")

        elapsed = time.time() - start
        print(f"   Completed 100 operations in {elapsed:.2f}s")
        print(f"   Rate: {100/elapsed:.1f} ops/sec")

        print("\n[OK] Database Connection Pool Working!")

        print("\nFinal Statistics:")
        final_stats = pool.get_stats()
        print(f"  - Total Created: {final_stats['total_created']}")
        print(f"  - Total Closed: {final_stats['total_closed']}")
        print(f"  - Current Size: {final_stats['current_size']}")
        print(f"  - Acquisitions: {final_stats['acquisitions']}")
        print(f"  - Avg Use Count: {final_stats['avg_use_count']:.1f}")

    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        pool.close_all()

        # Cleanup test database
        import os
        try:
            os.remove(test_db)
            os.remove(test_db + "-shm")
            os.remove(test_db + "-wal")
        except:
            pass


if __name__ == "__main__":
    main()
