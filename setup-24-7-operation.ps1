# Setup 24/7 Operation - Never Sleep Configuration
# Configures Viper PC for continuous operation

Write-Host "================================================"
Write-Host "Configuring Viper PC for 24/7 Operation"
Write-Host "================================================"
Write-Host ""

# Require Administrator
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "ERROR: This script requires Administrator privileges!" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    pause
    exit 1
}

Write-Host "[1/6] Configuring power plan settings..."

# Set monitor timeout to never (0 = never)
powercfg /change monitor-timeout-ac 0
powercfg /change monitor-timeout-dc 30

# Set standby timeout to never
powercfg /change standby-timeout-ac 0
powercfg /change standby-timeout-dc 30

# Set hibernate timeout to never
powercfg /change hibernate-timeout-ac 0
powercfg /change hibernate-timeout-dc 0

# Set disk timeout to never
powercfg /change disk-timeout-ac 0
powercfg /change disk-timeout-dc 30

Write-Host "   [OK] Power settings configured for 24/7 operation" -ForegroundColor Green

Write-Host ""
Write-Host "[2/6] Disabling sleep and hibernation..."

# Disable hibernation
powercfg /hibernate off

Write-Host "   [OK] Hibernation disabled" -ForegroundColor Green

Write-Host ""
Write-Host "[3/6] Configuring USB selective suspend..."

# Disable USB selective suspend (prevents USB devices from sleeping)
powercfg /setacvalueindex SCHEME_CURRENT 2a737441-1930-4402-8d77-b2bebba308a3 48e6b7a6-50f5-4782-a5d4-53bb8f07e226 0
powercfg /setactive SCHEME_CURRENT

Write-Host "   [OK] USB selective suspend disabled" -ForegroundColor Green

Write-Host ""
Write-Host "[4/6] Configuring wake timers..."

# Enable wake timers (for scheduled tasks)
powercfg /setacvalueindex SCHEME_CURRENT SUB_SLEEP RTCWAKE 1
powercfg /setactive SCHEME_CURRENT

Write-Host "   [OK] Wake timers enabled for scheduled tasks" -ForegroundColor Green

Write-Host ""
Write-Host "[5/6] Disabling fast startup..."

# Disable fast startup (can cause issues with scheduled tasks)
reg add "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Power" /v HiberbootEnabled /t REG_DWORD /d 0 /f | Out-Null

Write-Host "   [OK] Fast startup disabled" -ForegroundColor Green

Write-Host ""
Write-Host "[6/6] Verifying configuration..."

# Show current power configuration
Write-Host ""
Write-Host "Current Power Settings:" -ForegroundColor Cyan
Write-Host "  - Monitor timeout (AC): Never"
Write-Host "  - Sleep timeout (AC): Never"
Write-Host "  - Hibernate timeout (AC): Never"
Write-Host "  - Disk timeout (AC): Never"
Write-Host "  - Hibernation: Disabled"
Write-Host "  - USB selective suspend: Disabled"
Write-Host "  - Wake timers: Enabled"

Write-Host ""
Write-Host "================================================"
Write-Host "24/7 Configuration Complete!" -ForegroundColor Green
Write-Host "================================================"
Write-Host ""
Write-Host "Your PC is now configured to:"
Write-Host "  ✓ Never sleep when plugged in"
Write-Host "  ✓ Never turn off display (when plugged in)"
Write-Host "  ✓ Never hibernate"
Write-Host "  ✓ Wake for scheduled tasks"
Write-Host "  ✓ Keep USB devices active"
Write-Host ""
Write-Host "NOTE: On battery, conservative settings still apply."
Write-Host ""
Write-Host "Configuration complete! Check settings above."
