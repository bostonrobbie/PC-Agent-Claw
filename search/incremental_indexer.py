"""
Incremental Update System with File Watching

Priority 1.2: Watch workspace directory for changes and only re-index changed files.
Provides continuous intelligence - always up to date without manual re-indexing.

Features:
- File system monitoring with watchdog library (with fallback)
- File hash tracking to detect real changes
- Batch updates with change debouncing
- Incremental indexing (only changed files)
- Non-blocking background watcher
- Configurable watch patterns
- Change event queue
- Integration with SemanticCodeSearch
- Database for tracking file states (hashes)

Target: Continuous intelligence - always up to date without manual re-indexing

Author: AI Self-Improvement System
Created: 2026-02-03
"""

import sqlite3
import os
import hashlib
import time
import threading
import queue
import json
from datetime import datetime
from typing import Dict, List, Optional, Set, Callable
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import fnmatch
import logging

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileSystemEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FileEventType(Enum):
    """File change event types"""
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    MOVED = "moved"


@dataclass
class FileChangeEvent:
    """Represents a file change event"""
    event_type: FileEventType
    file_path: str
    timestamp: float
    old_path: Optional[str] = None  # For move events
    file_hash: Optional[str] = None  # Hash of new content


class FileStateTracker:
    """Tracks file states and detects changes using hashes"""

    def __init__(self, db_path: str = "file_state_tracker.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize file state database"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # File states table
        c.execute('''
            CREATE TABLE IF NOT EXISTS file_states (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE NOT NULL,
                content_hash TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                last_modified_time REAL NOT NULL,
                indexed_at TEXT DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'tracked'
            )
        ''')

        # Indexing history
        c.execute('''
            CREATE TABLE IF NOT EXISTS indexing_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                event_type TEXT NOT NULL,
                indexed_at TEXT DEFAULT CURRENT_TIMESTAMP,
                duration_ms FLOAT DEFAULT 0,
                success BOOLEAN DEFAULT 1
            )
        ''')

        # Create indexes
        c.execute('CREATE INDEX IF NOT EXISTS idx_file_path ON file_states(file_path)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_indexed_at ON file_states(indexed_at)')

        conn.commit()
        conn.close()

    def get_file_hash(self, file_path: str) -> Optional[str]:
        """Calculate hash of file content"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return None

    def track_file(self, file_path: str) -> bool:
        """Track a file's current state"""
        try:
            if not os.path.exists(file_path):
                return False

            file_hash = self.get_file_hash(file_path)
            file_size = os.path.getsize(file_path)
            mtime = os.path.getmtime(file_path)

            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()

            c.execute('''
                INSERT OR REPLACE INTO file_states
                (file_path, content_hash, file_size, last_modified_time, status)
                VALUES (?, ?, ?, ?, 'tracked')
            ''', (file_path, file_hash, file_size, mtime))

            conn.commit()
            conn.close()
            return True

        except Exception:
            return False

    def get_tracked_file_state(self, file_path: str) -> Optional[Dict]:
        """Get tracked state of a file"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute('''
            SELECT file_path, content_hash, file_size, last_modified_time, indexed_at
            FROM file_states
            WHERE file_path = ?
        ''', (file_path,))

        row = c.fetchone()
        conn.close()

        if row:
            return {
                'file_path': row[0],
                'content_hash': row[1],
                'file_size': row[2],
                'last_modified_time': row[3],
                'indexed_at': row[4]
            }
        return None

    def detect_change(self, file_path: str) -> bool:
        """Detect if file has actually changed"""
        try:
            if not os.path.exists(file_path):
                return True  # Deleted file is a change

            current_hash = self.get_file_hash(file_path)
            tracked_state = self.get_tracked_file_state(file_path)

            if not tracked_state:
                return True  # New file

            return current_hash != tracked_state['content_hash']

        except Exception:
            return True

    def mark_indexed(self, file_path: str, success: bool = True, duration_ms: float = 0):
        """Mark file as indexed"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute('''
            INSERT INTO indexing_history (file_path, event_type, duration_ms, success)
            VALUES (?, 'index', ?, ?)
        ''', (file_path, duration_ms, success))

        conn.commit()
        conn.close()

    def untrack_file(self, file_path: str):
        """Stop tracking a file (when deleted)"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute('DELETE FROM file_states WHERE file_path = ?', (file_path,))

        conn.commit()
        conn.close()

    def get_all_tracked_files(self) -> List[str]:
        """Get all currently tracked files"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute('SELECT file_path FROM file_states WHERE status = "tracked"')
        files = [row[0] for row in c.fetchall()]

        conn.close()
        return files


class ChangeEventQueue:
    """Thread-safe queue for file change events"""

    def __init__(self, max_size: int = 1000):
        self.queue = queue.Queue(maxsize=max_size)
        self.lock = threading.Lock()

    def put(self, event: FileChangeEvent, block: bool = True, timeout: float = None):
        """Add event to queue"""
        try:
            self.queue.put(event, block=block, timeout=timeout)
        except queue.Full:
            pass  # Drop event if queue is full

    def get(self, block: bool = True, timeout: float = None) -> Optional[FileChangeEvent]:
        """Get event from queue"""
        try:
            return self.queue.get(block=block, timeout=timeout)
        except queue.Empty:
            return None

    def get_batch(self, max_size: int = 100, timeout: float = 0.1) -> List[FileChangeEvent]:
        """Get batch of events (for debouncing)"""
        events = []
        start_time = time.time()

        while len(events) < max_size:
            elapsed = time.time() - start_time
            remaining = timeout - elapsed

            if remaining <= 0:
                break

            event = self.get(timeout=remaining)
            if event:
                events.append(event)
            else:
                break

        return events

    def qsize(self) -> int:
        """Get approximate queue size"""
        return self.queue.qsize()

    def empty(self) -> bool:
        """Check if queue is empty"""
        return self.queue.empty()


class CodeFileEventHandler(FileSystemEventHandler):
    """Handles file system events for code files (watchdog integration)"""

    def __init__(self, indexer: 'IncrementalIndexer'):
        self.indexer = indexer
        self.code_extensions = {
            '.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.cpp', '.c', '.h',
            '.cs', '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.scala',
            '.sql', '.sh', '.bash', '.ps1', '.r', '.m', '.mm'
        }

    def _is_code_file(self, path: str) -> bool:
        """Check if file is a code file we should index"""
        ext = os.path.splitext(path)[1].lower()
        return ext in self.code_extensions

    def _should_ignore(self, path: str) -> bool:
        """Check if path should be ignored"""
        ignore_patterns = [
            'node_modules', '.git', '__pycache__', '.venv', 'venv',
            'build', 'dist', '.pytest_cache', '.mypy_cache', '.db'
        ]
        return any(pattern in path for pattern in ignore_patterns)

    def on_created(self, event: FileSystemEvent):
        """Handle file creation"""
        if not event.is_directory and self._is_code_file(event.src_path):
            if not self._should_ignore(event.src_path):
                logger.info(f"File created: {event.src_path}")
                self.indexer.queue_change(event.src_path, FileEventType.CREATED)

    def on_modified(self, event: FileSystemEvent):
        """Handle file modification"""
        if not event.is_directory and self._is_code_file(event.src_path):
            if not self._should_ignore(event.src_path):
                logger.info(f"File modified: {event.src_path}")
                self.indexer.queue_change(event.src_path, FileEventType.MODIFIED)

    def on_deleted(self, event: FileSystemEvent):
        """Handle file deletion"""
        if not event.is_directory and self._is_code_file(event.src_path):
            if not self._should_ignore(event.src_path):
                logger.info(f"File deleted: {event.src_path}")
                self.indexer.queue_change(event.src_path, FileEventType.DELETED)


class FileWatcher:
    """Pure Python file watcher (fallback when watchdog unavailable)"""

    def __init__(self, watch_root: str):
        self.watch_root = os.path.abspath(watch_root)
        self.tracked_files: Dict[str, float] = {}  # file_path -> last_mtime
        self.running = False

    def should_skip_directory(self, dir_path: str) -> bool:
        """Check if directory should be skipped"""
        skip_dirs = {
            'node_modules', '.git', '__pycache__', '.venv', 'venv',
            'build', 'dist', '.pytest_cache', '.mypy_cache', '.idea',
            '.vscode', 'target', 'bin', 'obj', '.env'
        }
        return any(skip_dir in dir_path for skip_dir in skip_dirs)

    def should_index_file(self, file_path: str) -> bool:
        """Check if file should be indexed"""
        code_extensions = {
            '.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.cpp', '.c', '.h',
            '.cs', '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.scala',
            '.sql', '.sh', '.bash', '.ps1', '.r', '.m', '.mm'
        }
        ext = os.path.splitext(file_path)[1].lower()
        return ext in code_extensions

    def scan_directory(self) -> Dict[str, float]:
        """Scan directory for files and their mtimes"""
        current_files = {}

        try:
            for root, dirs, files in os.walk(self.watch_root):
                dirs[:] = [d for d in dirs if not self.should_skip_directory(
                    os.path.join(root, d)
                )]

                for file in files:
                    file_path = os.path.join(root, file)

                    if self.should_index_file(file_path):
                        try:
                            mtime = os.path.getmtime(file_path)
                            current_files[file_path] = mtime
                        except Exception:
                            pass

        except Exception:
            pass

        return current_files

    def detect_changes(self) -> List[FileChangeEvent]:
        """Detect changes by comparing current state with tracked state"""
        events = []
        current_files = self.scan_directory()

        # Detect modifications and creations
        for file_path, mtime in current_files.items():
            if file_path not in self.tracked_files:
                # New file
                events.append(FileChangeEvent(
                    event_type=FileEventType.CREATED,
                    file_path=file_path,
                    timestamp=time.time()
                ))
            elif self.tracked_files[file_path] != mtime:
                # Modified file
                events.append(FileChangeEvent(
                    event_type=FileEventType.MODIFIED,
                    file_path=file_path,
                    timestamp=time.time()
                ))

        # Detect deletions
        for file_path in list(self.tracked_files.keys()):
            if file_path not in current_files:
                events.append(FileChangeEvent(
                    event_type=FileEventType.DELETED,
                    file_path=file_path,
                    timestamp=time.time()
                ))

        # Update tracked files
        self.tracked_files = current_files

        return events


class IncrementalIndexer:
    """
    Incremental indexing system with real-time file monitoring.

    Features:
    - Monitors directory for file changes
    - Only re-indexes changed files
    - Delta updates to database
    - Background processing threads
    - Efficient batching
    - File hash tracking
    - Change debouncing
    """

    def __init__(self,
                 semantic_search_db: str,
                 project_name: str = "PC-Agent-Claw",
                 root_path: str = ".",
                 batch_size: int = 50,
                 batch_interval: float = 2.0,
                 debounce_interval: float = 1.0):
        """
        Initialize incremental indexer.

        Args:
            semantic_search_db: Path to semantic search database
            project_name: Name of the project to monitor
            root_path: Root directory to monitor
            batch_size: Number of changes to batch before processing
            batch_interval: Seconds to wait before processing partial batch
            debounce_interval: Seconds to debounce rapid changes
        """
        self.semantic_search_db = semantic_search_db
        self.project_name = project_name
        self.root_path = os.path.abspath(root_path)
        self.batch_size = batch_size
        self.batch_interval = batch_interval
        self.debounce_interval = debounce_interval

        # File watching
        self.file_watcher = FileWatcher(self.root_path)
        self.event_queue = ChangeEventQueue()

        # State
        self.running = False
        self.watch_thread: Optional[threading.Thread] = None
        self.process_thread: Optional[threading.Thread] = None
        self.observer: Optional[Observer] = None

        # File state tracking
        self.state_tracker = FileStateTracker(
            os.path.join(os.path.dirname(self.root_path), "file_state_tracker.db")
        )

        # Statistics
        self.stats = {
            'files_created': 0,
            'files_modified': 0,
            'files_deleted': 0,
            'batches_processed': 0,
            'total_events': 0,
            'last_update': None,
            'start_time': datetime.now().isoformat()
        }

        # Callbacks
        self.on_batch_start: Optional[Callable] = None
        self.on_batch_complete: Optional[Callable] = None
        self.on_error: Optional[Callable] = None

    def queue_change(self, file_path: str, event_type: FileEventType):
        """Queue a file change for processing"""
        # Only queue if actual change detected
        if event_type != FileEventType.DELETED:
            if not self.state_tracker.detect_change(file_path):
                logger.debug(f"No real change for {file_path}, skipping")
                return

        event = FileChangeEvent(
            event_type=event_type,
            file_path=file_path,
            timestamp=time.time()
        )

        self.event_queue.put(event)
        self.stats['total_events'] += 1
        logger.info(f"Queued {event_type.value} for {file_path}")

    def _process_changes(self):
        """Process queued changes in batch"""
        if self.event_queue.empty():
            return

        events = self.event_queue.get_batch(
            max_size=self.batch_size,
            timeout=0.5
        )

        if not events:
            return

        if self.on_batch_start:
            self.on_batch_start(len(events))

        logger.info(f"Processing batch of {len(events)} changes")
        start_time = time.time()

        try:
            conn = sqlite3.connect(self.semantic_search_db)

            # Get project ID
            c = conn.cursor()
            c.execute('SELECT id FROM projects WHERE name = ?', (self.project_name,))
            result = c.fetchone()

            if not result:
                logger.warning(f"Project {self.project_name} not found, creating...")
                c.execute('''
                    INSERT INTO projects (name, root_path)
                    VALUES (?, ?)
                ''', (self.project_name, self.root_path))
                conn.commit()
                project_id = c.lastrowid
            else:
                project_id = result[0]

            # Process each change
            for event in events:
                try:
                    if event.event_type == FileEventType.DELETED:
                        self._handle_delete(conn, event.file_path)
                        self.stats['files_deleted'] += 1
                    else:
                        self._handle_create_or_modify(conn, project_id, event)
                        if event.event_type == FileEventType.CREATED:
                            self.stats['files_created'] += 1
                        else:
                            self.stats['files_modified'] += 1
                except Exception as e:
                    logger.error(f"Error processing {event.file_path}: {e}")
                    if self.on_error:
                        self.on_error(str(e))

            conn.close()

            # Update statistics
            self.stats['batches_processed'] += 1
            self.stats['last_update'] = datetime.now().isoformat()

            elapsed = time.time() - start_time
            logger.info(f"Batch processed in {elapsed:.2f}s")

            if self.on_batch_complete:
                self.on_batch_complete(self.stats.copy())

        except Exception as e:
            logger.error(f"Error processing batch: {e}")
            if self.on_error:
                self.on_error(str(e))

    def _handle_delete(self, conn: sqlite3.Connection, file_path: str):
        """Handle file deletion"""
        c = conn.cursor()

        # Delete chunks for this file
        c.execute('''
            DELETE FROM semantic_index
            WHERE chunk_id IN (
                SELECT id FROM code_chunks WHERE file_path = ?
            )
        ''', (file_path,))

        c.execute('DELETE FROM code_chunks WHERE file_path = ?', (file_path,))
        deleted_count = c.rowcount

        conn.commit()

        # Untrack file
        self.state_tracker.untrack_file(file_path)

        logger.info(f"Deleted {deleted_count} chunks for {file_path}")

    def _handle_create_or_modify(self, conn: sqlite3.Connection,
                                  project_id: int, event: FileChangeEvent):
        """Handle file creation or modification"""
        c = conn.cursor()

        # Delete existing chunks for this file
        c.execute('''
            DELETE FROM semantic_index
            WHERE chunk_id IN (
                SELECT id FROM code_chunks WHERE file_path = ?
            )
        ''', (event.file_path,))

        c.execute('DELETE FROM code_chunks WHERE file_path = ?', (event.file_path,))
        conn.commit()

        # Parse and index file (using SemanticCodeSearch methods)
        try:
            from search.semantic_search import SemanticCodeSearch
            search = SemanticCodeSearch(self.semantic_search_db)
            chunks = search._parse_file(event.file_path, project_id)

            chunks_added = 0
            for chunk in chunks:
                chunk_id = search._add_chunk(conn, chunk)
                if chunk_id:
                    search._index_chunk(
                        conn, chunk_id, chunk.content, chunk.semantic_tags
                    )
                    chunks_added += 1

            logger.info(f"Indexed {chunks_added} chunks for {event.file_path}")

        except Exception as e:
            logger.error(f"Error parsing {event.file_path}: {e}")

        # Track file
        self.state_tracker.track_file(event.file_path)

    def _watch_loop(self):
        """Background thread: monitor file system"""
        logger.info("File watch loop started")
        self.file_watcher.running = True

        try:
            self.file_watcher.tracked_files = self.file_watcher.scan_directory()

            while self.running:
                try:
                    # Scan every second
                    events = self.file_watcher.detect_changes()

                    for event in events:
                        self.queue_change(event.file_path, event.event_type)

                    time.sleep(1)

                except Exception as e:
                    logger.error(f"Error in watch loop: {e}")
                    time.sleep(2)

        finally:
            self.file_watcher.running = False
            logger.info("File watch loop stopped")

    def _process_loop(self):
        """Background thread: process queued changes"""
        logger.info("Process loop started")
        last_process_time = 0

        try:
            while self.running:
                try:
                    current_time = time.time()

                    # Process if debounce interval passed or batch size reached
                    if (current_time - last_process_time >= self.debounce_interval or
                            self.event_queue.qsize() >= self.batch_size):

                        self._process_changes()
                        last_process_time = current_time

                    time.sleep(0.5)

                except Exception as e:
                    logger.error(f"Error in process loop: {e}")
                    time.sleep(1)

        finally:
            # Process remaining changes
            self._process_changes()
            logger.info("Process loop stopped")

    def start_monitoring(self) -> bool:
        """Start monitoring file system changes"""
        if self.running:
            logger.warning("Monitoring already started")
            return False

        self.running = True

        # Start watch thread
        self.watch_thread = threading.Thread(
            target=self._watch_loop,
            daemon=True,
            name="FileWatchThread"
        )
        self.watch_thread.start()

        # Start process thread
        self.process_thread = threading.Thread(
            target=self._process_loop,
            daemon=True,
            name="IndexProcessThread"
        )
        self.process_thread.start()

        # Try to start watchdog observer if available
        if WATCHDOG_AVAILABLE:
            try:
                event_handler = CodeFileEventHandler(self)
                self.observer = Observer()
                self.observer.schedule(event_handler, self.root_path, recursive=True)
                self.observer.start()
                logger.info("Watchdog observer started")
            except Exception as e:
                logger.warning(f"Could not start watchdog: {e}")

        logger.info(f"Monitoring started for {self.root_path}")
        return True

    def stop_monitoring(self):
        """Stop monitoring file system changes"""
        if not self.running:
            logger.warning("Monitoring not started")
            return

        self.running = False

        # Stop watchdog observer
        if self.observer:
            try:
                self.observer.stop()
                self.observer.join()
            except Exception:
                pass

        # Wait for threads
        if self.watch_thread:
            self.watch_thread.join(timeout=5)

        if self.process_thread:
            self.process_thread.join(timeout=5)

        logger.info("Monitoring stopped")

    def get_stats(self) -> Dict:
        """Get indexer statistics"""
        return {
            **self.stats,
            'queue_size': self.event_queue.qsize(),
            'running': self.running,
            'tracked_files': len(self.state_tracker.get_all_tracked_files())
        }

    def force_full_rescan(self):
        """Force a full rescan of the watch directory"""
        logger.info("Force full rescan initiated")
        self.file_watcher.tracked_files = {}

        events = self.file_watcher.detect_changes()
        for event in events:
            self.queue_change(event.file_path, event.event_type)

        logger.info(f"Queued {len(events)} files for rescanning")

    def get_indexing_history(self, limit: int = 50) -> List[Dict]:
        """Get recent indexing history"""
        return self.state_tracker.get_indexing_history(limit)


# Testing and example usage
def run_tests():
    """Run comprehensive tests"""
    print("Testing Incremental Indexer System...")

    # Test 1: File State Tracker
    print("\n1. Testing File State Tracker...")
    test_db = "test_state_tracker.db"
    if os.path.exists(test_db):
        os.remove(test_db)

    tracker = FileStateTracker(test_db)

    test_file = "test_incremental.txt"
    with open(test_file, 'w') as f:
        f.write("test content")

    try:
        assert tracker.track_file(test_file), "Failed to track file"
        assert not tracker.detect_change(test_file), "Should not detect change immediately"

        # Modify file
        time.sleep(0.1)
        with open(test_file, 'w') as f:
            f.write("modified content")

        assert tracker.detect_change(test_file), "Should detect modification"
        print("   [PASS] File State Tracker")

    finally:
        if os.path.exists(test_file):
            os.remove(test_file)
        if os.path.exists(test_db):
            os.remove(test_db)

    # Test 2: Change Event Queue
    print("\n2. Testing Change Event Queue...")
    event_queue = ChangeEventQueue()

    event = FileChangeEvent(
        event_type=FileEventType.CREATED,
        file_path="test.py",
        timestamp=time.time()
    )

    event_queue.put(event)
    assert not event_queue.empty(), "Queue should not be empty"
    assert event_queue.qsize() == 1, "Queue size should be 1"

    retrieved = event_queue.get()
    assert retrieved.file_path == "test.py", "Should retrieve correct event"
    print("   [PASS] Change Event Queue")

    # Test 3: File Watcher
    print("\n3. Testing File Watcher...")
    watcher = FileWatcher(".")
    assert watcher.should_index_file("test.py"), "Should index Python file"
    assert not watcher.should_index_file("test.txt"), "Should not index text file"
    print("   [PASS] File Watcher")

    # Test 4: File Event Type Enum
    print("\n4. Testing File Event Types...")
    assert FileEventType.CREATED.value == "created"
    assert FileEventType.MODIFIED.value == "modified"
    assert FileEventType.DELETED.value == "deleted"
    print("   [PASS] File Event Types")

    print("\n[SUCCESS] All tests passed!")
    print("\nTo use IncrementalIndexer:")
    print("  indexer = IncrementalIndexer(")
    print("      semantic_search_db='semantic_code_search.db',")
    print("      project_name='Your-Project',")
    print("      root_path='/path/to/project'")
    print("  )")
    print("  indexer.start_monitoring()")


if __name__ == "__main__":
    run_tests()
