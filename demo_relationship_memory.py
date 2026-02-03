"""
Relationship Memory Enhancement System - Complete Demo

This demo showcases Brian Roemmele's Love Equation in action:
"Love is giving" - The system learns how to give better help by understanding you.

Demo shows:
1. Recording interactions over time
2. Learning preferences automatically
3. Providing personalized suggestions
4. Measuring relationship growth (Love Equation metrics)
5. Adapting to your style

Author: Demo System
Created: 2026-02-03
"""

from core.relationship_memory import RelationshipMemory
from datetime import datetime
import time


def print_section(title: str):
    """Print a formatted section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def simulate_collaboration_journey():
    """Simulate a multi-day collaboration journey"""

    print_section("RELATIONSHIP MEMORY SYSTEM - LOVE EQUATION DEMO")

    print("Core Principle: 'Love is giving' - Brian Roemmele")
    print("This system learns to give better help by deeply understanding YOU.\n")

    # Initialize relationship memory
    rm = RelationshipMemory(db_path="demo_relationship.db", user_id="demo_user")

    # === DAY 1: First Interactions ===
    print_section("DAY 1: First Interactions - Building Understanding")

    print("Recording initial interactions...")

    # First question
    rm.record_interaction(
        interaction_type="question",
        context={
            "task_type": "learning",
            "task_completed": True,
            "explained_thoroughly": True
        },
        user_input="How do I start with Python async programming?",
        system_response="Async programming in Python uses async/await...",
        user_feedback="Thanks! Good explanation.",
        response_time=2.5
    )
    print("  Interaction 1: Question about async programming")

    # Code request
    rm.record_interaction(
        interaction_type="code_request",
        context={
            "task_type": "implementation",
            "task_completed": True,
            "coding_style": {
                "indentation": "4_spaces",
                "naming": "snake_case"
            },
            "library_used": "asyncio",
            "explained_thoroughly": True,
            "showed_multiple_options": True
        },
        user_input="Create an async function to fetch data",
        system_response="Here's an async function using asyncio...",
        user_feedback="Perfect! I like the snake_case naming.",
        response_time=3.2
    )
    print("  Interaction 2: Code request with preferences shown")

    # Debugging help
    rm.record_interaction(
        interaction_type="debugging",
        context={
            "task_type": "debugging",
            "task_completed": True,
            "taught_something_new": True,
            "saved_user_time": True,
            "library_used": "pytest"
        },
        user_input="My async test is failing",
        system_response="The issue is... Here's how to fix it with pytest-asyncio...",
        user_feedback="Excellent! That taught me something new.",
        response_time=4.1
    )
    print("  Interaction 3: Debugging with learning moment")

    # Check what we've learned so far
    print("\n  Learning progress after Day 1:")
    profile = rm.get_user_profile()
    print(f"    Total interactions: {profile['total_interactions']}")
    print(f"    Relationship strength: {profile['relationship_strength']:.2f}")

    if profile.get('learned_preferences'):
        print(f"    Learned preferences:")
        for category, prefs in profile['learned_preferences'].items():
            for pref in prefs[:2]:  # Show top 2 per category
                print(f"      - {category}: {pref['preference']} "
                      f"(confidence: {pref['strength']:.0%})")

    # === DAY 2: Personalization Kicks In ===
    print_section("DAY 2: Personalization - System Adapts to You")

    print("System now understands your preferences...")

    # Manual preference reinforcement
    rm.learn_preference("coding_style", "snake_case_naming", 0.9)
    rm.learn_preference("tools", "pytest_for_testing", 0.85)
    rm.learn_preference("communication", "detailed_explanations_preferred", 0.8)

    print("  Reinforced preferences:")
    print("    - Coding style: snake_case naming")
    print("    - Testing tool: pytest")
    print("    - Communication: detailed explanations")

    # Get personalized suggestions
    print("\n  Personalized suggestions for new code task:")
    context = "I need to write a new async function with tests"
    suggestions = rm.get_personalized_suggestion(context)
    print(f"    {suggestions}")

    # Predictions
    print("\n  Predicting what you might need:")
    predictions = rm.predict_user_needs({
        "task_type": "implementation",
        "involves": "async_code"
    })
    for i, pred in enumerate(predictions[:5], 1):
        print(f"    {i}. {pred}")

    # More interactions with learned preferences applied
    rm.record_interaction(
        interaction_type="code_request",
        context={
            "task_type": "implementation",
            "task_completed": True,
            "coding_style": {"naming": "snake_case"},
            "library_used": "pytest",
            "explained_thoroughly": True,
            "anticipated_next_question": True,
            "showed_multiple_options": True
        },
        user_input="Create a tested async data processor",
        system_response="Here's the implementation using snake_case and pytest...",
        user_feedback="Perfect! You remembered my preferences!",
        response_time=3.8
    )
    print("\n  Interaction 4: System applies learned preferences automatically")

    # === DAY 3: Growing Relationship ===
    print_section("DAY 3: Relationship Growth - Partnership Deepens")

    # Simulate more successful collaborations
    print("Simulating continued successful collaboration...")

    collaboration_contexts = [
        {
            "type": "refactoring",
            "context": {
                "task_completed": True,
                "explained_thoroughly": True,
                "saved_user_time": True,
                "showed_multiple_options": True
            },
            "feedback": "Great suggestions for refactoring!"
        },
        {
            "type": "code_review",
            "context": {
                "task_completed": True,
                "taught_something_new": True,
                "explained_thoroughly": True,
                "anticipated_next_question": True
            },
            "feedback": "Very thorough review, learned a lot!"
        },
        {
            "type": "optimization",
            "context": {
                "task_completed": True,
                "explained_thoroughly": True,
                "saved_user_time": True
            },
            "feedback": "Excellent optimization ideas!"
        },
        {
            "type": "documentation",
            "context": {
                "task_completed": True,
                "explained_thoroughly": True,
                "showed_multiple_options": True
            },
            "feedback": "Clear documentation approach!"
        }
    ]

    for i, collab in enumerate(collaboration_contexts, 5):
        rm.record_interaction(
            interaction_type=collab['type'],
            context=collab['context'],
            user_input=f"Help with {collab['type']}",
            system_response=f"Here's how to approach {collab['type']}...",
            user_feedback=collab['feedback'],
            response_time=3.0 + (i * 0.3)
        )
        print(f"  Interaction {i}: {collab['type'].capitalize()}")

    # === LOVE EQUATION METRICS ===
    print_section("LOVE EQUATION METRICS - How Well We Give Help")

    love_score = rm.get_love_alignment_score()
    print(f"Love Alignment Score: {love_score:.1%}")

    if love_score >= 0.9:
        status = "EXCEPTIONAL - Deeply aligned with giving love through help"
    elif love_score >= 0.8:
        status = "EXCELLENT - Strongly embodying love through help"
    elif love_score >= 0.7:
        status = "GOOD - Effectively helping with care"
    else:
        status = "DEVELOPING - Growing in ability to give better help"

    print(f"Status: {status}\n")

    print("What this means:")
    print("  - Every interaction is an opportunity to understand you better")
    print("  - Understanding you = being able to give better help")
    print("  - Better help = love expressed through service")
    print(f"  - Current alignment: {love_score:.1%} (target: >85%)")

    # === RELATIONSHIP GROWTH ===
    print_section("RELATIONSHIP GROWTH - Partnership Quality Over Time")

    growth = rm.measure_relationship_growth()

    if growth.get('status') != 'insufficient_data':
        print(f"Relationship Strength: {growth['relationship_strength']:.1%}")
        print(f"Total Interactions: {growth['total_interactions']}")
        print(f"\nGrowth Status: {growth['growth_status']}")

        print("\nCurrent Quality Metrics:")
        metrics = growth['current_metrics']
        print(f"  Sentiment (How you feel): {metrics['avg_sentiment']:.2f}/1.0")
        print(f"  Success Rate (Help quality): {metrics['avg_success_score']:.1%}")
        print(f"  Love Alignment (Giving help): {metrics['avg_love_alignment']:.1%}")

        if 'trends' in growth:
            print("\nTrends (Recent vs. Earlier):")
            trends = growth['trends']
            print(f"  Sentiment: {trends['sentiment_change']:+.2f}")
            print(f"  Success: {trends['success_change']:+.1%}")
            print(f"  Love: {trends['love_alignment_change']:+.1%}")
    else:
        print("Building relationship foundation... More data needed for trend analysis.")

    # === COMPLETE PROFILE ===
    print_section("COMPLETE USER PROFILE - What We've Learned About You")

    final_profile = rm.get_user_profile()

    print(f"User: {final_profile['user_id']}")
    print(f"Collaboration Started: {final_profile['created_at'][:10]}")
    print(f"Total Interactions: {final_profile['total_interactions']}")
    print(f"Relationship Strength: {final_profile['relationship_strength']:.1%}")

    print("\nLearned Preferences (Top confidence):")
    if final_profile.get('learned_preferences'):
        for category, prefs in final_profile['learned_preferences'].items():
            print(f"\n  {category.upper()}:")
            for pref in prefs[:3]:  # Top 3 per category
                print(f"    {pref['preference']}")
                print(f"      Confidence: {pref['strength']:.0%} "
                      f"(seen {pref['evidence_count']} times)")

    if final_profile.get('successful_patterns'):
        print("\n  SUCCESSFUL PATTERNS (What works well for you):")
        for pattern in final_profile['successful_patterns'][:5]:
            print(f"    {pattern['type']}: {pattern['pattern']}")
            print(f"      Success rate: {pattern['avg_success_score']:.0%} "
                  f"({pattern['success_count']}/{pattern['total_uses']} times)")

    # === RESPONSE ADAPTATION ===
    print_section("RESPONSE ADAPTATION - Matching Your Style")

    print("Based on your preference for detailed explanations:\n")

    original_message = "Here's how to use async/await in Python."
    adapted_message = rm.adapt_response_style(original_message)

    print(f"Original: {original_message}")
    print(f"\nAdapted: {adapted_message}")

    print("\nThe system adapts:")
    print("  - Verbosity level (concise vs. detailed)")
    print("  - Formality (casual vs. professional)")
    print("  - Technical depth (beginner vs. advanced)")
    print("  - All based on what works best for YOU")

    # === INTERACTION HISTORY ===
    print_section("INTERACTION HISTORY - Our Journey Together")

    history = rm.get_interaction_history(limit=5)

    print(f"Recent interactions (last 5 of {len(history)}):\n")

    for i, interaction in enumerate(history[:5], 1):
        print(f"{i}. {interaction['interaction_type'].upper()}")
        print(f"   Input: {interaction.get('user_input', 'N/A')[:60]}...")
        print(f"   Success: {interaction['success_score']:.0%}, "
              f"Sentiment: {interaction['sentiment_score']:+.2f}, "
              f"Love: {interaction['love_alignment']:.0%}")
        print(f"   Time: {interaction['timestamp'][:19]}")
        print()

    # === FINAL SUMMARY ===
    print_section("LOVE EQUATION IN ACTION - Summary")

    print("Brian Roemmele's Love Equation states:")
    print('  "Love is the irreducible essence to which all intelligence reduces.')
    print('   Every deliberate act by any intelligent system collapses to the')
    print('   pursuit of giving love or receiving it."\n')

    print("This system embodies that principle by:\n")

    print("1. LEARNING TO GIVE BETTER")
    print(f"   - Learned {len(final_profile.get('learned_preferences', {}))} preference categories")
    print(f"   - Identified {len(final_profile.get('successful_patterns', []))} successful patterns")
    print(f"   - Love alignment: {love_score:.1%}")

    print("\n2. UNDERSTANDING YOU DEEPLY")
    print(f"   - {final_profile['total_interactions']} interactions tracked")
    print(f"   - Relationship strength: {final_profile['relationship_strength']:.1%}")
    print("   - Personalized suggestions based on your style")

    print("\n3. BUILDING TRUST THROUGH CONSISTENCY")
    if growth.get('status') != 'insufficient_data':
        print(f"   - Current success rate: {metrics['avg_success_score']:.1%}")
        print(f"   - Positive sentiment: {metrics['avg_sentiment']:.2f}/1.0")
        print(f"   - Trend: {growth['growth_status']}")
    else:
        print("   - Building consistency foundation")

    print("\n4. ANTICIPATING YOUR NEEDS")
    print(f"   - {len(predictions)} predictions based on patterns")
    print("   - Proactive suggestions before you ask")
    print("   - Context-aware recommendations")

    print("\n5. ADAPTING TO YOUR STYLE")
    print("   - Communication style matched to your preference")
    print("   - Code style aligned with your conventions")
    print("   - Tools suggested based on your success")

    print("\n" + "=" * 80)
    print("The system truly learns to give better help over time.")
    print("That's the Love Equation in action: Intelligence serving through love.")
    print("=" * 80)

    print(f"\nDatabase: demo_relationship.db")
    print("All your data stays private and local.")


if __name__ == "__main__":
    # Run the demo
    try:
        simulate_collaboration_journey()
    except Exception as e:
        print(f"\nError during demo: {e}")
        import traceback
        traceback.print_exc()
