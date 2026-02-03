#!/usr/bin/env python3
"""
REST API Server for Business Process Management
Provides API endpoints for web/mobile interfaces
"""
import sys
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS
import json
from datetime import datetime

# Add parent directory to path
workspace = Path(__file__).parent.parent.parent
sys.path.insert(0, str(workspace))

from business.sop_manager import SOPManager
from business.process_automation import ProcessAutomation
from business.process_mining import ProcessMining
from business.bi_dashboard import BIDashboard
from business.workflow_orchestrator import WorkflowOrchestrator

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

# Initialize business systems
sop_manager = None
automation = None
mining = None
dashboard = None
orchestrator = None


def init_systems():
    """Initialize all business systems"""
    global sop_manager, automation, mining, dashboard, orchestrator

    sop_manager = SOPManager()
    automation = ProcessAutomation()
    mining = ProcessMining()
    dashboard = BIDashboard()
    orchestrator = WorkflowOrchestrator()


# === HEALTH CHECK ===

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'systems': {
            'sop_manager': sop_manager is not None,
            'automation': automation is not None,
            'mining': mining is not None,
            'dashboard': dashboard is not None,
            'orchestrator': orchestrator is not None
        }
    })


# === DASHBOARD / OVERVIEW ===

@app.route('/api/dashboard/overview', methods=['GET'])
def get_dashboard_overview():
    """Get business overview dashboard"""
    try:
        overview = dashboard.get_business_overview()
        return jsonify(overview)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/dashboard/trends', methods=['GET'])
def get_execution_trends():
    """Get execution trends"""
    try:
        days = request.args.get('days', 30, type=int)
        granularity = request.args.get('granularity', 'day')

        trends = dashboard.get_execution_trends(days=days, granularity=granularity)
        return jsonify(trends)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/dashboard/efficiency', methods=['GET'])
def get_efficiency_report():
    """Get efficiency report"""
    try:
        efficiency = dashboard.get_efficiency_report()
        return jsonify({'efficiency_data': efficiency})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/dashboard/bottlenecks', methods=['GET'])
def get_bottlenecks():
    """Get bottleneck summary"""
    try:
        bottlenecks = dashboard.get_bottleneck_summary()
        return jsonify({'bottlenecks': bottlenecks})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/dashboard/functions', methods=['GET'])
def get_function_performance():
    """Get performance by business function"""
    try:
        functions = dashboard.get_function_performance()
        return jsonify({'functions': functions})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# === BUSINESS FUNCTIONS ===

@app.route('/api/functions', methods=['GET'])
def list_functions():
    """List all business functions"""
    try:
        cursor = sop_manager.conn.cursor()
        cursor.execute('''
            SELECT id, function_name, description, parent_function_id
            FROM business_functions
            ORDER BY function_name
        ''')

        functions = [dict(row) for row in cursor.fetchall()]
        return jsonify({'functions': functions})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/functions', methods=['POST'])
