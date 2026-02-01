# OpenClaw Gateway Restart on Wake Script
# This script is triggered by Windows Task Scheduler when the system wakes from sleep
# It restarts the PM2-managed gateway to ensure connectivity is refreshed

param(
    [switch]$Force
)

$LogFile = "$env:USERPROFILE\.openclaw\logs\wake-restart.log"
$PM2Path = (Get-Command pm2 -ErrorAction SilentlyContinue).Source

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp - $Message" | Out-File -Append -FilePath $LogFile
    Write-Host $Message
}

# Ensure log directory exists
$logDir = Split-Path $LogFile
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

Write-Log "System wake detected - checking OpenClaw gateway..."

# Wait for network to be available (up to 30 seconds)
$maxWait = 30
$waited = 0
while ($waited -lt $maxWait) {
    try {
        $null = Test-NetConnection -ComputerName "api.telegram.org" -Port 443 -InformationLevel Quiet -WarningAction SilentlyContinue
        if ($?) {
            Write-Log "Network connectivity verified after ${waited}s"
            break
        }
    } catch {
        # Ignore errors
    }
    Start-Sleep -Seconds 2
    $waited += 2
}

if ($waited -ge $maxWait) {
    Write-Log "WARNING: Network not available after ${maxWait}s, proceeding anyway"
}

# Check if PM2 is available
if (-not $PM2Path) {
    Write-Log "PM2 not found in PATH, trying npm global path..."
    $PM2Path = "$env:APPDATA\npm\pm2.cmd"
    if (-not (Test-Path $PM2Path)) {
        Write-Log "ERROR: PM2 not found. Install with: npm install -g pm2"
        exit 1
    }
}

# Restart the gateway through PM2
try {
    Write-Log "Restarting openclaw-gateway via PM2..."
    & $PM2Path restart openclaw-gateway --update-env 2>&1 | Out-String | ForEach-Object { Write-Log $_ }
    
    # Give it a moment to start
    Start-Sleep -Seconds 3
    
    # Check status
    $status = & $PM2Path jlist 2>&1 | ConvertFrom-Json
    $gateway = $status | Where-Object { $_.name -eq 'openclaw-gateway' }
    
    if ($gateway -and $gateway.pm2_env.status -eq 'online') {
        Write-Log "SUCCESS: Gateway restarted and online"
    } else {
        Write-Log "WARNING: Gateway restart completed but status unclear"
    }
} catch {
    Write-Log "ERROR: Failed to restart gateway: $_"
    exit 1
}

Write-Log "Wake restart script completed"
