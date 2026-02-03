#!/usr/bin/env python3
"""
Smart Caching System - LRU cache with TTL for common computations
High-performance caching with automatic expiration and size limits
"""

import sqlite3
import json
import time
import hashlib
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from collections import OrderedDict
import threading


class SmartCache:
    """
    Smart caching system with LRU eviction and TTL

    Features:
    - LRU (Least Recently Used) eviction policy
    - TTL (Time To Live) for cache entries
    - Size-based limits
    - Hit/miss tracking
    - Cache statistics
    - Persistent cache storage
    - Thread-safe operations
    """

    def __init__(self, db_path: str = None, max_size: int = 1000,
                 default_ttl: int = 3600):
        if db_path is None:
            workspace = Path(__file__).parent.parent
            db_path = workspace / "memory.db"

        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

        self.max_size = max_size
        self.default_ttl = default_ttl

        # In-memory LRU cache
        self.memory_cache = OrderedDict()
        self.lock = threading.Lock()

        # Statistics
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    def _init_db(self):
        """Initialize database schema for caching"""
        cursor = self.conn.cursor()

        # Cache entries table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cache_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cache_key TEXT UNIQUE NOT NULL,
                cache_value TEXT NOT NULL,
                value_type TEXT,
                ttl_seconds INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                access_count INTEGER DEFAULT 0,
                hit_count INTEGER DEFAULT 0,
                size_bytes INTEGER
            )
        ''')

        # Cache statistics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cache_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation TEXT NOT NULL,
                cache_key TEXT,
                hit INTEGER DEFAULT 0,
                execution_time_ms REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Cache tags table (for grouped invalidation)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cache_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cache_key TEXT NOT NULL,
                tag TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (cache_key) REFERENCES cache_entries(cache_key)
            )
        ''')

        # Create indexes
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_cache_key ON cache_entries(cache_key)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_expires_at ON cache_entries(expires_at)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_cache_tags_key ON cache_tags(cache_key)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_cache_tags_tag ON cache_tags(tag)
        ''')

        self.conn.commit()

    # === CACHE OPERATIONS ===

    def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache"""
        start_time = time.time()

        with self.lock:
            # Check memory cache first
            if key in self.memory_cache:
                value, expires_at = self.memory_cache[key]

                # Check if expired
                if expires_at and time.time() > expires_at:
                    del self.memory_cache[key]
                    self.misses += 1
                    self._log_stat('get', key, hit=False, start_time=start_time)
                    return default

                # Move to end (most recently used)
                self.memory_cache.move_to_end(key)
                self.hits += 1
                self._log_stat('get', key, hit=True, start_time=start_time)
                self._update_access(key)
                return value

        # Check persistent cache
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT cache_value, value_type, expires_at
            FROM cache_entries
            WHERE cache_key = ?
        ''', (key,))

        row = cursor.fetchone()

        if row:
            # Check if expired
            if row['expires_at']:
                expires_dt = datetime.fromisoformat(row['expires_at'])
                if datetime.now() > expires_dt:
                    self.delete(key)
                    self.misses += 1
                    self._log_stat('get', key, hit=False, start_time=start_time)
                    return default

            # Deserialize value
            value = self._deserialize(row['cache_value'], row['value_type'])

            # Add to memory cache
            expires_at = datetime.fromisoformat(row['expires_at']).timestamp() if row['expires_at'] else None
            with self.lock:
                self.memory_cache[key] = (value, expires_at)
                self._enforce_size_limit()

            self.hits += 1
            self._log_stat('get', key, hit=True, start_time=start_time)
            self._update_access(key)
            return value

        self.misses += 1
        self._log_stat('get', key, hit=False, start_time=start_time)
        return default

    def set(self, key: str, value: Any, ttl: int = None, tags: List[str] = None):
        """Set value in cache with optional TTL"""
        start_time = time.time()

        ttl = ttl if ttl is not None else self.default_ttl
        expires_at = time.time() + ttl if ttl > 0 else None
        expires_dt = datetime.fromtimestamp(expires_at) if expires_at else None

        # Serialize value
        serialized, value_type = self._serialize(value)
        size_bytes = len(serialized)

        # Store in memory cache
        with self.lock:
            self.memory_cache[key] = (value, expires_at)
            self._enforce_size_limit()

        # Store in persistent cache
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO cache_entries
            (cache_key, cache_value, value_type, ttl_seconds, expires_at, size_bytes)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (key, serialized, value_type, ttl, expires_dt, size_bytes))

        # Add tags
        if tags:
            for tag in tags:
                cursor.execute('''
                    INSERT OR IGNORE INTO cache_tags (cache_key, tag)
                    VALUES (?, ?)
                ''', (key, tag))

        self.conn.commit()
        self._log_stat('set', key, hit=True, start_time=start_time)

    def delete(self, key: str):
        """Delete key from cache"""
        with self.lock:
            if key in self.memory_cache:
                del self.memory_cache[key]

        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM cache_entries WHERE cache_key = ?', (key,))
        cursor.execute('DELETE FROM cache_tags WHERE cache_key = ?', (key,))
        self.conn.commit()

    def clear(self):
        """Clear entire cache"""
        with self.lock:
            self.memory_cache.clear()

        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM cache_entries')
        cursor.execute('DELETE FROM cache_tags')
        self.conn.commit()

    def invalidate_by_tag(self, tag: str):
        """Invalidate all cache entries with a specific tag"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT cache_key FROM cache_tags WHERE tag = ?
        ''', (tag,))

        keys = [row['cache_key'] for row in cursor.fetchall()]

        for key in keys:
            self.delete(key)

    # === DECORATOR FOR FUNCTION CACHING ===

    def cached(self, ttl: int = None, tags: List[str] = None):
        """Decorator to cache function results"""
        def decorator(func: Callable) -> Callable:
            def wrapper(*args, **kwargs):
                # Generate cache key from function name and arguments
                cache_key = self._generate_key(func.__name__, args, kwargs)

                # Try to get from cache
                result = self.get(cache_key)
                if result is not None:
                    return result

                # Execute function
                result = func(*args, **kwargs)

                # Store in cache
                self.set(cache_key, result, ttl=ttl, tags=tags)
                return result

            return wrapper
        return decorator

    def _generate_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """Generate cache key from function and arguments"""
        key_parts = [func_name]

        # Add args
        for arg in args:
            key_parts.append(str(arg))

        # Add kwargs
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}={v}")

        key_str = ":".join(key_parts)
        return hashlib.md5(key_str.encode()).hexdigest()

    # === SIZE MANAGEMENT ===

    def _enforce_size_limit(self):
        """Enforce max cache size using LRU eviction"""
        while len(self.memory_cache) > self.max_size:
            # Remove oldest (least recently used)
            oldest_key = next(iter(self.memory_cache))
            del self.memory_cache[oldest_key]
            self.evictions += 1

    # === EXPIRATION ===

    def cleanup_expired(self):
        """Remove expired entries from cache"""
        cursor = self.conn.cursor()
        cursor.execute('''
            DELETE FROM cache_entries
            WHERE expires_at IS NOT NULL AND expires_at < datetime('now')
        ''')

        deleted = cursor.rowcount
        self.conn.commit()

        # Also clean memory cache
        with self.lock:
            current_time = time.time()
            expired_keys = [
                key for key, (value, expires_at) in self.memory_cache.items()
                if expires_at and current_time > expires_at
            ]
            for key in expired_keys:
                del self.memory_cache[key]

        return deleted

    # === SERIALIZATION ===

    def _serialize(self, value: Any) -> tuple:
        """Serialize value for storage"""
        if isinstance(value, (str, int, float, bool)):
            return json.dumps(value), 'json'
        else:
            return pickle.dumps(value).hex(), 'pickle'

    def _deserialize(self, serialized: str, value_type: str) -> Any:
        """Deserialize value from storage"""
        if value_type == 'json':
            return json.loads(serialized)
        elif value_type == 'pickle':
            return pickle.loads(bytes.fromhex(serialized))
        else:
            return serialized

    # === STATISTICS ===

    def _update_access(self, key: str):
        """Update access statistics for a key"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE cache_entries
            SET last_accessed = CURRENT_TIMESTAMP,
                access_count = access_count + 1,
                hit_count = hit_count + 1
            WHERE cache_key = ?
        ''', (key,))
        self.conn.commit()

    def _log_stat(self, operation: str, key: str, hit: bool, start_time: float):
        """Log cache operation statistics"""
        execution_time = (time.time() - start_time) * 1000  # Convert to ms

        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO cache_stats (operation, cache_key, hit, execution_time_ms)
            VALUES (?, ?, ?, ?)
        ''', (operation, key, 1 if hit else 0, execution_time))
        self.conn.commit()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        cursor = self.conn.cursor()

        # Total entries
        cursor.execute('SELECT COUNT(*) as count FROM cache_entries')
        total_entries = cursor.fetchone()['count']

        # Total size
        cursor.execute('SELECT SUM(size_bytes) as total FROM cache_entries')
        total_size = cursor.fetchone()['total'] or 0

        # Hit rate
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0

        # Most accessed
        cursor.execute('''
            SELECT cache_key, hit_count, access_count
            FROM cache_entries
            ORDER BY hit_count DESC
            LIMIT 10
        ''')
        most_accessed = [dict(row) for row in cursor.fetchall()]

        # Average execution time
        cursor.execute('''
            SELECT AVG(execution_time_ms) as avg_time
            FROM cache_stats
            WHERE timestamp >= datetime('now', '-1 hour')
        ''')
        avg_time = cursor.fetchone()['avg_time'] or 0

        return {
            'total_entries': total_entries,
            'memory_cache_size': len(self.memory_cache),
            'total_size_bytes': total_size,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': round(hit_rate, 3),
            'evictions': self.evictions,
            'most_accessed': most_accessed,
            'avg_execution_time_ms': round(avg_time, 3)
        }

    def close(self):
        """Close database connection"""
        self.conn.close()


