#!/usr/bin/env python3
"""
AI-Powered SOP Generator (Anthropic CLI)
Uses anthropic CLI in terminal for best GitHub/PR integration
"""
import sys
from pathlib import Path
import subprocess
import json
from typing import Dict, List, Optional
import tempfile

sys.path.append(str(Path(__file__).parent.parent))

from business.sop_manager import SOPManager


class SOPGeneratorAnthropicCLI:
    """
    Generate SOPs using Anthropic CLI

    Uses: anthropic (pip install anthropic-cli)
    Best for GitHub PR merges and terminal workflows
    """

    def __init__(self):
        self.sop_manager = SOPManager()
        self.use_anthropic_cli = self._check_anthropic_cli_available()

    def _check_anthropic_cli_available(self) -> bool:
        """Check if Anthropic CLI is available"""
        try:
            result = subprocess.run(
                ['anthropic', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            return False

    def generate_sop_from_description(self, description: str,
                                     function_name: str = "General") -> Dict:
        """
        Generate complete SOP from natural language description

        Args:
            description: What the process does
            function_name: Business function

        Returns:
            Generated SOP structure
        """
        if self.use_anthropic_cli:
            return self._generate_with_anthropic_cli(description, function_name)
        else:
            print("[INFO] Anthropic CLI not found, using template-based generation")
            return self._generate_smart_template(description)

    def _generate_with_anthropic_cli(self, description: str, function_name: str) -> Dict:
        """Generate SOP using Anthropic CLI"""
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

Make it practical, detailed, and actionable. Return ONLY the JSON, no other text."""

        try:
            # Use anthropic CLI (better for terminal/GitHub workflows)
            result = subprocess.run(
                ['anthropic', 'complete', '--prompt', prompt, '--max-tokens', '4096'],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                response_text = result.stdout

                # Extract JSON from response
                start = response_text.find('{')
                end = response_text.rfind('}') + 1

                if start != -1 and end != 0:
                    sop_data = json.loads(response_text[start:end])
                    return sop_data
                else:
                    print("[ERROR] Could not parse JSON from Anthropic CLI response")
                    return self._generate_smart_template(description)
            else:
                print(f"[ERROR] Anthropic CLI failed: {result.stderr}")
                return self._generate_smart_template(description)

        except Exception as e:
            print(f"[ERROR] AI generation failed: {e}")
            return self._generate_smart_template(description)

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

    def suggest_improvements(self, sop_id: int) -> List[Dict]:
        """
        Analyze existing SOP and suggest improvements

        Args:
            sop_id: SOP to analyze

        Returns:
            List of improvement suggestions
        """
        if not self.use_anthropic_cli:
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
]

Return ONLY the JSON array, no other text."""

        try:
            result = subprocess.run(
                ['anthropic', 'complete', '--prompt', prompt, '--max-tokens', '2048'],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                response_text = result.stdout
                start = response_text.find('[')
                end = response_text.rfind(']') + 1

                if start != -1 and end != 0:
                    return json.loads(response_text[start:end])
                else:
                    return self._mock_improvements()
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

    def _generate_smart_template(self, description: str) -> Dict:
        """Generate smart template-based SOP"""
        desc_lower = description.lower()

        # Intelligent parsing
        if 'customer' in desc_lower or 'client' in desc_lower:
            return self._customer_template(description)
        elif 'order' in desc_lower or 'purchase' in desc_lower:
            return self._order_template(description)
        elif 'employee' in desc_lower or 'staff' in desc_lower:
            return self._employee_template(description)
        elif 'finance' in desc_lower or 'invoice' in desc_lower:
            return self._finance_template(description)
        else:
            return self._general_template(description)

    def _customer_template(self, description: str) -> Dict:
        """Customer-focused SOP template"""
        return {
            "sop_code": "SOP-CUST-001",
            "title": "Customer Process",
            "description": description,
            "purpose": "Ensure consistent customer experience",
            "scope": "All customer interactions",
            "steps": [
                {
                    "step_number": 1,
                    "title": "Verify Customer Identity",
                    "description": "Confirm customer details and authentication",
                    "type": "manual",
                    "estimated_duration": 3,
                    "checklist": ["Check ID", "Verify email", "Confirm account"],
                    "automation_potential": "medium"
                },
                {
                    "step_number": 2,
                    "title": "Process Customer Request",
                    "description": "Handle customer's specific needs",
                    "type": "manual",
                    "estimated_duration": 10,
                    "checklist": ["Document request", "Check eligibility", "Process action"],
                    "automation_potential": "high"
                },
                {
                    "step_number": 3,
                    "title": "Confirm and Follow Up",
                    "description": "Send confirmation and schedule follow-up",
                    "type": "automated",
                    "estimated_duration": 2,
                    "checklist": ["Generate confirmation", "Send email", "Schedule follow-up"],
                    "automation_potential": "high"
                }
            ],
            "frequency": "as-needed",
            "estimated_duration": 15
        }

    def _order_template(self, description: str) -> Dict:
        """Order processing template"""
        return {
            "sop_code": "SOP-ORDER-001",
            "title": "Order Processing",
            "description": description,
            "purpose": "Efficient and accurate order fulfillment",
            "scope": "All order types",
            "steps": [
                {
                    "step_number": 1,
                    "title": "Receive and Validate Order",
                    "description": "Capture order details and validate",
                    "type": "automated",
                    "estimated_duration": 2,
                    "checklist": ["Validate data", "Check inventory", "Verify pricing"],
                    "automation_potential": "high"
                },
                {
                    "step_number": 2,
                    "title": "Process Payment",
                    "description": "Handle payment transaction",
                    "type": "automated",
                    "estimated_duration": 1,
                    "checklist": ["Verify payment", "Process transaction", "Generate receipt"],
                    "automation_potential": "high"
                },
                {
                    "step_number": 3,
                    "title": "Fulfill Order",
                    "description": "Prepare and ship order",
                    "type": "manual",
                    "estimated_duration": 20,
                    "checklist": ["Pick items", "Pack order", "Generate shipping label"],
                    "automation_potential": "medium"
                },
                {
                    "step_number": 4,
                    "title": "Send Confirmation",
                    "description": "Notify customer of shipment",
                    "type": "automated",
                    "estimated_duration": 1,
                    "checklist": ["Generate tracking", "Send email", "Update status"],
                    "automation_potential": "high"
                }
            ],
            "frequency": "continuous",
            "estimated_duration": 24
        }

    def _employee_template(self, description: str) -> Dict:
        """Employee-related template"""
        return {
            "sop_code": "SOP-HR-001",
            "title": "Employee Process",
            "description": description,
            "purpose": "Streamlined employee management",
            "scope": "HR operations",
            "steps": [
                {
                    "step_number": 1,
                    "title": "Create Employee Record",
                    "description": "Set up employee in all systems",
                    "type": "automated",
                    "estimated_duration": 5,
                    "checklist": ["Create email", "Set up accounts", "Generate ID"],
                    "automation_potential": "high"
                },
                {
                    "step_number": 2,
                    "title": "Assign Resources",
                    "description": "Provide equipment and access",
                    "type": "manual",
                    "estimated_duration": 15,
                    "checklist": ["Order equipment", "Grant access", "Assign workspace"],
                    "automation_potential": "medium"
                },
                {
                    "step_number": 3,
                    "title": "Schedule Orientation",
                    "description": "Set up training and onboarding",
                    "type": "automated",
                    "estimated_duration": 5,
                    "checklist": ["Send calendar invite", "Assign mentor", "Prepare materials"],
                    "automation_potential": "high"
                }
            ],
            "frequency": "as-needed",
            "estimated_duration": 25
        }

    def _finance_template(self, description: str) -> Dict:
        """Finance/accounting template"""
        return {
            "sop_code": "SOP-FIN-001",
            "title": "Financial Process",
            "description": description,
            "purpose": "Accurate financial processing",
            "scope": "Financial operations",
            "steps": [
                {
                    "step_number": 1,
                    "title": "Collect Financial Data",
                    "description": "Gather all required documents",
                    "type": "manual",
                    "estimated_duration": 10,
                    "checklist": ["Verify completeness", "Check accuracy", "Scan documents"],
                    "automation_potential": "medium"
                },
                {
                    "step_number": 2,
                    "title": "Process Transaction",
                    "description": "Enter and validate transaction",
                    "type": "automated",
                    "estimated_duration": 3,
                    "checklist": ["Enter data", "Validate rules", "Generate entries"],
                    "automation_potential": "high"
                },
                {
                    "step_number": 3,
                    "title": "Review and Approve",
                    "description": "Manager review and approval",
                    "type": "manual",
                    "estimated_duration": 5,
                    "checklist": ["Review entries", "Check compliance", "Approve"],
                    "automation_potential": "low"
                },
                {
                    "step_number": 4,
                    "title": "Archive Records",
                    "description": "Store for compliance",
                    "type": "automated",
                    "estimated_duration": 2,
                    "checklist": ["Generate PDF", "Store securely", "Update index"],
                    "automation_potential": "high"
                }
            ],
            "frequency": "daily",
            "estimated_duration": 20
        }

    def _general_template(self, description: str) -> Dict:
        """General purpose template"""
        return {
            "sop_code": "SOP-GEN-001",
            "title": "General Process",
            "description": description,
            "purpose": "Standardized process execution",
            "scope": "General operations",
            "steps": [
                {
                    "step_number": 1,
                    "title": "Prepare",
                    "description": "Set up and verify prerequisites",
                    "type": "manual",
                    "estimated_duration": 5,
                    "checklist": ["Verify requirements", "Gather materials", "Check access"],
                    "automation_potential": "medium"
                },
                {
                    "step_number": 2,
                    "title": "Execute",
                    "description": "Perform the main operation",
                    "type": "manual",
                    "estimated_duration": 15,
                    "checklist": ["Follow procedure", "Document progress", "Handle errors"],
                    "automation_potential": "high"
                },
                {
                    "step_number": 3,
                    "title": "Verify and Complete",
                    "description": "Check results and finalize",
                    "type": "manual",
                    "estimated_duration": 5,
                    "checklist": ["Verify output", "Update records", "Notify stakeholders"],
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
                "rationale": "Reduces manual errors and speeds up process",
                "impact": "30% time savings, improved accuracy"
            }
        ]

    def close(self):
        """Close database connection"""
        self.sop_manager.close()


# === TEST CODE ===

def main():
    """Test AI SOP generator (Anthropic CLI)"""
    print("=" * 70)
    print("AI-Powered SOP Generator (Anthropic CLI)")
    print("=" * 70)

    generator = SOPGeneratorAnthropicCLI()

    print(f"\nAnthropic CLI available: {generator.use_anthropic_cli}")
    if not generator.use_anthropic_cli:
        print("Install with: pip install anthropic-cli")

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

        print(f"\n[OK] AI SOP Generator (Anthropic CLI) working!")
        if generator.use_anthropic_cli:
            print("   Using Anthropic CLI for AI features")
        else:
            print("   Using smart template generation")

    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        generator.close()


if __name__ == "__main__":
    main()
