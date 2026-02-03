#!/usr/bin/env python3
"""Agentic Core - Master integration of all agentic capabilities"""
import sys
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

sys.path.append(str(Path(__file__).parent))

from memory.episodic_memory import EpisodicMemory
from core.persistent_memory import PersistentMemory
from core.telegram_connector import TelegramConnector

# Vision is optional (requires pytesseract)
try:
    from vision.vision_system import VisionSystem
    VISION_AVAILABLE = True
except ImportError:
    VISION_AVAILABLE = False

class AgenticCore:
    """
    Master integration of all agentic capabilities:
    - Vision (see the world)
    - Episodic Memory (remember relationships)
    - Deep Reasoning (think deeply)
    - Proactive Agent (act independently)
    - Multi-Agent (coordinate teams)
    """

    def __init__(self):
        workspace = Path(__file__).parent
        self.workspace = workspace

        # Initialize all systems
        print("Initializing Agentic Core...")

        # Core systems
        self.memory = PersistentMemory(str(workspace / "memory.db"))
        self.telegram = TelegramConnector()

        # Agentic capabilities
        if VISION_AVAILABLE:
            self.vision = VisionSystem()
        else:
            self.vision = None
            print("Vision system not available (requires pytesseract)")

        self.episodic_memory = EpisodicMemory()

        # Initialize all remaining systems
        self.reasoning = None
        self.proactive_agent = None
        self.multi_agent = None
        self.learning = None
        self.pattern_learner = None
        self.natural_language = None

        # State
        self.started_at = datetime.now()
        self.capabilities_active = {
            'vision': VISION_AVAILABLE,
            'episodic_memory': True,
            'reasoning': False,
            'proactive_agent': False,
            'multi_agent': False,
            'learning': False,
            'pattern_learner': False,
            'natural_language': False
        }

        # Try to initialize remaining systems
        self.initialize_remaining_systems()

        print("Agentic Core initialized!")

    def initialize_remaining_systems(self):
        """Initialize remaining systems after they're built"""
        try:
            from reasoning.deep_reasoning import DeepReasoning
            self.reasoning = DeepReasoning()
            self.capabilities_active['reasoning'] = True
        except ImportError:
            print("Deep Reasoning system not yet available")

        try:
            from agents.proactive_agent import ProactiveAgent
            self.proactive_agent = ProactiveAgent()
            self.capabilities_active['proactive_agent'] = True
        except ImportError:
            print("Proactive Agent not yet available")

        try:
            from agents.multi_agent_coordinator import MultiAgentCoordinator
            self.multi_agent = MultiAgentCoordinator()
            self.capabilities_active['multi_agent'] = True
        except ImportError:
            print("Multi-Agent Coordinator not yet available")

        try:
            from ml.reinforcement_learning import ReinforcementLearning
            self.learning = ReinforcementLearning()
            self.capabilities_active['learning'] = True
        except ImportError:
            print("Reinforcement Learning not yet available")

        try:
            from ml.pattern_learner import PatternLearner
            self.pattern_learner = PatternLearner()
            self.capabilities_active['pattern_learner'] = True
        except ImportError:
            print("Pattern Learner not yet available")

        try:
            from interface.natural_language import NaturalLanguageInterface
            self.natural_language = NaturalLanguageInterface()
            self.capabilities_active['natural_language'] = True
        except ImportError:
            print("Natural Language Interface not yet available")

    def see(self, analyze: bool = True) -> Dict:
        """
        Use vision to see and analyze current screen

        Args:
            analyze: Perform full analysis

        Returns:
            Vision analysis results
        """
        screenshot = self.vision.capture_screenshot()

        if analyze:
            analysis = self.vision.analyze_screenshot(screenshot)
            return analysis
        else:
            return {'screenshot': screenshot}

    def remember(self, user_message: str, my_response: str,
                context: str = None, sentiment: str = 'neutral'):
        """
        Remember this interaction in episodic memory

        Args:
            user_message: What the user said
            my_response: What I responded
            context: Additional context
            sentiment: Emotional tone
        """
        self.episodic_memory.remember_conversation(
            user_message, my_response, context, sentiment
        )

        # Also log to persistent memory
        self.memory.log_decision(
            'Conversation remembered',
            f'User: {user_message[:100]}...',
            tags=['episodic', 'conversation']
        )

    def learn_about_user(self, category: str, preference: str,
                        strength: float = 0.7, evidence: str = None):
        """
        Learn something about the user

        Args:
            category: Category (e.g., 'work_style', 'communication')
            preference: The preference learned
            strength: Confidence (0-1)
            evidence: Supporting evidence
        """
        self.episodic_memory.learn_preference(category, preference, strength, evidence)

        self.memory.log_decision(
            f'Learned user preference: {category}',
            f'{preference} (strength: {strength})',
            tags=['episodic', 'learning']
        )

    def recall(self, query: str) -> Dict:
        """
        Search all memory for relevant information

        Args:
            query: What to search for

        Returns:
            Search results from all memory systems
        """
        # Search episodic memory
        episodic_results = self.episodic_memory.search_memory(query)

        # Search persistent memory
        cursor = self.memory.conn.cursor()
        cursor.execute('''
            SELECT decision, rationale, created_at
            FROM decisions
            WHERE decision LIKE ? OR rationale LIKE ?
            ORDER BY created_at DESC
            LIMIT 20
        ''', (f'%{query}%', f'%{query}%'))

        persistent_results = [dict(row) for row in cursor.fetchall()]

        return {
            'episodic': episodic_results,
            'persistent': persistent_results
        }

    def get_user_profile(self) -> Dict:
        """Get complete user profile from episodic memory"""
        profile = self.episodic_memory.get_profile()
        preferences = self.episodic_memory.get_preferences()
        goals = self.episodic_memory.get_active_goals()
        summary = self.episodic_memory.get_relationship_summary()

        return {
            'profile': profile,
            'preferences': preferences,
            'active_goals': goals,
            'summary': summary
        }

    def verify_visual_output(self, expected_text: str = None) -> bool:
        """
        Verify something is visible on screen

        Args:
            expected_text: Text that should be visible

        Returns:
            True if verified
        """
        return self.vision.verify_output(expected_text=expected_text)

    def ask(self, question: str) -> str:
        """
        Ask question in natural language to any system

        Args:
            question: Natural language question

        Returns:
            Response from appropriate system
        """
        if self.natural_language:
            return self.natural_language.execute(question)
        return "Natural language interface not available"

    def learn_from_outcome(self, action_type: str, action_name: str,
                          success: bool, outcome_value: float = None) -> float:
        """
        Learn from action outcome

        Args:
            action_type: Type of action
            action_name: Specific action taken
            success: Whether it succeeded
            outcome_value: Numeric outcome

        Returns:
            Calculated reward
        """
        if self.learning:
            return self.learning.record_outcome(
                action_type, action_name, success, outcome_value
            )
        return 0.0

    def get_learning_summary(self) -> Dict:
        """Get summary of all learning"""
        if self.learning:
            return self.learning.get_learning_summary()
        return {'status': 'Learning system not available'}

    def get_capabilities_status(self) -> Dict:
        """Get status of all capabilities"""
        return {
            'active_capabilities': self.capabilities_active,
            'uptime': (datetime.now() - self.started_at).total_seconds(),
            'systems': {
                'vision': 'active' if self.vision else 'inactive',
                'episodic_memory': 'active' if self.episodic_memory else 'inactive',
                'reasoning': 'active' if self.reasoning else 'inactive',
                'proactive_agent': 'active' if self.proactive_agent else 'inactive',
                'multi_agent': 'active' if self.multi_agent else 'inactive',
                'learning': 'active' if self.learning else 'inactive',
                'pattern_learner': 'active' if self.pattern_learner else 'inactive',
                'natural_language': 'active' if self.natural_language else 'inactive'
            }
        }

    def notify(self, message: str):
        """Send notification via Telegram"""
        self.telegram.send_message(message)

    def __str__(self):
        """String representation"""
        active_count = sum(1 for v in self.capabilities_active.values() if v)
        total_count = len(self.capabilities_active)

        return f"AgenticCore ({active_count}/{total_count} capabilities active)"


