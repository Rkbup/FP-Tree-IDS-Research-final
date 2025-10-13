@echo off
echo =======================================
echo   FP-Tree IDS Experiment Runner (Docker)
echo =======================================
echo.

REM Check Docker
echo Checking Docker...
docker info >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Docker is not running. Please start Docker Desktop.
    pause
    exit /b 1
)
echo Docker is running!
echo.

REM Build image
echo Building Docker image...
docker build -t fp-tree-ids:latest .
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Docker build failed!
    pause
    exit /b 1
)
echo Docker image built successfully!
echo.

REM Extract dataset
echo Checking dataset...
if exist "data\raw\MachineLearningCSV.zip" (
    if not exist "data\raw\MachineLearningCVE" (
        echo Extracting dataset...
        powershell -Command "Expand-Archive -Path 'data\raw\MachineLearningCSV.zip' -DestinationPath 'data\raw' -Force"
        echo Dataset extracted!
    ) else (
        echo Dataset already extracted
    )
) else (
    echo WARNING: MachineLearningCSV.zip not found
)
echo.

REM Clear old results
if exist "results" (
    echo Clearing old results...
    rmdir /s /q "results" 2>nul
)

REM ===========================
REM EXPERIMENT 1: Real Dataset
REM ===========================
echo =======================================
echo   EXPERIMENT 1: Real CIC-IDS2017 Dataset
echo =======================================
echo.
echo Starting experiment on REAL dataset...
echo This may take 30-60 minutes...
echo.

docker run --rm --cpus="0.000" --memory="16g" -v "%CD%/data:/app/data" -v "%CD%/results:/app/results" -e PYTHONPATH=/app fp-tree-ids:latest python experiments/main_experiment.py

if %ERRORLEVEL% EQ 0 (
    echo.
    echo Real dataset experiment completed!
    
    REM Save results
    if exist "results_real_data" rmdir /s /q "results_real_data"
    xcopy /E /I /Y "results" "results_real_data" >nul
    echo Results saved to: results_real_data/
    echo.
    dir /s "results_real_data"
) else (
    echo.
    echo ERROR: Real dataset experiment failed!
    pause
    exit /b 1
)

echo.

REM Clear results for synthetic run
if exist "results" rmdir /s /q "results"

REM ==============================
REM EXPERIMENT 2: Synthetic Dataset
REM ==============================
echo =======================================
echo   EXPERIMENT 2: Synthetic Dataset
echo =======================================
echo.

