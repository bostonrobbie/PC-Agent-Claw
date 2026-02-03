"""
Git History Intelligence System
Analyzes git history to understand code evolution, change patterns, and historical context.
Provides insights into code authorship, blame annotation, and change impact analysis.
"""

import sqlite3
import subprocess
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from collections import defaultdict, Counter
import hashlib


class GitIntelligence:
    """Production-ready Git History Intelligence system with SQLite backend."""

    def __init__(self, repo_path: str = ".", db_path: Optional[str] = None):
        """Initialize Git Intelligence system.

        Args:
            repo_path: Path to git repository
            db_path: Path to SQLite database (defaults to git_intelligence.db in repo)
        """
        self.repo_path = Path(repo_path)
        if not (self.repo_path / ".git").exists():
            raise ValueError(f"Not a git repository: {repo_path}")

        self.db_path = Path(db_path or self.repo_path / "git_intelligence.db")
        self._init_database()

    def _init_database(self) -> None:
        """Initialize SQLite database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Commits table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS commits (
                    commit_hash TEXT PRIMARY KEY,
                    author TEXT NOT NULL,
                    author_email TEXT,
                    commit_date TEXT NOT NULL,
                    message TEXT,
                    summary TEXT,
                    files_changed INTEGER,
                    insertions INTEGER,
                    deletions INTEGER,
                    parents TEXT
                )
            """)

            # Files changed table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS file_changes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    commit_hash TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    change_type TEXT,
                    insertions INTEGER,
                    deletions INTEGER,
                    FOREIGN KEY(commit_hash) REFERENCES commits(commit_hash)
                )
            """)

            # Blame annotations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS blame_annotations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL,
                    line_number INTEGER,
                    commit_hash TEXT,
                    author TEXT,
                    author_email TEXT,
                    commit_date TEXT,
                    content TEXT,
                    FOREIGN KEY(commit_hash) REFERENCES commits(commit_hash)
                )
            """)

            # Change patterns table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS change_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_hash TEXT UNIQUE,
                    pattern_name TEXT,
                    file_patterns TEXT,
                    author TEXT,
                    frequency INTEGER,
                    first_occurrence TEXT,
                    last_occurrence TEXT
                )
            """)

            # Code authors table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS code_authors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    author TEXT UNIQUE,
                    email TEXT,
                    commit_count INTEGER,
                    lines_added INTEGER,
                    lines_deleted INTEGER,
                    files_touched INTEGER,
                    last_commit_date TEXT,
                    expertise_areas TEXT
                )
            """)

            # Change impact cache table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS change_impact (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    commit_hash TEXT,
                    impact_score REAL,
                    affected_files INTEGER,
                    potential_issues TEXT,
                    risk_level TEXT,
                    cached_date TEXT,
                    FOREIGN KEY(commit_hash) REFERENCES commits(commit_hash)
                )
            """)

            conn.commit()

    def analyze_git_history(self, max_commits: Optional[int] = None) -> Dict[str, Any]:
        """Analyze full git history and populate database.

        Args:
            max_commits: Maximum commits to analyze (None for all)

        Returns:
            Dictionary with analysis statistics
        """
        try:
            # Get commit log
            cmd = ["git", "-C", str(self.repo_path), "log", "--format=%H|%an|%ae|%aI|%s|%b|%P"]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            commits = result.stdout.strip().split("\n")

            if max_commits:
                commits = commits[:max_commits]

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                stats = {"total_commits": 0, "inserted": 0, "skipped": 0}

                for commit_line in commits:
                    if not commit_line.strip():
                        continue

                    parts = commit_line.split("|")
                    if len(parts) < 5:
                        continue

                    commit_hash = parts[0]
                    author = parts[1]
                    author_email = parts[2]
                    commit_date = parts[3]
                    message_summary = parts[4]
                    parents = parts[6] if len(parts) > 6 else ""

                    # Check if already in database
                    cursor.execute("SELECT commit_hash FROM commits WHERE commit_hash = ?", (commit_hash,))
                    if cursor.fetchone():
                        stats["skipped"] += 1
                        continue

                    # Get file statistics for this commit
                    files_stats = self._get_commit_file_stats(commit_hash)

                    # Insert commit
                    cursor.execute("""
                        INSERT OR IGNORE INTO commits
                        (commit_hash, author, author_email, commit_date, message, summary,
                         files_changed, insertions, deletions, parents)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        commit_hash, author, author_email, commit_date, parts[5] if len(parts) > 5 else "",
                        message_summary, files_stats["files"], files_stats["insertions"],
                        files_stats["deletions"], parents
                    ))

                    # Insert file changes
                    for file_change in files_stats["changes"]:
                        cursor.execute("""
                            INSERT INTO file_changes
                            (commit_hash, file_path, change_type, insertions, deletions)
                            VALUES (?, ?, ?, ?, ?)
                        """, (
                            commit_hash, file_change["path"], file_change["type"],
                            file_change.get("insertions", 0), file_change.get("deletions", 0)
                        ))

                    stats["inserted"] += 1
                    stats["total_commits"] += 1

                self._update_code_authors()
                self._identify_change_patterns()
                conn.commit()

            return stats

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Git command failed: {e.stderr}")

    def _get_commit_file_stats(self, commit_hash: str) -> Dict[str, Any]:
        """Get file change statistics for a commit."""
        try:
            cmd = [
                "git", "-C", str(self.repo_path), "show", "--numstat",
                "--format=%b", commit_hash
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            files = 0
            insertions = 0
            deletions = 0
            changes = []

            for line in result.stdout.strip().split("\n"):
                if not line.strip() or line.startswith("commit"):
                    continue

                parts = line.split("\t")
                if len(parts) >= 3:
                    try:
                        ins = int(parts[0]) if parts[0] != "-" else 0
                        dels = int(parts[1]) if parts[1] != "-" else 0
                        file_path = parts[2]

                        insertions += ins
                        deletions += dels
                        files += 1

                        # Determine change type
                        if ins == 0 and dels == 0:
                            change_type = "RENAME"
                        elif dels == 0:
                            change_type = "ADD"
                        elif ins == 0:
                            change_type = "DELETE"
                        else:
                            change_type = "MODIFY"

                        changes.append({
                            "path": file_path,
                            "type": change_type,
                            "insertions": ins,
                            "deletions": dels
                        })
                    except ValueError:
                        continue

            return {
                "files": files,
                "insertions": insertions,
                "deletions": deletions,
                "changes": changes
            }
        except subprocess.CalledProcessError:
            return {"files": 0, "insertions": 0, "deletions": 0, "changes": []}

    def get_blame_annotation(self, file_path: str) -> List[Dict[str, Any]]:
        """Get blame annotation for a file showing who last modified each line.

        Args:
            file_path: Path to file relative to repo

        Returns:
            List of blame annotations per line
        """
        try:
            full_path = self.repo_path / file_path
            if not full_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            cmd = [
                "git", "-C", str(self.repo_path), "blame", "-l", "--porcelain",
                file_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            annotations = []
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                for line_num, line in enumerate(result.stdout.strip().split("\n"), 1):
                    if not line.strip():
                        continue

                    parts = line.split()
                    if len(parts) < 2:
                        continue

                    commit_hash = parts[0].lstrip("^")

                    # Get commit details
                    cursor.execute("""
                        SELECT author, author_email, commit_date FROM commits
                        WHERE commit_hash = ?
                    """, (commit_hash,))

                    commit_info = cursor.fetchone()
                    if commit_info:
                        author, email, date = commit_info
                    else:
                        author = email = date = "Unknown"

                    annotation = {
                        "line_number": line_num,
                        "commit_hash": commit_hash,
                        "author": author,
                        "email": email,
                        "commit_date": date,
                        "content": " ".join(parts[9:]) if len(parts) > 9 else ""
                    }
                    annotations.append(annotation)

                    # Cache annotation
                    cursor.execute("""
                        INSERT INTO blame_annotations
                        (file_path, line_number, commit_hash, author, author_email, commit_date, content)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        file_path, line_num, commit_hash, author, email, date,
                        annotation["content"]
                    ))

                conn.commit()

            return annotations

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Git blame failed: {e.stderr}")

    def _identify_change_patterns(self) -> None:
        """Identify recurring change patterns in git history."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Get all file change sequences
            cursor.execute("""
                SELECT fc.file_path, c.author, GROUP_CONCAT(fc.change_type)
                FROM file_changes fc
                JOIN commits c ON fc.commit_hash = c.commit_hash
                GROUP BY fc.file_path, c.author
                ORDER BY COUNT(*) DESC
            """)

            patterns = defaultdict(lambda: {"authors": Counter(), "occurrences": 0})

            for row in cursor.fetchall():
                file_path, author, changes = row
                if not changes:
                    continue

                # Create pattern hash
                pattern = f"{file_path}:{changes}"
                pattern_hash = hashlib.md5(pattern.encode()).hexdigest()

                patterns[pattern_hash]["file_pattern"] = file_path
                patterns[pattern_hash]["change_sequence"] = changes
                patterns[pattern_hash]["authors"][author] += 1
                patterns[pattern_hash]["occurrences"] += 1

            # Store patterns with frequency > 1
            for pattern_hash, data in patterns.items():
                if data["occurrences"] > 1:
                    cursor.execute("""
                        INSERT OR IGNORE INTO change_patterns
                        (pattern_hash, pattern_name, file_patterns, author, frequency, first_occurrence)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        pattern_hash,
                        f"Pattern_{pattern_hash[:8]}",
                        data["file_pattern"],
                        max(data["authors"], key=data["authors"].get),
                        data["occurrences"],
                        datetime.now().isoformat()
                    ))

            conn.commit()

    def get_code_author_info(self, author_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get information about code authors and their expertise.

        Args:
            author_name: Optional specific author name

        Returns:
            List of author statistics
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if author_name:
                cursor.execute("""
                    SELECT author, email, commit_count, lines_added, lines_deleted,
                           files_touched, last_commit_date, expertise_areas
                    FROM code_authors WHERE author = ?
                """, (author_name,))
            else:
                cursor.execute("""
                    SELECT author, email, commit_count, lines_added, lines_deleted,
                           files_touched, last_commit_date, expertise_areas
                    FROM code_authors ORDER BY commit_count DESC
                """)

            results = []
            for row in cursor.fetchall():
                results.append({
                    "author": row[0],
                    "email": row[1],
                    "commits": row[2],
                    "lines_added": row[3],
                    "lines_deleted": row[4],
                    "files_touched": row[5],
                    "last_commit_date": row[6],
                    "expertise_areas": row[7]
                })

            return results

    def _update_code_authors(self) -> None:
        """Update code authors table with comprehensive statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT DISTINCT author, author_email FROM commits
            """)

            for author, email in cursor.fetchall():
                # Get statistics
                cursor.execute("""
                    SELECT COUNT(*), SUM(insertions), SUM(deletions), COUNT(DISTINCT fc.file_path)
                    FROM commits c
                    LEFT JOIN file_changes fc ON c.commit_hash = fc.commit_hash
                    WHERE c.author = ?
                """, (author,))

                stats = cursor.fetchone()
                commits = stats[0] or 0
                insertions = stats[1] or 0
                deletions = stats[2] or 0
                files = stats[3] or 0

                # Get last commit date
                cursor.execute("""
                    SELECT MAX(commit_date) FROM commits WHERE author = ?
                """, (author,))
                last_commit = cursor.fetchone()[0] or ""

                # Identify expertise areas (most modified file types)
                cursor.execute("""
                    SELECT substr(fc.file_path, instr(fc.file_path, '.') + 1) as ext,
                           COUNT(*) as cnt
                    FROM commits c
                    JOIN file_changes fc ON c.commit_hash = fc.commit_hash
                    WHERE c.author = ?
                    GROUP BY ext ORDER BY cnt DESC LIMIT 5
                """, (author,))

                expertise = ",".join([row[0] for row in cursor.fetchall()])

                cursor.execute("""
                    INSERT OR REPLACE INTO code_authors
                    (author, email, commit_count, lines_added, lines_deleted,
                     files_touched, last_commit_date, expertise_areas)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (author, email, commits, insertions, deletions, files, last_commit, expertise))

            conn.commit()

    def analyze_change_impact(self, commit_hash: str) -> Dict[str, Any]:
        """Analyze the impact of a specific commit.

        Args:
            commit_hash: Git commit hash

        Returns:
            Impact analysis with risk assessment
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Check cache
            cursor.execute("""
                SELECT impact_score, affected_files, potential_issues, risk_level
                FROM change_impact WHERE commit_hash = ?
            """, (commit_hash,))

            cached = cursor.fetchone()
            if cached:
                return {
                    "commit_hash": commit_hash,
                    "impact_score": cached[0],
                    "affected_files": cached[1],
                    "potential_issues": json.loads(cached[2]),
                    "risk_level": cached[3],
                    "cached": True
                }

            # Get commit details
            cursor.execute("""
                SELECT insertions, deletions, files_changed FROM commits
                WHERE commit_hash = ?
            """, (commit_hash,))

            commit = cursor.fetchone()
            if not commit:
                raise ValueError(f"Commit not found: {commit_hash}")

            insertions, deletions, files_changed = commit

            # Get changed files
            cursor.execute("""
                SELECT file_path, change_type, insertions, deletions
                FROM file_changes WHERE commit_hash = ?
            """, (commit_hash,))

            changes = cursor.fetchall()

            # Calculate impact score
            total_changes = insertions + deletions
            impact_score = min(100.0, (total_changes / 100.0) * 10 + files_changed * 2)

            # Assess risk
            issues = []
            risk_level = "LOW"

            if files_changed > 10:
                issues.append("Large number of files changed")
                risk_level = "MEDIUM"

            if total_changes > 1000:
                issues.append("Significant code modifications")
                if risk_level == "LOW":
                    risk_level = "MEDIUM"

            if deletions > insertions * 0.5:
                issues.append("Significant deletions detected")

            critical_files = [c[0] for c in changes if any(critical in c[0] for critical in ["config", "core", "auth"])]
            if critical_files:
                issues.append(f"Critical files modified: {', '.join(critical_files)}")
                risk_level = "HIGH"

            # Cache result
            cursor.execute("""
                INSERT INTO change_impact
                (commit_hash, impact_score, affected_files, potential_issues, risk_level, cached_date)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                commit_hash, impact_score, files_changed,
                json.dumps(issues), risk_level, datetime.now().isoformat()
            ))
            conn.commit()

            return {
                "commit_hash": commit_hash,
                "impact_score": impact_score,
                "affected_files": files_changed,
                "potential_issues": issues,
                "risk_level": risk_level,
                "cached": False
            }

    def get_historical_context(self, file_path: str, days_back: int = 30) -> Dict[str, Any]:
        """Retrieve historical context for a file.

        Args:
            file_path: Path to file relative to repo
            days_back: Number of days to look back

        Returns:
            Historical context including recent changes and authors
        """
        cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Get recent changes
            cursor.execute("""
                SELECT c.commit_hash, c.author, c.commit_date, c.message,
                       fc.change_type, fc.insertions, fc.deletions
                FROM file_changes fc
                JOIN commits c ON fc.commit_hash = c.commit_hash
                WHERE fc.file_path = ? AND c.commit_date > ?
                ORDER BY c.commit_date DESC
            """, (file_path, cutoff_date))

            recent_changes = []
            authors = Counter()

            for row in cursor.fetchall():
                recent_changes.append({
                    "commit": row[0],
                    "author": row[1],
                    "date": row[2],
                    "message": row[3],
                    "type": row[4],
                    "insertions": row[5],
                    "deletions": row[6]
                })
                authors[row[1]] += 1

            return {
                "file_path": file_path,
                "recent_changes": recent_changes,
                "primary_authors": authors.most_common(3),
                "total_changes_30d": len(recent_changes),
                "last_modified": recent_changes[0]["date"] if recent_changes else "Never"
            }

    def get_commit_details(self, commit_hash: str) -> Dict[str, Any]:
        """Get comprehensive details about a specific commit.

        Args:
            commit_hash: Git commit hash

        Returns:
            Complete commit information
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT commit_hash, author, author_email, commit_date, message,
                       summary, files_changed, insertions, deletions
                FROM commits WHERE commit_hash = ?
            """, (commit_hash,))

            commit = cursor.fetchone()
            if not commit:
                raise ValueError(f"Commit not found: {commit_hash}")

            cursor.execute("""
                SELECT file_path, change_type, insertions, deletions
                FROM file_changes WHERE commit_hash = ?
            """, (commit_hash,))

            files = []
            for row in cursor.fetchall():
                files.append({
                    "path": row[0],
                    "type": row[1],
                    "insertions": row[2],
                    "deletions": row[3]
                })

            return {
                "hash": commit[0],
                "author": commit[1],
                "email": commit[2],
                "date": commit[3],
                "message": commit[4],
                "summary": commit[5],
                "files_changed": commit[6],
                "insertions": commit[7],
                "deletions": commit[8],
                "files": files
            }

    def search_commits_by_pattern(self, pattern: str, search_in: str = "message") -> List[Dict[str, Any]]:
        """Search commits by pattern in message or code changes.

        Args:
            pattern: Regex pattern to search for
            search_in: "message", "files", or "author"

        Returns:
            Matching commits
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if search_in == "message":
                cursor.execute("""
                    SELECT commit_hash, author, commit_date, summary
                    FROM commits WHERE message LIKE ?
                    ORDER BY commit_date DESC LIMIT 50
                """, (f"%{pattern}%",))

            elif search_in == "author":
                cursor.execute("""
                    SELECT commit_hash, author, commit_date, summary
                    FROM commits WHERE author LIKE ?
                    ORDER BY commit_date DESC LIMIT 50
                """, (f"%{pattern}%",))

            elif search_in == "files":
                cursor.execute("""
                    SELECT DISTINCT c.commit_hash, c.author, c.commit_date, c.summary
                    FROM commits c
                    JOIN file_changes fc ON c.commit_hash = fc.commit_hash
                    WHERE fc.file_path LIKE ?
                    ORDER BY c.commit_date DESC LIMIT 50
                """, (f"%{pattern}%",))

            results = []
            for row in cursor.fetchall():
                results.append({
                    "commit": row[0],
                    "author": row[1],
                    "date": row[2],
                    "summary": row[3]
                })

            return results

    def get_statistics(self) -> Dict[str, Any]:
        """Get overall repository statistics from git history.

        Returns:
            Comprehensive statistics
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM commits")
            total_commits = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(DISTINCT author) FROM commits")
            unique_authors = cursor.fetchone()[0]

            cursor.execute("SELECT SUM(insertions), SUM(deletions) FROM commits")
            rows = cursor.fetchone()
            total_insertions = rows[0] or 0
            total_deletions = rows[1] or 0

            cursor.execute("SELECT COUNT(DISTINCT file_path) FROM file_changes")
            total_files = cursor.fetchone()[0]

            cursor.execute("SELECT MAX(commit_date) FROM commits")
            last_commit = cursor.fetchone()[0] or "Never"

            cursor.execute("SELECT COUNT(*) FROM change_patterns")
            identified_patterns = cursor.fetchone()[0]

            return {
                "total_commits": total_commits,
                "unique_authors": unique_authors,
                "total_insertions": total_insertions,
                "total_deletions": total_deletions,
                "total_files_modified": total_files,
                "last_commit_date": last_commit,
                "identified_patterns": identified_patterns,
                "average_insertions_per_commit": total_insertions / max(total_commits, 1),
                "average_deletions_per_commit": total_deletions / max(total_commits, 1)
            }


