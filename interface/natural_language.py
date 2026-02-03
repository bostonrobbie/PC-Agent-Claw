#!/usr/bin/env python3
"""
Natural Language Interface
Talk to all agentic systems conversationally
"""
import sys
from pathlib import Path
import json
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

sys.path.append(str(Path(__file__).parent.parent))


@dataclass
class Intent:
    """Parsed user intent"""
    action: str  # What to do
    system: str  # Which system
    parameters: Dict[str, Any]  # Parameters
    confidence: float  # Confidence in parse


class NaturalLanguageInterface:
    """
    Natural language interface to all agentic systems

    Features:
    - Parse natural language requests
    - Route to appropriate system
    - Extract parameters automatically
    - Handle multi-step conversations
    - Provide natural responses
    """

    def __init__(self):
        # Load all agentic systems
        self.systems = self._load_systems()

        # Intent patterns for each system
        self.patterns = self._define_patterns()

        # Conversation context
        self.context = {
            'last_system': None,
            'last_action': None,
            'pending_parameters': {}
        }

    def _load_systems(self) -> Dict:
        """Load all agentic systems"""
        systems = {}

        try:
            from vision.vision_system import VisionSystem
            systems['vision'] = VisionSystem()
        except Exception as e:
            print(f"[WARNING] Could not load Vision: {e}")

        try:
            from memory.episodic_memory import EpisodicMemory
            systems['memory'] = EpisodicMemory()
        except Exception as e:
            print(f"[WARNING] Could not load Memory: {e}")

        try:
            from reasoning.deep_reasoning import DeepReasoning
            systems['reasoning'] = DeepReasoning()
        except Exception as e:
            print(f"[WARNING] Could not load Reasoning: {e}")

        try:
            from agents.proactive_agent import ProactiveAgent
            systems['proactive'] = ProactiveAgent()
        except Exception as e:
            print(f"[WARNING] Could not load Proactive Agent: {e}")

        try:
            from agents.multi_agent_coordinator import MultiAgentCoordinator
            systems['multi_agent'] = MultiAgentCoordinator()
        except Exception as e:
            print(f"[WARNING] Could not load Multi-Agent: {e}")

        try:
            from ml.reinforcement_learning import ReinforcementLearning
            systems['learning'] = ReinforcementLearning()
        except Exception as e:
            print(f"[WARNING] Could not load Learning: {e}")

        try:
            from ml.pattern_learner import PatternLearner
            systems['patterns'] = PatternLearner()
        except Exception as e:
            print(f"[WARNING] Could not load Pattern Learner: {e}")

        return systems

    def _define_patterns(self) -> Dict:
        """Define intent patterns for natural language parsing"""
        return {
            # Vision system
            'vision': [
                (r'(take|capture|grab)\s+(a\s+)?screenshot', 'capture_screenshot', {}),
                (r'(read|extract|get)\s+(text|words)\s+from\s+screen', 'extract_text', {}),
                (r'(analyze|check|look at)\s+screen', 'analyze_screenshot', {}),
                (r'verify\s+(.+?)\s+(is\s+)?(on\s+)?screen', 'verify_output', {'expected': 1}),
                (r'monitor\s+(the\s+)?screen', 'start_monitoring', {}),
            ],

            # Memory system
            'memory': [
                (r'remember\s+(.+)', 'remember_conversation', {'message': 1}),
                (r'(what\s+do\s+you\s+know|tell\s+me)\s+about\s+(.+)', 'recall_conversations', {'query': 2}),
                (r'(learn|save)\s+preference[s]?\s+(.+)', 'learn_preference', {'preference': 2}),
                (r'(what|show)\s+(are\s+)?my\s+preferences', 'get_preferences', {}),
                (r'(what|show)\s+(is\s+)?my\s+profile', 'get_profile', {}),
                (r'add\s+goal\s+(.+)', 'add_goal', {'goal': 1}),
                (r'(what|show)\s+(are\s+)?my\s+goals', 'get_goals', {}),
            ],

            # Reasoning system
            'reasoning': [
                (r'(think|reason)\s+about\s+(.+)', 'start_reasoning_session', {'goal': 2}),
                (r'(generate|create|make)\s+plan\s+for\s+(.+)', 'generate_plan', {'goal': 2}),
                (r'simulate\s+(.+)', 'simulate_outcome', {'action': 1}),
                (r'(what|why)\s+caused\s+(.+)', 'analyze_causes', {'effect': 2}),
                (r'(show|get)\s+reasoning\s+report', 'generate_reasoning_report', {}),
            ],

            # Proactive agent
            'proactive': [
                (r'start\s+monitoring', 'start_monitoring', {}),
                (r'stop\s+monitoring', 'stop_monitoring', {}),
                (r'(what|show)\s+opportunities', 'get_opportunities', {}),
                (r'(what|show)\s+issues', 'get_issues', {}),
                (r'(what|show)\s+suggestions', 'get_suggestions', {}),
                (r'detect\s+opportunity\s+(.+)', 'detect_opportunity', {'title': 1}),
                (r'report\s+issue\s+(.+)', 'detect_issue', {'title': 1}),
            ],

            # Multi-agent
            'multi_agent': [
                (r'spawn\s+agent\s+(.+)', 'spawn_agent', {'name': 1}),
                (r'create\s+(\d+)\s+agents', 'create_hierarchy', {'num': 1}),
                (r'(decompose|break\s+down)\s+task\s+(.+)', 'decompose_task', {'task': 2}),
                (r'(show|get)\s+agents', 'get_all_agents', {}),
            ],

            # Learning system
            'learning': [
                (r'(choose|pick|select)\s+best\s+(.+)', 'choose_action', {'type': 2}),
                (r'record\s+(success|failure)\s+of\s+(.+)', 'record_outcome', {'action': 2, 'success': 1}),
                (r'(what|show)\s+learned\s+about\s+(.+)', 'get_action_recommendations', {'type': 2}),
                (r'(show|get)\s+learning\s+summary', 'get_learning_summary', {}),
            ],

            # Pattern learner
            'patterns': [
                (r'detect\s+patterns?\s+in\s+(.+)', 'detect_sequence_pattern', {'sequence': 1}),
                (r'find\s+correlation\s+between\s+(.+)\s+and\s+(.+)', 'detect_correlation', {'a': 1, 'b': 2}),
                (r'(is|check)\s+(.+)\s+anomaly', 'detect_anomaly', {'value': 2}),
                (r'(what|show)\s+pattern\s+summary', 'get_pattern_summary', {}),
            ],
        }

    def parse(self, user_input: str) -> Intent:
        """
        Parse natural language input into intent

        Args:
            user_input: Natural language request

        Returns:
            Parsed intent
        """
        user_input = user_input.lower().strip()

        # Try to match patterns for each system
        for system_name, patterns in self.patterns.items():
            for pattern, action, param_map in patterns:
                match = re.search(pattern, user_input, re.IGNORECASE)

                if match:
                    # Extract parameters from regex groups
                    parameters = {}
                    for param_name, group_idx in param_map.items():
                        if isinstance(group_idx, int) and group_idx <= len(match.groups()):
                            parameters[param_name] = match.group(group_idx).strip()
                        else:
                            parameters[param_name] = group_idx

                    # Handle special cases
                    if 'success' in parameters:
                        parameters['success'] = parameters['success'] == 'success'

                    return Intent(
                        action=action,
                        system=system_name,
                        parameters=parameters,
                        confidence=0.9
                    )

        # No pattern matched - try to infer from context
        if self.context['last_system']:
            # Assume continuation of last system
            return Intent(
                action='general_query',
                system=self.context['last_system'],
                parameters={'query': user_input},
                confidence=0.5
            )

        # Can't parse
        return Intent(
            action='unknown',
            system='none',
            parameters={'raw_input': user_input},
            confidence=0.0
        )

    def execute(self, user_input: str) -> str:
        """
        Parse and execute natural language request

        Args:
            user_input: Natural language request

        Returns:
            Natural language response
        """
        # Parse intent
        intent = self.parse(user_input)

        if intent.confidence < 0.3:
            return self._handle_unknown(user_input)

        # Update context
        self.context['last_system'] = intent.system
        self.context['last_action'] = intent.action

        # Get system
        system = self.systems.get(intent.system)
        if not system:
            return f"System '{intent.system}' is not available. Available systems: {list(self.systems.keys())}"

        # Execute action
        try:
            result = self._execute_action(system, intent.action, intent.parameters)
            return self._format_response(intent.system, intent.action, result)

        except Exception as e:
            return f"Error executing {intent.action}: {str(e)}"

    def _execute_action(self, system: Any, action: str, parameters: Dict) -> Any:
        """Execute action on system"""
        # Get method
        method = getattr(system, action, None)

        if not method:
            raise AttributeError(f"System does not have action '{action}'")

        # Call method with parameters
        if not parameters:
            return method()
        else:
            # Try to call with parameters
            try:
                return method(**parameters)
            except TypeError:
                # Try with positional args
                return method(*parameters.values())

    def _format_response(self, system: str, action: str, result: Any) -> str:
        """Format result as natural language response"""
        if result is None:
            return f"Completed {action} on {system} system."

        # Format based on result type
        if isinstance(result, bool):
            return f"{'Success' if result else 'Failed'}: {action}"

        if isinstance(result, (int, float)):
            return f"Result: {result}"

        if isinstance(result, str):
            return result

        if isinstance(result, dict):
            return self._format_dict(result)

        if isinstance(result, list):
            if not result:
                return f"No results found."
            return f"Found {len(result)} results:\n" + "\n".join(str(r)[:100] for r in result[:5])

        return f"Completed: {str(result)[:200]}"

    def _format_dict(self, data: Dict) -> str:
        """Format dictionary as readable text"""
        lines = []
        for key, value in data.items():
            if isinstance(value, (list, dict)):
                lines.append(f"{key}: {len(value) if isinstance(value, list) else 'complex'}")
            else:
                lines.append(f"{key}: {value}")

        return "\n".join(lines[:10])

    def _handle_unknown(self, user_input: str) -> str:
        """Handle unknown intent"""
        return (
            f"I'm not sure how to help with: '{user_input}'\n\n"
            f"I can help with:\n"
            f"- Vision: 'take screenshot', 'read text from screen', 'verify X is on screen'\n"
            f"- Memory: 'remember X', 'what do you know about X', 'show my preferences'\n"
            f"- Reasoning: 'think about X', 'generate plan for X', 'simulate X'\n"
            f"- Proactive: 'start monitoring', 'show opportunities', 'show issues'\n"
            f"- Multi-Agent: 'spawn agent', 'decompose task X'\n"
            f"- Learning: 'choose best X', 'show learned about X'\n"
            f"- Patterns: 'detect patterns in X', 'find correlation between X and Y'"
        )

    def chat(self):
        """Interactive chat mode"""
        print("Natural Language Interface")
        print("=" * 70)
        print("Talk to all agentic systems naturally. Type 'quit' to exit.\n")

        while True:
            try:
                user_input = input("You: ").strip()

                if not user_input:
                    continue

                if user_input.lower() in ['quit', 'exit', 'bye']:
                    print("Goodbye!")
                    break

                response = self.execute(user_input)
                print(f"\nAssistant: {response}\n")

            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except EOFError:
                break
            except Exception as e:
                print(f"Error: {e}\n")

    def close(self):
        """Close all systems"""
        for system in self.systems.values():
            if hasattr(system, 'close'):
                try:
                    system.close()
                except:
                    pass


# === TEST CODE ===

def main():
    """Test natural language interface"""
    print("Testing Natural Language Interface")
    print("=" * 70)

    nl = NaturalLanguageInterface()

    try:
        # Test various natural language inputs
        test_inputs = [
            "take a screenshot",
            "remember this is a test",
            "show my preferences",
            "think about optimizing the database",
            "start monitoring",
            "show learning summary",
            "spawn agent TestAgent",
            "what do you know about optimization",
        ]

        print("\nTesting natural language parsing...")
        for i, user_input in enumerate(test_inputs, 1):
            print(f"\n{i}. Input: '{user_input}'")

            intent = nl.parse(user_input)
            print(f"   Parsed: {intent.system}.{intent.action}")
            print(f"   Parameters: {intent.parameters}")
            print(f"   Confidence: {intent.confidence:.0%}")

        print(f"\n[OK] Natural Language Interface working!")
        print(f"Systems loaded: {list(nl.systems.keys())}")

        # Offer interactive mode
        print("\nStarting interactive mode (Ctrl+C to exit)...")
        nl.chat()

    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        nl.close()


if __name__ == "__main__":
    main()
