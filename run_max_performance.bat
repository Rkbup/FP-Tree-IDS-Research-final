@echo off
setlocal EnableDelayedExpansion

echo =======================================
echo   MAXIMUM PERFORMANCE EXPERIMENT RUNNER
echo =======================================
echo.
echo This will use ALL your PC resources!
echo - All CPU cores
echo - Maximum available RAM
echo - High priority process
echo.
pause

REM Check Docker
echo Checking Docker...
docker info >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Docker is not running!
    echo Please start Docker Desktop and try again.
    pause
    exit /b 1
)
echo Docker is running!
echo.

REM Stop any running containers
echo Stopping any existing containers...
for /f "tokens=*" %%i in ('docker ps -q') do docker stop %%i
echo.

REM Build with maximum resources
echo Building Docker image with maximum performance settings...
docker build --rm --no-cache -t fp-tree-ids:latest .
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Docker build failed!
    pause
    exit /b 1
)
echo Image built successfully!
echo.

REM Get system info
echo Detecting system resources...
for /f "tokens=2 delims==" %%i in ('wmic cpu get NumberOfLogicalProcessors /value ^| find "="') do set CPUS=%%i
for /f "tokens=2 delims==" %%i in ('wmic OS get TotalVisibleMemorySize /value ^| find "="') do set MEMORY_KB=%%i
set /a MEMORY_GB=%MEMORY_KB% / 1048576
set /a DOCKER_MEMORY=%MEMORY_GB% - 2
if %DOCKER_MEMORY% LSS 4 set DOCKER_MEMORY=4

echo.
echo System Resources:
echo   CPU Cores: %CPUS%
echo   Total RAM: %MEMORY_GB% GB
echo   Allocating to Docker: %DOCKER_MEMORY% GB
echo.

REM Extract dataset
if exist "data\raw\MachineLearningCSV.zip" (
    if not exist "data\raw\MachineLearningCVE" (
        echo Extracting dataset...
        powershell -Command "Expand-Archive -Path 'data\raw\MachineLearningCSV.zip' -DestinationPath 'data\raw' -Force"
    )
)

REM Clear old results
if exist "results" rmdir /s /q "results" 2>nul

REM ===========================
REM EXPERIMENT 1: Real Dataset
REM ===========================
echo.
echo =======================================
echo   RUNNING REAL DATASET EXPERIMENT
echo =======================================
echo.
echo Starting with MAXIMUM performance...
echo Press Ctrl+C to abort (not recommended)
echo.

REM Run with all available resources
docker run --rm ^
    --cpus="%CPUS%" ^
    --memory="%DOCKER_MEMORY%g" ^
    --memory-swap="%DOCKER_MEMORY%g" ^
    --cpu-shares=1024 ^
    --oom-kill-disable=false ^
    -v "%CD%\data:/app/data" ^
    -v "%CD%\results:/app/results" ^
    -e PYTHONPATH=/app ^
    -e OMP_NUM_THREADS=%CPUS% ^
    -e NUMEXPR_NUM_THREADS=%CPUS% ^
    -e MKL_NUM_THREADS=%CPUS% ^
    fp-tree-ids:latest ^
    python experiments/main_experiment.py

if %ERRORLEVEL% EQ 0 (
    echo.
    echo =======================================
    echo   REAL DATASET - COMPLETED!
    echo =======================================
    echo.
    
    if exist "results_real_data" rmdir /s /q "results_real_data"
    xcopy /E /I /Y "results" "results_real_data" >nul
    echo Results saved to: results_real_data\
    echo.
    dir /s /b "results_real_data\*.csv" "results_real_data\*.png" 2>nul
) else (
    echo.
    echo ERROR: Real dataset experiment failed!
    pause
    exit /b 1
)

REM Clear results for synthetic
if exist "results" rmdir /s /q "results" 2>nul

REM ==============================
REM EXPERIMENT 2: Synthetic Dataset
REM ==============================
echo.
echo =======================================
echo   RUNNING SYNTHETIC DATASET EXPERIMENT
echo =======================================
echo.

