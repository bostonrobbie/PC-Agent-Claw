# Setup Scheduled Tasks for Claude Agent
# This creates automated tasks that run without manual intervention

Write-Host "============================================================"
Write-Host "Setting Up Scheduled Tasks for Claude Agent"
Write-Host "============================================================"
Write-Host ""

$workspacePath = "C:\Users\User\.openclaw\workspace"

# Task 1: Daily Backup at 2 AM
Write-Host "[1/3] Creating daily backup task (2 AM)..."
$action = New-ScheduledTaskAction -Execute "$workspacePath\daily_backup_automation.bat"
$trigger = New-ScheduledTaskTrigger -Daily -At 2:00AM
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -LogonType Interactive
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

Register-ScheduledTask -TaskName "Claude_DailyBackup" `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Description "Automated daily backup for Claude AI Agent" `
    -Force

Write-Host "   [OK] Daily backup task created"
Write-Host ""

# Task 2: Weekly Summary Report (Monday 9 AM)
Write-Host "[2/3] Creating weekly summary task (Monday 9 AM)..."
$action2 = New-ScheduledTaskAction -Execute "C:\Python314\python.exe" -Argument "$workspacePath\weekly_summary.py"
$trigger2 = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 9:00AM

Register-ScheduledTask -TaskName "Claude_WeeklySummary" `
    -Action $action2 `
    -Trigger $trigger2 `
    -Principal $principal `
    -Settings $settings `
    -Description "Weekly summary report for Claude AI Agent" `
    -Force

Write-Host "   [OK] Weekly summary task created"
Write-Host ""

# Task 3: Memory Consolidation (Daily 3 AM)
Write-Host "[3/3] Creating memory consolidation task (3 AM)..."
$action3 = New-ScheduledTaskAction -Execute "C:\Python314\python.exe" -Argument "$workspacePath\memory\consolidate_learnings.py"
$trigger3 = New-ScheduledTaskTrigger -Daily -At 3:00AM

Register-ScheduledTask -TaskName "Claude_MemoryConsolidation" `
    -Action $action3 `
    -Trigger $trigger3 `
    -Principal $principal `
    -Settings $settings `
    -Description "Consolidate and organize learnings for Claude AI Agent" `
    -Force

Write-Host "   [OK] Memory consolidation task created"
Write-Host ""

Write-Host "============================================================"
Write-Host "Scheduled Tasks Created Successfully"
Write-Host "============================================================"
Write-Host ""
Write-Host "Tasks will run automatically:"
Write-Host "  - Daily Backup: Every day at 2:00 AM"
Write-Host "  - Weekly Summary: Every Monday at 9:00 AM"
Write-Host "  - Memory Consolidation: Every day at 3:00 AM"
Write-Host ""
Write-Host "You can view/manage these in Task Scheduler"
Write-Host ""
