#!/usr/bin/env python3
"""
Security Monitor & Defense System
Comprehensive security monitoring and threat detection
"""
import sys
from pathlib import Path
import json
import sqlite3
import hashlib
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import threading
import time

sys.path.append(str(Path(__file__).parent.parent))


class SecurityMonitor:
    """
    Security monitoring and defense

    Features:
    - Input validation and sanitization
    - Command injection prevention
    - SQL injection detection
    - XSS prevention
    - Path traversal prevention
    - Rate limiting
    - Anomaly detection
    - Audit logging
    - Threat detection and blocking
    """

    def __init__(self, db_path: str = None):
        workspace = Path(__file__).parent.parent
        if db_path is None:
            db_path = str(workspace / "memory.db")

        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

        # Security patterns
        self.patterns = self._load_threat_patterns()

        # Rate limiting
        self.rate_limits = {}
        self.blocked_ips = set()

        # Monitoring
        self.monitoring = False
        self.monitor_thread = None

        # Load Telegram notifier for critical alerts
        try:
            from telegram_notifier import TelegramNotifier
            self.notifier = TelegramNotifier()
        except Exception as e:
            print(f"[WARNING] Could not load Telegram notifier: {e}")
            self.notifier = None

    def _init_db(self):
        """Initialize database schema"""
        cursor = self.conn.cursor()

        # Security events
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS security_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                source TEXT,
                details TEXT,
                action_taken TEXT,
                blocked INTEGER DEFAULT 0,
                occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Blocked entities
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS blocked_entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type TEXT NOT NULL,
                entity_value TEXT NOT NULL,
                reason TEXT,
                blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
        ''')

        # Audit log
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                user_id TEXT,
                resource TEXT,
                result TEXT,
                details TEXT,
                logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # File integrity
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS file_integrity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL UNIQUE,
                file_hash TEXT NOT NULL,
                last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                integrity_status TEXT DEFAULT 'valid'
            )
        ''')

        self.conn.commit()

    def _load_threat_patterns(self) -> Dict:
        """Load threat detection patterns"""
        return {
            'sql_injection': [
                r"(\bUNION\b.*\bSELECT\b)",
                r"(\bOR\b\s+\d+\s*=\s*\d+)",
                r"(;.*DROP\s+TABLE)",
                r"(--\s*$)",
                r"(/\*.*\*/)"
            ],
            'command_injection': [
                r"(;\s*\w+)",
                r"(\|{1,2}\s*\w+)",
                r"(&{1,2}\s*\w+)",
                r"(`.*`)",
                r"(\$\(.*\))"
            ],
            'path_traversal': [
                r"(\.\.[\\/])",
                r"([\\/]\.\.)",
                r"(%2e%2e)",
                r"(\.\.%2f)",
                r"(%252e%252e)"
            ],
            'xss': [
                r"(<script.*?>)",
                r"(javascript:)",
                r"(on\w+\s*=)",
                r"(<iframe.*?>)",
                r"(eval\s*\()"
            ]
        }

    # === INPUT VALIDATION ===

    def validate_input(self, input_data: str, input_type: str = 'general') -> Tuple[bool, Optional[str]]:
        """
        Validate input for security threats

        Args:
            input_data: Data to validate
            input_type: Type of input ('general', 'sql', 'file_path', etc.)

        Returns:
            (is_safe, threat_detected)
        """
        if not input_data:
            return True, None

        # Check for SQL injection
        for pattern in self.patterns['sql_injection']:
            if re.search(pattern, input_data, re.IGNORECASE):
                self._log_event('sql_injection_attempt', 'high', input_data[:200], 'blocked')
                return False, 'sql_injection'

        # Check for command injection
        for pattern in self.patterns['command_injection']:
            if re.search(pattern, input_data):
                self._log_event('command_injection_attempt', 'critical', input_data[:200], 'blocked')
                return False, 'command_injection'

        # Check for path traversal
        if input_type == 'file_path':
            for pattern in self.patterns['path_traversal']:
                if re.search(pattern, input_data):
                    self._log_event('path_traversal_attempt', 'high', input_data[:200], 'blocked')
                    return False, 'path_traversal'

        # Check for XSS
        for pattern in self.patterns['xss']:
            if re.search(pattern, input_data, re.IGNORECASE):
                self._log_event('xss_attempt', 'medium', input_data[:200], 'blocked')
                return False, 'xss'

        return True, None

    def sanitize_input(self, input_data: str) -> str:
        """
        Sanitize input by removing dangerous characters

        Args:
            input_data: Data to sanitize

        Returns:
            Sanitized data
        """
        if not input_data:
            return ""

        # Remove dangerous characters
        sanitized = input_data

        # Remove SQL comments
        sanitized = re.sub(r'--.*$', '', sanitized)
        sanitized = re.sub(r'/\*.*?\*/', '', sanitized, flags=re.DOTALL)

        # Remove command injection chars
        sanitized = re.sub(r'[;&|`$]', '', sanitized)

        # Remove script tags
        sanitized = re.sub(r'<script.*?</script>', '', sanitized, flags=re.IGNORECASE | re.DOTALL)

        # Encode special HTML chars
        sanitized = sanitized.replace('<', '&lt;').replace('>', '&gt;')

        return sanitized

    # === RATE LIMITING ===

    def check_rate_limit(self, source_id: str, max_requests: int = 100,
                        window_seconds: int = 60) -> bool:
        """
        Check if source exceeds rate limit

        Args:
            source_id: Identifier for source
            max_requests: Maximum requests allowed
            window_seconds: Time window

        Returns:
            True if within limit, False if exceeded
        """
        now = datetime.now()

        # Clean old entries
        if source_id in self.rate_limits:
            self.rate_limits[source_id] = [
                ts for ts in self.rate_limits[source_id]
                if (now - ts).total_seconds() < window_seconds
            ]
        else:
            self.rate_limits[source_id] = []

        # Check limit
        if len(self.rate_limits[source_id]) >= max_requests:
            self._log_event('rate_limit_exceeded', 'medium', source_id, 'throttled')

            # Alert if critical
            if self.notifier and len(self.rate_limits[source_id]) > max_requests * 2:
                try:
                    self.notifier.send_message(
                        f"[SECURITY] Rate limit exceeded by {source_id}\n"
                        f"Requests: {len(self.rate_limits[source_id])} in {window_seconds}s",
                        priority="warning"
                    )
                except:
                    pass

            return False

        # Add timestamp
        self.rate_limits[source_id].append(now)
        return True

    # === FILE INTEGRITY ===

    def check_file_integrity(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """
        Check if file has been tampered with

        Args:
            file_path: Path to file

        Returns:
            (is_valid, stored_hash)
        """
        file_path_obj = Path(file_path)

        if not file_path_obj.exists():
            return False, None

        # Calculate current hash
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hasher.update(chunk)
        current_hash = hasher.hexdigest()

        # Check against stored hash
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT file_hash FROM file_integrity WHERE file_path = ?
        ''', (file_path,))

        result = cursor.fetchone()

        if not result:
            # First time - store hash
            cursor.execute('''
                INSERT INTO file_integrity (file_path, file_hash)
                VALUES (?, ?)
            ''', (file_path, current_hash))
            self.conn.commit()
            return True, current_hash

        stored_hash = result['file_hash']

        if current_hash != stored_hash:
            # File modified!
            self._log_event('file_tampering_detected', 'critical',
                          file_path, 'alert_sent')

            cursor.execute('''
                UPDATE file_integrity
                SET integrity_status = 'compromised', last_checked = CURRENT_TIMESTAMP
                WHERE file_path = ?
            ''', (file_path,))
            self.conn.commit()

            # Critical alert
            if self.notifier:
                try:
                    self.notifier.send_message(
                        f"[SECURITY CRITICAL] File tampering detected!\n"
                        f"File: {file_path}\n"
                        f"Expected: {stored_hash[:16]}...\n"
                        f"Found: {current_hash[:16]}...",
                        priority="critical"
                    )
                except:
                    pass

            return False, stored_hash

        # Valid
        cursor.execute('''
            UPDATE file_integrity
            SET last_checked = CURRENT_TIMESTAMP
            WHERE file_path = ?
        ''', (file_path,))
        self.conn.commit()

        return True, stored_hash

    def register_critical_files(self, file_paths: List[str]):
        """Register critical files for integrity monitoring"""
        for file_path in file_paths:
            self.check_file_integrity(file_path)

    # === AUDIT LOGGING ===

    def audit_log(self, action: str, user_id: str = None, resource: str = None,
                 result: str = 'success', details: Dict = None):
        """
        Log action for audit trail

        Args:
            action: Action performed
            user_id: User identifier
            resource: Resource accessed
            result: Result of action
            details: Additional details
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO audit_log (action, user_id, resource, result, details)
            VALUES (?, ?, ?, ?, ?)
        ''', (action, user_id, resource, result, json.dumps(details) if details else None))
        self.conn.commit()

    # === THREAT DETECTION ===

    def detect_anomaly(self, behavior: str, value: float, baseline_mean: float,
                      baseline_std: float) -> Tuple[bool, float]:
        """
        Detect anomalous behavior

        Args:
            behavior: Behavior being monitored
            value: Current value
            baseline_mean: Expected mean
            baseline_std: Expected standard deviation

        Returns:
            (is_anomalous, z_score)
        """
        if baseline_std == 0:
            return False, 0

        z_score = abs((value - baseline_mean) / baseline_std)

        if z_score > 3.0:  # 3 sigma
            self._log_event('anomaly_detected', 'medium',
                          f"{behavior}: {value} (z={z_score:.2f})",
                          'investigating')
            return True, z_score

        return False, z_score

    # === BLOCKING ===

    def block_entity(self, entity_type: str, entity_value: str, reason: str,
                    duration_hours: float = 24):
        """
        Block entity (IP, user, etc.)

        Args:
            entity_type: Type ('ip', 'user', etc.)
            entity_value: Value to block
            reason: Reason for blocking
            duration_hours: Block duration
        """
        cursor = self.conn.cursor()

        expires_at = datetime.now() + timedelta(hours=duration_hours)

        cursor.execute('''
            INSERT INTO blocked_entities
            (entity_type, entity_value, reason, expires_at)
            VALUES (?, ?, ?, ?)
        ''', (entity_type, entity_value, reason, expires_at))

        self.conn.commit()

        # Add to in-memory set
        if entity_type == 'ip':
            self.blocked_ips.add(entity_value)

        self._log_event('entity_blocked', 'high',
                      f"{entity_type}: {entity_value}", f"blocked for {duration_hours}h")

    def is_blocked(self, entity_type: str, entity_value: str) -> bool:
        """Check if entity is blocked"""
        # Check in-memory first
        if entity_type == 'ip' and entity_value in self.blocked_ips:
            return True

        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id FROM blocked_entities
            WHERE entity_type = ? AND entity_value = ?
            AND is_active = 1
            AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
        ''', (entity_type, entity_value))

        return cursor.fetchone() is not None

    # === EVENT LOGGING ===

    def _log_event(self, event_type: str, severity: str, details: str, action: str):
        """Log security event"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO security_events
            (event_type, severity, details, action_taken, blocked)
            VALUES (?, ?, ?, ?, ?)
        ''', (event_type, severity, details[:500], action, 1 if 'block' in action.lower() else 0))
        self.conn.commit()

    # === MONITORING ===

    def start_monitoring(self, interval_seconds: int = 300):
        """Start security monitoring"""
        if self.monitoring:
            return

        self.monitoring = True

        def monitor_loop():
            while self.monitoring:
                # Check critical files
                critical_files = [
                    'security/security_monitor.py',
                    'core/persistent_memory.py',
                    'agentic_core.py'
                ]

                for file_path in critical_files:
                    full_path = Path(__file__).parent.parent / file_path
                    if full_path.exists():
                        self.check_file_integrity(str(full_path))

                # Clean expired blocks
                self._clean_expired_blocks()

                time.sleep(interval_seconds)

        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()

        print("[SECURITY] Monitoring started")

    def stop_monitoring(self):
        """Stop security monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)

    def _clean_expired_blocks(self):
        """Clean expired blocks"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE blocked_entities
            SET is_active = 0
            WHERE expires_at IS NOT NULL AND expires_at < CURRENT_TIMESTAMP
        ''')
        self.conn.commit()

    # === REPORTING ===

    def get_security_summary(self, hours: int = 24) -> Dict:
        """Get security summary"""
        cursor = self.conn.cursor()

        # Event counts by type
        cursor.execute('''
            SELECT event_type, COUNT(*) as count, severity
            FROM security_events
            WHERE occurred_at >= datetime('now', ? || ' hours')
            GROUP BY event_type, severity
        ''', (f'-{hours}',))

        events = {}
        for row in cursor.fetchall():
            events[row['event_type']] = {
                'count': row['count'],
                'severity': row['severity']
            }

        # Blocked count
        cursor.execute('''
            SELECT COUNT(*) as count FROM security_events
            WHERE blocked = 1
            AND occurred_at >= datetime('now', ? || ' hours')
        ''', (f'-{hours}',))

        blocked_count = cursor.fetchone()['count']

        # Active blocks
        cursor.execute('''
            SELECT COUNT(*) as count FROM blocked_entities WHERE is_active = 1
        ''')

        active_blocks = cursor.fetchone()['count']

        return {
            'events': events,
            'blocked_attempts': blocked_count,
            'active_blocks': active_blocks,
            'period_hours': hours
        }

    def close(self):
        """Close database connection"""
        self.stop_monitoring()
        self.conn.close()


# === TEST CODE ===

def main():
    """Test security monitor"""
    print("Testing Security Monitor")
    print("=" * 70)

    monitor = SecurityMonitor()

    try:
        # Test input validation
        print("\n1. Testing input validation...")
        safe, threat = monitor.validate_input("SELECT * FROM users")
        print(f"   Normal query: safe={safe}")

        safe, threat = monitor.validate_input("SELECT * FROM users UNION SELECT * FROM passwords")
        print(f"   SQL injection: safe={safe}, threat={threat}")

        safe, threat = monitor.validate_input("../../etc/passwd", 'file_path')
        print(f"   Path traversal: safe={safe}, threat={threat}")

        # Test sanitization
        print("\n2. Testing input sanitization...")
        dirty = "<script>alert('XSS')</script>Hello"
        clean = monitor.sanitize_input(dirty)
        print(f"   Original: {dirty[:50]}")
        print(f"   Sanitized: {clean}")

        # Test rate limiting
        print("\n3. Testing rate limiting...")
        allowed = monitor.check_rate_limit("test_user", max_requests=5, window_seconds=60)
        print(f"   First request: allowed={allowed}")

        for i in range(6):
            allowed = monitor.check_rate_limit("test_user", max_requests=5)

        print(f"   After 6 requests: allowed={allowed}")

        # Test audit logging
        print("\n4. Testing audit logging...")
        monitor.audit_log("file_access", "user_1", "/etc/passwd", "denied")
        print("   Audit log created")

        # Test blocking
        print("\n5. Testing entity blocking...")
        monitor.block_entity("ip", "192.168.1.100", "suspicious_activity", duration_hours=1)
        is_blocked = monitor.is_blocked("ip", "192.168.1.100")
        print(f"   IP blocked: {is_blocked}")

        # Get summary
        print("\n6. Security summary...")
        summary = monitor.get_security_summary(hours=24)
        print(f"   Events: {len(summary['events'])}")
        print(f"   Blocked attempts: {summary['blocked_attempts']}")
        print(f"   Active blocks: {summary['active_blocks']}")

        print(f"\n[OK] Security Monitor working!")
        print(f"Database: {monitor.db_path}")

    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        monitor.close()


if __name__ == "__main__":
    main()
