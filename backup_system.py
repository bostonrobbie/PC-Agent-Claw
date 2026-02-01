#!/usr/bin/env python3
"""
Backup System - Protect Claude's memory and prevent data loss
"""

from pathlib import Path
from datetime import datetime
import shutil
import json

WORKSPACE = Path(r"C:\Users\User\.openclaw\workspace")
BACKUPS = WORKSPACE / "backups"

class BackupSystem:
    """Automated backup system for Claude's memory"""

    def __init__(self):
        BACKUPS.mkdir(parents=True, exist_ok=True)
        (BACKUPS / "daily").mkdir(exist_ok=True)
        (BACKUPS / "weekly").mkdir(exist_ok=True)
        (BACKUPS / "critical").mkdir(exist_ok=True)

    def backup_daily(self):
        """Daily backup of essential files"""
        today = datetime.now().strftime("%Y-%m-%d")
        backup_dir = BACKUPS / "daily" / today
        backup_dir.mkdir(exist_ok=True)

        # Critical files to backup
        files_to_backup = [
            "USER.md",
            "IDENTITY.md",
            "TOOLS.md",
            "MEMORY.md",
            "memory/",
            "iterations/",
        ]

        for item in files_to_backup:
            source = WORKSPACE / item
            if source.exists():
                if source.is_dir():
                    dest = backup_dir / item
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.copytree(source, dest)
                else:
                    shutil.copy2(source, backup_dir / item)

        # Create backup manifest
        manifest = {
            'date': datetime.now().isoformat(),
            'type': 'daily',
            'files_backed_up': [str(f) for f in backup_dir.rglob('*') if f.is_file()]
        }

        with open(backup_dir / "manifest.json", 'w') as f:
            json.dump(manifest, f, indent=2)

        return backup_dir

    def backup_weekly(self):
        """Weekly full snapshot"""
        week = datetime.now().strftime("%Y-W%W")
        backup_dir = BACKUPS / "weekly" / week
        backup_dir.mkdir(exist_ok=True)

        # Full workspace backup
        for item in WORKSPACE.iterdir():
            if item.name == 'backups':
                continue  # Don't backup backups

            dest = backup_dir / item.name

            if item.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)

        manifest = {
            'date': datetime.now().isoformat(),
            'type': 'weekly',
            'full_snapshot': True
        }

        with open(backup_dir / "manifest.json", 'w') as f:
            json.dump(manifest, f, indent=2)

        return backup_dir

    def backup_critical(self, change_name):
        """Backup before critical changes"""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_dir = BACKUPS / "critical" / f"{change_name}_{timestamp}"
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Full workspace backup
        for item in WORKSPACE.iterdir():
            if item.name == 'backups':
                continue

            dest = backup_dir / item.name

            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)

        manifest = {
            'date': datetime.now().isoformat(),
            'type': 'critical',
            'change': change_name,
            'note': 'Backup before critical operation'
        }

        with open(backup_dir / "manifest.json", 'w') as f:
            json.dump(manifest, f, indent=2)

        return backup_dir

    def list_backups(self, backup_type='all'):
        """List available backups"""
        backups = []

        if backup_type in ['all', 'daily']:
            for backup in (BACKUPS / "daily").iterdir():
                if backup.is_dir():
                    backups.append(('daily', backup.name, backup))

        if backup_type in ['all', 'weekly']:
            for backup in (BACKUPS / "weekly").iterdir():
                if backup.is_dir():
                    backups.append(('weekly', backup.name, backup))

        if backup_type in ['all', 'critical']:
            for backup in (BACKUPS / "critical").iterdir():
                if backup.is_dir():
                    backups.append(('critical', backup.name, backup))

        return backups

    def restore(self, backup_path):
        """Restore from a backup (USE WITH CAUTION)"""
        backup_path = Path(backup_path)

        if not backup_path.exists():
            raise ValueError(f"Backup not found: {backup_path}")

        # Create a backup of current state first
        safety_backup = self.backup_critical("before_restore")

        print(f"Created safety backup at: {safety_backup}")
        print(f"Restoring from: {backup_path}")

        # Restore files
        for item in backup_path.iterdir():
            if item.name == 'manifest.json':
                continue

            dest = WORKSPACE / item.name

            if item.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)

        print("Restore complete!")

# Run daily backup
if __name__ == "__main__":
    backup = BackupSystem()

    print("Running daily backup...")
    daily_backup = backup.backup_daily()
    print(f"Daily backup created: {daily_backup}")

    # List all backups
    print("\nAvailable backups:")
    for type, name, path in backup.list_backups():
        print(f"  [{type}] {name}")
