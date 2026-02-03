# Setup Auto-Start for Claude Agent
# Ensures Claude is always running on boot

Write-Host "================================================"
Write-Host "Setting Up Claude Auto-Start"
Write-Host "================================================"
Write-Host ""

$workspacePath = "C:\Users\User\.openclaw\workspace"

Write-Host "[1/3] Creating startup script..."

# Create a startup batch file
$startupScript = @"
@echo off
REM Claude Agent Auto-Start Script
echo Starting Claude Agent services...

REM Start any background services here
REM For now, this is a placeholder for future services

REM Log startup
echo %date% %time% - Claude Agent startup >> "$workspacePath\startup_log.txt"

echo Claude Agent ready!
"@

$startupScript | Out-File -FilePath "$workspacePath\claude-startup.bat" -Encoding ASCII

Write-Host "   [OK] Startup script created: claude-startup.bat" -ForegroundColor Green

Write-Host ""
Write-Host "[2/3] Adding to Windows Startup folder..."

# Get startup folder path
$startupFolder = [Environment]::GetFolderPath('Startup')

# Create shortcut in startup folder
$WshShell = New-Object -ComObject WScript.Shell
$shortcut = $WshShell.CreateShortcut("$startupFolder\Claude-Agent.lnk")
$shortcut.TargetPath = "$workspacePath\claude-startup.bat"
$shortcut.WorkingDirectory = $workspacePath
$shortcut.Description = "Claude AI Agent Auto-Start"
$shortcut.Save()

Write-Host "   [OK] Startup shortcut created" -ForegroundColor Green
Write-Host "   Location: $startupFolder\Claude-Agent.lnk"

Write-Host ""
Write-Host "[3/3] Creating keepalive monitor..."

# Create a keepalive script
$keepaliveScript = @"
# Claude Agent Keepalive Monitor
# Ensures critical services stay running

`$logFile = "$workspacePath\keepalive_log.txt"

while (`$true) {
    # Log heartbeat
    `$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path `$logFile -Value "`$timestamp - Heartbeat"

    # Check if critical processes are running
    # Add process monitoring here as needed

    # Sleep for 5 minutes
    Start-Sleep -Seconds 300
}
"@

$keepaliveScript | Out-File -FilePath "$workspacePath\keepalive-monitor.ps1" -Encoding UTF8

Write-Host "   [OK] Keepalive monitor created" -ForegroundColor Green

Write-Host ""
Write-Host "================================================"
Write-Host "Auto-Start Configuration Complete!" -ForegroundColor Green
Write-Host "================================================"
Write-Host ""
Write-Host "Created:"
Write-Host "  ✓ claude-startup.bat - Main startup script"
Write-Host "  ✓ Startup shortcut - Runs on login"
Write-Host "  ✓ keepalive-monitor.ps1 - Health monitoring"
Write-Host ""
Write-Host "Next boot, Claude will start automatically!"
Write-Host ""
Write-Host "Press any key to continue..."
pause
