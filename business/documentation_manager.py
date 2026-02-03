#!/usr/bin/env python3
"""Documentation Manager (#38) - Generate and manage system documentation"""
import os
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import json
import sys

sys.path.append(str(Path(__file__).parent.parent))

from core.persistent_memory import PersistentMemory

class DocumentationManager:
    """Manage system documentation"""

    def __init__(self, docs_dir: str = None, db_path: str = None):
        if docs_dir is None:
            workspace = Path(__file__).parent.parent
            docs_dir = str(workspace / "docs")

        self.docs_dir = Path(docs_dir)
        self.docs_dir.mkdir(exist_ok=True)

        if db_path is None:
            db_path = str(Path(__file__).parent.parent / "memory.db")

        self.memory = PersistentMemory(db_path)

    def generate_system_overview(self) -> str:
        """Generate high-level system overview"""
        workspace = Path(__file__).parent.parent

        # Count systems by category
        core_systems = len(list((workspace / "core").glob("*.py")))
        monitoring_systems = len(list((workspace / "monitoring").glob("*.py")))
        business_systems = len(list((workspace / "business").glob("*.py")))
        testing_systems = len(list((workspace / "testing").glob("*.py")))

        doc = f"""# System Overview

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Architecture

This AI agent system consists of multiple integrated components:

### Core Systems ({core_systems} modules)
- Persistent Memory: Long-term memory across sessions
- Long-Term Memory: Semantic memory retrieval
- Autonomous Work Queue: Background task processing
- API Access: Secure credential management
- API Connector: Universal REST API integration
- Database Query: Natural language to SQL
- Webhook System: External event handling
- Message Queue: Async communication

### Monitoring Systems ({monitoring_systems} modules)
- Performance Monitor: System metrics tracking
- Research Database: Knowledge organization
- Error Recovery: Automatic error handling
- Paper Trading Tracker: Simulated trading performance

### Business Systems ({business_systems} modules)
- Backtesting Pipeline: Strategy validation
- Context Compression: Token optimization
- Code Repository: Code search and analysis
- Strategy Library: Strategy management
- Documentation Manager: This system

### Testing Systems ({testing_systems} modules)
- Test Framework: Automated testing

## Data Storage

- **memory.db**: Core persistent memory (tasks, decisions, context)
- **long_term_memory.db**: Semantic memory storage
- **research.db**: Research and insights
- **paper_trading.db**: Paper trading records
- **strategy_library.db**: Trading strategies

## Key Features

1. **Autonomous Operation**: Works independently on queued tasks
2. **Persistent Memory**: Never forgets across sessions
3. **Self-Learning**: Improves from every interaction
4. **Dual GPU Support**: Parallel processing capability
5. **External Integration**: APIs, webhooks, message queues
6. **Comprehensive Testing**: Automated test framework

## Getting Started

1. Initialize systems: `python core/persistent_memory.py`
2. Start work queue: `python core/autonomous_work_queue.py`
3. Run tests: `python testing/test_framework.py`

## Architecture Diagram

```
┌─────────────────────────────────────────────┐
│          User Interface / CLI                │
└──────────────┬──────────────────────────────┘
               │
┌──────────────┴──────────────────────────────┐
│        Autonomous Work Queue                 │
│    (Background Task Processing)              │
└──────────────┬──────────────────────────────┘
               │
       ┌───────┴───────┐
       │               │
┌──────┴──────┐  ┌────┴─────┐
│ Core Systems │  │ Business │
│              │  │ Systems  │
│ - Memory     │  │          │
│ - API Access │  │ - Trading│
│ - Webhooks   │  │ - Backtest│
└──────┬──────┘  └────┬─────┘
       │               │
       └───────┬───────┘
               │
┌──────────────┴──────────────────────────────┐
│          Data Layer (SQLite DBs)             │
└──────────────────────────────────────────────┘
```
"""

        # Save to file
        overview_path = self.docs_dir / "SYSTEM_OVERVIEW.md"
        overview_path.write_text(doc)

        return doc

    def generate_api_reference(self, module_path: str) -> str:
        """Generate API reference for a module"""
        import importlib.util
        import inspect

        spec = importlib.util.spec_from_file_location("module", module_path)
        if not spec or not spec.loader:
            return "Error loading module"

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        doc = f"""# API Reference: {Path(module_path).stem}

"""

        # Find all classes
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if obj.__module__ == "module":
                doc += f"\n## class {name}\n\n"

                if obj.__doc__:
                    doc += f"{obj.__doc__.strip()}\n\n"

                # Find methods
                doc += "### Methods\n\n"
                for method_name, method in inspect.getmembers(obj, inspect.isfunction):
                    if not method_name.startswith('_') or method_name == '__init__':
                        sig = inspect.signature(method)
                        doc += f"#### `{method_name}{sig}`\n\n"

                        if method.__doc__:
                            doc += f"{method.__doc__.strip()}\n\n"

        return doc

    def generate_changelog(self, limit: int = 50) -> str:
        """Generate changelog from memory decisions"""
        cursor = self.memory.conn.cursor()

        cursor.execute('''
            SELECT decision, reasoning, created_at
            FROM decisions
            WHERE tags LIKE '%build%' OR tags LIKE '%completed%'
            ORDER BY created_at DESC
            LIMIT ?
        ''', (limit,))

        doc = f"""# Changelog

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Recent system changes:

"""

        for row in cursor.fetchall():
            date = row['created_at']
            decision = row['decision']
            doc += f"- **{date}**: {decision}\n"

        return doc

    def generate_deployment_guide(self) -> str:
        """Generate deployment guide"""
        doc = """# Deployment Guide

## Prerequisites

- Python 3.8+
- SQLite 3
- Git

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/bostonrobbie/PC-Agent-Claw.git
   cd PC-Agent-Claw
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Initialize databases:
   ```bash
   python core/persistent_memory.py
   python core/long_term_memory.py
   ```

## Configuration

1. Set up API credentials:
   ```python
   from core.api_access import APIAccessSystem
   api = APIAccessSystem()
   api.set_openai_key('your-key')
   api.set_manus_key('your-key')
   ```

2. Configure dual GPU (if available):
   ```python
   from dual_gpu_manager import DualGPUManager
   gpu = DualGPUManager()
   gpu.test_connection()
   ```

## Running

1. Start the autonomous work queue:
   ```bash
   python core/autonomous_work_queue.py
   ```

2. Run tests:
   ```bash
   python testing/test_framework.py
   ```

3. Start monitoring:
   ```bash
   python monitoring/performance_monitor.py
   ```

## Troubleshooting

- **Database locked**: Ensure only one instance is running
- **Import errors**: Check Python path and dependencies
- **GPU errors**: Verify CUDA installation and driver version

## Maintenance

- Backup databases regularly (*.db files)
- Monitor error logs in memory.db decisions table
- Update dependencies: `pip install --upgrade -r requirements.txt`
"""

        deployment_path = self.docs_dir / "DEPLOYMENT.md"
        deployment_path.write_text(doc)

        return doc

    def list_documentation(self) -> List[str]:
        """List all documentation files"""
        return [str(f.relative_to(self.docs_dir)) for f in self.docs_dir.glob("*.md")]


if __name__ == '__main__':
    # Test the system
    manager = DocumentationManager()

    print("Documentation Manager ready!")

    # Generate overview
    print("\nGenerating system overview...")
    manager.generate_system_overview()

    # Generate deployment guide
    print("Generating deployment guide...")
    manager.generate_deployment_guide()

    # Generate changelog
    print("Generating changelog...")
    changelog = manager.generate_changelog()

    # List docs
    docs = manager.list_documentation()
    print(f"\nDocumentation files: {len(docs)}")
    for doc in docs:
        print(f"  - {doc}")
