#!/usr/bin/env python3
"""
ChatGPT Data Import - Parse and import ChatGPT conversations into local memory
"""

from pathlib import Path
from datetime import datetime
import json
import re
from bs4 import BeautifulSoup
from collections import defaultdict

WORKSPACE = Path(r"C:\Users\User\.openclaw\workspace")
MEMORY_DIR = WORKSPACE / "memory"
CHATGPT_FILE = Path(r"C:\Users\User\Desktop\chatgpt_data\conversations.json")

class ChatGPTImporter:
    """Import ChatGPT conversations into local memory system"""

    def __init__(self):
        self.conversations = []
        self.topics = defaultdict(list)
        self.learnings = []
        self.rob_preferences = []

    def parse_json(self):
        """Parse the ChatGPT JSON export"""
        print(f"Parsing ChatGPT data from: {CHATGPT_FILE}")
        file_size_mb = CHATGPT_FILE.stat().st_size / 1024 / 1024
        print(f"File size: {file_size_mb:.1f} MB")

        # Read the JSON file directly
        with open(CHATGPT_FILE, 'r', encoding='utf-8') as f:
            conversations_data = json.load(f)

        print(f"Found {len(conversations_data)} conversations")
        return conversations_data

    def extract_conversations(self, conversations_data):
        """Extract useful information from conversations"""
        extracted = []

        # Check if it's JSON data or HTML elements
        if isinstance(conversations_data, list) and isinstance(conversations_data[0], dict):
            # JSON format
            for i, conv in enumerate(conversations_data):
                if i % 100 == 0:
                    print(f"Processing conversation {i}/{len(conversations_data)}...")

                title = conv.get('title', f"Conversation {i+1}")
                timestamp = conv.get('create_time')

                # Extract messages from mapping
                user_messages = []
                assistant_messages = []
                full_text = []

                if 'mapping' in conv:
                    for msg_id, msg_data in conv['mapping'].items():
                        if msg_data.get('message'):
                            msg = msg_data['message']
                            author = msg.get('author', {}).get('role', '')
                            content = msg.get('content', {})
                            parts = content.get('parts', [])

                            if parts and parts[0]:  # Skip empty messages
                                text = parts[0] if isinstance(parts[0], str) else str(parts[0])

                                if author == 'user':
                                    user_messages.append(text)
                                    full_text.append(f"User: {text}")
                                elif author == 'assistant':
                                    assistant_messages.append(text)
                                    full_text.append(f"Assistant: {text}")

                conversation_data = {
                    'id': i + 1,
                    'title': title,
                    'timestamp': datetime.fromtimestamp(timestamp).isoformat() if timestamp else None,
                    'user_messages': user_messages,
                    'assistant_messages': assistant_messages,
                    'full_text': '\n'.join(full_text)
                }

                extracted.append(conversation_data)
        else:
            # HTML format (fallback)
            for i, conv in enumerate(conversations_data):
                if i % 100 == 0:
                    print(f"Processing conversation {i}/{len(conversations_data)}...")

                title_elem = conv.find(['h1', 'h2', 'h3', 'h4'])
                title = title_elem.get_text(strip=True) if title_elem else f"Conversation {i+1}"

                conversation_data = {
                    'id': i + 1,
                    'title': title,
                    'timestamp': None,
                    'user_messages': [],
                    'assistant_messages': [],
                    'full_text': conv.get_text(strip=True)
                }

                extracted.append(conversation_data)

        return extracted

    def categorize_conversations(self, conversations):
        """Categorize conversations by topic"""
        categories = defaultdict(list)

        # Keywords for different categories
        business_keywords = ['business', 'money', 'profit', 'revenue', 'customer', 'market', 'sales', 'pricing']
        tech_keywords = ['code', 'python', 'javascript', 'api', 'database', 'server', 'programming']
        ai_keywords = ['ai', 'llm', 'gpt', 'claude', 'model', 'training', 'inference']
        trading_keywords = ['trade', 'trading', 'forex', 'crypto', 'stock', 'chart', 'analysis', 'strategy']

        for conv in conversations:
            text_lower = conv['full_text'].lower()

            # Check which categories this belongs to
            if any(kw in text_lower for kw in business_keywords):
                categories['business'].append(conv)
            if any(kw in text_lower for kw in tech_keywords):
                categories['technology'].append(conv)
            if any(kw in text_lower for kw in ai_keywords):
                categories['ai'].append(conv)
            if any(kw in text_lower for kw in trading_keywords):
                categories['trading'].append(conv)

        return categories

    def extract_learnings(self, conversations):
        """Extract key learnings and insights"""
        learnings = []

        # Look for conversations about preferences, decisions, lessons learned
        for conv in conversations:
            text = conv['full_text']

            # Look for preference indicators
            if any(phrase in text.lower() for phrase in ['i prefer', 'i like', 'i want', 'i need', 'important to me']):
                learnings.append({
                    'type': 'preference',
                    'source': conv['title'],
                    'timestamp': conv['timestamp'],
                    'content': text[:500]  # First 500 chars
                })

            # Look for decisions made
            if any(phrase in text.lower() for phrase in ['decided to', 'going with', 'chose', 'will use']):
                learnings.append({
                    'type': 'decision',
                    'source': conv['title'],
                    'timestamp': conv['timestamp'],
                    'content': text[:500]
                })

        return learnings

    def save_to_memory(self, conversations, categories, learnings):
        """Save imported data to local memory system"""

        # Create import directory
        import_dir = MEMORY_DIR / "chatgpt_import"
        import_dir.mkdir(parents=True, exist_ok=True)

        # Save full conversation index
        index_file = import_dir / "conversation_index.json"
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump([{
                'id': c['id'],
                'title': c['title'],
                'timestamp': c['timestamp'],
                'message_count': len(c['user_messages']) + len(c['assistant_messages'])
            } for c in conversations], f, indent=2)

        print(f"Saved conversation index: {index_file}")

        # Save by category
        for category, convs in categories.items():
            category_file = import_dir / f"{category}.json"
            with open(category_file, 'w', encoding='utf-8') as f:
                json.dump(convs, f, indent=2)
            print(f"Saved {len(convs)} conversations to: {category_file}")

        # Save learnings
        learnings_file = import_dir / "extracted_learnings.json"
        with open(learnings_file, 'w', encoding='utf-8') as f:
            json.dump(learnings, f, indent=2)
        print(f"Saved {len(learnings)} learnings to: {learnings_file}")

        # Create summary markdown
        summary_file = import_dir / "IMPORT_SUMMARY.md"
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(f"# ChatGPT Data Import Summary\n\n")
            f.write(f"**Import Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Source:** {CHATGPT_FILE}\n\n")
            f.write(f"## Statistics\n\n")
            f.write(f"- Total Conversations: {len(conversations)}\n")
            f.write(f"- Learnings Extracted: {len(learnings)}\n\n")
            f.write(f"## Categories\n\n")
            for category, convs in categories.items():
                f.write(f"- **{category.title()}:** {len(convs)} conversations\n")
            f.write(f"\n## Files Created\n\n")
            f.write(f"- `conversation_index.json` - Full conversation index\n")
            for category in categories.keys():
                f.write(f"- `{category}.json` - {category.title()} conversations\n")
            f.write(f"- `extracted_learnings.json` - Key learnings and preferences\n")
            f.write(f"\n## Location\n\n")
            f.write(f"All data stored locally at: `{import_dir}`\n")
            f.write(f"\n**Security:** All data remains on your PC. Nothing shared externally.\n")

        print(f"\nImport summary: {summary_file}")

        return {
            'total_conversations': len(conversations),
            'categories': {k: len(v) for k, v in categories.items()},
            'learnings': len(learnings),
            'location': str(import_dir)
        }

    def run_import(self):
        """Run the full import process"""
        print("=" * 60)
        print("ChatGPT Data Import - LOCAL MEMORY SYSTEM")
        print("=" * 60)
        print()

        # Parse JSON
        raw_conversations = self.parse_json()

        # Extract structured data
        print("\nExtracting conversation data...")
        conversations = self.extract_conversations(raw_conversations)

        # Categorize
        print("\nCategorizing conversations...")
        categories = self.categorize_conversations(conversations)

        # Extract learnings
        print("\nExtracting learnings...")
        learnings = self.extract_learnings(conversations)

        # Save to local memory
        print("\nSaving to local memory system...")
        result = self.save_to_memory(conversations, categories, learnings)

        print("\n" + "=" * 60)
        print("IMPORT COMPLETE")
        print("=" * 60)
        print(f"\nTotal Conversations: {result['total_conversations']}")
        print(f"Learnings Extracted: {result['learnings']}")
        print(f"\nCategories:")
        for cat, count in result['categories'].items():
            print(f"  - {cat.title()}: {count}")
        print(f"\nLocation: {result['location']}")
        print(f"\nSecurity: [OK] All data stored locally on your PC")
        print(f"          [OK] Nothing shared with external services")
        print(f"          [OK] Full privacy maintained")

        return result

# Run import
if __name__ == "__main__":
    try:
        importer = ChatGPTImporter()
        result = importer.run_import()
    except Exception as e:
        print(f"\nError during import: {e}")
        import traceback
        traceback.print_exc()
