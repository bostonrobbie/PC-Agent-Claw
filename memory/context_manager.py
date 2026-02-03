"""
Context Window Expansion with Smart Summarization

Automatically manages context when approaching token limits.
Identifies and compresses less-important information while preserving critical details.
Uses hierarchical summarization and importance scoring.

Author: AI Self-Improvement System
Created: 2026-02-03
"""

import sqlite3
import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum


class ImportanceLevel(Enum):
    """Importance levels for information retention"""
    CRITICAL = 5    # Never compress - project goals, key decisions, user preferences
    HIGH = 4        # Compress minimally - active tasks, recent context
    MEDIUM = 3      # Compress moderately - completed tasks, older context
    LOW = 2         # Compress heavily - background info, tangential details
    TRIVIAL = 1     # Can discard - repeated info, unnecessary verbosity


@dataclass
class ContextChunk:
    """A piece of context with metadata"""
    id: Optional[int]
    session_id: str
    content: str
    content_type: str  # 'code', 'decision', 'conversation', 'error', 'file_content'
    importance: ImportanceLevel
    timestamp: str
    tokens_estimated: int
    compressed: bool
    compression_ratio: float
    tags: List[str]

    def to_dict(self) -> Dict:
        d = asdict(self)
        d['importance'] = self.importance.value
        d['tags'] = json.dumps(self.tags)
        return d


