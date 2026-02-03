#!/usr/bin/env python3
"""Code Repository Integration (#36) - Search and analyze code repositories"""
import os
import subprocess
from pathlib import Path
from typing import List, Dict, Optional
import sys

sys.path.append(str(Path(__file__).parent.parent))

from core.persistent_memory import PersistentMemory

class CodeRepository:
    """Interface for searching and analyzing code repositories"""

    def __init__(self, repo_path: str = None, db_path: str = None):
        if repo_path is None:
            repo_path = str(Path(__file__).parent.parent)

        self.repo_path = Path(repo_path)

        if db_path is None:
            db_path = str(self.repo_path / "memory.db")

        self.memory = PersistentMemory(db_path)

    def search_code(self, pattern: str, file_pattern: str = "*", max_results: int = 50) -> List[Dict]:
        """Search for code patterns in the repository"""
        results = []

        try:
            # Use ripgrep if available, otherwise fall back to find + grep
            if self._command_exists('rg'):
                cmd = ['rg', '-n', '--json', pattern, '-g', file_pattern, str(self.repo_path)]
            else:
                cmd = ['grep', '-rn', pattern, str(self.repo_path)]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                for line in result.stdout.split('\n')[:max_results]:
                    if line.strip():
                        results.append(self._parse_grep_line(line))

        except Exception as e:
            self.memory.log_decision(
                f'Code search failed',
                f'Pattern: {pattern}, Error: {str(e)}',
                tags=['code_repo', 'search_error']
            )

        return results

    def find_files(self, pattern: str, file_type: str = None) -> List[str]:
        """Find files matching a pattern"""
        files = []

        try:
            for path in self.repo_path.rglob(pattern):
                if path.is_file():
                    if file_type is None or path.suffix == f'.{file_type}':
                        files.append(str(path.relative_to(self.repo_path)))

        except Exception as e:
            self.memory.log_decision(
                f'File search failed',
                f'Pattern: {pattern}, Error: {str(e)}',
                tags=['code_repo', 'file_search_error']
            )

        return files

    def analyze_structure(self) -> Dict:
        """Analyze repository structure"""
        structure = {
            'total_files': 0,
            'by_extension': {},
            'directories': [],
            'total_lines': 0
        }

        for path in self.repo_path.rglob('*'):
            if path.is_file():
                structure['total_files'] += 1

                ext = path.suffix or 'no_extension'
                structure['by_extension'][ext] = structure['by_extension'].get(ext, 0) + 1

                # Count lines
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        structure['total_lines'] += sum(1 for _ in f)
                except:
                    pass

            elif path.is_dir():
                rel_path = str(path.relative_to(self.repo_path))
                if not rel_path.startswith('.'):
                    structure['directories'].append(rel_path)

        return structure

    def get_file_content(self, file_path: str) -> Optional[str]:
        """Get content of a specific file"""
        try:
            full_path = self.repo_path / file_path
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            self.memory.log_decision(
                f'Failed to read file',
                f'File: {file_path}, Error: {str(e)}',
                tags=['code_repo', 'read_error']
            )
            return None

    def get_git_info(self) -> Dict:
        """Get git repository information"""
        info = {}

        try:
            # Get current branch
            result = subprocess.run(['git', 'branch', '--show-current'],
                                  capture_output=True, text=True, cwd=self.repo_path)
            info['current_branch'] = result.stdout.strip()

            # Get remote URL
            result = subprocess.run(['git', 'remote', 'get-url', 'origin'],
                                  capture_output=True, text=True, cwd=self.repo_path)
            info['remote_url'] = result.stdout.strip()

            # Get last commit
            result = subprocess.run(['git', 'log', '-1', '--pretty=format:%H|%an|%s'],
                                  capture_output=True, text=True, cwd=self.repo_path)
            if result.stdout:
                commit_parts = result.stdout.split('|')
                info['last_commit'] = {
                    'hash': commit_parts[0],
                    'author': commit_parts[1] if len(commit_parts) > 1 else '',
                    'message': commit_parts[2] if len(commit_parts) > 2 else ''
                }

        except Exception as e:
            info['error'] = str(e)

        return info

    def _command_exists(self, command: str) -> bool:
        """Check if a command exists"""
        try:
            subprocess.run([command, '--version'], capture_output=True, timeout=2)
            return True
        except:
            return False

    def _parse_grep_line(self, line: str) -> Dict:
        """Parse a grep output line"""
        parts = line.split(':', 2)
        if len(parts) >= 3:
            return {
                'file': parts[0],
                'line': int(parts[1]) if parts[1].isdigit() else 0,
                'content': parts[2].strip()
            }
        return {'content': line}


if __name__ == '__main__':
    # Test the system
    repo = CodeRepository()

    print("Code Repository Integration ready!")

    # Get git info
    git_info = repo.get_git_info()
    print(f"\nGit Info:")
    print(f"  Branch: {git_info.get('current_branch', 'unknown')}")
    print(f"  Remote: {git_info.get('remote_url', 'unknown')}")

    # Analyze structure
    structure = repo.analyze_structure()
    print(f"\nRepository Structure:")
    print(f"  Total files: {structure['total_files']}")
    print(f"  Total lines: {structure['total_lines']}")
    print(f"  File types: {len(structure['by_extension'])}")

    # Find Python files
    py_files = repo.find_files('*.py')
    print(f"\nPython files: {len(py_files)}")
