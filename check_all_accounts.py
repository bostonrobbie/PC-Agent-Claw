#!/usr/bin/env python3
"""
Check all AI service accounts and access Manus
"""

from playwright.sync_api import sync_playwright
import time
import os
from pathlib import Path

WORKSPACE = Path(r"C:\Users\User\.openclaw\workspace")

def check_all_services():
    """Check ChatGPT, Claude, and Manus with Chrome profile"""

    print("=" * 60)
    print("Checking All AI Service Accounts")
    print("=" * 60)
    print()

    chrome_profile = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")

    print(f"Using Chrome profile: {chrome_profile}")
    print()

    with sync_playwright() as p:
        # Launch with Chrome profile
        print("Opening browser with your Chrome profile...")
        browser = p.chromium.launch_persistent_context(
            user_data_dir=chrome_profile,
            headless=False,
            channel='chrome',
            slow_mo=1000,
            args=[
                '--disable-blink-features=AutomationControlled',
            ]
        )

        results = {}

        # Check ChatGPT
        print("\n[1/3] Checking ChatGPT...")
        page1 = browser.new_page()
        try:
            page1.goto("https://chatgpt.com/", wait_until='networkidle', timeout=30000)
            time.sleep(3)

            # Take screenshot
            screenshot1 = WORKSPACE / "chatgpt_status.png"
            page1.screenshot(path=str(screenshot1))

            # Check if logged in by looking for user indicators
            page_content = page1.content().lower()
            if 'login' in page_content or 'sign in' in page_content:
                results['ChatGPT'] = 'Not logged in'
                print("   Status: NOT logged in")
            else:
                results['ChatGPT'] = 'Logged in'
                print("   Status: Logged in")

            print(f"   Screenshot: {screenshot1}")

        except Exception as e:
            results['ChatGPT'] = f'Error: {str(e)}'
            print(f"   Error: {e}")

        # Check Claude Web
        print("\n[2/3] Checking Claude Web...")
        page2 = browser.new_page()
        try:
            page2.goto("https://claude.ai/", wait_until='networkidle', timeout=30000)
            time.sleep(3)

            screenshot2 = WORKSPACE / "claude_web_status.png"
            page2.screenshot(path=str(screenshot2))

            page_content = page2.content().lower()
            if 'login' in page_content or 'sign in' in page_content:
                results['Claude Web'] = 'Not logged in'
                print("   Status: NOT logged in")
            else:
                results['Claude Web'] = 'Logged in'
                print("   Status: Logged in")

            print(f"   Screenshot: {screenshot2}")

        except Exception as e:
            results['Claude Web'] = f'Error: {str(e)}'
            print(f"   Error: {e}")

        # Check Manus
        print("\n[3/3] Checking Manus...")
        page3 = browser.new_page()
        try:
            page3.goto("https://manus.im/", wait_until='networkidle', timeout=30000)
            time.sleep(5)

            screenshot3 = WORKSPACE / "manus_status.png"
            page3.screenshot(path=str(screenshot3))

            page_content = page3.content().lower()
            if 'sign in' in page_content or 'sign up' in page_content:
                results['Manus'] = 'Not logged in'
                print("   Status: NOT logged in")
            else:
                results['Manus'] = 'Logged in'
                print("   Status: Logged in")

                # Try to find Signals & Strategy
                print("\n   Searching for 'Signals and Strategy' chat...")
                time.sleep(3)

                # Get all text on page
                all_text = page3.evaluate("() => document.body.innerText")

                if 'signal' in all_text.lower() and 'strategy' in all_text.lower():
                    print("   Found 'Signals and Strategy' text on page!")
                else:
                    print("   Could not find 'Signals and Strategy' yet")

                # Take full page screenshot
                screenshot3_full = WORKSPACE / "manus_full_page.png"
                page3.screenshot(path=str(screenshot3_full), full_page=True)
                print(f"   Full screenshot: {screenshot3_full}")

            print(f"   Screenshot: {screenshot3}")

        except Exception as e:
            results['Manus'] = f'Error: {str(e)}'
            print(f"   Error: {e}")

        # Summary
        print("\n" + "=" * 60)
        print("Summary")
        print("=" * 60)
        for service, status in results.items():
            print(f"{service}: {status}")

        # Keep browser open for manual navigation
        print("\n" + "=" * 60)
        print("Browser staying open for 30 seconds...")
        print("You can navigate manually if needed")
        print("=" * 60)
        time.sleep(30)

        browser.close()

        return results

if __name__ == "__main__":
    try:
        results = check_all_services()
        print("\n[OK] Check complete")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