# ============================================================================
# WORKING TEST CODE
# ============================================================================

if __name__ == "__main__":
    import tempfile
    import os

    print("=" * 70)
    print("Git History Intelligence System - Test Suite")
    print("=" * 70)

    # Initialize with current repo
    repo_path = "."

    try:
        # Create intelligence system
        print("\n[1] Initializing Git Intelligence System...")
        git_intel = GitIntelligence(repo_path=repo_path)
        print("✓ System initialized with database at:", git_intel.db_path)

        # Analyze git history
        print("\n[2] Analyzing git history (max 20 commits)...")
        stats = git_intel.analyze_git_history(max_commits=20)
        print(f"✓ Analysis complete:")
        print(f"  - Total commits: {stats['total_commits']}")
        print(f"  - Inserted: {stats['inserted']}")
        print(f"  - Skipped: {stats['skipped']}")

        # Get repository statistics
        print("\n[3] Repository Statistics:")
        repo_stats = git_intel.get_statistics()
        for key, value in repo_stats.items():
            if isinstance(value, float):
                print(f"  - {key}: {value:.2f}")
            else:
                print(f"  - {key}: {value}")

        # Get code authors
        print("\n[4] Top Code Authors:")
        authors = git_intel.get_code_author_info()
        for idx, author in enumerate(authors[:5], 1):
            print(f"  {idx}. {author['author']}")
            print(f"     Commits: {author['commits']}, Lines: +{author['lines_added']}/-{author['lines_deleted']}")

        # Search commits
        print("\n[5] Searching Commits:")
        if repo_stats['total_commits'] > 0:
            commits = git_intel.search_commits_by_pattern("Add", search_in="message")
            print(f"✓ Found {len(commits)} commits with 'Add' in message")
            for commit in commits[:3]:
                print(f"  - {commit['commit'][:8]}: {commit['summary']}")

        # Get first commit for testing
        print("\n[6] Analyzing Commit Impact:")
        with sqlite3.connect(git_intel.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT commit_hash FROM commits LIMIT 1")
            first_commit = cursor.fetchone()

            if first_commit:
                commit_hash = first_commit[0]
                impact = git_intel.analyze_change_impact(commit_hash)
                print(f"✓ Commit: {commit_hash[:8]}")
                print(f"  - Impact Score: {impact['impact_score']:.2f}")
                print(f"  - Affected Files: {impact['affected_files']}")
                print(f"  - Risk Level: {impact['risk_level']}")
                print(f"  - Issues: {len(impact['potential_issues'])}")

        # Get commit details
        print("\n[7] Commit Details:")
        with sqlite3.connect(git_intel.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT commit_hash FROM commits LIMIT 1")
            first_commit = cursor.fetchone()

            if first_commit:
                details = git_intel.get_commit_details(first_commit[0])
                print(f"✓ Commit: {details['hash'][:8]}")
                print(f"  - Author: {details['author']}")
                print(f"  - Date: {details['date']}")
                print(f"  - Summary: {details['summary']}")
                print(f"  - Files Changed: {len(details['files'])}")

        print("\n" + "=" * 70)
        print("✓ All tests completed successfully!")
        print("=" * 70)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
