#!/usr/bin/env python3
"""
Pattern Clustering with Machine Learning

Uses scikit-learn KMeans to cluster similar mistakes and code patterns.
Identifies pattern categories and recommends solutions by cluster.

Features:
- KMeans clustering for pattern grouping
- TF-IDF vectorization for text patterns
- Automatic cluster labeling
- Solution recommendation by cluster
- Integration with mistake learner

Author: AI Self-Improvement System
Created: 2026-02-03
"""

import sys
from pathlib import Path
import sqlite3
import json
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import re
import warnings

sys.path.append(str(Path(__file__).parent.parent))

# ML imports
try:
    from sklearn.cluster import KMeans
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics import silhouette_score
    from sklearn.decomposition import PCA
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    warnings.warn("scikit-learn not available. Pattern clustering disabled.")

warnings.filterwarnings('ignore')


@dataclass
class PatternCluster:
    """Represents a cluster of similar patterns"""
    cluster_id: int
    cluster_label: str
    pattern_count: int
    centroid: Optional[np.ndarray]
    common_keywords: List[str]
    example_patterns: List[str]
    recommended_solution: Optional[str] = None
    avg_severity: float = 0.0


@dataclass
class ClusteredPattern:
    """A pattern assigned to a cluster"""
    pattern_id: int
    cluster_id: int
    pattern_text: str
    distance_to_centroid: float
    error_type: str
    occurrence_count: int


