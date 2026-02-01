---
name: python-tools
description: Execute Python automation tools (browser, screenshots, system monitoring, file watching)
---

# Python Tools Skill

Provides access to installed Python automation tools for advanced tasks.

## Available Tools

### 1. Browser Automation (Playwright)
```bash
python -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto('https://example.com')
    print(page.title())
    browser.close()
"
```

### 2. Screenshots (mss)
```bash
python -c "
import mss
with mss.mss() as sct:
    sct.shot(output='screenshot.png')
    print('Screenshot saved to screenshot.png')
"
```

### 3. System Monitoring (psutil)
```bash
python -c "
import psutil
print(f'CPU: {psutil.cpu_percent()}%')
print(f'RAM: {psutil.virtual_memory().percent}%')
print(f'Disk: {psutil.disk_usage(\"/\").percent}%')
"
```

### 4. GUI Automation (pyautogui)
```bash
python -c "
import pyautogui
print(f'Screen size: {pyautogui.size()}')
print(f'Mouse position: {pyautogui.position()}')
"
```

### 5. HTTP Requests (httpx)
```bash
python -c "
import httpx
r = httpx.get('https://httpbin.org/get')
print(r.json())
"
```

### 6. File Watcher (watchdog)
```python
# watch_files.py
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time

class Handler(FileSystemEventHandler):
    def on_modified(self, event):
        print(f'Modified: {event.src_path}')

observer = Observer()
observer.schedule(Handler(), path='.', recursive=True)
observer.start()
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    observer.stop()
observer.join()
```

## Usage via Telegram

You can ask OpenClaw to run any of these commands via Telegram messages:
- "Take a screenshot"
- "Check system status"
- "Monitor CPU usage"
- "Scrape this website: [url]"

## Notes
- All tools installed in: `C:\Users\User\AppData\Roaming\Python\Python314\site-packages`
- Playwright browsers in: `C:\Users\User\AppData\Local\ms-playwright`
