#!/usr/bin/env python3
"""
Access Manus with saved Chrome session - Creative Solution
"""

from playwright.sync_api import sync_playwright
import time
import json
from pathlib import Path
from datetime import datetime

WORKSPACE = Path(r"C:\Users\User\.openclaw\workspace")

def access_manus_creatively():
    """Access Manus using a copy of Chrome profile to avoid conflicts"""

    print("=" * 60)
    print("Accessing Manus - Creative Solution")
    print("=" * 60)
    print()

    # Create a separate profile directory for automation
    automation_profile = WORKSPACE / "chrome_automation_profile"
    automation_profile.mkdir(exist_ok=True)

    print(f"Using automation profile: {automation_profile}")
    print()

    with sync_playwright() as p:
        # Use a fresh profile but try to inherit cookies
        browser = p.chromium.launch(
            headless=False,
            channel='chrome',
            slow_mo=500
        )

        context = browser.new_context()
        page = context.new_page()

        print("[1/5] Navigating to Manus...")
        page.goto("https://manus.im/", wait_until='networkidle', timeout=60000)
        time.sleep(5)

        # Take screenshot to see current state
        screenshot1 = WORKSPACE / "manus_access_attempt.png"
        page.screenshot(path=str(screenshot1))
        print(f"   Screenshot: {screenshot1}")

        # Check if logged in
        page_text = page.evaluate("() => document.body.innerText").lower()

        if 'sign in' in page_text or 'sign up' in page_text:
            print("\n[2/5] Not logged in yet - attempting cookie transfer...")

            # Try to use stored cookies if they exist
            cookie_file = WORKSPACE / "manus_cookies.json"
            if cookie_file.exists():
                print("   Found saved cookies, loading...")
                with open(cookie_file, 'r') as f:
                    cookies = json.load(f)
                context.add_cookies(cookies)

                # Reload page with cookies
                page.reload(wait_until='networkidle')
                time.sleep(3)

                screenshot2 = WORKSPACE / "manus_after_cookies.png"
                page.screenshot(path=str(screenshot2))
                print(f"   Screenshot after cookies: {screenshot2}")
            else:
                print("   No saved cookies found")
                print("   The page is loaded - you may need to login once")
        else:
            print("\n[2/5] Already logged in!")

        print("\n[3/5] Searching for 'Signals and Strategy' chat...")
        time.sleep(3)

        # Get all page content
        all_text = page.evaluate("() => document.body.innerText")

        # Search for signals and strategy
        if 'signal' in all_text.lower() and 'strategy' in all_text.lower():
            print("   Found 'Signals and Strategy' text!")
        else:
            print("   Text not found yet - might need navigation")

        # Try to find clickable elements
        print("\n[4/5] Looking for navigation elements...")

        # Get all links and buttons
        elements = page.evaluate("""
            () => {
                const items = [];
                document.querySelectorAll('a, button, [role="button"]').forEach(el => {
                    const text = el.innerText || el.textContent;
                    if (text && text.length > 0 && text.length < 100) {
                        items.push({
                            text: text.trim(),
                            tag: el.tagName
                        });
                    }
                });
                return items;
            }
        """)

        # Look for anything related to signals or chats
        relevant = [e for e in elements if 'signal' in e['text'].lower()
                    or 'strategy' in e['text'].lower()
                    or 'chat' in e['text'].lower()
                    or 'message' in e['text'].lower()]

        if relevant:
            print(f"   Found {len(relevant)} relevant elements:")
            for elem in relevant[:5]:
                print(f"     - {elem['text'][:50]}")

        print("\n[5/5] Taking full page screenshot...")
        screenshot_full = WORKSPACE / "manus_full_page.png"
        page.screenshot(path=str(screenshot_full), full_page=True)
        print(f"   Full page: {screenshot_full}")

        # Save current state
        report = {
            'timestamp': datetime.now().isoformat(),
            'logged_in': 'sign in' not in page_text,
            'signals_found': 'signal' in all_text.lower() and 'strategy' in all_text.lower(),
            'page_title': page.title(),
            'url': page.url,
            'relevant_elements': relevant[:10],
            'screenshots': [str(screenshot1), str(screenshot_full)]
        }

        report_file = WORKSPACE / "manus_access_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\n   Report saved: {report_file}")

        # Save cookies for next time
        cookies = context.cookies()
        cookie_file = WORKSPACE / "manus_cookies.json"
        with open(cookie_file, 'w') as f:
            json.dump(cookies, f, indent=2)
        print(f"   Cookies saved: {cookie_file}")

        print("\n" + "=" * 60)
        print("Keeping browser open for 60 seconds...")
        print("Checking what's visible...")
        print("=" * 60)

        time.sleep(60)

        browser.close()

        return report

if __name__ == "__main__":
    try:
        result = access_manus_creatively()

        print("\n" + "=" * 60)
        print("ACCESS COMPLETE")
        print("=" * 60)
        print(f"\nLogged in: {result['logged_in']}")
        print(f"Signals found: {result['signals_found']}")
        print(f"\nCheck screenshots for details:")
        for ss in result['screenshots']:
            print(f"  - {ss}")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