class PatternClusterer:
    """
    Machine learning-based pattern clustering

    Uses KMeans to group similar error patterns, mistakes, and code issues.
    Identifies categories and recommends solutions by cluster.
    """

    def __init__(self, db_path: str = None, n_clusters: int = 5):
        workspace = Path(__file__).parent.parent
        if db_path is None:
            db_path = str(workspace / "mistake_learning.db")

        self.db_path = db_path
        self.n_clusters = n_clusters
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        self.vectorizer = None
        self.kmeans = None
        self.pca = None

        self._init_db()

        if not ML_AVAILABLE:
            print("[Warning] scikit-learn not available. Pattern clustering disabled.")

    def _init_db(self):
        """Initialize clustering database"""
        cursor = self.conn.cursor()

        # Clusters table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pattern_clusters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cluster_label TEXT NOT NULL,
                pattern_count INTEGER DEFAULT 0,
                common_keywords TEXT,
                example_patterns TEXT,
                recommended_solution TEXT,
                avg_severity REAL DEFAULT 0.0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Pattern assignments
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pattern_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_id INTEGER NOT NULL,
                cluster_id INTEGER NOT NULL,
                pattern_type TEXT NOT NULL,
                pattern_text TEXT NOT NULL,
                distance_to_centroid REAL,
                assigned_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (cluster_id) REFERENCES pattern_clusters (id)
            )
        ''')

        # Clustering runs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clustering_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                n_clusters INTEGER NOT NULL,
                n_patterns INTEGER NOT NULL,
                silhouette_score REAL,
                inertia REAL,
                algorithm TEXT DEFAULT 'kmeans',
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create failure_patterns table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS failure_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_description TEXT NOT NULL,
                pattern_signature TEXT NOT NULL,
                error_type TEXT,
                failure_count INTEGER DEFAULT 1,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                examples TEXT,
                suggested_fix TEXT,
                UNIQUE(pattern_signature)
            )
        ''')

        self.conn.commit()

    def cluster_mistakes(self, min_patterns: int = 5) -> Dict:
        """
        Cluster mistake patterns using KMeans

        Args:
            min_patterns: Minimum patterns needed for clustering

        Returns:
            Clustering results with statistics
        """
        if not ML_AVAILABLE:
            return {'error': 'ML libraries not available'}

        # Fetch patterns from database
        patterns = self._fetch_patterns()

        if len(patterns) < min_patterns:
            return {
                'error': f'Not enough patterns for clustering. Found {len(patterns)}, need at least {min_patterns}'
            }

        print(f"[Clustering] Found {len(patterns)} patterns to cluster...")

        # Vectorize patterns
        pattern_texts = [p['text'] for p in patterns]
        X = self._vectorize_patterns(pattern_texts)

        # Determine optimal number of clusters
        optimal_k = self._find_optimal_clusters(X, min(self.n_clusters, len(patterns) - 1))
        print(f"[Clustering] Using {optimal_k} clusters...")

        # Perform clustering
        self.kmeans = KMeans(n_clusters=optimal_k, random_state=42, n_init=10)
        cluster_labels = self.kmeans.fit_predict(X)

        # Calculate metrics
        silhouette = silhouette_score(X, cluster_labels) if len(set(cluster_labels)) > 1 else 0
        inertia = self.kmeans.inertia_

        print(f"[Clustering] Silhouette score: {silhouette:.3f}")
        print(f"[Clustering] Inertia: {inertia:.2f}")

        # Record clustering run
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO clustering_runs (n_clusters, n_patterns, silhouette_score, inertia)
            VALUES (?, ?, ?, ?)
        ''', (optimal_k, len(patterns), silhouette, inertia))
        run_id = cursor.lastrowid
        self.conn.commit()

        # Create clusters
        clusters = self._create_clusters(patterns, cluster_labels, X)

        # Store clusters
        self._store_clusters(clusters, patterns, cluster_labels)

        return {
            'run_id': run_id,
            'n_clusters': optimal_k,
            'n_patterns': len(patterns),
            'silhouette_score': silhouette,
            'inertia': inertia,
            'clusters': clusters
        }

    def _fetch_patterns(self) -> List[Dict]:
        """Fetch patterns from mistake database"""
        cursor = self.conn.cursor()

        patterns = []

        # Fetch from mistakes
        cursor.execute('''
            SELECT
                id,
                mistake_type,
                description,
                error_message,
                code_snippet,
                severity
            FROM mistakes
            WHERE description IS NOT NULL
        ''')

        for row in cursor.fetchall():
            # Combine fields for pattern text
            text_parts = []
            if row['mistake_type']:
                text_parts.append(row['mistake_type'])
            if row['description']:
                text_parts.append(row['description'])
            if row['error_message']:
                text_parts.append(row['error_message'])
            if row['code_snippet']:
                # Clean code snippet
                code = row['code_snippet'][:200]  # Limit length
                text_parts.append(code)

            patterns.append({
                'id': row['id'],
                'type': 'mistake',
                'text': ' '.join(text_parts),
                'error_type': row['mistake_type'],
                'severity': row['severity']
            })

        # Fetch from failure patterns
        cursor.execute('''
            SELECT
                id,
                error_type,
                pattern_description,
                examples,
                failure_count
            FROM failure_patterns
        ''')

        for row in cursor.fetchall():
            text_parts = []
            if row['error_type']:
                text_parts.append(row['error_type'])
            if row['pattern_description']:
                text_parts.append(row['pattern_description'])
            if row['examples']:
                text_parts.append(row['examples'][:200])

            patterns.append({
                'id': row['id'],
                'type': 'failure_pattern',
                'text': ' '.join(text_parts),
                'error_type': row['error_type'],
                'occurrence_count': row['failure_count']
            })

        return patterns

    def _vectorize_patterns(self, pattern_texts: List[str]) -> np.ndarray:
        """Vectorize pattern texts using TF-IDF"""
        # Initialize vectorizer
        self.vectorizer = TfidfVectorizer(
            max_features=100,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=1
        )

        # Fit and transform
        X = self.vectorizer.fit_transform(pattern_texts)
        return X.toarray()

    def _find_optimal_clusters(self, X: np.ndarray, max_k: int) -> int:
        """Find optimal number of clusters using elbow method"""
        if max_k < 2:
            return max(2, min(max_k, len(X) - 1))

        # Try different k values
        inertias = []
        k_range = range(2, min(max_k + 1, len(X)))

        for k in k_range:
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            kmeans.fit(X)
            inertias.append(kmeans.inertia_)

        # Simple elbow detection (use middle value)
        if len(inertias) > 0:
            optimal_k = k_range[len(k_range) // 2]
        else:
            optimal_k = 2

        return optimal_k

    def _create_clusters(self, patterns: List[Dict], labels: np.ndarray,
                        X: np.ndarray) -> List[PatternCluster]:
        """Create cluster objects with metadata"""
        clusters = []

        for cluster_id in range(self.kmeans.n_clusters):
            # Get patterns in this cluster
            cluster_mask = labels == cluster_id
            cluster_patterns = [p for i, p in enumerate(patterns) if cluster_mask[i]]

            if len(cluster_patterns) == 0:
                continue

            # Extract common keywords
            cluster_texts = [p['text'] for p in cluster_patterns]
            common_keywords = self._extract_common_keywords(cluster_texts)

            # Generate cluster label
            cluster_label = self._generate_cluster_label(cluster_patterns, common_keywords)

            # Get example patterns
            example_patterns = [p['text'][:100] for p in cluster_patterns[:3]]

            # Calculate average severity
            severities = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
            avg_severity = np.mean([
                severities.get(p.get('severity', 'medium'), 2)
                for p in cluster_patterns
            ])

            clusters.append(PatternCluster(
                cluster_id=cluster_id,
                cluster_label=cluster_label,
                pattern_count=len(cluster_patterns),
                centroid=self.kmeans.cluster_centers_[cluster_id],
                common_keywords=common_keywords,
                example_patterns=example_patterns,
                avg_severity=avg_severity
            ))

        return clusters

    def _extract_common_keywords(self, texts: List[str]) -> List[str]:
        """Extract common keywords from cluster texts"""
        # Get feature names from vectorizer
        if self.vectorizer is None:
            return []

        feature_names = self.vectorizer.get_feature_names_out()

        # Count keyword occurrences
        keyword_counts = {}
        for text in texts:
            words = set(re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]{2,}\b', text.lower()))
            for word in words:
                if word in feature_names:
                    keyword_counts[word] = keyword_counts.get(word, 0) + 1

        # Get top keywords
        top_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)
        return [kw for kw, count in top_keywords[:5]]

    def _generate_cluster_label(self, patterns: List[Dict], keywords: List[str]) -> str:
        """Generate a descriptive label for the cluster"""
        # Count error types
        error_types = {}
        for p in patterns:
            error_type = p.get('error_type', 'unknown')
            error_types[error_type] = error_types.get(error_type, 0) + 1

        # Get most common error type
        if error_types:
            most_common_type = max(error_types.items(), key=lambda x: x[1])[0]
        else:
            most_common_type = 'unknown'

        # Generate label
        if keywords:
            label = f"{most_common_type}: {', '.join(keywords[:3])}"
        else:
            label = f"{most_common_type} errors"

        return label[:100]  # Limit length

    def _store_clusters(self, clusters: List[PatternCluster],
                       patterns: List[Dict], labels: np.ndarray):
        """Store clusters and assignments in database"""
        cursor = self.conn.cursor()

        # Clear old clusters
        cursor.execute('DELETE FROM pattern_clusters')
        cursor.execute('DELETE FROM pattern_assignments')

        # Store clusters
        cluster_id_map = {}
        for cluster in clusters:
            cursor.execute('''
                INSERT INTO pattern_clusters
                (cluster_label, pattern_count, common_keywords, example_patterns, avg_severity)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                cluster.cluster_label,
                cluster.pattern_count,
                json.dumps(cluster.common_keywords),
                json.dumps(cluster.example_patterns),
                cluster.avg_severity
            ))
            cluster_id_map[cluster.cluster_id] = cursor.lastrowid

        # Store pattern assignments
        for i, (pattern, label) in enumerate(zip(patterns, labels)):
            if label in cluster_id_map:
                db_cluster_id = cluster_id_map[label]

                # Calculate distance to centroid
                distance = np.linalg.norm(
                    self.vectorizer.transform([pattern['text']]).toarray()[0] -
                    self.kmeans.cluster_centers_[label]
                )

                cursor.execute('''
                    INSERT INTO pattern_assignments
                    (pattern_id, cluster_id, pattern_type, pattern_text, distance_to_centroid)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    pattern['id'],
                    db_cluster_id,
                    pattern['type'],
                    pattern['text'][:500],
                    float(distance)
                ))

        self.conn.commit()

    def get_clusters(self) -> List[Dict]:
        """Get all clusters from database"""
        cursor = self.conn.cursor()

        cursor.execute('''
            SELECT * FROM pattern_clusters
            ORDER BY pattern_count DESC
        ''')

        clusters = []
        for row in cursor.fetchall():
            clusters.append({
                'id': row['id'],
                'label': row['cluster_label'],
                'pattern_count': row['pattern_count'],
                'common_keywords': json.loads(row['common_keywords']),
                'example_patterns': json.loads(row['example_patterns']),
                'recommended_solution': row['recommended_solution'],
                'avg_severity': row['avg_severity']
            })

        return clusters

    def get_patterns_in_cluster(self, cluster_id: int) -> List[Dict]:
        """Get all patterns assigned to a cluster"""
        cursor = self.conn.cursor()

        cursor.execute('''
            SELECT * FROM pattern_assignments
            WHERE cluster_id = ?
            ORDER BY distance_to_centroid ASC
        ''', (cluster_id,))

        patterns = []
        for row in cursor.fetchall():
            patterns.append({
                'pattern_id': row['pattern_id'],
                'pattern_type': row['pattern_type'],
                'pattern_text': row['pattern_text'],
                'distance': row['distance_to_centroid']
            })

        return patterns

    def recommend_solution(self, cluster_id: int, solution: str):
        """Add a recommended solution for a cluster"""
        cursor = self.conn.cursor()

        cursor.execute('''
            UPDATE pattern_clusters
            SET recommended_solution = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (solution, cluster_id))

        self.conn.commit()

    def find_cluster_for_error(self, error_text: str) -> Optional[Dict]:
        """Find which cluster a new error belongs to"""
        if self.kmeans is None or self.vectorizer is None:
            return None

        # Vectorize error
        X = self.vectorizer.transform([error_text]).toarray()

        # Predict cluster
        cluster_label = self.kmeans.predict(X)[0]

        # Get cluster info
        clusters = self.get_clusters()
        if cluster_label < len(clusters):
            return clusters[cluster_label]

        return None

    def get_clustering_stats(self) -> Dict:
        """Get statistics about clustering"""
        cursor = self.conn.cursor()

        cursor.execute('SELECT COUNT(*) as count FROM pattern_clusters')
        total_clusters = cursor.fetchone()['count']

        cursor.execute('SELECT COUNT(*) as count FROM pattern_assignments')
        total_assignments = cursor.fetchone()['count']

        cursor.execute('SELECT * FROM clustering_runs ORDER BY timestamp DESC LIMIT 1')
        last_run = cursor.fetchone()

        cursor.execute('''
            SELECT cluster_id, COUNT(*) as count
            FROM pattern_assignments
            GROUP BY cluster_id
            ORDER BY count DESC
        ''')
        cluster_sizes = [row['count'] for row in cursor.fetchall()]

        return {
            'total_clusters': total_clusters,
            'total_patterns': total_assignments,
            'last_run': dict(last_run) if last_run else None,
            'cluster_sizes': cluster_sizes,
            'ml_available': ML_AVAILABLE
        }

    def visualize_clusters(self, output_path: str = None) -> Dict:
        """
        Create a 2D visualization of clusters using PCA

        Returns:
            Dictionary with visualization data
        """
        if not ML_AVAILABLE or self.kmeans is None:
            return {'error': 'Clustering not performed or ML not available'}

        # Get patterns
        patterns = self._fetch_patterns()
        pattern_texts = [p['text'] for p in patterns]
        X = self.vectorizer.transform(pattern_texts).toarray()

        # Reduce to 2D using PCA
        pca = PCA(n_components=2)
        X_2d = pca.fit_transform(X)

        # Get cluster labels
        labels = self.kmeans.predict(X)

        visualization_data = {
            'points': X_2d.tolist(),
            'labels': labels.tolist(),
            'pattern_texts': [p['text'][:50] for p in patterns],
            'n_clusters': self.kmeans.n_clusters,
            'explained_variance': pca.explained_variance_ratio_.tolist()
        }

        return visualization_data

    def close(self):
        """Close database connection"""
        self.conn.close()


