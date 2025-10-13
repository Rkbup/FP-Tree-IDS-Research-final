@echo off
echo =======================================
echo   CHECKPOINTING EXPERIMENT RUNNER
echo =======================================
echo.
echo Features:
echo   - Saves progress every 1000 transactions
echo   - Auto-resume if interrupted
echo   - Power failure safe
echo.
pause

REM Check Docker
docker info >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Docker not running!
    pause
    exit /b 1
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
echo   REAL DATASET EXPERIMENT (with checkpointing)
echo =======================================
echo.
echo If interrupted, run this script again to resume!
echo.

REM Run with checkpointing and resume support - MAXIMUM RESOURCES
docker run --rm ^
    -v "%CD%\data:/app/data" ^
    -v "%CD%\results:/app/results" ^
    -v "%CD%\checkpoints:/app/checkpoints" ^
    -e PYTHONPATH=/app ^
    fp-tree-ids:latest ^
    python experiments/main_experiment_with_checkpointing.py --resume

if %ERRORLEVEL% EQ 0 (
    echo.
    echo =======================================
    echo   SUCCESS!
    echo =======================================
    
    if exist "results_real_data" rmdir /s /q "results_real_data"
    xcopy /E /I /Y "results" "results_real_data" >nul
    echo Results saved to: results_real_data\
    
    REM Clear checkpoints after success
    if exist "checkpoints" rmdir /s /q "checkpoints"
    echo Checkpoints cleared.
) else (
    echo.
    echo Process was interrupted or failed.
    echo Your progress is saved in checkpoints\
    echo Run this script again to resume!
    pause
    exit /b 1
)

echo.
echo Press any key to run synthetic dataset experiment...
pause >nul

REM Clear results
if exist "results" rmdir /s /q "results"
if exist "checkpoints" rmdir /s /q "checkpoints"

echo.
echo =======================================
echo   SYNTHETIC DATASET EXPERIMENT
echo =======================================
echo.

REM Create synthetic script
(
echo import sys
echo sys.path.insert(0, "/app"^)
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
echo Path('/app/results/figures'^).mkdir(parents=True, exist_ok=True^)
echo Path('/app/results/tables'^).mkdir(parents=True, exist_ok=True^)
echo labels = (data['Label'] != 'BENIGN'^).astype(int^).to_numpy(^)
echo fe = FeatureEngineer(n_bins=5^)
echo selected = fe.select_features(data^)
echo discretised = fe.discretize_continuous_features(selected^)
echo tb = TransactionBuilder(^)
echo transactions = tb.build_transactions(discretised^)
echo algorithms = {
echo     'NR': NoReorderFPTree(min_support=0.005, window_size=2000^),
echo     'PR': PartialRebuildFPTree(min_support=0.005, window_size=2000, rebuild_threshold=0.1^),
echo     'TT': TwoTreeFPTree(min_support=0.005, half_window_size=1000^),
echo     'DH': DecayHybridFPTree(min_support=0.005, window_size=2000, decay_factor=0.995^),
echo     'HS-Trees': HalfSpaceTrees(n_trees=25, tree_depth=15^),
echo     'RCF': RandomCutForest(n_trees=100, sample_size=256^),
echo     'Autoencoder': OnlineAutoencoder(encoding_dim=0.5^)
echo }
echo results = evaluate_streaming_performance(algorithms=algorithms, transactions=transactions, labels=labels, window_size=2000, anomaly_threshold=0.5^)
echo results_df = pd.DataFrame.from_dict(results, orient='index'^)
echo results_df.to_csv('/app/results/tables/performance.csv'^)
echo plot_throughput_latency({name: {'throughput': m['throughput'], 'latency': m['latency']} for name, m in results.items(^)}, '/app/results/figures/throughput_latency.png'^)
echo print("Synthetic experiment completed!"^)
) > run_synthetic.py

docker run --rm ^
    --cpus="0.000" ^
    --memory="8g" ^
    -v "%CD%\data:/app/data" ^
    -v "%CD%\results:/app/results" ^
    -v "%CD%\run_synthetic.py:/app/run_synthetic.py" ^
    -e PYTHONPATH=/app ^
    fp-tree-ids:latest ^
    python /app/run_synthetic.py

if %ERRORLEVEL% EQ 0 (
    echo.
    echo SUCCESS!
    if exist "results_synthetic_data" rmdir /s /q "results_synthetic_data"
    xcopy /E /I /Y "results" "results_synthetic_data" >nul
    echo Results saved to: results_synthetic_data\
)

del run_synthetic.py 2>nul

echo.
echo =======================================
echo   ALL EXPERIMENTS COMPLETED!
echo =======================================
echo.
echo Results in:
echo   - results_real_data\
echo   - results_synthetic_data\
echo.
pause
