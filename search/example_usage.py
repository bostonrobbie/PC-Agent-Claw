"""
Example Usage: ML-Based Semantic Search with Embeddings

Demonstrates practical usage patterns for semantic code search.

Author: AI Self-Improvement System
Created: 2026-02-03
"""

import os
import time
from search.semantic_search_ml import MLSemanticSearch, TRANSFORMERS_AVAILABLE, FAISS_AVAILABLE


def example_basic_indexing():
    """Example: Basic chunk indexing with embeddings"""
    print("\n" + "="*80)
    print("EXAMPLE 1: Basic Chunk Indexing")
    print("="*80)

    search = MLSemanticSearch(db_path="example_search.db")

    # Sample code chunks to index
    code_chunks = {
        1: "def authenticate_user(username, password):\n    token = jwt.encode({'user': username})\n    return token",
        2: "async def fetch_user_data(user_id):\n    response = await api.get(f'/users/{user_id}')\n    return response.json()",
        3: "def hash_password(password):\n    return bcrypt.hashpw(password.encode(), bcrypt.gensalt())",
        4: "class UserRepository:\n    def save(self, user):\n        self.db.users.insert_one(user)\n        return user",
        5: "SELECT * FROM users WHERE email = ? AND is_active = 1",
    }

    if not TRANSFORMERS_AVAILABLE:
        print("[WARNING] Transformers not available - skipping embedding generation")
        return

    print("\nIndexing code chunks with embeddings...")
    chunk_ids = list(code_chunks.keys())
    contents = list(code_chunks.values())

    start_time = time.time()
    result = search.index_chunks_batch(chunk_ids, contents)
    elapsed = time.time() - start_time

    print(f"Result: {result}")
    print(f"  Chunks indexed: {result['chunks_indexed']}")
    print(f"  Time: {elapsed:.2f}s")
    print(f"  Speed: {result.get('chunks_per_sec', 0):.1f} chunks/sec")


def example_semantic_search():
    """Example: Semantic search using embeddings"""
    print("\n" + "="*80)
    print("EXAMPLE 2: Semantic Search")
    print("="*80)

    search = MLSemanticSearch(db_path="example_search.db")

    queries = [
        "user authentication and token generation",
        "fetch data from API endpoint",
        "password security and encryption",
        "database operations and persistence"
    ]

    if not TRANSFORMERS_AVAILABLE:
        print("[WARNING] Transformers not available - using keyword fallback")

    for query in queries:
        print(f"\nQuery: {query}")
        print("-" * 60)

        start_time = time.time()
        results = search.search_semantic(query, limit=2, threshold=0.3)
        elapsed = time.time() - start_time

        if results:
            for i, result in enumerate(results, 1):
                print(f"\n{i}. Relevance: {result.similarity_score:.3f}")
                print(f"   File: {result.file_path}")
                print(f"   Type: {result.chunk_type}")
                print(f"   Content: {result.content[:70]}...")
        else:
            print("  No results found")

        print(f"  Search time: {elapsed*1000:.1f}ms")


def example_hybrid_search():
    """Example: Hybrid search combining semantic and keyword"""
    print("\n" + "="*80)
    print("EXAMPLE 3: Hybrid Search")
    print("="*80)

    search = MLSemanticSearch(db_path="example_search.db")

    query = "authentication security"

    print(f"\nQuery: {query}")
    print("-" * 60)

    # Try different semantic weights
    weights = [0.0, 0.5, 1.0]

    for weight in weights:
        print(f"\nSemantic weight: {weight} (Keyword: {1-weight})")

        results = search.search_hybrid(query, limit=3, semantic_weight=weight)

        if results:
            for result in results:
                score_label = f"ML: {result.similarity_score:.3f}" if result.similarity_score > 0 else "Keyword"
                print(f"  - Combined: {result.relevance_score:.3f} ({score_label})")
        else:
            print("  No results")


def example_statistics():
    """Example: Retrieve search statistics"""
    print("\n" + "="*80)
    print("EXAMPLE 4: Search Statistics")
    print("="*80)

    search = MLSemanticSearch(db_path="example_search.db")

    stats = search.get_stats()

    print("\nSearch Engine Statistics:")
    print("-" * 60)
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print("\nInterpretation:")
    print(f"  - Embedding coverage: {stats['embedding_coverage']} of chunks have embeddings")
    print(f"  - Average search time: {stats['avg_search_time_ms']}ms")
    print(f"  - FAISS enabled: {stats['using_faiss']}")
    if stats['using_faiss']:
        print(f"  - FAISS index size: {stats['faiss_index_size']} embeddings")


def example_performance_benchmark():
    """Example: Performance benchmarking"""
    print("\n" + "="*80)
    print("EXAMPLE 5: Performance Benchmarking")
    print("="*80)

    if not TRANSFORMERS_AVAILABLE:
        print("[WARNING] Transformers not available - skipping benchmark")
        return

    search = MLSemanticSearch(db_path="example_search.db", use_faiss=FAISS_AVAILABLE)

    # Test embedding generation speed
    print("\n1. Embedding Generation Speed")
    print("-" * 60)

    test_code = [
        "def function1(): pass",
        "def function2(): pass",
        "def function3(): pass",
    ] * 10  # 30 chunks

    start_time = time.time()
    embeddings = search._generate_embeddings_batch(test_code, batch_size=32)
    elapsed = time.time() - start_time

    print(f"  Generated {len([e for e in embeddings if e is not None])} embeddings")
    print(f"  Time: {elapsed:.3f}s")
    print(f"  Speed: {len(test_code)/elapsed:.0f} chunks/second")

    # Test search speed
    print("\n2. Search Speed")
    print("-" * 60)

    queries = [
        "authentication",
        "database",
        "API",
        "error handling",
        "configuration"
    ]

    search_times = []

    for query in queries:
        start_time = time.time()
        results = search.search_semantic(query, limit=5)
        elapsed = time.time() - start_time
        search_times.append(elapsed * 1000)

    avg_search_time = sum(search_times) / len(search_times)
    print(f"  Queries: {len(queries)}")
    print(f"  Average time: {avg_search_time:.2f}ms")
    print(f"  Min: {min(search_times):.2f}ms, Max: {max(search_times):.2f}ms")


def main():
    """Run all examples"""
    print("\n" + "="*80)
    print("ML-BASED SEMANTIC SEARCH - USAGE EXAMPLES")
    print("="*80)

    print(f"\nSystem Status:")
    print(f"  - Transformers available: {TRANSFORMERS_AVAILABLE}")
    print(f"  - FAISS available: {FAISS_AVAILABLE}")

    try:
        # Run examples
        example_basic_indexing()
        example_semantic_search()
        example_hybrid_search()
        example_statistics()
        example_performance_benchmark()

        print("\n" + "="*80)
        print("ALL EXAMPLES COMPLETED SUCCESSFULLY")
        print("="*80 + "\n")

    except Exception as e:
        print(f"\n[ERROR] Example failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