# Global instance
_agentic_core = None

def get_agentic_core() -> AgenticCore:
    """Get or create global agentic core instance"""
    global _agentic_core
    if _agentic_core is None:
        _agentic_core = AgenticCore()
    return _agentic_core


if __name__ == '__main__':
    # Test agentic core
    print("=" * 60)
    print("AGENTIC CORE - MASTER INTEGRATION")
    print("=" * 60)

    core = AgenticCore()

    # Test vision
    print("\n1. Testing vision...")
    try:
        analysis = core.see()
        print(f"   Screen analyzed: {analysis.get('is_dashboard')}")
    except Exception as e:
        print(f"   Vision test: {e}")

    # Test memory
    print("\n2. Testing episodic memory...")
    core.remember(
        "Build all agentic capabilities",
        "Building all 5 systems autonomously",
        context="Complete vision implementation"
    )

    core.learn_about_user(
        "work_style",
        "wants autonomous operation",
        strength=0.9,
        evidence="Explicitly requested full vision build"
    )

    profile = core.get_user_profile()
    print(f"   Conversations remembered: {profile['summary']['total_conversations']}")
    print(f"   Preferences learned: {profile['summary']['preferences_learned']}")

    # Test recall
    print("\n3. Testing memory recall...")
    results = core.recall("vision")
    print(f"   Found {len(results['episodic']['conversations'])} conversations")
    print(f"   Found {len(results['persistent'])} persistent memories")

    # Check status
    print("\n4. Capabilities status:")
    status = core.get_capabilities_status()
    for cap, active in status['active_capabilities'].items():
        print(f"   {cap}: {'ACTIVE' if active else 'PENDING'}")

    print("\n" + "=" * 60)
    print(f"{core}")
    print("=" * 60)
    print("\nAgentic Core operational!")