REM Create synthetic experiment script
echo import sys > run_synthetic_experiment.py
echo sys.path.insert(0, "/app") >> run_synthetic_experiment.py
echo. >> run_synthetic_experiment.py
echo import pandas as pd >> run_synthetic_experiment.py
echo from pathlib import Path >> run_synthetic_experiment.py
echo import numpy as np >> run_synthetic_experiment.py
echo from src.preprocessing.feature_engineering import FeatureEngineer >> run_synthetic_experiment.py
echo from src.preprocessing.transaction_builder import TransactionBuilder >> run_synthetic_experiment.py
echo from experiments.main_experiment import evaluate_streaming_performance >> run_synthetic_experiment.py
echo from src.algorithms.variants.no_reorder import NoReorderFPTree >> run_synthetic_experiment.py
echo from src.algorithms.variants.partial_rebuild import PartialRebuildFPTree >> run_synthetic_experiment.py
echo from src.algorithms.variants.two_tree import TwoTreeFPTree >> run_synthetic_experiment.py
echo from src.algorithms.variants.decay_hybrid import DecayHybridFPTree >> run_synthetic_experiment.py
echo from src.algorithms.baselines.half_space_trees import HalfSpaceTrees >> run_synthetic_experiment.py
echo from src.algorithms.baselines.random_cut_forest import RandomCutForest >> run_synthetic_experiment.py
echo from src.algorithms.baselines.online_autoencoder import OnlineAutoencoder >> run_synthetic_experiment.py
echo from src.evaluation.visualization import plot_throughput_latency >> run_synthetic_experiment.py
echo. >> run_synthetic_experiment.py
echo print("Loading synthetic dataset...") >> run_synthetic_experiment.py
echo data = pd.read_csv("/app/data/raw/synthetic_cic_ids2017.csv") >> run_synthetic_experiment.py
echo print(f"Loaded {len(data)} rows") >> run_synthetic_experiment.py
echo. >> run_synthetic_experiment.py
echo Path('/app/results/figures').mkdir(parents=True, exist_ok=True) >> run_synthetic_experiment.py
echo Path('/app/results/tables').mkdir(parents=True, exist_ok=True) >> run_synthetic_experiment.py
echo. >> run_synthetic_experiment.py
echo labels = (data['Label'] != 'BENIGN').astype(int).to_numpy() >> run_synthetic_experiment.py
echo fe = FeatureEngineer(n_bins=5) >> run_synthetic_experiment.py
echo selected = fe.select_features(data) >> run_synthetic_experiment.py
echo discretised = fe.discretize_continuous_features(selected) >> run_synthetic_experiment.py
echo tb = TransactionBuilder() >> run_synthetic_experiment.py
echo transactions = tb.build_transactions(discretised) >> run_synthetic_experiment.py
echo. >> run_synthetic_experiment.py
echo algorithms = { >> run_synthetic_experiment.py
echo     'NR': NoReorderFPTree(min_support=0.005, window_size=2000), >> run_synthetic_experiment.py
echo     'PR': PartialRebuildFPTree(min_support=0.005, window_size=2000, rebuild_threshold=0.1), >> run_synthetic_experiment.py
echo     'TT': TwoTreeFPTree(min_support=0.005, half_window_size=1000), >> run_synthetic_experiment.py
echo     'DH': DecayHybridFPTree(min_support=0.005, window_size=2000, decay_factor=0.995), >> run_synthetic_experiment.py
echo     'HS-Trees': HalfSpaceTrees(n_trees=25, tree_depth=15), >> run_synthetic_experiment.py
echo     'RCF': RandomCutForest(n_trees=100, sample_size=256), >> run_synthetic_experiment.py
echo     'Autoencoder': OnlineAutoencoder(encoding_dim=0.5) >> run_synthetic_experiment.py
echo } >> run_synthetic_experiment.py
echo. >> run_synthetic_experiment.py
echo results = evaluate_streaming_performance(algorithms=algorithms, transactions=transactions, labels=labels, window_size=2000, anomaly_threshold=0.5) >> run_synthetic_experiment.py
echo. >> run_synthetic_experiment.py
echo results_df = pd.DataFrame.from_dict(results, orient='index') >> run_synthetic_experiment.py
echo results_df.to_csv('/app/results/tables/performance.csv') >> run_synthetic_experiment.py
echo. >> run_synthetic_experiment.py
echo plot_throughput_latency({name: {'throughput': m['throughput'], 'latency': m['latency']} for name, m in results.items()}, '/app/results/figures/throughput_latency.png') >> run_synthetic_experiment.py
echo. >> run_synthetic_experiment.py
echo print("Synthetic experiment completed!") >> run_synthetic_experiment.py

echo Starting experiment on SYNTHETIC dataset...
echo This should be faster (less than 5 minutes)...
echo.

docker run --rm --cpus="0.000" --memory="8g" -v "%CD%/data:/app/data" -v "%CD%/results:/app/results" -v "%CD%/run_synthetic_experiment.py:/app/run_synthetic_experiment.py" -e PYTHONPATH=/app fp-tree-ids:latest python /app/run_synthetic_experiment.py

if %ERRORLEVEL% EQ 0 (
    echo.
    echo Synthetic dataset experiment completed!
    
    REM Save results
    if exist "results_synthetic_data" rmdir /s /q "results_synthetic_data"
    xcopy /E /I /Y "results" "results_synthetic_data" >nul
    echo Results saved to: results_synthetic_data/
    echo.
    dir /s "results_synthetic_data"
) else (
    echo.
    echo ERROR: Synthetic dataset experiment failed!
    pause
    exit /b 1
)

REM Clean up
del run_synthetic_experiment.py 2>nul

echo.
echo =======================================
echo   ALL EXPERIMENTS COMPLETED!
echo =======================================
echo.
echo Results:
echo   - results_real_data/      (Real CIC-IDS2017 dataset)
echo   - results_synthetic_data/ (Synthetic dataset)
echo.
echo Compare the performance.csv files in both folders!
echo.
pause
