@echo off
echo ============================================================
echo GitHub Authentication Helper
echo ============================================================
echo.
echo This will authenticate GitHub CLI with your account.
echo.
echo You'll be asked to:
echo 1. Choose authentication method (web browser recommended)
echo 2. Login via GitHub.com
echo 3. Authorize GitHub CLI
echo.
echo Press any key to start authentication...
pause >nul

"C:\Program Files\GitHub CLI\gh.exe" auth login

echo.
echo ============================================================
echo Authentication complete!
echo ============================================================
echo.
echo Now Claude can create repositories and push code.
echo.
pause
