#!/usr/bin/env python3
"""
Dual GPU Manager - Automatically uses RTX 5070 or RTX 3060
Routes tasks to best available GPU with automatic fallback
"""

import os
import sys
import requests
import json
from datetime import datetime
from typing import Optional, Dict, List

class DualGPUManager:
    def __init__(self):
        self.rtx_5070_host = None  # Will be set after user provides IP
        self.rtx_3060_host = "http://localhost:11434"
        self.active_gpu = None
        self.gpu_stats = {
            'rtx_5070': {'attempts': 0, 'successes': 0, 'failures': 0},
            'rtx_3060': {'attempts': 0, 'successes': 0, 'failures': 0}
        }

        # GPU priorities (higher = better)
        self.gpu_priority = {
            'rtx_5070': 100,  # Prefer RTX 5070 (more powerful)
            'rtx_3060': 50    # Fallback to local RTX 3060
        }

    def set_rtx5070_ip(self, ip_address: str):
        """Set RTX 5070 IP address once provided by user"""
        self.rtx_5070_host = f"http://{ip_address}:11434"
        print(f"[OK] RTX 5070 configured at {self.rtx_5070_host}")

    def test_gpu(self, gpu_name: str, host: str, timeout: int = 3) -> bool:
        """Test if a GPU is available and responding"""
        if not host:
            return False

        try:
            # Quick health check
            response = requests.get(f"{host}/api/tags", timeout=timeout)
            if response.status_code == 200:
                self.gpu_stats[gpu_name]['successes'] += 1
                return True
        except Exception as e:
            self.gpu_stats[gpu_name]['failures'] += 1
            return False

        return False

    def select_best_gpu(self) -> Optional[str]:
        """Select best available GPU based on priority and availability"""

        # Try RTX 5070 first (if configured and available)
        if self.rtx_5070_host:
            self.gpu_stats['rtx_5070']['attempts'] += 1
            if self.test_gpu('rtx_5070', self.rtx_5070_host):
                self.active_gpu = 'rtx_5070'
                os.environ['OLLAMA_HOST'] = self.rtx_5070_host
                print(f"[OK] Using RTX 5070 (Remote) - {self.rtx_5070_host}")
                return 'rtx_5070'

        # Fallback to local RTX 3060
        self.gpu_stats['rtx_3060']['attempts'] += 1
        if self.test_gpu('rtx_3060', self.rtx_3060_host):
            self.active_gpu = 'rtx_3060'
            os.environ['OLLAMA_HOST'] = self.rtx_3060_host
            print(f"[OK] Using RTX 3060 (Local) - {self.rtx_3060_host}")
            return 'rtx_3060'

        print("[ERROR] No GPUs available!")
        return None

    def run_prompt(self, model: str, prompt: str, max_retries: int = 2) -> Optional[str]:
        """
        Run a prompt on best available GPU with automatic retry/fallback
        """
        for attempt in range(max_retries):
            gpu = self.select_best_gpu()

            if not gpu:
                print(f"[ERROR] No GPU available (attempt {attempt+1}/{max_retries})")
                continue

            try:
                host = self.rtx_5070_host if gpu == 'rtx_5070' else self.rtx_3060_host

                response = requests.post(
                    f"{host}/api/generate",
                    json={
                        'model': model,
                        'prompt': prompt,
                        'stream': False
                    },
                    timeout=120
                )

                if response.status_code == 200:
                    result = response.json()
                    return result.get('response', '')

            except Exception as e:
                print(f"[ERROR] {gpu} failed: {str(e)}")
                # Mark GPU as temporarily unavailable and retry
                if gpu == 'rtx_5070':
                    self.rtx_5070_host = None  # Will retry RTX 3060

        return None

    def get_status(self) -> Dict:
        """Get current GPU status and statistics"""
        return {
            'active_gpu': self.active_gpu,
            'rtx_5070_configured': self.rtx_5070_host is not None,
            'rtx_5070_host': self.rtx_5070_host,
            'rtx_3060_host': self.rtx_3060_host,
            'stats': self.gpu_stats,
            'timestamp': datetime.now().isoformat()
        }

    def print_status(self):
        """Print formatted GPU status"""
        status = self.get_status()

        print("\n" + "="*60)
        print("DUAL GPU MANAGER STATUS")
        print("="*60)
        print(f"Active GPU: {status['active_gpu'] or 'None'}")
        print(f"RTX 5070 Configured: {status['rtx_5070_configured']}")
        if status['rtx_5070_host']:
            print(f"RTX 5070 Host: {status['rtx_5070_host']}")
        print(f"RTX 3060 Host: {status['rtx_3060_host']}")
        print("\nStatistics:")
        for gpu, stats in status['stats'].items():
            print(f"  {gpu.upper()}:")
            print(f"    Attempts: {stats['attempts']}")
            print(f"    Successes: {stats['successes']}")
            print(f"    Failures: {stats['failures']}")
            if stats['attempts'] > 0:
                success_rate = (stats['successes'] / stats['attempts']) * 100
                print(f"    Success Rate: {success_rate:.1f}%")
        print("="*60 + "\n")


def main():
    """Example usage"""
    manager = DualGPUManager()

    # Check if RTX 5070 IP is provided via command line
    if len(sys.argv) > 1:
        rtx5070_ip = sys.argv[1]
        manager.set_rtx5070_ip(rtx5070_ip)
    else:
        print("[INFO] RTX 5070 not configured. Using local RTX 3060 only.")
        print("[INFO] To use RTX 5070, run: python dual_gpu_manager.py <RTX5070_IP>")

    # Test connection
    print("\nTesting GPU availability...")
    gpu = manager.select_best_gpu()

    if gpu:
        print(f"\n[OK] Successfully connected to {gpu.upper()}")

        # Run a test prompt
        print("\nRunning test prompt...")
        result = manager.run_prompt(
            model="qwen2.5:0.5b",
            prompt="Respond with 'GPU connection successful' if you can read this."
        )

        if result:
            print(f"\n[OK] Test Result: {result[:100]}...")
        else:
            print("\n[ERROR] Test failed")
    else:
        print("\n[ERROR] No GPU available")

    # Print final status
    manager.print_status()


if __name__ == "__main__":
    main()
