#!/usr/bin/env python3
"""
NVIDIA Driver Downloader Helper
Downloads the latest NVIDIA driver for RTX 3060
"""

import sys
import subprocess
import os
from pathlib import Path

def open_nvidia_driver_page():
    """Open NVIDIA driver download page in default browser"""

    # Construct the URL for RTX 3060 driver search
    url = "https://www.nvidia.com/Download/index.aspx?lang=en-us"

    # Direct URL with pre-filled parameters for RTX 3060
    direct_url = (
        "https://www.nvidia.com/en-us/drivers/results/"
        "?operatingSystem=Windows+11+64-bit"
        "&series=GeForce+RTX+30+Series"
        "&product=GeForce+RTX+3060"
        "&driverType=Game+Ready+Driver+(GRD)"
    )

    print("=" * 70)
    print("NVIDIA Driver Download Helper")
    print("=" * 70)
    print()
    print("GPU: GeForce RTX 3060")
    print("Driver Needed: 572.70 or newer (for CUDA 13.1 support)")
    print()
    print("Opening NVIDIA driver download page in your browser...")
    print()

    # Try to open the URL
    try:
        if sys.platform == 'win32':
            os.startfile(direct_url)
        elif sys.platform == 'darwin':
            subprocess.run(['open', direct_url])
        else:
            subprocess.run(['xdg-open', direct_url])

        print("✓ Browser opened successfully")
        print()
        print("Steps:")
        print("1. Verify the driver version shown (should be 572.70+)")
        print("2. Click the Download button")
        print("3. Save the .exe file to your Downloads folder")
        print("4. Run the installer (select Custom > Clean Installation)")
        print("5. Restart your computer")
        print()
        print("After restart, test Ollama:")
        print("  ollama run qwen2.5:0.5b \"hello\"")
        print()

    except Exception as e:
        print(f"Error opening browser: {e}")
        print()
        print("Manual steps:")
        print(f"1. Open this URL in your browser:")
        print(f"   {direct_url}")
        print()
        print("2. Download the driver")
        print("3. Run the installer")
        print()


def check_current_driver():
    """Check currently installed NVIDIA driver version"""
    print()
    print("Checking current driver version...")
    print()

    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=driver_version', '--format=csv,noheader'],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"Current Driver: {version}")

            # Check if update needed
            major_version = int(version.split('.')[0])
            if major_version < 570:
                print("⚠️  Update needed! (Need 570.65+ for CUDA 13.1)")
            elif major_version >= 572:
                print("✓ Driver version should support CUDA 13.1")
            else:
                print("⚠️  Driver version may work but 572+ recommended")
        else:
            print("Could not detect driver version")

    except Exception as e:
        print(f"Error checking driver: {e}")

    print()


if __name__ == "__main__":
    check_current_driver()
    open_nvidia_driver_page()

    print("=" * 70)
    print("Download helper complete")
    print("=" * 70)
