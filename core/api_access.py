#!/usr/bin/env python3
"""API Access System (#4) - Manage API keys and access to external services"""
import os
import json
from pathlib import Path
from typing import Dict, Optional
import sys
from cryptography.fernet import Fernet
import base64

sys.path.append(str(Path(__file__).parent.parent))

from core.persistent_memory import PersistentMemory

class APIAccessSystem:
    """Secure management of API keys and external service access"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            workspace = Path(__file__).parent.parent
            db_path = str(workspace / "memory.db")

        self.memory = PersistentMemory(db_path)
        self.credentials_file = Path(__file__).parent.parent / ".credentials.enc"
        self.key_file = Path(__file__).parent.parent / ".key"

        # Initialize encryption
        self._ensure_encryption_key()

    def _ensure_encryption_key(self):
        """Ensure encryption key exists"""
        if not self.key_file.exists():
            key = Fernet.generate_key()
            self.key_file.write_bytes(key)
            self.key_file.chmod(0o600)  # Read/write for owner only

        self.cipher = Fernet(self.key_file.read_bytes())

    def store_credential(self, service: str, key_name: str, key_value: str):
        """Store an API credential securely"""
        # Load existing credentials
        credentials = self._load_credentials()

        # Add new credential
        if service not in credentials:
            credentials[service] = {}

        credentials[service][key_name] = key_value

        # Save encrypted
        self._save_credentials(credentials)

        # Log to memory (without exposing the key)
        self.memory.log_decision(
            f'Credential stored: {service}.{key_name}',
            f'Service: {service}, Key: {key_name}',
            tags=['api_access', 'credential', service]
        )

    def get_credential(self, service: str, key_name: str) -> Optional[str]:
        """Retrieve an API credential"""
        credentials = self._load_credentials()

        if service in credentials and key_name in credentials[service]:
            return credentials[service][key_name]

        # Try environment variables as fallback
        env_var = f"{service.upper()}_{key_name.upper()}"
        return os.getenv(env_var)

    def list_services(self) -> list:
        """List all services with stored credentials"""
        credentials = self._load_credentials()
        return list(credentials.keys())

    def remove_credential(self, service: str, key_name: str = None):
        """Remove a credential (or entire service)"""
        credentials = self._load_credentials()

        if service in credentials:
            if key_name:
                if key_name in credentials[service]:
                    del credentials[service][key_name]
            else:
                del credentials[service]

            self._save_credentials(credentials)

            self.memory.log_decision(
                f'Credential removed: {service}' + (f'.{key_name}' if key_name else ''),
                f'Service: {service}',
                tags=['api_access', 'removal', service]
            )

    def _load_credentials(self) -> Dict:
        """Load and decrypt credentials"""
        if not self.credentials_file.exists():
            return {}

        try:
            encrypted_data = self.credentials_file.read_bytes()
            decrypted_data = self.cipher.decrypt(encrypted_data)
            return json.loads(decrypted_data)
        except Exception:
            return {}

    def _save_credentials(self, credentials: Dict):
        """Encrypt and save credentials"""
        json_data = json.dumps(credentials)
        encrypted_data = self.cipher.encrypt(json_data.encode())
        self.credentials_file.write_bytes(encrypted_data)
        self.credentials_file.chmod(0o600)

    # Convenience methods for common services

    def set_openai_key(self, api_key: str):
        """Store OpenAI API key"""
        self.store_credential('openai', 'api_key', api_key)

    def get_openai_key(self) -> Optional[str]:
        """Get OpenAI API key"""
        return self.get_credential('openai', 'api_key')

    def set_manus_key(self, api_key: str):
        """Store Manus API key"""
        self.store_credential('manus', 'api_key', api_key)

    def get_manus_key(self) -> Optional[str]:
        """Get Manus API key"""
        return self.get_credential('manus', 'api_key')

    def set_google_ads_credentials(self, client_id: str, client_secret: str,
                                   developer_token: str, refresh_token: str = None):
        """Store Google Ads credentials"""
        self.store_credential('google_ads', 'client_id', client_id)
        self.store_credential('google_ads', 'client_secret', client_secret)
        self.store_credential('google_ads', 'developer_token', developer_token)
        if refresh_token:
            self.store_credential('google_ads', 'refresh_token', refresh_token)

    def get_google_ads_credentials(self) -> Dict:
        """Get Google Ads credentials"""
        return {
            'client_id': self.get_credential('google_ads', 'client_id'),
            'client_secret': self.get_credential('google_ads', 'client_secret'),
            'developer_token': self.get_credential('google_ads', 'developer_token'),
            'refresh_token': self.get_credential('google_ads', 'refresh_token')
        }

    def set_telegram_token(self, bot_token: str):
        """Store Telegram bot token"""
        self.store_credential('telegram', 'bot_token', bot_token)

    def get_telegram_token(self) -> Optional[str]:
        """Get Telegram bot token"""
        return self.get_credential('telegram', 'bot_token')


if __name__ == '__main__':
    # Test the system
    api_access = APIAccessSystem()

    print("API Access System ready!")
    print("\nStored services:")
    services = api_access.list_services()
    for service in services:
        print(f"  - {service}")

    print("\nExample usage:")
    print("  api_access.set_openai_key('sk-...')")
    print("  api_access.set_manus_key('manus_...')")
    print("  api_access.set_google_ads_credentials(...)")
    print("  api_access.set_telegram_token('bot123:...')")
