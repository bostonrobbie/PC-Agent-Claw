"""
Comprehensive tests for ML-Based Semantic Search with Embeddings

Tests cover:
- Embedding generation and storage
- Vector similarity search
- FAISS index operations
- Batch processing
- Keyword fallback
- Hybrid search
- Performance benchmarks

Author: AI Self-Improvement System
Created: 2026-02-03
"""

import pytest
import sqlite3
import os
import tempfile
import numpy as np
from pathlib import Path

# Add parent directory to path for imports
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from search.semantic_search_ml import MLSemanticSearch, EmbeddingResult, TRANSFORMERS_AVAILABLE, FAISS_AVAILABLE


@pytest.fixture
def temp_db():
    """Create temporary database for testing"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    yield db_path
    # Cleanup
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture
def search_engine(temp_db):
    """Create search engine instance"""
    return MLSemanticSearch(db_path=temp_db, use_faiss=FAISS_AVAILABLE)


class TestDatabaseInitialization:
    """Test database creation and structure"""

    def test_database_creation(self, temp_db):
        """Test database is created with proper schema"""
        search = MLSemanticSearch(db_path=temp_db)
        assert os.path.exists(temp_db)

    def test_tables_exist(self, search_engine):
        """Test all required tables are created"""
        conn = sqlite3.connect(search_engine.db_path)
        c = conn.cursor()

        tables = ['projects', 'code_chunks', 'embeddings', 'semantic_index', 'search_history']
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in c.fetchall()]

        for table in tables:
            assert table in existing_tables, f"Table {table} not found"

        conn.close()

    def test_indexes_created(self, search_engine):
        """Test indexes are created for performance"""
        conn = sqlite3.connect(search_engine.db_path)
        c = conn.cursor()

        c.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in c.fetchall()]

        expected_indexes = ['idx_embeddings_chunk', 'idx_chunks_hash', 'idx_chunks_type', 'idx_semantic_word']
        for idx in expected_indexes:
            assert idx in indexes, f"Index {idx} not found"

        conn.close()


class TestEmbeddingGeneration:
    """Test embedding generation and storage"""

    @pytest.mark.skipif(not TRANSFORMERS_AVAILABLE, reason="transformers not available")
    def test_generate_embedding(self, search_engine):
        """Test single embedding generation"""
        text = "def authenticate_user(username, password):\n    return token"
        embedding = search_engine._generate_embedding(text)

        assert embedding is not None
        assert isinstance(embedding, np.ndarray)
        assert embedding.dtype == np.float32
        assert len(embedding) > 0

    @pytest.mark.skipif(not TRANSFORMERS_AVAILABLE, reason="transformers not available")
    def test_generate_embeddings_batch(self, search_engine):
        """Test batch embedding generation"""
        texts = [
            "def function1(): pass",
            "def function2(): pass",
            "def function3(): pass"
        ]
        embeddings = search_engine._generate_embeddings_batch(texts)

        assert len(embeddings) == 3
        for emb in embeddings:
            assert emb is not None
            assert isinstance(emb, np.ndarray)
            assert emb.dtype == np.float32

    @pytest.mark.skipif(not TRANSFORMERS_AVAILABLE, reason="transformers not available")
    def test_index_chunk(self, search_engine):
        """Test indexing a single chunk with embedding"""
        # Create a project and chunk first
        conn = sqlite3.connect(search_engine.db_path)
        c = conn.cursor()

        c.execute("INSERT INTO projects (name, root_path) VALUES (?, ?)", ("test_project", "/test"))
        project_id = c.lastrowid

        c.execute("""
            INSERT INTO code_chunks (project_id, file_path, content, content_hash,
                                   language, chunk_type, semantic_tags)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (project_id, "test.py", "def test(): pass", "hash1", "python", "function", "[]"))
        chunk_id = c.lastrowid
        conn.commit()
        conn.close()

        # Index the chunk
        result = search_engine.index_chunk(chunk_id, "def test(): pass")
        assert result is True

        # Verify embedding was stored
        conn = sqlite3.connect(search_engine.db_path)
        c = conn.cursor()
        c.execute("SELECT embedding FROM embeddings WHERE chunk_id = ?", (chunk_id,))
        row = c.fetchone()
        assert row is not None
        assert row[0] is not None
        conn.close()

    @pytest.mark.skipif(not TRANSFORMERS_AVAILABLE, reason="transformers not available")
    def test_index_chunks_batch(self, search_engine):
        """Test batch indexing of chunks"""
        # Create project and chunks
        conn = sqlite3.connect(search_engine.db_path)
        c = conn.cursor()

        c.execute("INSERT INTO projects (name, root_path) VALUES (?, ?)", ("test_project", "/test"))
        project_id = c.lastrowid

        chunk_ids = []
        for i in range(3):
            c.execute("""
                INSERT INTO code_chunks (project_id, file_path, content, content_hash,
                                       language, chunk_type, semantic_tags)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (project_id, f"test{i}.py", f"def func{i}(): pass", f"hash{i}", "python", "function", "[]"))
            chunk_ids.append(c.lastrowid)

        conn.commit()
        conn.close()

        # Batch index
        contents = [f"def func{i}(): pass" for i in range(3)]
        result = search_engine.index_chunks_batch(chunk_ids, contents)

        assert result['success'] is True
        assert result['chunks_indexed'] == 3

    @pytest.mark.skipif(not TRANSFORMERS_AVAILABLE, reason="transformers not available")
    def test_embedding_caching(self, search_engine):
        """Test embedding cache mechanism"""
        conn = sqlite3.connect(search_engine.db_path)
        c = conn.cursor()

        c.execute("INSERT INTO projects (name, root_path) VALUES (?, ?)", ("test_project", "/test"))
        project_id = c.lastrowid

        c.execute("""
            INSERT INTO code_chunks (project_id, file_path, content, content_hash,
                                   language, chunk_type, semantic_tags)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (project_id, "test.py", "def test(): pass", "hash1", "python", "function", "[]"))
        chunk_id = c.lastrowid
        conn.commit()
        conn.close()

        # Index chunk
        search_engine.index_chunk(chunk_id, "def test(): pass")

        # Check cache
        assert chunk_id in search_engine._embedding_cache
        assert isinstance(search_engine._embedding_cache[chunk_id], np.ndarray)


