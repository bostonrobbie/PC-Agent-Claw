#!/usr/bin/env python3
"""
AI-Powered SOP Generator
Uses LLM to automatically generate SOPs from descriptions
"""
import sys
from pathlib import Path
import anthropic
import os
from typing import Dict, List, Optional
import json

sys.path.append(str(Path(__file__).parent.parent))

from business.sop_manager import SOPManager


class SOPGenerator:
    """
    Generate SOPs using AI

    Features:
    - Generate SOP from natural language description
    - Extract steps automatically
    - Identify automation opportunities
    - Suggest improvements to existing SOPs
    - Generate checklists and validation criteria
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')

        if not self.api_key:
            print("[WARNING] No Anthropic API key found. AI features will be limited.")
            self.client = None
        else:
            self.client = anthropic.Anthropic(api_key=self.api_key)

        self.sop_manager = SOPManager()

    def generate_sop_from_description(self, description: str,
                                     function_name: str = "General",
                                     model: str = "claude-sonnet-4-5-20250929") -> Dict:
        """
        Generate complete SOP from natural language description

        Args:
            description: What the process does
            function_name: Business function
            model: Claude model to use

        Returns:
            Generated SOP structure
        """
        if not self.client:
            return self._generate_mock_sop(description)

        prompt = f"""Generate a detailed Standard Operating Procedure (SOP) for the following process:

{description}

Please provide a JSON response with the following structure:
{{
  "sop_code": "SOP-XXX-001",
  "title": "Brief title",
  "description": "Detailed description",
  "purpose": "Why this SOP exists",
  "scope": "What this SOP covers",
  "steps": [
    {{
      "step_number": 1,
      "title": "Step title",
      "description": "Detailed step description",
      "type": "manual" or "automated",
      "estimated_duration": minutes,
      "checklist": ["item1", "item2"],
      "automation_potential": "high/medium/low"
    }}
  ],
  "frequency": "daily/weekly/monthly/as-needed",
  "estimated_duration": total_minutes
}}

Make it practical, detailed, and actionable."""

        try:
            message = self.client.messages.create(
                model=model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = message.content[0].text

            # Extract JSON from response
            start = response_text.find('{')
            end = response_text.rfind('}') + 1

            if start != -1 and end != 0:
                sop_data = json.loads(response_text[start:end])
                return sop_data
            else:
                print("[ERROR] Could not parse JSON from AI response")
                return self._generate_mock_sop(description)

        except Exception as e:
            print(f"[ERROR] AI generation failed: {e}")
            return self._generate_mock_sop(description)

    def create_sop_in_database(self, sop_data: Dict, function_id: int) -> int:
        """
        Create SOP in database from generated data

        Args:
            sop_data: Generated SOP structure
            function_id: Business function ID

        Returns:
            Created SOP ID
        """
        # Create SOP
        sop_id = self.sop_manager.create_sop(
            sop_data['sop_code'],
            sop_data['title'],
            function_id,
            description=sop_data.get('description'),
            purpose=sop_data.get('purpose'),
            scope=sop_data.get('scope'),
            frequency=sop_data.get('frequency'),
            estimated_duration=sop_data.get('estimated_duration')
        )

        # Add steps
        for step in sop_data.get('steps', []):
            step_id = self.sop_manager.add_step(
                sop_id,
                step['step_number'],
                step['title'],
                step['description'],
                step_type=step.get('type', 'manual'),
                estimated_duration=step.get('estimated_duration')
            )

            # Add checklist items
            for item in step.get('checklist', []):
                self.sop_manager.add_checklist_item(step_id, item)

        return sop_id

    def suggest_improvements(self, sop_id: int,
                           model: str = "claude-sonnet-4-5-20250929") -> List[Dict]:
        """
        Analyze existing SOP and suggest improvements

        Args:
            sop_id: SOP to analyze
            model: Claude model to use

        Returns:
            List of improvement suggestions
        """
        if not self.client:
            return self._mock_improvements()

        # Get SOP data
        sop = self.sop_manager.get_sop(sop_id)
        steps = self.sop_manager.get_steps(sop_id)

        prompt = f"""Analyze this Standard Operating Procedure and suggest improvements:

SOP: {sop['sop_title']}
Description: {sop.get('description', 'N/A')}

Steps:
"""
        for step in steps:
            prompt += f"\n{step['step_number']}. {step['step_title']} ({step['step_type']})"
            prompt += f"\n   {step['description']}"

        prompt += """

