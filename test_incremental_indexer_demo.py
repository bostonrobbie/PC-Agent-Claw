"""
Incremental Indexer - Comprehensive Usage Demo

Demonstrates the Priority 1.2 Incremental Update System with File Watching.

Features:
- Real-time file monitoring
- Incremental indexing (only changed files)
- File hash tracking
- Batch processing with debouncing
- Non-blocking background operations
- Integration with SemanticCodeSearch

Author: AI Self-Improvement System
Created: 2026-02-03
"""

import os
import sys
import time
from pathlib import Path

# Add workspace to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from search.incremental_indexer import (
    IncrementalIndexer,
    FileStateTracker,
    FileEventType,
    ChangeEventQueue,
    FileWatcher
)


def demo_file_state_tracking():
    """Demonstrate file state tracking with hashes"""
    print("\n" + "="*60)
    print("DEMO 1: File State Tracking")
    print("="*60)

    tracker = FileStateTracker("demo_state_tracker.db")

    # Create a test file
    test_file = "demo_file.py"
    print(f"\n1. Creating file: {test_file}")
    with open(test_file, 'w') as f:
        f.write("def hello():\n    print('Hello')\n")

    # Track it
    print(f"2. Tracking file...")
    tracker.track_file(test_file)

    # Check state
    state = tracker.get_tracked_file_state(test_file)
    print(f"   - Hash: {state['content_hash'][:16]}...")
    print(f"   - Size: {state['file_size']} bytes")

    # No change detected
    print(f"3. Checking for changes (should be no change)...")
    changed = tracker.detect_change(test_file)
    print(f"   - Changed: {changed}")

    # Modify file
    print(f"4. Modifying file...")
    time.sleep(0.1)
    with open(test_file, 'w') as f:
        f.write("def hello():\n    print('Hello World')\n")

    # Change detected
    print(f"5. Checking for changes (should detect change)...")
    changed = tracker.detect_change(test_file)
    print(f"   - Changed: {changed}")

    # Update tracking
    print(f"6. Updating tracked state...")
    tracker.track_file(test_file)

    # Cleanup
    os.remove(test_file)
    if os.path.exists("demo_state_tracker.db"):
        os.remove("demo_state_tracker.db")
    print("\n   [DEMO COMPLETE]")


def demo_event_queue():
    """Demonstrate change event queue with batching"""
    print("\n" + "="*60)
    print("DEMO 2: Change Event Queue & Batching")
    print("="*60)

    queue = ChangeEventQueue(max_size=1000)

    print("\n1. Creating and queuing events...")
    events_data = [
        ("file1.py", FileEventType.CREATED),
        ("file2.py", FileEventType.MODIFIED),
        ("file3.py", FileEventType.MODIFIED),
        ("file4.py", FileEventType.CREATED),
        ("file5.py", FileEventType.DELETED),
    ]

    for file_path, event_type in events_data:
        from search.incremental_indexer import FileChangeEvent
        event = FileChangeEvent(
            event_type=event_type,
            file_path=file_path,
            timestamp=time.time()
        )
        queue.put(event)
        print(f"   + Queued: {event_type.value:10} {file_path}")

    print(f"\n2. Queue statistics:")
    print(f"   - Total events: {queue.qsize()}")

    print(f"\n3. Getting batch of events...")
    batch = queue.get_batch(max_size=3, timeout=0.5)
    print(f"   - Batch size: {len(batch)}")
    for event in batch:
        print(f"     * {event.event_type.value}: {event.file_path}")

    print(f"\n4. Remaining in queue: {queue.qsize()}")
    print("\n   [DEMO COMPLETE]")


