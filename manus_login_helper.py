#!/usr/bin/env python3
"""
Manus Login Helper - Opens Manus and keeps browser open for manual login
"""

from playwright.sync_api import sync_playwright
import time

def open_manus_for_login():
    """Open Manus browser and wait for manual login"""

    print("=" * 60)
    print("Manus Login Helper")
    print("=" * 60)
    print()
    print("Opening Manus for you to login...")
    print()

    with sync_playwright() as p:
        # Launch browser with user data dir for persistent login
        user_data_dir = r"C:\Users\User\AppData\Local\ManusBrowserData"

        print(f"Using browser profile: {user_data_dir}")
        print("This will save your login for future sessions")
        print()

        browser = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            channel='chrome',
            slow_mo=500
        )

        page = browser.pages[0] if browser.pages else browser.new_page()

        # Navigate to Manus
        print("Navigating to Manus...")
        page.goto("https://manus.im/", wait_until='networkidle')

        print()
        print("=" * 60)
        print("Browser is open for you to login")
        print("=" * 60)
        print()
        print("Please:")
        print("1. Login to Manus using your preferred method")
        print("2. Navigate around to make sure it works")
        print("3. Find the 'Signals and Strategy' chat if possible")
        print("4. When done, close this browser window")
        print()
        print("Your login will be saved for next time!")
        print("=" * 60)

        # Wait for user to close browser manually
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nClosing browser...")

        browser.close()

if __name__ == "__main__":
    open_manus_for_login()
