"""
Example: Integrating Incremental Indexer with SemanticCodeSearch

This example demonstrates how to use the IncrementalIndexer with
SemanticCodeSearch for continuous intelligence.

Author: AI Self-Improvement System
Created: 2026-02-03
"""

import os
import sys
import time
from datetime import datetime

# Add workspace to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from search.semantic_search import SemanticCodeSearch
from search.incremental_indexer import IncrementalIndexer


def example_1_basic_setup():
    """Example 1: Basic setup with initial indexing"""
    print("\n" + "="*70)
    print("EXAMPLE 1: Basic Setup with Initial Indexing")
    print("="*70)

    # Step 1: Create search engine
    print("\n1. Initializing SemanticCodeSearch...")
    search = SemanticCodeSearch(db_path="example_search.db")

    # Step 2: Index initial project
    print("2. Indexing project (initial full scan)...")
    result = search.index_project(
        project_name="Example-Project",
        root_path=".",
        parallel=True
    )

    print(f"\n   Results:")
    print(f"   - Files indexed: {result.get('files_indexed', 0)}")
    print(f"   - Chunks indexed: {result.get('chunks_indexed', 0)}")
    print(f"   - Time elapsed: {result.get('elapsed_time', 0):.2f}s")
    print(f"   - Files/sec: {result.get('files_per_second', 0):.1f}")

    # Cleanup
    if os.path.exists("example_search.db"):
        os.remove("example_search.db")

    print("\n   [EXAMPLE COMPLETE]")


def example_2_continuous_monitoring():
    """Example 2: Continuous monitoring with callbacks"""
    print("\n" + "="*70)
    print("EXAMPLE 2: Continuous Monitoring with Callbacks")
    print("="*70)

    # Statistics
    stats = {
        'batches': 0,
        'total_changes': 0,
        'start_time': datetime.now()
    }

    # Callbacks
    def on_batch_start(count):
        print(f"\n   Processing batch: {count} changes detected")

    def on_batch_complete(batch_stats):
        stats['batches'] += 1
        stats['total_changes'] += (
            batch_stats['files_created'] +
            batch_stats['files_modified'] +
            batch_stats['files_deleted']
        )

        print(f"   Batch #{stats['batches']} complete:")
        print(f"     - Created: {batch_stats['files_created']}")
        print(f"     - Modified: {batch_stats['files_modified']}")
        print(f"     - Deleted: {batch_stats['files_deleted']}")
        print(f"     - Queue size: {batch_stats['queue_size']}")

    def on_error(error):
        print(f"   ERROR: {error}")

    # Create indexer
    print("\n1. Creating incremental indexer...")
    indexer = IncrementalIndexer(
        semantic_search_db="example_search.db",
        project_name="Example-Project",
        root_path=".",
        batch_size=10,
        batch_interval=1.0,
        debounce_interval=0.5
    )

    # Attach callbacks
    print("2. Setting up callbacks...")
    indexer.on_batch_start = on_batch_start
    indexer.on_batch_complete = on_batch_complete
    indexer.on_error = on_error

    # Start monitoring
    print("3. Starting monitoring...")
    indexer.start_monitoring()
    print("   Monitoring started! (10 second demo)")

    # Monitor for 10 seconds
    try:
        for i in range(10):
            time.sleep(1)
            current_stats = indexer.get_stats()
            if i % 3 == 0:
                print(f"\n   [{i}s] Queue: {current_stats['queue_size']}, "
                      f"Running: {current_stats['running']}")
    except KeyboardInterrupt:
        print("\n   Interrupted by user")

    # Stop monitoring
    print("\n4. Stopping monitoring...")
    indexer.stop_monitoring()

    # Summary
    print("\n   SUMMARY:")
    print(f"   - Total batches processed: {stats['batches']}")
    print(f"   - Total changes: {stats['total_changes']}")
    elapsed = (datetime.now() - stats['start_time']).total_seconds()
    print(f"   - Duration: {elapsed:.1f}s")

    # Cleanup
    if os.path.exists("example_search.db"):
        os.remove("example_search.db")

    print("\n   [EXAMPLE COMPLETE]")


def example_3_statistics_and_reporting():
    """Example 3: Real-time statistics and reporting"""
    print("\n" + "="*70)
    print("EXAMPLE 3: Statistics and Reporting")
    print("="*70)

    # Create indexer
    print("\n1. Creating indexer and simulating changes...")
    indexer = IncrementalIndexer(
        semantic_search_db="example_search.db",
        project_name="Example-Project",
        root_path="."
    )

    # Simulate some changes
    from search.incremental_indexer import FileChangeEvent, FileEventType

    print("2. Simulating 5 file changes...")
    for i in range(5):
        event = FileChangeEvent(
            event_type=FileEventType.CREATED if i % 2 == 0 else FileEventType.MODIFIED,
            file_path=f"example_file_{i}.py",
            timestamp=time.time()
        )
        indexer.event_queue.put(event)

    # Get statistics
    print("\n3. Current statistics:")
    stats = indexer.get_stats()

    report = f"""
   Project: {indexer.project_name}
   Root Path: {indexer.root_path}
   Running: {stats['running']}

   File Statistics:
   - Created: {stats['files_created']}
   - Modified: {stats['files_modified']}
   - Deleted: {stats['files_deleted']}
   - Total Events: {stats['total_events']}

   Batch Statistics:
   - Batches Processed: {stats['batches_processed']}
   - Queue Size: {stats['queue_size']}
   - Tracked Files: {stats['tracked_files']}

   Configuration:
   - Batch Size: {indexer.batch_size}
   - Batch Interval: {indexer.batch_interval}s
   - Debounce Interval: {indexer.debounce_interval}s

   Start Time: {stats['start_time']}
   Last Update: {stats['last_update']}
    """

    print(report)

    # Cleanup
    if os.path.exists("example_search.db"):
        os.remove("example_search.db")

    print("   [EXAMPLE COMPLETE]")