def demo_file_watcher():
    """Demonstrate file watcher pattern matching"""
    print("\n" + "="*60)
    print("DEMO 3: File Watcher & Pattern Matching")
    print("="*60)

    watcher = FileWatcher(".")

    print("\n1. Testing file indexing rules...")
    test_cases = [
        ("example.py", True),
        ("example.js", True),
        ("example.ts", True),
        ("example.java", True),
        ("example.txt", False),
        ("example.pdf", False),
        ("example.md", False),
        ("Makefile", False),
    ]

    for file_name, should_index in test_cases:
        result = watcher.should_index_file(file_name)
        status = "OK" if result == should_index else "FAIL"
        print(f"   {status:4} {file_name:20} -> index={result}")

    print("\n2. Testing directory skip patterns...")
    skip_dirs = [
        "node_modules/package.json",
        ".git/config",
        "__pycache__/module.cpython.pyc",
        ".venv/bin/python",
        "src/main.py",  # Should NOT skip
    ]

    for dir_path in skip_dirs:
        result = watcher.should_skip_directory(dir_path)
        status = "SKIP" if result else "INDEX"
        print(f"   {status:5} {dir_path}")

    print("\n   [DEMO COMPLETE]")


def demo_incremental_indexer_stats():
    """Demonstrate IncrementalIndexer statistics tracking"""
    print("\n" + "="*60)
    print("DEMO 4: Incremental Indexer Statistics")
    print("="*60)

    # Create a test database
    test_db = "test_semantic_search.db"

    # Initialize database
    import sqlite3
    conn = sqlite3.connect(test_db)
    c = conn.cursor()

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

    c.execute('''
        CREATE TABLE IF NOT EXISTS semantic_index (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT NOT NULL,
            chunk_id INTEGER NOT NULL,
            weight REAL DEFAULT 1.0,
            FOREIGN KEY (chunk_id) REFERENCES code_chunks (id)
        )
    ''')

    conn.commit()
    conn.close()

    print("\n1. Creating incremental indexer...")
    indexer = IncrementalIndexer(
        semantic_search_db=test_db,
        project_name="Demo-Project",
        root_path=".",
        batch_size=10,
        batch_interval=1.0
    )

    print(f"\n2. Initial statistics:")
    stats = indexer.get_stats()
    for key, value in stats.items():
        print(f"   - {key}: {value}")

    print(f"\n3. Simulating file changes...")

    # Simulate some events
    from search.incremental_indexer import FileChangeEvent
    for i in range(5):
        event = FileChangeEvent(
            event_type=FileEventType.CREATED,
            file_path=f"file_{i}.py",
            timestamp=time.time()
        )
        indexer.event_queue.put(event)

    print(f"   - Queued 5 CREATED events")

    print(f"\n4. Updated statistics:")
    stats = indexer.get_stats()
    print(f"   - Queue size: {stats['queue_size']}")
    print(f"   - Total events: {stats['total_events']}")
    print(f"   - Batches processed: {stats['batches_processed']}")

    # Cleanup
    if os.path.exists(test_db):
        os.remove(test_db)

    print("\n   [DEMO COMPLETE]")


def demo_monitoring_workflow():
    """Demonstrate typical monitoring workflow"""
    print("\n" + "="*60)
    print("DEMO 5: Typical Monitoring Workflow")
    print("="*60)

    print("""
    TYPICAL WORKFLOW FOR USING INCREMENTALINDEXER:

    1. INITIALIZE THE INDEXER
    ---------------------------------------------------
    indexer = IncrementalIndexer(
        semantic_search_db='semantic_code_search.db',
        project_name='My-Project',
        root_path='/path/to/project',
        batch_size=50,
        batch_interval=2.0,
        debounce_interval=1.0
    )

    2. SET UP CALLBACKS (OPTIONAL)
    ---------------------------------------------------
    def on_batch_start(count):
        print(f"Processing {count} changes...")

    def on_batch_complete(stats):
        print(f"Processed: {stats['files_created']} created")
        print(f"Processed: {stats['files_modified']} modified")
        print(f"Processed: {stats['files_deleted']} deleted")

    def on_error(error):
        print(f"Error: {error}")

    indexer.on_batch_start = on_batch_start
    indexer.on_batch_complete = on_batch_complete
    indexer.on_error = on_error

    3. START MONITORING
    ---------------------------------------------------
    success = indexer.start_monitoring()
    if success:
        print("Monitoring started!")

    4. MONITOR IN REAL-TIME
    ---------------------------------------------------
    while True:
        stats = indexer.get_stats()
        print(f"Queue: {stats['queue_size']}, "
              f"Created: {stats['files_created']}, "
              f"Modified: {stats['files_modified']}")
        time.sleep(5)

    5. STOP MONITORING WHEN DONE
    ---------------------------------------------------
    indexer.stop_monitoring()

    KEY FEATURES:
    ---------------------------------------------------
    - Non-blocking: Runs in background threads
    - Efficient: Only re-indexes changed files
    - Reliable: File hash tracking prevents false positives
    - Batched: Groups changes for efficient processing
    - Debounced: Avoids rapid re-indexing
    - Integrated: Works with SemanticCodeSearch

    CONFIGURATION OPTIONS:
    ---------------------------------------------------
    - batch_size: Max changes per batch (default: 50)
    - batch_interval: Max wait between batches (default: 2.0s)
    - debounce_interval: Wait time before processing (default: 1.0s)
    - semantic_search_db: Path to index database
    - project_name: Project identifier
    - root_path: Directory to monitor
    """)

    print("\n   [DEMO COMPLETE]")


