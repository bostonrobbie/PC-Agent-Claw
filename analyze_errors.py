#!/usr/bin/env python3
"""Analyze all errors encountered during this session"""
import sqlite3
from pathlib import Path
import json
from collections import defaultdict

workspace = Path(__file__).parent
db_path = workspace / "memory.db"

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Get all error-related entries
cursor.execute("""
    SELECT decision, context, tags, created_at
    FROM decisions
    WHERE tags LIKE '%error%' OR decision LIKE '%error%' OR decision LIKE '%fail%'
    ORDER BY created_at DESC
    LIMIT 100
""")

errors = cursor.fetchall()

print("=" * 80)
print("ERROR ANALYSIS - Session Summary")
print("=" * 80)
print(f"\nTotal errors/failures found: {len(errors)}\n")

# Categorize errors
error_categories = defaultdict(list)

for error in errors:
    decision = error['decision']
    context = error['context']
    tags = error['tags']
    created_at = error['created_at']

    # Categorize
    if 'connection' in decision.lower() or 'connection' in context.lower():
        category = 'Connection Errors'
    elif 'telegram' in decision.lower() or 'telegram' in context.lower():
        category = 'Telegram Errors'
    elif 'encoding' in decision.lower() or 'charmap' in context.lower():
        category = 'Encoding Errors'
    elif 'sqlite' in decision.lower() or 'database' in context.lower():
        category = 'Database Errors'
    elif 'thread' in decision.lower():
        category = 'Threading Errors'
    elif 'git' in decision.lower():
        category = 'Git Errors'
    else:
        category = 'Other Errors'

    error_categories[category].append({
        'decision': decision,
        'context': context[:200],
        'time': created_at
    })

# Print categorized errors
for category, error_list in sorted(error_categories.items()):
    print(f"\n{'=' * 80}")
    print(f"{category} ({len(error_list)} occurrences)")
    print('=' * 80)

    for i, err in enumerate(error_list[:5], 1):  # Show first 5 of each category
        print(f"\n{i}. {err['time']}")
        print(f"   Decision: {err['decision']}")
        print(f"   Context: {err['context']}")

conn.close()

print("\n" + "=" * 80)
print("SUMMARY OF MAIN ISSUES")
print("=" * 80)

print("""
1. TELEGRAM CONNECTION ISSUES
   - Unauthorized errors (401) with bot token
   - Encoding errors (charmap codec) when sending Unicode
   - Notifier configuration not properly loaded

2. THREADING/SQLITE ISSUES
   - SQLite objects can only be used in thread they were created
   - Fixed by using per-thread connections

3. ENCODING ISSUES
   - Unicode emoji characters failing with charmap codec
   - Affects Windows console output
   - Fixed by removing emoji or using UTF-8 encoding

4. GIT ISSUES
   - 'nul' file causing commit errors
   - Fixed by deleting and using specific file paths

5. CONNECTION ISSUES
   - Broker connection checks
   - Background agent completion checking

RECOMMENDATIONS:
- Build robust Telegram connection handler
- Add keep-alive monitoring system
- Improve error recovery for common failures
- Add health check endpoints
- Build notification queue with retry logic
""")
