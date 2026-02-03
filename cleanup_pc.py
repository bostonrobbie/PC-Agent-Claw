#!/usr/bin/env python3
"""
PC Cleanup Script - Find and Remove Non-Essential Files
Safe cleanup that preserves all work files
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

class PCCleaner:
    def __init__(self):
        self.user_home = Path(os.path.expanduser("~"))
        self.total_size_found = 0
        self.files_to_delete = []

        # PROTECTED DIRECTORIES - DO NOT TOUCH
        self.protected_dirs = [
            self.user_home / "Documents" / "AI",
            self.user_home / ".openclaw",
            Path("C:\\Program Files\\Interactive Brokers"),
            Path("C:\\Program Files\\MetaTrader 5"),
            Path("C:\\QuantConnect"),
            self.user_home / "AppData" / "Roaming" / "Python",
        ]

        # SAFE TO DELETE - Non-essential locations
        self.cleanup_targets = {
            'temp_files': self.user_home / "AppData" / "Local" / "Temp",
            'downloads_old': self.user_home / "Downloads",
            'desktop_screenshots': self.user_home / "Desktop",
            'browser_cache': self.user_home / "AppData" / "Local" / "Google" / "Chrome" / "User Data" / "Default" / "Cache",
        }

    def is_protected(self, path):
        """Check if path is in protected directory"""
        path = Path(path)
        for protected in self.protected_dirs:
            try:
                path.relative_to(protected)
                return True
            except ValueError:
                continue
        return False

    def get_dir_size(self, path):
        """Get total size of directory"""
        total = 0
        try:
            for entry in os.scandir(path):
                if entry.is_file(follow_symlinks=False):
                    total += entry.stat().st_size
                elif entry.is_dir(follow_symlinks=False):
                    total += self.get_dir_size(entry.path)
        except (PermissionError, FileNotFoundError):
            pass
        return total

    def format_size(self, bytes_size):
        """Format bytes to human-readable"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.2f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.2f} PB"

    def find_large_non_essential_files(self):
        """Find large files that can be safely deleted"""
        print("=" * 70)
        print("PC CLEANUP - Finding Non-Essential Files")
        print("=" * 70)
        print()

        candidates = []

        # 1. Old downloads (>30 days)
        print("[1/5] Scanning Downloads for old files...")
        downloads = self.user_home / "Downloads"
        if downloads.exists():
            cutoff_date = datetime.now().timestamp() - (30 * 24 * 60 * 60)
            for file in downloads.rglob("*"):
                if file.is_file() and not self.is_protected(file):
                    try:
                        if file.stat().st_mtime < cutoff_date:
                            size = file.stat().st_size
                            if size > 10 * 1024 * 1024:  # >10MB
                                candidates.append({
                                    'path': file,
                                    'size': size,
                                    'category': 'Old Downloads (>30 days)',
                                    'age_days': int((datetime.now().timestamp() - file.stat().st_mtime) / (24*60*60))
                                })
                    except (PermissionError, FileNotFoundError):
                        pass

        # 2. Temp files
        print("[2/5] Scanning Temp directories...")
        temp_dir = self.user_home / "AppData" / "Local" / "Temp"
        if temp_dir.exists():
            try:
                for file in temp_dir.rglob("*"):
                    if file.is_file() and not self.is_protected(file):
                        try:
                            size = file.stat().st_size
                            if size > 5 * 1024 * 1024:  # >5MB
                                candidates.append({
                                    'path': file,
                                    'size': size,
                                    'category': 'Temp Files'
                                })
                        except (PermissionError, FileNotFoundError):
                            pass
            except (PermissionError, FileNotFoundError):
                pass

        # 3. Screenshots on Desktop (>30 days old)
        print("[3/5] Scanning Desktop for old screenshots...")
        desktop = self.user_home / "Desktop"
        if desktop.exists():
            cutoff_date = datetime.now().timestamp() - (30 * 24 * 60 * 60)
            for file in desktop.glob("*.png"):
                if not self.is_protected(file):
                    try:
                        if file.stat().st_mtime < cutoff_date:
                            size = file.stat().st_size
                            candidates.append({
                                'path': file,
                                'size': size,
                                'category': 'Old Desktop Screenshots',
                                'age_days': int((datetime.now().timestamp() - file.stat().st_mtime) / (24*60*60))
                            })
                    except (PermissionError, FileNotFoundError):
                        pass

        # 4. Windows Update cleanup
        print("[4/5] Scanning Windows Update files...")
        win_update = Path("C:\\Windows\\SoftwareDistribution\\Download")
        if win_update.exists():
            try:
                size = self.get_dir_size(win_update)
                if size > 100 * 1024 * 1024:  # >100MB
                    candidates.append({
                        'path': win_update,
                        'size': size,
                        'category': 'Windows Update Cache',
                        'is_dir': True
                    })
            except (PermissionError, FileNotFoundError):
                pass

        # 5. Browser cache
        print("[5/5] Scanning browser cache...")
        chrome_cache = self.user_home / "AppData" / "Local" / "Google" / "Chrome" / "User Data" / "Default" / "Cache"
        if chrome_cache.exists():
            try:
                size = self.get_dir_size(chrome_cache)
                if size > 50 * 1024 * 1024:  # >50MB
                    candidates.append({
                        'path': chrome_cache,
                        'size': size,
                        'category': 'Browser Cache',
                        'is_dir': True
                    })
            except (PermissionError, FileNotFoundError):
                pass

        return candidates

    def show_candidates(self, candidates):
        """Display candidates for deletion"""
        print()
        print("=" * 70)
        print(f"FOUND {len(candidates)} ITEMS TO CLEAN")
        print("=" * 70)
        print()

        # Group by category
        by_category = {}
        for item in candidates:
            cat = item['category']
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(item)

        total_size = 0
        for category, items in sorted(by_category.items()):
            cat_size = sum(item['size'] for item in items)
            total_size += cat_size
            print(f"{category}: {len(items)} items ({self.format_size(cat_size)})")

            # Show top 5 largest in this category
            sorted_items = sorted(items, key=lambda x: x['size'], reverse=True)[:5]
            for item in sorted_items:
                age_str = f" ({item['age_days']} days old)" if 'age_days' in item else ""
                is_dir = " [DIR]" if item.get('is_dir') else ""
                print(f"  - {item['path'].name}{is_dir}: {self.format_size(item['size'])}{age_str}")

        print()
        print("=" * 70)
        print(f"TOTAL SPACE TO FREE: {self.format_size(total_size)}")
        print("=" * 70)
        print()

        return candidates, total_size

    def cleanup(self, candidates, dry_run=True):
        """Delete candidates (or show what would be deleted)"""
        if dry_run:
            print("DRY RUN - No files will be deleted")
            print()
            print("To actually delete, run with: python cleanup_pc.py --delete")
            return

        print("DELETING FILES...")
        print()

        deleted_count = 0
        deleted_size = 0
        errors = []

        for item in candidates:
            try:
                if item.get('is_dir'):
                    shutil.rmtree(item['path'])
                else:
                    item['path'].unlink()

                deleted_count += 1
                deleted_size += item['size']
                print(f"[OK] Deleted: {item['path']}")

            except Exception as e:
                errors.append((item['path'], str(e)))
                print(f"[ERROR] Failed to delete {item['path']}: {e}")

        print()
        print("=" * 70)
        print(f"CLEANUP COMPLETE")
        print("=" * 70)
        print(f"Deleted: {deleted_count} items")
        print(f"Freed: {self.format_size(deleted_size)}")
        if errors:
            print(f"Errors: {len(errors)}")
        print("=" * 70)


def main():
    import sys

    cleaner = PCCleaner()

    print("Scanning for non-essential files...")
    print()

    candidates = cleaner.find_large_non_essential_files()
    candidates, total_size = cleaner.show_candidates(candidates)

    # Check if user wants to actually delete
    dry_run = "--delete" not in sys.argv

    cleaner.cleanup(candidates, dry_run=dry_run)


if __name__ == "__main__":
    main()
