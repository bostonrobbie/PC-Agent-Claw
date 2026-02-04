# OpenClaw Smart Watchdog
# Checks for crashes (Port Closed) AND Zombies (Log Stale)
# Run invisible in background

$LogPath = "C:\tmp\openclaw"
$GatewayDir = "C:\Users\User\Documents\AI\OpenClaw"
$Port = 18789
$StaleThresholdMinutes = 60
$CheckIntervalSeconds = 120

function Write-Log {
    param($Message)
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogMsg = "[$Timestamp] WD: $Message"
    Write-Host $LogMsg
    Add-Content -Path "$LogPath\watchdog.log" -Value $LogMsg
}

Write-Log "Smart Watchdog Started. Threshold: $StaleThresholdMinutes mins."

while ($true) {
    try {
        # 1. Check if Port is Open (Crash Detection)
        $PortOpen = $false
        try {
            # Use netstat for broader compatibility than Get-NetTCPConnection on some Windows environments
            $Netstat = netstat -an | Select-String ":$Port"
            if ($Netstat) { $PortOpen = $true }
        }
        catch {
            Write-Log "Error checking port: $_"
        }

        # 2. Check HTTP Health (Zombie Detection)
        # Prefer HTTP over log freshness because logs can stop while process works
        $IsZombie = $false
        if ($PortOpen) {
            try {
                # Check Localhost first
                $Response = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/api/health" -TimeoutSec 10 -UseBasicParsing -ErrorAction Stop
                Write-Log "API Health Check OK (Status: $($Response.StatusCode))"
            }
            catch {
                try {
                    # If localhost fails (e.g. bound to specific IP), try 100.123.64.78
                    $Response = Invoke-WebRequest -Uri "http://100.123.64.78:$Port/api/health" -TimeoutSec 10 -UseBasicParsing -ErrorAction Stop
                    Write-Log "API Health Check (Tailscale) OK (Status: $($Response.StatusCode))"
                }
                catch {
                    Write-Log "ZOMBIE DETECTED! Port open but /api/health failed: $_"
                    $IsZombie = $true
                }
            }
        }
        else {
            Write-Log "CRASH DETECTED! Port $Port is not listening."
        }

        # 3. Restart Action
        if (-not $PortOpen -or $IsZombie) {
            Write-Log "Restarting Gateway..."
            
            # Kill any lingering node processes if Zombie
            if ($IsZombie) {
                Stop-Process -Name node -Force -ErrorAction SilentlyContinue
                Start-Sleep -Seconds 2
            }

            # Restart logic continues below...

            # Start Gateway
            Start-Process -FilePath "cmd" -ArgumentList "/c cd /d $GatewayDir && npx openclaw gateway" -WindowStyle Minimized
            
            Write-Log "Gateway restart command issued."
            
            # Wait a bit longer after restart to let it initialize
            Start-Sleep -Seconds 30
        }

    }
    catch {
        Write-Log "Watchdog Loop Error: $_"
    }

    Start-Sleep -Seconds $CheckIntervalSeconds
}