REM Create optimized synthetic script
(
echo import sys, os
echo sys.path.insert(0, "/app"^)
echo os.environ['OMP_NUM_THREADS'] = '%CPUS%'
echo os.environ['NUMEXPR_NUM_THREADS'] = '%CPUS%'
echo os.environ['MKL_NUM_THREADS'] = '%CPUS%'
echo.
echo import pandas as pd
echo import numpy as np
echo from pathlib import Path
echo from src.preprocessing.feature_engineering import FeatureEngineer
echo from src.preprocessing.transaction_builder import TransactionBuilder
echo from experiments.main_experiment import evaluate_streaming_performance
echo from src.algorithms.variants.no_reorder import NoReorderFPTree
echo from src.algorithms.variants.partial_rebuild import PartialRebuildFPTree
echo from src.algorithms.variants.two_tree import TwoTreeFPTree
echo from src.algorithms.variants.decay_hybrid import DecayHybridFPTree
echo from src.algorithms.baselines.half_space_trees import HalfSpaceTrees
echo from src.algorithms.baselines.random_cut_forest import RandomCutForest
echo from src.algorithms.baselines.online_autoencoder import OnlineAutoencoder
echo from src.evaluation.visualization import plot_throughput_latency
echo.
echo print("Loading synthetic dataset..."^)
echo data = pd.read_csv("/app/data/raw/synthetic_cic_ids2017.csv"^)
echo print(f"Loaded {len(data^)} rows"^)
echo.
echo Path('/app/results/figures'^).mkdir(parents=True, exist_ok=True^)
echo Path('/app/results/tables'^).mkdir(parents=True, exist_ok=True^)
echo.
echo labels = (data['Label'] != 'BENIGN'^).astype(int^).to_numpy(^)
echo fe = FeatureEngineer(n_bins=5^)
echo selected = fe.select_features(data^)
echo discretised = fe.discretize_continuous_features(selected^)
echo tb = TransactionBuilder(^)
echo transactions = tb.build_transactions(discretised^)
echo.
echo algorithms = {
echo     'NR': NoReorderFPTree(min_support=0.005, window_size=2000^),
echo     'PR': PartialRebuildFPTree(min_support=0.005, window_size=2000, rebuild_threshold=0.1^),
echo     'TT': TwoTreeFPTree(min_support=0.005, half_window_size=1000^),
echo     'DH': DecayHybridFPTree(min_support=0.005, window_size=2000, decay_factor=0.995^),
echo     'HS-Trees': HalfSpaceTrees(n_trees=25, tree_depth=15^),
echo     'RCF': RandomCutForest(n_trees=100, sample_size=256^),
echo     'Autoencoder': OnlineAutoencoder(encoding_dim=0.5^)
echo }
echo.
echo results = evaluate_streaming_performance(algorithms=algorithms, transactions=transactions, labels=labels, window_size=2000, anomaly_threshold=0.5^)
echo.
echo results_df = pd.DataFrame.from_dict(results, orient='index'^)
echo results_df.to_csv('/app/results/tables/performance.csv'^)
echo plot_throughput_latency({name: {'throughput': m['throughput'], 'latency': m['latency']} for name, m in results.items(^)}, '/app/results/figures/throughput_latency.png'^)
echo print("Synthetic experiment completed!"^)
) > run_synthetic.py

docker run --rm ^
    --cpus="%CPUS%" ^
    --memory="8g" ^
    --cpu-shares=1024 ^
    -v "%CD%\data:/app/data" ^
    -v "%CD%\results:/app/results" ^
    -v "%CD%\run_synthetic.py:/app/run_synthetic.py" ^
    -e PYTHONPATH=/app ^
    -e OMP_NUM_THREADS=%CPUS% ^
    -e NUMEXPR_NUM_THREADS=%CPUS% ^
    fp-tree-ids:latest ^
    python /app/run_synthetic.py

if %ERRORLEVEL% EQ 0 (
    echo.
    echo =======================================
    echo   SYNTHETIC DATASET - COMPLETED!
    echo =======================================
    echo.
    
    if exist "results_synthetic_data" rmdir /s /q "results_synthetic_data"
    xcopy /E /I /Y "results" "results_synthetic_data" >nul
    echo Results saved to: results_synthetic_data\
    echo.
    dir /s /b "results_synthetic_data\*.csv" "results_synthetic_data\*.png" 2>nul
) else (
    echo ERROR: Synthetic experiment failed!
    pause
    exit /b 1
)

del run_synthetic.py 2>nul

echo.
echo =======================================
echo   ALL EXPERIMENTS COMPLETED!
echo =======================================
echo.
echo Results are in:
echo   - results_real_data\
echo   - results_synthetic_data\
echo.
echo Compare performance.csv files to analyze!
echo.
pause
