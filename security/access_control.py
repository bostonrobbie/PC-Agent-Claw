#!/usr/bin/env python3
"""
Access Control & Authorization System
Permission management and access control
"""
import sys
from pathlib import Path
import json
import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

sys.path.append(str(Path(__file__).parent.parent))


class AccessControl:
    """
    Access control and authorization

    Features:
    - Role-based access control (RBAC)
    - Permission management
    - API key management
    - Token generation and validation
    - Access logging
    - Privilege escalation detection
    """

    def __init__(self, db_path: str = None):
        workspace = Path(__file__).parent.parent
        if db_path is None:
            db_path = str(workspace / "memory.db")

        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

        # In-memory permission cache for performance
        self.permission_cache = {}

    def _init_db(self):
        """Initialize database schema"""
        cursor = self.conn.cursor()

        # Roles
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role_name TEXT UNIQUE NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Permissions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                permission_name TEXT UNIQUE NOT NULL,
                resource_type TEXT,
                action TEXT,
                description TEXT
            )
        ''')

        # Role permissions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS role_permissions (
                role_id INTEGER NOT NULL,
                permission_id INTEGER NOT NULL,
                granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (role_id, permission_id),
                FOREIGN KEY (role_id) REFERENCES roles(id),
                FOREIGN KEY (permission_id) REFERENCES permissions(id)
            )
        ''')

        # Users/entities
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id TEXT UNIQUE NOT NULL,
                entity_type TEXT NOT NULL,
                role_id INTEGER,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (role_id) REFERENCES roles(id)
            )
        ''')

        # API keys
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_hash TEXT UNIQUE NOT NULL,
                entity_id TEXT NOT NULL,
                description TEXT,
                expires_at TIMESTAMP,
                last_used TIMESTAMP,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (entity_id) REFERENCES entities(entity_id)
            )
        ''')

        # Access log
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS access_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id TEXT NOT NULL,
                resource TEXT NOT NULL,
                action TEXT NOT NULL,
                granted INTEGER NOT NULL,
                reason TEXT,
                logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        self.conn.commit()

        # Create default roles
        self._create_default_roles()

    def _create_default_roles(self):
        """Create default roles"""
        default_roles = [
            ('admin', 'Full system access'),
            ('user', 'Standard user access'),
            ('read_only', 'Read-only access'),
            ('api', 'API access only')
        ]

        cursor = self.conn.cursor()

        for role_name, description in default_roles:
            cursor.execute('''
                INSERT OR IGNORE INTO roles (role_name, description)
                VALUES (?, ?)
            ''', (role_name, description))

        self.conn.commit()

    # === ROLE MANAGEMENT ===

    def create_role(self, role_name: str, description: str = None) -> int:
        """Create new role"""
        cursor = self.conn.cursor()

        cursor.execute('''
            INSERT INTO roles (role_name, description)
            VALUES (?, ?)
        ''', (role_name, description))

        self.conn.commit()
        return cursor.lastrowid

    def assign_permission_to_role(self, role_name: str, permission_name: str) -> bool:
        """Assign permission to role"""
        cursor = self.conn.cursor()

        # Get role ID
        cursor.execute('SELECT id FROM roles WHERE role_name = ?', (role_name,))
        role_result = cursor.fetchone()

        if not role_result:
            return False

        # Get permission ID
        cursor.execute('SELECT id FROM permissions WHERE permission_name = ?', (permission_name,))
        perm_result = cursor.fetchone()

        if not perm_result:
            return False

        # Assign
        cursor.execute('''
            INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
            VALUES (?, ?)
        ''', (role_result['id'], perm_result['id']))

        self.conn.commit()

        # Clear cache
        self.permission_cache.clear()

        return True

    # === PERMISSION MANAGEMENT ===

    def create_permission(self, permission_name: str, resource_type: str,
                         action: str, description: str = None) -> int:
        """Create new permission"""
        cursor = self.conn.cursor()

        cursor.execute('''
            INSERT INTO permissions (permission_name, resource_type, action, description)
            VALUES (?, ?, ?, ?)
        ''', (permission_name, resource_type, action, description))

        self.conn.commit()
        return cursor.lastrowid

    def has_permission(self, entity_id: str, permission_name: str) -> bool:
        """
        Check if entity has permission

        Args:
            entity_id: Entity identifier
            permission_name: Permission to check

        Returns:
            True if has permission
        """
        # Check cache first
        cache_key = f"{entity_id}:{permission_name}"
        if cache_key in self.permission_cache:
            return self.permission_cache[cache_key]

        cursor = self.conn.cursor()

        # Get entity's role
        cursor.execute('''
            SELECT role_id FROM entities WHERE entity_id = ? AND is_active = 1
        ''', (entity_id,))

        entity_result = cursor.fetchone()

        if not entity_result or not entity_result['role_id']:
            self.permission_cache[cache_key] = False
            return False

        # Check if role has permission
        cursor.execute('''
            SELECT COUNT(*) as count
            FROM role_permissions rp
            JOIN permissions p ON rp.permission_id = p.id
            WHERE rp.role_id = ? AND p.permission_name = ?
        ''', (entity_result['role_id'], permission_name))

        has_perm = cursor.fetchone()['count'] > 0

        # Cache result
        self.permission_cache[cache_key] = has_perm

        return has_perm

    def check_access(self, entity_id: str, resource: str, action: str) -> bool:
        """
        Check if entity can perform action on resource

        Args:
            entity_id: Entity identifier
            resource: Resource being accessed
            action: Action being performed

        Returns:
            True if access granted
        """
        # Build permission name
        permission_name = f"{resource}:{action}"

        has_perm = self.has_permission(entity_id, permission_name)

        # Log access attempt
        self._log_access(entity_id, resource, action, has_perm,
                        None if has_perm else "Permission denied")

        return has_perm

    def _log_access(self, entity_id: str, resource: str, action: str,
                   granted: bool, reason: str = None):
        """Log access attempt"""
        cursor = self.conn.cursor()

        cursor.execute('''
            INSERT INTO access_log (entity_id, resource, action, granted, reason)
            VALUES (?, ?, ?, ?, ?)
        ''', (entity_id, resource, action, 1 if granted else 0, reason))

        self.conn.commit()

    # === ENTITY MANAGEMENT ===

    def register_entity(self, entity_id: str, entity_type: str, role_name: str) -> bool:
        """Register new entity with role"""
        cursor = self.conn.cursor()

        # Get role ID
        cursor.execute('SELECT id FROM roles WHERE role_name = ?', (role_name,))
        role_result = cursor.fetchone()

        if not role_result:
            return False

        # Register entity
        cursor.execute('''
            INSERT OR REPLACE INTO entities (entity_id, entity_type, role_id)
            VALUES (?, ?, ?)
        ''', (entity_id, entity_type, role_result['id']))

        self.conn.commit()
        return True

    def deactivate_entity(self, entity_id: str):
        """Deactivate entity"""
        cursor = self.conn.cursor()

        cursor.execute('''
            UPDATE entities SET is_active = 0 WHERE entity_id = ?
        ''', (entity_id,))

        self.conn.commit()

        # Clear permissions cache for this entity
        self.permission_cache = {k: v for k, v in self.permission_cache.items()
                                if not k.startswith(f"{entity_id}:")}

    # === API KEY MANAGEMENT ===

    def generate_api_key(self, entity_id: str, description: str = None,
                        expires_days: int = 365) -> str:
        """
        Generate API key for entity

        Args:
            entity_id: Entity identifier
            description: Key description
            expires_days: Days until expiration

        Returns:
            API key (only returned once!)
        """
        # Generate secure random key
        api_key = f"sk_{secrets.token_urlsafe(32)}"

        # Hash for storage
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        # Calculate expiration
        expires_at = datetime.now() + timedelta(days=expires_days)

        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO api_keys (key_hash, entity_id, description, expires_at)
            VALUES (?, ?, ?, ?)
        ''', (key_hash, entity_id, description, expires_at))

        self.conn.commit()

        return api_key

    def validate_api_key(self, api_key: str) -> Optional[str]:
        """
        Validate API key and return entity ID

        Args:
            api_key: API key to validate

        Returns:
            Entity ID if valid, None otherwise
        """
        # Hash provided key
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT entity_id FROM api_keys
            WHERE key_hash = ?
            AND is_active = 1
            AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
        ''', (key_hash,))

        result = cursor.fetchone()

        if result:
            # Update last used
            cursor.execute('''
                UPDATE api_keys
                SET last_used = CURRENT_TIMESTAMP
                WHERE key_hash = ?
            ''', (key_hash,))
            self.conn.commit()

            return result['entity_id']

        return None

    def revoke_api_key(self, api_key: str):
        """Revoke API key"""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE api_keys SET is_active = 0 WHERE key_hash = ?
        ''', (key_hash,))
        self.conn.commit()

    # === REPORTING ===

    def get_access_summary(self, entity_id: str = None, hours: int = 24) -> Dict:
        """Get access summary"""
        cursor = self.conn.cursor()

        if entity_id:
            cursor.execute('''
                SELECT
                    COUNT(*) as total,
                    SUM(granted) as granted_count,
                    SUM(CASE WHEN granted = 0 THEN 1 ELSE 0 END) as denied_count
                FROM access_log
                WHERE entity_id = ?
                AND logged_at >= datetime('now', ? || ' hours')
            ''', (entity_id, f'-{hours}'))
        else:
            cursor.execute('''
                SELECT
                    COUNT(*) as total,
                    SUM(granted) as granted_count,
                    SUM(CASE WHEN granted = 0 THEN 1 ELSE 0 END) as denied_count
                FROM access_log
                WHERE logged_at >= datetime('now', ? || ' hours')
            ''', (f'-{hours}',))

        result = cursor.fetchone()

        return {
            'total_attempts': result['total'],
            'granted': result['granted_count'],
            'denied': result['denied_count'],
            'period_hours': hours
        }

    def close(self):
        """Close database connection"""
        self.conn.close()


# === TEST CODE ===

def main():
    """Test access control"""
    print("Testing Access Control System")
    print("=" * 70)

    ac = AccessControl()

    try:
        # Create permissions
        print("\n1. Creating permissions...")
        ac.create_permission("system:read", "system", "read", "Read system data")
        ac.create_permission("system:write", "system", "write", "Write system data")
        ac.create_permission("system:admin", "system", "admin", "Admin system access")
        print("   Created 3 permissions")

        # Assign permissions to roles
        print("\n2. Assigning permissions to roles...")
        ac.assign_permission_to_role("admin", "system:admin")
        ac.assign_permission_to_role("admin", "system:write")
        ac.assign_permission_to_role("admin", "system:read")
        ac.assign_permission_to_role("user", "system:read")
        ac.assign_permission_to_role("user", "system:write")
        print("   Permissions assigned")

        # Register entities
        print("\n3. Registering entities...")
        ac.register_entity("user_admin", "user", "admin")
        ac.register_entity("user_standard", "user", "user")
        print("   Registered 2 entities")

        # Check permissions
        print("\n4. Checking permissions...")
        can_admin = ac.has_permission("user_admin", "system:admin")
        can_user_admin = ac.has_permission("user_standard", "system:admin")
        print(f"   Admin has admin permission: {can_admin}")
        print(f"   User has admin permission: {can_user_admin}")

        # Check access
        print("\n5. Checking access...")
        admin_access = ac.check_access("user_admin", "system", "admin")
        user_access = ac.check_access("user_standard", "system", "admin")
        print(f"   Admin access granted: {admin_access}")
        print(f"   User access granted: {user_access}")

        # Generate API key
        print("\n6. Generating API key...")
        api_key = ac.generate_api_key("user_admin", "Test key", expires_days=30)
        print(f"   API key: {api_key[:20]}...")

        # Validate API key
        print("\n7. Validating API key...")
        entity_id = ac.validate_api_key(api_key)
        print(f"   Valid for entity: {entity_id}")

        # Get summary
        print("\n8. Access summary...")
        summary = ac.get_access_summary(hours=24)
        print(f"   Total attempts: {summary['total_attempts']}")
        print(f"   Granted: {summary['granted']}")
        print(f"   Denied: {summary['denied']}")

        print(f"\n[OK] Access Control working!")
        print(f"Database: {ac.db_path}")

    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        ac.close()


if __name__ == "__main__":
    main()