def create_function():
    """Create new business function"""
    try:
        data = request.json
        function_id = sop_manager.create_function(
            data['function_name'],
            data.get('description'),
            data.get('parent_function_id')
        )
        return jsonify({'id': function_id, 'success': True}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# === ROLES ===

@app.route('/api/roles', methods=['GET'])
def list_roles():
    """List all business roles"""
    try:
        cursor = sop_manager.conn.cursor()
        cursor.execute('''
            SELECT r.id, r.role_name, r.description, r.function_id,
                   f.function_name
            FROM business_roles r
            LEFT JOIN business_functions f ON r.function_id = f.id
            ORDER BY r.role_name
        ''')

        roles = [dict(row) for row in cursor.fetchall()]
        return jsonify({'roles': roles})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/roles', methods=['POST'])
def create_role():
    """Create new business role"""
    try:
        data = request.json
        role_id = sop_manager.create_role(
            data['role_name'],
            data['function_id'],
            data.get('description')
        )
        return jsonify({'id': role_id, 'success': True}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# === SOPs ===

@app.route('/api/sops', methods=['GET'])
def list_sops():
    """List all SOPs"""
    try:
        function_id = request.args.get('function_id', type=int)
        status = request.args.get('status', 'active')

        sops = sop_manager.list_sops(function_id=function_id, status=status)
        return jsonify({'sops': sops})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sops/<int:sop_id>', methods=['GET'])
def get_sop(sop_id):
    """Get SOP details"""
    try:
        sop = sop_manager.get_sop(sop_id)
        return jsonify(sop)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sops', methods=['POST'])
def create_sop():
    """Create new SOP"""
    try:
        data = request.json
        sop_id = sop_manager.create_sop(
            data['sop_code'],
            data['sop_title'],
            data['function_id'],
            description=data.get('description'),
            purpose=data.get('purpose'),
            scope=data.get('scope')
        )
        return jsonify({'id': sop_id, 'success': True}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sops/<int:sop_id>', methods=['PUT'])
def update_sop(sop_id):
    """Update SOP"""
    try:
        data = request.json
        sop_manager.update_sop(sop_id, data)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sops/<int:sop_id>/steps', methods=['GET'])
def get_sop_steps(sop_id):
    """Get SOP steps"""
    try:
        steps = sop_manager.get_steps(sop_id)
        return jsonify({'steps': steps})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sops/<int:sop_id>/steps', methods=['POST'])
def add_sop_step(sop_id):
    """Add step to SOP"""
    try:
        data = request.json
        step_id = sop_manager.add_step(
            sop_id,
            data['step_number'],
            data['step_title'],
            data['description'],
            step_type=data.get('step_type', 'manual'),
            estimated_duration=data.get('estimated_duration')
        )
        return jsonify({'id': step_id, 'success': True}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sops/<int:sop_id>/performance', methods=['GET'])
def get_sop_performance(sop_id):
    """Get SOP performance metrics"""
    try:
        days = request.args.get('days', 30, type=int)
        performance = dashboard.get_sop_performance(sop_id=sop_id, days=days)

        if performance:
            return jsonify(performance[0])
        else:
            return jsonify({'error': 'No performance data'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sops/<int:sop_id>/roi', methods=['GET'])
def get_sop_roi(sop_id):
    """Calculate SOP automation ROI"""
    try:
        roi = dashboard.calculate_automation_roi(sop_id)
        return jsonify(roi)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# === SOP EXECUTION ===

@app.route('/api/executions/start', methods=['POST'])
def start_execution():
    """Start SOP execution"""
    try:
        data = request.json
        exec_id = sop_manager.start_execution(
            data['sop_id'],
            data['executed_by']
        )
        return jsonify({'execution_id': exec_id, 'success': True}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/executions/<int:exec_id>/step/<int:step_number>', methods=['POST'])
def complete_step(exec_id, step_number):
    """Complete execution step"""
    try:
        data = request.json
        success = sop_manager.complete_step(
            exec_id,
            step_number,
            result=data.get('result'),
            notes=data.get('notes')
        )
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/executions/<int:exec_id>/complete', methods=['POST'])
def complete_execution(exec_id):
    """Complete SOP execution"""
    try:
        data = request.json
        sop_manager.complete_execution(
            exec_id,
            success=data.get('success', True)
        )
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# === AUTOMATION ===

@app.route('/api/automation/status', methods=['GET'])
def automation_status():
    """Get automation status"""
    try:
        status = automation.get_automation_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/automation/execute', methods=['POST'])
def execute_automated():
    """Execute SOP automatically"""
    try:
        data = request.json
        result = automation.execute_sop(
            data['sop_id'],
            context=data.get('context', {})
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# === PROCESS MINING ===

@app.route('/api/mining/bottlenecks/<int:sop_id>', methods=['GET'])
def identify_bottlenecks(sop_id):
    """Identify process bottlenecks"""
    try:
        bottlenecks = mining.identify_bottlenecks(sop_id)
        return jsonify({'bottlenecks': bottlenecks})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/mining/optimizations/<int:sop_id>', methods=['GET'])
def get_optimizations(sop_id):
    """Get optimization suggestions"""
    try:
        suggestions = mining.suggest_optimizations(sop_id)
        return jsonify({'suggestions': suggestions})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/mining/efficiency/<int:sop_id>', methods=['GET'])
def calculate_efficiency(sop_id):
    """Calculate efficiency score"""
    try:
        efficiency = mining.calculate_efficiency_score(sop_id)
        return jsonify(efficiency)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# === WORKFLOWS ===

@app.route('/api/workflows', methods=['GET'])
def list_workflows():
    """List all workflows"""
    try:
        cursor = orchestrator.conn.cursor()
        cursor.execute('''
            SELECT id, workflow_name, description, workflow_type, is_template
            FROM workflows
            ORDER BY workflow_name
        ''')

        workflows = [dict(row) for row in cursor.fetchall()]
        return jsonify({'workflows': workflows})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/workflows', methods=['POST'])
def create_workflow():
    """Create new workflow"""
    try:
        data = request.json
        workflow_id = orchestrator.create_workflow(
            data['workflow_name'],
            description=data.get('description'),
            workflow_type=data.get('workflow_type', 'sequential'),
            is_template=data.get('is_template', False)
        )
        return jsonify({'id': workflow_id, 'success': True}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/workflows/<int:workflow_id>', methods=['GET'])
def get_workflow(workflow_id):
    """Get workflow details"""
    try:
        cursor = orchestrator.conn.cursor()

        # Get workflow
        cursor.execute('SELECT * FROM workflows WHERE id = ?', (workflow_id,))
        workflow = dict(cursor.fetchone())

        # Get nodes
        cursor.execute('SELECT * FROM workflow_nodes WHERE workflow_id = ?', (workflow_id,))
        workflow['nodes'] = [dict(row) for row in cursor.fetchall()]

        # Get edges
        cursor.execute('SELECT * FROM workflow_edges WHERE workflow_id = ?', (workflow_id,))
        workflow['edges'] = [dict(row) for row in cursor.fetchall()]

        return jsonify(workflow)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/workflows/<int:workflow_id>/execute', methods=['POST'])
def execute_workflow(workflow_id):
    """Execute workflow"""
    try:
        data = request.json
        exec_id = orchestrator.execute_workflow(
            workflow_id,
            context=data.get('context', {})
        )
        return jsonify({'execution_id': exec_id, 'success': True}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/workflows/executions/<int:exec_id>', methods=['GET'])
def get_workflow_status(exec_id):
    """Get workflow execution status"""
    try:
        status = orchestrator.get_workflow_status(exec_id)
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# === SEARCH ===

@app.route('/api/search', methods=['GET'])
def search():
    """Search across SOPs"""
    try:
        query = request.args.get('q', '')

        cursor = sop_manager.conn.cursor()
        cursor.execute('''
            SELECT id, sop_code, sop_title, description, status
            FROM sops
            WHERE sop_code LIKE ? OR sop_title LIKE ? OR description LIKE ?
            ORDER BY sop_code
            LIMIT 50
        ''', (f'%{query}%', f'%{query}%', f'%{query}%'))

        results = [dict(row) for row in cursor.fetchall()]
        return jsonify({'results': results})
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
    """Run API server"""
    print("=" * 70)
    print("Business Process Management API Server")
    print("=" * 70)

    print("\nInitializing systems...")
    init_systems()

    print("✓ SOP Manager")
    print("✓ Process Automation")
    print("✓ Process Mining")
    print("✓ BI Dashboard")
    print("✓ Workflow Orchestrator")

    print("\n" + "=" * 70)
    print("API Server running on http://localhost:5000")
    print("=" * 70)
    print("\nAPI Endpoints:")
    print("  GET  /api/health              - Health check")
    print("  GET  /api/dashboard/overview  - Business overview")
    print("  GET  /api/sops                - List SOPs")
    print("  POST /api/sops                - Create SOP")
    print("  GET  /api/workflows           - List workflows")
    print("  POST /api/automation/execute  - Execute SOP")
    print("\nPress Ctrl+C to stop")
    print("=" * 70 + "\n")

    app.run(host='0.0.0.0', port=5000, debug=True)


if __name__ == "__main__":
    main()