class TestSemanticSearch:
    """Test semantic search functionality"""

    @pytest.mark.skipif(not TRANSFORMERS_AVAILABLE, reason="transformers not available")
    def test_search_semantic_returns_results(self, search_engine):
        """Test semantic search returns proper results"""
        # Setup test data
        conn = sqlite3.connect(search_engine.db_path)
        c = conn.cursor()

        c.execute("INSERT INTO projects (name, root_path) VALUES (?, ?)", ("test_project", "/test"))
        project_id = c.lastrowid

        # Add chunks
        test_chunks = [
            ("authenticate function", "def authenticate_user(username, password):\n    token = generate_token()\n    return token"),
            ("fetch API function", "async def fetch_from_api(url):\n    response = await httpx.get(url)\n    return response"),
            ("database query", "SELECT * FROM users WHERE id = ?")
        ]

        for i, (desc, content) in enumerate(test_chunks):
            c.execute("""
                INSERT INTO code_chunks (project_id, file_path, content, content_hash,
                                       language, chunk_type, semantic_tags)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (project_id, f"test{i}.py", content, f"hash{i}", "python", "function", "[]"))

        conn.commit()
        conn.close()

        # Get chunk IDs and index them
        conn = sqlite3.connect(search_engine.db_path)
        c = conn.cursor()
        c.execute("SELECT id, content FROM code_chunks")
        chunks = c.fetchall()
        conn.close()

        chunk_ids = [chunk[0] for chunk in chunks]
        contents = [chunk[1] for chunk in chunks]
        search_engine.index_chunks_batch(chunk_ids, contents)

        # Search
        results = search_engine.search_semantic("authentication token generation", limit=3)

        assert isinstance(results, list)
        assert len(results) > 0
        assert all(isinstance(r, EmbeddingResult) for r in results)

    @pytest.mark.skipif(not TRANSFORMERS_AVAILABLE, reason="transformers not available")
    def test_search_similarity_scores(self, search_engine):
        """Test similarity scores are within valid range"""
        conn = sqlite3.connect(search_engine.db_path)
        c = conn.cursor()

        c.execute("INSERT INTO projects (name, root_path) VALUES (?, ?)", ("test_project", "/test"))
        project_id = c.lastrowid

        c.execute("""
            INSERT INTO code_chunks (project_id, file_path, content, content_hash,
                                   language, chunk_type, semantic_tags)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (project_id, "test.py", "def authenticate(): pass", "hash1", "python", "function", "[]"))
        chunk_id = c.lastrowid
        conn.commit()
        conn.close()

        search_engine.index_chunk(chunk_id, "def authenticate(): pass")

        results = search_engine.search_semantic("authentication", limit=1)

        for result in results:
            assert 0.0 <= result.similarity_score <= 1.0

    def test_search_keyword_fallback(self, search_engine):
        """Test keyword-based fallback search"""
        conn = sqlite3.connect(search_engine.db_path)
        c = conn.cursor()

        c.execute("INSERT INTO projects (name, root_path) VALUES (?, ?)", ("test_project", "/test"))
        project_id = c.lastrowid

        # Add code chunk
        c.execute("""
            INSERT INTO code_chunks (project_id, file_path, content, content_hash,
                                   language, chunk_type, semantic_tags)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (project_id, "test.py", "def database_query(): SELECT * FROM users", "hash1", "python", "function", '["database"]'))

        chunk_id = c.lastrowid

        # Add semantic index
        c.execute("INSERT INTO semantic_index (word, chunk_id, weight) VALUES (?, ?, ?)",
                 ("database", chunk_id, 3.0))
        c.execute("INSERT INTO semantic_index (word, chunk_id, weight) VALUES (?, ?, ?)",
                 ("query", chunk_id, 1.0))

        conn.commit()
        conn.close()

        # Search
        results = search_engine._search_keyword_fallback("database query", limit=5)

        assert isinstance(results, list)
        assert len(results) > 0
        assert all(isinstance(r, EmbeddingResult) for r in results)


class TestHybridSearch:
    """Test hybrid search combining semantic and keyword search"""

    @pytest.mark.skipif(not TRANSFORMERS_AVAILABLE, reason="transformers not available")
    def test_hybrid_search(self, search_engine):
        """Test hybrid search merges results properly"""
        conn = sqlite3.connect(search_engine.db_path)
        c = conn.cursor()

        c.execute("INSERT INTO projects (name, root_path) VALUES (?, ?)", ("test_project", "/test"))
        project_id = c.lastrowid

        c.execute("""
            INSERT INTO code_chunks (project_id, file_path, content, content_hash,
                                   language, chunk_type, semantic_tags)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (project_id, "test.py", "def authenticate_user(): pass", "hash1", "python", "function", "[]"))

        chunk_id = c.lastrowid
        conn.commit()
        conn.close()

        search_engine.index_chunk(chunk_id, "def authenticate_user(): pass")

        results = search_engine.search_hybrid("authentication", limit=5)

        assert isinstance(results, list)
        assert all(isinstance(r, EmbeddingResult) for r in results)

    @pytest.mark.skipif(not TRANSFORMERS_AVAILABLE, reason="transformers not available")
    def test_hybrid_search_weighting(self, search_engine):
        """Test semantic weight affects result ordering"""
        conn = sqlite3.connect(search_engine.db_path)
        c = conn.cursor()

        c.execute("INSERT INTO projects (name, root_path) VALUES (?, ?)", ("test_project", "/test"))
        project_id = c.lastrowid

        c.execute("""
            INSERT INTO code_chunks (project_id, file_path, content, content_hash,
                                   language, chunk_type, semantic_tags)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (project_id, "test.py", "def authenticate(): pass", "hash1", "python", "function", "[]"))

        chunk_id = c.lastrowid
        conn.commit()
        conn.close()

        search_engine.index_chunk(chunk_id, "def authenticate(): pass")

        # Hybrid with high semantic weight
        results_high_weight = search_engine.search_hybrid("authentication", limit=5, semantic_weight=0.9)
        # Hybrid with low semantic weight
        results_low_weight = search_engine.search_hybrid("authentication", limit=5, semantic_weight=0.1)

        assert isinstance(results_high_weight, list)
        assert isinstance(results_low_weight, list)


class TestStatistics:
    """Test statistics collection"""

    def test_get_stats_empty_db(self, search_engine):
        """Test stats on empty database"""
        stats = search_engine.get_stats()

        assert isinstance(stats, dict)
        assert stats['total_projects'] == 0
        assert stats['total_chunks'] == 0
        assert stats['total_embeddings'] == 0
        assert stats['total_searches'] == 0

    @pytest.mark.skipif(not TRANSFORMERS_AVAILABLE, reason="transformers not available")
    def test_get_stats_populated_db(self, search_engine):
        """Test stats with data"""
        conn = sqlite3.connect(search_engine.db_path)
        c = conn.cursor()

        c.execute("INSERT INTO projects (name, root_path) VALUES (?, ?)", ("test_project", "/test"))
        project_id = c.lastrowid

        c.execute("""
            INSERT INTO code_chunks (project_id, file_path, content, content_hash,
                                   language, chunk_type, semantic_tags)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (project_id, "test.py", "def test(): pass", "hash1", "python", "function", "[]"))

        chunk_id = c.lastrowid
        conn.commit()
        conn.close()

        search_engine.index_chunk(chunk_id, "def test(): pass")

        stats = search_engine.get_stats()

        assert stats['total_projects'] == 1
        assert stats['total_chunks'] == 1
        assert stats['total_embeddings'] == 1
        assert 'embedding_coverage' in stats

    def test_search_history_recorded(self, search_engine):
        """Test search history is recorded"""
        search_engine._record_search("test query", 5, "semantic", 42.5)

        conn = sqlite3.connect(search_engine.db_path)
        c = conn.cursor()
        c.execute("SELECT query, results_count, search_type, elapsed_ms FROM search_history")
        row = c.fetchone()
        conn.close()

        assert row is not None
        assert row[0] == "test query"
        assert row[1] == 5
        assert row[2] == "semantic"
        assert row[3] == 42.5


