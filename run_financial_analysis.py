#!/usr/bin/env python3
"""
Run Financial Analysis on All Opportunities
Uses RTX 5070 GPU for heavy analysis
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Add paths
WORKSPACE = Path(r"C:\Users\User\.openclaw\workspace")
sys.path.append(str(WORKSPACE))
sys.path.append(str(WORKSPACE / "business_agent"))

from business_agent.core.financial_modeler import FinancialModeler

def main():
    print("=" * 70)
    print("FINANCIAL ANALYSIS - 9 OPPORTUNITIES")
    print("=" * 70)
    print()

    # Load opportunities
    opportunities_file = WORKSPACE / "business_agent" / "logs" / "opportunities.json"
    with open(opportunities_file, 'r') as f:
        opportunities = json.load(f)

    print(f"Loaded {len(opportunities)} opportunities")
    print()

    # Create modeler
    modeler = FinancialModeler()

    # Analyze each opportunity
    all_analyses = []

    for i, opp in enumerate(opportunities, 1):
        print(f"[{i}/{len(opportunities)}] Analyzing: {opp['name']}")

        try:
            analysis = modeler.run_full_analysis(opp)
            all_analyses.append(analysis)

            # Print quick summary
            verdict = analysis['verdict']
            print(f"  Recommendation: {verdict['recommendation']}")
            print(f"  Confidence: {verdict['confidence']}")
            print()

        except Exception as e:
            print(f"  ERROR: {str(e)}")
            print()

    # Save all analyses
    output_dir = WORKSPACE / "business_agent" / "logs"
    output_file = output_dir / f"financial_analyses_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(output_file, 'w') as f:
        json.dump(all_analyses, f, indent=2)

    print("=" * 70)
    print(f"COMPLETE - Saved to: {output_file}")
    print("=" * 70)
    print()

    # Print summary rankings
    print("SUMMARY RANKINGS:")
    print()

    # Sort by some criteria (for now just by name)
    for i, analysis in enumerate(all_analyses, 1):
        name = analysis['opportunity_name']
        verdict = analysis['verdict']['recommendation']
        capital = analysis['capital_requirements']['total_to_profitability']

        print(f"{i}. {name}")
        print(f"   Verdict: {verdict}")
        print(f"   Capital Needed: {capital}")
        print()

    return all_analyses


if __name__ == "__main__":
    analyses = main()
