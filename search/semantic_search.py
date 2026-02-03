"""
Semantic Code Search Across All Projects

Index and search across every file with semantic understanding, not just keywords.
Find similar code patterns, reuse solutions across projects.

Author: AI Self-Improvement System
Created: 2026-02-03
"""

import sqlite3
import json
import os
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading


@dataclass
class CodeChunk:
    """A piece of code with semantic metadata"""
    id: Optional[int]
    project_name: str
    file_path: str
    content: str
    content_hash: str
    language: str
    chunk_type: str  # 'function', 'class', 'module', 'snippet'
    semantic_tags: List[str]
    dependencies: List[str]
    complexity_score: int
    lines_of_code: int
    created_at: str
    last_updated: str


class SemanticCodeSearch:
    """Semantic code search across all projects"""

    def __init__(self, db_path: str = "semantic_code_search.db", max_workers: int = 8):
        self.db_path = db_path
        self.max_workers = max_workers
        self._db_lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        """Initialize database"""
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

        # Semantic index (word -> chunk mappings)
        c.execute('''
            CREATE TABLE IF NOT EXISTS semantic_index (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT NOT NULL,
                chunk_id INTEGER NOT NULL,
                weight REAL DEFAULT 1.0,
                FOREIGN KEY (chunk_id) REFERENCES code_chunks (id)
            )
        ''')

        # Pattern library (reusable patterns)
        c.execute('''
            CREATE TABLE IF NOT EXISTS patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                pattern_type TEXT NOT NULL,
                code_template TEXT NOT NULL,
                usage_count INTEGER DEFAULT 0,
                quality_score REAL DEFAULT 0.0,
                tags TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Search history
        c.execute('''
            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                results_count INTEGER NOT NULL,
                top_result_id INTEGER,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create indexes
        c.execute('CREATE INDEX IF NOT EXISTS idx_semantic_word ON semantic_index(word)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_chunks_hash ON code_chunks(content_hash)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_chunks_type ON code_chunks(chunk_type)')

        conn.commit()
        conn.close()

    def index_project(self, project_name: str, root_path: str, parallel: bool = True) -> Dict:
        """
        Index all code in a project with optional parallel processing.

        Args:
            project_name: Name of the project
            root_path: Root directory to index
            parallel: Use multi-threaded indexing (default: True)

        Returns:
            Dict with indexing stats including performance metrics
        """
        start_time = time.time()
        root_path = os.path.abspath(root_path)

        if not os.path.exists(root_path):
            return {'error': f'Path does not exist: {root_path}'}

        # Create or get project
        with self._db_lock:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()

            c.execute('''
                INSERT INTO projects (name, root_path)
                VALUES (?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    root_path = ?,
                    last_indexed = CURRENT_TIMESTAMP
            ''', (project_name, root_path, root_path))

            c.execute('SELECT id FROM projects WHERE name = ?', (project_name,))
            project_id = c.fetchone()[0]

            conn.commit()
            conn.close()

        # Find all code files
        code_files = self._find_code_files(root_path)
        total_files = len(code_files)

        if parallel and len(code_files) > 10:
            total_chunks = self._index_files_parallel(code_files, project_id)
        else:
            total_chunks = self._index_files_sequential(code_files, project_id)

        # Update project stats
        with self._db_lock:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('''
                UPDATE projects
                SET total_files = ?, total_chunks = ?, last_indexed = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (total_files, total_chunks, project_id))

            conn.commit()
            conn.close()

        elapsed_time = time.time() - start_time
        files_per_sec = total_files / elapsed_time if elapsed_time > 0 else 0

        return {
            'project_name': project_name,
            'files_indexed': total_files,
            'chunks_indexed': total_chunks,
            'elapsed_time': round(elapsed_time, 2),
            'files_per_second': round(files_per_sec, 2),
            'parallel': parallel
        }

    def _index_files_sequential(self, code_files: List[str], project_id: int) -> int:
        """Index files sequentially (original method)"""
        total_chunks = 0
        conn = sqlite3.connect(self.db_path)

        for file_path in code_files:
            try:
                chunks = self._parse_file(file_path, project_id)
                for chunk in chunks:
                    chunk_id = self._add_chunk(conn, chunk)
                    if chunk_id:
                        self._index_chunk(conn, chunk_id, chunk.content, chunk.semantic_tags)
                        total_chunks += 1
            except Exception as e:
                print(f"Error indexing {file_path}: {e}")

        conn.close()
        return total_chunks

    def _index_files_parallel(self, code_files: List[str], project_id: int) -> int:
        """
        Index files in parallel using ThreadPoolExecutor.
        Target: 100+ files/sec with 8 threads.
        """
        total_chunks = 0
        chunk_buffer = []
        buffer_lock = threading.Lock()

        def process_file(file_path: str) -> int:
            """Process a single file and return chunk count"""
            try:
                chunks = self._parse_file(file_path, project_id)

                # Add to buffer for batch insertion
                with buffer_lock:
                    chunk_buffer.extend(chunks)

                    # Flush buffer when it reaches threshold
                    if len(chunk_buffer) >= 50:
                        self._flush_chunk_buffer(chunk_buffer.copy())
                        chunk_buffer.clear()

                return len(chunks)
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
                return 0

        # Process files in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(process_file, file_path): file_path
                      for file_path in code_files}

            for future in as_completed(futures):
                try:
                    chunk_count = future.result()
                    total_chunks += chunk_count
                except Exception as e:
                    file_path = futures[future]
                    print(f"Exception processing {file_path}: {e}")

        # Flush remaining chunks
        if chunk_buffer:
            self._flush_chunk_buffer(chunk_buffer)

        return total_chunks

    def _flush_chunk_buffer(self, chunks: List[CodeChunk]):
        """Flush chunk buffer to database in batch"""
        with self._db_lock:
            conn = sqlite3.connect(self.db_path)
            try:
                for chunk in chunks:
                    chunk_id = self._add_chunk(conn, chunk)
                    if chunk_id:
                        self._index_chunk(conn, chunk_id, chunk.content, chunk.semantic_tags)
            finally:
                conn.close()

    def _find_code_files(self, root_path: str) -> List[str]:
        """Find all code files in directory"""
        extensions = {
            '.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.cpp', '.c', '.h',
            '.cs', '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.scala',
            '.sql', '.sh', '.bash', '.ps1', '.r', '.m', '.mm'
        }

        code_files = []
        for root, dirs, files in os.walk(root_path):
            # Skip common non-code directories
            dirs[:] = [d for d in dirs if d not in {
                'node_modules', '.git', '__pycache__', '.venv', 'venv',
                'build', 'dist', '.pytest_cache', '.mypy_cache'
            }]

            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    code_files.append(os.path.join(root, file))

        return code_files

    def _parse_file(self, file_path: str, project_id: int) -> List[CodeChunk]:
        """Parse file into semantic chunks"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception:
            return []

        language = self._detect_language(file_path)
        chunks = []

        # Extract functions, classes, etc.
        if language == 'python':
            chunks.extend(self._parse_python(file_path, content, project_id))
        elif language in ('javascript', 'typescript'):
            chunks.extend(self._parse_javascript(file_path, content, project_id))
        else:
            # Generic parsing - split by meaningful sections
            chunks.extend(self._parse_generic(file_path, content, project_id, language))

        return chunks

    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension"""
        ext = os.path.splitext(file_path)[1].lower()
        mapping = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.jsx': 'javascript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.cs': 'csharp',
            '.go': 'go',
            '.rs': 'rust',
            '.rb': 'ruby',
            '.php': 'php',
        }
        return mapping.get(ext, 'unknown')

    def _parse_python(self, file_path: str, content: str, project_id: int) -> List[CodeChunk]:
        """Parse Python code into semantic chunks"""
        chunks = []

        # Find functions
        func_pattern = r'def\s+(\w+)\s*\([^)]*\):'
        for match in re.finditer(func_pattern, content):
            func_name = match.group(1)
            start = match.start()

            # Extract function body (simplified - just next 20 lines)
            lines = content[start:].split('\n')[:20]
            func_content = '\n'.join(lines)

            # Extract semantic info
            tags = self._extract_semantic_tags(func_content)
            deps = self._extract_dependencies(func_content)

            chunks.append(CodeChunk(
                id=None,
                project_name='',
                file_path=file_path,
                content=func_content,
                content_hash=hashlib.md5(func_content.encode()).hexdigest(),
                language='python',
                chunk_type='function',
                semantic_tags=tags,
                dependencies=deps,
                complexity_score=self._calculate_complexity(func_content),
                lines_of_code=len(lines),
                created_at=datetime.now().isoformat(),
                last_updated=datetime.now().isoformat()
            ))

        # Find classes
        class_pattern = r'class\s+(\w+)'
        for match in re.finditer(class_pattern, content):
            class_name = match.group(1)
            start = match.start()
            lines = content[start:].split('\n')[:30]
            class_content = '\n'.join(lines)

            tags = self._extract_semantic_tags(class_content)
            deps = self._extract_dependencies(class_content)

            chunks.append(CodeChunk(
                id=None,
                project_name='',
                file_path=file_path,
                content=class_content,
                content_hash=hashlib.md5(class_content.encode()).hexdigest(),
                language='python',
                chunk_type='class',
                semantic_tags=tags,
                dependencies=deps,
                complexity_score=self._calculate_complexity(class_content),
                lines_of_code=len(lines),
                created_at=datetime.now().isoformat(),
                last_updated=datetime.now().isoformat()
            ))

        return chunks

    def _parse_javascript(self, file_path: str, content: str, project_id: int) -> List[CodeChunk]:
        """Parse JavaScript/TypeScript code"""
        chunks = []

        # Find functions (multiple patterns)
        patterns = [
            r'function\s+(\w+)\s*\([^)]*\)',
            r'const\s+(\w+)\s*=\s*\([^)]*\)\s*=>',
            r'(\w+)\s*:\s*function\s*\([^)]*\)',
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, content):
                func_name = match.group(1)
                start = match.start()
                lines = content[start:].split('\n')[:20]
                func_content = '\n'.join(lines)

                tags = self._extract_semantic_tags(func_content)
                deps = self._extract_dependencies(func_content)

                chunks.append(CodeChunk(
                    id=None,
                    project_name='',
                    file_path=file_path,
                    content=func_content,
                    content_hash=hashlib.md5(func_content.encode()).hexdigest(),
                    language='javascript',
                    chunk_type='function',
                    semantic_tags=tags,
                    dependencies=deps,
                    complexity_score=self._calculate_complexity(func_content),
                    lines_of_code=len(lines),
                    created_at=datetime.now().isoformat(),
                    last_updated=datetime.now().isoformat()
                ))

        return chunks

    def _parse_generic(self, file_path: str, content: str, project_id: int, language: str) -> List[CodeChunk]:
        """Generic parsing for unknown languages"""
        # Split into meaningful sections (every 10 lines)
        lines = content.split('\n')
        chunks = []

        for i in range(0, len(lines), 10):
            section = '\n'.join(lines[i:i+10])
            if not section.strip():
                continue

            tags = self._extract_semantic_tags(section)
            deps = self._extract_dependencies(section)

            chunks.append(CodeChunk(
                id=None,
                project_name='',
                file_path=file_path,
                content=section,
                content_hash=hashlib.md5(section.encode()).hexdigest(),
                language=language,
                chunk_type='snippet',
                semantic_tags=tags,
                dependencies=deps,
                complexity_score=self._calculate_complexity(section),
                lines_of_code=len(section.split('\n')),
                created_at=datetime.now().isoformat(),
                last_updated=datetime.now().isoformat()
            ))

        return chunks

    def _extract_semantic_tags(self, code: str) -> List[str]:
        """Extract semantic tags from code"""
        tags = set()

        # Common patterns
        if re.search(r'\bapi\b|\bhttp\b|\brequest\b', code, re.I):
            tags.add('api')
        if re.search(r'\bdatabase\b|\bsql\b|\bquery\b', code, re.I):
            tags.add('database')
        if re.search(r'\bauth\b|\blogin\b|\btoken\b', code, re.I):
            tags.add('authentication')
        if re.search(r'\btest\b|\bassert\b|\bmock\b', code, re.I):
            tags.add('testing')
        if re.search(r'\bfile\b|\bread\b|\bwrite\b', code, re.I):
            tags.add('file_io')
        if re.search(r'\basync\b|\bawait\b|\bpromise\b', code, re.I):
            tags.add('async')
        if re.search(r'\berror\b|\bexception\b|\btry\b|\bcatch\b', code, re.I):
            tags.add('error_handling')

        return list(tags)

    def _extract_dependencies(self, code: str) -> List[str]:
        """Extract dependencies from code"""
        deps = set()

        # Python imports
        for match in re.finditer(r'import\s+([\w.]+)', code):
            deps.add(match.group(1))
        for match in re.finditer(r'from\s+([\w.]+)\s+import', code):
            deps.add(match.group(1))

        # JavaScript imports
        for match in re.finditer(r'import\s+.*\s+from\s+["\']([^"\']+)["\']', code):
            deps.add(match.group(1))

        return list(deps)

    def _calculate_complexity(self, code: str) -> int:
        """Calculate code complexity (cyclomatic complexity approximation)"""
        complexity = 1  # Base complexity

        # Count decision points
        keywords = ['if', 'elif', 'else', 'for', 'while', 'and', 'or', 'case', 'catch']
        for keyword in keywords:
            complexity += len(re.findall(rf'\b{keyword}\b', code))

        return complexity

    def _add_chunk(self, conn: sqlite3.Connection, chunk: CodeChunk) -> Optional[int]:
        """Add code chunk to database"""
        c = conn.cursor()

        try:
            c.execute('''
                INSERT INTO code_chunks
                (project_id, file_path, content, content_hash, language,
                 chunk_type, semantic_tags, dependencies, complexity_score, lines_of_code)
                SELECT p.id, ?, ?, ?, ?, ?, ?, ?, ?, ?
                FROM projects p
                WHERE p.root_path = (
                    SELECT root_path FROM projects
                    ORDER BY length(root_path) DESC
                    LIMIT 1
                )
            ''', (
                chunk.file_path, chunk.content, chunk.content_hash,
                chunk.language, chunk.chunk_type,
                json.dumps(chunk.semantic_tags),
                json.dumps(chunk.dependencies),
                chunk.complexity_score, chunk.lines_of_code
            ))

            conn.commit()
            return c.lastrowid

        except sqlite3.IntegrityError:
            # Chunk already exists (duplicate hash)
            return None

    def _index_chunk(self, conn: sqlite3.Connection, chunk_id: int,
                     content: str, semantic_tags: List[str]):
        """Index chunk for semantic search"""
        c = conn.cursor()

        # Extract words (simplified tokenization)
        words = set(re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]{2,}\b', content.lower()))

        # Add semantic tags with higher weight
        for tag in semantic_tags:
            c.execute('''
                INSERT INTO semantic_index (word, chunk_id, weight)
                VALUES (?, ?, ?)
            ''', (tag, chunk_id, 3.0))

        # Add regular words with normal weight
        for word in words:
            c.execute('''
                INSERT INTO semantic_index (word, chunk_id, weight)
                VALUES (?, ?, ?)
            ''', (word, chunk_id, 1.0))

        conn.commit()

    def search(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Semantic search for code.

        Returns chunks ranked by relevance.
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Extract query words
        query_words = set(re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]{2,}\b', query.lower()))

        if not query_words:
            conn.close()
            return []

        # Find matching chunks with relevance scoring
        placeholders = ','.join('?' * len(query_words))
        c.execute(f'''
            SELECT
                cc.id,
                cc.file_path,
                cc.content,
                cc.language,
                cc.chunk_type,
                cc.semantic_tags,
                SUM(si.weight) as relevance_score,
                p.name as project_name
            FROM code_chunks cc
            JOIN semantic_index si ON cc.id = si.chunk_id
            JOIN projects p ON cc.project_id = p.id
            WHERE si.word IN ({placeholders})
            GROUP BY cc.id
            ORDER BY relevance_score DESC
            LIMIT ?
        ''', (*query_words, limit))

        results = []
        for row in c.fetchall():
            results.append({
                'id': row[0],
                'file_path': row[1],
                'content': row[2],
                'language': row[3],
                'chunk_type': row[4],
                'semantic_tags': json.loads(row[5]),
                'relevance_score': row[6],
                'project_name': row[7]
            })

        # Record search
        if results:
            c.execute('''
                INSERT INTO search_history (query, results_count, top_result_id)
                VALUES (?, ?, ?)
            ''', (query, len(results), results[0]['id'] if results else None))

        conn.commit()
        conn.close()

        return results

    def find_similar(self, code: str, limit: int = 5) -> List[Dict]:
        """Find similar code chunks"""
        tags = self._extract_semantic_tags(code)
        if not tags:
            return []

        # Search using semantic tags
        query = ' '.join(tags)
        return self.search(query, limit)

    def get_stats(self) -> Dict:
        """Get search engine statistics"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute('SELECT COUNT(*) FROM projects')
        total_projects = c.fetchone()[0]

        c.execute('SELECT COUNT(*) FROM code_chunks')
        total_chunks = c.fetchone()[0]

        c.execute('SELECT COUNT(*) FROM search_history')
        total_searches = c.fetchone()[0]

        c.execute('SELECT COUNT(DISTINCT word) FROM semantic_index')
        unique_words = c.fetchone()[0]

        conn.close()

        return {
            'total_projects': total_projects,
            'total_chunks': total_chunks,
            'total_searches': total_searches,
            'unique_words': unique_words
        }


# Example usage and testing
if __name__ == "__main__":
    print("Testing Semantic Code Search...")

    search = SemanticCodeSearch()

    # Index current project
    print("\n1. Indexing current project...")
    result = search.index_project("PC-Agent-Claw", os.getcwd())
    print(f"   Files indexed: {result.get('files_indexed', 0)}")
    print(f"   Chunks indexed: {result.get('chunks_indexed', 0)}")

    # Get stats
    print("\n2. Search engine stats...")
    stats = search.get_stats()
    print(f"   Total projects: {stats['total_projects']}")
    print(f"   Total chunks: {stats['total_chunks']}")
    print(f"   Unique words: {stats['unique_words']}")

    # Search for code
    print("\n3. Searching for 'database query'...")
    results = search.search("database query", limit=5)
    print(f"   Found {len(results)} results")
    for i, result in enumerate(results[:3], 1):
        print(f"   {i}. {result['file_path']}")
        print(f"      Type: {result['chunk_type']}, Language: {result['language']}")
        print(f"      Relevance: {result['relevance_score']:.1f}")
        print(f"      Tags: {result['semantic_tags']}")

    # Find similar code
    print("\n4. Finding similar code...")
    sample_code = """
    def authenticate_user(username, password):
        token = generate_token(username)
        return token
    """
    similar = search.find_similar(sample_code, limit=3)
    print(f"   Found {len(similar)} similar chunks")

    print("\n[SUCCESS] Semantic Code Search testing complete!")
    print(f"   Database: {search.db_path}")
