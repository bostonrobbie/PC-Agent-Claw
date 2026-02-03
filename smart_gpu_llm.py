#!/usr/bin/env python3
"""
Smart GPU LLM - Automatically uses best available GPU
Priority: RTX 5070 (remote) > RTX 3060 (local)
"""

import os
import sys
import requests
import subprocess
from pathlib import Path

class SmartGPU:
    """Automatically selects and uses the best available GPU for LLM tasks"""

    def __init__(self):
        self.available_gpus = {
            'rtx_5070': {
                'name': 'RTX 5070 (Remote)',
                'host': None,  # Will be configured
                'priority': 1,
                'vram': '12GB',
                'performance': 'Highest'
            },
            'rtx_3060': {
                'name': 'RTX 3060 (Local - Viper PC)',
                'host': 'http://localhost:11434',
                'priority': 2,
                'vram': '12GB',
                'performance': 'High'
            }
        }
        self.active_gpu = None
        self.ollama_host = None

    def configure_rtx_5070(self, host):
        """
        Configure RTX 5070 remote access

        Args:
            host (str): RTX 5070 Ollama host
                       Examples:
                       - "http://192.168.1.100:11434" (local network)
                       - "http://100.x.x.x:11434" (Tailscale)
        """
        self.available_gpus['rtx_5070']['host'] = host

    def test_gpu_connection(self, gpu_name):
        """Test if a GPU is available"""
        gpu = self.available_gpus.get(gpu_name)
        if not gpu or not gpu['host']:
            return False

        try:
            response = requests.get(
                f"{gpu['host']}/api/tags",
                timeout=2
            )
            return response.status_code == 200
        except:
            return False

    def select_best_gpu(self):
        """
        Automatically select the best available GPU

        Returns:
            str: Name of selected GPU
        """
        # Sort GPUs by priority
        sorted_gpus = sorted(
            self.available_gpus.items(),
            key=lambda x: x[1]['priority']
        )

        for gpu_name, gpu_info in sorted_gpus:
            if self.test_gpu_connection(gpu_name):
                self.active_gpu = gpu_name
                self.ollama_host = gpu_info['host']
                os.environ['OLLAMA_HOST'] = gpu_info['host']
                return gpu_name

        # No GPU available
        return None

    def get_status(self):
        """Get current GPU status"""
        if not self.active_gpu:
            self.select_best_gpu()

        if self.active_gpu:
            gpu = self.available_gpus[self.active_gpu]
            return {
                'gpu': gpu['name'],
                'host': gpu['host'],
                'vram': gpu['vram'],
                'performance': gpu['performance'],
                'status': 'Available'
            }
        else:
            return {
                'gpu': 'None',
                'status': 'No GPU Available'
            }

    def run_prompt(self, model, prompt):
        """
        Run a prompt on the best available GPU

        Args:
            model (str): Model name (e.g., "qwen2.5:7b")
            prompt (str): The prompt text

        Returns:
            str: Model response
        """
        if not self.active_gpu:
            gpu = self.select_best_gpu()
            if not gpu:
                return "Error: No GPU available"

        try:
            # Set OLLAMA_HOST environment variable
            env = os.environ.copy()
            env['OLLAMA_HOST'] = self.ollama_host

            result = subprocess.run(
                ['ollama', 'run', model, prompt],
                capture_output=True,
                text=True,
                timeout=120,
                env=env
            )

            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return f"Error: {result.stderr}"

        except Exception as e:
            return f"Error: {e}"


def main():
    """Interactive GPU selector and tester"""
    print("=" * 70)
    print("Smart GPU LLM Selector")
    print("=" * 70)
    print()

    gpu = SmartGPU()

    # Check if RTX 5070 config exists
    config_file = Path(__file__).parent / "rtx_5070_config.txt"
    if config_file.exists():
        with open(config_file, 'r') as f:
            rtx_5070_host = f.read().strip()
            gpu.configure_rtx_5070(rtx_5070_host)
            print(f"RTX 5070 configured: {rtx_5070_host}")
            print()

    print("Testing available GPUs...")
    print()

    # Test RTX 5070
    if gpu.available_gpus['rtx_5070']['host']:
        if gpu.test_gpu_connection('rtx_5070'):
            print("[OK] RTX 5070 (Remote): AVAILABLE")
        else:
            print("[X] RTX 5070 (Remote): Not reachable")
    else:
        print("[O] RTX 5070 (Remote): Not configured")

    # Test RTX 3060
    if gpu.test_gpu_connection('rtx_3060'):
        print("[OK] RTX 3060 (Local): AVAILABLE")
    else:
        print("[X] RTX 3060 (Local): Not available")

    print()
    print("Selecting best GPU...")
    best_gpu = gpu.select_best_gpu()

    if best_gpu:
        status = gpu.get_status()
        print(f"[OK] Using: {status['gpu']}")
        print(f"  Host: {status['host']}")
        print(f"  VRAM: {status['vram']}")
        print(f"  Performance: {status['performance']}")
        print()

        # Test with a prompt
        print("Running test prompt...")
        response = gpu.run_prompt("qwen2.5:7b", "Say 'GPU working' if you can read this")
        print(f"Response: {response}")
    else:
        print("[X] No GPU available")

    print()
    print("=" * 70)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "configure":
        # Configure RTX 5070
        if len(sys.argv) > 2:
            host = sys.argv[2]
            config_file = Path(__file__).parent / "rtx_5070_config.txt"
            with open(config_file, 'w') as f:
                f.write(host)
            print(f"RTX 5070 configured: {host}")
            print(f"Config saved to: {config_file}")
        else:
            print("Usage: python smart_gpu_llm.py configure <host>")
            print("Example: python smart_gpu_llm.py configure http://192.168.1.100:11434")
    else:
        main()