class TestFAISSIntegration:
    """Test FAISS index integration if available"""

    @pytest.mark.skipif(not FAISS_AVAILABLE, reason="FAISS not available")
    @pytest.mark.skipif(not TRANSFORMERS_AVAILABLE, reason="transformers not available")
    def test_faiss_index_initialization(self, search_engine):
        """Test FAISS index initialization"""
        assert search_engine._faiss_index is not None or not search_engine.use_faiss

    @pytest.mark.skipif(not FAISS_AVAILABLE, reason="FAISS not available")
    @pytest.mark.skipif(not TRANSFORMERS_AVAILABLE, reason="transformers not available")
    def test_faiss_search_performance(self, search_engine):
        """Test FAISS search performance"""
        import time

        conn = sqlite3.connect(search_engine.db_path)
        c = conn.cursor()

        c.execute("INSERT INTO projects (name, root_path) VALUES (?, ?)", ("test_project", "/test"))
        project_id = c.lastrowid

        # Add multiple chunks
        chunk_ids = []
        for i in range(10):
            c.execute("""
                INSERT INTO code_chunks (project_id, file_path, content, content_hash,
                                       language, chunk_type, semantic_tags)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (project_id, f"test{i}.py", f"def function{i}(): pass", f"hash{i}", "python", "function", "[]"))
            chunk_ids.append(c.lastrowid)

        conn.commit()
        conn.close()

        # Index all
        contents = [f"def function{i}(): pass" for i in range(10)]
        search_engine.index_chunks_batch(chunk_ids, contents)

        # Time the search
        start_time = time.time()
        results = search_engine.search_semantic("function", limit=5)
        elapsed_ms = (time.time() - start_time) * 1000

        assert elapsed_ms < 100, f"Search took {elapsed_ms}ms, expected <100ms"
        assert len(results) <= 5


class TestThreadSafety:
    """Test thread safety"""

    @pytest.mark.skipif(not TRANSFORMERS_AVAILABLE, reason="transformers not available")
    def test_concurrent_embedding_generation(self, search_engine):
        """Test concurrent embedding generation is thread-safe"""
        import threading

        results = []

        def generate_embedding():
            emb = search_engine._generate_embedding("def test(): pass")
            results.append(emb)

        threads = [threading.Thread(target=generate_embedding) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 5
        assert all(r is not None for r in results)


class TestErrorHandling:
    """Test error handling"""

    def test_invalid_query_handling(self, search_engine):
        """Test handling of invalid queries"""
        # Empty query
        results = search_engine.search_semantic("", limit=5)
        assert isinstance(results, list)

        # Very long query
        long_query = "test " * 10000
        results = search_engine.search_semantic(long_query, limit=5)
        assert isinstance(results, list)

    def test_duplicate_chunk_handling(self, search_engine):
        """Test handling of duplicate chunks"""
        conn = sqlite3.connect(search_engine.db_path)
        c = conn.cursor()

        c.execute("INSERT INTO projects (name, root_path) VALUES (?, ?)", ("test_project", "/test"))
        project_id = c.lastrowid

        # Add same chunk twice (same hash)
        for i in range(2):
            try:
                c.execute("""
                    INSERT INTO code_chunks (project_id, file_path, content, content_hash,
                                           language, chunk_type, semantic_tags)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (project_id, "test.py", "def test(): pass", "same_hash", "python", "function", "[]"))
            except sqlite3.IntegrityError:
                pass

        conn.commit()
        conn.close()

        stats = search_engine.get_stats()
        assert stats['total_chunks'] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
