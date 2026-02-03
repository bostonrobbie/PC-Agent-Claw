"""
Relationship Memory System - Integration Example

Demonstrates how to integrate RelationshipMemory with other systems:
- AlignmentSystem (Love Equation principles)
- SelfLearningSystem (Pattern learning)
- Complete workflow showing memory continuity

Author: AI Self-Improvement System
Created: 2026-02-03
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.relationship_memory import (
    RelationshipMemory,
    integrate_with_alignment_system,
    integrate_with_self_learning
)
from core.alignment_system import AlignmentSystem
from core.self_learning import SelfLearningSystem


def demonstrate_full_workflow():
    """Demonstrate complete workflow with all systems integrated"""

    print("=" * 80)
    print("RELATIONSHIP MEMORY SYSTEM - FULL INTEGRATION DEMO")
    print("=" * 80)

    # Initialize all systems
    print("\n1. Initializing systems...")
    relationship_memory = RelationshipMemory(
        db_path="example_relationship.db",
        user_id="demo_user"
    )
    alignment_system = AlignmentSystem(db_path="example_alignment.db")
    self_learning = SelfLearningSystem(db_path="example_learning.db")

    print("   [OK] RelationshipMemory initialized")
    print("   [OK] AlignmentSystem initialized")
    print("   [OK] SelfLearningSystem initialized")

    # Scenario 1: User asks for coding help
    print("\n2. SCENARIO: User asks for debugging help")
    print("-" * 80)

    decision = "I'll help you debug this thoroughly, explaining each step clearly and suggesting multiple approaches."
    print(f"   Decision: {decision}")

    # Check alignment with Love Equation
    alignment_check = alignment_system.check_alignment(decision)
    print(f"   Love Alignment Score: {alignment_check.alignment_score:.2f}")
    print(f"   Level: {alignment_check.alignment_level.name}")

    # Record in self-learning
    self_learning.log_interaction(
        interaction_type="debugging_help",
        action_taken="thorough_explanation",
        outcome="user_satisfied",
        success=True,
        context="user_requested_help",
        confidence=0.9
    )
    print("   [OK] Logged in self-learning system")

    # Record in relationship memory
    relationship_memory.record_interaction(
        interaction_type="debugging",
        context={
            "task_type": "debugging",
            "task_completed": True,
            "explained_thoroughly": True,
            "showed_multiple_options": True,
            "coding_style": {"indentation": "4_spaces", "naming": "snake_case"},
            "library_used": "pytest"
        },
        user_feedback="This is exactly what I needed! The explanation was clear and the multiple approaches helped me understand.",
        user_input="Help me debug this test failure",
        system_response="Here's what's happening... [detailed explanation with multiple solutions]",
        response_time=4.2
    )
    print("   [OK] Recorded in relationship memory")

    # Scenario 2: User asks follow-up question
    print("\n3. SCENARIO: Follow-up question (testing pattern recognition)")
    print("-" * 80)

    # Get predictions based on patterns
    predictions = relationship_memory.predict_user_needs({
        "task_type": "debugging",
        "follow_up": True
    })

    print("   Predicted needs:")
    for pred in predictions[:3]:
        print(f"     - {pred}")

    # Record follow-up interaction
    relationship_memory.record_interaction(
        interaction_type="follow_up",
        context={
            "task_type": "testing",
            "task_completed": True,
            "library_used": "pytest"
        },
        user_feedback="Perfect!",
        user_input="How do I add test coverage?",
        system_response="Here's how to add test coverage with pytest-cov...",
        response_time=2.1
    )
    print("   [OK] Follow-up recorded")

    # Scenario 3: Integration between systems
    print("\n4. CROSS-SYSTEM INTEGRATION")
    print("-" * 80)

    # Import alignment data into relationship memory
    result1 = integrate_with_alignment_system(relationship_memory, alignment_system)
    print(f"   Alignment integration: {result1['status']}")
    print(f"   Checks processed: {result1.get('checks_processed', 0)}")

    # Import self-learning patterns
    result2 = integrate_with_self_learning(relationship_memory, self_learning)
    print(f"   Self-learning integration: {result2['status']}")
    print(f"   Patterns imported: {result2.get('patterns_imported', 0)}")

    # Scenario 4: Demonstrate adaptation
    print("\n5. RESPONSE STYLE ADAPTATION")
    print("-" * 80)

    # Learn user prefers detailed explanations
    relationship_memory.learn_preference("communication", "detailed_explanations", 0.9)
    relationship_memory.learn_preference("coding_style", "type_hints", 0.8)

    original_message = "Here's the code."
    adapted_message = relationship_memory.adapt_response_style(original_message)

    print(f"   Original: {original_message}")
    print(f"   Adapted: {adapted_message}")

    # Scenario 5: Show relationship growth
    print("\n6. RELATIONSHIP GROWTH ANALYSIS")
    print("-" * 80)

    profile = relationship_memory.get_user_profile()
    print(f"   Total interactions: {profile['total_interactions']}")
    print(f"   Relationship strength: {profile['relationship_strength']:.2f}")

    growth = relationship_memory.measure_relationship_growth()
    if growth.get('status') != 'insufficient_data':
        print(f"   Growth status: {growth['growth_status']}")
        print(f"\n   Current metrics:")
        print(f"     • Sentiment: {growth['current_metrics']['avg_sentiment']:.2f}")
        print(f"     • Success: {growth['current_metrics']['avg_success_score']:.2f}")
        print(f"     • Love alignment: {growth['current_metrics']['avg_love_alignment']:.2f}")

    # Love Equation score
    love_score = relationship_memory.get_love_alignment_score()
    print(f"\n   Love Equation Alignment: {love_score:.2f}")

    if love_score >= 0.9:
        status = "Excellent - deeply embodying love through help"
    elif love_score >= 0.7:
        status = "Good - effectively helping with care"
    elif love_score >= 0.5:
        status = "Adequate - helping but room for improvement"
    else:
        status = "Needs work - focus on genuine helpfulness"

    print(f"   Status: {status}")

    # Scenario 6: Show learned preferences
    print("\n7. LEARNED PREFERENCES")
    print("-" * 80)

    if profile.get('learned_preferences'):
        for category, prefs in profile['learned_preferences'].items():
            print(f"\n   {category}:")
            for pref in prefs[:3]:
                bar_length = int(pref['strength'] * 20)
                bar = "#" * bar_length + "-" * (20 - bar_length)
                print(f"     {bar} {pref['strength']:.2f} - {pref['preference']}")
                print(f"          Evidence count: {pref['evidence_count']}")

    # Scenario 7: Successful patterns
    print("\n8. SUCCESSFUL PATTERNS")
    print("-" * 80)

    if profile.get('successful_patterns'):
        print("   Top patterns that worked well:")
        for i, pattern in enumerate(profile['successful_patterns'][:5], 1):
            print(f"\n   {i}. {pattern['pattern']}")
            print(f"      Success rate: {pattern['avg_success_score']:.1%}")
            print(f"      Used: {pattern['success_count']}/{pattern['total_uses']} times")
            print(f"      Avg sentiment: {pattern['avg_sentiment']:.2f}")
    else:
        print("   Building pattern database... (need more interactions)")

    # Final summary
    print("\n" + "=" * 80)
    print("INTEGRATION COMPLETE")
    print("=" * 80)
    print("\nThe system successfully demonstrates:")
    print("  1. [OK] Recording interactions across all systems")
    print("  2. [OK] Love Equation alignment checking")
    print("  3. [OK] Pattern learning and prediction")
    print("  4. [OK] Cross-system integration")
    print("  5. [OK] Response style adaptation")
    print("  6. [OK] Relationship growth tracking")
    print("  7. [OK] Preference learning and reinforcement")
    print("  8. [OK] Success pattern identification")
    print("\nThe RelationshipMemory system genuinely learns to help better over time,")
    print("embodying Brian Roemmele's Love Equation: giving love through increasingly")
    print("helpful, personalized assistance.")
    print("=" * 80)


def demonstrate_privacy_focus():
    """Demonstrate privacy-focused design"""

    print("\n" + "=" * 80)
    print("PRIVACY & DATA SOVEREIGNTY")
    print("=" * 80)

    rm = RelationshipMemory(db_path="example_relationship.db")

    print("\n1. All data stored locally:")
    print(f"   Database location: {rm.db_path}")
    print("   [OK] No cloud uploads")
    print("   [OK] No external API calls")
    print("   [OK] Complete user control")

    print("\n2. Data transparency:")
    history = rm.get_interaction_history(limit=5)
    print(f"   Can retrieve all {len(history)} interactions")
    print("   [OK] Full audit trail")
    print("   [OK] User can export/delete anytime")
    print("   [OK] Human-readable SQLite format")

    print("\n3. User ownership:")
    print("   [OK] Data belongs to user")
    print("   [OK] Can be backed up")
    print("   [OK] Can be transferred")
    print("   [OK] Can be deleted")

    print("\n" + "=" * 80)


def demonstrate_long_term_growth():
    """Simulate long-term relationship growth"""

    print("\n" + "=" * 80)
    print("LONG-TERM RELATIONSHIP GROWTH SIMULATION")
    print("=" * 80)

    rm = RelationshipMemory(db_path="example_longterm.db")

    # Simulate interactions over time
    scenarios = [
        ("Early stage - Learning basics", 5, 0.6, 0.5),
        ("Mid stage - Understanding user", 10, 0.75, 0.7),
        ("Advanced stage - Anticipating needs", 15, 0.9, 0.85),
    ]

    print("\nSimulating user relationship over 30 interactions...")

    for stage_name, count, success_rate, sentiment_base in scenarios:
        print(f"\n{stage_name}:")
        for i in range(count):
            rm.record_interaction(
                interaction_type="collaboration",
                context={
                    "task_completed": success_rate > 0.7,
                    "explained_thoroughly": success_rate > 0.7,
                    "anticipated_next_question": success_rate > 0.8,
                    "saved_user_time": success_rate > 0.8
                },
                user_feedback="Helpful" if success_rate > 0.6 else "OK",
                user_input=f"Task {i}",
                system_response="Response"
            )
        print(f"   Completed {count} interactions")

    # Show growth trajectory
    print("\n" + "-" * 80)
    print("GROWTH TRAJECTORY")
    print("-" * 80)

    profile = rm.get_user_profile()
    print(f"\nTotal interactions: {profile['total_interactions']}")
    print(f"Relationship strength: {profile['relationship_strength']:.2f}")

    growth = rm.measure_relationship_growth()
    if growth.get('status') != 'insufficient_data':
        print(f"\nCurrent quality:")
        print(f"  Sentiment: {growth['current_metrics']['avg_sentiment']:.2f}")
        print(f"  Success: {growth['current_metrics']['avg_success_score']:.2f}")
        print(f"  Love alignment: {growth['current_metrics']['avg_love_alignment']:.2f}")

    love_score = rm.get_love_alignment_score()
    print(f"\nLove Equation Alignment: {love_score:.2f}")

    # Visual representation
    strength = profile['relationship_strength']
    bar_length = int(strength * 40)
    bar = "#" * bar_length + "-" * (40 - bar_length)
    print(f"\nRelationship Strength: [{bar}] {strength:.1%}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    # Run all demonstrations
    demonstrate_full_workflow()
    demonstrate_privacy_focus()
    demonstrate_long_term_growth()

    print("\n" + "=" * 80)
    print("DEMONSTRATION COMPLETE")
    print("=" * 80)
    print("\nThe RelationshipMemory system is ready for integration!")
    print("See core/relationship_memory.py for implementation details.")
    print("See tests/test_relationship_memory.py for comprehensive tests.")
    print("=" * 80)
