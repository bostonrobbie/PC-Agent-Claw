#!/usr/bin/env python3
"""
Financial Modeler - Validate Opportunities with Numbers
Runs financial models on business opportunities to verify viability
"""

import json
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

class FinancialModeler:
    """
    Run financial analysis on business opportunities

    Philosophy: "Ideas are cheap, execution and numbers matter"
    - Like backtesting a trading strategy
    - Verify assumptions with conservative estimates
    - Calculate TAM, SAM, SOM
    - Model revenue, costs, profitability
    - Assess capital requirements and ROI
    """

    def __init__(self):
        self.models_run = []

    def run_full_analysis(self, opportunity: Dict) -> Dict:
        """
        Run complete financial analysis on opportunity

        Args:
            opportunity: Dict with opportunity details

        Returns:
            Dict with financial model results
        """

        analysis = {
            'opportunity_name': opportunity.get('name', 'Unknown'),
            'timestamp': datetime.now().isoformat(),
            'market_analysis': self._analyze_market(opportunity),
            'revenue_model': self._model_revenue(opportunity),
            'cost_structure': self._model_costs(opportunity),
            'profitability': self._calculate_profitability(opportunity),
            'capital_requirements': self._estimate_capital(opportunity),
            'roi_analysis': self._calculate_roi(opportunity),
            'sensitivity_analysis': self._run_sensitivity(opportunity),
            'risk_assessment': self._assess_risks(opportunity),
            'verdict': None
        }

        # Overall verdict
        analysis['verdict'] = self._generate_verdict(analysis)

        self.models_run.append(analysis)
        return analysis

    def _analyze_market(self, opportunity: Dict) -> Dict:
        """
        Analyze Total Addressable Market (TAM), SAM, SOM
        """

        # Extract market data from opportunity if available
        raw_text = opportunity.get('raw_text', '')
        name = opportunity.get('name', '')

        market = {
            'tam': None,  # Total Addressable Market
            'sam': None,  # Serviceable Available Market
            'som': None,  # Serviceable Obtainable Market
            'growth_rate': None,
            'market_maturity': 'unknown',
            'competitive_intensity': 'unknown',
            'notes': []
        }

        # Try to extract market size from raw_text
        # This is a simplified version - would need LLM for real extraction
        if 'market size' in raw_text.lower():
            market['notes'].append('Market size data found in opportunity description')

        if 'billion' in raw_text.lower():
            market['notes'].append('Billion-dollar market mentioned')
            market['tam'] = 'Large (>$1B)'
        elif 'million' in raw_text.lower():
            market['notes'].append('Million-dollar market mentioned')
            market['tam'] = 'Medium ($1M-$1B)'

        # Check for growth indicators
        if 'growing' in raw_text.lower() or 'cagr' in raw_text.lower():
            market['notes'].append('Market growth indicated')
            market['growth_rate'] = 'Positive'

        return market

    def _model_revenue(self, opportunity: Dict) -> Dict:
        """
        Model potential revenue streams and projections
        """

        revenue = {
            'revenue_streams': [],
            'pricing_model': 'unknown',
            'year1_projection': None,
            'year3_projection': None,
            'year5_projection': None,
            'assumptions': []
        }

        # Identify revenue model from opportunity type
        name = opportunity.get('name', '').lower()

        if 'subscription' in name or 'platform' in name:
            revenue['pricing_model'] = 'Subscription/SaaS'
            revenue['revenue_streams'] = ['Monthly subscriptions', 'Premium tiers', 'API access']
            revenue['assumptions'].append('Assume $10-50/user/month')
            revenue['assumptions'].append('Assume 5% monthly growth in users')

        elif 'marketplace' in name:
            revenue['pricing_model'] = 'Marketplace (Take Rate)'
            revenue['revenue_streams'] = ['Transaction fees', 'Seller subscriptions', 'Advertising']
            revenue['assumptions'].append('Assume 10-15% take rate')
            revenue['assumptions'].append('GMV growth drives revenue')

        elif 'product' in name or 'technology' in name:
            revenue['pricing_model'] = 'Product Sales'
            revenue['revenue_streams'] = ['Unit sales', 'Licensing', 'Services']
            revenue['assumptions'].append('Assume pricing based on value delivered')
            revenue['assumptions'].append('Gross margins 40-70%')

        else:
            revenue['pricing_model'] = 'To be determined'
            revenue['assumptions'].append('Need more detail on business model')

        return revenue

    def _model_costs(self, opportunity: Dict) -> Dict:
        """
        Model cost structure and operating expenses
        """

        costs = {
            'fixed_costs': [],
            'variable_costs': [],
            'one_time_costs': [],
            'monthly_burn': None,
            'unit_economics': {},
            'assumptions': []
        }

        name = opportunity.get('name', '').lower()

        # Common startup costs
        costs['fixed_costs'] = [
            'Salaries and benefits',
            'Office/infrastructure',
            'Software subscriptions',
            'Legal and accounting',
            'Marketing and sales'
        ]

        if 'platform' in name or 'marketplace' in name or 'subscription' in name:
            costs['variable_costs'] = [
                'Server/hosting (scales with users)',
                'Customer support (scales with users)',
                'Payment processing fees',
                'User acquisition costs'
            ]
            costs['assumptions'].append('Hosting: $0.10-1.00 per user/month')
            costs['assumptions'].append('CAC: $10-100 per user depending on channel')

        elif 'product' in name or 'technology' in name:
            costs['variable_costs'] = [
                'Manufacturing/production',
                'Materials and components',
                'Shipping and fulfillment',
                'Sales commissions'
            ]
            costs['assumptions'].append('COGS: 30-60% of revenue')
            costs['assumptions'].append('Distribution: 10-20% of revenue')

        # One-time costs
        costs['one_time_costs'] = [
            'Product development',
            'Initial marketing',
            'Legal setup',
            'Tooling/equipment'
        ]

        costs['assumptions'].append('Estimate $50-200K for MVP development')
        costs['assumptions'].append('Estimate $20-100K for initial marketing')

        return costs

    def _calculate_profitability(self, opportunity: Dict) -> Dict:
        """
        Calculate profitability metrics and breakeven
        """

        profitability = {
            'gross_margin': 'TBD',
            'contribution_margin': 'TBD',
            'breakeven_point': 'TBD',
            'path_to_profitability': 'TBD',
            'assumptions': []
        }

        name = opportunity.get('name', '').lower()

        if 'software' in name or 'platform' in name or 'subscription' in name:
            profitability['gross_margin'] = '70-85% (typical for SaaS)'
            profitability['assumptions'].append('SaaS businesses typically have high gross margins')
            profitability['assumptions'].append('Profitability depends on CAC payback < 12 months')
            profitability['path_to_profitability'] = '18-36 months typical for SaaS'

        elif 'marketplace' in name:
            profitability['gross_margin'] = '60-80% (marketplace take rate)'
            profitability['assumptions'].append('Marketplace gross margins high, but need liquidity')
            profitability['path_to_profitability'] = '24-48 months (chicken-egg problem)'

        elif 'product' in name or 'hardware' in name:
            profitability['gross_margin'] = '30-50% (typical for physical products)'
            profitability['assumptions'].append('Hardware margins lower, inventory risk higher')
            profitability['path_to_profitability'] = '12-24 months if demand exists'

        else:
            profitability['assumptions'].append('Need business model details for profitability analysis')

        return profitability

    def _estimate_capital(self, opportunity: Dict) -> Dict:
        """
        Estimate capital requirements to launch and scale
        """

        capital = {
            'seed_stage': 'TBD',
            'series_a_equivalent': 'TBD',
            'total_to_profitability': 'TBD',
            'capital_efficiency': 'unknown',
            'assumptions': []
        }

        name = opportunity.get('name', '').lower()

        if 'software' in name or 'platform' in name or 'subscription' in name:
            capital['seed_stage'] = '$100-500K (MVP + initial traction)'
            capital['series_a_equivalent'] = '$1-3M (scale sales and marketing)'
            capital['total_to_profitability'] = '$2-5M'
            capital['capital_efficiency'] = 'High (software scales well)'
            capital['assumptions'].append('SaaS can be capital efficient if product-market fit exists')

        elif 'marketplace' in name:
            capital['seed_stage'] = '$200-750K (build platform + seed liquidity)'
            capital['series_a_equivalent'] = '$2-5M (growth and network effects)'
            capital['total_to_profitability'] = '$5-15M'
            capital['capital_efficiency'] = 'Medium (need to subsidize growth initially)'
            capital['assumptions'].append('Marketplaces need capital to bootstrap both sides')

        elif 'product' in name or 'hardware' in name or 'manufacturing' in name:
            capital['seed_stage'] = '$250K-1M (tooling, inventory, testing)'
            capital['series_a_equivalent'] = '$2-5M (manufacturing scale-up)'
            capital['total_to_profitability'] = '$3-8M'
            capital['capital_efficiency'] = 'Low-Medium (inventory and COGS require capital)'
            capital['assumptions'].append('Physical products require more upfront capital')

        return capital

    def _calculate_roi(self, opportunity: Dict) -> Dict:
        """
        Calculate potential return on investment
        """

        roi = {
            'expected_roi': 'TBD',
            'payback_period': 'TBD',
            'irr': 'TBD',
            'exit_scenarios': [],
            'assumptions': []
        }

        # Generic startup ROI assumptions
        roi['exit_scenarios'] = [
            'Acquisition: 3-7x revenue (typical SaaS)',
            'IPO: 5-10x revenue (if scaled)',
            'Cashflow business: 5-15x EBITDA'
        ]

        roi['assumptions'] = [
            'Assumes product-market fit is achieved',
            'Assumes execution risk is managed',
            'Assumes market conditions remain favorable',
            'Typical startup failure rate: 90% (most return 0x)'
        ]

        roi['expected_roi'] = 'High risk, high reward (0x or 10-100x)'
        roi['payback_period'] = '5-10 years typical for VC-backed startups'

        return roi

    def _run_sensitivity(self, opportunity: Dict) -> Dict:
        """
        Run sensitivity analysis on key assumptions
        """

        sensitivity = {
            'key_variables': [],
            'best_case': {},
            'base_case': {},
            'worst_case': {},
            'assumptions': []
        }

        # Identify key variables to test
        sensitivity['key_variables'] = [
            'Customer acquisition cost (CAC)',
            'Conversion rate',
            'Churn rate',
            'Pricing/ARPU',
            'Market growth rate'
        ]

        sensitivity['assumptions'] = [
            'Best case: All assumptions 20% better than expected',
            'Base case: Assumptions as modeled',
            'Worst case: All assumptions 20% worse than expected',
            'Reality usually falls between base and worst case'
        ]

        return sensitivity

    def _assess_risks(self, opportunity: Dict) -> Dict:
        """
        Assess key risks to financial model
        """

        risks = {
            'market_risk': [],
            'execution_risk': [],
            'financial_risk': [],
            'regulatory_risk': [],
            'competitive_risk': [],
            'mitigation_strategies': []
        }

        # Common startup risks
        risks['market_risk'] = [
            'Market size smaller than expected',
            'Customer willingness to pay lower than assumed',
            'Market growth slower than projected'
        ]

        risks['execution_risk'] = [
            'Product development takes longer than planned',
            'Difficulty hiring key talent',
            'Operational challenges in scaling'
        ]

        risks['financial_risk'] = [
            'Burn rate higher than modeled',
            'Revenue ramp slower than expected',
            'Difficulty raising follow-on funding'
        ]

        risks['competitive_risk'] = [
            'Incumbents respond aggressively',
            'New entrants with more capital',
            'Substitutes or alternatives emerge'
        ]

        # Generic mitigation strategies
        risks['mitigation_strategies'] = [
            'Start with MVP to validate assumptions quickly',
            'Focus on unit economics before scaling',
            'Build capital-efficient business model',
            'Secure committed customers/LOIs before launch',
            'Maintain 12-18 months cash runway minimum'
        ]

        return risks

    def _generate_verdict(self, analysis: Dict) -> Dict:
        """
        Generate overall financial verdict
        """

        verdict = {
            'recommendation': 'NEEDS MORE DATA',
            'confidence': 'Low',
            'key_strengths': [],
            'key_concerns': [],
            'next_steps': []
        }

        # This is simplified - would need actual data to make real recommendations
        verdict['key_concerns'] = [
            'Limited quantitative data in opportunity description',
            'Need market size validation',
            'Need customer interviews for willingness to pay',
            'Need competitive analysis'
        ]

        verdict['next_steps'] = [
            'Conduct market research (TAM/SAM/SOM sizing)',
            'Interview 20-50 potential customers',
            'Build detailed financial model with real data',
            'Validate key assumptions with experiments',
            'Assess competitive landscape',
            'Determine capital requirements for MVP'
        ]

        verdict['recommendation'] = 'INVESTIGATE FURTHER'
        verdict['confidence'] = 'Medium - Need more data for GO/NO-GO decision'

        return verdict

    def save_analysis(self, analysis: Dict, filepath: str):
        """Save financial analysis to file"""
        with open(filepath, 'w') as f:
            json.dump(analysis, f, indent=2)

    def generate_summary(self, analysis: Dict) -> str:
        """Generate text summary of financial analysis"""

        summary = []
        summary.append("=" * 70)
        summary.append(f"FINANCIAL ANALYSIS: {analysis['opportunity_name']}")
        summary.append("=" * 70)
        summary.append("")

        # Market
        market = analysis['market_analysis']
        summary.append("MARKET ANALYSIS:")
        summary.append(f"  TAM: {market.get('tam', 'Unknown')}")
        summary.append(f"  Growth Rate: {market.get('growth_rate', 'Unknown')}")
        summary.append("")

        # Revenue Model
        revenue = analysis['revenue_model']
        summary.append("REVENUE MODEL:")
        summary.append(f"  Pricing: {revenue['pricing_model']}")
        if revenue['revenue_streams']:
            summary.append(f"  Streams: {', '.join(revenue['revenue_streams'])}")
        summary.append("")

        # Profitability
        profit = analysis['profitability']
        summary.append("PROFITABILITY:")
        summary.append(f"  Gross Margin: {profit['gross_margin']}")
        summary.append(f"  Path to Profit: {profit['path_to_profitability']}")
        summary.append("")

        # Capital
        capital = analysis['capital_requirements']
        summary.append("CAPITAL REQUIREMENTS:")
        summary.append(f"  Seed Stage: {capital['seed_stage']}")
        summary.append(f"  Total to Profitability: {capital['total_to_profitability']}")
        summary.append(f"  Capital Efficiency: {capital['capital_efficiency']}")
        summary.append("")

        # Verdict
        verdict = analysis['verdict']
        summary.append("VERDICT:")
        summary.append(f"  Recommendation: {verdict['recommendation']}")
        summary.append(f"  Confidence: {verdict['confidence']}")
        summary.append("")

        if verdict['key_strengths']:
            summary.append("  Strengths:")
            for strength in verdict['key_strengths']:
                summary.append(f"    - {strength}")
            summary.append("")

        if verdict['key_concerns']:
            summary.append("  Concerns:")
            for concern in verdict['key_concerns']:
                summary.append(f"    - {concern}")
            summary.append("")

        if verdict['next_steps']:
            summary.append("NEXT STEPS:")
            for i, step in enumerate(verdict['next_steps'], 1):
                summary.append(f"  {i}. {step}")

        summary.append("")
        summary.append("=" * 70)

        return "\n".join(summary)


def main():
    """Test financial modeler"""
    modeler = FinancialModeler()

    # Test with a sample opportunity
    test_opportunity = {
        'name': 'Subscription-Based Trading Platform',
        'raw_text': 'Market size: $500M, growing at 15% CAGR. Subscription model for traders.',
        'combined_score': 0.84
    }

    print("Running financial analysis...")
    analysis = modeler.run_full_analysis(test_opportunity)

    print(modeler.generate_summary(analysis))

    # Save to file
    output_dir = Path(__file__).parent.parent / 'logs'
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / 'financial_analysis_test.json'
    modeler.save_analysis(analysis, str(output_file))
    print(f"\nAnalysis saved to: {output_file}")


if __name__ == "__main__":
    main()
