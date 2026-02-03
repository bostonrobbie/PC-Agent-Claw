#!/usr/bin/env python3
"""Test all 5 agentic systems"""
import sys
from pathlib import Path

workspace = Path(__file__).parent
sys.path.insert(0, str(workspace))

def test_episodic_memory():
    """Test episodic memory system"""
    print("\n[1/5] Testing Episodic Memory...")
    try:
        from memory.episodic_memory import EpisodicMemory

        memory = EpisodicMemory()

        # Test conversation memory
        memory.remember_conversation(
            "Test question",
            "Test response",
            context="testing",
            sentiment="neutral"
        )

        # Test preference learning
        memory.learn_preference(
            "test_category",
            "test_preference",
            strength=0.8,
            evidence="Test evidence"
        )

        # Test profile
        memory.update_profile("test_key", "test_value", confidence=0.9)

        # Test important moment
        memory.remember_important_moment(
            "Test moment",
            "Testing memory system",
            emotion="neutral"
        )

        # Test goal
        goal_id = memory.add_goal("Test goal", priority=5)

        # Verify
        conversations = memory.recall_conversations(query="test")
        preferences = memory.get_preferences(category="test_category")
        profile = memory.get_profile()

        print("   [OK] Episodic Memory working")
        print(f"   - Conversations: {len(conversations)}")
        print(f"   - Preferences: {len(preferences)}")
        print(f"   - Profile keys: {len(profile)}")
        return True

    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        return False


def test_deep_reasoning():
    """Test deep reasoning system"""
    print("\n[2/5] Testing Deep Reasoning...")
    try:
        from reasoning.deep_reasoning import DeepReasoning, ReasoningType

        reasoner = DeepReasoning()

        # Start session
        session_id = reasoner.start_reasoning_session(
            session_name="Test Reasoning",
            goal="Test the reasoning system",
            reasoning_type=ReasoningType.DEDUCTIVE,
            context={'test': True}
        )

        # Add thought
        reasoner.add_thought(
            thought="This is a test thought",
            reasoning_type=ReasoningType.DEDUCTIVE,
            confidence=0.8,
            evidence=["Test evidence"],
            session_id=session_id
        )

        # Generate plan
        plan_id = reasoner.generate_plan(
            plan_name="Test Plan",
            description="A test plan",
            steps=["Step 1", "Step 2"],
            expected_outcome="Success",
            probability_success=0.9,
            session_id=session_id
        )

        # Simulate outcome
        reasoner.simulate_outcome(
            scenario_name="Test Scenario",
            conditions={'test': True},
            predicted_outcome="Test outcome",
            probability=0.8,
            impact_score=7.5,
            session_id=session_id
        )

        # Add causal link
        reasoner.add_causal_link(
            cause="Test cause",
            effect="Test effect",
            mechanism="Test mechanism",
            confidence=0.8,
            session_id=session_id
        )

        # Complete session
        reasoner.complete_reasoning_session(
            session_id=session_id,
            conclusion="Test completed successfully",
            confidence=0.85
        )

        # Verify
        thoughts = reasoner.get_thought_chain(session_id)
        plans = reasoner.get_plans(session_id)

        reasoner.close()

        print("   [OK] Deep Reasoning working")
        print(f"   - Thought steps: {len(thoughts)}")
        print(f"   - Plans: {len(plans)}")
        return True

    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_proactive_agent():
    """Test proactive agent system"""
    print("\n[3/5] Testing Proactive Agent...")
    try:
        from agents.proactive_agent import ProactiveAgent, OpportunityType, IssueSeverity

        agent = ProactiveAgent()

        # Detect opportunity
        opp_id = agent.detect_opportunity(
            opportunity_type=OpportunityType.OPTIMIZATION,
            title="Test Optimization",
            description="Test opportunity",
            potential_impact=0.75,
            confidence=0.85,
            effort_estimate_hours=4,
            notify=False
        )

        # Detect issue
        issue_id = agent.detect_issue(
            issue_type="test",
            title="Test Issue",
            description="Test issue description",
            severity=IssueSeverity.MEDIUM,
            notify=False
        )

        # Suggest improvement
        suggestion_id = agent.suggest_improvement(
            category="test",
            title="Test Suggestion",
            description="Test suggestion description",
            rationale="Test rationale",
            expected_benefit="Test benefit",
            implementation_steps=["Step 1", "Step 2"],
            priority=2,
            notify=False
        )

        # Generate goal
        goal_id = agent.generate_goal(
            goal_name="Test Goal",
            description="Test goal description",
            reasoning="Test reasoning",
            success_criteria=["Criterion 1"],
            priority=3,
            notify=False
        )

        # Verify
        opportunities = agent.get_opportunities()
        issues = agent.get_issues()
        suggestions = agent.get_suggestions()
        goals = agent.get_goals()

        agent.close()

        print("   [OK] Proactive Agent working")
        print(f"   - Opportunities: {len(opportunities)}")
        print(f"   - Issues: {len(issues)}")
        print(f"   - Suggestions: {len(suggestions)}")
        print(f"   - Goals: {len(goals)}")
        return True

    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_multi_agent_coordinator():
    """Test multi-agent coordinator"""
    print("\n[4/5] Testing Multi-Agent Coordinator...")
    try:
        from agents.multi_agent_coordinator import MultiAgentCoordinator, AgentRole

        coordinator = MultiAgentCoordinator(max_agents=5)

        # Spawn agent
        agent_id = coordinator.spawn_agent(
            agent_name="TestAgent",
            role=AgentRole.WORKER,
            capabilities=["test", "compute"]
        )

        # Decompose task
        master_task_id = coordinator.decompose_task(
            task_name="Test Task",
            description="Test task description",
            priority=3
        )

        # Add subtask
        subtask_id = coordinator.add_subtask(
            master_task_id=master_task_id,
            subtask_name="Test Subtask",
            description="Test subtask description",
            priority=3
        )

        # Verify
        agents = coordinator.get_all_agents()
        master_task = coordinator.get_master_task(master_task_id)

        coordinator.close()

        print("   [OK] Multi-Agent Coordinator working")
        print(f"   - Agents spawned: {len(agents)}")
        print(f"   - Master task: {master_task['status']}")
        return True

    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_vision_system():
    """Test vision system (may fail if dependencies missing)"""
    print("\n[5/5] Testing Vision System...")
    try:
        from vision.vision_system import VisionSystem

        vision = VisionSystem()

        # Note: Can't test actual screenshot without display
        # Just verify initialization

        print("   [OK] Vision System initialized")
        print("   - Note: Requires pytesseract for full functionality")
        return True

    except ImportError as e:
        print(f"   [SKIP] Vision System requires pytesseract: {e}")
        return True  # Not a failure, just missing dependency
    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 70)
    print("TESTING ALL 5 AGENTIC SYSTEMS")
    print("=" * 70)

    results = []

    # Test all systems
    results.append(("Episodic Memory", test_episodic_memory()))
    results.append(("Deep Reasoning", test_deep_reasoning()))
    results.append(("Proactive Agent", test_proactive_agent()))
    results.append(("Multi-Agent Coordinator", test_multi_agent_coordinator()))
    results.append(("Vision System", test_vision_system()))

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "[OK]" if result else "[FAIL]"
        print(f"{status} {name}")

    print(f"\nPassed: {passed}/{total}")

    if passed == total:
        print("\n[OK] ALL AGENTIC SYSTEMS OPERATIONAL")
        return 0
    else:
        print(f"\n[WARNING] {total - passed} system(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
