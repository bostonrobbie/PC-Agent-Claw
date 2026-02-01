#!/usr/bin/env python3
"""
Check Manus Signals & Strategy chat for website hosting status
"""

from playwright.sync_api import sync_playwright
import time
import json
from pathlib import Path
from datetime import datetime

WORKSPACE = Path(r"C:\Users\User\.openclaw\workspace")

def check_manus_websites():
    """Navigate to Manus and check Signals & Strategy chat"""

    print("=" * 60)
    print("Manus Website Status Checker")
    print("=" * 60)
    print()

    with sync_playwright() as p:
        # Launch browser
        print("[1/5] Launching browser...")
        browser = p.chromium.launch(
            headless=False,
            channel='chrome',
            slow_mo=1000  # Slow down by 1 second to see what's happening
        )
        context = browser.new_context()
        page = context.new_page()

        # Navigate to Manus
        print("[2/5] Navigating to Manus...")
        page.goto("https://manus.im/", wait_until='networkidle')
        time.sleep(3)

        print("[3/5] Waiting for login check...")
        # Check if we're logged in by looking for navigation elements
        try:
            # Look for chat/project navigation
            # Manus typically has a sidebar or navigation area
            page.wait_for_selector('a, button, [role="button"]', timeout=5000)

            print("[4/5] Searching for 'Signals and Strategy' chat...")

            # Get page content for analysis
            content = page.content()

            # Try to find Signals and Strategy chat
            # Common patterns: links, buttons, or text containing "signals" and "strategy"

            # Method 1: Search all links
            links = page.query_selector_all('a')
            found_signals = False

            for link in links:
                text = link.inner_text().lower() if link.inner_text() else ""
                if 'signal' in text and 'strategy' in text:
                    print(f"   Found link: {link.inner_text()}")
                    link.click()
                    found_signals = True
                    break

            if not found_signals:
                # Method 2: Search all text elements
                elements = page.query_selector_all('div, span, p, h1, h2, h3, h4')
                for elem in elements:
                    text = elem.inner_text().lower() if elem.inner_text() else ""
                    if 'signal' in text and 'strategy' in text:
                        print(f"   Found element: {elem.inner_text()}")
                        elem.click()
                        found_signals = True
                        break

            if found_signals:
                print("[5/5] Loading Signals and Strategy chat...")
                time.sleep(3)

                # Extract chat messages/content
                print("\nExtracting chat content...")

                # Get all visible text
                chat_content = page.evaluate("""
                    () => {
                        const elements = document.querySelectorAll('*');
                        const messages = [];
                        for (const elem of elements) {
                            const text = elem.innerText;
                            if (text && text.length > 10 && text.length < 1000) {
                                messages.push(text);
                            }
                        }
                        return messages;
                    }
                """)

                # Filter for website-related content
                website_info = []
                for msg in chat_content:
                    msg_lower = msg.lower()
                    if any(keyword in msg_lower for keyword in ['website', 'hosting', 'domain', 'url', 'deploy', 'live', 'http', 'www', '.com']):
                        website_info.append(msg)

                # Take screenshot for manual review
                screenshot_path = WORKSPACE / "manus_signals_strategy_screenshot.png"
                page.screenshot(path=str(screenshot_path))
                print(f"\nScreenshot saved: {screenshot_path}")

                # Save extracted data
                report_data = {
                    'timestamp': datetime.now().isoformat(),
                    'chat_found': True,
                    'website_mentions': website_info[:20],  # First 20 mentions
                    'all_content_sample': chat_content[:50],  # First 50 messages
                    'screenshot': str(screenshot_path)
                }

            else:
                print("\n[!] Could not find 'Signals and Strategy' chat automatically")
                print("    Taking screenshot of current page for manual review...")

                screenshot_path = WORKSPACE / "manus_main_page_screenshot.png"
                page.screenshot(path=str(screenshot_path))
                print(f"    Screenshot saved: {screenshot_path}")

                # Get all visible text for analysis
                all_text = page.evaluate("() => document.body.innerText")

                report_data = {
                    'timestamp': datetime.now().isoformat(),
                    'chat_found': False,
                    'error': 'Could not locate Signals and Strategy chat',
                    'page_text_sample': all_text[:2000],  # First 2000 chars
                    'screenshot': str(screenshot_path),
                    'instructions': 'Please manually navigate to the Signals and Strategy chat'
                }

        except Exception as e:
            print(f"\n[ERROR] {e}")

            screenshot_path = WORKSPACE / "manus_error_screenshot.png"
            page.screenshot(path=str(screenshot_path))

            report_data = {
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'screenshot': str(screenshot_path)
            }

        # Save report
        report_file = WORKSPACE / "manus_website_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2)

        print(f"\nReport saved: {report_file}")

        # Auto-close after delay
        print("\n" + "=" * 60)
        print("Waiting 10 seconds for page to fully load...")
        print("=" * 60)

        time.sleep(10)

        # Take final screenshot
        final_screenshot = WORKSPACE / "manus_final_screenshot.png"
        page.screenshot(path=str(final_screenshot), full_page=True)
        print(f"Full page screenshot: {final_screenshot}")

        report_data['final_screenshot'] = str(final_screenshot)

        browser.close()

        return report_data

if __name__ == "__main__":
    try:
        report = check_manus_websites()
        print("\n[OK] Check complete")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
