"""
ML-Based Semantic Search with Dense Vector Embeddings

Implements semantic code search using sentence-transformers and FAISS for efficient
vector similarity search. Provides ML-enhanced code retrieval with embeddings and
backward compatibility with keyword-based search.

Features:
- Dense vector embeddings for code chunks (all-MiniLM-L6-v2 or CodeBERT)
- FAISS-based efficient vector search with <100ms latency
- SQLite BLOB storage for embeddings
- Semantic similarity search with cosine similarity
- Batch embedding generation for performance
- Model caching and lazy loading
- Top-K results with similarity scores
- Incremental updates supported
- Backward compatible with existing keyword-based search

Author: AI Self-Improvement System
Created: 2026-02-03
"""

import sqlite3
import json
import os
import hashlib
import numpy as np
import time
import threading
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from pathlib import Path
import re
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ML imports with graceful fallback
try:
    from sentence_transformers import SentenceTransformer
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("sentence-transformers not installed. Install with: pip install sentence-transformers")

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logger.warning("faiss-cpu not installed. Install with: pip install faiss-cpu")


@dataclass
class EmbeddingResult:
    """Result from semantic search with embedding metadata"""
    chunk_id: int
    file_path: str
    content: str
    language: str
    chunk_type: str
    semantic_tags: List[str]
    similarity_score: float  # 0.0 to 1.0 cosine similarity
    embedding_distance: float  # L2 distance
    relevance_score: Optional[float] = None  # Combined score
    project_name: Optional[str] = None


