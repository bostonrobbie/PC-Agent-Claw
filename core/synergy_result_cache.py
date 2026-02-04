"""
Synergy Chain Result Caching - MEDIUM PRIORITY IMPROVEMENT #5

Caches synergy chain results for 5 minutes to avoid redundant processing.
Expected benefit: 40-60% faster for repeated operations.
"""

import time
import hashlib
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from dataclasses import dataclass


@dataclass
class CacheEntry:
    """Cached result entry"""
    key: str
    result: Any
    cached_at: float
    ttl_seconds: int
    hit_count: int


class SynergyResultCache:
    """
    LRU cache with TTL for synergy chain results

    Prevents redundant chain executions when same input seen recently.
    """

    def __init__(self, db_path: str = "synergy_cache.db", default_ttl: int = 300):
        self.db_path = db_path
        self.default_ttl = default_ttl  # 5 minutes
        self._init_db()

    def _init_db(self):
        """Initialize cache database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cache_entries (
                cache_key TEXT PRIMARY KEY,
                chain_name TEXT,
                input_hash TEXT,
                result_json TEXT,
                cached_at REAL,
                ttl_seconds INTEGER,
                hit_count INTEGER DEFAULT 0,
                last_accessed REAL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cache_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation TEXT,
                cache_hit INTEGER,
                timestamp TEXT
            )
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_chain_name ON cache_entries(chain_name)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_cached_at ON cache_entries(cached_at)
        ''')

        conn.commit()
        conn.close()

    def _generate_key(self, chain_name: str, input_data: Dict) -> str:
        """Generate cache key from chain name and input"""
        # Create deterministic hash of input
        input_str = json.dumps(input_data, sort_keys=True)
        input_hash = hashlib.sha256(input_str.encode()).hexdigest()[:16]

        return f"{chain_name}:{input_hash}"

    def get(self, chain_name: str, input_data: Dict) -> Optional[Dict]:
        """
        Get cached result if available and not expired

        Args:
            chain_name: Name of synergy chain
            input_data: Input data for the chain

        Returns:
            Cached result or None if not found/expired
        """
        key = self._generate_key(chain_name, input_data)
        now = time.time()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT result_json, cached_at, ttl_seconds, hit_count
            FROM cache_entries
            WHERE cache_key = ?
        ''', (key,))

        row = cursor.fetchone()

        if row:
            result_json, cached_at, ttl_seconds, hit_count = row

            # Check if expired
            age = now - cached_at
            if age < ttl_seconds:
                # Cache HIT - update hit count and access time
                cursor.execute('''
                    UPDATE cache_entries
                    SET hit_count = hit_count + 1, last_accessed = ?
                    WHERE cache_key = ?
                ''', (now, key))

                self._record_stat(cursor, "get", True)

                conn.commit()
                conn.close()

                result = json.loads(result_json)
                result['_cached'] = True
                result['_cache_age_seconds'] = age
                result['_cache_hit_count'] = hit_count + 1

                return result

            else:
                # Expired - delete it
                cursor.execute('DELETE FROM cache_entries WHERE cache_key = ?', (key,))
                conn.commit()

        # Cache MISS
        self._record_stat(cursor, "get", False)
        conn.commit()
        conn.close()

        return None

    def set(self, chain_name: str, input_data: Dict, result: Dict,
            ttl_seconds: Optional[int] = None):
        """
        Cache a chain execution result

        Args:
            chain_name: Name of synergy chain
            input_data: Input data for the chain
            result: Result to cache
            ttl_seconds: Time-to-live in seconds (default: 5 min)
        """
        key = self._generate_key(chain_name, input_data)
        input_hash = key.split(':')[1]
        ttl = ttl_seconds or self.default_ttl

        # Remove _cached flag if present
        result_to_cache = {k: v for k, v in result.items() if not k.startswith('_cache')}

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO cache_entries
            (cache_key, chain_name, input_hash, result_json, cached_at, ttl_seconds, hit_count, last_accessed)
            VALUES (?, ?, ?, ?, ?, ?, 0, ?)
        ''', (
            key,
            chain_name,
            input_hash,
            json.dumps(result_to_cache),
            time.time(),
            ttl,
            time.time()
        ))

        self._record_stat(cursor, "set", True)

        conn.commit()
        conn.close()

    def invalidate(self, chain_name: str, input_data: Optional[Dict] = None):
        """
        Invalidate cache entries

        Args:
            chain_name: Chain to invalidate
            input_data: Specific input to invalidate, or None for all
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if input_data:
            key = self._generate_key(chain_name, input_data)
            cursor.execute('DELETE FROM cache_entries WHERE cache_key = ?', (key,))
        else:
            cursor.execute('DELETE FROM cache_entries WHERE chain_name = ?', (chain_name,))

        conn.commit()
        conn.close()

    def cleanup_expired(self):
        """Remove all expired cache entries"""
        now = time.time()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            DELETE FROM cache_entries
            WHERE (? - cached_at) > ttl_seconds
        ''', (now,))

        deleted = cursor.rowcount

        conn.commit()
        conn.close()

        return deleted

    def get_stats(self) -> Dict:
        """Get cache statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Total entries
        cursor.execute('SELECT COUNT(*) FROM cache_entries')
        total_entries = cursor.fetchone()[0]

        # Recent hits/misses
        cursor.execute('''
            SELECT
                SUM(CASE WHEN cache_hit = 1 THEN 1 ELSE 0 END) as hits,
                SUM(CASE WHEN cache_hit = 0 THEN 1 ELSE 0 END) as misses
            FROM cache_stats
            WHERE datetime(timestamp) > datetime('now', '-1 hour')
        ''')
        row = cursor.fetchone()
        hits = row[0] or 0
        misses = row[1] or 0

        # Hit rate
        total = hits + misses
        hit_rate = (hits / total * 100) if total > 0 else 0

        # Top cached chains
        cursor.execute('''
            SELECT chain_name, COUNT(*) as count, SUM(hit_count) as total_hits
            FROM cache_entries
            GROUP BY chain_name
            ORDER BY total_hits DESC
            LIMIT 5
        ''')
        top_chains = [
            {'chain': row[0], 'entries': row[1], 'hits': row[2]}
            for row in cursor.fetchall()
        ]

        # Average hit count
        cursor.execute('SELECT AVG(hit_count) FROM cache_entries')
        avg_hits = cursor.fetchone()[0] or 0

        conn.close()

        return {
            'total_entries': total_entries,
            'recent_hits': hits,
            'recent_misses': misses,
            'hit_rate_percent': hit_rate,
            'avg_hits_per_entry': avg_hits,
            'top_chains': top_chains
        }

    def _record_stat(self, cursor, operation: str, cache_hit: bool):
        """Record cache operation statistic"""
        cursor.execute('''
            INSERT INTO cache_stats (operation, cache_hit, timestamp)
            VALUES (?, ?, ?)
        ''', (operation, 1 if cache_hit else 0, datetime.now().isoformat()))


# Integration with CapabilitySynergy
def integrate_with_synergy():
    """
    Example of integrating cache with CapabilitySynergy class

    Add this to capability_synergy.py:
    """
    from core.synergy_result_cache import SynergyResultCache

    class CapabilitySynergy:
        def __init__(self):
            # ... existing init ...
            self.result_cache = SynergyResultCache()

        def execute_chain(self, chain_name: str, input_data: Dict) -> Dict:
            # Try cache first
            cached = self.result_cache.get(chain_name, input_data)
            if cached:
                print(f"[CACHE HIT] Using cached result for {chain_name}")
                return cached

            # Execute chain normally
            result = self._execute_chain_impl(chain_name, input_data)

            # Cache the result
            self.result_cache.set(chain_name, input_data, result)

            return result


# Example usage
if __name__ == '__main__':
    cache = SynergyResultCache()

    # Simulate chain execution
    chain_name = "discovery_learning_chain"
    input_data = {'query': 'authentication', 'file': 'auth.py'}

    # First execution - cache miss
    print("\n1. First execution (should be cache MISS)...")
    result1 = cache.get(chain_name, input_data)
    print(f"Cached result: {result1}")

    if not result1:
        # Execute chain (simulated)
        print("Executing chain...")
        result = {
            'status': 'completed',
            'steps': 3,
            'insights': ['insight1', 'insight2'],
            'execution_time': 2.5
        }
        cache.set(chain_name, input_data, result)
        print("Result cached")

    # Second execution - cache hit
    print("\n2. Second execution (should be cache HIT)...")
    result2 = cache.get(chain_name, input_data)
    print(f"Cached result: {result2}")
    print(f"Cache age: {result2.get('_cache_age_seconds', 0):.1f}s")
    print(f"Hit count: {result2.get('_cache_hit_count', 0)}")

    # Stats
    print("\n3. Cache statistics...")
    stats = cache.get_stats()
    print(f"Total entries: {stats['total_entries']}")
    print(f"Hit rate: {stats['hit_rate_percent']:.1f}%")
    print(f"Recent hits: {stats['recent_hits']}")
    print(f"Recent misses: {stats['recent_misses']}")

    # Cleanup
    print("\n4. Cleanup expired entries...")
    deleted = cache.cleanup_expired()
    print(f"Deleted {deleted} expired entries")
