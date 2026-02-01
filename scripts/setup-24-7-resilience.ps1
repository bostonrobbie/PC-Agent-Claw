# OpenClaw 24/7 Resilience Setup Script
# Run this script as Administrator to complete the setup

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "   OpenClaw 24/7 Gateway Resilience Setup" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

$OpenClawDir = "C:\Users\User\Documents\AI\OpenClaw"
$PM2Path = "$env:APPDATA\npm\pm2.cmd"

# Step 1: Create Wake Restart Scheduled Task
Write-Host "[1/3] Creating scheduled task for system wake..." -ForegroundColor Yellow
try {
    # Remove existing task if present
    Unregister-ScheduledTask -TaskName "OpenClaw Gateway Wake Restart" -Confirm:$false -ErrorAction SilentlyContinue
    
    $action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$OpenClawDir\scripts\restart-on-wake.ps1`""
    
    # Create a trigger for system startup
    $triggerStartup = New-ScheduledTaskTrigger -AtStartup
    
    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType S4U -RunLevel Limited
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
    
    Register-ScheduledTask -TaskName "OpenClaw Gateway Wake Restart" -Action $action -Trigger $triggerStartup -Principal $principal -Settings $settings -Description "Restarts OpenClaw gateway when system starts or wakes from sleep" -Force | Out-Null
    
    Write-Host "  + Scheduled task created successfully" -ForegroundColor Green
}
catch {
    Write-Host "  - Failed to create scheduled task: $_" -ForegroundColor Red
}

# Step 2: Configure Network Adapter Power Settings
Write-Host "[2/3] Configuring network adapter power settings..." -ForegroundColor Yellow
try {
    $adapters = Get-NetAdapter | Where-Object { $_.Status -eq 'Up' }
    foreach ($adapter in $adapters) {
        $pnpDevice = Get-PnpDevice | Where-Object { $_.FriendlyName -eq $adapter.InterfaceDescription }
        if ($pnpDevice) {
            # Try to disable power management for the adapter
            $deviceId = $pnpDevice.InstanceId
            $key = "HKLM:\SYSTEM\CurrentControlSet\Control\Class\{4d36e972-e325-11ce-bfc1-08002be10318}"
            $subkeys = Get-ChildItem $key -ErrorAction SilentlyContinue
            foreach ($subkey in $subkeys) {
                $props = Get-ItemProperty $subkey.PSPath -ErrorAction SilentlyContinue
                if ($props.DriverDesc -eq $adapter.InterfaceDescription) {
                    Set-ItemProperty $subkey.PSPath -Name "PnPCapabilities" -Value 24 -Type DWord -Force -ErrorAction SilentlyContinue
                    Write-Host "  + Disabled power saving for: $($adapter.Name)" -ForegroundColor Green
                }
            }
        }
    }
}
catch {
    Write-Host "  - Could not configure all adapters: $_" -ForegroundColor Yellow
    Write-Host "    You may need to manually disable 'Allow the computer to turn off this device to save power'" -ForegroundColor Yellow
}

# Step 3: Setup PM2 Windows Service
Write-Host "[3/3] Setting up PM2 Windows service..." -ForegroundColor Yellow
try {
    if (Test-Path $PM2Path) {
        # Install pm2-windows-service if not present
        $pm2Service = Get-Service pm2.exe -ErrorAction SilentlyContinue
        if (-not $pm2Service) {
            Write-Host "  Installing pm2-windows-service..." -ForegroundColor Cyan
            npm install -g pm2-windows-service 2>&1 | Out-Null
            
            # Configure and install the service
            Write-Host "  Configuring PM2 service..." -ForegroundColor Cyan
            pm2-service-install -n PM2 2>&1 | Out-Null
        }
        Write-Host "  + PM2 service configured" -ForegroundColor Green
    }
    else {
        Write-Host "  - PM2 not found at expected path" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "  - PM2 service setup failed: $_" -ForegroundColor Yellow
    Write-Host "    PM2 will still work, but won't auto-start as a Windows service" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "                Setup Complete!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps to start using PM2:" -ForegroundColor Yellow
Write-Host "  1. Stop any running gateway process"
Write-Host "  2. Run: cd $OpenClawDir"
Write-Host "  3. Run: pm2 start ecosystem.config.js"
Write-Host "  4. Run: pm2 save"
Write-Host "  5. (Optional) Run: pm2 startup"
Write-Host ""
Read-Host "Press Enter to exit"
