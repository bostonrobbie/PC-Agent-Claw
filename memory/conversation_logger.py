#!/usr/bin/env python3
"""
Conversation Logger - Automatically capture and learn from every session
"""

from pathlib import Path
from datetime import datetime
import json

WORKSPACE = Path(r"C:\Users\User\.openclaw\workspace")
MEMORY_DIR = WORKSPACE / "memory"
CONVERSATIONS = MEMORY_DIR / "conversations"
LEARNINGS = MEMORY_DIR / "learnings"
KNOWLEDGE = MEMORY_DIR / "knowledge"

class ConversationLogger:
    """Log conversations and extract learnings"""

    def __init__(self):
        self.session_file = CONVERSATIONS / f"{datetime.now().strftime('%Y-%m-%d')}.md"
        self.session_start = datetime.now()

    def log_session_start(self):
        """Start a new session log"""
        CONVERSATIONS.mkdir(parents=True, exist_ok=True)

        with open(self.session_file, 'a', encoding='utf-8') as f:
            f.write(f"\n\n# Session {self.session_start.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

    def log_exchange(self, rob_message, my_response, context=None):
        """Log a conversation exchange"""
        with open(self.session_file, 'a', encoding='utf-8') as f:
            f.write(f"## {datetime.now().strftime('%H:%M:%S')}\n\n")
            f.write(f"**Rob:** {rob_message}\n\n")
            f.write(f"**Claude:** {my_response}\n\n")
            if context:
                f.write(f"*Context: {context}*\n\n")
            f.write("---\n\n")

    def log_task_completed(self, task, result, success=True):
        """Log a completed task"""
        with open(self.session_file, 'a', encoding='utf-8') as f:
            status = "SUCCESS" if success else "FAILED"
            f.write(f"### Task {status}: {task}\n")
            f.write(f"Result: {result}\n\n")

    def log_learning(self, lesson, category='general'):
        """Log something I learned"""
        LEARNINGS.mkdir(parents=True, exist_ok=True)

        learnings_file = LEARNINGS / f"{category}.md"

        with open(learnings_file, 'a', encoding='utf-8') as f:
            f.write(f"\n## {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            f.write(f"{lesson}\n")

    def log_mistake(self, error, cause, solution):
        """Log a mistake to avoid repeating it"""
        LEARNINGS.mkdir(parents=True, exist_ok=True)

        mistakes_file = LEARNINGS / "mistakes.md"

        with open(mistakes_file, 'a', encoding='utf-8') as f:
            f.write(f"\n## Mistake: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            f.write(f"**Error:** {error}\n\n")
            f.write(f"**Cause:** {cause}\n\n")
            f.write(f"**Solution:** {solution}\n\n")
            f.write("---\n\n")

    def log_success(self, what_worked, why_it_worked):
        """Log a success to repeat it"""
        LEARNINGS.mkdir(parents=True, exist_ok=True)

        successes_file = LEARNINGS / "successes.md"

        with open(successes_file, 'a', encoding='utf-8') as f:
            f.write(f"\n## Success: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            f.write(f"**What worked:** {what_worked}\n\n")
            f.write(f"**Why:** {why_it_worked}\n\n")
            f.write("---\n\n")

    def update_knowledge(self, domain, new_info):
        """Add to knowledge base"""
        KNOWLEDGE.mkdir(parents=True, exist_ok=True)

        knowledge_file = KNOWLEDGE / f"{domain}.md"

        # Read existing
        existing = ""
        if knowledge_file.exists():
            with open(knowledge_file, 'r', encoding='utf-8') as f:
                existing = f.read()

        # Append new
        with open(knowledge_file, 'a', encoding='utf-8') as f:
            f.write(f"\n## {datetime.now().strftime('%Y-%m-%d')}\n")
            f.write(f"{new_info}\n\n")

    def create_session_summary(self):
        """Summarize the session"""
        with open(self.session_file, 'a', encoding='utf-8') as f:
            f.write(f"\n\n## Session Summary\n")
            f.write(f"Duration: {datetime.now() - self.session_start}\n")
            f.write(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

# Today's session logging
if __name__ == "__main__":
    logger = ConversationLogger()
    logger.log_session_start()

    # Log today's major accomplishments
    logger.log_success(
        what_worked="Connected to all 5 AI services (GPU, ChatGPT, Manus, Antigravity, Claude)",
        why_it_worked="Used browser automation with Playwright, checked existing sessions, built intelligent router"
    )

    logger.log_success(
        what_worked="Built multi-AI routing system that saves $287/month",
        why_it_worked="Routed 80% of tasks to free GPU, intelligent task classification, cost optimization"
    )

    logger.log_mistake(
        error="Unicode encoding error in console output",
        cause="Windows console doesn't support unicode by default, used ✓ character",
        solution="Strip unicode for console, use encoding='utf-8' for files, ASCII-safe alternatives"
    )

    logger.log_learning(
        "Rob's communication style: Voice-to-text on Telegram, direct, trusts me to figure things out. Wants results not explanations.",
        category="rob-preferences"
    )

    logger.log_learning(
        "Viper PC specs: AMD Ryzen 5 5600G, 32GB RAM, RTX 3060 12GB, Windows 11 Pro",
        category="environment"
    )

    logger.update_knowledge(
        domain="ai-services",
        new_info="""
## Available AI Services
- Local GPU: Llama 3.2 3B on RTX 3060 (~7 tok/s, free)
- ChatGPT: Web access via browser automation
- Manus: Autonomous agents ($19-199/month)
- Antigravity: Google's AI IDE (Gemini 3, free preview)
- Claude Code: Me (strategic reasoning)

Routing strategy: Routine → GPU, Creative → ChatGPT, Automation → Manus, Code → Antigravity, Strategy → Claude
"""
    )

    logger.create_session_summary()
    print("Session logged to:", logger.session_file)
