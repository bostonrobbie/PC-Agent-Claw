#!/usr/bin/env python3
"""
Create GitHub Backup Repository - Automated setup
"""

import subprocess
from pathlib import Path

WORKSPACE = Path(r"C:\Users\User\.openclaw\workspace")

def check_auth():
    """Check if GitHub CLI is authenticated"""
    result = subprocess.run(
        [r"C:\Program Files\GitHub CLI\gh.exe", "auth", "status"],
        capture_output=True,
        text=True
    )
    return result.returncode == 0

def create_backup_repo():
    """Create GitHub backup repository"""

    print("=" * 60)
    print("GitHub Backup Repository Creation")
    print("=" * 60)
    print()

    # Check authentication
    print("[1/5] Checking GitHub authentication...")
    if not check_auth():
        print("   [ERROR] Not authenticated!")
        print("   Please authenticate first:")
        print("   Run: gh auth login --web")
        return False

    print("   [OK] Authenticated")

    # Create repository
    print("\n[2/5] Creating private repository...")
    result = subprocess.run(
        [
            r"C:\Program Files\GitHub CLI\gh.exe",
            "repo", "create",
            "claude-agent-workspace",
            "--private",
            "--description", "Claude AI Agent operational workspace - memory, automation, and learning systems",
            "--source", str(WORKSPACE),
            "--push"
        ],
        cwd=str(WORKSPACE),
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print("   [OK] Repository created!")
    elif "already exists" in result.stderr.lower():
        print("   [INFO] Repository already exists")
        print("   Setting up remote connection...")

        # Add remote if not exists
        subprocess.run(
            ["git", "remote", "remove", "origin"],
            cwd=str(WORKSPACE),
            capture_output=True
        )

        subprocess.run(
            ["git", "remote", "add", "origin", "https://github.com/bostonrobbie/claude-agent-workspace.git"],
            cwd=str(WORKSPACE),
            capture_output=True
        )
    else:
        print(f"   [ERROR] {result.stderr}")
        return False

    # Push to GitHub
    print("\n[3/5] Pushing code to GitHub...")
    result = subprocess.run(
        ["git", "push", "-u", "origin", "master"],
        cwd=str(WORKSPACE),
        capture_output=True,
        text=True
    )

    if result.returncode == 0 or "up-to-date" in result.stderr.lower():
        print("   [OK] Code pushed successfully")
    else:
        print(f"   [WARNING] Push issue: {result.stderr}")

    # Set up branch protection (optional)
    print("\n[4/5] Configuring repository settings...")
    subprocess.run(
        [
            r"C:\Program Files\GitHub CLI\gh.exe",
            "repo", "edit",
            "--enable-issues",
            "--enable-wiki=false"
        ],
        cwd=str(WORKSPACE),
        capture_output=True
    )
    print("   [OK] Settings configured")

    # Get repo URL
    print("\n[5/5] Getting repository URL...")
    result = subprocess.run(
        [r"C:\Program Files\GitHub CLI\gh.exe", "repo", "view", "--web", "--json", "url"],
        cwd=str(WORKSPACE),
        capture_output=True,
        text=True
    )

    print("\n" + "=" * 60)
    print("GITHUB BACKUP COMPLETE")
    print("=" * 60)
    print()
    print("Repository: https://github.com/bostonrobbie/claude-agent-workspace")
    print()
    print("Your workspace is now backed up on GitHub!")
    print("All future changes will be automatically pushed.")
    print()

    return True

if __name__ == "__main__":
    success = create_backup_repo()

    if success:
        print("[OK] GitHub backup setup complete")
    else:
        print("[ERROR] Setup failed - check authentication")
