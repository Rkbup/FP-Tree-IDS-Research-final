@echo off
echo =======================================
echo   ROBUST EXPERIMENT RUNNER
echo =======================================
echo.
echo Features:
echo   - More reliable checkpointing system
echo   - Better error handling
echo   - Memory optimization
echo   - Run single algorithm at a time
echo.
pause

REM Check Docker
echo Checking Docker...
docker info >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Docker not running!
    echo Starting Docker Desktop...
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    echo Waiting for Docker to start (30 seconds)...
    timeout /t 30 /nobreak
    
    REM Check again
    docker info >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo Docker failed to start! Please start Docker Desktop manually.
        pause
        exit /b 1
    ) else {
        echo Docker started successfully.
    }
)

REM Build image
echo Building Docker image...
docker build -t fp-tree-ids:latest .
if %ERRORLEVEL% NEQ 0 (
    echo Build failed!
    pause
    exit /b 1
)

REM Extract dataset
if exist "data\raw\MachineLearningCSV.zip" (
    if not exist "data\raw\MachineLearningCVE" (
        echo Extracting dataset...
        powershell -Command "Expand-Archive -Path 'data\raw\MachineLearningCSV.zip' -DestinationPath 'data\raw' -Force"
    )
)

REM Create checkpoints directory
if not exist "checkpoints" mkdir "checkpoints"

echo.
echo =======================================
echo   EXPERIMENT MENU
echo =======================================
echo.
echo Choose algorithm to run:
echo.
echo 1. NoReorderFPTree (NR)
echo 2. PartialRebuildFPTree (PR)
echo 3. TwoTreeFPTree (TT)
echo 4. DecayHybridFPTree (DH)
echo 5. HalfSpaceTrees (HS-Trees)
echo 6. RandomCutForest (RCF)
echo 7. OnlineAutoencoder (Autoencoder)
echo 8. All algorithms (may take very long)
echo.

set /p algo_choice="Enter choice (1-8): "

set algo=
if "%algo_choice%"=="1" set algo=NR
if "%algo_choice%"=="2" set algo=PR
if "%algo_choice%"=="3" set algo=TT
if "%algo_choice%"=="4" set algo=DH
if "%algo_choice%"=="5" set algo=HS-Trees
if "%algo_choice%"=="6" set algo=RCF
if "%algo_choice%"=="7" set algo=Autoencoder
if "%algo_choice%"=="8" set algo=all

if "%algo%"=="" (
    echo Invalid choice!
    pause
    exit /b 1
)

echo.
echo Running experiment with algorithm: %algo%
echo.

REM Make sure container is stopped if running
docker ps -q --filter "name=fp-tree-experiment" | findstr /r "." > nul
if %ERRORLEVEL% EQU 0 (
    echo Stopping existing container...
    docker stop fp-tree-experiment
)

REM Run with checkpointing and resume support
docker run --name fp-tree-experiment --rm ^
    --cpus="0.000" ^
    --memory="16g" ^
    -v "%CD%\data:/app/data" ^
    -v "%CD%\results:/app/results" ^
    -v "%CD%\checkpoints:/app/checkpoints" ^
    -e PYTHONPATH=/app ^
    fp-tree-ids:latest ^
    python /app/experiments/resume_experiment.py --resume --algorithm %algo%

if %ERRORLEVEL% EQ 0 (
    echo.
    echo =======================================
    echo   SUCCESS!
    echo =======================================
    
    if exist "results_algo_%algo%" rmdir /s /q "results_algo_%algo%"
    mkdir "results_algo_%algo%"
    xcopy /E /I /Y "results\*" "results_algo_%algo%" >nul
    echo Results saved to: results_algo_%algo%\
) else (
    echo.
    echo Process was interrupted or failed.
    echo Your progress is saved in checkpoints\
    echo Run this script again to resume!
    pause
    exit /b 1
)

echo.
echo Press any key to exit...
pause >nul