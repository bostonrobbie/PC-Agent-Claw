#!/usr/bin/env python3
"""
Test all business process management systems
"""
import sys
from pathlib import Path

workspace = Path(__file__).parent
sys.path.insert(0, str(workspace))


def test_sop_manager():
    """Test SOP management system"""
    print("\n[1/5] Testing SOP Manager...")
    try:
        from business.sop_manager import SOPManager

        manager = SOPManager()

        # Get or create business function
        cursor = manager.conn.cursor()
        cursor.execute('SELECT id FROM business_functions WHERE function_name = "Operations"')
        result = cursor.fetchone()

        if result:
            function_id = result['id']
        else:
            function_id = manager.create_function("Operations", "Operational processes")

        # Create role
        role_id = manager.create_role("Test Operator", function_id)

        # Create SOP with unique code
        import time
        sop_code = f"SOP-TEST-{int(time.time())}"
        sop_id = manager.create_sop(
            sop_code,
            "Test Process",
            function_id,
            description="Test SOP for validation",
            purpose="Testing"
        )

        # Add steps
        step1 = manager.add_step(
            sop_id,
            1,
            "Initialize",
            "Set up environment",
            step_type="manual"
        )

        step2 = manager.add_step(
            sop_id,
            2,
            "Execute",
            "Run the process",
            step_type="automated"
        )

        # Start execution
        exec_id = manager.start_execution(sop_id, "test_user")

        # Complete steps
        manager.complete_step(exec_id, 1, result="Step 1 complete")
        manager.complete_step(exec_id, 2, result="Step 2 complete")

        # Complete execution
        manager.complete_execution(exec_id, success=True)

        # Get metrics
        metrics = manager.get_sop_metrics(sop_id)

        manager.close()

        print(f"   SOP ID: {sop_id}, Executions: {metrics['total_executions']}")
        print("   [OK] SOP Manager working")
        return True

    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_process_automation():
    """Test process automation engine"""
    print("\n[2/5] Testing Process Automation...")
    try:
        from business.process_automation import ProcessAutomation

        automation = ProcessAutomation()

        # Register handler
        def test_handler(step, context):
            return {'success': True, 'result': 'Automated execution'}

        automation.register_automation('test_type', test_handler)

        # Get automation stats
        stats = automation.get_automation_status()

        automation.close()

        print(f"   Automation rate: {stats['automation_rate']:.0%}")
        print("   [OK] Process Automation working")
        return True

    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_process_mining():
    """Test process mining"""
    print("\n[3/5] Testing Process Mining...")
    try:
        from business.process_mining import ProcessMining

        mining = ProcessMining()

        # System ready (needs execution data)
        print("   Process mining system initialized")

        mining.close()

        print("   [OK] Process Mining working")
        return True

    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_bi_dashboard():
    """Test BI dashboard"""
    print("\n[4/5] Testing BI Dashboard...")
    try:
        from business.bi_dashboard import BIDashboard

        dashboard = BIDashboard()

        # Get overview
        overview = dashboard.get_business_overview()

        # Get performance
        performance = dashboard.get_sop_performance(days=30)

        # Get trends
        trends = dashboard.get_execution_trends(days=7)

        # Get efficiency
        efficiency = dashboard.get_efficiency_report()

        dashboard.close()

        print(f"   Total SOPs: {overview['total_sops']}")
        print(f"   Success Rate: {overview['success_rate']:.0%}")
        print("   [OK] BI Dashboard working")
        return True

    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_workflow_orchestrator():
    """Test workflow orchestrator"""
    print("\n[5/5] Testing Workflow Orchestrator...")
    try:
        from business.workflow_orchestrator import WorkflowOrchestrator

        orchestrator = WorkflowOrchestrator()

        # Create workflow
        workflow_id = orchestrator.create_workflow(
            "Test Workflow",
            "Test sequential workflow",
            workflow_type="sequential"
        )

        # Add nodes
        node1 = orchestrator.add_node(workflow_id, "Start", node_type='sop')
        node2 = orchestrator.add_node(workflow_id, "Process", node_type='sop')
        node3 = orchestrator.add_node(workflow_id, "End", node_type='sop')

        # Connect
        orchestrator.connect_nodes(workflow_id, node1, node2, condition_type='always')
        orchestrator.connect_nodes(workflow_id, node2, node3, condition_type='always')

        # Execute
        exec_id = orchestrator.execute_workflow(workflow_id, context={'test': True})

        # Get status
        status = orchestrator.get_workflow_status(exec_id)

        orchestrator.close()

        print(f"   Workflow ID: {workflow_id}")
        print(f"   Status: {status['status']}")
        print(f"   Nodes executed: {len(status['node_executions'])}")
        print("   [OK] Workflow Orchestrator working")
        return True

    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_integration():
    """Test integration between systems"""
    print("\n[INTEGRATION] Testing system integration...")
    try:
        from business.sop_manager import SOPManager
        from business.process_automation import ProcessAutomation
        from business.bi_dashboard import BIDashboard

        # Create SOP
        sop_manager = SOPManager()
        function_id = sop_manager.create_function("Integration Test", "Test function")
        sop_id = sop_manager.create_sop("SOP-INT-001", "Integration SOP", function_id)

        step_id = sop_manager.add_step(sop_id, 1, "Test Step", "Description", step_type="automated")

        # Execute via automation
        automation = ProcessAutomation()
        result = automation.execute_sop(sop_id, context={'test': True})

        # View in dashboard
        dashboard = BIDashboard()
        overview = dashboard.get_business_overview()
        performance = dashboard.get_sop_performance(sop_id=sop_id)

        sop_manager.close()
        automation.close()
        dashboard.close()

        print(f"   SOP created and executed")
        print(f"   Dashboard overview: {overview['total_sops']} SOPs")
        print("   [OK] Integration working")
        return True

    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("=" * 70)
    print("TESTING BUSINESS PROCESS MANAGEMENT SYSTEMS")
    print("=" * 70)

    results = []

    # Test individual systems
    results.append(("SOP Manager", test_sop_manager()))
    results.append(("Process Automation", test_process_automation()))
    results.append(("Process Mining", test_process_mining()))
    results.append(("BI Dashboard", test_bi_dashboard()))
    results.append(("Workflow Orchestrator", test_workflow_orchestrator()))

    # Test integration
    results.append(("System Integration", test_integration()))

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "[OK]" if result else "[FAIL]"
        print(f"{status} {name}")

    print(f"\nPassed: {passed}/{total}")

    if passed == total:
        print("\n[SUCCESS] All business systems operational!")
        return 0
    else:
        print(f"\n[WARNING] {total - passed} system(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
