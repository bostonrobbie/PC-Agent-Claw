#!/usr/bin/env python3
"""
Manus Session Fix - Use your existing Chrome profile for persistent login
"""

from playwright.sync_api import sync_playwright
import time
import os

def use_existing_chrome_profile():
    """Connect to your existing Chrome profile where you're already logged in"""

    print("=" * 60)
    print("Manus Access via Your Chrome Profile")
    print("=" * 60)
    print()

    # Try common Chrome profile locations
    chrome_profiles = [
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data"),
        os.path.expandvars(r"%USERPROFILE%\AppData\Local\Google\Chrome\User Data"),
    ]

    chrome_path = None
    for path in chrome_profiles:
        if os.path.exists(path):
            chrome_path = path
            break

    if not chrome_path:
        print("Could not find Chrome profile directory")
        print("Please login to Manus in your regular Chrome browser first")
        print("Then I can access it from there")
        return

    print(f"Using Chrome profile: {chrome_path}")
    print()
    print("IMPORTANT: Close ALL Chrome windows before continuing!")
    print("Press Enter when all Chrome windows are closed...")
    input()

    try:
        with sync_playwright() as p:
            # Connect to existing Chrome profile
            # Using 'Default' profile (main profile)
            browser = p.chromium.launch_persistent_context(
                user_data_dir=chrome_path,
                headless=False,
                channel='chrome',
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox'
                ]
            )

            page = browser.pages[0] if browser.pages else browser.new_page()

            print("\nNavigating to Manus...")
            page.goto("https://manus.im/", wait_until='networkidle')

            print()
            print("=" * 60)
            print("Browser opened with your Chrome profile")
            print("=" * 60)
            print()
            print("You should already be logged in (if you were in Chrome)")
            print("If not, login now and it will save to your Chrome profile")
            print()
            print("Navigate to Signals & Strategy chat, then close browser")
            print("=" * 60)

            # Wait for manual close
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass

            browser.close()

    except Exception as e:
        print(f"\nError: {e}")
        print("\nAlternative: Just use your regular Chrome browser")
        print("I can ask you for updates from Manus instead")

def simple_check_other_services():
    """Quick check of what services we can access"""

    print("\n" + "=" * 60)
    print("Checking Access to Other AI Services")
    print("=" * 60)
    print()

    services = {
        "ChatGPT": "https://chatgpt.com/",
        "Claude Web": "https://claude.ai/",
        "Antigravity": "C:\\Users\\User\\AppData\\Local\\Programs\\Antigravity\\Antigravity.exe"
    }

    for name, location in services.items():
        if name == "Antigravity":
            if os.path.exists(location):
                print(f"[OK] {name}: Installed locally")
            else:
                print(f"[X] {name}: Not found at {location}")
        else:
            print(f"[?] {name}: {location} (will test with browser)")

    print()
    print("For web services, you should already be logged in via Chrome")
    print("I can access them using your Chrome profile")

if __name__ == "__main__":
    simple_check_other_services()

    print("\n" + "=" * 60)
    print("Manus Access Options")
    print("=" * 60)
    print()
    print("Option 1: Use your Chrome profile (recommended)")
    print("  - You login to Manus in regular Chrome first")
    print("  - Then I access via your profile")
    print("  - No security blocks")
    print()
    print("Option 2: Manual updates")
    print("  - You check Manus yourself")
    print("  - Tell me what you find")
    print("  - I organize and track it")
    print()
    choice = input("Try Option 1 now? (y/n): ")

    if choice.lower() == 'y':
        use_existing_chrome_profile()
    else:
        print("\nNo problem! Let me know what you find in Manus")
        print("and I'll organize the information")