Please provide improvement suggestions in JSON format:
[
  {
    "type": "automation/efficiency/clarity/safety",
    "priority": "high/medium/low",
    "step_number": affected_step_or_null,
    "suggestion": "Specific improvement",
    "rationale": "Why this helps",
    "impact": "Expected benefit"
  }
]"""

        try:
            message = self.client.messages.create(
                model=model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = message.content[0].text
            start = response_text.find('[')
            end = response_text.rfind(']') + 1

            if start != -1 and end != 0:
                return json.loads(response_text[start:end])
            else:
                return self._mock_improvements()

        except Exception as e:
            print(f"[ERROR] AI analysis failed: {e}")
            return self._mock_improvements()

    def identify_automation_opportunities(self, sop_id: int) -> List[Dict]:
        """
        Identify which steps can be automated

        Args:
            sop_id: SOP to analyze

        Returns:
            Automation opportunities
        """
        steps = self.sop_manager.get_steps(sop_id)

        opportunities = []
        for step in steps:
            if step['step_type'] == 'manual':
                # Analyze if automatable
                automation_score = self._calculate_automation_score(step)

                if automation_score > 0.5:
                    opportunities.append({
                        'step_number': step['step_number'],
                        'step_title': step['step_title'],
                        'automation_score': automation_score,
                        'suggested_approach': self._suggest_automation_approach(step),
                        'estimated_effort': self._estimate_automation_effort(automation_score)
                    })

        return sorted(opportunities, key=lambda x: x['automation_score'], reverse=True)

    def _calculate_automation_score(self, step: Dict) -> float:
        """Calculate how suitable a step is for automation (0-1)"""
        score = 0.0

        description = (step['description'] or '').lower()

        # Keywords indicating automation potential
        automation_keywords = [
            'calculate', 'compute', 'send', 'email', 'check', 'verify',
            'validate', 'process', 'generate', 'create', 'update', 'fetch',
            'retrieve', 'store', 'save', 'record', 'notify', 'alert'
        ]

        manual_keywords = [
            'review', 'approve', 'decide', 'judge', 'meet', 'discuss',
            'negotiate', 'call', 'interview', 'inspect', 'examine'
        ]

        for keyword in automation_keywords:
            if keyword in description:
                score += 0.15

        for keyword in manual_keywords:
            if keyword in description:
                score -= 0.2

        return max(0.0, min(1.0, score))

    def _suggest_automation_approach(self, step: Dict) -> str:
        """Suggest how to automate this step"""
        description = (step['description'] or '').lower()

        if 'email' in description or 'notify' in description:
            return "Email/notification automation"
        elif 'calculate' in description or 'compute' in description:
            return "Calculation script"
        elif 'validate' in description or 'check' in description:
            return "Validation rules"
        elif 'generate' in description or 'create' in description:
            return "Template-based generation"
        else:
            return "Custom automation handler"

    def _estimate_automation_effort(self, automation_score: float) -> str:
        """Estimate effort to automate"""
        if automation_score > 0.8:
            return "Low (1-2 days)"
        elif automation_score > 0.6:
            return "Medium (3-5 days)"
        else:
            return "High (1-2 weeks)"

    def _generate_mock_sop(self, description: str) -> Dict:
        """Generate mock SOP when AI is unavailable"""
        return {
            "sop_code": "SOP-GEN-001",
            "title": "Generated Process",
            "description": description,
            "purpose": "Auto-generated SOP",
            "scope": "General process",
            "steps": [
                {
                    "step_number": 1,
                    "title": "Initialize Process",
                    "description": "Set up and prepare",
                    "type": "manual",
                    "estimated_duration": 5,
                    "checklist": ["Verify requirements", "Gather materials"],
                    "automation_potential": "medium"
                },
                {
                    "step_number": 2,
                    "title": "Execute Main Task",
                    "description": "Perform the core operation",
                    "type": "manual",
                    "estimated_duration": 15,
                    "checklist": ["Follow procedure", "Document results"],
                    "automation_potential": "high"
                },
                {
                    "step_number": 3,
                    "title": "Verify and Complete",
                    "description": "Check results and finalize",
                    "type": "manual",
                    "estimated_duration": 5,
                    "checklist": ["Verify output", "Update records"],
                    "automation_potential": "low"
                }
            ],
            "frequency": "as-needed",
            "estimated_duration": 25
        }

    def _mock_improvements(self) -> List[Dict]:
        """Mock improvements when AI unavailable"""
        return [
            {
                "type": "automation",
                "priority": "high",
                "step_number": 2,
                "suggestion": "Automate data validation",
                "rationale": "Reduces manual errors",
                "impact": "30% time savings"
            }
        ]

    def close(self):
        """Close database connection"""
        self.sop_manager.close()


# === TEST CODE ===

def main():
    """Test AI SOP generator"""
    print("=" * 70)
    print("AI-Powered SOP Generator")
    print("=" * 70)

    generator = SOPGenerator()

    try:
        print("\n1. Generating SOP from description...")
        description = """
        Process for onboarding a new employee:
        - Create user accounts (email, systems)
        - Order equipment (laptop, phone)
        - Schedule orientation
        - Assign mentor
        - Set up workstation
        """

        sop_data = generator.generate_sop_from_description(
            description,
            function_name="Human Resources"
        )

        print(f"   Generated SOP: {sop_data['sop_code']} - {sop_data['title']}")
        print(f"   Steps: {len(sop_data['steps'])}")
        print(f"   Duration: {sop_data['estimated_duration']} minutes")

        print("\n2. Identifying automation opportunities...")
        opportunities = generator.identify_automation_opportunities(1)  # Example SOP
        print(f"   Found {len(opportunities)} automation opportunities")

        if opportunities:
            top = opportunities[0]
            print(f"   Top: {top['step_title']} (score: {top['automation_score']:.2f})")

        print(f"\n[OK] AI SOP Generator working!")
        print(f"Note: Set ANTHROPIC_API_KEY env var for full AI features")

    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        generator.close()


if __name__ == "__main__":
    main()
