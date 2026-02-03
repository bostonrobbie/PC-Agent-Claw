#!/usr/bin/env python3
"""
Strategy Variant Generator - Uses Local LLM to create optimized variants
Leverages qwen2.5:7b-32k on local GPU for cost-effective analysis
"""

import requests
import json
from pathlib import Path

WORKSPACE = Path(r"C:\Users\User\.openclaw\workspace")
OLLAMA_API = "http://localhost:11434/api/generate"

class StrategyVariantGenerator:
    """Generate and test strategy variants using local LLM"""

    def __init__(self, base_strategy_results):
        self.base_results = base_strategy_results
        self.model = "qwen2.5:7b-32k"

    def query_local_llm(self, prompt):
        """Query Ollama local LLM"""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_predict": 2000
            }
        }

        try:
            response = requests.post(OLLAMA_API, json=payload, timeout=120)
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '')
            else:
                print(f"Error: {response.status_code}")
                return None
        except Exception as e:
            print(f"LLM query failed: {e}")
            return None

    def generate_variants(self):
        """Generate strategy variants based on base results"""

        prompt = f"""You are a quantitative trading strategy optimizer. Analyze this 15-minute opening range breakout strategy and suggest 3-5 variants to test.

BASE STRATEGY RESULTS (15 years backtest):
- Total Return: 348.33%
- Max Drawdown: 20.91%
- Sharpe Ratio: 0.93
- Profit Factor: 1.22
- Win Rate: 53.6%
- Total Trades: 3,515
- Avg Win: $1,038
- Avg Loss: -$985

CURRENT LOGIC:
- Captures high/low of first 5min bar (9:30-9:35)
- If price breaks above high in next 10min → LONG
- If price breaks below low in next 10min → SHORT
- Exits exactly at 9:45 bar open (15min holding period)
- One trade per day maximum

CONSTRAINTS (MUST FOLLOW):
1. Must use 5-minute OHLC data only
2. Trading window must be 9:30-9:45 AM ET or nearby
3. Maximum 1 trade per day
4. Must align with professional intraday trading rules
5. No overfitting - keep it simple
6. Must be Pine Script compatible

TASK: Suggest 3-5 variant ideas that could improve performance WITHOUT overfitting.

For each variant, provide:
1. Variant name
2. What changes from base strategy
3. Hypothesis for why it might improve results
4. Risk of overfitting (Low/Medium/High)

FORMAT your response as JSON array:
[
  {{
    "name": "Variant 1 Name",
    "changes": "What's different",
    "hypothesis": "Why this might work",
    "overfit_risk": "Low/Medium/High"
  }}
]

Only suggest variants with Low or Medium overfit risk.
"""

        print("Querying local LLM (qwen2.5:7b-32k) for strategy variants...")
        print("This may take 30-60 seconds...")

        response = self.query_local_llm(prompt)

        if response:
            print("\n" + "="*70)
            print("LLM RESPONSE:")
            print("="*70)
            print(response)
            print("="*70 + "\n")

            # Try to parse JSON from response
            try:
                # Find JSON array in response
                start = response.find('[')
                end = response.rfind(']') + 1
                if start != -1 and end > start:
                    json_str = response[start:end]
                    variants = json.loads(json_str)
                    return variants
                else:
                    # If no JSON found, return raw response
                    return response
            except json.JSONDecodeError:
                # Return raw response if JSON parsing fails
                return response

        return None

    def analyze_variant_feasibility(self, variant):
        """Use LLM to analyze if a variant is feasible"""

        prompt = f"""As a trading strategy expert, analyze this variant for feasibility:

VARIANT: {variant.get('name', 'Unknown')}
CHANGES: {variant.get('changes', 'Not specified')}
HYPOTHESIS: {variant.get('hypothesis', 'Not specified')}

EVALUATION CRITERIA:
1. Can this be implemented in Pine Script? (Yes/No)
2. Does it follow live market rules? (Yes/No)
3. Is it too complex/overfitted? (Yes/No)
4. Would it work in real-time trading? (Yes/No)
5. Overall feasibility score (1-10)

Provide brief analysis (max 200 words).
"""

        response = self.query_local_llm(prompt)
        return response

    def create_variant_pine_script(self, variant_name, changes):
        """Use LLM to generate Pine Script for variant"""

        # Read base strategy
        base_script_file = WORKSPACE / "NQ_15min_Opening_Range_Strategy.pine"
        with open(base_script_file, 'r') as f:
            base_script = f.read()

        prompt = f"""You are a Pine Script expert. Modify this base strategy to implement the variant.

BASE STRATEGY:
{base_script}

VARIANT TO IMPLEMENT:
Name: {variant_name}
Changes: {changes}

TASK: Generate the complete modified Pine Script code.

REQUIREMENTS:
1. Keep all comments and structure
2. Only modify the parts needed for the variant
3. Ensure syntax is valid Pine Script v5
4. Test that logic is sound

Output ONLY the Pine Script code, no explanations.
"""

        response = self.query_local_llm(prompt)
        return response


def main():
    """Generate and analyze strategy variants"""

    print("="*70)
    print("STRATEGY VARIANT GENERATOR")
    print("Using Local LLM: qwen2.5:7b-32k on RTX 3060")
    print("="*70 + "\n")

    # Base strategy results
    base_results = {
        'Total Return (%)': 348.33,
        'Max Drawdown (%)': 20.91,
        'Sharpe Ratio': 0.93,
        'Profit Factor': 1.22,
        'Win Rate (%)': 53.6
    }

    generator = StrategyVariantGenerator(base_results)

    # Generate variants
    print("[1/3] Generating strategy variants using local LLM...")
    variants = generator.generate_variants()

    if not variants:
        print("Failed to generate variants")
        return

    # Save variants
    variants_file = WORKSPACE / "strategy_variants.json"

    if isinstance(variants, list):
        with open(variants_file, 'w') as f:
            json.dump(variants, f, indent=2)
        print(f"\nSaved {len(variants)} variants to: {variants_file}")

        # Analyze each variant
        print("\n[2/3] Analyzing variant feasibility...")
        for i, variant in enumerate(variants, 1):
            print(f"\n--- Variant {i}: {variant.get('name', 'Unknown')} ---")
            print(f"Changes: {variant.get('changes', 'N/A')}")
            print(f"Overfit Risk: {variant.get('overfit_risk', 'N/A')}")
            print(f"\nFeasibility Analysis:")

            analysis = generator.analyze_variant_feasibility(variant)
            if analysis:
                print(analysis)
    else:
        # Raw text response
        with open(variants_file.with_suffix('.txt'), 'w') as f:
            f.write(str(variants))
        print(f"\nSaved LLM response to: {variants_file.with_suffix('.txt')}")

    print("\n[3/3] Variant generation complete!")
    print("\nNext steps:")
    print("1. Review variants in strategy_variants.json")
    print("2. Select best variant to implement")
    print("3. Backtest selected variant")
    print("4. Compare results with base strategy")

    print("\n" + "="*70)
    print("COMPLETE - Used Local LLM (Cost: $0)")
    print("="*70)


if __name__ == "__main__":
    main()
