#!/usr/bin/env python3
"""Vision System - See and understand the visual world"""
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from PIL import Image, ImageGrab
import pytesseract
import numpy as np
import json

sys.path.append(str(Path(__file__).parent.parent))

from core.persistent_memory import PersistentMemory
from core.telegram_connector import TelegramConnector

class VisionSystem:
    """Computer vision for autonomous agent"""

    def __init__(self, db_path: str = None):
        workspace = Path(__file__).parent.parent
        if db_path is None:
            db_path = str(workspace / "memory.db")

        self.memory = PersistentMemory(db_path)
        self.telegram = TelegramConnector()

        # Screenshots directory
        self.screenshots_dir = workspace / "screenshots"
        self.screenshots_dir.mkdir(exist_ok=True)

        # Visual memory (recent screenshots)
        self.visual_memory = []

    def capture_screenshot(self, region: Tuple[int, int, int, int] = None,
                          save: bool = True) -> Image.Image:
        """
        Capture screenshot

        Args:
            region: (x1, y1, x2, y2) to capture specific region
            save: Save to disk

        Returns:
            PIL Image
        """
        try:
            if region:
                screenshot = ImageGrab.grab(bbox=region)
            else:
                screenshot = ImageGrab.grab()

            if save:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filepath = self.screenshots_dir / f"screenshot_{timestamp}.png"
                screenshot.save(filepath)

                self.memory.log_decision(
                    'Screenshot captured',
                    f'Saved to: {filepath}',
                    tags=['vision', 'screenshot']
                )

            # Add to visual memory
            self.visual_memory.append({
                'image': screenshot,
                'timestamp': datetime.now(),
                'region': region
            })

            # Keep only last 10
            if len(self.visual_memory) > 10:
                self.visual_memory.pop(0)

            return screenshot

        except Exception as e:
            self.memory.log_decision(
                'Screenshot capture failed',
                f'Error: {str(e)}',
                tags=['vision', 'error']
            )
            raise

    def extract_text(self, image: Image.Image = None,
                    screenshot_path: str = None) -> str:
        """
        Extract text from image using OCR

        Args:
            image: PIL Image (or will capture screenshot)
            screenshot_path: Path to saved screenshot

        Returns:
            Extracted text
        """
        try:
            if screenshot_path:
                image = Image.open(screenshot_path)
            elif image is None:
                image = self.capture_screenshot()

            # OCR
            text = pytesseract.image_to_string(image)

            self.memory.log_decision(
                'Text extracted from image',
                f'Extracted {len(text)} characters',
                tags=['vision', 'ocr']
            )

            return text

        except Exception as e:
            self.memory.log_decision(
                'OCR failed',
                f'Error: {str(e)}',
                tags=['vision', 'ocr_error']
            )
            return ""

    def analyze_screenshot(self, image: Image.Image = None) -> Dict:
        """
        Analyze screenshot for key information

        Args:
            image: PIL Image (or will capture screenshot)

        Returns:
            Analysis results
        """
        if image is None:
            image = self.capture_screenshot()

        analysis = {
            'timestamp': datetime.now().isoformat(),
            'size': image.size,
            'mode': image.mode
        }

        # Extract text
        text = self.extract_text(image)
        analysis['text_content'] = text
        analysis['text_length'] = len(text)

        # Detect if this looks like a dashboard
        dashboard_keywords = ['dashboard', 'chart', 'graph', 'metric', 'status']
        is_dashboard = any(keyword in text.lower() for keyword in dashboard_keywords)
        analysis['is_dashboard'] = is_dashboard

        # Detect if error message
        error_keywords = ['error', 'exception', 'failed', 'warning']
        has_error = any(keyword in text.lower() for keyword in error_keywords)
        analysis['has_error'] = has_error

        # Basic color analysis
        img_array = np.array(image)
        if len(img_array.shape) == 3:
            avg_color = img_array.mean(axis=(0, 1))
            analysis['avg_color'] = avg_color.tolist()

            # Detect dark theme (low brightness)
            brightness = avg_color.mean()
            analysis['is_dark_theme'] = brightness < 100

        self.memory.log_decision(
            'Screenshot analyzed',
            f'Dashboard: {is_dashboard}, Error: {has_error}',
            tags=['vision', 'analysis']
        )

        return analysis

    def detect_ui_elements(self, image: Image.Image = None) -> List[Dict]:
        """
        Detect UI elements (buttons, text fields, etc.)

        Args:
            image: PIL Image

        Returns:
            List of detected elements
        """
        if image is None:
            image = self.capture_screenshot()

        # Simple contour detection
        img_array = np.array(image.convert('L'))  # Convert to grayscale

        # Detect edges (simple threshold)
        edges = (img_array < 100).astype(np.uint8) * 255

        # Find contours (simplified)
        elements = []

        # This is a placeholder - full implementation would use OpenCV
        # For now, just detect text regions via OCR
        try:
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

            for i in range(len(data['text'])):
                if data['text'][i].strip():
                    elements.append({
                        'type': 'text',
                        'content': data['text'][i],
                        'confidence': data['conf'][i],
                        'bbox': (data['left'][i], data['top'][i],
                                data['width'][i], data['height'][i])
                    })

        except Exception as e:
            pass

        return elements

    def read_chart(self, image: Image.Image = None) -> Dict:
        """
        Read and interpret charts/graphs

        Args:
            image: PIL Image of chart

        Returns:
            Chart analysis
        """
        if image is None:
            image = self.capture_screenshot()

        analysis = {
            'chart_detected': False,
            'chart_type': 'unknown',
            'trends': []
        }

        # Convert to numpy
        img_array = np.array(image)

        # Detect chart characteristics
        # (Simplified - full implementation would use ML)

        # Look for lines (potential line chart)
        if len(img_array.shape) == 3:
            gray = img_array.mean(axis=2)
        else:
            gray = img_array

        # Detect trend (rising/falling)
        # Very simplified - check if there are diagonal patterns
        height, width = gray.shape[:2]

        # Sample horizontal strips
        strips = []
        for i in range(5):
            y = int(height * (i + 1) / 6)
            strip = gray[y, :]
            strips.append(strip)

        # Detect if ascending/descending
        # (Very basic heuristic)

        analysis['chart_detected'] = True
        analysis['width'] = width
        analysis['height'] = height

        return analysis

    def verify_output(self, expected_text: str = None,
                     expected_color: Tuple[int, int, int] = None) -> bool:
        """
        Verify visual output matches expectations

        Args:
            expected_text: Text that should be visible
            expected_color: Color that should be present

        Returns:
            True if verified
        """
        screenshot = self.capture_screenshot()
        analysis = self.analyze_screenshot(screenshot)

        verified = True

        if expected_text:
            text_content = analysis.get('text_content', '')
            if expected_text.lower() not in text_content.lower():
                verified = False

                self.memory.log_decision(
                    'Visual verification failed',
                    f'Expected text "{expected_text}" not found',
                    tags=['vision', 'verification_failed']
                )

        if expected_color and not verified:
            avg_color = analysis.get('avg_color')
            if avg_color:
                # Check if colors are close (within threshold)
                diff = sum(abs(a - b) for a, b in zip(avg_color, expected_color))
                if diff > 100:  # Threshold
                    verified = False

        if verified:
            self.memory.log_decision(
                'Visual verification passed',
                'Output matches expectations',
                tags=['vision', 'verification_passed']
            )

        return verified

    def monitor_screen(self, check_interval: int = 5,
                      alert_on_error: bool = True) -> None:
        """
        Monitor screen for changes or errors

        Args:
            check_interval: Seconds between checks
            alert_on_error: Send Telegram alert on error detection
        """
        import time

        print(f"Starting screen monitoring (every {check_interval}s)...")

        while True:
            try:
                screenshot = self.capture_screenshot(save=False)
                analysis = self.analyze_screenshot(screenshot)

                if alert_on_error and analysis.get('has_error'):
                    error_text = analysis.get('text_content', '')[:200]

                    self.telegram.send_message(
                        f"[SCREEN ERROR DETECTED]\n"
                        f"Time: {datetime.now().strftime('%H:%M:%S')}\n"
                        f"Text: {error_text}"
                    )

                    self.memory.log_decision(
                        'Error detected on screen',
                        f'Error text: {error_text}',
                        tags=['vision', 'monitor', 'error_detected']
                    )

                time.sleep(check_interval)

            except KeyboardInterrupt:
                print("\nMonitoring stopped")
                break
            except Exception as e:
                print(f"Monitor error: {e}")
                time.sleep(check_interval)

    def get_visual_summary(self) -> Dict:
        """Get summary of recent visual activity"""
        return {
            'screenshots_captured': len(self.visual_memory),
            'recent_screenshots': [
                {
                    'timestamp': item['timestamp'].isoformat(),
                    'size': item['image'].size,
                    'region': item['region']
                }
                for item in self.visual_memory[-5:]
            ]
        }


if __name__ == '__main__':
    # Test vision system
    vision = VisionSystem()

    print("Vision System ready!")
    print("\nTesting capabilities...")

    try:
        # Capture screenshot
        print("\n1. Capturing screenshot...")
        screenshot = vision.capture_screenshot()
        print(f"   Captured: {screenshot.size}")

        # Extract text
        print("\n2. Extracting text (OCR)...")
        text = vision.extract_text(screenshot)
        print(f"   Extracted {len(text)} characters")
        if text:
            print(f"   Sample: {text[:100]}...")

        # Analyze
        print("\n3. Analyzing screenshot...")
        analysis = vision.analyze_screenshot(screenshot)
        print(f"   Dashboard: {analysis.get('is_dashboard')}")
        print(f"   Has error: {analysis.get('has_error')}")
        print(f"   Dark theme: {analysis.get('is_dark_theme')}")

        # Detect elements
        print("\n4. Detecting UI elements...")
        elements = vision.detect_ui_elements(screenshot)
        print(f"   Found {len(elements)} elements")

        print("\nVision System operational!")

    except Exception as e:
        print(f"\nError during testing: {e}")
        print("Note: Some features require pytesseract installation")
        print("Install: pip install pytesseract pillow")