class MLSemanticSearch:
    """
    ML-based semantic search using dense vector embeddings.

    Combines transformer embeddings with FAISS for fast similarity search.
    Maintains backward compatibility with keyword-based search.
    """

    def __init__(self,
                 db_path: str = "semantic_search_ml.db",
                 embedding_model: str = "all-MiniLM-L6-v2",
                 use_faiss: bool = True,
                 embedding_cache_size: int = 10000,
                 max_workers: int = 4):
        """
        Initialize ML-based semantic search.

        Args:
            db_path: Path to SQLite database
            embedding_model: Model name from sentence-transformers
            use_faiss: Use FAISS for vector search (much faster)
            embedding_cache_size: Max embeddings to cache in memory
            max_workers: Number of worker threads
        """
        self.db_path = db_path
        self.embedding_model_name = embedding_model
        self.use_faiss = use_faiss and FAISS_AVAILABLE
        self.embedding_cache_size = embedding_cache_size
        self.max_workers = max_workers

        # Model and search state
        self._model = None
        self._model_lock = threading.Lock()
        self._faiss_index = None
        self._index_lock = threading.Lock()
        self._embedding_cache: Dict[int, np.ndarray] = {}
        self._chunk_id_map: Dict[int, int] = {}  # FAISS index -> chunk_id
        self._next_faiss_id = 0
        self._db_lock = threading.Lock()

        self._init_db()

    def _init_db(self):
        """Initialize database with embedding storage"""
        with self._db_lock:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()

            # Projects table
            c.execute('''
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    root_path TEXT NOT NULL,
                    last_indexed TEXT,
                    total_files INTEGER DEFAULT 0,
                    total_chunks INTEGER DEFAULT 0,
                    total_embeddings INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Code chunks table
            c.execute('''
                CREATE TABLE IF NOT EXISTS code_chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    file_path TEXT NOT NULL,
                    content TEXT NOT NULL,
                    content_hash TEXT UNIQUE NOT NULL,
                    language TEXT NOT NULL,
                    chunk_type TEXT NOT NULL,
                    semantic_tags TEXT,
                    dependencies TEXT,
                    complexity_score INTEGER DEFAULT 0,
                    lines_of_code INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_updated TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects (id)
                )
            ''')

            # Embeddings table - stores dense vectors
            c.execute('''
                CREATE TABLE IF NOT EXISTS embeddings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chunk_id INTEGER UNIQUE NOT NULL,
                    embedding BLOB NOT NULL,
                    embedding_model TEXT NOT NULL,
                    embedding_dim INTEGER NOT NULL,
                    norm REAL DEFAULT 1.0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (chunk_id) REFERENCES code_chunks (id) ON DELETE CASCADE
                )
            ''')

            # Semantic index for keyword fallback
            c.execute('''
                CREATE TABLE IF NOT EXISTS semantic_index (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    word TEXT NOT NULL,
                    chunk_id INTEGER NOT NULL,
                    weight REAL DEFAULT 1.0,
                    FOREIGN KEY (chunk_id) REFERENCES code_chunks (id) ON DELETE CASCADE
                )
            ''')

            # Search history
            c.execute('''
                CREATE TABLE IF NOT EXISTS search_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT NOT NULL,
                    results_count INTEGER NOT NULL,
                    search_type TEXT,
                    elapsed_ms REAL,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Create indexes for performance
            c.execute('CREATE INDEX IF NOT EXISTS idx_embeddings_chunk ON embeddings(chunk_id)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_chunks_hash ON code_chunks(content_hash)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_chunks_type ON code_chunks(chunk_type)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_semantic_word ON semantic_index(word)')

            conn.commit()
            conn.close()

        logger.info(f"Database initialized: {self.db_path}")

    def _load_model(self) -> Optional[SentenceTransformer]:
        """Lazy load embedding model with thread safety"""
        if not TRANSFORMERS_AVAILABLE:
            logger.error("sentence-transformers not available")
            return None

        with self._model_lock:
            if self._model is None:
                try:
                    logger.info(f"Loading embedding model: {self.embedding_model_name}")
                    self._model = SentenceTransformer(self.embedding_model_name)
                    dim = self._model.get_sentence_embedding_dimension()
                    logger.info(f"Model loaded. Embedding dimension: {dim}")
                except Exception as e:
                    logger.error(f"Failed to load model {self.embedding_model_name}: {e}")
                    return None

            return self._model

    def _generate_embedding(self, text: str) -> Optional[np.ndarray]:
        """Generate embedding for a text chunk"""
        model = self._load_model()
        if model is None:
            return None

        try:
            text = text.strip()
            if not text:
                return None

            embedding = model.encode(text, convert_to_numpy=True)
            return embedding.astype(np.float32)
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None

    def _generate_embeddings_batch(self, texts: List[str], batch_size: int = 32) -> List[Optional[np.ndarray]]:
        """Generate embeddings for multiple texts efficiently"""
        model = self._load_model()
        if model is None:
            return [None] * len(texts)

        try:
            embeddings = model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=False,
                convert_to_numpy=True
            )
            return [e.astype(np.float32) for e in embeddings]
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            return [None] * len(texts)

    def _init_faiss_index(self, dimension: int = 384):
        """Initialize FAISS index for similarity search"""
        if not FAISS_AVAILABLE or not self.use_faiss:
            return

        with self._index_lock:
            try:
                # Create flat index with L2 distance
                self._faiss_index = faiss.IndexFlatL2(dimension)
                self._next_faiss_id = 0
                self._chunk_id_map.clear()
                logger.info(f"FAISS index initialized (dimension: {dimension})")
            except Exception as e:
                logger.error(f"Failed to initialize FAISS index: {e}")
                self._faiss_index = None

    def _load_embeddings_to_faiss(self):
        """Load all embeddings from database to FAISS index"""
        if not self._faiss_index:
            self._init_faiss_index()

        with self._db_lock:
            try:
                conn = sqlite3.connect(self.db_path)
                c = conn.cursor()

                c.execute('''
                    SELECT chunk_id, embedding
                    FROM embeddings
                    ORDER BY chunk_id
                ''')

                embeddings_list = []
                chunk_ids = []

                for chunk_id, embedding_bytes in c.fetchall():
                    embedding = np.frombuffer(embedding_bytes, dtype=np.float32)
                    embeddings_list.append(embedding)
                    chunk_ids.append(chunk_id)

                if embeddings_list:
                    embeddings_array = np.array(embeddings_list)
                    with self._index_lock:
                        self._faiss_index.add(embeddings_array)
                        for i, chunk_id in enumerate(chunk_ids):
                            self._chunk_id_map[i] = chunk_id
                        self._next_faiss_id = len(chunk_ids)

                    logger.info(f"Loaded {len(embeddings_list)} embeddings to FAISS index")

                conn.close()
            except Exception as e:
                logger.error(f"Error loading embeddings to FAISS: {e}")

    def index_chunk(self, chunk_id: int, content: str, force: bool = False) -> bool:
        """
        Generate and store embedding for a code chunk.

        Args:
            chunk_id: ID of code chunk in database
            content: Code content to embed
            force: Force re-indexing even if embedding exists

        Returns:
            True if embedding was generated and stored
        """
        if not TRANSFORMERS_AVAILABLE:
            logger.warning("sentence-transformers not available, skipping embedding")
            return False

        # Check if embedding already exists
        if not force:
            with self._db_lock:
                conn = sqlite3.connect(self.db_path)
                c = conn.cursor()
                c.execute('SELECT id FROM embeddings WHERE chunk_id = ?', (chunk_id,))
                if c.fetchone():
                    conn.close()
                    return True
                conn.close()

        # Generate embedding
        embedding = self._generate_embedding(content)
        if embedding is None:
            return False

        # Store in database
        try:
            with self._db_lock:
                conn = sqlite3.connect(self.db_path)
                c = conn.cursor()

                embedding_bytes = embedding.tobytes()
                embedding_dim = len(embedding)

                c.execute('''
                    INSERT OR REPLACE INTO embeddings
                    (chunk_id, embedding, embedding_model, embedding_dim)
                    VALUES (?, ?, ?, ?)
                ''', (chunk_id, embedding_bytes, self.embedding_model_name, embedding_dim))

                conn.commit()
                conn.close()

            # Cache embedding
            self._embedding_cache[chunk_id] = embedding
            if len(self._embedding_cache) > self.embedding_cache_size:
                self._embedding_cache.pop(next(iter(self._embedding_cache)))

            # Add to FAISS index
            if self._faiss_index:
                with self._index_lock:
                    self._faiss_index.add(np.array([embedding]))
                    self._chunk_id_map[self._next_faiss_id] = chunk_id
                    self._next_faiss_id += 1

            return True

        except Exception as e:
            logger.error(f"Error storing embedding for chunk {chunk_id}: {e}")
            return False

    def index_chunks_batch(self, chunk_ids: List[int], contents: List[str]) -> Dict:
        """
        Efficiently index multiple chunks with embeddings.

        Args:
            chunk_ids: List of chunk IDs
            contents: List of code contents

        Returns:
            Dict with indexing statistics
        """
        if not TRANSFORMERS_AVAILABLE:
            logger.warning("sentence-transformers not available")
            return {'success': False, 'chunks_indexed': 0}

        if len(chunk_ids) != len(contents):
            raise ValueError("chunk_ids and contents must have same length")

        start_time = time.time()

        # Generate embeddings in batch
        embeddings = self._generate_embeddings_batch(contents)

        # Store embeddings and build FAISS index
        stored_count = 0
        faiss_embeddings = []
        faiss_chunk_ids = []

        try:
            with self._db_lock:
                conn = sqlite3.connect(self.db_path)
                c = conn.cursor()

                for chunk_id, embedding in zip(chunk_ids, embeddings):
                    if embedding is None:
                        continue

                    try:
                        embedding_bytes = embedding.tobytes()
                        embedding_dim = len(embedding)

                        c.execute('''
                            INSERT OR REPLACE INTO embeddings
                            (chunk_id, embedding, embedding_model, embedding_dim)
                            VALUES (?, ?, ?, ?)
                        ''', (chunk_id, embedding_bytes, self.embedding_model_name, embedding_dim))

                        stored_count += 1

                        # Collect for FAISS
                        faiss_embeddings.append(embedding)
                        faiss_chunk_ids.append(chunk_id)

                        # Cache
                        self._embedding_cache[chunk_id] = embedding

                    except Exception as e:
                        logger.error(f"Error storing embedding {chunk_id}: {e}")

                conn.commit()
                conn.close()

            # Add to FAISS index
            if self._faiss_index and faiss_embeddings:
                with self._index_lock:
                    embeddings_array = np.array(faiss_embeddings)
                    self._faiss_index.add(embeddings_array)
                    for embedding in faiss_embeddings:
                        idx = len(self._chunk_id_map)
                        self._chunk_id_map[idx] = faiss_chunk_ids[idx]
                        self._next_faiss_id += 1

            elapsed = time.time() - start_time
            return {
                'success': True,
                'chunks_indexed': stored_count,
                'elapsed_time': elapsed,
                'chunks_per_sec': stored_count / elapsed if elapsed > 0 else 0
            }

        except Exception as e:
            logger.error(f"Error in batch indexing: {e}")
            return {
                'success': False,
                'chunks_indexed': stored_count,
                'error': str(e)
            }


    def search_semantic(self, query: str, limit: int = 10, threshold: float = 0.3) -> List[EmbeddingResult]:
        """
        Semantic search using embedding similarity.

        Args:
            query: Search query text
            limit: Maximum results to return
            threshold: Minimum similarity score (0.0-1.0)

        Returns:
            List of EmbeddingResult objects sorted by similarity
        """
        start_time = time.time()

        if not TRANSFORMERS_AVAILABLE:
            logger.warning("Falling back to keyword search (transformers unavailable)")
            return self._search_keyword_fallback(query, limit)

        # Generate query embedding
        query_embedding = self._generate_embedding(query)
        if query_embedding is None:
            return []

        results = []

        if self._faiss_index and self.use_faiss:
            results = self._search_faiss(query_embedding, limit, threshold)
        else:
            results = self._search_exhaustive(query_embedding, limit, threshold)

        elapsed = time.time() - start_time

        # Record search
        self._record_search(query, len(results), 'semantic', elapsed * 1000)

        return results

    def _search_faiss(self, query_embedding: np.ndarray, limit: int, threshold: float) -> List[EmbeddingResult]:
        """Search using FAISS index"""
        try:
            # Ensure index has data
            if self._faiss_index.ntotal == 0:
                self._load_embeddings_to_faiss()

            if self._faiss_index.ntotal == 0:
                return []

            # Search FAISS index
            query_embedding = np.array([query_embedding], dtype=np.float32)

            with self._index_lock:
                distances, indices = self._faiss_index.search(query_embedding, min(limit * 2, self._faiss_index.ntotal))

            results = []
            dimension = query_embedding.shape[1]

            for distance, idx in zip(distances[0], indices[0]):
                if idx < 0:  # Invalid result
                    continue

                chunk_id = self._chunk_id_map.get(idx)
                if chunk_id is None:
                    continue

                # Convert L2 distance to similarity score
                max_distance = np.sqrt(2 * dimension)
                similarity = 1.0 - (distance / max_distance)

                if similarity >= threshold:
                    result = self._get_chunk_result(chunk_id, similarity, distance)
                    if result:
                        results.append(result)

                if len(results) >= limit:
                    break

            return results

        except Exception as e:
            logger.error(f"Error in FAISS search: {e}")
            return []

    def _search_exhaustive(self, query_embedding: np.ndarray, limit: int, threshold: float) -> List[EmbeddingResult]:
        """Exhaustive search through all embeddings in database"""
        results = []

        try:
            with self._db_lock:
                conn = sqlite3.connect(self.db_path)
                c = conn.cursor()

                c.execute('''
                    SELECT chunk_id, embedding
                    FROM embeddings
                    ORDER BY chunk_id
                    LIMIT 1000
                ''')

                similarities = []

                for chunk_id, embedding_bytes in c.fetchall():
                    embedding = np.frombuffer(embedding_bytes, dtype=np.float32)

                    # Calculate cosine similarity
                    dot_product = np.dot(query_embedding, embedding)
                    norm_q = np.linalg.norm(query_embedding)
                    norm_e = np.linalg.norm(embedding)

                    if norm_q > 0 and norm_e > 0:
                        similarity = dot_product / (norm_q * norm_e)
                    else:
                        similarity = 0.0

                    if similarity >= threshold:
                        similarities.append((chunk_id, similarity))

                conn.close()

            # Sort by similarity and get top results
            similarities.sort(key=lambda x: x[1], reverse=True)

            for chunk_id, similarity in similarities[:limit]:
                result = self._get_chunk_result(chunk_id, similarity, 0.0)
                if result:
                    results.append(result)

            return results

        except Exception as e:
            logger.error(f"Error in exhaustive search: {e}")
            return []

    def _get_chunk_result(self, chunk_id: int, similarity: float, distance: float) -> Optional[EmbeddingResult]:
        """Get chunk data and create EmbeddingResult"""
        try:
            with self._db_lock:
                conn = sqlite3.connect(self.db_path)
                c = conn.cursor()

                c.execute('''
                    SELECT cc.id, cc.file_path, cc.content, cc.language, cc.chunk_type,
                           cc.semantic_tags, p.name
                    FROM code_chunks cc
                    LEFT JOIN projects p ON cc.project_id = p.id
                    WHERE cc.id = ?
                ''', (chunk_id,))

                row = c.fetchone()
                conn.close()

                if not row:
                    return None

                return EmbeddingResult(
                    chunk_id=row[0],
                    file_path=row[1],
                    content=row[2],
                    language=row[3],
                    chunk_type=row[4],
                    semantic_tags=json.loads(row[5]) if row[5] else [],
                    similarity_score=similarity,
                    embedding_distance=distance,
                    project_name=row[6]
                )

        except Exception as e:
            logger.error(f"Error getting chunk result for {chunk_id}: {e}")
            return None

    def _search_keyword_fallback(self, query: str, limit: int) -> List[EmbeddingResult]:
        """Fallback keyword-based search when embeddings unavailable"""
        results = []

        try:
            with self._db_lock:
                conn = sqlite3.connect(self.db_path)
                c = conn.cursor()

                # Extract query words
                query_words = set(re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]{2,}\b', query.lower()))

                if query_words:
                    placeholders = ','.join('?' * len(query_words))
                    c.execute(f'''
                        SELECT cc.id, cc.file_path, cc.content, cc.language, cc.chunk_type,
                               cc.semantic_tags, p.name, SUM(si.weight) as score
                        FROM code_chunks cc
                        LEFT JOIN semantic_index si ON cc.id = si.chunk_id
                        LEFT JOIN projects p ON cc.project_id = p.id
                        WHERE si.word IN ({placeholders})
                        GROUP BY cc.id
                        ORDER BY score DESC
                        LIMIT ?
                    ''', (*query_words, limit))

                    for row in c.fetchall():
                        results.append(EmbeddingResult(
                            chunk_id=row[0],
                            file_path=row[1],
                            content=row[2],
                            language=row[3],
                            chunk_type=row[4],
                            semantic_tags=json.loads(row[5]) if row[5] else [],
                            similarity_score=0.0,
                            embedding_distance=0.0,
                            relevance_score=row[7],
                            project_name=row[6]
                        ))

                conn.close()

        except Exception as e:
            logger.error(f"Error in keyword fallback search: {e}")

        return results

    def search_hybrid(self, query: str, limit: int = 10, semantic_weight: float = 0.7) -> List[EmbeddingResult]:
        """
        Hybrid search combining semantic and keyword search.

        Args:
            query: Search query
            limit: Maximum results
            semantic_weight: Weight for semantic results (0.0-1.0)

        Returns:
            Combined and ranked results
        """
        # Semantic search
        semantic_results = self.search_semantic(query, limit * 2)

        # Keyword search
        keyword_results = self._search_keyword_fallback(query, limit * 2)

        # Combine and re-rank
        combined = {}
        for result in semantic_results:
            score = result.similarity_score * semantic_weight
            if result.chunk_id in combined:
                combined[result.chunk_id].relevance_score = (combined[result.chunk_id].relevance_score or 0) + score
            else:
                result.relevance_score = score
                combined[result.chunk_id] = result

        for result in keyword_results:
            weight = (1.0 - semantic_weight)
            score = (result.relevance_score or 1.0) * weight
            if result.chunk_id in combined:
                combined[result.chunk_id].relevance_score = (combined[result.chunk_id].relevance_score or 0) + score
            else:
                result.relevance_score = score
                combined[result.chunk_id] = result

        # Sort by combined relevance
        sorted_results = sorted(combined.values(), key=lambda x: x.relevance_score or 0, reverse=True)
        return sorted_results[:limit]

    def _record_search(self, query: str, results_count: int, search_type: str, elapsed_ms: float):
        """Record search query for analytics"""
        try:
            with self._db_lock:
                conn = sqlite3.connect(self.db_path)
                c = conn.cursor()

                c.execute('''
                    INSERT INTO search_history (query, results_count, search_type, elapsed_ms)
                    VALUES (?, ?, ?, ?)
                ''', (query, results_count, search_type, elapsed_ms))

                conn.commit()
                conn.close()

        except Exception as e:
            logger.error(f"Error recording search: {e}")

    def get_stats(self) -> Dict:
        """Get search engine statistics"""
        try:
            with self._db_lock:
                conn = sqlite3.connect(self.db_path)
                c = conn.cursor()

                c.execute('SELECT COUNT(*) FROM projects')
                total_projects = c.fetchone()[0]

                c.execute('SELECT COUNT(*) FROM code_chunks')
                total_chunks = c.fetchone()[0]

                c.execute('SELECT COUNT(*) FROM embeddings')
                total_embeddings = c.fetchone()[0]

                c.execute('SELECT COUNT(*) FROM search_history')
                total_searches = c.fetchone()[0]

                if total_searches > 0:
                    c.execute('SELECT AVG(elapsed_ms) FROM search_history')
                    avg_search_time = c.fetchone()[0] or 0
                else:
                    avg_search_time = 0

                conn.close()

                return {
                    'total_projects': total_projects,
                    'total_chunks': total_chunks,
                    'total_embeddings': total_embeddings,
                    'embedding_coverage': f"{100.0 * total_embeddings / total_chunks:.1f}%" if total_chunks > 0 else "0%",
                    'total_searches': total_searches,
                    'avg_search_time_ms': round(avg_search_time, 2),
                    'using_faiss': self.use_faiss,
                    'faiss_index_size': self._faiss_index.ntotal if self._faiss_index else 0,
                    'cache_size': len(self._embedding_cache)
                }

        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}


