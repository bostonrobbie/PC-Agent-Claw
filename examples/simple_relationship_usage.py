"""
Simple Relationship Memory Usage Example

A minimal example showing how to integrate RelationshipMemory
into your existing code.

Author: AI Self-Improvement System
Created: 2026-02-03
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.relationship_memory import RelationshipMemory


def example_coding_session():
    """Example: A typical coding session with the AI"""

    print("=" * 60)
    print("SIMPLE RELATIONSHIP MEMORY EXAMPLE")
    print("=" * 60)

    # Initialize once at start of session
    rm = RelationshipMemory(user_id="developer_123")

    # Scenario 1: User asks for help
    print("\n1. User asks: 'How do I test this async function?'")

    # Your code generates a response...
    response = """You can test async functions with pytest-asyncio:

```python
import pytest

@pytest.mark.asyncio
async def test_my_async_function():
    result = await my_async_function()
    assert result == expected_value
```

Install with: pip install pytest-asyncio
"""

    # Record the interaction
    rm.record_interaction(
        interaction_type="question",
        context={
            "task_type": "testing",
            "library_used": "pytest",
            "explained_thoroughly": True,
            "showed_code_example": True
        },
        user_input="How do I test this async function?",
        system_response=response,
        user_feedback="Thanks! That works perfectly.",
        response_time=2.1
    )

    print(f"Response: {response[:100]}...")
    print("[Interaction recorded]")

    # Scenario 2: Next question
    print("\n2. User asks: 'How do I add test coverage?'")

    # Check what we've learned
    profile = rm.get_user_profile()
    print(f"\nLearned about user:")
    print(f"  - Total interactions: {profile['total_interactions']}")

    # Predict what they might need
    predictions = rm.predict_user_needs({"task_type": "testing"})
    print(f"\nPredicted needs:")
    for pred in predictions[:2]:
        print(f"  - {pred}")

    # Generate adapted response
    original = "Use pytest-cov."
    adapted = rm.adapt_response_style(original)

    print(f"\nOriginal response: '{original}'")
    print(f"Adapted response: '{adapted}'")

    # Record this interaction too
    rm.record_interaction(
        interaction_type="follow_up",
        context={
            "task_type": "testing",
            "library_used": "pytest",
            "follow_up_question": True
        },
        user_input="How do I add test coverage?",
        system_response=adapted,
        user_feedback="Great!",
        response_time=1.5
    )

    print("[Interaction recorded]")

    # Show growth
    print("\n3. Relationship Status:")
    print("-" * 60)

    love_score = rm.get_love_alignment_score()
    print(f"Love Equation Alignment: {love_score:.2%}")

    if love_score >= 0.8:
        print("Status: Excellent - providing genuinely helpful assistance")
    else:
        print("Status: Building relationship...")

    growth = rm.measure_relationship_growth()
    if growth.get('status') != 'insufficient_data':
        print(f"\nRelationship Strength: {growth['relationship_strength']:.2%}")
        print(f"Growth: {growth['growth_status']}")

    print("\n" + "=" * 60)
    print("That's it! The system learns from every interaction.")
    print("=" * 60)


def example_learning_preferences():
    """Example: Learning user preferences over time"""

    print("\n" + "=" * 60)
    print("PREFERENCE LEARNING EXAMPLE")
    print("=" * 60)

    rm = RelationshipMemory(user_id="developer_456")

    # Simulate user consistently using certain patterns
    print("\nSimulating user interactions with consistent style...")

    interactions = [
        {
            "type": "code_request",
            "context": {
                "coding_style": "4_spaces",
                "library_used": "asyncio",
                "task_completed": True
            }
        },
        {
            "type": "code_request",
            "context": {
                "coding_style": "4_spaces",
                "library_used": "asyncio",
                "task_completed": True
            }
        },
        {
            "type": "debugging",
            "context": {
                "coding_style": "4_spaces",
                "library_used": "pytest",
                "task_completed": True
            }
        },
    ]

    for i, interaction in enumerate(interactions, 1):
        rm.record_interaction(
            interaction_type=interaction["type"],
            context=interaction["context"],
            user_input=f"Task {i}",
            system_response="Here you go...",
            user_feedback="Perfect!"
        )

    print(f"Recorded {len(interactions)} interactions")

    # Show what we learned
    profile = rm.get_user_profile()

    print("\nLearned Preferences:")
    print("-" * 60)

    if profile.get('learned_preferences'):
        for category, prefs in profile['learned_preferences'].items():
            print(f"\n{category}:")
            for pref in prefs[:3]:
                confidence = "High" if pref['strength'] > 0.7 else "Medium" if pref['strength'] > 0.4 else "Low"
                print(f"  - {pref['preference']}")
                print(f"    Strength: {pref['strength']:.2f} ({confidence} confidence)")
                print(f"    Evidence: {pref['evidence_count']} observations")

    print("\n" + "=" * 60)
    print("System adapts to THIS user's unique style!")
    print("=" * 60)


def example_pattern_recognition():
    """Example: Recognizing successful patterns"""

    print("\n" + "=" * 60)
    print("PATTERN RECOGNITION EXAMPLE")
    print("=" * 60)

    rm = RelationshipMemory(user_id="developer_789")

    # Simulate a successful pattern
    print("\nSimulating repeated successful pattern...")

    for i in range(5):
        rm.record_interaction(
            interaction_type="implementation",
            context={
                "approach": "test_driven_development",
                "task_completed": True,
                "tests_passed": True,
                "user_satisfied": True
            },
            user_input=f"Implement feature {i}",
            system_response="Using TDD approach...",
            user_feedback="Excellent, tests pass!",
            response_time=3.0
        )

    print("Recorded 5 successful TDD interactions")

    # Now predict for similar task
    print("\nPredicting for new implementation task...")

    predictions = rm.predict_user_needs({"task_type": "implementation"})

    print("\nRecommendations:")
    for pred in predictions:
        print(f"  - {pred}")

    # Show successful patterns
    profile = rm.get_user_profile()

    if profile.get('successful_patterns'):
        print("\nProven Successful Patterns:")
        print("-" * 60)
        for pattern in profile['successful_patterns'][:3]:
            print(f"\n  {pattern['pattern']}")
            print(f"    Success rate: {pattern['avg_success_score']:.1%}")
            print(f"    Times used: {pattern['total_uses']}")
            print(f"    User sentiment: {pattern['avg_sentiment']:.2f}")

    print("\n" + "=" * 60)
    print("System remembers what works best for YOU!")
    print("=" * 60)


if __name__ == "__main__":
    # Run all examples
    example_coding_session()
    example_learning_preferences()
    example_pattern_recognition()

    print("\n" + "=" * 60)
    print("INTEGRATION TIPS")
    print("=" * 60)
    print("""
1. Initialize once per user session:
   rm = RelationshipMemory(user_id="unique_user_id")

2. Record every significant interaction:
   rm.record_interaction(...)

3. Use predictions to be proactive:
   predictions = rm.predict_user_needs(current_context)

4. Adapt your responses:
   adapted = rm.adapt_response_style(message)

5. Check alignment periodically:
   score = rm.get_love_alignment_score()

6. Monitor growth:
   growth = rm.measure_relationship_growth()

The system gets better the more you use it!
    """)
    print("=" * 60)
