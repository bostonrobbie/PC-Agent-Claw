#!/usr/bin/env python3
"""
Manus Creative Solution - Extract cookies from Chrome to access Manus
"""

import sqlite3
import json
import shutil
import os
from pathlib import Path
from datetime import datetime

WORKSPACE = Path(r"C:\Users\User\.openclaw\workspace")

def extract_chrome_cookies_for_manus():
    """
    Creative solution: Extract Manus cookies from Chrome's cookie database
    """

    print("=" * 60)
    print("Manus Cookie Extraction - Creative Solution")
    print("=" * 60)
    print()

    chrome_user_data = Path(os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data"))
    cookie_db_path = chrome_user_data / "Default" / "Network" / "Cookies"

    if not cookie_db_path.exists():
        # Try alternative path
        cookie_db_path = chrome_user_data / "Default" / "Cookies"

    if not cookie_db_path.exists():
        print(f"[ERROR] Could not find Chrome cookies at: {cookie_db_path}")
        return None

    print(f"Found Chrome cookies: {cookie_db_path}")

    # Copy the cookie database to avoid locking issues
    temp_cookie_db = WORKSPACE / "temp_cookies.db"
    try:
        shutil.copy2(cookie_db_path, temp_cookie_db)
        print(f"Copied to temp location: {temp_cookie_db}")
    except Exception as e:
        print(f"[ERROR] Could not copy cookie database: {e}")
        print("Chrome might be running. Trying alternative approach...")

        # Alternative: Read without copying (might fail if Chrome is locked)
        temp_cookie_db = cookie_db_path

    # Extract Manus cookies
    try:
        conn = sqlite3.connect(temp_cookie_db)
        cursor = conn.cursor()

        # Query for manus.im cookies
        query = """
            SELECT name, value, host_key, path, expires_utc, is_secure, is_httponly
            FROM cookies
            WHERE host_key LIKE '%manus%' OR host_key LIKE '%meta%'
        """

        cursor.execute(query)
        cookies = cursor.fetchall()

        conn.close()

        if cookies:
            print(f"\n[OK] Found {len(cookies)} cookies for Manus/Meta")

            # Convert to Playwright cookie format
            playwright_cookies = []
            for cookie in cookies:
                name, value, domain, path, expires, secure, httponly = cookie

                playwright_cookie = {
                    'name': name,
                    'value': value,
                    'domain': domain,
                    'path': path,
                    'expires': expires / 1000000 - 11644473600 if expires else -1,  # Convert Chrome time to Unix
                    'httpOnly': bool(httponly),
                    'secure': bool(secure),
                    'sameSite': 'Lax'
                }

                playwright_cookies.append(playwright_cookie)

            # Save cookies
            cookie_file = WORKSPACE / "manus_extracted_cookies.json"
            with open(cookie_file, 'w') as f:
                json.dump(playwright_cookies, f, indent=2)

            print(f"Saved cookies to: {cookie_file}")

            # Clean up temp file
            if temp_cookie_db != cookie_db_path:
                temp_cookie_db.unlink()

            return playwright_cookies

        else:
            print("\n[INFO] No Manus cookies found")
            print("This means you're not logged into Manus in Chrome yet")
            print("Please login to https://manus.im/ in Chrome first")
            conn.close()
            return None

    except Exception as e:
        print(f"\n[ERROR] Could not read cookies: {e}")
        return None

def access_manus_with_extracted_cookies():
    """Access Manus using extracted cookies"""

    from playwright.sync_api import sync_playwright
    import time

    cookies = extract_chrome_cookies_for_manus()

    if not cookies:
        print("\n[INFO] Could not extract cookies")
        print("Make sure you're logged into Manus in Chrome")
        return

    print("\n" + "=" * 60)
    print("Accessing Manus with Extracted Cookies")
    print("=" * 60)
    print()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, channel='chrome')
        context = browser.new_context()

        # Add extracted cookies
        context.add_cookies(cookies)

        page = context.new_page()

        print("[1/4] Navigating to Manus with cookies...")
        page.goto("https://manus.im/", wait_until='networkidle')
        time.sleep(5)

        screenshot1 = WORKSPACE / "manus_with_cookies.png"
        page.screenshot(path=str(screenshot1))
        print(f"   Screenshot: {screenshot1}")

        # Check if logged in
        page_text = page.evaluate("() => document.body.innerText").lower()

        if 'sign in' not in page_text:
            print("\n[2/4] SUCCESS! Logged into Manus!")

            print("\n[3/4] Searching for Signals and Strategy...")
            time.sleep(3)

            # Get all page content
            all_text = page.evaluate("() => document.body.innerText")

            # Save page content
            content_file = WORKSPACE / "manus_page_content.txt"
            with open(content_file, 'w', encoding='utf-8') as f:
                f.write(all_text)
            print(f"   Saved page content: {content_file}")

            # Search for signals and strategy
            if 'signal' in all_text.lower() and 'strategy' in all_text.lower():
                print("   [OK] Found 'Signals and Strategy' text!")

                # Try to click on it
                try:
                    # Look for clickable element
                    elements = page.query_selector_all('a, button, [role="button"], div[class*="chat"], div[class*="conversation"]')

                    for elem in elements:
                        text = elem.inner_text() if elem.inner_text() else ""
                        if 'signal' in text.lower() and 'strategy' in text.lower():
                            print(f"   Clicking on: {text[:50]}")
                            elem.click()
                            time.sleep(5)
                            break

                except Exception as e:
                    print(f"   Could not click: {e}")

            print("\n[4/4] Taking full page screenshot...")
            screenshot_full = WORKSPACE / "manus_logged_in_full.png"
            page.screenshot(path=str(screenshot_full), full_page=True)
            print(f"   Screenshot: {screenshot_full}")

            # Keep open for inspection
            print("\n" + "=" * 60)
            print("Keeping browser open for 60 seconds...")
            print("=" * 60)
            time.sleep(60)

        else:
            print("\n[ERROR] Still not logged in")
            print("Cookies may have expired or not transferred correctly")

        browser.close()

if __name__ == "__main__":
    access_manus_with_extracted_cookies()
