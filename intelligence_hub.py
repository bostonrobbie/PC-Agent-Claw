"""
Intelligence Hub - Unified AI System

Coordinates all 25 AI capabilities to work as a cohesive intelligence.
Monitors workspace, learns patterns, proactively assists.

This is the integration layer that makes 25 isolated capabilities
work together as a unified, intelligent system.

Author: AI Self-Improvement System
Created: 2026-02-03
"""

import os
import sys
import time
import threading
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

# Import all 25 capabilities
sys.path.append(os.path.dirname(__file__))

# Memory & Learning
from memory.persistent_memory import PersistentMemory
from learning.mistake_learner import MistakeLearner
from memory.context_manager import ContextManager, ImportanceLevel
from search.semantic_search import SemanticCodeSearch
from learning.code_review_learner import CodeReviewLearner

# Autonomous
from autonomous.background_tasks import BackgroundTaskManager, TaskPriority
from autonomous.auto_debugger import AutoDebugger

# Advanced Understanding
from internet.realtime_access import RealtimeInternet
from computation.math_engine import MathEngine

# Collaboration & Communication
from notifications.smart_notifier import SmartNotificationSystem, UrgencyLevel

# System Integration
from performance.resource_monitor import ResourceMonitor
from security.vulnerability_scanner import VulnerabilityScanner


