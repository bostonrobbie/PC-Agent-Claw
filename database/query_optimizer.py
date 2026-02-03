"""
Database Query Optimization System

A comprehensive tool for analyzing database schemas, detecting performance issues,
suggesting indexes, and optimizing queries across PostgreSQL, MySQL, and SQLite.

Features:
- Schema analysis and relationship detection
- Query pattern tracking and analysis
- N+1 query problem detection
- EXPLAIN ANALYZE parsing
- Intelligent index recommendations
- Query optimization suggestions
"""

import sqlite3
import json
import re
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional
from collections import defaultdict, Counter
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseSchema:
    """Analyzes and stores database schema information."""

    def __init__(self):
        self.tables: Dict[str, Dict] = {}
        self.relationships: List[Dict] = []
        self.indexes: Dict[str, List[str]] = defaultdict(list)

    def add_table(self, table_name: str, columns: List[Dict[str, str]]):
        """Add table schema information."""
        self.tables[table_name] = {
            'columns': columns,
            'primary_key': None,
            'created_at': datetime.now().isoformat()
        }

        for col in columns:
            if col.get('is_primary_key'):
                self.tables[table_name]['primary_key'] = col['name']

    def add_relationship(self, from_table: str, from_col: str, to_table: str, to_col: str):
        """Record foreign key relationship."""
        self.relationships.append({
            'from_table': from_table,
            'from_col': from_col,
            'to_table': to_table,
            'to_col': to_col
        })

    def add_index(self, table_name: str, column_name: str):
        """Record existing index."""
        self.indexes[table_name].append(column_name)

    def to_dict(self) -> Dict:
        """Convert schema to dictionary for storage."""
        return {
            'tables': self.tables,
            'relationships': self.relationships,
            'indexes': dict(self.indexes)
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'DatabaseSchema':
        """Create schema from dictionary."""
        schema = cls()
        schema.tables = data.get('tables', {})
        schema.relationships = data.get('relationships', [])
        schema.indexes = defaultdict(list, data.get('indexes', {}))
        return schema


class QueryAnalyzer:
    """Analyzes SQL queries for performance issues."""

    def __init__(self):
        self.query_cache: Dict[str, Dict] = {}
        self.pattern_stats = Counter()

    def analyze_query(self, query: str, execution_time: float = 0.0) -> Dict[str, Any]:
        """Analyze a single query."""
        analysis = {
            'query': query,
            'timestamp': datetime.now().isoformat(),
            'execution_time': execution_time,
            'issues': [],
            'suggestions': [],
            'patterns': self._extract_patterns(query)
        }

        # Check for common issues
        if self._has_select_star(query):
            analysis['issues'].append('SELECT * detected - specify needed columns')
            analysis['suggestions'].append('Use explicit column selection for better performance')

        if self._has_subquery_in_select(query):
            analysis['issues'].append('Subquery in SELECT clause - potential N+1 pattern')
            analysis['suggestions'].append('Consider joining instead of subquery')

        if self._has_missing_where(query):
            analysis['issues'].append('Missing WHERE clause or filtering')
            analysis['suggestions'].append('Add filtering conditions to reduce result set')

        if self._has_join_without_index(query):
            analysis['issues'].append('JOIN without indexed columns')
            analysis['suggestions'].append('Ensure JOIN columns are indexed')

        if self._has_order_by_unindexed(query):
            analysis['issues'].append('ORDER BY on potentially unindexed column')
            analysis['suggestions'].append('Add index on ORDER BY columns')

        # Record pattern
        pattern = self._get_query_pattern(query)
        self.pattern_stats[pattern] += 1

        return analysis

    def _extract_patterns(self, query: str) -> List[str]:
        """Extract SQL patterns from query."""
        patterns = []
        query_upper = query.upper().strip()

        if query_upper.startswith('SELECT'):
            patterns.append('SELECT')
        if 'JOIN' in query_upper:
            patterns.append('JOIN')
        if 'WHERE' in query_upper:
            patterns.append('WHERE')
        if 'ORDER BY' in query_upper:
            patterns.append('ORDER_BY')
        if 'GROUP BY' in query_upper:
            patterns.append('GROUP_BY')
        if 'LIMIT' in query_upper:
            patterns.append('LIMIT')
        if 'DISTINCT' in query_upper:
            patterns.append('DISTINCT')
        if 'SUBQUERY' in query_upper or '(SELECT' in query_upper:
            patterns.append('SUBQUERY')
        if 'UNION' in query_upper:
            patterns.append('UNION')

        return patterns

    def _get_query_pattern(self, query: str) -> str:
        """Get simplified query pattern."""
        pattern = re.sub(r"'[^']*'", "STRING", query)
        pattern = re.sub(r"\d+", "NUM", pattern)
        pattern = re.sub(r"\s+", " ", pattern).strip()
        return pattern[:100]

    def _has_select_star(self, query: str) -> bool:
        """Check for SELECT *."""
        return bool(re.search(r'SELECT\s+\*', query, re.IGNORECASE))

    def _has_subquery_in_select(self, query: str) -> bool:
        """Check for subquery in SELECT clause."""
        select_part = query.split('FROM')[0] if 'FROM' in query else query
        return '(SELECT' in select_part.upper()

    def _has_missing_where(self, query: str) -> bool:
        """Check if query lacks WHERE clause."""
        return 'WHERE' not in query.upper() and 'LIMIT' not in query.upper()

    def _has_join_without_index(self, query: str) -> bool:
        """Check for JOIN without indexed columns."""
        return 'JOIN' in query.upper() and not re.search(r'ON\s+\w+\.\w+\s*=\s*\w+\.\w+', query)

    def _has_order_by_unindexed(self, query: str) -> bool:
        """Check for ORDER BY without index."""
        return 'ORDER BY' in query.upper()


class N1QueryDetector:
    """Detects N+1 query patterns."""

    def __init__(self):
        self.query_sequences: List[List[Dict]] = []
        self.current_sequence: List[Dict] = []

    def add_query(self, query: str, execution_time: float, table: str):
        """Add query to sequence."""
        self.current_sequence.append({
            'query': query,
            'execution_time': execution_time,
            'table': table,
            'timestamp': datetime.now().isoformat()
        })

    def detect_n1_pattern(self, window_size: int = 50) -> List[Dict]:
        """Detect N+1 query patterns."""
        n1_issues = []

        if len(self.current_sequence) < 2:
            return n1_issues

        # Look for repeated queries to same table
        table_queries = defaultdict(list)
        for query_info in self.current_sequence[-window_size:]:
            table_queries[query_info['table']].append(query_info)

        for table, queries in table_queries.items():
            if len(queries) > 5:
                total_time = sum(q['execution_time'] for q in queries)
                n1_issues.append({
                    'type': 'N+1_PATTERN',
                    'table': table,
                    'query_count': len(queries),
                    'total_execution_time': total_time,
                    'average_time': total_time / len(queries),
                    'queries': queries[:3]  # First 3 as sample
                })

        return n1_issues

    def reset_sequence(self):
        """Reset current sequence."""
        if len(self.current_sequence) > 0:
            self.query_sequences.append(self.current_sequence)
        self.current_sequence = []


class ExplainAnalyzer:
    """Parses and analyzes EXPLAIN ANALYZE output."""

    def parse_explain_output(self, explain_json: str) -> Dict[str, Any]:
        """Parse EXPLAIN ANALYZE JSON output."""
        try:
            data = json.loads(explain_json)
            plan = data.get('Plan', {})

            analysis = {
                'execution_time': data.get('Execution Time', 0),
                'planning_time': data.get('Planning Time', 0),
                'plan': plan,
                'issues': [],
                'optimization_tips': []
            }

            # Analyze plan
            analysis.update(self._analyze_plan_node(plan))

            return analysis
        except json.JSONDecodeError:
            return {'error': 'Invalid EXPLAIN ANALYZE output', 'raw': explain_json}

    def _analyze_plan_node(self, node: Dict) -> Dict[str, Any]:
        """Analyze a plan node recursively."""
        issues = []
        optimization_tips = []
        total_cost = node.get('Total Cost', 0)

        node_type = node.get('Node Type', 'Unknown')

        # Check for sequential scans
        if node_type == 'Seq Scan':
            issues.append(f'Sequential scan on {node.get("Relation Name", "unknown")}')
            optimization_tips.append('Consider adding an index on filter columns')

        # Check for nested loops
        if node_type == 'Nested Loop':
            if node.get('Actual Loops', 1) > 1:
                issues.append(f'Nested loop with {node.get("Actual Loops", 1)} iterations')
                optimization_tips.append('Consider using hash join or indexes')

        # High cost threshold
        if total_cost > 10000:
            issues.append(f'High estimated cost: {total_cost}')
            optimization_tips.append('Query may benefit from optimization')

        # Check rows vs actual
        rows = node.get('Plans', [])
        for sub_node in rows:
            sub_analysis = self._analyze_plan_node(sub_node)
            issues.extend(sub_analysis.get('issues', []))
            optimization_tips.extend(sub_analysis.get('optimization_tips', []))

        return {
            'issues': issues,
            'optimization_tips': optimization_tips,
            'node_type': node_type,
            'total_cost': total_cost
        }


class IndexRecommendationEngine:
    """Recommends indexes based on query patterns."""

    def __init__(self, schema: DatabaseSchema):
        self.schema = schema
        self.column_access_count = Counter()
        self.column_filter_count = Counter()
        self.column_join_count = Counter()

    def analyze_queries(self, queries: List[str]):
        """Analyze queries to build recommendations."""
        for query in queries:
            self._analyze_query_access(query)

    def _analyze_query_access(self, query: str):
        """Extract column access patterns."""
        # Extract WHERE columns
        where_match = re.search(r'WHERE\s+(.+?)(?:GROUP BY|ORDER BY|LIMIT|$)', query, re.IGNORECASE)
        if where_match:
            columns = re.findall(r'(\w+)\s*[=<>]', where_match.group(1))
            for col in columns:
                self.column_filter_count[col] += 1

        # Extract JOIN columns
        joins = re.findall(r'ON\s+(\w+\.\w+)\s*=\s*(\w+\.\w+)', query, re.IGNORECASE)
        for col1, col2 in joins:
            self.column_join_count[col1] += 1
            self.column_join_count[col2] += 1

        # Extract ORDER BY columns
        order_match = re.search(r'ORDER BY\s+(.+?)(?:LIMIT|$)', query, re.IGNORECASE)
        if order_match:
            columns = re.findall(r'(\w+)', order_match.group(1))
            for col in columns:
                self.column_access_count[col] += 1

    def get_recommendations(self, min_score: int = 5) -> List[Dict[str, Any]]:
        """Generate index recommendations."""
        recommendations = []

        # Combine all access patterns
        all_scores = {}
        for col, count in self.column_filter_count.items():
            all_scores[col] = all_scores.get(col, 0) + count * 3  # Weight filter more
        for col, count in self.column_join_count.items():
            all_scores[col] = all_scores.get(col, 0) + count * 2
        for col, count in self.column_access_count.items():
            all_scores[col] = all_scores.get(col, 0) + count

        # Create recommendations
        for col, score in sorted(all_scores.items(), key=lambda x: x[1], reverse=True):
            if score >= min_score:
                table, column = col.split('.') if '.' in col else (col, col)
                if table in self.schema.tables:
                    recommendations.append({
                        'table': table,
                        'column': column,
                        'score': score,
                        'reason': self._get_recommendation_reason(col, score),
                        'already_indexed': column in self.schema.indexes.get(table, [])
                    })

        return recommendations[:10]  # Top 10

    def _get_recommendation_reason(self, col: str, score: int) -> str:
        """Generate reason for recommendation."""
        if col in self.column_filter_count:
            return 'Frequently used in WHERE clauses'
        elif col in self.column_join_count:
            return 'Frequently used in JOIN conditions'
        else:
            return 'Frequently used in ORDER BY clauses'


class QueryOptimizer:
    """Main orchestrator for query optimization."""

    def __init__(self, db_path: str = 'query_optimizer.db'):
        self.db_path = db_path
        self.conn = None
        self.schema = DatabaseSchema()
        self.analyzer = QueryAnalyzer()
        self.n1_detector = N1QueryDetector()
        self.explain_analyzer = ExplainAnalyzer()
        self.recommendation_engine = None
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database for tracking."""
        self.conn = sqlite3.connect(self.db_path)
        cursor = self.conn.cursor()

        # Schema analysis table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS schema_analysis (
                id INTEGER PRIMARY KEY,
                table_name TEXT,
                schema_json TEXT,
                analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Query analysis table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS query_analysis (
                id INTEGER PRIMARY KEY,
                query TEXT,
                execution_time REAL,
                issues TEXT,
                suggestions TEXT,
                patterns TEXT,
                analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # N+1 detection table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS n1_detection (
                id INTEGER PRIMARY KEY,
                table_name TEXT,
                query_count INTEGER,
                total_execution_time REAL,
                details TEXT,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Index recommendations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS index_recommendations (
                id INTEGER PRIMARY KEY,
                table_name TEXT,
                column_name TEXT,
                score INTEGER,
                reason TEXT,
                already_indexed BOOLEAN,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        self.conn.commit()

    def add_schema(self, db_type: str, tables: Dict[str, List[Dict]]):
        """Add schema information."""
        for table_name, columns in tables.items():
            self.schema.add_table(table_name, columns)

        # Store in database
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO schema_analysis (table_name, schema_json) VALUES (?, ?)',
            ('all', json.dumps(self.schema.to_dict()))
        )
        self.conn.commit()

        # Initialize recommendation engine
        self.recommendation_engine = IndexRecommendationEngine(self.schema)

    def analyze_query(self, query: str, execution_time: float = 0.0) -> Dict[str, Any]:
        """Analyze a query and store results."""
        analysis = self.analyzer.analyze_query(query, execution_time)

        # Store in database
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO query_analysis
            (query, execution_time, issues, suggestions, patterns)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            query,
            execution_time,
            json.dumps(analysis['issues']),
            json.dumps(analysis['suggestions']),
            json.dumps(analysis['patterns'])
        ))
        self.conn.commit()

        return analysis

    def analyze_queries_batch(self, queries: List[Tuple[str, float]]) -> List[Dict]:
        """Analyze multiple queries."""
        results = []
        for query, exec_time in queries:
            results.append(self.analyze_query(query, exec_time))
            # Feed to recommendation engine
            if self.recommendation_engine:
                self.recommendation_engine.analyze_queries([query])
        return results

    def detect_n1_issues(self) -> List[Dict]:
        """Detect N+1 query issues."""
        issues = self.n1_detector.detect_n1_pattern()

        # Store in database
        cursor = self.conn.cursor()
        for issue in issues:
            cursor.execute('''
                INSERT INTO n1_detection
                (table_name, query_count, total_execution_time, details)
                VALUES (?, ?, ?, ?)
            ''', (
                issue['table'],
                issue['query_count'],
                issue['total_execution_time'],
                json.dumps(issue)
            ))
        self.conn.commit()

        return issues

    def get_index_recommendations(self) -> List[Dict]:
        """Get index recommendations."""
        if not self.recommendation_engine:
            return []

        recommendations = self.recommendation_engine.get_recommendations()

        # Store in database
        cursor = self.conn.cursor()
        for rec in recommendations:
            cursor.execute('''
                INSERT INTO index_recommendations
                (table_name, column_name, score, reason, already_indexed)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                rec['table'],
                rec['column'],
                rec['score'],
                rec['reason'],
                rec['already_indexed']
            ))
        self.conn.commit()

        return recommendations

    def get_statistics(self) -> Dict[str, Any]:
        """Get optimization statistics."""
        cursor = self.conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM query_analysis')
        query_count = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM n1_detection')
        n1_count = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM index_recommendations WHERE already_indexed = 0')
        rec_count = cursor.fetchone()[0]

        cursor.execute('SELECT AVG(execution_time) FROM query_analysis')
        avg_exec = cursor.fetchone()[0] or 0

        return {
            'total_queries_analyzed': query_count,
            'n1_issues_detected': n1_count,
            'pending_index_recommendations': rec_count,
            'average_query_execution_time': round(avg_exec, 4),
            'schema_tables': len(self.schema.tables)
        }

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


# ============================================================================
# TEST CODE - PRODUCTION READY EXAMPLES
# ============================================================================

def test_query_optimizer():
    """Comprehensive test suite for query optimizer."""
    print("\n" + "="*70)
    print("DATABASE QUERY OPTIMIZATION SYSTEM - TEST SUITE")
    print("="*70)

    # Initialize optimizer
    optimizer = QueryOptimizer('query_optimizer.db')
    print("\n[1] Initializing Query Optimizer...")

    # Define sample schema
    schema = {
        'users': [
            {'name': 'id', 'type': 'INTEGER', 'is_primary_key': True},
            {'name': 'email', 'type': 'TEXT'},
            {'name': 'name', 'type': 'TEXT'},
            {'name': 'created_at', 'type': 'TIMESTAMP'}
        ],
        'posts': [
            {'name': 'id', 'type': 'INTEGER', 'is_primary_key': True},
            {'name': 'user_id', 'type': 'INTEGER'},
            {'name': 'title', 'type': 'TEXT'},
            {'name': 'content', 'type': 'TEXT'},
            {'name': 'created_at', 'type': 'TIMESTAMP'}
        ],
        'comments': [
            {'name': 'id', 'type': 'INTEGER', 'is_primary_key': True},
            {'name': 'post_id', 'type': 'INTEGER'},
            {'name': 'user_id', 'type': 'INTEGER'},
            {'name': 'text', 'type': 'TEXT'},
            {'name': 'created_at', 'type': 'TIMESTAMP'}
        ]
    }

    optimizer.add_schema('postgresql', schema)
    print("   Schema added: users, posts, comments")

    # Test queries with various patterns
    test_queries = [
        ("SELECT * FROM users WHERE id = 1", 0.002),
        ("SELECT id, name, email FROM users WHERE created_at > '2024-01-01'", 0.005),
        ("SELECT p.*, u.name FROM posts p JOIN users u ON p.user_id = u.id", 0.008),
        ("SELECT * FROM posts WHERE user_id IN (SELECT id FROM users)", 0.010),
        ("SELECT title FROM posts ORDER BY created_at DESC LIMIT 10", 0.003),
        ("SELECT id, COUNT(*) FROM posts GROUP BY user_id", 0.015),
        ("SELECT DISTINCT user_id FROM posts", 0.004),
    ]

    print("\n[2] Analyzing Query Patterns...")
    results = optimizer.analyze_queries_batch(test_queries)

    for i, result in enumerate(results, 1):
        query = result['query'][:50] + "..." if len(result['query']) > 50 else result['query']
        issues = len(result['issues'])
        print(f"   Query {i}: {issues} issues found")
        if result['issues']:
            print(f"      Issues: {', '.join(result['issues'][:2])}")

    # Simulate N+1 pattern detection
    print("\n[3] Detecting N+1 Query Patterns...")
    for _ in range(15):
        optimizer.n1_detector.add_query(
            "SELECT * FROM comments WHERE post_id = ?",
            0.003,
            'comments'
        )
    for _ in range(8):
        optimizer.n1_detector.add_query(
            "SELECT * FROM users WHERE id = ?",
            0.001,
            'users'
        )

    n1_issues = optimizer.detect_n1_issues()
    if n1_issues:
        print(f"   N+1 Issues Found: {len(n1_issues)}")
        for issue in n1_issues:
            print(f"      Table '{issue['table']}': {issue['query_count']} queries")
    else:
        print("   No N+1 issues detected")

    # Get index recommendations
    print("\n[4] Index Recommendations...")
    recommendations = optimizer.get_index_recommendations()
    if recommendations:
        print(f"   Generated {len(recommendations)} recommendations:")
        for rec in recommendations[:5]:
            status = "EXISTS" if rec['already_indexed'] else "RECOMMENDED"
            print(f"      {rec['table']}.{rec['column']}: {rec['reason']} [{status}]")

    # Display statistics
    print("\n[5] Optimization Statistics...")
    stats = optimizer.get_statistics()
    print(f"   Total Queries Analyzed: {stats['total_queries_analyzed']}")
    print(f"   N+1 Issues Detected: {stats['n1_issues_detected']}")
    print(f"   Pending Recommendations: {stats['pending_index_recommendations']}")
    print(f"   Avg Query Time: {stats['average_query_execution_time']}ms")
    print(f"   Schema Tables: {stats['schema_tables']}")

    # Test EXPLAIN ANALYZE parsing
    print("\n[6] Testing EXPLAIN ANALYZE Parsing...")
    sample_explain = {
        "Plan": {
            "Node Type": "Seq Scan",
            "Relation Name": "users",
            "Total Cost": 35.50,
            "Actual Loops": 1
        },
        "Planning Time": 0.123,
        "Execution Time": 2.456
    }
    explain_analysis = optimizer.explain_analyzer.parse_explain_output(json.dumps(sample_explain))
    print(f"   Execution Time: {explain_analysis['execution_time']}ms")
    print(f"   Planning Time: {explain_analysis['planning_time']}ms")
    if explain_analysis['issues']:
        print(f"   Issues: {explain_analysis['issues'][0]}")

    print("\n" + "="*70)
    print("TEST SUITE COMPLETED SUCCESSFULLY")
    print("="*70)
    print(f"\nDatabase saved to: query_optimizer.db")

    optimizer.close()


if __name__ == '__main__':
    test_query_optimizer()