def main():
    """Test smart cache system"""
    print("Testing Smart Caching System")
    print("=" * 50)

    cache = SmartCache(max_size=100, default_ttl=3600)

    # Basic get/set
    print("\n1. Basic caching operations...")
    cache.set('user:123', {'name': 'Alice', 'age': 30}, ttl=60)
    cache.set('user:456', {'name': 'Bob', 'age': 25}, ttl=60)
    cache.set('count', 42)

    user = cache.get('user:123')
    print(f"   Retrieved: {user}")

    count = cache.get('count')
    print(f"   Count: {count}")

    # Test miss
    missing = cache.get('nonexistent', default='NOT_FOUND')
    print(f"   Missing key: {missing}")

    # Using tags
    print("\n2. Caching with tags...")
    cache.set('post:1', {'title': 'First Post'}, tags=['posts', 'public'])
    cache.set('post:2', {'title': 'Second Post'}, tags=['posts', 'draft'])
    cache.set('comment:1', {'text': 'Great!'}, tags=['comments'])
    print("   Cached 3 items with tags")

    # Invalidate by tag
    print("\n3. Invalidating by tag...")
    cache.invalidate_by_tag('posts')
    print("   Invalidated all 'posts' entries")

    post1 = cache.get('post:1')
    comment1 = cache.get('comment:1')
    print(f"   Post after invalidation: {post1}")
    print(f"   Comment (should exist): {comment1}")

    # Function caching with decorator
    print("\n4. Function caching with decorator...")

    @cache.cached(ttl=30)
    def expensive_computation(x, y):
        print(f"   Computing {x} + {y}...")
        time.sleep(0.1)  # Simulate expensive operation
        return x + y

    # First call - cache miss
    start = time.time()
    result1 = expensive_computation(5, 3)
    time1 = time.time() - start
    print(f"   First call: {result1} (took {time1*1000:.1f}ms)")

    # Second call - cache hit
    start = time.time()
    result2 = expensive_computation(5, 3)
    time2 = time.time() - start
    print(f"   Second call: {result2} (took {time2*1000:.1f}ms)")
    print(f"   Speedup: {time1/time2:.1f}x")

    # TTL expiration test
    print("\n5. Testing TTL expiration...")
    cache.set('temp', 'will_expire', ttl=1)
    print(f"   Immediately: {cache.get('temp')}")
    time.sleep(1.5)
    print(f"   After 1.5s: {cache.get('temp', 'EXPIRED')}")

    # Cleanup expired
    print("\n6. Cleaning up expired entries...")
    deleted = cache.cleanup_expired()
    print(f"   Deleted {deleted} expired entries")

    # Get statistics
    print("\n7. Cache Statistics:")
    stats = cache.get_stats()
    for key, value in stats.items():
        if key == 'most_accessed':
            print(f"   {key}:")
            for item in value[:3]:
                print(f"     - {item['cache_key']}: {item['hit_count']} hits")
        else:
            print(f"   {key}: {value}")

    # Test LRU eviction
    print("\n8. Testing LRU eviction...")
    small_cache = SmartCache(max_size=3)
    for i in range(5):
        small_cache.set(f'key_{i}', i)
    print(f"   Memory cache size: {len(small_cache.memory_cache)} (max: 3)")
    print(f"   Evictions: {small_cache.evictions}")

    print(f"\n✓ Smart cache system working!")
    print(f"Database: {cache.db_path}")

    cache.close()
    small_cache.close()


if __name__ == "__main__":
    main()
