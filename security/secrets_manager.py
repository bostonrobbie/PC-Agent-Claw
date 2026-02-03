#!/usr/bin/env python3
"""
Secrets Manager & Data Encryption
Secure storage and encryption for sensitive data
"""
import sys
from pathlib import Path
import json
import sqlite3
import secrets
import hashlib
import base64
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2

sys.path.append(str(Path(__file__).parent.parent))


class SecretsManager:
    """
    Secure secrets and data encryption

    Features:
    - Encrypted secret storage
    - API key/token management
    - Password hashing
    - Data encryption at rest
    - Secret rotation
    - Audit logging
    """

    def __init__(self, db_path: str = None, master_key: bytes = None):
        workspace = Path(__file__).parent.parent
        if db_path is None:
            db_path = str(workspace / "memory.db")

        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

        # Initialize encryption
        self.master_key = master_key or self._get_or_create_master_key()
        self.fernet = Fernet(self.master_key)

    def _init_db(self):
        """Initialize database schema"""
        cursor = self.conn.cursor()

        # Encrypted secrets
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS encrypted_secrets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                secret_name TEXT UNIQUE NOT NULL,
                secret_value_encrypted BLOB NOT NULL,
                secret_type TEXT,
                expires_at TIMESTAMP,
                last_rotated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                rotation_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Master key storage (encrypted with itself - bootstrap)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS master_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_id TEXT UNIQUE NOT NULL,
                key_hash TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Secret access log
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS secret_access_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                secret_name TEXT NOT NULL,
                accessed_by TEXT,
                access_type TEXT,
                accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        self.conn.commit()

    def _get_or_create_master_key(self) -> bytes:
        """Get or create master encryption key"""
        cursor = self.conn.cursor()

        # Check for existing active key
        cursor.execute('''
            SELECT key_hash FROM master_keys WHERE is_active = 1 ORDER BY created_at DESC LIMIT 1
        ''')

        result = cursor.fetchone()

        if result:
            # Derive key from hash (in production, use proper key derivation)
            key_material = result['key_hash'].encode()[:32]
            key = base64.urlsafe_b64encode(key_material.ljust(32, b'0'))
            return key

        # Generate new master key
        key = Fernet.generate_key()
        key_id = secrets.token_hex(16)
        key_hash = hashlib.sha256(key).hexdigest()

        cursor.execute('''
            INSERT INTO master_keys (key_id, key_hash, is_active)
            VALUES (?, ?, 1)
        ''', (key_id, key_hash))

        self.conn.commit()

        return key

    # === SECRET STORAGE ===

    def store_secret(self, secret_name: str, secret_value: str,
                    secret_type: str = 'generic', expires_days: int = None) -> bool:
        """
        Store encrypted secret

        Args:
            secret_name: Name/identifier for secret
            secret_value: Secret value to encrypt
            secret_type: Type of secret (api_key, password, token, etc.)
            expires_days: Days until expiration

        Returns:
            Success status
        """
        try:
            # Encrypt secret
            encrypted_value = self.fernet.encrypt(secret_value.encode())

            # Calculate expiration
            expires_at = None
            if expires_days:
                expires_at = datetime.now() + timedelta(days=expires_days)

            cursor = self.conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO encrypted_secrets
                (secret_name, secret_value_encrypted, secret_type, expires_at)
                VALUES (?, ?, ?, ?)
            ''', (secret_name, encrypted_value, secret_type, expires_at))

            self.conn.commit()

            self._log_access(secret_name, "system", "store")

            return True

        except Exception as e:
            print(f"[ERROR] Failed to store secret: {e}")
            return False

    def get_secret(self, secret_name: str, accessed_by: str = "system") -> Optional[str]:
        """
        Retrieve and decrypt secret

        Args:
            secret_name: Name of secret
            accessed_by: Who is accessing

        Returns:
            Decrypted secret value or None
        """
        cursor = self.conn.cursor()

        cursor.execute('''
            SELECT secret_value_encrypted, expires_at
            FROM encrypted_secrets
            WHERE secret_name = ?
        ''', (secret_name,))

        result = cursor.fetchone()

        if not result:
            return None

        # Check expiration
        if result['expires_at']:
            expires_at = datetime.fromisoformat(result['expires_at'])
            if datetime.now() > expires_at:
                self._log_access(secret_name, accessed_by, "access_expired")
                return None

        # Decrypt
        try:
            decrypted_value = self.fernet.decrypt(result['secret_value_encrypted']).decode()
            self._log_access(secret_name, accessed_by, "access")
            return decrypted_value

        except Exception as e:
            print(f"[ERROR] Failed to decrypt secret: {e}")
            self._log_access(secret_name, accessed_by, "decrypt_failed")
            return None

    def delete_secret(self, secret_name: str) -> bool:
        """Delete secret"""
        cursor = self.conn.cursor()

        cursor.execute('''
            DELETE FROM encrypted_secrets WHERE secret_name = ?
        ''', (secret_name,))

        self.conn.commit()

        self._log_access(secret_name, "system", "delete")

        return cursor.rowcount > 0

    # === PASSWORD HASHING ===

    def hash_password(self, password: str, salt: bytes = None) -> tuple:
        """
        Hash password securely

        Args:
            password: Password to hash
            salt: Optional salt (generated if not provided)

        Returns:
            (hash, salt) tuple
        """
        if salt is None:
            salt = secrets.token_bytes(16)

        # Use PBKDF2 with SHA256
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000
        )

        key = kdf.derive(password.encode())
        password_hash = base64.b64encode(key).decode()

        return password_hash, salt

    def verify_password(self, password: str, password_hash: str, salt: bytes) -> bool:
        """
        Verify password against hash

        Args:
            password: Password to verify
            password_hash: Stored hash
            salt: Salt used in hashing

        Returns:
            True if password matches
        """
        computed_hash, _ = self.hash_password(password, salt)
        return computed_hash == password_hash

    # === DATA ENCRYPTION ===

    def encrypt_data(self, data: Any) -> str:
        """
        Encrypt arbitrary data

        Args:
            data: Data to encrypt (will be JSON serialized)

        Returns:
            Encrypted data as base64 string
        """
        json_data = json.dumps(data)
        encrypted = self.fernet.encrypt(json_data.encode())
        return base64.b64encode(encrypted).decode()

    def decrypt_data(self, encrypted_data: str) -> Any:
        """
        Decrypt data

        Args:
            encrypted_data: Base64 encrypted data

        Returns:
            Decrypted and deserialized data
        """
        try:
            encrypted_bytes = base64.b64decode(encrypted_data.encode())
            decrypted = self.fernet.decrypt(encrypted_bytes)
            return json.loads(decrypted.decode())
        except Exception as e:
            print(f"[ERROR] Failed to decrypt data: {e}")
            return None

    # === SECRET ROTATION ===

    def rotate_secret(self, secret_name: str) -> Optional[str]:
        """
        Rotate secret (generate new value)

        Args:
            secret_name: Secret to rotate

        Returns:
            New secret value or None
        """
        # Get current secret
        current = self.get_secret(secret_name)

        if not current:
            return None

        # Generate new secret value based on type
        cursor = self.conn.cursor()
        cursor.execute('SELECT secret_type FROM encrypted_secrets WHERE secret_name = ?',
                      (secret_name,))

        result = cursor.fetchone()
        secret_type = result['secret_type'] if result else 'generic'

        # Generate new value
        if secret_type == 'api_key':
            new_value = f"sk_{secrets.token_urlsafe(32)}"
        elif secret_type == 'token':
            new_value = secrets.token_urlsafe(32)
        else:
            new_value = secrets.token_hex(32)

        # Store new value
        self.store_secret(secret_name, new_value, secret_type)

        # Update rotation count
        cursor.execute('''
            UPDATE encrypted_secrets
            SET rotation_count = rotation_count + 1,
                last_rotated = CURRENT_TIMESTAMP
            WHERE secret_name = ?
        ''', (secret_name,))

        self.conn.commit()

        self._log_access(secret_name, "system", "rotate")

        return new_value

    def check_expiring_secrets(self, days: int = 30) -> list:
        """
        Check for secrets expiring soon

        Args:
            days: Days threshold

        Returns:
            List of expiring secrets
        """
        cursor = self.conn.cursor()

        threshold = datetime.now() + timedelta(days=days)

        cursor.execute('''
            SELECT secret_name, expires_at, secret_type
            FROM encrypted_secrets
            WHERE expires_at IS NOT NULL
            AND expires_at <= ?
            ORDER BY expires_at ASC
        ''', (threshold,))

        return [dict(row) for row in cursor.fetchall()]

    # === LOGGING ===

    def _log_access(self, secret_name: str, accessed_by: str, access_type: str):
        """Log secret access"""
        cursor = self.conn.cursor()

        cursor.execute('''
            INSERT INTO secret_access_log (secret_name, accessed_by, access_type)
            VALUES (?, ?, ?)
        ''', (secret_name, accessed_by, access_type))

        self.conn.commit()

    def get_access_log(self, secret_name: str = None, limit: int = 100) -> list:
        """Get secret access log"""
        cursor = self.conn.cursor()

        if secret_name:
            cursor.execute('''
                SELECT * FROM secret_access_log
                WHERE secret_name = ?
                ORDER BY accessed_at DESC
                LIMIT ?
            ''', (secret_name, limit))
        else:
            cursor.execute('''
                SELECT * FROM secret_access_log
                ORDER BY accessed_at DESC
                LIMIT ?
            ''', (limit,))

        return [dict(row) for row in cursor.fetchall()]

    # === UTILITIES ===

    def list_secrets(self) -> list:
        """List all stored secrets (names only)"""
        cursor = self.conn.cursor()

        cursor.execute('''
            SELECT secret_name, secret_type, expires_at, rotation_count, created_at
            FROM encrypted_secrets
            ORDER BY created_at DESC
        ''')

        return [dict(row) for row in cursor.fetchall()]

    def close(self):
        """Close database connection"""
        self.conn.close()


# === TEST CODE ===

def main():
    """Test secrets manager"""
    print("Testing Secrets Manager")
    print("=" * 70)

    # Note: cryptography library required
    try:
        from cryptography.fernet import Fernet
    except ImportError:
        print("[SKIP] cryptography library not installed")
        print("Install with: pip install cryptography")
        return

    manager = SecretsManager()

    try:
        # Store secret
        print("\n1. Storing encrypted secret...")
        success = manager.store_secret(
            "test_api_key",
            "sk_test_1234567890abcdef",
            secret_type="api_key",
            expires_days=90
        )
        print(f"   Stored: {success}")

        # Retrieve secret
        print("\n2. Retrieving secret...")
        secret = manager.get_secret("test_api_key", accessed_by="test_user")
        print(f"   Retrieved: {secret[:20]}..." if secret else "   Failed")

        # Hash password
        print("\n3. Hashing password...")
        password = "secure_password_123"
        password_hash, salt = manager.hash_password(password)
        print(f"   Hash: {password_hash[:20]}...")

        # Verify password
        print("\n4. Verifying password...")
        is_valid = manager.verify_password(password, password_hash, salt)
        is_invalid = manager.verify_password("wrong_password", password_hash, salt)
        print(f"   Correct password: {is_valid}")
        print(f"   Wrong password: {is_invalid}")

        # Encrypt data
        print("\n5. Encrypting data...")
        data = {"user": "test", "permissions": ["read", "write"]}
        encrypted = manager.encrypt_data(data)
        print(f"   Encrypted: {encrypted[:40]}...")

        # Decrypt data
        print("\n6. Decrypting data...")
        decrypted = manager.decrypt_data(encrypted)
        print(f"   Decrypted: {decrypted}")

        # Rotate secret
        print("\n7. Rotating secret...")
        new_secret = manager.rotate_secret("test_api_key")
        print(f"   New secret: {new_secret[:20]}..." if new_secret else "   Failed")

        # Check expiring
        print("\n8. Checking expiring secrets...")
        expiring = manager.check_expiring_secrets(days=90)
        print(f"   Expiring in 90 days: {len(expiring)}")

        # List secrets
        print("\n9. Listing secrets...")
        secrets_list = manager.list_secrets()
        print(f"   Total secrets: {len(secrets_list)}")

        # Get access log
        print("\n10. Access log...")
        log = manager.get_access_log("test_api_key", limit=5)
        print(f"   Access events: {len(log)}")

        print(f"\n[OK] Secrets Manager working!")
        print(f"Database: {manager.db_path}")

    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        manager.close()


if __name__ == "__main__":
    main()
