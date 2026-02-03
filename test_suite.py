#!/usr/bin/env python3
"""
Automated test suite - runs before claiming anything works
"""

import subprocess
import requests
import json
import time
from pathlib import Path

class TestSuite:
    def __init__(self):
        self.results = []
        self.workspace = Path("C:/Users/User/.openclaw/workspace")

    def test_telegram_notifications(self):
        """Test I can send you messages"""
        print("Testing Telegram notifications...")
        try:
            response = requests.post(
                "https://api.telegram.org/bot7509919329:AAEm5g4H7YYiUTkrQiRNdoJmMgM4PW5M4gA/sendMessage",
                json={"chat_id": "5791597360", "text": "Test: OpenClaw health check"},
                timeout=10
            )
            success = response.status_code == 200
            self.results.append(("Telegram Notifications", success))
            return success
        except Exception as e:
            self.results.append(("Telegram Notifications", False, str(e)))
            return False

    def test_file_operations(self):
        """Test I can read/write files"""
        print("Testing file operations...")
        try:
            test_file = self.workspace / "test_temp.txt"
            # Write
            test_file.write_text("test content")
            # Read
            content = test_file.read_text()
            # Delete
            test_file.unlink()
            success = content == "test content"
            self.results.append(("File Operations", success))
            return success
        except Exception as e:
            self.results.append(("File Operations", False, str(e)))
            return False

    def test_command_execution(self):
        """Test I can run commands"""
        print("Testing command execution...")
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            success = result.returncode == 0
            self.results.append(("Command Execution", success))
            return success
        except Exception as e:
            self.results.append(("Command Execution", False, str(e)))
            return False

    def test_antigravity_workspace(self):
        """Test access to Antigravity workspace"""
        print("Testing Antigravity workspace access...")
        try:
            workspace = Path("C:/Users/User/Documents/AI")
            success = workspace.exists() and workspace.is_dir()
            self.results.append(("Antigravity Workspace", success))
            return success
        except Exception as e:
            self.results.append(("Antigravity Workspace", False, str(e)))
            return False

    def run_all(self):
        """Run all tests and return report"""
        print("\n=== OpenClaw Health Check ===\n")

        self.test_telegram_notifications()
        self.test_file_operations()
        self.test_command_execution()
        self.test_antigravity_workspace()

        # Generate report
        print("\n=== Test Results ===")
        all_passed = True
        for result in self.results:
            name = result[0]
            passed = result[1]
            status = "[PASS]" if passed else "[FAIL]"
            print(f"{status}: {name}")
            if not passed and len(result) > 2:
                print(f"  Error: {result[2]}")
            all_passed = all_passed and passed

        print(f"\nOverall: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")
        return all_passed

if __name__ == "__main__":
    suite = TestSuite()
    success = suite.run_all()
    exit(0 if success else 1)
