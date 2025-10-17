@echo off
echo ========================================
echo FP-Tree IDS - Docker Desktop Launcher
echo ========================================
echo.

echo Starting Docker Desktop...
start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"

echo.
echo Waiting 60 seconds for Docker to initialize...
timeout /t 60 /nobreak

echo.
echo Docker Desktop should be ready now!
echo.
echo Next steps:
echo   1. Check Docker icon in system tray (should be green)
echo   2. Run: .\fresh_start.ps1
echo.
pause
