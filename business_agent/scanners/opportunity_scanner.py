#!/usr/bin/env python3
"""
Opportunity Scanner - Strategic Sources
Mines forgotten knowledge, historical patents, and contrarian ideas
"""

import sys
from pathlib import Path
from datetime import datetime

# Add workspace to path
WORKSPACE = Path(r"C:\Users\User\.openclaw\workspace")
sys.path.append(str(WORKSPACE))
sys.path.append(str(WORKSPACE / "business_agent"))

from smart_gpu_llm import SmartGPU
from core.love_equation_framework import LoveEquationFramework
from core.deep_truth_analyzer import DeepTruthAnalyzer

class OpportunityScanner:
    """
    Scans for business opportunities using strategic sources:
    - Historical patents (1920-1990)
    - Forgotten research
    - Pre-internet publications
    - Contrarian but evidence-backed ideas
    - Failed businesses with good ideas
    """

    def __init__(self):
        self.gpu = SmartGPU()
        self.love_framework = LoveEquationFramework()
        self.truth_analyzer = DeepTruthAnalyzer()
        self.opportunities_found = []

    def scan_opportunities(self, focus_area: str = "general") -> list:
        """
        Scan for opportunities using strategic sources

        Args:
            focus_area: Area to focus on (trading, business, technology, etc.)

        Returns:
            List of opportunities with analysis
        """

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting opportunity scan...")
        print(f"Focus area: {focus_area}")

        opportunities = []

        # Source 1: Historical Patents & Forgotten Research
        hist_opps = self._scan_historical_knowledge(focus_area)
        opportunities.extend(hist_opps)

        # Source 2: Failed Businesses With Good Ideas
        failed_opps = self._scan_failed_businesses(focus_area)
        opportunities.extend(failed_opps)

        # Source 3: Cross-Industry Patterns
        cross_opps = self._scan_cross_industry_patterns(focus_area)
        opportunities.extend(cross_opps)

        # Source 4: Contrarian But Evidence-Backed
        contrarian_opps = self._scan_contrarian_ideas(focus_area)
        opportunities.extend(contrarian_opps)

        # Analyze each with Deep Truth + Love Equation
        analyzed_opportunities = []
        for opp in opportunities:
            analysis = self._analyze_opportunity(opp)
            analyzed_opportunities.append(analysis)

        # Sort by combined score
        analyzed_opportunities.sort(
            key=lambda x: x['combined_score'],
            reverse=True
        )

        self.opportunities_found.extend(analyzed_opportunities)

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Scan complete: {len(analyzed_opportunities)} opportunities found")

        return analyzed_opportunities

    def _scan_historical_knowledge(self, focus_area: str) -> list:
        """Scan historical patents and forgotten research"""

        prompt = f"""
        You are mining HISTORICAL KNOWLEDGE for business opportunities.

        Focus: {focus_area}

        Search these strategic sources:
        1. Historical patents (1920-1990 era) - expired, proven technology
        2. Defunct research firms - good research, company failed for human reasons (finances)
        3. Pre-internet business publications - high editorial standards, empirical data

        Find opportunities where:
        - Technology/idea was proven
        - Timing was wrong (too early) or execution failed
        - Costs have dropped (making it viable now)
        - Market conditions have changed favorably

        Return 2-3 specific opportunities with:
        - Brief description
        - Source (year, publication/patent)
        - Why it failed originally
        - Why it's viable now
        - Empirical evidence

        Format each as:
        OPPORTUNITY: [name]
        SOURCE: [historical source]
        WHY_FAILED: [reason]
        WHY_NOW: [reason viable]
        EVIDENCE: [data]
        """

        response = self.gpu.run_prompt("qwen2.5:7b", prompt)

        # Parse response into opportunities
        opportunities = self._parse_llm_response(response, source_type='historical_knowledge')

        return opportunities

    def _scan_failed_businesses(self, focus_area: str) -> list:
        """Scan failed businesses with good ideas"""

        prompt = f"""
        Analyze FAILED BUSINESSES with good core ideas in: {focus_area}

        Find cases where:
        - Core idea was sound
        - Business failed due to execution, timing, or finances (not bad idea)
        - Market conditions have improved
        - Technology has made it more feasible

        Return 1-2 specific examples with:
        - Company name and what they did
        - Why they failed
        - Why the core idea was good
        - What's changed that makes it viable now
        - Evidence of demand

        Format each as:
        OPPORTUNITY: [revive X idea]
        FAILED_COMPANY: [name and description]
        FAILURE_REASON: [why they failed]
        IDEA_MERIT: [why idea was good]
        CHANGED_CONDITIONS: [what's different now]
        DEMAND_EVIDENCE: [proof of demand]
        """

        response = self.gpu.run_prompt("qwen2.5:7b", prompt)

        opportunities = self._parse_llm_response(response, source_type='failed_business')

        return opportunities

    def _scan_cross_industry_patterns(self, focus_area: str) -> list:
        """Scan for successful patterns in other industries"""

        prompt = f"""
        Find CROSS-INDUSTRY PATTERNS for: {focus_area}

        Look for successful business models/strategies in OTHER industries
        that could be adapted to {focus_area}.

        Examples:
        - Subscription model: Magazines → Software → Razors → Everything
        - Marketplace model: Real estate → Jobs → Services → Niche markets
        - Freemium: Software → Media → Gaming

        Return 1-2 proven patterns with:
        - Original industry where it works
        - Evidence of success (data)
        - How to adapt to {focus_area}
        - Why it hasn't been done yet (knowledge gap)

        Format each as:
        OPPORTUNITY: [apply X to {focus_area}]
        ORIGINAL_INDUSTRY: [where it works]
        SUCCESS_DATA: [empirical evidence]
        ADAPTATION: [how to apply]
        KNOWLEDGE_GAP: [why not done yet]
        """

        response = self.gpu.run_prompt("qwen2.5:7b", prompt)

        opportunities = self._parse_llm_response(response, source_type='cross_industry')

        return opportunities

    def _scan_contrarian_ideas(self, focus_area: str) -> list:
        """Scan for contrarian but evidence-backed ideas"""

        prompt = f"""
        Find CONTRARIAN but EVIDENCE-BACKED opportunities in: {focus_area}

        Look for:
        - Currently unfashionable or "not allowed" ideas
        - BUT with empirical evidence of effectiveness
        - Against current trends but proven by data
        - Unpopular but profitable

        Example: Value investing was "dead" before it outperformed

        Return 1-2 contrarian ideas with:
        - The contrarian position
        - Why it's unpopular currently
        - Empirical evidence supporting it
        - Potential ROI
        - Risk assessment

        Format each as:
        OPPORTUNITY: [contrarian idea]
        UNFASHIONABLE_REASON: [why unpopular]
        EMPIRICAL_SUPPORT: [data supporting it]
        POTENTIAL_ROI: [estimated return]
        RISKS: [what could go wrong]
        """

        response = self.gpu.run_prompt("qwen2.5:7b", prompt)

        opportunities = self._parse_llm_response(response, source_type='contrarian')

        return opportunities

    def _parse_llm_response(self, response: str, source_type: str) -> list:
        """Parse LLM response into structured opportunities"""

        opportunities = []

        # Simple parsing - split by "OPPORTUNITY:"
        sections = response.split('OPPORTUNITY:')

        for section in sections[1:]:  # Skip first empty section
            opp = {
                'source_type': source_type,
                'raw_text': section.strip(),
                'timestamp': datetime.now().isoformat()
            }

            # Extract opportunity name (first line)
            lines = section.strip().split('\n')
            if lines:
                opp['name'] = lines[0].strip()

            opportunities.append(opp)

        return opportunities

    def _analyze_opportunity(self, opportunity: dict) -> dict:
        """Analyze opportunity with Love Equation + Deep Truth"""

        # Create mock sources for Deep Truth analysis
        # (In production, would extract actual sources from LLM response)
        sources = [{
            'name': opportunity.get('name', 'Unknown'),
            'type': self._map_source_type(opportunity['source_type']),
            'year': 1970,  # Mock - would extract from response
            'has_empirical_data': True,
            'empirical_data': 'See opportunity details',
            'unique_perspective': True,
            'perspective': 'Forgotten knowledge opportunity',
            'supports_opportunity': 'Empirical backing from source',
            'opposes_opportunity': 'Market conditions may have changed'
        }]

        truth_analysis = self.truth_analyzer.analyze_opportunity(
            opportunity['name'],
            sources
        )

        # Create context for Love Equation
        love_context = {
            'benefits': ['Potential revenue', 'Market opportunity', 'Proven concept'],
            'costs': ['Development time', 'Market risk'],
            'risks': ['Execution risk', 'Market timing'],
            'time_horizon': 'medium',
            'sustainability': 'medium',
            'confidence': 0.6,
            'compounds_value': True,
            'scalable': True,
            'creates_value': True,
            'zero_sum': False
        }

        love_evaluation = self.love_framework.evaluate_decision(
            opportunity['name'],
            love_context
        )

        # Combined score
        combined_score = (truth_analysis['truth_score'] * 0.5 +
                         love_evaluation['love_score'] * 0.5)

        return {
            **opportunity,
            'truth_analysis': truth_analysis,
            'love_evaluation': love_evaluation,
            'combined_score': combined_score,
            'recommendation': truth_analysis['recommendation']
        }

    def _map_source_type(self, internal_type: str) -> str:
        """Map internal source type to Deep Truth categories"""
        mapping = {
            'historical_knowledge': 'old_research',
            'failed_business': 'independent_study',
            'cross_industry': 'cross_industry',
            'contrarian': 'contrarian_evidence'
        }
        return mapping.get(internal_type, 'modern_research')


# CLI Interface
if __name__ == "__main__":
    scanner = OpportunityScanner()

    focus = sys.argv[1] if len(sys.argv) > 1 else "trading and business"

    opportunities = scanner.scan_opportunities(focus)

    print("\n" + "=" * 70)
    print("OPPORTUNITY SCAN RESULTS")
    print("=" * 70)

    for i, opp in enumerate(opportunities[:5], 1):  # Top 5
        print(f"\n{i}. {opp['name']}")
        print(f"   Source Type: {opp['source_type']}")
        print(f"   Combined Score: {opp['combined_score']:.2f}")
        print(f"   Recommendation: {opp['recommendation']}")

    print("\n" + "=" * 70)
