#!/usr/bin/env python3
"""
Manus API Helper - Interact with Manus.ai API
"""

import os
import sys
import json
import requests
from pathlib import Path

WORKSPACE = Path(r"C:\Users\User\.openclaw\workspace")

class ManusAPI:
    """Manus.ai API client"""

    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get('MANUS_API_KEY')
        self.base_url = 'https://api.manus.ai/v1'

        if not self.api_key:
            print("ERROR: MANUS_API_KEY not set")
            print("Set it via: set MANUS_API_KEY=your_key_here")
            sys.exit(1)

    def create_task(self, prompt, **kwargs):
        """
        Create a new task on Manus

        Args:
            prompt (str): The task prompt
            **kwargs: Additional task parameters

        Returns:
            dict: Task response
        """
        url = f"{self.base_url}/tasks"

        headers = {
            'accept': 'application/json',
            'content-type': 'application/json',
            'API_KEY': self.api_key
        }

        data = {
            'prompt': prompt,
            **kwargs
        }

        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)

            if response.status_code == 200 or response.status_code == 201:
                print(f"✓ Task created successfully")
                return response.json()
            else:
                print(f"ERROR: API returned {response.status_code}")
                print(f"Response: {response.text}")
                return None

        except Exception as e:
            print(f"ERROR: Request failed - {e}")
            return None

    def get_task(self, task_id):
        """Get task status/result"""
        url = f"{self.base_url}/tasks/{task_id}"

        headers = {
            'accept': 'application/json',
            'API_KEY': self.api_key
        }

        try:
            response = requests.get(url, headers=headers, timeout=30)

            if response.status_code == 200:
                return response.json()
            else:
                print(f"ERROR: API returned {response.status_code}")
                print(f"Response: {response.text}")
                return None

        except Exception as e:
            print(f"ERROR: Request failed - {e}")
            return None


def test_api():
    """Test the Manus API with a simple task"""
    manus = ManusAPI()

    print("=" * 70)
    print("Testing Manus API Connection")
    print("=" * 70)
    print()

    # Test with simple prompt
    print("Creating test task...")
    result = manus.create_task("hello")

    if result:
        print()
        print("Task Response:")
        print(json.dumps(result, indent=2))

        # If task has an ID, try to get status
        if 'id' in result or 'task_id' in result:
            task_id = result.get('id') or result.get('task_id')
            print()
            print(f"Fetching task status (ID: {task_id})...")
            status = manus.get_task(task_id)

            if status:
                print()
                print("Task Status:")
                print(json.dumps(status, indent=2))
    else:
        print("Failed to create task")
        print()
        print("Make sure MANUS_API_KEY is set:")
        print("  set MANUS_API_KEY=your_key_here")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Create task from command line
        prompt = ' '.join(sys.argv[1:])
        manus = ManusAPI()
        result = manus.create_task(prompt)

        if result:
            print(json.dumps(result, indent=2))
    else:
        # Run test
        test_api()