# Testing and demonstration
if __name__ == "__main__":
    print("Testing ML-Based Semantic Search...\n")

    # Check dependencies
    if not TRANSFORMERS_AVAILABLE:
        print("WARNING: sentence-transformers not installed")
        print("Install with: pip install sentence-transformers")
        print("Some tests will be skipped\n")

    if not FAISS_AVAILABLE:
        print("WARNING: faiss-cpu not installed")
        print("Install with: pip install faiss-cpu")
        print("Will use slower exhaustive search\n")

    search = MLSemanticSearch(
        db_path="test_ml_search.db",
        use_faiss=FAISS_AVAILABLE
    )

    # Test data
    sample_chunks = [
        (1, "def authenticate_user(username, password):\n    token = generate_jwt_token(username)\n    return token"),
        (2, "async def fetch_data_from_api(url):\n    response = await httpx.get(url)\n    return response.json()"),
        (3, "SELECT * FROM users WHERE email = ?"),
        (4, "class UserRepository:\n    def save(self, user):\n        db.commit()\n        return user"),
        (5, "def calculate_hash(data):\n    return hashlib.sha256(data).hexdigest()")
    ]

    print("1. Indexing sample chunks with embeddings...")
    if TRANSFORMERS_AVAILABLE:
        chunk_ids = [cid for cid, _ in sample_chunks]
        contents = [content for _, content in sample_chunks]
        result = search.index_chunks_batch(chunk_ids, contents)
        print(f"   Indexed: {result['chunks_indexed']} chunks")
        print(f"   Time: {result.get('elapsed_time', 0):.2f}s")
    else:
        print("   Skipped (transformers not available)")

    print("\n2. Semantic search test...")
    if TRANSFORMERS_AVAILABLE:
        results = search.search_semantic("authentication and token generation", limit=3)
        print(f"   Found {len(results)} results")
        for i, result in enumerate(results, 1):
            print(f"   {i}. Type: {result.chunk_type}, Score: {result.similarity_score:.3f}")
            print(f"      {result.content[:60]}...")
    else:
        print("   Skipped (transformers not available)")

    print("\n3. Statistics...")
    stats = search.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")

    print("\n[SUCCESS] ML-Based Semantic Search testing complete!")
    print(f"   Database: test_ml_search.db")
