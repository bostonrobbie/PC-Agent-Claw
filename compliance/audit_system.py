#!/usr/bin/env python3
"""
Compliance and Audit System
Track compliance, maintain audit trails, enforce regulatory requirements
"""
import sys
from pathlib import Path
import sqlite3
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum

sys.path.append(str(Path(__file__).parent.parent))


class ComplianceLevel(Enum):
    """Compliance requirement levels"""
    BASIC = "basic"
    STANDARD = "standard"
    STRICT = "strict"
    REGULATORY = "regulatory"


class AuditSystem:
    """
    Compliance and audit management

    Features:
    - Complete audit trail for all actions
    - Compliance requirement tracking
    - Approval workflows
    - Regulatory reporting
    - Data retention policies
    - Access logs
    - Change tracking
    """

    def __init__(self, db_path: str = None):
        workspace = Path(__file__).parent.parent
        if db_path is None:
            db_path = str(workspace / "memory.db")

        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        """Initialize audit database schema"""
        cursor = self.conn.cursor()

        # Audit log
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id TEXT NOT NULL,
                action TEXT NOT NULL,
                resource_type TEXT,
                resource_id TEXT,
                details TEXT,
                ip_address TEXT,
                user_agent TEXT,
                status TEXT DEFAULT 'success',
                checksum TEXT
            )
        ''')

        # Compliance requirements
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS compliance_requirements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                requirement_code TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                compliance_level TEXT,
                regulatory_framework TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # SOP compliance mapping
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sop_compliance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sop_id INTEGER NOT NULL,
                requirement_id INTEGER NOT NULL,
                compliance_status TEXT DEFAULT 'pending',
                last_verified TIMESTAMP,
                verified_by TEXT,
                notes TEXT,
                FOREIGN KEY (sop_id) REFERENCES sops(id),
                FOREIGN KEY (requirement_id) REFERENCES compliance_requirements(id)
            )
        ''')

        # Approval workflows
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS approval_workflows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_name TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                required_approvers INTEGER DEFAULT 1,
                approval_order TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Approval requests
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS approval_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id INTEGER NOT NULL,
                resource_type TEXT NOT NULL,
                resource_id TEXT NOT NULL,
                requested_by TEXT NOT NULL,
                requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending',
                completed_at TIMESTAMP,
                FOREIGN KEY (workflow_id) REFERENCES approval_workflows(id)
            )
        ''')

        # Individual approvals
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS approvals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id INTEGER NOT NULL,
                approver_id TEXT NOT NULL,
                decision TEXT,
                decided_at TIMESTAMP,
                comments TEXT,
                FOREIGN KEY (request_id) REFERENCES approval_requests(id)
            )
        ''')

        # Data retention policies
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS retention_policies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resource_type TEXT NOT NULL,
                retention_days INTEGER NOT NULL,
                policy_description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        self.conn.commit()

    # === AUDIT LOGGING ===

    def log_action(self, user_id: str, action: str,
                  resource_type: str = None, resource_id: str = None,
                  details: Dict = None, ip_address: str = None,
                  user_agent: str = None, status: str = 'success') -> int:
        """
        Log action to audit trail

        Args:
            user_id: User performing action
            action: Action performed (create/update/delete/access/etc.)
            resource_type: Type of resource (sop/workflow/etc.)
            resource_id: Resource identifier
            details: Additional details
            ip_address: User's IP address
            user_agent: Browser user agent
            status: Action status

        Returns:
            Audit log entry ID
        """
        cursor = self.conn.cursor()

        # Create details JSON
        details_json = json.dumps(details) if details else None

        # Create checksum for integrity
        checksum_data = f"{user_id}{action}{resource_type}{resource_id}{details_json}"
        checksum = hashlib.sha256(checksum_data.encode()).hexdigest()

        cursor.execute('''
            INSERT INTO audit_log
            (user_id, action, resource_type, resource_id, details,
             ip_address, user_agent, status, checksum)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, action, resource_type, resource_id, details_json,
              ip_address, user_agent, status, checksum))

        self.conn.commit()
        return cursor.lastrowid

    def get_audit_trail(self, resource_type: str = None, resource_id: str = None,
                       user_id: str = None, action: str = None,
                       start_date: str = None, end_date: str = None,
                       limit: int = 100) -> List[Dict]:
        """
        Query audit trail

        Args:
            resource_type: Filter by resource type
            resource_id: Filter by resource ID
            user_id: Filter by user
            action: Filter by action
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            limit: Maximum results

        Returns:
            List of audit log entries
        """
        cursor = self.conn.cursor()

        query = 'SELECT * FROM audit_log WHERE 1=1'
        params = []

        if resource_type:
            query += ' AND resource_type = ?'
            params.append(resource_type)

        if resource_id:
            query += ' AND resource_id = ?'
            params.append(resource_id)

        if user_id:
            query += ' AND user_id = ?'
            params.append(user_id)

        if action:
            query += ' AND action = ?'
            params.append(action)

        if start_date:
            query += ' AND DATE(timestamp) >= ?'
            params.append(start_date)

        if end_date:
            query += ' AND DATE(timestamp) <= ?'
            params.append(end_date)

        query += f' ORDER BY timestamp DESC LIMIT {limit}'

        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def verify_audit_integrity(self, log_id: int) -> bool:
        """Verify audit log entry hasn't been tampered with"""
        cursor = self.conn.cursor()

        cursor.execute('SELECT * FROM audit_log WHERE id = ?', (log_id,))
        entry = dict(cursor.fetchone())

        # Recalculate checksum
        checksum_data = f"{entry['user_id']}{entry['action']}"
        checksum_data += f"{entry['resource_type']}{entry['resource_id']}{entry['details']}"
        checksum = hashlib.sha256(checksum_data.encode()).hexdigest()

        return checksum == entry['checksum']

    # === COMPLIANCE MANAGEMENT ===

    def create_compliance_requirement(self, requirement_code: str, title: str,
                                     description: str = None,
                                     compliance_level: ComplianceLevel = ComplianceLevel.STANDARD,
                                     regulatory_framework: str = None) -> int:
        """
        Create compliance requirement

        Args:
            requirement_code: Unique code (e.g., "SOX-404", "GDPR-32")
            title: Requirement title
            description: Detailed description
            compliance_level: Severity level
            regulatory_framework: Framework (SOX, GDPR, HIPAA, etc.)

        Returns:
            Requirement ID
        """
        cursor = self.conn.cursor()

        cursor.execute('''
            INSERT INTO compliance_requirements
            (requirement_code, title, description, compliance_level, regulatory_framework)
            VALUES (?, ?, ?, ?, ?)
        ''', (requirement_code, title, description, compliance_level.value, regulatory_framework))

        self.conn.commit()
        return cursor.lastrowid

    def assign_compliance_to_sop(self, sop_id: int, requirement_id: int) -> int:
        """Map compliance requirement to SOP"""
        cursor = self.conn.cursor()

        cursor.execute('''
            INSERT INTO sop_compliance (sop_id, requirement_id)
            VALUES (?, ?)
        ''', (sop_id, requirement_id))

        self.conn.commit()
        return cursor.lastrowid

    def verify_sop_compliance(self, sop_id: int, requirement_id: int,
                            verified_by: str, compliant: bool,
                            notes: str = None) -> bool:
        """
        Verify SOP meets compliance requirement

        Args:
            sop_id: SOP to verify
            requirement_id: Requirement to check
            verified_by: User verifying
            compliant: Whether compliant
            notes: Verification notes

        Returns:
            Success status
        """
        cursor = self.conn.cursor()

        status = 'compliant' if compliant else 'non_compliant'

        cursor.execute('''
            UPDATE sop_compliance
            SET compliance_status = ?,
                last_verified = CURRENT_TIMESTAMP,
                verified_by = ?,
                notes = ?
            WHERE sop_id = ? AND requirement_id = ?
        ''', (status, verified_by, notes, sop_id, requirement_id))

        self.conn.commit()

        # Log audit event
        self.log_action(
            verified_by,
            'compliance_verification',
            'sop',
            str(sop_id),
            {
                'requirement_id': requirement_id,
                'result': status,
                'notes': notes
            }
        )

        return True

    def get_compliance_status(self, sop_id: int = None) -> List[Dict]:
        """
        Get compliance status for SOP(s)

        Args:
            sop_id: Specific SOP or None for all

        Returns:
            Compliance status records
        """
        cursor = self.conn.cursor()

        if sop_id:
            cursor.execute('''
                SELECT
                    sc.*,
                    cr.requirement_code,
                    cr.title as requirement_title,
                    cr.compliance_level,
                    s.sop_code,
                    s.sop_title
                FROM sop_compliance sc
                JOIN compliance_requirements cr ON sc.requirement_id = cr.id
                JOIN sops s ON sc.sop_id = s.id
                WHERE sc.sop_id = ?
            ''', (sop_id,))
        else:
            cursor.execute('''
                SELECT
                    sc.*,
                    cr.requirement_code,
                    cr.title as requirement_title,
                    cr.compliance_level,
                    s.sop_code,
                    s.sop_title
                FROM sop_compliance sc
                JOIN compliance_requirements cr ON sc.requirement_id = cr.id
                JOIN sops s ON sc.sop_id = s.id
                WHERE sc.compliance_status != 'compliant'
            ''')

        return [dict(row) for row in cursor.fetchall()]

    # === APPROVAL WORKFLOWS ===

    def create_approval_workflow(self, workflow_name: str, resource_type: str,
                                required_approvers: int = 1,
                                approval_order: List[str] = None) -> int:
        """
        Create approval workflow

        Args:
            workflow_name: Workflow name
            resource_type: Type of resource requiring approval
            required_approvers: Number of required approvals
            approval_order: Ordered list of approver IDs

        Returns:
            Workflow ID
        """
        cursor = self.conn.cursor()

        order_json = json.dumps(approval_order) if approval_order else None

        cursor.execute('''
            INSERT INTO approval_workflows
            (workflow_name, resource_type, required_approvers, approval_order)
            VALUES (?, ?, ?, ?)
        ''', (workflow_name, resource_type, required_approvers, order_json))

        self.conn.commit()
        return cursor.lastrowid

    def request_approval(self, workflow_id: int, resource_type: str,
                        resource_id: str, requested_by: str) -> int:
        """
        Submit resource for approval

        Args:
            workflow_id: Approval workflow to use
            resource_type: Resource type
            resource_id: Resource ID
            requested_by: User requesting approval

        Returns:
            Approval request ID
        """
        cursor = self.conn.cursor()

        cursor.execute('''
            INSERT INTO approval_requests
            (workflow_id, resource_type, resource_id, requested_by)
            VALUES (?, ?, ?, ?)
        ''', (workflow_id, resource_type, resource_id, requested_by))

        request_id = cursor.lastrowid

        # Get workflow details
        cursor.execute('''
            SELECT approval_order, required_approvers
            FROM approval_workflows
            WHERE id = ?
        ''', (workflow_id,))

        workflow = dict(cursor.fetchone())

        # Create approval records for each approver
        if workflow['approval_order']:
            approvers = json.loads(workflow['approval_order'])
            for approver in approvers:
                cursor.execute('''
                    INSERT INTO approvals (request_id, approver_id)
                    VALUES (?, ?)
                ''', (request_id, approver))

        self.conn.commit()

        # Log audit event
        self.log_action(
            requested_by,
            'approval_requested',
            resource_type,
            resource_id,
            {'request_id': request_id, 'workflow_id': workflow_id}
        )

        return request_id

    def approve_or_reject(self, request_id: int, approver_id: str,
                         decision: str, comments: str = None) -> bool:
        """
        Approve or reject request

        Args:
            request_id: Approval request ID
            approver_id: User approving/rejecting
            decision: 'approved' or 'rejected'
            comments: Optional comments

        Returns:
            Success status
        """
        cursor = self.conn.cursor()

        # Record decision
        cursor.execute('''
            UPDATE approvals
            SET decision = ?, decided_at = CURRENT_TIMESTAMP, comments = ?
            WHERE request_id = ? AND approver_id = ?
        ''', (decision, comments, request_id, approver_id))

        # Check if all required approvals received
        cursor.execute('''
            SELECT COUNT(*) as approved_count
            FROM approvals
            WHERE request_id = ? AND decision = 'approved'
        ''', (request_id,))

        approved_count = cursor.fetchone()['approved_count']

        cursor.execute('''
            SELECT w.required_approvers
            FROM approval_requests ar
            JOIN approval_workflows w ON ar.workflow_id = w.id
            WHERE ar.id = ?
        ''', (request_id,))

        required = cursor.fetchone()['required_approvers']

        # Update request status if complete
        if approved_count >= required:
            cursor.execute('''
                UPDATE approval_requests
                SET status = 'approved', completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (request_id,))
        elif decision == 'rejected':
            cursor.execute('''
                UPDATE approval_requests
                SET status = 'rejected', completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (request_id,))

        self.conn.commit()

        # Log audit event
        cursor.execute('''
            SELECT resource_type, resource_id
            FROM approval_requests
            WHERE id = ?
        ''', (request_id,))

        request = dict(cursor.fetchone())

        self.log_action(
            approver_id,
            f'approval_{decision}',
            request['resource_type'],
            request['resource_id'],
            {'request_id': request_id, 'comments': comments}
        )

        return True

    def get_pending_approvals(self, approver_id: str) -> List[Dict]:
        """Get pending approval requests for user"""
        cursor = self.conn.cursor()

        cursor.execute('''
            SELECT
                ar.id as request_id,
                ar.resource_type,
                ar.resource_id,
                ar.requested_by,
                ar.requested_at,
                a.id as approval_id
            FROM approval_requests ar
            JOIN approvals a ON ar.id = a.request_id
            WHERE a.approver_id = ?
            AND a.decision IS NULL
            AND ar.status = 'pending'
            ORDER BY ar.requested_at DESC
        ''', (approver_id,))

        return [dict(row) for row in cursor.fetchall()]

    # === REPORTING ===

    def generate_compliance_report(self, start_date: str = None,
                                  end_date: str = None) -> Dict:
        """
        Generate compliance report

        Args:
            start_date: Report start date
            end_date: Report end date

        Returns:
            Compliance report
        """
        cursor = self.conn.cursor()

        # Overall compliance status
        cursor.execute('''
            SELECT
                COUNT(*) as total_requirements,
                SUM(CASE WHEN compliance_status = 'compliant' THEN 1 ELSE 0 END) as compliant,
                SUM(CASE WHEN compliance_status = 'non_compliant' THEN 1 ELSE 0 END) as non_compliant,
                SUM(CASE WHEN compliance_status = 'pending' THEN 1 ELSE 0 END) as pending
            FROM sop_compliance
        ''')

        summary = dict(cursor.fetchone())

        # By compliance level
        cursor.execute('''
            SELECT
                cr.compliance_level,
                COUNT(*) as total,
                SUM(CASE WHEN sc.compliance_status = 'compliant' THEN 1 ELSE 0 END) as compliant
            FROM sop_compliance sc
            JOIN compliance_requirements cr ON sc.requirement_id = cr.id
            GROUP BY cr.compliance_level
        ''')

        by_level = [dict(row) for row in cursor.fetchall()]

        return {
            'summary': summary,
            'by_level': by_level,
            'generated_at': datetime.now().isoformat()
        }

    def close(self):
        """Close database connection"""
        self.conn.close()


# === TEST CODE ===

def main():
    """Test audit system"""
    print("=" * 70)
    print("Compliance and Audit System")
    print("=" * 70)

    audit = AuditSystem()

    try:
        print("\n1. Logging audit events...")
        log_id = audit.log_action(
            "test_user",
            "create",
            "sop",
            "SOP-001",
            {"description": "Created new SOP"},
            "192.168.1.1"
        )
        print(f"   Audit log ID: {log_id}")

        # Verify integrity
        valid = audit.verify_audit_integrity(log_id)
        print(f"   Integrity check: {'✓ Valid' if valid else '✗ Invalid'}")

        print("\n2. Creating compliance requirement...")
        req_id = audit.create_compliance_requirement(
            "SOX-404",
            "Internal Control Assessment",
            "Annual assessment of internal controls",
            ComplianceLevel.REGULATORY,
            "SOX"
        )
        print(f"   Requirement ID: {req_id}")

        print("\n3. Creating approval workflow...")
        workflow_id = audit.create_approval_workflow(
            "SOP Approval",
            "sop",
            required_approvers=2,
            approval_order=["manager1", "manager2"]
        )
        print(f"   Workflow ID: {workflow_id}")

        print("\n4. Generating compliance report...")
        report = audit.generate_compliance_report()
        print(f"   Total requirements: {report['summary']['total_requirements']}")

        print(f"\n[OK] Audit System working!")

    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        audit.close()


if __name__ == "__main__":
    main()
