#!/usr/bin/env python3
"""
Enhanced Memory Search - Search through all memory and knowledge
"""

from pathlib import Path
import json
import re
from datetime import datetime

WORKSPACE = Path(r"C:\Users\User\.openclaw\workspace")
MEMORY_DIR = WORKSPACE / "memory"

class MemorySearch:
    """Search through Claude's memory system"""

    def __init__(self):
        self.memory_dir = MEMORY_DIR

    def search_all(self, query, case_sensitive=False):
        """Search through all memory files"""

        print("=" * 60)
        print(f"Memory Search: '{query}'")
        print("=" * 60)
        print()

        results = {
            'query': query,
            'timestamp': datetime.now().isoformat(),
            'matches': []
        }

        flags = 0 if case_sensitive else re.IGNORECASE

        # Search conversations
        print("[1/4] Searching conversations...")
        conv_dir = self.memory_dir / "conversations"
        if conv_dir.exists():
            for file in conv_dir.glob("*.md"):
                with open(file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    matches = re.finditer(query, content, flags)
                    for match in matches:
                        # Get context around match
                        start = max(0, match.start() - 100)
                        end = min(len(content), match.end() + 100)
                        context = content[start:end]

                        results['matches'].append({
                            'type': 'conversation',
                            'file': file.name,
                            'date': file.stem,
                            'context': context,
                            'position': match.start()
                        })

        print(f"   Found {len([m for m in results['matches'] if m['type']=='conversation'])} matches")

        # Search knowledge
        print("[2/4] Searching knowledge base...")
        knowledge_dir = self.memory_dir / "knowledge"
        if knowledge_dir.exists():
            for file in knowledge_dir.glob("*.md"):
                with open(file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    matches = re.finditer(query, content, flags)
                    for match in matches:
                        start = max(0, match.start() - 100)
                        end = min(len(content), match.end() + 100)
                        context = content[start:end]

                        results['matches'].append({
                            'type': 'knowledge',
                            'domain': file.stem,
                            'file': file.name,
                            'context': context,
                            'position': match.start()
                        })

        print(f"   Found {len([m for m in results['matches'] if m['type']=='knowledge'])} matches")

        # Search learnings
        print("[3/4] Searching learnings...")
        learnings_dir = self.memory_dir / "learnings"
        if learnings_dir.exists():
            for file in learnings_dir.glob("*.md"):
                with open(file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    matches = re.finditer(query, content, flags)
                    for match in matches:
                        start = max(0, match.start() - 100)
                        end = min(len(content), match.end() + 100)
                        context = content[start:end]

                        results['matches'].append({
                            'type': 'learning',
                            'category': file.stem,
                            'file': file.name,
                            'context': context,
                            'position': match.start()
                        })

        print(f"   Found {len([m for m in results['matches'] if m['type']=='learning'])} matches")

        # Search ChatGPT import
        print("[4/4] Searching ChatGPT import...")
        chatgpt_dir = self.memory_dir / "chatgpt_import"
        if chatgpt_dir.exists():
            for file in chatgpt_dir.glob("*.json"):
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # Convert to string for searching
                        content = json.dumps(data, indent=2)
                        if re.search(query, content, flags):
                            results['matches'].append({
                                'type': 'chatgpt_import',
                                'file': file.name,
                                'note': 'Found in ChatGPT data'
                            })
                except:
                    pass

        print(f"   Found {len([m for m in results['matches'] if m['type']=='chatgpt_import'])} files")

        # Save results
        results_file = WORKSPACE / f"search_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)

        print()
        print("=" * 60)
        print(f"SEARCH COMPLETE: {len(results['matches'])} total matches")
        print("=" * 60)
        print()
        print(f"Results saved to: {results_file}")
        print()

        # Display summary
        by_type = {}
        for match in results['matches']:
            mtype = match['type']
            by_type[mtype] = by_type.get(mtype, 0) + 1

        print("Matches by type:")
        for mtype, count in by_type.items():
            print(f"  - {mtype}: {count}")

        return results

    def search_recent(self, query, days=7):
        """Search only recent conversations"""

        from datetime import timedelta
        now = datetime.now()
        cutoff = now - timedelta(days=days)

        print(f"Searching conversations from last {days} days...")

        results = []
        conv_dir = self.memory_dir / "conversations"
        if conv_dir.exists():
            for file in conv_dir.glob("*.md"):
                try:
                    file_date = datetime.strptime(file.stem, '%Y-%m-%d')
                    if file_date >= cutoff:
                        with open(file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if re.search(query, content, re.IGNORECASE):
                                results.append({
                                    'date': file.stem,
                                    'file': str(file)
                                })
                except:
                    pass

        print(f"Found {len(results)} recent conversations with '{query}'")
        return results

if __name__ == "__main__":
    import sys

    searcher = MemorySearch()

    if len(sys.argv) > 1:
        query = ' '.join(sys.argv[1:])
        searcher.search_all(query)
    else:
        print("Usage: python search_memory.py <query>")
        print("Example: python search_memory.py trading strategy")
