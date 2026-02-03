#!/usr/bin/env python3
"""Dependency Tracker (#39) - Track and manage system dependencies"""
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Set
import json
import re

sys.path.append(str(Path(__file__).parent.parent))

class DependencyTracker:
    """Track and manage Python dependencies"""

    def __init__(self, project_root: str = None):
        if project_root is None:
            self.project_root = Path(__file__).parent.parent
        else:
            self.project_root = Path(project_root)

    def scan_imports(self) -> Dict[str, List[str]]:
        """Scan all Python files for imports"""
        imports_by_file = {}

        for py_file in self.project_root.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                imports = self._extract_imports(content)
                rel_path = str(py_file.relative_to(self.project_root))
                imports_by_file[rel_path] = imports

            except Exception as e:
                print(f"Error scanning {py_file}: {e}")

        return imports_by_file

    def _extract_imports(self, content: str) -> List[str]:
        """Extract import statements from Python code"""
        imports = []

        # Match: import module
        for match in re.finditer(r'^\s*import\s+([a-zA-Z0-9_\.]+)', content, re.MULTILINE):
            module = match.group(1).split('.')[0]
            imports.append(module)

        # Match: from module import ...
        for match in re.finditer(r'^\s*from\s+([a-zA-Z0-9_\.]+)\s+import', content, re.MULTILINE):
            module = match.group(1).split('.')[0]
            imports.append(module)

        return list(set(imports))  # Remove duplicates

    def get_installed_packages(self) -> Dict[str, str]:
        """Get list of installed packages with versions"""
        result = subprocess.run([sys.executable, '-m', 'pip', 'list', '--format=json'],
                              capture_output=True, text=True)

        if result.returncode == 0:
            packages = json.loads(result.stdout)
            return {pkg['name'].lower(): pkg['version'] for pkg in packages}

        return {}

    def get_external_dependencies(self) -> Set[str]:
        """Get list of external (non-standard library) dependencies"""
        all_imports = set()

        imports_by_file = self.scan_imports()
        for imports in imports_by_file.values():
            all_imports.update(imports)

        # Filter out standard library modules
        stdlib_modules = set(sys.stdlib_module_names)
        external_deps = all_imports - stdlib_modules

        # Filter out local modules
        local_modules = {'core', 'monitoring', 'business', 'testing', 'strategies'}
        external_deps = external_deps - local_modules

        return external_deps

    def generate_requirements_txt(self) -> str:
        """Generate requirements.txt content"""
        external_deps = self.get_external_dependencies()
        installed = self.get_installed_packages()

        requirements = []
        for dep in sorted(external_deps):
            dep_lower = dep.lower().replace('_', '-')

            # Try to find version
            if dep_lower in installed:
                requirements.append(f"{dep_lower}=={installed[dep_lower]}")
            else:
                # Try alternative names
                found = False
                for pkg_name, version in installed.items():
                    if dep.lower() in pkg_name or pkg_name in dep.lower():
                        requirements.append(f"{pkg_name}=={version}")
                        found = True
                        break

                if not found:
                    requirements.append(dep_lower)

        return '\n'.join(requirements)

    def check_missing_dependencies(self) -> List[str]:
        """Check for imported modules that aren't installed"""
        external_deps = self.get_external_dependencies()
        installed = self.get_installed_packages()

        missing = []
        for dep in external_deps:
            dep_lower = dep.lower().replace('_', '-')

            # Check if it's installed
            if dep_lower not in installed:
                # Check alternative names
                found = any(dep.lower() in pkg or pkg in dep.lower()
                          for pkg in installed.keys())

                if not found:
                    missing.append(dep)

        return missing

    def get_dependency_graph(self) -> Dict[str, List[str]]:
        """Get dependency graph showing which files depend on which modules"""
        imports_by_file = self.scan_imports()
        external_deps = self.get_external_dependencies()

        graph = {}
        for file_path, imports in imports_by_file.items():
            file_deps = [imp for imp in imports if imp in external_deps]
            if file_deps:
                graph[file_path] = file_deps

        return graph

    def get_statistics(self) -> Dict:
        """Get dependency statistics"""
        imports_by_file = self.scan_imports()
        external_deps = self.get_external_dependencies()
        installed = self.get_installed_packages()
        missing = self.check_missing_dependencies()

        return {
            'total_python_files': len(imports_by_file),
            'external_dependencies': len(external_deps),
            'installed_packages': len(installed),
            'missing_dependencies': len(missing),
            'missing_list': missing
        }

    def save_requirements(self, filepath: str = None):
        """Save requirements.txt file"""
        if filepath is None:
            filepath = self.project_root / "requirements.txt"

        requirements = self.generate_requirements_txt()

        with open(filepath, 'w') as f:
            f.write(requirements)

        return filepath


if __name__ == '__main__':
    # Test the system
    tracker = DependencyTracker()

    print("Dependency Tracker ready!")

    # Get statistics
    stats = tracker.get_statistics()
    print(f"\nDependency Statistics:")
    print(json.dumps(stats, indent=2))

    # Generate requirements.txt
    print(f"\nGenerating requirements.txt...")
    requirements = tracker.generate_requirements_txt()
    print(f"Found {len(requirements.splitlines())} dependencies")

    # Check missing
    missing = tracker.check_missing_dependencies()
    if missing:
        print(f"\nWARNING: Missing dependencies: {', '.join(missing)}")