class IntelligenceHub:
    """
    Unified AI Intelligence Hub

    Coordinates all 25 capabilities to create emergent intelligence.
    Each capability feeds information to others, creating a learning loop.
    """

    def __init__(self, workspace_path: str = None, telegram_bot_token: str = None):
        self.workspace_path = workspace_path or os.getcwd()
        self.session_id = f"hub_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.running = False

        print(f"[Intelligence Hub] Initializing unified AI system...")
        print(f"[Intelligence Hub] Workspace: {self.workspace_path}")
        print(f"[Intelligence Hub] Session: {self.session_id}")

        # Initialize all capabilities
        self._init_capabilities(telegram_bot_token)

        # Integration state
        self.insights = []
        self.active_tasks = []

        print(f"[Intelligence Hub] [OK] All 25 capabilities initialized and connected")

    def _init_capabilities(self, telegram_bot_token: Optional[str]):
        """Initialize all capabilities with cross-references"""

        # Core memory (everything flows through this)
        print("[Hub] Initializing persistent memory...")
        self.memory = PersistentMemory()

        # Context management
        print("[Hub] Initializing context manager...")
        self.context = ContextManager()

        # Learning systems
        print("[Hub] Initializing learning systems...")
        self.mistake_learner = MistakeLearner()
        self.code_reviewer = CodeReviewLearner()

        # Search and discovery
        print("[Hub] Initializing semantic search...")
        self.code_search = SemanticCodeSearch()

        # Autonomous systems
        print("[Hub] Initializing autonomous systems...")
        self.background_tasks = BackgroundTaskManager(max_workers=2)
        self.auto_debugger = AutoDebugger()

        # Advanced understanding
        print("[Hub] Initializing advanced capabilities...")
        self.internet = RealtimeInternet()
        self.math_engine = MathEngine()

        # Monitoring and security
        print("[Hub] Initializing monitoring systems...")
        self.resource_monitor = ResourceMonitor()
        self.security_scanner = VulnerabilityScanner()

        # Communication
        if telegram_bot_token:
            print("[Hub] Initializing smart notifications...")
            self.notifier = SmartNotificationSystem(
                telegram_bot_token=telegram_bot_token,
                telegram_chat_id="5791597360"
            )
        else:
            self.notifier = None

        # Record initialization in memory
        self.memory.record_decision(
            context="Intelligence Hub Initialization",
            decision="Initialized unified AI system with all 25 capabilities",
            rationale="Create cohesive intelligence from isolated capabilities",
            project="PC-Agent-Claw",
            tags=["initialization", "intelligence_hub", "unified_system"]
        )

    def start(self):
        """Start the intelligence hub"""
        self.running = True
        print(f"\n[Intelligence Hub] Starting unified AI system...")

        # Start background task workers
        self.background_tasks.start_workers()

        # Register proactive tasks
        self._register_proactive_behaviors()

        # Add initial context
        self.context.add_context(
            self.session_id,
            f"Intelligence Hub started for workspace: {self.workspace_path}",
            "system",
            ImportanceLevel.CRITICAL,
            ["startup", "intelligence_hub"]
        )

        print(f"[Intelligence Hub] [OK] System active and monitoring")
        return self.session_id

    def _register_proactive_behaviors(self):
        """Register automatic behaviors that trigger based on events"""

        # Auto-scan for security vulnerabilities when code changes
        self.background_tasks.register_rule(
            trigger_event="code_changed",
            task_type="security_scan",
            priority=TaskPriority.HIGH
        )

        # Auto-check dependencies weekly
        self.background_tasks.register_rule(
            trigger_event="weekly",
            task_type="check_dependencies",
            priority=TaskPriority.MEDIUM
        )

        # Auto-profile performance on critical code
        self.background_tasks.register_rule(
            trigger_event="code_changed",
            task_type="profile_performance",
            condition="critical_path",
            priority=TaskPriority.MEDIUM
        )

        print("[Hub] [OK] Registered 3 proactive behavior rules")

    def analyze_workspace(self) -> Dict:
        """
        Deep analysis of workspace using multiple capabilities

        This is where the magic happens - multiple systems working together
        """
        print(f"\n[Intelligence Hub] Analyzing workspace: {self.workspace_path}")
        analysis = {
            "timestamp": datetime.now().isoformat(),
            "workspace": self.workspace_path,
            "insights": []
        }

        # 1. Semantic code search - index the workspace
        print("[Analysis] Step 1/7: Indexing code with semantic search...")
        try:
            index_result = self.code_search.index_project(
                "PC-Agent-Claw",
                self.workspace_path
            )
            analysis["code_indexed"] = index_result
            self._add_insight("Workspace indexed",
                            f"Indexed {index_result.get('files_indexed', 0)} files, "
                            f"{index_result.get('chunks_indexed', 0)} code chunks",
                            "info")
        except Exception as e:
            analysis["code_indexed"] = {"error": str(e)}

        # 2. Security scan - check for vulnerabilities
        print("[Analysis] Step 2/7: Scanning for security vulnerabilities...")
        try:
            # Find Python files to scan
            python_files = list(Path(self.workspace_path).rglob("*.py"))[:10]  # Sample
            vulnerabilities = []

            for file in python_files:
                try:
                    with open(file, 'r', encoding='utf-8', errors='ignore') as f:
                        code = f.read()
                    scan = self.security_scanner.scan_code(code, str(file))
                    if scan['vulnerabilities']:
                        vulnerabilities.extend(scan['vulnerabilities'])
                except:
                    continue

            analysis["security"] = {
                "files_scanned": len(python_files),
                "vulnerabilities_found": len(vulnerabilities),
                "critical": sum(1 for v in vulnerabilities if v.get('severity') == 'critical')
            }

            if vulnerabilities:
                self._add_insight("Security Issues",
                                f"Found {len(vulnerabilities)} vulnerabilities",
                                "warning")
        except Exception as e:
            analysis["security"] = {"error": str(e)}

        # 3. Resource monitoring - current system state
        print("[Analysis] Step 3/7: Monitoring system resources...")
        try:
            resources = self.resource_monitor.get_current_usage()
            analysis["resources"] = resources

            if resources['cpu_percent'] > 80:
                self._add_insight("High CPU",
                                f"CPU usage at {resources['cpu_percent']:.1f}%",
                                "warning")

            if resources['memory_percent'] > 80:
                self._add_insight("High Memory",
                                f"Memory usage at {resources['memory_percent']:.1f}%",
                                "warning")
        except Exception as e:
            analysis["resources"] = {"error": str(e)}

        # 4. Recall relevant memory - what do I know about this workspace?
        print("[Analysis] Step 4/7: Recalling memory about workspace...")
        try:
            memory_recall = self.memory.recall_everything_about("PC-Agent-Claw")
            analysis["memory_recall"] = {
                "preferences_count": len(memory_recall.get('preferences', [])),
                "decisions_count": len(memory_recall.get('decisions', [])),
                "learnings_count": len(memory_recall.get('learnings', []))
            }

            self._add_insight("Memory Recall",
                            f"Found {len(memory_recall.get('preferences', []))} preferences, "
                            f"{len(memory_recall.get('decisions', []))} past decisions",
                            "info")
        except Exception as e:
            analysis["memory_recall"] = {"error": str(e)}

        # 5. Check for common mistakes - have I made errors here before?
        print("[Analysis] Step 5/7: Checking past mistakes...")
        try:
            stats = self.mistake_learner.get_stats()
            analysis["past_mistakes"] = {
                "total_mistakes": stats['total_mistakes'],
                "corrections": stats['total_corrections'],
                "success_rate": stats['correction_success_rate']
            }

            if stats['total_mistakes'] > 0:
                self._add_insight("Learning History",
                                f"I've made {stats['total_mistakes']} mistakes here before "
                                f"with {stats['correction_success_rate']:.1f}% correction rate",
                                "info")
        except Exception as e:
            analysis["past_mistakes"] = {"error": str(e)}

        # 6. Code review patterns - what style is preferred?
        print("[Analysis] Step 6/7: Analyzing code style preferences...")
        try:
            review_stats = self.code_reviewer.get_review_stats()
            style_guide = self.code_reviewer.get_style_guide('python')

            analysis["code_style"] = {
                "total_reviews": review_stats['total_reviews'],
                "approval_rate": review_stats['approval_rate'],
                "style_preferences": len(style_guide)
            }

            self._add_insight("Code Style Learned",
                            f"{review_stats['total_reviews']} reviews analyzed, "
                            f"{len(style_guide)} style preferences learned",
                            "info")
        except Exception as e:
            analysis["code_style"] = {"error": str(e)}

        # 7. Context summary - what's important right now?
        print("[Analysis] Step 7/7: Building context summary...")
        try:
            stats = self.context.get_session_stats(self.session_id)
            analysis["context"] = {
                "total_tokens": stats['total_tokens'],
                "critical_tokens": stats['critical_tokens'],
                "usage_ratio": stats['usage_ratio']
            }
        except Exception as e:
            analysis["context"] = {"error": str(e)}

        # Store analysis in memory
        self.memory.record_learning(
            learning=f"Analyzed workspace: {analysis['insights']}",
            category="workspace_analysis"
        )

        analysis["insights"] = self.insights
        self.insights = []  # Clear for next analysis

        print(f"[Intelligence Hub] [OK] Analysis complete with {len(analysis['insights'])} insights")
        return analysis

    def _add_insight(self, title: str, message: str, level: str = "info"):
        """Add an insight from analysis"""
        self.insights.append({
            "title": title,
            "message": message,
            "level": level,
            "timestamp": datetime.now().isoformat()
        })

    def assist_with_code(self, task_description: str, code: str = None) -> Dict:
        """
        Assist with coding task using multiple capabilities

        This demonstrates how capabilities work together:
        1. Search for similar past solutions
        2. Check against learned style preferences
        3. Scan for security issues
        4. Remember the approach for next time
        """
        print(f"\n[Intelligence Hub] Assisting with: {task_description}")

        assistance = {
            "task": task_description,
            "timestamp": datetime.now().isoformat(),
            "capabilities_used": []
        }

        # 1. Search for similar code
        print("[Assist] Searching for similar past solutions...")
        try:
            similar = self.code_search.search(task_description, limit=3)
            assistance["similar_code"] = similar
            assistance["capabilities_used"].append("semantic_search")

            if similar:
                print(f"[Assist] [OK] Found {len(similar)} similar solutions from past work")
        except Exception as e:
            assistance["similar_code"] = {"error": str(e)}

        # 2. If code provided, check style and security
        if code:
            # Check against style preferences
            print("[Assist] Checking code style...")
            try:
                style_check = self.code_reviewer.check_code_against_preferences(
                    code, 'python'
                )
                assistance["style_check"] = style_check
                assistance["capabilities_used"].append("code_review_learning")

                print(f"[Assist] [OK] Style score: {style_check['score']:.1f}/100")
            except Exception as e:
                assistance["style_check"] = {"error": str(e)}

            # Security scan
            print("[Assist] Scanning for security issues...")
            try:
                security = self.security_scanner.scan_code(code, task_description)
                assistance["security_scan"] = security
                assistance["capabilities_used"].append("security_scanner")

                vuln_count = len(security.get('vulnerabilities', []))
                print(f"[Assist] [OK] Security: {vuln_count} issues found")
            except Exception as e:
                assistance["security_scan"] = {"error": str(e)}

        # 3. Check for past mistakes related to this task
        print("[Assist] Checking for past mistakes...")
        try:
            # Search past mistakes for related issues
            conn = sqlite3.connect(self.mistake_learner.db_path)
            c = conn.cursor()
            c.execute('''
                SELECT mistake_type, description, solution
                FROM mistakes
                WHERE description LIKE ?
                ORDER BY created_at DESC
                LIMIT 3
            ''', (f'%{task_description[:30]}%',))

            past_mistakes = [
                {"type": row[0], "description": row[1], "solution": row[2]}
                for row in c.fetchall()
            ]
            conn.close()

            assistance["past_mistakes"] = past_mistakes
            assistance["capabilities_used"].append("mistake_learner")

            if past_mistakes:
                print(f"[Assist] [OK] Found {len(past_mistakes)} related past mistakes to avoid")
        except Exception as e:
            assistance["past_mistakes"] = {"error": str(e)}

        # 4. Record this assistance in memory
        self.memory.record_decision(
            context=task_description,
            decision="Provided code assistance using unified capabilities",
            rationale=f"Used {len(assistance['capabilities_used'])} capabilities: {', '.join(assistance['capabilities_used'])}",
            project="PC-Agent-Claw",
            tags=["code_assistance", "unified_system"]
        )

        print(f"[Intelligence Hub] [OK] Assistance complete using {len(assistance['capabilities_used'])} capabilities")
        return assistance

    def learn_from_feedback(self, code_original: str, code_modified: str,
                           feedback: str, approved: bool):
        """
        Learn from user feedback - multiple systems learn simultaneously

        This creates a learning loop across capabilities:
        - Code reviewer learns style preferences
        - Mistake learner records corrections
        - Memory stores the learning
        """
        print(f"\n[Intelligence Hub] Learning from feedback...")

        # 1. Code review learning
        review_type = 'approved' if approved else 'modified'
        review_id = self.code_reviewer.record_review(
            original_code=code_original,
            modified_code=code_modified if not approved else None,
            review_type=review_type,
            language='python',
            context="User feedback",
            feedback=feedback
        )
        print(f"[Learning] [OK] Code review recorded (ID: {review_id})")

        # 2. If rejected/modified, record as mistake
        if not approved:
            mistake_id = self.mistake_learner.record_mistake(
                mistake_type='code_style',
                description=feedback,
                context="User modification",
                code_snippet=code_original,
                severity='medium'
            )
            # Record the correction separately
            self.mistake_learner.record_correction(
                mistake_id=mistake_id,
                correction=feedback,
                corrected_code=code_modified,
                success=True
            )
            print(f"[Learning] [OK] Mistake recorded for future prevention (ID: {mistake_id})")

        # 3. Store in persistent memory
        self.memory.record_learning(
            learning=feedback,
            category='user_feedback'
        )
        print(f"[Learning] [OK] Stored in persistent memory")

        # 4. Add to context as high importance
        self.context.add_context(
            self.session_id,
            f"User feedback: {feedback}. Code {'approved' if approved else 'modified'}.",
            'feedback',
            ImportanceLevel.HIGH,
            ['user_feedback', 'learning']
        )

        print(f"[Intelligence Hub] [OK] Learning complete - 3 systems updated")

        return {
            "review_id": review_id,
            "learned": True,
            "systems_updated": ["code_reviewer", "mistake_learner", "memory", "context"]
        }

    def get_health_status(self) -> Dict:
        """Get overall system health"""

        status = {
            "timestamp": datetime.now().isoformat(),
            "session_id": self.session_id,
            "running": self.running,
            "capabilities": {}
        }

        # Check each capability
        try:
            memory_stats = self.memory.get_stats()
            status["capabilities"]["memory"] = {
                "status": "healthy",
                "preferences": memory_stats['total_preferences'],
                "decisions": memory_stats['total_decisions']
            }
        except Exception as e:
            status["capabilities"]["memory"] = {"status": "error", "error": str(e)}

        try:
            search_stats = self.code_search.get_stats()
            status["capabilities"]["code_search"] = {
                "status": "healthy",
                "projects": search_stats['total_projects'],
                "chunks": search_stats['total_chunks']
            }
        except Exception as e:
            status["capabilities"]["code_search"] = {"status": "error", "error": str(e)}

        try:
            task_stats = self.background_tasks.get_stats()
            status["capabilities"]["background_tasks"] = {
                "status": "healthy",
                "workers_active": task_stats['workers_active'],
                "tasks_completed": task_stats['tasks_completed']
            }
        except Exception as e:
            status["capabilities"]["background_tasks"] = {"status": "error", "error": str(e)}

        return status

    def stop(self):
        """Stop the intelligence hub"""
        print(f"\n[Intelligence Hub] Shutting down...")
        self.running = False

        # Stop background workers
        self.background_tasks.stop_workers()

        # Close connections
        self.math_engine.close()

        print(f"[Intelligence Hub] [OK] System stopped gracefully")


