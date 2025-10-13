@echo off
echo =======================================
echo   EXPERIMENT MONITOR
echo =======================================
echo.
echo Monitoring Docker container logs...
echo Press Ctrl+C to stop monitoring
echo.
timeout /t 2 /nobreak >nul

:loop
docker logs --tail 50 fp-tree-synthetic 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Waiting for container to start...
    timeout /t 3 /nobreak >nul
    goto loop
)

REM Follow logs in real-time
docker logs -f fp-tree-synthetic
