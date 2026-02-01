@echo off
REM Daily Automated Backup Script
REM Runs backup system and commits to git

cd "C:\Users\User\.openclaw\workspace"

echo ============================================================
echo Daily Automated Backup - %date% %time%
echo ============================================================
echo.

REM Run Python backup system
echo [1/3] Running backup system...
C:\Python314\python.exe backup_system.py

echo.
echo [2/3] Committing changes to git...
git add -A
git commit -m "Automated daily backup - %date%"

echo.
echo [3/3] Attempting to push to GitHub (if authenticated)...
git push origin master 2>nul
if %errorlevel% neq 0 (
    echo Note: GitHub push skipped - not authenticated yet
) else (
    echo GitHub backup successful!
)

echo.
echo ============================================================
echo Backup Complete
echo ============================================================
echo.

REM Log completion
echo %date% %time% - Daily backup completed >> daily_backup_log.txt