def example_4_error_handling():
    """Example 4: Error handling and recovery"""
    print("\n" + "="*70)
    print("EXAMPLE 4: Error Handling and Recovery")
    print("="*70)

    error_log = []

    def on_error(error):
        error_log.append({
            'time': datetime.now().isoformat(),
            'error': error
        })
        print(f"   ERROR CAUGHT: {error}")

    # Create indexer with error handler
    print("\n1. Creating indexer with error handler...")
    indexer = IncrementalIndexer(
        semantic_search_db="example_search.db",
        project_name="Example-Project",
        root_path="."
    )
    indexer.on_error = on_error

    # Try to process invalid events
    print("2. Testing error scenarios...")

    try:
        # Simulate various error conditions
        print("   - Testing with non-existent path...")
        indexer.root_path = "/nonexistent/path/that/does/not/exist"

        print("   - Testing graceful handling...")
        indexer.start_monitoring()
        time.sleep(1)
        indexer.stop_monitoring()

        print(f"   - Errors caught: {len(error_log)}")

    except Exception as e:
        print(f"   Exception handled: {e}")

    print("\n   [EXAMPLE COMPLETE]")


def example_5_performance_tuning():
    """Example 5: Performance tuning for different scenarios"""
    print("\n" + "="*70)
    print("EXAMPLE 5: Performance Tuning")
    print("="*70)

    scenarios = [
        {
            'name': 'High-Volume Changes (Large Batches)',
            'batch_size': 100,
            'batch_interval': 3.0,
            'debounce_interval': 2.0,
            'use_case': 'For projects with frequent, bursty changes'
        },
        {
            'name': 'Low-Latency Updates (Small Batches)',
            'batch_size': 10,
            'batch_interval': 0.5,
            'debounce_interval': 0.3,
            'use_case': 'For real-time monitoring requirements'
        },
        {
            'name': 'Memory Efficient (Small Queue)',
            'batch_size': 25,
            'batch_interval': 2.0,
            'debounce_interval': 1.0,
            'use_case': 'For resource-constrained environments'
        },
        {
            'name': 'Default Balanced',
            'batch_size': 50,
            'batch_interval': 2.0,
            'debounce_interval': 1.0,
            'use_case': 'General purpose, good for most scenarios'
        }
    ]

    print("\nTuning Profiles:\n")

    for i, scenario in enumerate(scenarios, 1):
        print(f"{i}. {scenario['name']}")
        print(f"   Use Case: {scenario['use_case']}")
        print(f"   Configuration:")
        print(f"     - Batch Size: {scenario['batch_size']} files/batch")
        print(f"     - Batch Interval: {scenario['batch_interval']}s (max wait)")
        print(f"     - Debounce Interval: {scenario['debounce_interval']}s")
        print()

    print("   [EXAMPLE COMPLETE]")


def main():
    """Run all examples"""
    print("""
    ============================================================
    Incremental Indexer - Integration Examples
    ============================================================
    """)

    try:
        example_1_basic_setup()
        example_2_continuous_monitoring()
        example_3_statistics_and_reporting()
        example_4_error_handling()
        example_5_performance_tuning()

        print("\n" + "="*70)
        print("ALL EXAMPLES COMPLETED")
        print("="*70)

        print("""
    WHAT YOU LEARNED:
    ---------------------------------------------------
    1. How to initialize SemanticCodeSearch
    2. How to create and configure IncrementalIndexer
    3. How to set up callbacks for monitoring
    4. How to read real-time statistics
    5. How to handle errors gracefully
    6. How to tune performance for different scenarios

    NEXT STEPS:
    ---------------------------------------------------
    1. Read INCREMENTAL_INDEXER_README.md for detailed documentation
    2. Review search/incremental_indexer.py source code
    3. Run test_incremental_indexer_demo.py for comprehensive demo
    4. Integrate into your application
    5. Monitor production usage with callbacks
    6. Adjust tuning parameters for your workload

    KEY TAKEAWAYS:
    ---------------------------------------------------
    - Incremental indexing is much faster than full re-indexing
    - File change detection uses MD5 hashing
    - Batching and debouncing prevent rapid re-indexing
    - Callbacks provide hooks for monitoring and notifications
    - Pure Python fallback ensures it works everywhere
    - Statistics tracking enables performance monitoring
        """)

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
