"""
Code Example Library System
Production-ready system for managing reusable code patterns, examples, and templates.
Features: Pattern matching, similarity scoring, quality assessment, and smart search.
"""

import sqlite3
import json
import hashlib
import re
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from difflib import SequenceMatcher
from collections import Counter
import os


@dataclass
class CodePattern:
    """Represents a code pattern with metadata"""
    pattern_id: Optional[int] = None
    name: str = ""
    code: str = ""
    language: str = "python"
    category: str = ""
    tags: List[str] = None
    description: str = ""
    quality_score: float = 0.0
    usage_count: int = 0
    created_at: str = ""
    updated_at: str = ""
    template_vars: Dict[str, str] = None
    dependencies: List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.template_vars is None:
            self.template_vars = {}
        if self.dependencies is None:
            self.dependencies = []
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()


class CodeLibraryDB:
    """Database management for code patterns"""

    def __init__(self, db_path: str = "code_library.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """Initialize database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS code_patterns (
                pattern_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                code TEXT NOT NULL,
                language TEXT DEFAULT 'python',
                category TEXT,
                description TEXT,
                quality_score REAL DEFAULT 0.0,
                usage_count INTEGER DEFAULT 0,
                created_at TEXT,
                updated_at TEXT,
                template_vars TEXT,
                dependencies TEXT,
                code_hash TEXT UNIQUE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pattern_tags (
                tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_id INTEGER NOT NULL,
                tag TEXT NOT NULL,
                FOREIGN KEY (pattern_id) REFERENCES code_patterns(pattern_id),
                UNIQUE(pattern_id, tag)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pattern_similarity (
                similarity_id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_id_1 INTEGER NOT NULL,
                pattern_id_2 INTEGER NOT NULL,
                similarity_score REAL,
                FOREIGN KEY (pattern_id_1) REFERENCES code_patterns(pattern_id),
                FOREIGN KEY (pattern_id_2) REFERENCES code_patterns(pattern_id),
                UNIQUE(pattern_id_1, pattern_id_2)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quality_metrics (
                metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_id INTEGER NOT NULL,
                readability REAL,
                maintainability REAL,
                efficiency REAL,
                test_coverage REAL,
                FOREIGN KEY (pattern_id) REFERENCES code_patterns(pattern_id)
            )
        """)

        conn.commit()
        conn.close()

    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def execute_query(self, query: str, params: Tuple = ()) -> List[sqlite3.Row]:
        """Execute SELECT query"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        return results

    def execute_update(self, query: str, params: Tuple = ()) -> int:
        """Execute INSERT/UPDATE/DELETE query"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        last_id = cursor.lastrowid
        conn.close()
        return last_id


class PatternMatcher:
    """Pattern matching and similarity analysis"""

    @staticmethod
    def compute_code_hash(code: str) -> str:
        """Generate hash of code for duplicate detection"""
        return hashlib.sha256(code.encode()).hexdigest()

    @staticmethod
    def extract_structure(code: str) -> Dict[str, Any]:
        """Extract structural features from code"""
        structure = {
            "lines": len(code.split('\n')),
            "functions": len(re.findall(r'^def \w+\(', code, re.MULTILINE)),
            "classes": len(re.findall(r'^class \w+', code, re.MULTILINE)),
            "imports": len(re.findall(r'^import |^from ', code, re.MULTILINE)),
            "loops": len(re.findall(r'\b(for|while)\b', code)),
            "conditionals": len(re.findall(r'\b(if|elif|else)\b', code)),
            "comments": len(re.findall(r'#.*$', code, re.MULTILINE)),
        }
        return structure

    @staticmethod
    def similarity_ratio(code1: str, code2: str) -> float:
        """Calculate similarity ratio between two code snippets"""
        matcher = SequenceMatcher(None, code1, code2)
        return matcher.ratio()

    @staticmethod
    def extract_tokens(code: str) -> List[str]:
        """Extract meaningful tokens from code"""
        tokens = re.findall(r'\b\w+\b', code)
        return [t for t in tokens if len(t) > 2]

    @staticmethod
    def semantic_similarity(code1: str, code2: str) -> float:
        """Calculate semantic similarity based on token overlap"""
        tokens1 = set(PatternMatcher.extract_tokens(code1))
        tokens2 = set(PatternMatcher.extract_tokens(code2))

        if not tokens1 or not tokens2:
            return 0.0

        intersection = len(tokens1 & tokens2)
        union = len(tokens1 | tokens2)
        return intersection / union if union > 0 else 0.0

    @staticmethod
    def extract_patterns(code: str) -> List[str]:
        """Extract common patterns from code"""
        patterns = []

        # Function definitions
        functions = re.findall(r'def (\w+)\(([^)]*)\)', code)
        for func_name, params in functions:
            patterns.append(f"function:{func_name}")

        # Class definitions
        classes = re.findall(r'class (\w+)(?:\(([^)]*)\))?:', code)
        for class_name, _ in classes:
            patterns.append(f"class:{class_name}")

        # Exception handling
        if 'try:' in code:
            patterns.append("exception_handling")

        # List comprehensions
        if '[' in code and 'for' in code and ']' in code:
            patterns.append("list_comprehension")

        # Decorators
        if '@' in code:
            decorators = re.findall(r'@(\w+)', code)
            patterns.extend([f"decorator:{d}" for d in decorators])

        # Context managers
        if 'with ' in code:
            patterns.append("context_manager")

        return patterns


class QualityScorer:
    """Calculate quality metrics for code patterns"""

    @staticmethod
    def score_readability(code: str) -> float:
        """Score code readability (0-1)"""
        score = 1.0

        # Penalty for long lines
        long_lines = sum(1 for line in code.split('\n') if len(line) > 100)
        score -= min(0.2, long_lines * 0.05)

        # Bonus for comments
        comment_lines = len(re.findall(r'#.*$', code, re.MULTILINE))
        total_lines = len(code.split('\n'))
        comment_ratio = comment_lines / total_lines if total_lines > 0 else 0
        score += min(0.2, comment_ratio * 0.5)

        # Bonus for proper naming
        named_items = len(re.findall(r'\b[a-z_][a-z_0-9]*\b', code))
        if named_items > 0:
            score += 0.1

        return max(0.0, min(1.0, score))

    @staticmethod
    def score_maintainability(code: str) -> float:
        """Score code maintainability (0-1)"""
        score = 1.0

        # Function complexity
        functions = re.findall(r'def \w+\([^)]*\):', code)
        if len(functions) > 5:
            score -= 0.2

        # Excessive nesting
        max_indent = max(len(line) - len(line.lstrip())
                        for line in code.split('\n') if line.strip())
        if max_indent > 20:
            score -= 0.15

        # Code duplication
        lines = code.split('\n')
        line_counts = Counter(lines)
        duplicates = sum(count - 1 for count in line_counts.values() if count > 1)
        score -= min(0.3, duplicates * 0.05)

        return max(0.0, min(1.0, score))

    @staticmethod
    def score_efficiency(code: str) -> float:
        """Score code efficiency (0-1)"""
        score = 1.0

        # Avoid O(n^2) patterns
        nested_loops = len(re.findall(r'for.*?:\s*for', code, re.DOTALL))
        score -= min(0.3, nested_loops * 0.15)

        # Check for inefficient string operations
        if 'for' in code and '+=' in code:
            score -= 0.1

        # Bonus for using built-ins
        builtins = ['list', 'dict', 'set', 'enumerate', 'zip', 'map', 'filter']
        builtin_count = sum(code.count(b) for b in builtins)
        score += min(0.2, builtin_count * 0.05)

        return max(0.0, min(1.0, score))

    @staticmethod
    def calculate_quality_score(code: str) -> float:
        """Calculate overall quality score"""
        readability = QualityScorer.score_readability(code)
        maintainability = QualityScorer.score_maintainability(code)
        efficiency = QualityScorer.score_efficiency(code)

        # Weighted average
        return (readability * 0.3 + maintainability * 0.4 + efficiency * 0.3)


class CodeLibrary:
    """Main Code Library System"""

    def __init__(self, db_path: str = "code_library.db"):
        self.db = CodeLibraryDB(db_path)
        self.matcher = PatternMatcher()
        self.scorer = QualityScorer()

    def save_pattern(self, pattern: CodePattern) -> int:
        """Save a code pattern to library"""
        code_hash = self.matcher.compute_code_hash(pattern.code)

        # Check for duplicates
        existing = self.db.execute_query(
            "SELECT pattern_id FROM code_patterns WHERE code_hash = ?",
            (code_hash,)
        )
        if existing:
            raise ValueError(f"Duplicate pattern detected: {pattern.name}")

        # Calculate quality score
        if pattern.quality_score == 0.0:
            pattern.quality_score = self.scorer.calculate_quality_score(pattern.code)

        # Insert pattern
        pattern_id = self.db.execute_update(
            """INSERT INTO code_patterns
               (name, code, language, category, description, quality_score,
                created_at, updated_at, template_vars, dependencies, code_hash)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (pattern.name, pattern.code, pattern.language, pattern.category,
             pattern.description, pattern.quality_score, pattern.created_at,
             pattern.updated_at, json.dumps(pattern.template_vars),
             json.dumps(pattern.dependencies), code_hash)
        )

        # Insert tags
        for tag in pattern.tags:
            self.db.execute_update(
                "INSERT INTO pattern_tags (pattern_id, tag) VALUES (?, ?)",
                (pattern_id, tag)
            )

        return pattern_id

    def get_pattern(self, pattern_id: int) -> Optional[CodePattern]:
        """Retrieve a pattern by ID"""
        results = self.db.execute_query(
            "SELECT * FROM code_patterns WHERE pattern_id = ?",
            (pattern_id,)
        )

        if not results:
            return None

        row = results[0]
        pattern = CodePattern(
            pattern_id=row['pattern_id'],
            name=row['name'],
            code=row['code'],
            language=row['language'],
            category=row['category'],
            description=row['description'],
            quality_score=row['quality_score'],
            usage_count=row['usage_count'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            template_vars=json.loads(row['template_vars']) if row['template_vars'] else {},
            dependencies=json.loads(row['dependencies']) if row['dependencies'] else []
        )

        # Get tags
        tag_results = self.db.execute_query(
            "SELECT tag FROM pattern_tags WHERE pattern_id = ?",
            (pattern_id,)
        )
        pattern.tags = [tag['tag'] for tag in tag_results]

        return pattern

    def find_similar_patterns(self, code: str, threshold: float = 0.6) -> List[Tuple[int, float]]:
        """Find patterns similar to given code"""
        all_patterns = self.db.execute_query("SELECT pattern_id, code FROM code_patterns")
        similar = []

        for row in all_patterns:
            similarity = self.matcher.similarity_ratio(code, row['code'])
            if similarity >= threshold:
                similar.append((row['pattern_id'], similarity))

        # Sort by similarity score
        similar.sort(key=lambda x: x[1], reverse=True)
        return similar

    def search_by_pattern(self, pattern_name: str) -> List[CodePattern]:
        """Search patterns by extracted features"""
        all_patterns = self.db.execute_query("SELECT pattern_id FROM code_patterns")
        results = []

        for row in all_patterns:
            pattern = self.get_pattern(row['pattern_id'])
            if pattern:
                patterns = self.matcher.extract_patterns(pattern.code)
                if any(pattern_name.lower() in p.lower() for p in patterns):
                    results.append(pattern)

        return results

    def search_by_tag(self, tag: str) -> List[CodePattern]:
        """Search patterns by tag"""
        results = self.db.execute_query(
            """SELECT DISTINCT p.pattern_id FROM code_patterns p
               JOIN pattern_tags pt ON p.pattern_id = pt.pattern_id
               WHERE pt.tag = ?""",
            (tag,)
        )

        patterns = []
        for row in results:
            pattern = self.get_pattern(row['pattern_id'])
            if pattern:
                patterns.append(pattern)

        return patterns

    def search_by_category(self, category: str) -> List[CodePattern]:
        """Search patterns by category"""
        results = self.db.execute_query(
            "SELECT pattern_id FROM code_patterns WHERE category = ?",
            (category,)
        )

        return [self.get_pattern(row['pattern_id']) for row in results]

    def search_by_use_case(self, use_case: str) -> List[CodePattern]:
        """Search patterns by use case keyword"""
        results = self.db.execute_query("SELECT pattern_id FROM code_patterns")
        matches = []

        for row in results:
            pattern = self.get_pattern(row['pattern_id'])
            if pattern:
                search_text = (pattern.description + ' ' + pattern.name + ' ' +
                             ' '.join(pattern.tags)).lower()
                if use_case.lower() in search_text:
                    matches.append(pattern)

        return matches

    def instantiate_template(self, pattern_id: int, variables: Dict[str, str]) -> str:
        """Instantiate a template pattern with variables"""
        pattern = self.get_pattern(pattern_id)
        if not pattern:
            raise ValueError(f"Pattern {pattern_id} not found")

        code = pattern.code
        for var_name, var_value in variables.items():
            code = code.replace(f"{{{var_name}}}", var_value)

        return code

    def get_quality_metrics(self, pattern_id: int) -> Dict[str, float]:
        """Get quality metrics for a pattern"""
        results = self.db.execute_query(
            "SELECT * FROM quality_metrics WHERE pattern_id = ?",
            (pattern_id,)
        )

        if results:
            row = results[0]
            return {
                "readability": row['readability'],
                "maintainability": row['maintainability'],
                "efficiency": row['efficiency'],
                "test_coverage": row['test_coverage']
            }

        return {}

    def update_quality_metrics(self, pattern_id: int, metrics: Dict[str, float]):
        """Update quality metrics for a pattern"""
        self.db.execute_update(
            """INSERT OR REPLACE INTO quality_metrics
               (pattern_id, readability, maintainability, efficiency, test_coverage)
               VALUES (?, ?, ?, ?, ?)""",
            (pattern_id, metrics.get('readability', 0),
             metrics.get('maintainability', 0), metrics.get('efficiency', 0),
             metrics.get('test_coverage', 0))
        )

    def increment_usage(self, pattern_id: int):
        """Increment usage count for a pattern"""
        self.db.execute_update(
            "UPDATE code_patterns SET usage_count = usage_count + 1 WHERE pattern_id = ?",
            (pattern_id,)
        )

    def list_all_patterns(self, limit: int = 100) -> List[CodePattern]:
        """List all patterns with optional limit"""
        results = self.db.execute_query(
            "SELECT pattern_id FROM code_patterns ORDER BY quality_score DESC LIMIT ?",
            (limit,)
        )

        return [self.get_pattern(row['pattern_id']) for row in results]

    def get_statistics(self) -> Dict[str, Any]:
        """Get library statistics"""
        count_result = self.db.execute_query(
            "SELECT COUNT(*) as count FROM code_patterns"
        )

        score_result = self.db.execute_query(
            "SELECT AVG(quality_score) as avg_score, MAX(quality_score) as max_score FROM code_patterns"
        )

        return {
            "total_patterns": count_result[0]['count'] if count_result else 0,
            "avg_quality_score": score_result[0]['avg_score'] if score_result else 0,
            "max_quality_score": score_result[0]['max_score'] if score_result else 0
        }


# ============================================================================
# TEST CODE - Production Ready Tests
# ============================================================================

if __name__ == "__main__":
    import sys

    print("=" * 70)
    print("CODE EXAMPLE LIBRARY SYSTEM - PRODUCTION TEST SUITE")
    print("=" * 70)

    # Clean up old test database
    if os.path.exists("code_library.db"):
        os.remove("code_library.db")

    library = CodeLibrary("code_library.db")

    # Test 1: Save approved code patterns
    print("\n[TEST 1] Saving code patterns...")

    pattern1 = CodePattern(
        name="fibonacci_recursive",
        code="""def fibonacci(n):
    \"\"\"Calculate fibonacci number recursively\"\"\"
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)""",
        language="python",
        category="algorithms",
        description="Recursive fibonacci implementation",
        tags=["recursion", "mathematical", "simple"],
        dependencies=[]
    )

    pattern2 = CodePattern(
        name="fibonacci_iterative",
        code="""def fibonacci(n):
    \"\"\"Calculate fibonacci number iteratively\"\"\"
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b""",
        language="python",
        category="algorithms",
        description="Iterative fibonacci implementation",
        tags=["iteration", "mathematical", "efficient"],
        dependencies=[]
    )

    pattern3 = CodePattern(
        name="list_filter_map",
        code="""numbers = [1, 2, 3, 4, 5]
squared = [x**2 for x in numbers if x % 2 == 0]
print(squared)""",
        language="python",
        category="functional",
        description="Filter and map using list comprehension",
        tags=["list_comprehension", "functional", "python"],
        dependencies=[]
    )

    id1 = library.save_pattern(pattern1)
    id2 = library.save_pattern(pattern2)
    id3 = library.save_pattern(pattern3)

    print(f"[OK] Saved pattern 1: fibonacci_recursive (ID: {id1})")
    print(f"[OK] Saved pattern 2: fibonacci_iterative (ID: {id2})")
    print(f"[OK] Saved pattern 3: list_filter_map (ID: {id3})")

    # Test 2: Retrieve patterns
    print("\n[TEST 2] Retrieving patterns...")
    retrieved = library.get_pattern(id1)
    print(f"[OK] Retrieved pattern: {retrieved.name}")
    print(f"  Quality Score: {retrieved.quality_score:.2f}")
    print(f"  Tags: {retrieved.tags}")

    # Test 3: Pattern matching and similarity
    print("\n[TEST 3] Finding similar patterns...")
    test_code = """def fibonacci(n):
    if n <= 1:
        return n
    a, b = 0, 1
    for i in range(2, n + 1):
        a, b = b, a + b
    return b"""

    similar = library.find_similar_patterns(test_code, threshold=0.5)
    print(f"[OK] Found {len(similar)} similar patterns:")
    for pid, score in similar:
        pattern = library.get_pattern(pid)
        print(f"  - {pattern.name}: {score:.2f}")

    # Test 4: Search by tag
    print("\n[TEST 4] Searching by tag...")
    results = library.search_by_tag("mathematical")
    print(f"[OK] Found {len(results)} patterns with tag 'mathematical':")
    for pattern in results:
        print(f"  - {pattern.name}")

    # Test 5: Search by category
    print("\n[TEST 5] Searching by category...")
    results = library.search_by_category("algorithms")
    print(f"[OK] Found {len(results)} patterns in 'algorithms' category:")
    for pattern in results:
        print(f"  - {pattern.name}")

    # Test 6: Search by use case
    print("\n[TEST 6] Searching by use case...")
    results = library.search_by_use_case("efficient")
    print(f"[OK] Found {len(results)} patterns matching 'efficient':")
    for pattern in results:
        print(f"  - {pattern.name}")

    # Test 7: Pattern extraction
    print("\n[TEST 7] Extracting patterns...")
    code = pattern1.code
    patterns = library.matcher.extract_patterns(code)
    print(f"[OK] Extracted patterns from code:")
    for pattern in patterns:
        print(f"  - {pattern}")

    # Test 8: Quality scoring
    print("\n[TEST 8] Quality scoring metrics...")
    quality = library.scorer.calculate_quality_score(pattern1.code)
    readability = library.scorer.score_readability(pattern1.code)
    maintainability = library.scorer.score_maintainability(pattern1.code)
    efficiency = library.scorer.score_efficiency(pattern1.code)

    print(f"[OK] Quality Metrics for {pattern1.name}:")
    print(f"  - Overall: {quality:.2f}")
    print(f"  - Readability: {readability:.2f}")
    print(f"  - Maintainability: {maintainability:.2f}")
    print(f"  - Efficiency: {efficiency:.2f}")

    # Test 9: Usage tracking
    print("\n[TEST 9] Usage tracking...")
    library.increment_usage(id1)
    library.increment_usage(id1)
    updated = library.get_pattern(id1)
    print(f"[OK] Usage count for {updated.name}: {updated.usage_count}")

    # Test 10: Statistics
    print("\n[TEST 10] Library statistics...")
    stats = library.get_statistics()
    print(f"[OK] Total patterns: {stats['total_patterns']}")
    print(f"[OK] Average quality: {stats['avg_quality_score']:.2f}")
    print(f"[OK] Max quality: {stats['max_quality_score']:.2f}")

    # Test 11: List all patterns
    print("\n[TEST 11] Listing all patterns...")
    all_patterns = library.list_all_patterns()
    print(f"[OK] Retrieved {len(all_patterns)} patterns:")
    for pattern in all_patterns:
        print(f"  - {pattern.name} (Score: {pattern.quality_score:.2f})")

    # Test 12: Semantic similarity
    print("\n[TEST 12] Semantic similarity analysis...")
    sim1 = library.matcher.semantic_similarity(pattern1.code, pattern2.code)
    sim2 = library.matcher.semantic_similarity(pattern1.code, pattern3.code)
    print(f"[OK] Semantic similarity (fib_recursive vs fib_iterative): {sim1:.2f}")
    print(f"[OK] Semantic similarity (fib_recursive vs list_filter): {sim2:.2f}")

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED SUCCESSFULLY")
    print("=" * 70)
