#!/usr/bin/env python3
"""
Simple test for business process management systems
Tests each system in isolation
"""
import sys
from pathlib import Path
import time

workspace = Path(__file__).parent
sys.path.insert(0, str(workspace))


def main():
    """Run tests"""
    print("=" * 70)
    print("BUSINESS PROCESS MANAGEMENT SYSTEMS - SIMPLE TEST")
    print("=" * 70)

    results = []

    # Test 1: SOP Manager
    print("\n[1/5] Testing SOP Manager...")
    try:
        from business.sop_manager import SOPManager

        manager = SOPManager()

        # Get existing function or use default
        cursor = manager.conn.cursor()
        cursor.execute('SELECT id FROM business_functions LIMIT 1')
        result = cursor.fetchone()
        function_id = result['id'] if result else 1

        # Create unique SOP
        sop_code = f"TEST-{int(time.time())}"
        sop_id = manager.create_sop(sop_code, "Test SOP", function_id)

        manager.add_step(sop_id, 1, "Step 1", "Test step", step_type="manual")

        manager.close()

        print(f"   Created SOP: {sop_code}")
        print("   [OK] SOP Manager working")
        results.append(("SOP Manager", True))

    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        results.append(("SOP Manager", False))

    time.sleep(0.5)  # Allow DB to unlock

    # Test 2: Process Automation
    print("\n[2/5] Testing Process Automation...")
    try:
        from business.process_automation import ProcessAutomation

        automation = ProcessAutomation()

        def test_handler(step, context):
            return {'success': True}

        automation.register_automation('test_handler', test_handler)
        stats = automation.get_automation_status()

        automation.close()

        print(f"   Automation rate: {stats['automation_rate']:.0%}")
        print("   [OK] Process Automation working")
        results.append(("Process Automation", True))

    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        results.append(("Process Automation", False))

    time.sleep(0.5)

    # Test 3: Process Mining
    print("\n[3/5] Testing Process Mining...")
    try:
        from business.process_mining import ProcessMining

        mining = ProcessMining()
        mining.close()

        print("   [OK] Process Mining working")
        results.append(("Process Mining", True))

    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        results.append(("Process Mining", False))

    time.sleep(0.5)

    # Test 4: BI Dashboard
    print("\n[4/5] Testing BI Dashboard...")
    try:
        from business.bi_dashboard import BIDashboard

        dashboard = BIDashboard()
        overview = dashboard.get_business_overview()
        dashboard.close()

        print(f"   Total SOPs: {overview['total_sops']}")
        print(f"   Success Rate: {overview['success_rate']:.0%}")
        print("   [OK] BI Dashboard working")
        results.append(("BI Dashboard", True))

    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        results.append(("BI Dashboard", False))

    time.sleep(0.5)

    # Test 5: Workflow Orchestrator
    print("\n[5/5] Testing Workflow Orchestrator...")
    try:
        from business.workflow_orchestrator import WorkflowOrchestrator

        orchestrator = WorkflowOrchestrator()

        workflow_id = orchestrator.create_workflow(
            f"Test-{int(time.time())}",
            "Test workflow",
            workflow_type="sequential"
        )

        node1 = orchestrator.add_node(workflow_id, "Start", node_type='sop')
        node2 = orchestrator.add_node(workflow_id, "End", node_type='sop')
        orchestrator.connect_nodes(workflow_id, node1, node2, condition_type='always')

        exec_id = orchestrator.execute_workflow(workflow_id)
        status = orchestrator.get_workflow_status(exec_id)

        orchestrator.close()

        print(f"   Workflow status: {status['status']}")
        print(f"   Nodes executed: {len(status['node_executions'])}")
        print("   [OK] Workflow Orchestrator working")
        results.append(("Workflow Orchestrator", True))

    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Workflow Orchestrator", False))

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
