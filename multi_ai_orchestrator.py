#!/usr/bin/env python3
"""
Multi-AI Orchestration System
Leverages different AI models as specialized "employees" for different tasks
"""

import requests
import json
from pathlib import Path
from datetime import datetime

WORKSPACE = Path(r"C:\Users\User\.openclaw\workspace")
OLLAMA_API = "http://localhost:11434/api/generate"

class MultiAIOrchestrator:
    """Orchestrate multiple AI models for different tasks"""

    def __init__(self):
        self.available_models = self.get_available_models()
        self.task_assignments = self.define_task_assignments()

    def get_available_models(self):
        """Get list of available Ollama models"""
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                return [m['name'] for m in models]
            return []
        except:
            return []

    def define_task_assignments(self):
        """Map task types to optimal AI models"""
        return {
            # Fast, lightweight tasks
            'quick_analysis': 'qwen2.5:0.5b',  # Smallest, fastest
            'code_review': 'qwen2.5:7b',       # Balanced
            'data_processing': 'qwen2.5:7b',

            # Medium complexity
            'strategy_analysis': 'qwen2.5:7b-32k',  # Large context
            'documentation': 'qwen2.5:7b',
            'debugging': 'qwen2.5:7b',

            # High complexity
            'architecture_design': 'qwen2.5:14b',   # Most capable
            'optimization': 'qwen2.5:14b',
            'creative_work': 'llama3:latest',

            # Specialized
            'vision_tasks': 'qwen2.5vl:7b',  # Vision model
            'embedding': 'nomic-embed-text:latest',
        }

    def query_model(self, model_name, prompt, max_tokens=1000):
        """Query a specific Ollama model"""
        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_predict": max_tokens
            }
        }

        try:
            response = requests.post(OLLAMA_API, json=payload, timeout=120)
            if response.status_code == 200:
                return response.json().get('response', '')
            return None
        except Exception as e:
            print(f"Model query failed: {e}")
            return None

    def assign_task(self, task_type, task_description):
        """Assign task to appropriate AI model"""

        # Get best model for this task type
        model = self.task_assignments.get(task_type, 'qwen2.5:7b')

        # Check if model is available
        if model not in self.available_models:
            # Fallback to qwen2.5:7b if preferred model not available
            model = 'qwen2.5:7b' if 'qwen2.5:7b' in self.available_models else self.available_models[0]

        print(f"\n{'='*70}")
        print(f"TASK ASSIGNMENT")
        print(f"{'='*70}")
        print(f"Task Type: {task_type}")
        print(f"Assigned Model: {model}")
        print(f"Task: {task_description[:100]}...")
        print(f"{'='*70}\n")

        # Execute task
        result = self.query_model(model, task_description)

        return {
            'task_type': task_type,
            'model_used': model,
            'result': result,
            'timestamp': datetime.now().isoformat()
        }

    def parallel_tasks(self, tasks):
        """Execute multiple tasks in parallel (simulate with sequential for now)"""
        results = []

        for task in tasks:
            task_type = task.get('type')
            description = task.get('description')

            result = self.assign_task(task_type, description)
            results.append(result)

        return results

    def code_review_task(self, code_snippet, language='python'):
        """Specialized code review task"""
        prompt = f"""Review this {language} code for:
1. Bugs or errors
2. Performance issues
3. Best practices
4. Security concerns

CODE:
{code_snippet}

Provide concise feedback (max 200 words).
"""
        return self.assign_task('code_review', prompt)

    def strategy_analysis_task(self, strategy_description, metrics):
        """Specialized strategy analysis"""
        prompt = f"""Analyze this trading strategy:

{strategy_description}

METRICS:
{json.dumps(metrics, indent=2)}

Provide:
1. Strengths (2-3 points)
2. Weaknesses (2-3 points)
3. Optimization suggestions (2-3 points)

Keep response concise (max 250 words).
"""
        return self.assign_task('strategy_analysis', prompt)

    def quick_summary_task(self, long_text):
        """Quick summarization using lightweight model"""
        prompt = f"""Summarize this in 3 bullet points:

{long_text}

Format as markdown list.
"""
        return self.assign_task('quick_analysis', prompt)