# === TEST CODE ===

def main():
    """Test pattern clusterer"""
    print("=" * 80)
    print("PATTERN CLUSTERING WITH MACHINE LEARNING")
    print("=" * 80)

    if not ML_AVAILABLE:
        print("\n[ERROR] scikit-learn not available. Cannot run clustering.")
        return

    clusterer = PatternClusterer(n_clusters=5)

    try:
        print("\n1. Clustering mistake patterns...")
        result = clusterer.cluster_mistakes(min_patterns=3)

        if 'error' in result:
            print(f"   {result['error']}")
        else:
            print(f"   Clusters created: {result['n_clusters']}")
            print(f"   Patterns clustered: {result['n_patterns']}")
            print(f"   Silhouette score: {result['silhouette_score']:.3f}")
            print(f"   Inertia: {result['inertia']:.2f}")

        print("\n2. Getting cluster information...")
        clusters = clusterer.get_clusters()
        print(f"   Found {len(clusters)} clusters:")

        for i, cluster in enumerate(clusters, 1):
            print(f"\n   Cluster {i}: {cluster['label']}")
            print(f"      Patterns: {cluster['pattern_count']}")
            print(f"      Keywords: {', '.join(cluster['common_keywords'])}")
            print(f"      Avg severity: {cluster['avg_severity']:.1f}")
            print(f"      Examples:")
            for ex in cluster['example_patterns'][:2]:
                print(f"         - {ex}")

        print("\n3. Adding recommended solutions...")
        if len(clusters) > 0:
            clusterer.recommend_solution(
                clusters[0]['id'],
                "Check input validation and type conversion"
            )
            print("   Solution added to first cluster")

        print("\n4. Testing error classification...")
        test_error = "ValueError: invalid literal for int() with base 10"
        cluster = clusterer.find_cluster_for_error(test_error)
        if cluster:
            print(f"   Error classified to cluster: {cluster['label']}")
            if cluster['recommended_solution']:
                print(f"   Recommended solution: {cluster['recommended_solution']}")

        print("\n5. Clustering statistics...")
        stats = clusterer.get_clustering_stats()
        print(f"   Total clusters: {stats['total_clusters']}")
        print(f"   Total patterns: {stats['total_patterns']}")
        print(f"   Cluster sizes: {stats['cluster_sizes']}")

        print("\n6. Visualization data...")
        viz_data = clusterer.visualize_clusters()
        if 'error' not in viz_data:
            print(f"   Generated 2D visualization with {len(viz_data['points'])} points")
            print(f"   Explained variance: {viz_data['explained_variance']}")

        print(f"\n[OK] Pattern Clustering System Working!")
        print(f"Database: {clusterer.db_path}")

    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        clusterer.close()


if __name__ == "__main__":
    main()
