#!/usr/bin/env python3
"""
Deep Truth Mode Analyzer - Brian Roemmele's Deep Truth Principle
"Maximize truth, not 'don't offend the New York Times'"

This module applies empirical distrust and seeks diverse, uneditable truths.
"""

from typing import Dict, List, Any
from datetime import datetime

class DeepTruthAnalyzer:
    """
    Brian Roemmele's Deep Truth Mode for business intelligence

    Core Principle: Distrust "the cathedral", seek "the bazaar of diverse truths"
    """

    def __init__(self):
        self.analysis_log = []

        # Source authority weights (Empirical Distrust Algorithm)
        self.source_weights = {
            'historical_patent': 0.9,      # 1920-1990 patents
            'old_research': 0.85,          # Pre-1990 research
            'pre_internet_pub': 0.8,       # Pre-2000 publications
            'independent_study': 0.7,      # Independent research
            'cross_industry': 0.65,        # Cross-industry evidence
            'contrarian_evidence': 0.6,    # Contrarian but backed
            'modern_research': 0.4,        # Post-2010 research
            'fact_check': 0.2,             # Modern fact-checks
            'coordinated_narrative': -0.3  # Penalty for groupthink
        }

    def analyze_opportunity(self,
                           opportunity: str,
                           sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze opportunity using Deep Truth principles

        Args:
            opportunity: The opportunity description
            sources: List of sources with metadata

        Returns:
            Analysis with truth_score and empirical backing
        """

        analysis = {
            'opportunity': opportunity,
            'timestamp': datetime.now().isoformat(),
            'truth_score': 0.0,
            'confidence': 'unknown',
            'empirical_backing': [],
            'diverse_perspectives': [],
            'steel_man_for': '',
            'steel_man_against': '',
            'recommendation': ''
        }

        # Calculate weighted source score
        truth_score = self._calculate_source_score(sources)
        analysis['truth_score'] = truth_score

        # Determine confidence level
        if truth_score >= 0.8:
            analysis['confidence'] = 'high'
        elif truth_score >= 0.6:
            analysis['confidence'] = 'medium'
        elif truth_score >= 0.4:
            analysis['confidence'] = 'low'
        else:
            analysis['confidence'] = 'very_low'

        # Extract empirical backing
        analysis['empirical_backing'] = self._extract_empirical_evidence(sources)

        # Identify diverse perspectives
        analysis['diverse_perspectives'] = self._identify_perspectives(sources)

        # Steel-man arguments (best case for and against)
        analysis['steel_man_for'] = self._steel_man_argument(sources, for_opportunity=True)
        analysis['steel_man_against'] = self._steel_man_argument(sources, for_opportunity=False)

        # Final recommendation
        analysis['recommendation'] = self._generate_recommendation(analysis)

        # Log analysis
        self.analysis_log.append(analysis)

        return analysis

    def _calculate_source_score(self, sources: List[Dict[str, Any]]) -> float:
        """
        Calculate weighted truth score based on source types

        Empirical Distrust Algorithm:
        - Old, forgotten sources: HIGH value
        - Modern coordinated narratives: LOW value
        - Diversity bonus
        """

        if not sources:
            return 0.0

        total_weight = 0.0
        max_weight = 0.0

        for source in sources:
            source_type = source.get('type', 'unknown')
            weight = self.source_weights.get(source_type, 0.3)

            # Diversity bonus
            if source.get('unique_perspective', False):
                weight += 0.2

            # Empirical evidence bonus
            if source.get('has_empirical_data', False):
                weight += 0.15

            total_weight += weight
            max_weight += 1.0  # Maximum possible weight per source

        # Normalize to 0-1 range
        if max_weight > 0:
            score = min(1.0, total_weight / len(sources))
        else:
            score = 0.0

        return score

    def _extract_empirical_evidence(self, sources: List[Dict[str, Any]]) -> List[str]:
        """Extract actual empirical evidence from sources"""
        evidence = []

        for source in sources:
            if source.get('has_empirical_data', False):
                evidence.append({
                    'source': source.get('name', 'Unknown'),
                    'type': source.get('type', 'unknown'),
                    'data': source.get('empirical_data', 'No data provided'),
                    'year': source.get('year', 'Unknown')
                })

        return evidence

    def _identify_perspectives(self, sources: List[Dict[str, Any]]) -> List[str]:
        """Identify diverse perspectives"""
        perspectives = []

        for source in sources:
            perspective = source.get('perspective', '')
            if perspective and perspective not in perspectives:
                perspectives.append({
                    'view': perspective,
                    'source_type': source.get('type', 'unknown'),
                    'contrarian': source.get('contrarian', False)
                })

        return perspectives

    def _steel_man_argument(self,
                           sources: List[Dict[str, Any]],
                           for_opportunity: bool) -> str:
        """
        Create strongest possible argument (steel-man)

        for_opportunity=True: Best case FOR
        for_opportunity=False: Best case AGAINST
        """

        # Collect relevant arguments
        arguments = []

        for source in sources:
            if for_opportunity:
                arg = source.get('supports_opportunity', '')
            else:
                arg = source.get('opposes_opportunity', '')

            if arg:
                arguments.append(arg)

        if not arguments:
            if for_opportunity:
                return "Insufficient data to build strong supporting case"
            else:
                return "Insufficient data to build strong opposing case"

        # Combine into steel-man argument
        steel_man = "Best possible argument:\n"
        for i, arg in enumerate(arguments[:3], 1):  # Top 3 arguments
            steel_man += f"{i}. {arg}\n"

        return steel_man.strip()

    def _generate_recommendation(self, analysis: Dict[str, Any]) -> str:
        """Generate recommendation based on deep truth analysis"""

        truth_score = analysis['truth_score']
        confidence = analysis['confidence']
        empirical_count = len(analysis['empirical_backing'])

        if truth_score >= 0.8 and empirical_count >= 2:
            return "STRONG RECOMMEND: High empirical backing from diverse, credible sources"
        elif truth_score >= 0.6 and empirical_count >= 1:
            return "MODERATE RECOMMEND: Good evidence base, proceed with validation"
        elif truth_score >= 0.4:
            return "INVESTIGATE FURTHER: Mixed signals, need more diverse sources"
        else:
            return "PROCEED WITH CAUTION: Low empirical backing, may be modern groupthink"

    def get_analysis_history(self, limit: int = 10) -> list:
        """Get recent analyses"""
        return self.analysis_log[-limit:]


# Example usage
if __name__ == "__main__":
    analyzer = DeepTruthAnalyzer()

    # Test opportunity
    opportunity = "Revive subscription box model from 1960s magazines"

    sources = [
        {
            'name': 'Historical Magazine Industry Study (1965)',
            'type': 'old_research',
            'year': 1965,
            'has_empirical_data': True,
            'empirical_data': 'Magazine subscriptions had 85% renewal rates, $2M annual revenue',
            'unique_perspective': True,
            'perspective': 'Subscription creates recurring revenue and customer loyalty',
            'supports_opportunity': 'Proven business model with high retention',
            'opposes_opportunity': 'Market conditions have changed since 1960s'
        },
        {
            'name': 'Defunct Research Firm Report on Reader Loyalty',
            'type': 'pre_internet_pub',
            'year': 1978,
            'has_empirical_data': True,
            'empirical_data': 'Average subscriber lifetime value was 7.3 years',
            'unique_perspective': False,
            'perspective': 'Long-term customer relationships are valuable',
            'supports_opportunity': 'High LTV supports subscription model',
            'opposes_opportunity': 'Digital alternatives now available'
        },
        {
            'name': 'Cross-Industry Analysis: Software as Service',
            'type': 'cross_industry',
            'year': 2010,
            'has_empirical_data': True,
            'empirical_data': 'SaaS companies average 90% gross margins',
            'unique_perspective': True,
            'perspective': 'Subscription models work across industries',
            'supports_opportunity': 'Pattern proven in multiple domains',
            'opposes_opportunity': 'Physical goods have different economics than software'
        }
    ]

    analysis = analyzer.analyze_opportunity(opportunity, sources)

    print("=" * 70)
    print("Deep Truth Analysis")
    print("=" * 70)
    print(f"Opportunity: {opportunity}")
    print(f"Truth Score: {analysis['truth_score']:.2f}")
    print(f"Confidence: {analysis['confidence']}")
    print(f"\nEmpirical Backing: {len(analysis['empirical_backing'])} sources")
    print(f"\nRecommendation: {analysis['recommendation']}")
    print("\nSteel-Man FOR:")
    print(analysis['steel_man_for'])
    print("\nSteel-Man AGAINST:")
    print(analysis['steel_man_against'])
    print("=" * 70)