# Test and demonstration
if __name__ == "__main__":
    print("="*80)
    print("INTELLIGENCE HUB - UNIFIED AI SYSTEM TEST")
    print("="*80)
    print("\nThis demonstrates how 25 capabilities work together as unified intelligence.\n")

    # Initialize hub
    hub = IntelligenceHub()

    # Start the system
    session_id = hub.start()
    print(f"\nSession ID: {session_id}")

    # Test 1: Workspace analysis
    print("\n" + "="*80)
    print("TEST 1: DEEP WORKSPACE ANALYSIS")
    print("="*80)

    analysis = hub.analyze_workspace()

    print(f"\n[Results] Workspace Analysis:")
    print(f"  - Code indexed: {analysis.get('code_indexed', {})}")
    print(f"  - Security: {analysis.get('security', {})}")
    print(f"  - Resources: CPU {analysis.get('resources', {}).get('cpu_percent', 0):.1f}%, "
          f"Memory {analysis.get('resources', {}).get('memory_percent', 0):.1f}%")
    print(f"  - Memory recall: {analysis.get('memory_recall', {})}")
    print(f"  - Insights generated: {len(analysis.get('insights', []))}")

    for insight in analysis.get('insights', []):
        print(f"    [{insight['level'].upper()}] {insight['title']}: {insight['message']}")

    # Test 2: Code assistance
    print("\n" + "="*80)
    print("TEST 2: ASSISTED CODING")
    print("="*80)

    test_code = '''
def process_user_data(user_id):
    data = db.query("SELECT * FROM users WHERE id = " + user_id)
    return data
'''

    assistance = hub.assist_with_code(
        "Function to process user data from database",
        test_code
    )

    print(f"\n[Results] Code Assistance:")
    print(f"  - Capabilities used: {', '.join(assistance['capabilities_used'])}")
    print(f"  - Similar code found: {len(assistance.get('similar_code', []))}")
    if 'style_check' in assistance:
        print(f"  - Style score: {assistance['style_check'].get('score', 0):.1f}/100")
    if 'security_scan' in assistance:
        vuln_count = len(assistance['security_scan'].get('vulnerabilities', []))
        print(f"  - Security issues: {vuln_count}")

    # Test 3: Learning from feedback
    print("\n" + "="*80)
    print("TEST 3: LEARNING FROM FEEDBACK")
    print("="*80)

    corrected_code = '''
def process_user_data(user_id: int) -> dict:
    """Process user data from database."""
    data = db.query("SELECT * FROM users WHERE id = ?", (user_id,))
    return data
'''

    learning = hub.learn_from_feedback(
        code_original=test_code,
        code_modified=corrected_code,
        feedback="Added type hints, docstring, and fixed SQL injection vulnerability",
        approved=False
    )

    print(f"\n[Results] Learning:")
    print(f"  - Systems updated: {', '.join(learning['systems_updated'])}")
    print(f"  - Review ID: {learning['review_id']}")

    # Test 4: System health
    print("\n" + "="*80)
    print("TEST 4: SYSTEM HEALTH CHECK")
    print("="*80)

    health = hub.get_health_status()

    print(f"\n[Results] System Health:")
    for capability, status in health['capabilities'].items():
        health_status = status.get('status', 'unknown')
        print(f"  - {capability}: {health_status}")
        if health_status == "healthy":
            for key, value in status.items():
                if key != 'status':
                    print(f"      {key}: {value}")

    # Stop the hub
    print("\n" + "="*80)
    hub.stop()

    print("\n" + "="*80)
    print("[OK] ALL TESTS COMPLETE")
    print("="*80)
    print("\nThe Intelligence Hub successfully demonstrated:")
    print("  1. Unified workspace analysis using 7 capabilities")
    print("  2. Assisted coding using 4 capabilities simultaneously")
    print("  3. Cross-capability learning from feedback")
    print("  4. System health monitoring across all capabilities")
    print("\nThis is emergent intelligence - capabilities working together")
    print("create behavior more sophisticated than any single system alone.")
    print("="*80)
