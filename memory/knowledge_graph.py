#!/usr/bin/env python3
"""
Knowledge Graph & Synthesis - Build interconnected understanding from all experiences

This system creates a semantic knowledge graph that:
- Connects concepts, entities, and experiences across domains
- Discovers non-obvious relationships through graph traversal
- Synthesizes insights by analyzing connection patterns
- Generates hypotheses from unexpected connections
- Answers complex relational queries like "how is X related to Y?"
"""

import sqlite3
from pathlib import Path as FilePath
from typing import Dict, List, Optional, Set, Tuple, Any
from datetime import datetime
from collections import defaultdict, deque
from dataclasses import dataclass
import json
import math
import sys

sys.path.append(str(FilePath(__file__).parent.parent))


@dataclass
class Node:
    """Represents a concept or entity in the knowledge graph"""
    id: int
    name: str
    type: str
    properties: Dict[str, Any]
    importance: float
    created_at: str


@dataclass
class Edge:
    """Represents a relationship between two nodes"""
    id: int
    source_id: int
    target_id: int
    relationship_type: str
    strength: float
    evidence: str
    created_at: str


@dataclass
class Path:
    """Represents a path between two nodes"""
    nodes: List[Node]
    edges: List[Edge]
    total_strength: float
    path_length: int


@dataclass
class Insight:
    """Represents a synthesized insight"""
    id: int
    insight_text: str
    insight_type: str
    supporting_nodes: List[int]
    supporting_edges: List[int]
    confidence: float
    created_at: str


class RelationshipType:
    """Standard relationship types for the knowledge graph"""

    # Hierarchical relationships
    IS_A = "is_a"                      # Category/type relationship
    PART_OF = "part_of"                # Composition relationship
    HAS_PROPERTY = "has_property"      # Attribute relationship

    # Causal relationships
    CAUSES = "causes"                  # Direct causation
    ENABLES = "enables"                # Enabling relationship
    PREVENTS = "prevents"              # Prevention relationship
    INFLUENCES = "influences"          # Indirect influence

    # Temporal relationships
    PRECEDES = "precedes"              # Temporal ordering
    FOLLOWS = "follows"                # Temporal ordering
    CO_OCCURS_WITH = "co_occurs_with"  # Simultaneous occurrence

    # Similarity relationships
    SIMILAR_TO = "similar_to"          # Conceptual similarity
    OPPOSITE_OF = "opposite_of"        # Conceptual opposition
    RELATED_TO = "related_to"          # General relatedness

    # Functional relationships
    USES = "uses"                      # Usage relationship
    DEPENDS_ON = "depends_on"          # Dependency relationship
    SUPPORTS = "supports"              # Support relationship
    CONFLICTS_WITH = "conflicts_with"  # Conflict relationship

    # Contextual relationships
    MENTIONED_WITH = "mentioned_with"  # Co-mention relationship
    LEARNED_FROM = "learned_from"      # Learning relationship
    APPLIED_TO = "applied_to"          # Application relationship

    # Meta relationships
    IMPLIES = "implies"                # Logical implication
    CONTRADICTS = "contradicts"        # Logical contradiction
    EXEMPLIFIES = "exemplifies"        # Example relationship