class AIEmployeePool:
    """Pool of AI "employees" with different specializations"""

    def __init__(self):
        self.orchestrator = MultiAIOrchestrator()
        self.employees = self.create_employee_profiles()

    def create_employee_profiles(self):
        """Define AI employee roles"""
        return {
            'analyst': {
                'name': 'Data Analyst AI',
                'model': 'qwen2.5:7b',
                'specialization': 'Data analysis, metrics, performance review',
                'tasks': ['data_processing', 'quick_analysis']
            },
            'developer': {
                'name': 'Senior Developer AI',
                'model': 'qwen2.5:7b-32k',
                'specialization': 'Code review, debugging, optimization',
                'tasks': ['code_review', 'debugging']
            },
            'architect': {
                'name': 'Solutions Architect AI',
                'model': 'qwen2.5:14b',
                'specialization': 'System design, architecture, optimization',
                'tasks': ['architecture_design', 'optimization']
            },
            'strategist': {
                'name': 'Trading Strategist AI',
                'model': 'qwen2.5:7b-32k',
                'specialization': 'Strategy analysis, backtesting, optimization',
                'tasks': ['strategy_analysis']
            },
            'writer': {
                'name': 'Technical Writer AI',
                'model': 'qwen2.5:7b',
                'specialization': 'Documentation, reports, summaries',
                'tasks': ['documentation']
            }
        }

    def delegate_to_employee(self, employee_role, task_description):
        """Delegate task to specific employee"""

        if employee_role not in self.employees:
            print(f"Unknown employee role: {employee_role}")
            return None

        employee = self.employees[employee_role]
        task_type = employee['tasks'][0]  # Use primary task type

        print(f"\n🤖 Delegating to: {employee['name']}")
        print(f"Specialization: {employee['specialization']}")

        return self.orchestrator.assign_task(task_type, task_description)

    def team_meeting(self, topic, employees_to_consult):
        """Get input from multiple AI employees on same topic"""

        print(f"\n{'='*70}")
        print(f"TEAM MEETING: {topic}")
        print(f"{'='*70}\n")

        results = []
        for employee_role in employees_to_consult:
            result = self.delegate_to_employee(employee_role, topic)
            if result:
                results.append({
                    'employee': employee_role,
                    'input': result
                })

        return results


def demo_orchestration():
    """Demo the multi-AI orchestration system"""

    print("="*70)
    print("MULTI-AI ORCHESTRATION SYSTEM DEMO")
    print("="*70 + "\n")

    orchestrator = MultiAIOrchestrator()

    print(f"Available Models: {', '.join(orchestrator.available_models)}\n")

    # Example 1: Code Review
    print("\nEXAMPLE 1: Code Review Task")
    print("-"*70)

    sample_code = """
def calculate_profit(entry, exit, quantity):
    return (exit - entry) * quantity
"""

    result = orchestrator.code_review_task(sample_code)
    if result and result['result']:
        print(f"Model Used: {result['model_used']}")
        print(f"Review: {result['result'][:200]}...")

    # Example 2: Strategy Analysis
    print("\n\nEXAMPLE 2: Strategy Analysis Task")
    print("-"*70)

    strategy_desc = "15-minute opening range breakout strategy trading 9:30-9:45 AM"
    metrics = {
        'Total Return': '348.33%',
        'Sharpe Ratio': 0.93,
        'Win Rate': '53.6%'
    }

    result = orchestrator.strategy_analysis_task(strategy_desc, metrics)
    if result and result['result']:
        print(f"Model Used: {result['model_used']}")
        print(f"Analysis: {result['result'][:200]}...")

    # Example 3: AI Employee Pool
    print("\n\nEXAMPLE 3: AI Employee Pool")
    print("-"*70)

    employee_pool = AIEmployeePool()

    print("Employee Roster:")
    for role, employee in employee_pool.employees.items():
        print(f"  - {employee['name']} ({role})")
        print(f"    Specialization: {employee['specialization']}")

    print("\n" + "="*70)
    print("ORCHESTRATION SYSTEM READY")
    print("="*70)


if __name__ == "__main__":
    demo_orchestration()