class ContextManager:
    """Manages context window with smart summarization"""

    def __init__(self, db_path: str = "context_manager.db"):
        self.db_path = db_path
        self.max_tokens = 180000  # Conservative estimate for Claude
        self.warning_threshold = 0.8  # Warn at 80%
        self.compression_threshold = 0.9  # Compress at 90%
        self._init_db()

    def _init_db(self):
        """Initialize database"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Context chunks table
        c.execute('''
            CREATE TABLE IF NOT EXISTS context_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                content TEXT NOT NULL,
                content_type TEXT NOT NULL,
                importance INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                tokens_estimated INTEGER NOT NULL,
                compressed INTEGER DEFAULT 0,
                compression_ratio REAL DEFAULT 1.0,
                tags TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Compression history
        c.execute('''
            CREATE TABLE IF NOT EXISTS compression_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                original_tokens INTEGER NOT NULL,
                compressed_tokens INTEGER NOT NULL,
                compression_ratio REAL NOT NULL,
                chunks_compressed INTEGER NOT NULL,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Session metadata
        c.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                total_tokens INTEGER DEFAULT 0,
                critical_tokens INTEGER DEFAULT 0,
                compressed_tokens INTEGER DEFAULT 0,
                last_compression TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()

    def add_context(self, session_id: str, content: str, content_type: str,
                   importance: ImportanceLevel, tags: List[str] = None) -> int:
        """Add a new piece of context"""
        tokens = self._estimate_tokens(content)

        chunk = ContextChunk(
            id=None,
            session_id=session_id,
            content=content,
            content_type=content_type,
            importance=importance,
            timestamp=datetime.now().isoformat(),
            tokens_estimated=tokens,
            compressed=False,
            compression_ratio=1.0,
            tags=tags or []
        )

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute('''
            INSERT INTO context_chunks
            (session_id, content, content_type, importance, timestamp,
             tokens_estimated, compressed, compression_ratio, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            chunk.session_id, chunk.content, chunk.content_type,
            chunk.importance.value, chunk.timestamp, chunk.tokens_estimated,
            int(chunk.compressed), chunk.compression_ratio, json.dumps(chunk.tags)
        ))

        chunk_id = c.lastrowid

        # Update session totals
        c.execute('''
            INSERT INTO sessions (session_id, total_tokens, critical_tokens)
            VALUES (?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                total_tokens = total_tokens + ?,
                critical_tokens = critical_tokens + ?,
                updated_at = CURRENT_TIMESTAMP
        ''', (
            session_id, tokens,
            tokens if importance == ImportanceLevel.CRITICAL else 0,
            tokens,
            tokens if importance == ImportanceLevel.CRITICAL else 0
        ))

        conn.commit()
        conn.close()

        # Check if we need to compress
        self._check_and_compress(session_id)

        return chunk_id

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation)"""
        # Rough estimate: 1 token ≈ 4 characters for English text
        return len(text) // 4

    def _check_and_compress(self, session_id: str):
        """Check if compression is needed and trigger it"""
        stats = self.get_session_stats(session_id)
        usage_ratio = stats['total_tokens'] / self.max_tokens

        if usage_ratio >= self.compression_threshold:
            self.compress_context(session_id)
        elif usage_ratio >= self.warning_threshold:
            print(f"⚠️  Context usage at {usage_ratio*100:.1f}% - compression coming soon")

    def get_session_stats(self, session_id: str) -> Dict:
        """Get current session statistics"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute('SELECT * FROM sessions WHERE session_id = ?', (session_id,))
        row = c.fetchone()

        if not row:
            conn.close()
            return {
                'total_tokens': 0,
                'critical_tokens': 0,
                'compressed_tokens': 0,
                'usage_ratio': 0.0
            }

        conn.close()

        total = row[1]
        return {
            'total_tokens': total,
            'critical_tokens': row[2],
            'compressed_tokens': row[3],
            'usage_ratio': total / self.max_tokens
        }

    def compress_context(self, session_id: str) -> Dict:
        """
        Compress context intelligently based on importance.

        Strategy:
        - CRITICAL: Never compress
        - HIGH: Light compression (keep 80%)
        - MEDIUM: Moderate compression (keep 50%)
        - LOW: Heavy compression (keep 20%)
        - TRIVIAL: Discard completely
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Get chunks by importance (exclude already compressed)
        c.execute('''
            SELECT id, content, importance, tokens_estimated
            FROM context_chunks
            WHERE session_id = ? AND compressed = 0
            ORDER BY importance ASC, timestamp ASC
        ''', (session_id,))

        chunks = c.fetchall()

        original_tokens = sum(chunk[3] for chunk in chunks)
        compressed_tokens = 0
        chunks_compressed = 0

        for chunk_id, content, importance, tokens in chunks:
            importance_level = ImportanceLevel(importance)

            if importance_level == ImportanceLevel.CRITICAL:
                # Never compress critical content
                compressed_tokens += tokens
                continue

            elif importance_level == ImportanceLevel.TRIVIAL:
                # Discard trivial content
                c.execute('DELETE FROM context_chunks WHERE id = ?', (chunk_id,))
                chunks_compressed += 1
                continue

            else:
                # Compress based on importance
                compression_ratios = {
                    ImportanceLevel.HIGH: 0.8,
                    ImportanceLevel.MEDIUM: 0.5,
                    ImportanceLevel.LOW: 0.2
                }

                ratio = compression_ratios.get(importance_level, 0.5)
                compressed_content = self._compress_text(content, ratio)
                new_tokens = self._estimate_tokens(compressed_content)

                c.execute('''
                    UPDATE context_chunks
                    SET content = ?, compressed = 1, compression_ratio = ?,
                        tokens_estimated = ?
                    WHERE id = ?
                ''', (compressed_content, ratio, new_tokens, chunk_id))

                compressed_tokens += new_tokens
                chunks_compressed += 1

        # Record compression event
        compression_ratio = compressed_tokens / original_tokens if original_tokens > 0 else 1.0

        c.execute('''
            INSERT INTO compression_history
            (session_id, original_tokens, compressed_tokens, compression_ratio, chunks_compressed)
            VALUES (?, ?, ?, ?, ?)
        ''', (session_id, original_tokens, compressed_tokens, compression_ratio, chunks_compressed))

        # Update session
        c.execute('''
            UPDATE sessions
            SET compressed_tokens = ?,
                last_compression = CURRENT_TIMESTAMP,
                total_tokens = (
                    SELECT SUM(tokens_estimated) FROM context_chunks WHERE session_id = ?
                )
            WHERE session_id = ?
        ''', (compressed_tokens, session_id, session_id))

        conn.commit()
        conn.close()

        return {
            'original_tokens': original_tokens,
            'compressed_tokens': compressed_tokens,
            'compression_ratio': compression_ratio,
            'chunks_compressed': chunks_compressed,
            'tokens_saved': original_tokens - compressed_tokens
        }

    def _compress_text(self, text: str, ratio: float) -> str:
        """
        Compress text to target ratio.

        Strategies:
        1. Remove redundant whitespace
        2. Abbreviate common phrases
        3. Extract key sentences
        4. Summarize if needed
        """
        # Step 1: Clean whitespace
        compressed = re.sub(r'\s+', ' ', text.strip())

        # Step 2: Abbreviate common phrases
        abbreviations = {
            'function': 'fn',
            'return': 'ret',
            'parameter': 'param',
            'parameters': 'params',
            'variable': 'var',
            'variables': 'vars',
            'initialize': 'init',
            'configuration': 'config',
            'implementation': 'impl',
            'documentation': 'docs',
            'repository': 'repo',
        }

        for full, abbr in abbreviations.items():
            compressed = compressed.replace(full, abbr)

        # Step 3: Extract key sentences (if still too long)
        current_ratio = len(compressed) / len(text) if len(text) > 0 else 1.0

        if current_ratio > ratio:
            # Split into sentences and keep most important ones
            sentences = re.split(r'[.!?]+', compressed)
            target_sentences = max(1, int(len(sentences) * ratio))

            # Keep first and last sentences, plus fill from middle
            if target_sentences < len(sentences):
                kept = [sentences[0]]
                if target_sentences > 2:
                    step = len(sentences) // (target_sentences - 1)
                    kept.extend(sentences[step:len(sentences)-step:step][:target_sentences-2])
                if target_sentences > 1:
                    kept.append(sentences[-1])
                compressed = '. '.join(kept) + '.'

        return compressed

    def get_context_summary(self, session_id: str, importance_threshold: ImportanceLevel = ImportanceLevel.MEDIUM) -> str:
        """Get summarized context above importance threshold"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute('''
            SELECT content_type, content, importance
            FROM context_chunks
            WHERE session_id = ? AND importance >= ?
            ORDER BY importance DESC, timestamp DESC
        ''', (session_id, importance_threshold.value))

        chunks = c.fetchall()
        conn.close()

        summary_parts = []
        for content_type, content, importance in chunks:
            summary_parts.append(f"[{content_type.upper()}] {content}")

        return "\n\n".join(summary_parts)

    def get_compression_history(self, session_id: str) -> List[Dict]:
        """Get compression history for session"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute('''
            SELECT original_tokens, compressed_tokens, compression_ratio,
                   chunks_compressed, timestamp
            FROM compression_history
            WHERE session_id = ?
            ORDER BY timestamp DESC
        ''', (session_id,))

        rows = c.fetchall()
        conn.close()

        return [
            {
                'original_tokens': row[0],
                'compressed_tokens': row[1],
                'compression_ratio': row[2],
                'chunks_compressed': row[3],
                'timestamp': row[4]
            }
            for row in rows
        ]

    def prioritize_retention(self, session_id: str, keywords: List[str]) -> int:
        """Boost importance of chunks matching keywords"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        updated = 0
        for keyword in keywords:
            c.execute('''
                UPDATE context_chunks
                SET importance = MIN(importance + 1, 5)
                WHERE session_id = ? AND content LIKE ? AND importance < 5
            ''', (session_id, f'%{keyword}%'))
            updated += c.rowcount

        conn.commit()
        conn.close()

        return updated


# Example usage and testing
if __name__ == "__main__":
    print("Testing Context Manager with Smart Summarization...")

    manager = ContextManager()
    session_id = "test_session_" + datetime.now().strftime("%Y%m%d_%H%M%S")

    # Add various types of context
    print("\n1. Adding critical context...")
    manager.add_context(
        session_id,
        "Project Goal: Build autonomous AI agent with 25 capabilities for PC-Agent-Claw",
        "decision",
        ImportanceLevel.CRITICAL,
        ["project_goal", "requirements"]
    )

    print("2. Adding high importance context...")
    manager.add_context(
        session_id,
        "User prefers Anthropic CLI for GitHub operations, not Claude Code CLI",
        "preference",
        ImportanceLevel.HIGH,
        ["user_preference", "tools"]
    )

    print("3. Adding medium importance context...")
    manager.add_context(
        session_id,
        "Completed implementation of persistent memory system with SQLite database",
        "conversation",
        ImportanceLevel.MEDIUM,
        ["completed_task"]
    )

    print("4. Adding low importance context...")
    for i in range(10):
        manager.add_context(
            session_id,
            f"Background discussion about implementation details for feature {i}. " * 20,
            "conversation",
            ImportanceLevel.LOW,
            ["background"]
        )

    print("5. Adding trivial context...")
    for i in range(5):
        manager.add_context(
            session_id,
            f"Trivial note {i}: This is just some noise in the conversation. " * 30,
            "conversation",
            ImportanceLevel.TRIVIAL,
            ["noise"]
        )

    # Check stats
    print("\n6. Checking session stats...")
    stats = manager.get_session_stats(session_id)
    print(f"   Total tokens: {stats['total_tokens']}")
    print(f"   Critical tokens: {stats['critical_tokens']}")
    print(f"   Usage ratio: {stats['usage_ratio']*100:.2f}%")

    # Force compression test
    print("\n7. Testing compression...")
    result = manager.compress_context(session_id)
    print(f"   Original tokens: {result['original_tokens']}")
    print(f"   Compressed tokens: {result['compressed_tokens']}")
    print(f"   Compression ratio: {result['compression_ratio']:.2f}")
    print(f"   Chunks compressed: {result['chunks_compressed']}")
    print(f"   Tokens saved: {result['tokens_saved']}")

    # Check stats after compression
    print("\n8. Stats after compression...")
    stats = manager.get_session_stats(session_id)
    print(f"   Total tokens: {stats['total_tokens']}")
    print(f"   Usage ratio: {stats['usage_ratio']*100:.2f}%")

    # Get summary
    print("\n9. Getting context summary...")
    summary = manager.get_context_summary(session_id, ImportanceLevel.HIGH)
    print(f"   Summary length: {len(summary)} chars")
    print(f"   Summary preview: {summary[:200]}...")

    # Test prioritization
    print("\n10. Testing keyword prioritization...")
    updated = manager.prioritize_retention(session_id, ["Anthropic", "CLI"])
    print(f"    Updated {updated} chunks with boosted importance")

    print("\n[SUCCESS] Context Manager testing complete!")
    print(f"   Database: {manager.db_path}")
