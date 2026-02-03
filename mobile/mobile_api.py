#!/usr/bin/env python3
"""
Mobile API
Optimized API endpoints for mobile app execution
"""
import sys
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS
import json
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))

from business.sop_manager import SOPManager
from business.process_automation import ProcessAutomation
from compliance.audit_system import AuditSystem

app = Flask(__name__)
CORS(app)

# Initialize systems
sop_manager = None
automation = None
audit = None


def init_systems():
    """Initialize business systems"""
    global sop_manager, automation, audit

    sop_manager = SOPManager()
    automation = ProcessAutomation()
    audit = AuditSystem()


# === MOBILE-OPTIMIZED ENDPOINTS ===

@app.route('/api/mobile/health', methods=['GET'])
def health_check():
    """Health check for mobile app"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })


@app.route('/api/mobile/sops/active', methods=['GET'])
def get_active_sops():
    """
    Get active SOPs (mobile-optimized)
    Returns minimal data for fast loading
    """
    try:
        user_id = request.headers.get('X-User-ID', 'mobile_user')

        # Log access
        audit.log_action(
            user_id,
            'view_sops',
            'sop_list',
            None,
            ip_address=request.remote_addr
        )

        cursor = sop_manager.conn.cursor()
        cursor.execute('''
            SELECT
                id,
                sop_code,
                sop_title,
                estimated_duration_minutes,
                automation_level
            FROM sops
            WHERE status = 'active'
            ORDER BY sop_code
        ''')

        sops = []
        for row in cursor.fetchall():
            sops.append({
                'id': row['id'],
                'code': row['sop_code'],
                'title': row['sop_title'],
                'duration': row['estimated_duration_minutes'],
                'automated': row['automation_level'] > 0.5
            })

        return jsonify({
            'sops': sops,
            'count': len(sops)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/mobile/sops/<int:sop_id>', methods=['GET'])
def get_sop_detail(sop_id):
    """Get SOP details for mobile execution"""
    try:
        user_id = request.headers.get('X-User-ID', 'mobile_user')

        # Log access
        audit.log_action(
            user_id,
            'view_sop_detail',
            'sop',
            str(sop_id),
            ip_address=request.remote_addr
        )

        # Get SOP
        sop = sop_manager.get_sop(sop_id)

        # Get steps
        steps = sop_manager.get_steps(sop_id)

        # Simplify for mobile
        mobile_steps = []
        for step in steps:
            mobile_steps.append({
                'number': step['step_number'],
                'title': step['step_title'],
                'description': step['description'],
                'type': step['step_type'],
                'duration': step['estimated_duration_minutes']
            })

        return jsonify({
            'id': sop['id'],
            'code': sop['sop_code'],
            'title': sop['sop_title'],
            'description': sop['description'],
            'purpose': sop['purpose'],
            'steps': mobile_steps,
            'total_duration': sop['estimated_duration_minutes']
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/mobile/execute/start', methods=['POST'])
def start_mobile_execution():
    """Start SOP execution from mobile"""
    try:
        data = request.json
        user_id = data.get('user_id', 'mobile_user')
        sop_id = data['sop_id']

        # Start execution
        exec_id = sop_manager.start_execution(sop_id, user_id)

        # Log event
        audit.log_action(
            user_id,
            'start_execution',
            'sop',
            str(sop_id),
            {'execution_id': exec_id, 'platform': 'mobile'},
            ip_address=request.remote_addr
        )

        return jsonify({
            'execution_id': exec_id,
            'success': True,
            'started_at': datetime.now().isoformat()
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/mobile/execute/<int:exec_id>/step/<int:step_num>', methods=['POST'])
def complete_mobile_step(exec_id, step_num):
    """Complete step from mobile"""
    try:
        data = request.json
        user_id = data.get('user_id', 'mobile_user')

        # Complete step
        success = sop_manager.complete_step(
            exec_id,
            step_num,
            result=data.get('result'),
            notes=data.get('notes')
        )

        # Log event
        audit.log_action(
            user_id,
            'complete_step',
            'execution',
            str(exec_id),
            {'step_number': step_num, 'platform': 'mobile'},
            ip_address=request.remote_addr
        )

        return jsonify({
            'success': success,
            'completed_at': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/mobile/execute/<int:exec_id>/complete', methods=['POST'])
def complete_mobile_execution(exec_id):
    """Complete execution from mobile"""
    try:
        data = request.json
        user_id = data.get('user_id', 'mobile_user')
        success = data.get('success', True)

        # Complete execution
        sop_manager.complete_execution(exec_id, success=success)

        # Log event
        audit.log_action(
            user_id,
            'complete_execution',
            'execution',
            str(exec_id),
            {'success': success, 'platform': 'mobile'},
            ip_address=request.remote_addr
        )

        return jsonify({
            'success': True,
            'completed_at': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/mobile/executions/active', methods=['GET'])
def get_active_executions():
    """Get user's active executions"""
    try:
        user_id = request.headers.get('X-User-ID', 'mobile_user')

        cursor = sop_manager.conn.cursor()
        cursor.execute('''
            SELECT
                e.id,
                e.sop_id,
                e.started_at,
                s.sop_code,
                s.sop_title,
                s.estimated_duration_minutes
            FROM sop_executions e
            JOIN sops s ON e.sop_id = s.id
            WHERE e.executed_by = ?
            AND e.completed_at IS NULL
            ORDER BY e.started_at DESC
        ''', (user_id,))

        executions = []
        for row in cursor.fetchall():
            executions.append({
                'id': row['id'],
                'sop_id': row['sop_id'],
                'code': row['sop_code'],
                'title': row['sop_title'],
                'started': row['started_at'],
                'estimated_duration': row['estimated_duration_minutes']
            })

        return jsonify({
            'executions': executions,
            'count': len(executions)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/mobile/user/stats', methods=['GET'])
def get_user_stats():
    """Get user's execution statistics"""
    try:
        user_id = request.headers.get('X-User-ID', 'mobile_user')

        cursor = sop_manager.conn.cursor()

        # Total executions
        cursor.execute('''
            SELECT COUNT(*) as total
            FROM sop_executions
            WHERE executed_by = ?
        ''', (user_id,))
        total = cursor.fetchone()['total']

        # Success rate
        cursor.execute('''
            SELECT AVG(CASE WHEN success = 1 THEN 1.0 ELSE 0.0 END) as success_rate
            FROM sop_executions
            WHERE executed_by = ?
        ''', (user_id,))
        success_rate = cursor.fetchone()['success_rate'] or 0

        # This week
        cursor.execute('''
            SELECT COUNT(*) as week_count
            FROM sop_executions
            WHERE executed_by = ?
            AND started_at >= DATE('now', '-7 days')
        ''', (user_id,))
        week_count = cursor.fetchone()['week_count']

        return jsonify({
            'total_executions': total,
            'success_rate': round(success_rate, 2),
            'this_week': week_count
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/mobile/notifications', methods=['GET'])
def get_notifications():
    """Get user notifications"""
    try:
        user_id = request.headers.get('X-User-ID', 'mobile_user')

        # Get pending approvals
        pending_approvals = audit.get_pending_approvals(user_id)

        notifications = []

        for approval in pending_approvals:
            notifications.append({
                'type': 'approval_required',
                'title': 'Approval Required',
                'message': f"Approval needed for {approval['resource_type']} {approval['resource_id']}",
                'request_id': approval['request_id'],
                'timestamp': approval['requested_at']
            })

        return jsonify({
            'notifications': notifications,
            'count': len(notifications),
            'unread': len(notifications)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/mobile/sync', methods=['POST'])
def sync_data():
    """Sync offline data from mobile"""
    try:
        data = request.json
        user_id = data.get('user_id', 'mobile_user')

        # Process offline actions
        offline_actions = data.get('offline_actions', [])

        results = []
        for action in offline_actions:
            try:
                # Execute offline action
                if action['type'] == 'complete_step':
                    sop_manager.complete_step(
                        action['execution_id'],
                        action['step_number'],
                        result=action.get('result')
                    )
                    results.append({'action_id': action['id'], 'success': True})
                else:
                    results.append({'action_id': action['id'], 'success': False,
                                  'error': 'Unknown action type'})

            except Exception as e:
                results.append({'action_id': action['id'], 'success': False,
                              'error': str(e)})

        # Log sync event
        audit.log_action(
            user_id,
            'mobile_sync',
            None,
            None,
            {'actions_count': len(offline_actions), 'success_count': sum(1 for r in results if r['success'])},
            ip_address=request.remote_addr
        )

        return jsonify({
            'synced': True,
            'results': results,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# === ERROR HANDLERS ===

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500


# === MAIN ===

def main():
    """Run mobile API server"""
    print("=" * 70)
    print("Mobile API Server")
    print("=" * 70)

    print("\nInitializing systems...")
    init_systems()

    print("✓ SOP Manager")
    print("✓ Process Automation")
    print("✓ Audit System")

    print("\n" + "=" * 70)
    print("Mobile API running on http://localhost:5001")
    print("=" * 70)
    print("\nMobile Endpoints:")
    print("  GET  /api/mobile/sops/active       - List active SOPs")
    print("  POST /api/mobile/execute/start     - Start execution")
    print("  POST /api/mobile/execute/.../step  - Complete step")
    print("  GET  /api/mobile/user/stats        - User statistics")
    print("  POST /api/mobile/sync              - Sync offline data")
    print("\nPress Ctrl+C to stop")
    print("=" * 70 + "\n")

    app.run(host='0.0.0.0', port=5001, debug=True)


if __name__ == "__main__":
    main()
