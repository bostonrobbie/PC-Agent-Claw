#!/usr/bin/env python3
"""
Capability Result Caching System
LRU cache with TTL for expensive operations
"""
import sys
from pathlib import Path
import hashlib
import pickle
import json
import time
import threading
from typing import Any, Callable, Dict, List, Optional, Tuple
from collections import OrderedDict
from datetime import datetime, timedelta
from functools import wraps

sys.path.append(str(Path(__file__).parent.parent))


class ResultCache:
    """
    Advanced result caching for expensive operations

    Features:
    - LRU (Least Recently Used) eviction
    - TTL (Time To Live) expiration
    - Memory and persistent caching
    - Cache key generation from function signatures
    - Thread-safe operations
    - Cache statistics and monitoring
    - Tag-based invalidation
    - Warmup and preloading
    """

    def __init__(self, max_size: int = 1000, default_ttl: int = 3600,
                 enable_persistent: bool = False, db_path: str = None):
        """
        Initialize result cache

        Args:
            max_size: Maximum number of entries in memory cache
            default_ttl: Default TTL in seconds (0 = no expiration)
            enable_persistent: Enable persistent caching to disk
            db_path: Path to SQLite database for persistence
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.enable_persistent = enable_persistent

        # In-memory LRU cache: {key: (value, expires_at, created_at, access_count)}
        self.cache = OrderedDict()
        self.lock = threading.RLock()

        # Tag mapping: {tag: set(keys)}
        self.tags = {}

        # Statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expirations': 0,
            'sets': 0,
            'deletes': 0
        }

        # Persistent storage
        self.db_conn = None
        if enable_persistent and db_path:
            self._init_persistent_storage(db_path)

    def _init_persistent_storage(self, db_path: str):
        """Initialize persistent cache storage"""
        import sqlite3

        self.db_conn = sqlite3.connect(db_path, check_same_thread=False)
        self.db_conn.row_factory = sqlite3.Row

        cursor = self.db_conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS result_cache (
                cache_key TEXT PRIMARY KEY,
                cache_value BLOB NOT NULL,
                ttl_seconds INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                access_count INTEGER DEFAULT 0,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                size_bytes INTEGER
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cache_tags (
                cache_key TEXT NOT NULL,
                tag TEXT NOT NULL,
                PRIMARY KEY (cache_key, tag),
                FOREIGN KEY (cache_key) REFERENCES result_cache(cache_key) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_cache_expires ON result_cache(expires_at)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_cache_tags ON cache_tags(tag)
        ''')

        self.db_conn.commit()

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get value from cache

        Args:
            key: Cache key
            default: Default value if key not found

        Returns:
            Cached value or default
        """
        with self.lock:
            # Check memory cache
            if key in self.cache:
                value, expires_at, created_at, access_count = self.cache[key]

                # Check expiration
                if expires_at and time.time() > expires_at:
                    # Expired - remove it
                    del self.cache[key]
                    self.stats['expirations'] += 1
                    self.stats['misses'] += 1
                    return default

                # Cache hit - update LRU order
                self.cache.move_to_end(key)
                self.cache[key] = (value, expires_at, created_at, access_count + 1)
                self.stats['hits'] += 1

                # Update persistent storage if enabled
                if self.enable_persistent:
                    self._update_access(key)

                return value

            # Check persistent cache if enabled
            if self.enable_persistent:
                persistent_value = self._get_from_persistent(key)
                if persistent_value is not None:
                    value, expires_at = persistent_value

                    # Add to memory cache
                    self.cache[key] = (value, expires_at, time.time(), 1)
                    self._enforce_size_limit()

                    self.stats['hits'] += 1
                    return value

            # Cache miss
            self.stats['misses'] += 1
            return default

    def set(self, key: str, value: Any, ttl: Optional[int] = None,
            tags: Optional[List[str]] = None) -> None:
        """
        Set value in cache

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (None = use default)
            tags: Optional tags for grouped invalidation
        """
        ttl = self.default_ttl if ttl is None else ttl
        expires_at = time.time() + ttl if ttl > 0 else None

        with self.lock:
            # Add to memory cache
            self.cache[key] = (value, expires_at, time.time(), 0)
            self.cache.move_to_end(key)  # Mark as most recently used

            # Handle tags
            if tags:
                for tag in tags:
                    if tag not in self.tags:
                        self.tags[tag] = set()
                    self.tags[tag].add(key)

            # Enforce size limit
            self._enforce_size_limit()

            self.stats['sets'] += 1

            # Store in persistent cache if enabled
            if self.enable_persistent:
                self._set_in_persistent(key, value, ttl, expires_at, tags)

    def delete(self, key: str) -> bool:
        """
        Delete key from cache

        Args:
            key: Cache key to delete

        Returns:
            True if key existed, False otherwise
        """
        with self.lock:
            existed = key in self.cache

            if existed:
                del self.cache[key]
                self.stats['deletes'] += 1

                # Remove from tags
                for tag, keys in self.tags.items():
                    keys.discard(key)

            # Delete from persistent storage
            if self.enable_persistent:
                cursor = self.db_conn.cursor()
                cursor.execute('DELETE FROM result_cache WHERE cache_key = ?', (key,))
                cursor.execute('DELETE FROM cache_tags WHERE cache_key = ?', (key,))
                self.db_conn.commit()

            return existed

    def clear(self) -> int:
        """
        Clear entire cache

        Returns:
            Number of entries cleared
        """
        with self.lock:
            count = len(self.cache)
            self.cache.clear()
            self.tags.clear()

            if self.enable_persistent:
                cursor = self.db_conn.cursor()
                cursor.execute('DELETE FROM result_cache')
                cursor.execute('DELETE FROM cache_tags')
                self.db_conn.commit()

            return count

    def invalidate_by_tag(self, tag: str) -> int:
        """
        Invalidate all cache entries with a specific tag

        Args:
            tag: Tag to invalidate

        Returns:
            Number of entries invalidated
        """
        with self.lock:
            if tag not in self.tags:
                return 0

            keys_to_delete = list(self.tags[tag])
            for key in keys_to_delete:
                self.delete(key)

            del self.tags[tag]
            return len(keys_to_delete)

    def _enforce_size_limit(self):
        """Enforce max cache size using LRU eviction"""
        while len(self.cache) > self.max_size:
            # Remove oldest (least recently used)
            oldest_key, _ = self.cache.popitem(last=False)
            self.stats['evictions'] += 1

            # Remove from tags
            for tag, keys in self.tags.items():
                keys.discard(oldest_key)

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries

        Returns:
            Number of entries removed
        """
        with self.lock:
            current_time = time.time()
            expired_keys = [
                key for key, (_, expires_at, _, _) in self.cache.items()
                if expires_at and current_time > expires_at
            ]

            for key in expired_keys:
                del self.cache[key]
                self.stats['expirations'] += 1

            # Clean persistent storage
            if self.enable_persistent:
                cursor = self.db_conn.cursor()
                cursor.execute('''
                    DELETE FROM result_cache
                    WHERE expires_at IS NOT NULL AND expires_at < datetime('now')
                ''')
                self.db_conn.commit()

            return len(expired_keys)

    def cached(self, ttl: Optional[int] = None, tags: Optional[List[str]] = None,
               key_func: Optional[Callable] = None):
        """
        Decorator to cache function results

        Args:
            ttl: Cache TTL in seconds
            tags: Tags for invalidation
            key_func: Custom function to generate cache key

        Example:
            @cache.cached(ttl=300, tags=['expensive'])
            def expensive_operation(x, y):
                return x + y
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Generate cache key
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    cache_key = self.generate_key(func.__name__, args, kwargs)

                # Try to get from cache
                result = self.get(cache_key)
                if result is not None:
                    return result

                # Execute function
                result = func(*args, **kwargs)

                # Cache result
                self.set(cache_key, result, ttl=ttl, tags=tags)

                return result

            # Add cache control methods to function
            wrapper.cache_clear = lambda: self.invalidate_pattern(f"{func.__name__}:")
            wrapper.cache_info = lambda: self.get_stats()

            return wrapper
        return decorator

    def generate_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """
        Generate cache key from function name and arguments

        Args:
            func_name: Function name
            args: Positional arguments
            kwargs: Keyword arguments

        Returns:
            Cache key string
        """
        key_parts = [func_name]

        # Add positional args
        for arg in args:
            if isinstance(arg, (str, int, float, bool, type(None))):
                key_parts.append(str(arg))
            else:
                # Use hash for complex objects
                key_parts.append(str(hash(str(arg))))

        # Add keyword args (sorted for consistency)
        for k, v in sorted(kwargs.items()):
            if isinstance(v, (str, int, float, bool, type(None))):
                key_parts.append(f"{k}={v}")
            else:
                key_parts.append(f"{k}={hash(str(v))}")

        # Create hash of full key
        key_str = ":".join(key_parts)
        return hashlib.md5(key_str.encode()).hexdigest()

    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all keys matching pattern

        Args:
            pattern: Pattern to match (substring)

        Returns:
            Number of keys invalidated
        """
        with self.lock:
            matching_keys = [k for k in self.cache.keys() if pattern in k]
            for key in matching_keys:
                self.delete(key)
            return len(matching_keys)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics

        Returns:
            Statistics dictionary
        """
        with self.lock:
            total_requests = self.stats['hits'] + self.stats['misses']
            hit_rate = self.stats['hits'] / total_requests if total_requests > 0 else 0

            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'hits': self.stats['hits'],
                'misses': self.stats['misses'],
                'hit_rate': round(hit_rate, 3),
                'evictions': self.stats['evictions'],
                'expirations': self.stats['expirations'],
                'sets': self.stats['sets'],
                'deletes': self.stats['deletes'],
                'tags_count': len(self.tags),
                'total_requests': total_requests
            }

    def warmup(self, data: Dict[str, Any], ttl: Optional[int] = None):
        """
        Warm up cache with predefined data

        Args:
            data: Dictionary of key-value pairs to cache
            ttl: TTL for all entries
        """
        for key, value in data.items():
            self.set(key, value, ttl=ttl)

    # === Persistent Storage Methods ===

    def _get_from_persistent(self, key: str) -> Optional[Tuple[Any, Optional[float]]]:
        """Get value from persistent storage"""
        if not self.db_conn:
            return None

        cursor = self.db_conn.cursor()
        cursor.execute('''
            SELECT cache_value, expires_at FROM result_cache WHERE cache_key = ?
        ''', (key,))

        row = cursor.fetchone()
        if not row:
            return None

        # Check expiration
        if row['expires_at']:
            expires_dt = datetime.fromisoformat(row['expires_at'])
            if datetime.now() > expires_dt:
                # Expired - delete it
                cursor.execute('DELETE FROM result_cache WHERE cache_key = ?', (key,))
                self.db_conn.commit()
                return None
            expires_at = expires_dt.timestamp()
        else:
            expires_at = None

        # Deserialize value
        try:
            value = pickle.loads(row['cache_value'])
        except:
            # Corrupted data - delete it
            cursor.execute('DELETE FROM result_cache WHERE cache_key = ?', (key,))
            self.db_conn.commit()
            return None

        return value, expires_at

    def _set_in_persistent(self, key: str, value: Any, ttl: int,
                          expires_at: Optional[float], tags: Optional[List[str]]):
        """Set value in persistent storage"""
        if not self.db_conn:
            return

        # Serialize value
        try:
            serialized = pickle.dumps(value)
        except:
            # Can't serialize - skip persistent storage
            return

        expires_dt = datetime.fromtimestamp(expires_at) if expires_at else None

        cursor = self.db_conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO result_cache
            (cache_key, cache_value, ttl_seconds, expires_at, size_bytes)
            VALUES (?, ?, ?, ?, ?)
        ''', (key, serialized, ttl, expires_dt, len(serialized)))

        # Add tags
        if tags:
            cursor.execute('DELETE FROM cache_tags WHERE cache_key = ?', (key,))
            for tag in tags:
                cursor.execute('''
                    INSERT INTO cache_tags (cache_key, tag) VALUES (?, ?)
                ''', (key, tag))

        self.db_conn.commit()

    def _update_access(self, key: str):
        """Update access statistics in persistent storage"""
        if not self.db_conn:
            return

        cursor = self.db_conn.cursor()
        cursor.execute('''
            UPDATE result_cache
            SET access_count = access_count + 1,
                last_accessed = CURRENT_TIMESTAMP
            WHERE cache_key = ?
        ''', (key,))
        self.db_conn.commit()

    def close(self):
        """Close persistent storage connection"""
        if self.db_conn:
            self.db_conn.close()
            self.db_conn = None


# Global cache instance for easy importing
_global_cache = None


def get_cache(max_size: int = 1000, default_ttl: int = 3600,
              enable_persistent: bool = False) -> ResultCache:
    """
    Get global cache instance (singleton pattern)

    Args:
        max_size: Maximum cache size
        default_ttl: Default TTL
        enable_persistent: Enable persistence

    Returns:
        Global ResultCache instance
    """
    global _global_cache

    if _global_cache is None:
        workspace = Path(__file__).parent.parent
        db_path = str(workspace / "result_cache.db") if enable_persistent else None

        _global_cache = ResultCache(
            max_size=max_size,
            default_ttl=default_ttl,
            enable_persistent=enable_persistent,
            db_path=db_path
        )

    return _global_cache


def main():
    """Test result cache system"""
    print("=" * 70)
    print("Capability Result Caching System")
    print("=" * 70)

    # Create cache instance
    cache = ResultCache(max_size=100, default_ttl=60, enable_persistent=True,
                       db_path="test_result_cache.db")

    try:
        print("\n1. Basic caching operations...")
        cache.set('user:123', {'name': 'Alice', 'age': 30}, ttl=60)
        cache.set('user:456', {'name': 'Bob', 'age': 25}, ttl=60)

        user = cache.get('user:123')
        print(f"   Retrieved user: {user}")

        missing = cache.get('nonexistent', default={'error': 'not found'})
        print(f"   Missing key: {missing}")

        print("\n2. Caching with tags...")
        cache.set('api:v1:data', {'data': [1, 2, 3]}, tags=['api', 'v1'])
        cache.set('api:v1:users', {'users': ['alice', 'bob']}, tags=['api', 'v1'])
        cache.set('api:v2:data', {'data': [4, 5, 6]}, tags=['api', 'v2'])
        print("   Cached 3 API results with tags")

        print("\n3. Invalidating by tag...")
        invalidated = cache.invalidate_by_tag('v1')
        print(f"   Invalidated {invalidated} entries with tag 'v1'")

        print("\n4. Function caching with decorator...")

        @cache.cached(ttl=30, tags=['expensive'])
        def expensive_calculation(x: int, y: int) -> int:
            print(f"   Computing {x} + {y}...")
            time.sleep(0.1)  # Simulate expensive operation
            return x + y

        # First call - cache miss
        start = time.time()
        result1 = expensive_calculation(5, 3)
        time1 = time.time() - start
        print(f"   First call: {result1} (took {time1*1000:.1f}ms)")

        # Second call - cache hit
        start = time.time()
        result2 = expensive_calculation(5, 3)
        time2 = time.time() - start
        print(f"   Second call: {result2} (took {time2*1000:.1f}ms)")
        print(f"   Speedup: {time1/time2:.1f}x faster!")

        print("\n5. TTL expiration test...")
        cache.set('temp', 'expires_soon', ttl=1)
        print(f"   Immediately: {cache.get('temp')}")
        time.sleep(1.5)
        print(f"   After 1.5s: {cache.get('temp', 'EXPIRED')}")

        print("\n6. Cache statistics:")
        stats = cache.get_stats()
        for key, value in stats.items():
            print(f"   {key}: {value}")

        print("\n7. LRU eviction test...")
        small_cache = ResultCache(max_size=3)
        for i in range(5):
            small_cache.set(f'key_{i}', f'value_{i}')
        print(f"   Added 5 items to cache with max_size=3")
        print(f"   Cache size: {small_cache.get_stats()['size']}")
        print(f"   Evictions: {small_cache.get_stats()['evictions']}")

        print("\n8. Cleanup expired entries...")
        deleted = cache.cleanup_expired()
        print(f"   Deleted {deleted} expired entries")

        print("\n9. Warmup cache...")
        cache.warmup({
            'config:db': {'host': 'localhost', 'port': 5432},
            'config:cache': {'max_size': 1000, 'ttl': 3600}
        }, ttl=300)
        print("   Warmed up cache with 2 config entries")

        print(f"\n[OK] Result Cache System Working!")
        print(f"\nFinal Statistics:")
        final_stats = cache.get_stats()
        print(f"  - Total Requests: {final_stats['total_requests']}")
        print(f"  - Hit Rate: {final_stats['hit_rate']*100:.1f}%")
        print(f"  - Cache Size: {final_stats['size']}/{final_stats['max_size']}")

    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cache.close()
        small_cache.close()


if __name__ == "__main__":
    main()