def print_architecture():
    """Print system architecture diagram"""
    print("\n" + "="*60)
    print("ARCHITECTURE: Incremental Update System")
    print("="*60)

    print("""
    SYSTEM COMPONENTS:
    ---------------------------------------------------
    1. Incremental Indexer System
       - Monitors file changes
       - Routes to appropriate handlers
       - Manages lifecycle

    2. File Monitoring (Dual Mode)
       - File Watcher (Pure Python) - Always available
       - Watchdog Observer (Optional) - When installed
       - Automatic fallback mechanism

    3. State Tracking
       - File State Tracker - Hash-based change detection
       - MD5 hashing for accuracy
       - Persistent database

    4. Event Processing
       - FileChangeEvent - Immutable change representation
       - ChangeEventQueue - Thread-safe, batching
       - Debouncing & batching for efficiency

    5. Batch Processing Thread
       - Collects changes from queue
       - Debounces rapid changes
       - Processes in batches
       - Calls callbacks on completion

    6. Integration Layer
       - Reads from SemanticCodeSearch
       - Parses files using existing code
       - Updates database with new/modified chunks
       - Removes chunks for deleted files

    DATA FLOW:
    ---------------------------------------------------
    File System Changes
        |
        v
    Watcher / Watchdog
        |
        v
    FileChangeEvent Objects
        |
        v
    ChangeEventQueue (Batching)
        |
        v
    Batch Processor Thread
        |
        v
    State Change Handler
        |
        v
    SemanticCodeSearch Indexing
        |
        v
    Database Update
        |
        v
    Statistics & Callbacks
    """)


def main():
    """Run all demos"""
    print("""
    ============================================================
    Incremental Indexer - Comprehensive Demo Suite
    Priority 1.2: File Watching & Incremental Updates
    ============================================================
    """)

    try:
        # Run all demos
        demo_file_state_tracking()
        demo_event_queue()
        demo_file_watcher()
        demo_incremental_indexer_stats()
        demo_monitoring_workflow()
        print_architecture()

        print("\n" + "="*60)
        print("ALL DEMOS COMPLETED SUCCESSFULLY")
        print("="*60)

        print("""
        NEXT STEPS:
        ---------------------------------------------------
        1. Review the IncrementalIndexer implementation:
           search/incremental_indexer.py

        2. Integrate with your application:
           from search.incremental_indexer import IncrementalIndexer
           indexer = IncrementalIndexer(...)
           indexer.start_monitoring()

        3. Monitor for continuous updates:
           stats = indexer.get_stats()

        4. Handle callbacks for batch completions:
           indexer.on_batch_complete = your_callback

        5. Install watchdog for better performance:
           pip install watchdog

        FEATURES IMPLEMENTED:
        ---------------------------------------------------
        [X] File system monitoring (pure Python + watchdog)
        [X] File hash tracking (MD5 for change detection)
        [X] Batch processing (efficient updates)
        [X] Change debouncing (avoid rapid re-indexing)
        [X] Thread-safe event queue
        [X] Non-blocking background threads
        [X] Integration with SemanticCodeSearch
        [X] Comprehensive error handling
        [X] Statistics tracking
        [X] File state persistence
        [X] Configurable patterns
        [X] Indexing history

        TARGET: Continuous Intelligence
        ---------------------------------------------------
        Always up-to-date code index without manual re-indexing.
        """)

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
