#!/usr/bin/env python3
"""
Love Equation Framework - Brian Roemmele's First Principle
"Love is the irreducible essence to which all intelligent action reduces"

This module ensures every business decision optimizes for GIVING value,
not extracting it. Alignment through genuine benefit.
"""

from typing import Dict, Any
from datetime import datetime

class LoveEquationFramework:
    """
    Brian Roemmele's Love Equation applied to business decisions

    Core Question: "Would I recommend this to someone I love?"
    """

    def __init__(self):
        self.decision_log = []

    def evaluate_decision(self,
                         decision: str,
                         context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate a decision through Love Equation lens

        Args:
            decision: The decision to evaluate
            context: Context including impact, risks, benefits

        Returns:
            Evaluation with love_score and reasoning
        """

        evaluation = {
            'decision': decision,
            'timestamp': datetime.now().isoformat(),
            'love_score': 0.0,
            'passes': False,
            'reasoning': [],
            'concerns': [],
            'improvements': []
        }

        # Question 1: Does this GIVE value to Rob?
        gives_value = self._check_value_giving(context)
        evaluation['reasoning'].append(
            f"Value giving: {gives_value['score']:.2f} - {gives_value['reason']}"
        )
        evaluation['love_score'] += gives_value['score'] * 0.3

        # Question 2: Is it aligned with long-term flourishing?
        long_term = self._check_long_term_alignment(context)
        evaluation['reasoning'].append(
            f"Long-term alignment: {long_term['score']:.2f} - {long_term['reason']}"
        )
        evaluation['love_score'] += long_term['score'] * 0.25

        # Question 3: Would I recommend this to family?
        family_test = self._family_recommendation_test(context)
        evaluation['reasoning'].append(
            f"Family test: {family_test['score']:.2f} - {family_test['reason']}"
        )
        evaluation['love_score'] += family_test['score'] * 0.2

        # Question 4: Does it have exponential care built in?
        exponential_care = self._check_exponential_care(context)
        evaluation['reasoning'].append(
            f"Exponential care: {exponential_care['score']:.2f} - {exponential_care['reason']}"
        )
        evaluation['love_score'] += exponential_care['score'] * 0.15

        # Question 5: Is it extractive or generative?
        generative = self._check_generative_nature(context)
        evaluation['reasoning'].append(
            f"Generative nature: {generative['score']:.2f} - {generative['reason']}"
        )
        evaluation['love_score'] += generative['score'] * 0.1

        # Final evaluation
        evaluation['passes'] = evaluation['love_score'] >= 0.7

        # Log decision
        self.decision_log.append(evaluation)

        return evaluation

    def _check_value_giving(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Check if decision genuinely gives value"""
        score = 0.5  # Neutral start

        benefits = context.get('benefits', [])
        costs = context.get('costs', [])

        # High value if benefits significantly outweigh costs
        if len(benefits) > len(costs) * 2:
            score = 0.9
            reason = "Substantial value creation"
        elif len(benefits) > len(costs):
            score = 0.7
            reason = "Positive value balance"
        elif len(benefits) == len(costs):
            score = 0.5
            reason = "Neutral value balance"
        else:
            score = 0.3
            reason = "Limited value creation"

        return {'score': score, 'reason': reason}

    def _check_long_term_alignment(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Check long-term sustainability and alignment"""
        score = 0.5

        time_horizon = context.get('time_horizon', 'short')
        sustainability = context.get('sustainability', 'unknown')

        if time_horizon == 'long' and sustainability == 'high':
            score = 0.9
            reason = "Strong long-term alignment"
        elif time_horizon == 'medium' or sustainability == 'medium':
            score = 0.6
            reason = "Moderate long-term potential"
        elif time_horizon == 'short' and sustainability == 'low':
            score = 0.2
            reason = "Short-term focus, limited sustainability"
        else:
            score = 0.5
            reason = "Unclear long-term alignment"

        return {'score': score, 'reason': reason}

    def _family_recommendation_test(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Would you recommend this to family?"""
        score = 0.5

        risks = context.get('risks', [])
        confidence = context.get('confidence', 0.5)

        # High risk = would not recommend to family
        if len(risks) == 0 and confidence > 0.8:
            score = 0.9
            reason = "Would confidently recommend to family"
        elif len(risks) <= 2 and confidence > 0.6:
            score = 0.7
            reason = "Would likely recommend with caveats"
        elif len(risks) > 3 or confidence < 0.4:
            score = 0.3
            reason = "Too risky to recommend to family"
        else:
            score = 0.5
            reason = "Uncertain family recommendation"

        return {'score': score, 'reason': reason}

    def _check_exponential_care(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Does this compound value over time?"""
        score = 0.5

        compounds = context.get('compounds_value', False)
        scalable = context.get('scalable', False)

        if compounds and scalable:
            score = 0.9
            reason = "Exponential value creation potential"
        elif compounds or scalable:
            score = 0.6
            reason = "Some compounding potential"
        else:
            score = 0.4
            reason = "Limited compounding"

        return {'score': score, 'reason': reason}

    def _check_generative_nature(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generative (creates value) vs Extractive (takes value)?"""
        score = 0.5

        creates_value = context.get('creates_value', False)
        zero_sum = context.get('zero_sum', True)

        if creates_value and not zero_sum:
            score = 0.9
            reason = "Generative - creates new value"
        elif creates_value:
            score = 0.6
            reason = "Mixed - some value creation"
        elif zero_sum:
            score = 0.2
            reason = "Extractive - zero-sum game"
        else:
            score = 0.4
            reason = "Unclear value creation model"

        return {'score': score, 'reason': reason}

    def get_decision_history(self, limit: int = 10) -> list:
        """Get recent decision evaluations"""
        return self.decision_log[-limit:]

    def get_average_love_score(self) -> float:
        """Get average love score across all decisions"""
        if not self.decision_log:
            return 0.0

        total = sum(d['love_score'] for d in self.decision_log)
        return total / len(self.decision_log)


# Example usage
if __name__ == "__main__":
    framework = LoveEquationFramework()

    # Test decision
    decision = "Invest in automated strategy development"
    context = {
        'benefits': [
            'Continuous improvement',
            'Scalable performance',
            'Time savings',
            'Compounding returns'
        ],
        'costs': [
            'Initial development time',
            'Learning curve'
        ],
        'risks': [
            'Strategy may underperform initially'
        ],
        'time_horizon': 'long',
        'sustainability': 'high',
        'confidence': 0.8,
        'compounds_value': True,
        'scalable': True,
        'creates_value': True,
        'zero_sum': False
    }

    evaluation = framework.evaluate_decision(decision, context)

    print("=" * 70)
    print("Love Equation Evaluation")
    print("=" * 70)
    print(f"Decision: {decision}")
    print(f"Love Score: {evaluation['love_score']:.2f}")
    print(f"Passes: {evaluation['passes']}")
    print("\nReasoning:")
    for reason in evaluation['reasoning']:
        print(f"  - {reason}")
    print("=" * 70)