class KnowledgeGraph:
    """
    Knowledge Graph & Synthesis System

    Builds an interconnected graph from all experiences and enables:
    - Semantic concept connections
    - Multi-hop relationship discovery
    - Cross-domain insight synthesis
    - Hypothesis generation
    - Complex relational queries
    """

    def __init__(self, db_path: str = None):
        workspace = FilePath(__file__).parent.parent
        if db_path is None:
            db_path = str(workspace / "knowledge_graph.db")

        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

        # Cache for graph traversal optimization
        self._adjacency_cache = {}
        self._cache_valid = False

    def _init_db(self):
        """Initialize database schema"""
        cursor = self.conn.cursor()

        # Nodes table - concepts, entities, experiences
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                type TEXT NOT NULL,
                properties TEXT,
                importance REAL DEFAULT 0.5,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Edges table - relationships between nodes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                target_id INTEGER NOT NULL,
                relationship_type TEXT NOT NULL,
                strength REAL DEFAULT 0.5,
                evidence TEXT,
                bidirectional INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_id) REFERENCES nodes (id),
                FOREIGN KEY (target_id) REFERENCES nodes (id),
                UNIQUE(source_id, target_id, relationship_type)
            )
        ''')

        # Insights table - synthesized knowledge
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                insight_text TEXT NOT NULL,
                insight_type TEXT NOT NULL,
                supporting_nodes TEXT,
                supporting_edges TEXT,
                confidence REAL DEFAULT 0.5,
                validated INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Hypotheses table - generated hypotheses from connections
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS hypotheses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hypothesis_text TEXT NOT NULL,
                basis_path TEXT,
                confidence REAL DEFAULT 0.3,
                tested INTEGER DEFAULT 0,
                result TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Clusters table - groups of related nodes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clusters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                node_ids TEXT,
                cohesion REAL DEFAULT 0.5,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_nodes_name ON nodes(name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_edges_type ON edges(relationship_type)')

        self.conn.commit()

    def add_node(self, name: str, node_type: str, properties: Dict[str, Any] = None,
                 importance: float = 0.5) -> int:
        """
        Add a node to the knowledge graph

        Args:
            name: Unique name/identifier for the node
            node_type: Type of node (concept, entity, experience, skill, etc.)
            properties: Additional properties as key-value pairs
            importance: Importance score (0-1)

        Returns:
            Node ID
        """
        cursor = self.conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO nodes (name, type, properties, importance)
                VALUES (?, ?, ?, ?)
            ''', (name, node_type, json.dumps(properties or {}), importance))
            self.conn.commit()
            self._cache_valid = False
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            # Node already exists, update it
            cursor.execute('''
                UPDATE nodes
                SET type = ?, properties = ?, importance = ?, updated_at = CURRENT_TIMESTAMP
                WHERE name = ?
            ''', (node_type, json.dumps(properties or {}), importance, name))
            self.conn.commit()

            cursor.execute('SELECT id FROM nodes WHERE name = ?', (name,))
            return cursor.fetchone()[0]

    def get_node(self, node_id: int = None, name: str = None) -> Optional[Node]:
        """Get a node by ID or name"""
        cursor = self.conn.cursor()

        if node_id:
            cursor.execute('SELECT * FROM nodes WHERE id = ?', (node_id,))
        elif name:
            cursor.execute('SELECT * FROM nodes WHERE name = ?', (name,))
        else:
            return None

        row = cursor.fetchone()
        if row:
            return Node(
                id=row['id'],
                name=row['name'],
                type=row['type'],
                properties=json.loads(row['properties']),
                importance=row['importance'],
                created_at=row['created_at']
            )
        return None

    def connect_nodes(self, source: int, target: int, relationship_type: str,
                     strength: float = 0.5, evidence: str = None,
                     bidirectional: bool = False) -> int:
        """
        Create a relationship between two nodes

        Args:
            source: Source node ID
            target: Target node ID
            relationship_type: Type of relationship (use RelationshipType constants)
            strength: Relationship strength (0-1)
            evidence: Evidence supporting this relationship
            bidirectional: Whether relationship goes both ways

        Returns:
            Edge ID
        """
        cursor = self.conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO edges (source_id, target_id, relationship_type, strength, evidence, bidirectional)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (source, target, relationship_type, strength, evidence, 1 if bidirectional else 0))
            self.conn.commit()
            self._cache_valid = False
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            # Edge already exists, update it
            cursor.execute('''
                UPDATE edges
                SET strength = ?, evidence = ?, bidirectional = ?, updated_at = CURRENT_TIMESTAMP
                WHERE source_id = ? AND target_id = ? AND relationship_type = ?
            ''', (strength, evidence, 1 if bidirectional else 0, source, target, relationship_type))
            self.conn.commit()

            cursor.execute('''
                SELECT id FROM edges
                WHERE source_id = ? AND target_id = ? AND relationship_type = ?
            ''', (source, target, relationship_type))
            return cursor.fetchone()[0]

    def get_neighbors(self, node_id: int, relationship_type: str = None,
                     direction: str = 'outgoing') -> List[Tuple[Node, Edge]]:
        """
        Get neighboring nodes and their connecting edges

        Args:
            node_id: Node to get neighbors for
            relationship_type: Filter by relationship type
            direction: 'outgoing', 'incoming', or 'both'

        Returns:
            List of (node, edge) tuples
        """
        cursor = self.conn.cursor()
        neighbors = []

        # Outgoing edges
        if direction in ['outgoing', 'both']:
            query = '''
                SELECT
                    n.id as n_id, n.name as n_name, n.type as n_type,
                    n.properties as n_properties, n.importance as n_importance,
                    n.created_at as n_created_at,
                    e.id as e_id, e.source_id, e.target_id,
                    e.relationship_type, e.strength, e.evidence,
                    e.created_at as e_created_at
                FROM nodes n
                JOIN edges e ON n.id = e.target_id
                WHERE e.source_id = ?
            '''
            params = [node_id]

            if relationship_type:
                query += ' AND e.relationship_type = ?'
                params.append(relationship_type)

            cursor.execute(query, params)

            for row in cursor.fetchall():
                node = Node(
                    id=row['n_id'],
                    name=row['n_name'],
                    type=row['n_type'],
                    properties=json.loads(row['n_properties']),
                    importance=row['n_importance'],
                    created_at=row['n_created_at']
                )
                edge = Edge(
                    id=row['e_id'],
                    source_id=row['source_id'],
                    target_id=row['target_id'],
                    relationship_type=row['relationship_type'],
                    strength=row['strength'],
                    evidence=row['evidence'],
                    created_at=row['e_created_at']
                )
                neighbors.append((node, edge))

        # Incoming edges (or bidirectional)
        if direction in ['incoming', 'both']:
            query = '''
                SELECT
                    n.id as n_id, n.name as n_name, n.type as n_type,
                    n.properties as n_properties, n.importance as n_importance,
                    n.created_at as n_created_at,
                    e.id as e_id, e.source_id, e.target_id,
                    e.relationship_type, e.strength, e.evidence,
                    e.created_at as e_created_at
                FROM nodes n
                JOIN edges e ON n.id = e.source_id
                WHERE e.target_id = ?
            '''
            params = [node_id]

            if relationship_type:
                query += ' AND e.relationship_type = ?'
                params.append(relationship_type)

            cursor.execute(query, params)

            for row in cursor.fetchall():
                node = Node(
                    id=row['n_id'],
                    name=row['n_name'],
                    type=row['n_type'],
                    properties=json.loads(row['n_properties']),
                    importance=row['n_importance'],
                    created_at=row['n_created_at']
                )
                edge = Edge(
                    id=row['e_id'],
                    source_id=row['source_id'],
                    target_id=row['target_id'],
                    relationship_type=row['relationship_type'],
                    strength=row['strength'],
                    evidence=row['evidence'],
                    created_at=row['e_created_at']
                )
                neighbors.append((node, edge))

        return neighbors

    def find_path(self, source_id: int, target_id: int, max_depth: int = 5,
                  min_strength: float = 0.3) -> Optional[Path]:
        """
        Find shortest path between two nodes using BFS

        Args:
            source_id: Starting node
            target_id: Destination node
            max_depth: Maximum path length
            min_strength: Minimum edge strength to consider

        Returns:
            Path object or None if no path found
        """
        if source_id == target_id:
            node = self.get_node(source_id)
            return Path(nodes=[node], edges=[], total_strength=1.0, path_length=0)

        # BFS with path tracking
        queue = deque([(source_id, [source_id], [], 1.0)])
        visited = {source_id}

        while queue:
            current_id, path_nodes, path_edges, cumulative_strength = queue.popleft()

            if len(path_nodes) > max_depth:
                continue

            # Get neighbors
            neighbors = self.get_neighbors(current_id, direction='both')

            for neighbor_node, edge in neighbors:
                if edge.strength < min_strength:
                    continue

                if neighbor_node.id == target_id:
                    # Found path!
                    final_nodes = [self.get_node(nid) for nid in path_nodes] + [neighbor_node]
                    final_edges = path_edges + [edge]
                    final_strength = cumulative_strength * edge.strength

                    return Path(
                        nodes=final_nodes,
                        edges=final_edges,
                        total_strength=final_strength,
                        path_length=len(final_edges)
                    )

                if neighbor_node.id not in visited:
                    visited.add(neighbor_node.id)
                    new_strength = cumulative_strength * edge.strength
                    queue.append((
                        neighbor_node.id,
                        path_nodes + [neighbor_node.id],
                        path_edges + [edge],
                        new_strength
                    ))

        return None

    def find_all_paths(self, source_id: int, target_id: int, max_depth: int = 4,
                      min_strength: float = 0.3, max_paths: int = 10) -> List[Path]:
        """
        Find multiple paths between two nodes (depth-first search)

        Returns:
            List of Path objects, sorted by strength
        """
        paths = []

        def dfs(current_id: int, target_id: int, visited: Set[int],
                path_nodes: List[int], path_edges: List[Edge], cumulative_strength: float):

            if len(paths) >= max_paths:
                return

            if len(path_nodes) > max_depth:
                return

            if current_id == target_id:
                # Found a path
                nodes = [self.get_node(nid) for nid in path_nodes]
                paths.append(Path(
                    nodes=nodes,
                    edges=path_edges[:],
                    total_strength=cumulative_strength,
                    path_length=len(path_edges)
                ))
                return

            neighbors = self.get_neighbors(current_id, direction='both')

            for neighbor_node, edge in neighbors:
                if edge.strength < min_strength:
                    continue

                if neighbor_node.id not in visited:
                    visited.add(neighbor_node.id)
                    dfs(
                        neighbor_node.id,
                        target_id,
                        visited,
                        path_nodes + [neighbor_node.id],
                        path_edges + [edge],
                        cumulative_strength * edge.strength
                    )
                    visited.remove(neighbor_node.id)

        visited = {source_id}
        dfs(source_id, target_id, visited, [source_id], [], 1.0)

        # Sort by strength and return
        paths.sort(key=lambda p: p.total_strength, reverse=True)
        return paths

    def query_relationships(self, node_id: int, relationship_type: str = None,
                          min_strength: float = 0.0) -> List[Dict]:
        """
        Query all relationships for a node

        Returns:
            List of relationship dictionaries with node and edge info
        """
        neighbors = self.get_neighbors(node_id, relationship_type, direction='both')

        relationships = []
        for node, edge in neighbors:
            if edge.strength >= min_strength:
                relationships.append({
                    'node': {
                        'id': node.id,
                        'name': node.name,
                        'type': node.type,
                        'importance': node.importance
                    },
                    'relationship': {
                        'type': edge.relationship_type,
                        'strength': edge.strength,
                        'evidence': edge.evidence,
                        'direction': 'outgoing' if edge.source_id == node_id else 'incoming'
                    }
                })

        return relationships

    def discover_connections(self, node_id: int, max_hops: int = 3,
                           min_path_strength: float = 0.2) -> List[Dict]:
        """
        Discover non-obvious connections from a node

        Finds nodes within max_hops that aren't directly connected,
        revealing hidden relationships.

        Returns:
            List of discovered connections with paths
        """
        discovered = []
        direct_neighbors = {n.id for n, _ in self.get_neighbors(node_id, direction='both')}
        direct_neighbors.add(node_id)

        # BFS to find reachable nodes
        queue = deque([(node_id, 0)])
        visited = {node_id}
        reachable = {}  # node_id -> distance

        while queue:
            current_id, distance = queue.popleft()

            if distance >= max_hops:
                continue

            neighbors = self.get_neighbors(current_id, direction='both')

            for neighbor_node, edge in neighbors:
                if neighbor_node.id not in visited:
                    visited.add(neighbor_node.id)
                    new_distance = distance + 1
                    reachable[neighbor_node.id] = new_distance
                    queue.append((neighbor_node.id, new_distance))

        # Find paths to non-direct neighbors
        for target_id, distance in reachable.items():
            if target_id not in direct_neighbors and distance > 1:
                path = self.find_path(node_id, target_id, max_depth=max_hops,
                                    min_strength=min_path_strength)

                if path and path.total_strength >= min_path_strength:
                    target_node = self.get_node(target_id)
                    discovered.append({
                        'target': {
                            'id': target_node.id,
                            'name': target_node.name,
                            'type': target_node.type
                        },
                        'distance': distance,
                        'path_strength': path.total_strength,
                        'path': [n.name for n in path.nodes],
                        'relationships': [e.relationship_type for e in path.edges]
                    })

        # Sort by strength and distance
        discovered.sort(key=lambda x: (x['path_strength'], -x['distance']), reverse=True)
        return discovered

    def synthesize_insight(self, node_ids: List[int], insight_text: str,
                         insight_type: str = 'pattern', confidence: float = 0.5) -> int:
        """
        Record a synthesized insight from multiple nodes/edges

        Args:
            node_ids: Nodes supporting this insight
            insight_text: The insight itself
            insight_type: Type (pattern, connection, hypothesis, etc.)
            confidence: Confidence in this insight

        Returns:
            Insight ID
        """
        cursor = self.conn.cursor()

        # Find edges between these nodes
        edge_ids = []
        for i, source in enumerate(node_ids):
            for target in node_ids[i+1:]:
                cursor.execute('''
                    SELECT id FROM edges
                    WHERE (source_id = ? AND target_id = ?)
                       OR (target_id = ? AND source_id = ? AND bidirectional = 1)
                ''', (source, target, source, target))

                edge = cursor.fetchone()
                if edge:
                    edge_ids.append(edge['id'])

        cursor.execute('''
            INSERT INTO insights (insight_text, insight_type, supporting_nodes,
                                supporting_edges, confidence)
            VALUES (?, ?, ?, ?, ?)
        ''', (insight_text, insight_type, json.dumps(node_ids),
              json.dumps(edge_ids), confidence))

        self.conn.commit()
        return cursor.lastrowid

    def generate_hypothesis(self, source_id: int, target_id: int,
                          min_confidence: float = 0.3) -> Optional[Dict]:
        """
        Generate a hypothesis about relationship between two nodes

        Uses path analysis to infer potential relationships
        """
        paths = self.find_all_paths(source_id, target_id, max_depth=4,
                                   min_strength=0.2, max_paths=5)

        if not paths:
            return None

        source_node = self.get_node(source_id)
        target_node = self.get_node(target_id)

        # Analyze paths to generate hypothesis
        relationship_types = defaultdict(float)
        total_strength = 0

        for path in paths:
            for edge in path.edges:
                relationship_types[edge.relationship_type] += edge.strength
                total_strength += path.total_strength

        # Most common relationship type
        likely_relationship = max(relationship_types.items(), key=lambda x: x[1])[0]
        confidence = min(total_strength / len(paths), 1.0)

        if confidence < min_confidence:
            return None

        hypothesis_text = (
            f"{source_node.name} likely has a '{likely_relationship}' relationship "
            f"with {target_node.name}"
        )

        # Store hypothesis
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO hypotheses (hypothesis_text, basis_path, confidence)
            VALUES (?, ?, ?)
        ''', (hypothesis_text, json.dumps([p.path_length for p in paths]), confidence))
        self.conn.commit()

        return {
            'hypothesis': hypothesis_text,
            'confidence': confidence,
            'relationship_type': likely_relationship,
            'supporting_paths': len(paths),
            'paths': [[n.name for n in p.nodes] for p in paths[:3]]
        }

    def get_graph_statistics(self) -> Dict:
        """Get statistics about the knowledge graph"""
        cursor = self.conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM nodes')
        total_nodes = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM edges')
        total_edges = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(DISTINCT type) FROM nodes')
        unique_types = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(DISTINCT relationship_type) FROM edges')
        unique_relationships = cursor.fetchone()[0]

        cursor.execute('SELECT AVG(importance) FROM nodes')
        avg_importance = cursor.fetchone()[0] or 0

        cursor.execute('SELECT AVG(strength) FROM edges')
        avg_edge_strength = cursor.fetchone()[0] or 0

        # Calculate graph density
        max_possible_edges = total_nodes * (total_nodes - 1)
        density = total_edges / max_possible_edges if max_possible_edges > 0 else 0

        cursor.execute('SELECT COUNT(*) FROM insights')
        total_insights = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM hypotheses')
        total_hypotheses = cursor.fetchone()[0]

        return {
            'nodes': total_nodes,
            'edges': total_edges,
            'unique_node_types': unique_types,
            'unique_relationship_types': unique_relationships,
            'graph_density': density,
            'average_node_importance': avg_importance,
            'average_edge_strength': avg_edge_strength,
            'insights_generated': total_insights,
            'hypotheses_generated': total_hypotheses
        }

    def get_most_connected_nodes(self, limit: int = 10) -> List[Dict]:
        """Get nodes with most connections (hub nodes)"""
        cursor = self.conn.cursor()

        cursor.execute('''
            SELECT n.id, n.name, n.type, n.importance,
                   COUNT(DISTINCT e1.id) + COUNT(DISTINCT e2.id) as connection_count
            FROM nodes n
            LEFT JOIN edges e1 ON n.id = e1.source_id
            LEFT JOIN edges e2 ON n.id = e2.target_id
            GROUP BY n.id
            ORDER BY connection_count DESC
            LIMIT ?
        ''', (limit,))

        results = []
        for row in cursor.fetchall():
            results.append({
                'id': row['id'],
                'name': row['name'],
                'type': row['type'],
                'importance': row['importance'],
                'connections': row['connection_count']
            })

        return results

    def find_clusters(self, min_size: int = 3, max_distance: float = 2.5) -> List[Dict]:
        """
        Identify clusters of highly connected nodes

        Uses a simple algorithm to find groups of nodes with strong interconnections
        """
        cursor = self.conn.cursor()
        cursor.execute('SELECT id FROM nodes')
        all_node_ids = [row['id'] for row in cursor.fetchall()]

        clusters = []
        assigned = set()

        for seed_id in all_node_ids:
            if seed_id in assigned:
                continue

            # Build cluster from seed
            cluster_nodes = {seed_id}
            queue = deque([seed_id])

            while queue:
                current_id = queue.popleft()
                neighbors = self.get_neighbors(current_id, direction='both')

                for neighbor_node, edge in neighbors:
                    if neighbor_node.id not in cluster_nodes and edge.strength > 0.5:
                        cluster_nodes.add(neighbor_node.id)
                        queue.append(neighbor_node.id)

                        if len(cluster_nodes) > 20:  # Limit cluster size
                            break

            if len(cluster_nodes) >= min_size:
                # Calculate cluster cohesion
                internal_edges = 0
                total_strength = 0

                for node_id in cluster_nodes:
                    neighbors = self.get_neighbors(node_id, direction='both')
                    for neighbor_node, edge in neighbors:
                        if neighbor_node.id in cluster_nodes:
                            internal_edges += 1
                            total_strength += edge.strength

                cohesion = total_strength / internal_edges if internal_edges > 0 else 0

                clusters.append({
                    'size': len(cluster_nodes),
                    'node_ids': list(cluster_nodes),
                    'cohesion': cohesion
                })

                assigned.update(cluster_nodes)

        clusters.sort(key=lambda c: (c['size'], c['cohesion']), reverse=True)
        return clusters

    def export_graph(self, format: str = 'json') -> str:
        """
        Export the knowledge graph

        Args:
            format: 'json' or 'graphml'

        Returns:
            Serialized graph data
        """
        cursor = self.conn.cursor()

        cursor.execute('SELECT * FROM nodes')
        nodes = [dict(row) for row in cursor.fetchall()]

        cursor.execute('SELECT * FROM edges')
        edges = [dict(row) for row in cursor.fetchall()]

        if format == 'json':
            return json.dumps({
                'nodes': nodes,
                'edges': edges
            }, indent=2, default=str)

        return json.dumps({'nodes': nodes, 'edges': edges}, default=str)

    def close(self):
        """Close database connection"""
        self.conn.close()


# Helper functions for common operations

def build_concept_graph(concepts: List[str], relationships: List[Tuple[str, str, str]]) -> KnowledgeGraph:
    """
    Helper to build a knowledge graph from concepts and relationships

    Args:
        concepts: List of concept names
        relationships: List of (source_concept, relationship_type, target_concept)

    Returns:
        Populated KnowledgeGraph
    """
    kg = KnowledgeGraph()

    # Add concepts as nodes
    concept_ids = {}
    for concept in concepts:
        node_id = kg.add_node(concept, 'concept', importance=0.5)
        concept_ids[concept] = node_id

    # Add relationships
    for source, rel_type, target in relationships:
        if source in concept_ids and target in concept_ids:
            kg.connect_nodes(
                concept_ids[source],
                concept_ids[target],
                rel_type,
                strength=0.7
            )

    return kg


if __name__ == '__main__':
    print("Knowledge Graph & Synthesis System - Testing")
    print("=" * 60)

    # Initialize
    kg = KnowledgeGraph()

    # Test 1: Add nodes
    print("\n1. Adding nodes...")
    python = kg.add_node("Python", "programming_language",
                        {"paradigm": "multi-paradigm", "typing": "dynamic"},
                        importance=0.9)

    ml = kg.add_node("Machine Learning", "field",
                    {"domain": "AI", "complexity": "high"},
                    importance=0.85)

    data_science = kg.add_node("Data Science", "field",
                              {"domain": "analytics"},
                              importance=0.8)

    pandas = kg.add_node("Pandas", "library",
                        {"language": "Python"},
                        importance=0.7)

    numpy = kg.add_node("NumPy", "library",
                       {"language": "Python"},
                       importance=0.75)

    scikit = kg.add_node("Scikit-learn", "library",
                        {"domain": "ML"},
                        importance=0.8)

    print(f"Added 6 nodes: Python, ML, Data Science, Pandas, NumPy, Scikit-learn")

    # Test 2: Connect nodes
    print("\n2. Creating relationships...")
    kg.connect_nodes(pandas, python, RelationshipType.PART_OF, 0.9, "Pandas is a Python library")
    kg.connect_nodes(numpy, python, RelationshipType.PART_OF, 0.9, "NumPy is a Python library")
    kg.connect_nodes(scikit, python, RelationshipType.PART_OF, 0.9, "Scikit-learn is a Python library")

    kg.connect_nodes(data_science, python, RelationshipType.USES, 0.85,
                    "Data science uses Python as primary language")
    kg.connect_nodes(ml, python, RelationshipType.USES, 0.9,
                    "Machine learning uses Python widely")

    kg.connect_nodes(pandas, data_science, RelationshipType.ENABLES, 0.8,
                    "Pandas enables data science workflows")
    kg.connect_nodes(scikit, ml, RelationshipType.ENABLES, 0.9,
                    "Scikit-learn enables ML")

    kg.connect_nodes(ml, data_science, RelationshipType.RELATED_TO, 0.7,
                    bidirectional=True)

    kg.connect_nodes(pandas, numpy, RelationshipType.DEPENDS_ON, 0.95,
                    "Pandas depends on NumPy")
    kg.connect_nodes(scikit, numpy, RelationshipType.DEPENDS_ON, 0.9,
                    "Scikit-learn depends on NumPy")

    print("Created 10 relationships")

    # Test 3: Query relationships
    print("\n3. Querying relationships for Python...")
    relationships = kg.query_relationships(python)
    print(f"Found {len(relationships)} relationships:")
    for rel in relationships[:5]:
        print(f"  - {rel['node']['name']} ({rel['relationship']['type']}, "
              f"strength: {rel['relationship']['strength']:.2f})")

    # Test 4: Find path
    print("\n4. Finding path from Pandas to Machine Learning...")
    path = kg.find_path(pandas, ml)
    if path:
        print(f"Path found (length {path.path_length}, strength {path.total_strength:.3f}):")
        for i, node in enumerate(path.nodes):
            print(f"  {node.name}", end='')
            if i < len(path.edges):
                print(f" --[{path.edges[i].relationship_type}]--> ", end='')
        print()

    # Test 5: Discover connections
    print("\n5. Discovering non-obvious connections from NumPy...")
    connections = kg.discover_connections(numpy, max_hops=3)
    print(f"Found {len(connections)} indirect connections:")
    for conn in connections[:3]:
        print(f"  - {conn['target']['name']} (distance: {conn['distance']}, "
              f"strength: {conn['path_strength']:.3f})")
        print(f"    Path: {' -> '.join(conn['path'])}")

    # Test 6: Generate hypothesis
    print("\n6. Generating hypothesis: NumPy -> Data Science...")
    hypothesis = kg.generate_hypothesis(numpy, data_science)
    if hypothesis:
        print(f"Hypothesis: {hypothesis['hypothesis']}")
        print(f"Confidence: {hypothesis['confidence']:.3f}")
        print(f"Based on {hypothesis['supporting_paths']} paths")

    # Test 7: Synthesize insight
    print("\n7. Synthesizing insight from Python ecosystem...")
    insight_id = kg.synthesize_insight(
        [python, pandas, numpy, scikit],
        "Python's data science ecosystem is built on NumPy's array operations, "
        "with Pandas for data manipulation and Scikit-learn for ML algorithms",
        insight_type="ecosystem_pattern",
        confidence=0.85
    )
    print(f"Created insight #{insight_id}")

    # Test 8: Graph statistics
    print("\n8. Graph statistics:")
    stats = kg.get_graph_statistics()
    print(f"  Nodes: {stats['nodes']}")
    print(f"  Edges: {stats['edges']}")
    print(f"  Node types: {stats['unique_node_types']}")
    print(f"  Relationship types: {stats['unique_relationship_types']}")
    print(f"  Graph density: {stats['graph_density']:.4f}")
    print(f"  Avg edge strength: {stats['average_edge_strength']:.3f}")
    print(f"  Insights: {stats['insights_generated']}")
    print(f"  Hypotheses: {stats['hypotheses_generated']}")

    # Test 9: Most connected nodes
    print("\n9. Most connected nodes:")
    hubs = kg.get_most_connected_nodes(limit=5)
    for hub in hubs:
        print(f"  {hub['name']}: {hub['connections']} connections "
              f"(importance: {hub['importance']:.2f})")

    # Test 10: Find all paths
    print("\n10. Finding all paths from Scikit-learn to Data Science...")
    all_paths = kg.find_all_paths(scikit, data_science, max_depth=4, max_paths=5)
    print(f"Found {len(all_paths)} paths:")
    for i, path in enumerate(all_paths, 1):
        print(f"  Path {i} (strength {path.total_strength:.3f}):")
        print(f"    {' -> '.join([n.name for n in path.nodes])}")

    # Test 11: Advanced - build larger graph
    print("\n11. Building expanded graph with more concepts...")

    # Add more nodes
    tensorflow = kg.add_node("TensorFlow", "library", importance=0.85)
    pytorch = kg.add_node("PyTorch", "library", importance=0.85)
    deep_learning = kg.add_node("Deep Learning", "field", importance=0.9)
    neural_nets = kg.add_node("Neural Networks", "concept", importance=0.8)

    # Add relationships
    kg.connect_nodes(tensorflow, python, RelationshipType.PART_OF, 0.9)
    kg.connect_nodes(pytorch, python, RelationshipType.PART_OF, 0.9)
    kg.connect_nodes(deep_learning, ml, RelationshipType.IS_A, 0.95)
    kg.connect_nodes(neural_nets, deep_learning, RelationshipType.PART_OF, 0.9)
    kg.connect_nodes(tensorflow, deep_learning, RelationshipType.ENABLES, 0.9)
    kg.connect_nodes(pytorch, deep_learning, RelationshipType.ENABLES, 0.9)
    kg.connect_nodes(tensorflow, pytorch, RelationshipType.SIMILAR_TO, 0.8, bidirectional=True)

    print("Added 4 more nodes and 7 relationships")

    # Test 12: Complex path finding
    print("\n12. Finding path from Pandas to Deep Learning...")
    path = kg.find_path(pandas, deep_learning, max_depth=5)
    if path:
        print(f"Found path (length {path.path_length}):")
        print(f"  {' -> '.join([n.name for n in path.nodes])}")

    # Test 13: Cluster detection
    print("\n13. Detecting clusters in the graph...")
    clusters = kg.find_clusters(min_size=2)
    print(f"Found {len(clusters)} clusters:")
    for i, cluster in enumerate(clusters[:3], 1):
        print(f"  Cluster {i}: {cluster['size']} nodes, cohesion {cluster['cohesion']:.3f}")

    # Final statistics
    print("\n" + "=" * 60)
    print("Final Graph Statistics:")
    final_stats = kg.get_graph_statistics()
    print(json.dumps(final_stats, indent=2))

    print("\nKnowledge Graph & Synthesis System - All tests completed!")
    print("=" * 60)

    kg.close()
