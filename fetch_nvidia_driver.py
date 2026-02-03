#!/usr/bin/env python3
"""
Fetch NVIDIA Driver Direct Download Link
Uses NVIDIA's API to get the latest driver for RTX 3060
"""

import requests
import json

def get_nvidia_driver_info():
    """Get driver info from NVIDIA's lookup API"""

    # NVIDIA Driver lookup API endpoint
    # These are the parameters for RTX 3060, Windows 11
    params = {
        'psid': '135',  # GeForce RTX 3060
        'pfid': '930',  # GeForce RTX 30 Series
        'osid': '57',   # Windows 11 64-bit
        'lid': '1',     # English
        'whql': '1',    # WHQL certified
        'ctk': '0',     # Not Beta
        'dtcid': '1'    # Game Ready Driver
    }

    # Try to fetch from NVIDIA
    url = "https://gfwsl.geforce.com/services_toolkit/services/com/nvidia/services/AjaxDriverService.php"

    try:
        print("Fetching latest NVIDIA driver info...")
        print(f"GPU: GeForce RTX 3060")
        print(f"OS: Windows 11 64-bit")
        print()

        # Add method to params
        params['func'] = 'DriverManualLookup'

        response = requests.get(url, params=params, timeout=30)

        if response.status_code == 200:
            data = response.json()

            if 'IDS' in data and len(data['IDS']) > 0:
                driver_info = data['IDS'][0]

                print(f"Found Driver:")
                print(f"  Version: {driver_info.get('Version', 'Unknown')}")
                print(f"  Release Date: {driver_info.get('ReleaseDateTime', 'Unknown')}")
                print(f"  File Size: {driver_info.get('DownloadURL', 'Unknown')}")
                print()

                # Try to construct download URL
                download_url = driver_info.get('DownloadURL', '')
                if download_url:
                    print(f"Download URL: {download_url}")
                    return download_url
                else:
                    print("No download URL found in response")
                    return None
            else:
                print("No driver found in response")
                return None
        else:
            print(f"Error: HTTP {response.status_code}")
            return None

    except Exception as e:
        print(f"Error fetching driver info: {e}")
        return None


def main():
    print("=" * 70)
    print("NVIDIA Driver Fetcher")
    print("=" * 70)
    print()

    driver_url = get_nvidia_driver_info()

    if not driver_url:
        print()
        print("Could not fetch direct download link automatically.")
        print()
        print("Manual download required:")
        print("1. Visit: https://www.nvidia.com/en-us/geforce/drivers/")
        print("2. Select RTX 3060")
        print("3. Download version 572.70 or newer")
        print()
    else:
        print()
        print("You can download from this URL or use the manual method.")
        print()

    print("=" * 70)


if __name__ == "__main__":
    main()
