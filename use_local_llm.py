#!/usr/bin/env python3
"""
Local GPU LLM Helper - Use Ollama for cost-effective AI tasks
Replaces expensive API calls with free GPU-accelerated local models
"""

import subprocess
import sys
import json
from pathlib import Path

class LocalLLM:
    """Interface for using local Ollama models with GPU acceleration"""

    def __init__(self, model="qwen2.5:7b"):
        """
        Initialize with a model

        Available models:
        - qwen2.5:0.5b (fastest, 400MB)
        - qwen2.5:7b (balanced, 4.7GB) - DEFAULT
        - qwen2.5:7b-32k (longer context, 4.7GB)
        - qwen2.5:14b (most capable, 9GB)
        """
        self.model = model

    def prompt(self, text, max_length=None):
        """
        Send a prompt to the local LLM

        Args:
            text (str): The prompt text
            max_length (int): Optional max response length

        Returns:
            str: Model response
        """
        try:
            cmd = ['ollama', 'run', self.model, text]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return f"Error: {result.stderr}"

        except subprocess.TimeoutExpired:
            return "Error: Request timed out"
        except Exception as e:
            return f"Error: {e}"

    def analyze_code(self, code, language="python"):
        """Analyze code for improvements"""
        prompt = f"Analyze this {language} code and suggest improvements:\n\n{code}"
        return self.prompt(prompt)

    def generate_variants(self, base_text, num_variants=3):
        """Generate variants of text (useful for strategy testing)"""
        prompt = f"Generate {num_variants} variants of this:\n\n{base_text}\n\nFormat as numbered list."
        return self.prompt(prompt)

    def summarize(self, text):
        """Summarize long text"""
        prompt = f"Summarize this concisely:\n\n{text}"
        return self.prompt(prompt)

    def explain_strategy(self, strategy_name, details):
        """Explain a trading strategy"""
        prompt = f"Explain this trading strategy clearly:\n\nName: {strategy_name}\nDetails: {details}"
        return self.prompt(prompt)


# Example usage functions
def test_gpu_llm():
    """Test the GPU LLM functionality"""
    print("=" * 70)
    print("Testing Local GPU LLM")
    print("=" * 70)
    print()

    llm = LocalLLM("qwen2.5:7b")

    print("Test 1: Simple prompt")
    response = llm.prompt("What are 3 benefits of using local LLMs?")
    print(response)
    print()

    print("=" * 70)
    print("GPU LLM Test Complete!")
    print("=" * 70)


def analyze_backtest_results(results_file):
    """Use GPU LLM to analyze backtest results"""
    llm = LocalLLM("qwen2.5:7b")

    try:
        with open(results_file, 'r') as f:
            results = f.read()

        print("Analyzing backtest results with GPU LLM...")
        analysis = llm.prompt(
            f"Analyze these backtest results and provide insights:\n\n{results[:2000]}"
        )
        print(analysis)

    except Exception as e:
        print(f"Error: {e}")


def generate_strategy_variants(base_strategy):
    """Use GPU LLM to generate strategy variants"""
    llm = LocalLLM("qwen2.5:14b")  # Use larger model for complex task

    prompt = f"""
    Given this base trading strategy, suggest 5 optimization variants
    that could improve performance without overfitting:

    {base_strategy}

    For each variant:
    1. Describe the change
    2. Explain the hypothesis
    3. Rate overfit risk (Low/Med/High)
    """

    return llm.prompt(prompt)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Command line usage
        model = sys.argv[1] if len(sys.argv) > 2 else "qwen2.5:7b"
        prompt_text = ' '.join(sys.argv[1:]) if len(sys.argv) > 2 else sys.argv[1]

        llm = LocalLLM(model)
        response = llm.prompt(prompt_text)
        print(response)
    else:
        # Run test
        test_gpu_llm()
