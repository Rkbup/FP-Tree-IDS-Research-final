@echo off
setlocal
echo =======================================
echo   MAXIMUM PERFORMANCE SYNTHETIC RUN
echo =======================================
echo.
echo Using ALL available resources:
echo   - Unlimited CPU cores
echo   - Maximum RAM available
echo   - GPU acceleration (if available)
echo.
pause

REM Check Docker
echo Checking Docker...
docker info >nul 2>&1
if not ERRORLEVEL 1 goto build_image

echo ERROR: Docker not running!
echo Starting Docker Desktop...
start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
echo Waiting for Docker to start (30 seconds)...
timeout /t 30 /nobreak

REM Check again
docker info >nul 2>&1
if ERRORLEVEL 1 (
    echo Docker failed to start! Please start Docker Desktop manually.
    pause
    exit /b 1
)
echo Docker is running.

:build_image

echo Pulling latest base image...
docker pull python:3.11-slim
if ERRORLEVEL 1 (
    echo Failed to pull base image!
    pause
    exit /b 1
)

REM Build image
echo Building Docker image...
docker build -t fp-tree-ids:latest .
if ERRORLEVEL 1 (
    echo Build failed!
    pause
    exit /b 1
)

REM Create results directory
if not exist "results" mkdir "results"
if not exist "results\figures" mkdir "results\figures"
if not exist "results\tables" mkdir "results\tables"

echo.
echo =======================================
echo   SYNTHETIC DATASET EXPERIMENT
echo   (Maximum Performance Mode)
echo =======================================
echo.

REM Synthetic experiment script is pre-baked in repository
echo Using experiments\synthetic_run_max.py inside the container.

REM Stop any existing container
docker ps -q --filter "name=fp-tree-synthetic" | findstr /r "." > nul
if not ERRORLEVEL 1 (
    echo Stopping existing container...
    docker stop fp-tree-synthetic
)

REM Run with MAXIMUM resources
echo.
echo Running with maximum available resources...
echo.

docker run --name fp-tree-synthetic --rm ^
    -v "%CD%\data:/app/data" ^
    -v "%CD%\results:/app/results" ^
    -e PYTHONPATH=/app ^
    fp-tree-ids:latest ^
    python /app/experiments/synthetic_run_max.py

if not ERRORLEVEL 1 (
    echo.
    echo =======================================
    echo   SUCCESS!
    echo =======================================
    echo.
    
    if exist "results_synthetic_data" rmdir /s /q "results_synthetic_data"
    mkdir "results_synthetic_data"
    xcopy /E /I /Y "results\*" "results_synthetic_data\" >nul
    echo Results saved to: results_synthetic_data\
    echo.
    echo You can view the results in:
    echo   - results_synthetic_data\tables\performance_synthetic.csv
    echo   - results_synthetic_data\figures\throughput_latency_synthetic.png
) else (
    echo.
    echo =======================================
    echo   EXPERIMENT FAILED OR INTERRUPTED
    echo =======================================
    pause
    exit /b 1
)

echo.
endlocal
echo Press any key to exit...
pause >nul
