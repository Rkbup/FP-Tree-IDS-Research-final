# Complete Docker-based Experiment Runner
# This script runs experiments on both Real and Synthetic datasets using Docker

Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "  FP-Tree IDS Experiment Runner (Docker)" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is running
Write-Host "🔍 Checking Docker..." -ForegroundColor Yellow
docker info > $null 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker is not running. Please start Docker Desktop and try again." -ForegroundColor Red
    exit 1
}
Write-Host "✅ Docker is running" -ForegroundColor Green
Write-Host ""

# Build Docker image
Write-Host "🔨 Building Docker image..." -ForegroundColor Yellow
docker build -t fp-tree-ids:latest .
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker build failed!" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Docker image built successfully" -ForegroundColor Green
Write-Host ""

# Extract dataset if needed
Write-Host "📦 Checking dataset..." -ForegroundColor Yellow
$zipFile = "data\raw\MachineLearningCSV.zip"
$extractFolder = "data\raw\MachineLearningCVE"

if (Test-Path $zipFile) {
    if (-not (Test-Path $extractFolder)) {
        Write-Host "📂 Extracting dataset..." -ForegroundColor Yellow
        Expand-Archive -Path $zipFile -DestinationPath "data\raw" -Force
        Write-Host "✅ Dataset extracted" -ForegroundColor Green
    } else {
        Write-Host "✅ Dataset already extracted" -ForegroundColor Green
    }
} else {
    Write-Host "⚠️  Warning: MachineLearningCSV.zip not found" -ForegroundColor Yellow
}
Write-Host ""

# ===========================
# EXPERIMENT 1: Real Dataset
# ===========================
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "  EXPERIMENT 1: Real CIC-IDS2017 Dataset" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host ""

# Clear old results
if (Test-Path "results") {
    Write-Host "🗑️  Clearing old results..." -ForegroundColor Yellow
    Remove-Item -Path "results\*" -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host "🚀 Starting experiment on REAL dataset..." -ForegroundColor Green
Write-Host "⏱️  This may take 30-60 minutes depending on your CPU..." -ForegroundColor Yellow
Write-Host ""

$startTime = Get-Date

# Run Docker container for real data
docker run --rm `
    --cpus="0.000" `
    --memory="16g" `
    -v "${PWD}/data:/app/data" `
    -v "${PWD}/results:/app/results" `
    -v "${PWD}/config:/app/config" `
    -e PYTHONPATH=/app `
    fp-tree-ids:latest `
    python experiments/main_experiment.py

$realExitCode = $LASTEXITCODE
$endTime = Get-Date
$duration = $endTime - $startTime

if ($realExitCode -eq 0) {
    Write-Host ""
    Write-Host "✅ Real dataset experiment completed in $($duration.TotalMinutes.ToString('0.00')) minutes!" -ForegroundColor Green
    
    # Save results
    if (Test-Path "results_real_data") {
        Remove-Item -Path "results_real_data" -Recurse -Force
    }
    Copy-Item -Path "results" -Destination "results_real_data" -Recurse
    Write-Host "💾 Results saved to: results_real_data/" -ForegroundColor Green
    
    # Show results
    Write-Host ""
    Write-Host "📊 Generated files:" -ForegroundColor Cyan
    Get-ChildItem -Path "results_real_data" -Recurse -File | Select-Object FullName, @{Name="SizeKB";Expression={[math]::Round($_.Length/1KB,2)}} | Format-Table -AutoSize
} else {
    Write-Host ""
    Write-Host "❌ Real dataset experiment failed with exit code $realExitCode" -ForegroundColor Red
    Write-Host "Check the output above for errors." -ForegroundColor Yellow
    exit $realExitCode
}

Write-Host ""

# ==============================
# EXPERIMENT 2: Synthetic Dataset
# ==============================
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "  EXPERIMENT 2: Synthetic Dataset" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host ""

# Clear results folder
if (Test-Path "results") {
    Write-Host "🗑️  Clearing results from previous run..." -ForegroundColor Yellow
    Remove-Item -Path "results\*" -Recurse -Force -ErrorAction SilentlyContinue
}

# Create synthetic experiment script
$syntheticScript = @'
import sys
sys.path.insert(0, "/app")

import pandas as pd
from pathlib import Path
import numpy as np
from src.preprocessing.feature_engineering import FeatureEngineer
from src.preprocessing.transaction_builder import TransactionBuilder
from experiments.main_experiment import evaluate_streaming_performance
from src.algorithms.variants.no_reorder import NoReorderFPTree
from src.algorithms.variants.partial_rebuild import PartialRebuildFPTree
from src.algorithms.variants.two_tree import TwoTreeFPTree
from src.algorithms.variants.decay_hybrid import DecayHybridFPTree
from src.algorithms.baselines.half_space_trees import HalfSpaceTrees
from src.algorithms.baselines.random_cut_forest import RandomCutForest
from src.algorithms.baselines.online_autoencoder import OnlineAutoencoder
from src.evaluation.visualization import plot_throughput_latency

print("Loading synthetic dataset...")
data = pd.read_csv("/app/data/raw/synthetic_cic_ids2017.csv")
print(f"Loaded {len(data)} rows")

# Create results directories
Path('/app/results/figures').mkdir(parents=True, exist_ok=True)
Path('/app/results/tables').mkdir(parents=True, exist_ok=True)
Path('/app/results/logs').mkdir(parents=True, exist_ok=True)

# Process data
labels = (data['Label'] != 'BENIGN').astype(int).to_numpy()
fe = FeatureEngineer(n_bins=5)
selected = fe.select_features(data)
discretised = fe.discretize_continuous_features(selected)
tb = TransactionBuilder()
transactions = tb.build_transactions(discretised)

# Algorithms (smaller window for synthetic data)
algorithms = {
    'NR': NoReorderFPTree(min_support=0.005, window_size=2000),
    'PR': PartialRebuildFPTree(min_support=0.005, window_size=2000, rebuild_threshold=0.1),
    'TT': TwoTreeFPTree(min_support=0.005, half_window_size=1000),
    'DH': DecayHybridFPTree(min_support=0.005, window_size=2000, decay_factor=0.995),
    'HS-Trees': HalfSpaceTrees(n_trees=25, tree_depth=15),
    'RCF': RandomCutForest(n_trees=100, sample_size=256),
    'Autoencoder': OnlineAutoencoder(encoding_dim=0.5)
}

# Run evaluation
results = evaluate_streaming_performance(
    algorithms=algorithms,
    transactions=transactions,
    labels=labels,
    window_size=2000,
    anomaly_threshold=0.5
)

# Save results
results_df = pd.DataFrame.from_dict(results, orient='index')
results_df.to_csv('/app/results/tables/performance.csv')

plot_throughput_latency(
    {name: {'throughput': m['throughput'], 'latency': m['latency']} for name, m in results.items()},
    '/app/results/figures/throughput_latency.png'
)

print("Synthetic experiment completed!")
'@

Set-Content -Path "run_synthetic_experiment.py" -Value $syntheticScript

Write-Host "🚀 Starting experiment on SYNTHETIC dataset..." -ForegroundColor Green
Write-Host "⏱️  This should be much faster (< 5 minutes)..." -ForegroundColor Yellow
Write-Host ""

$startTime = Get-Date

# Run Docker container for synthetic data
docker run --rm `
    --cpus="0.000" `
    --memory="8g" `
    -v "${PWD}/data:/app/data" `
    -v "${PWD}/results:/app/results" `
    -v "${PWD}/run_synthetic_experiment.py:/app/run_synthetic_experiment.py" `
    -e PYTHONPATH=/app `
    fp-tree-ids:latest `
    python /app/run_synthetic_experiment.py

$syntheticExitCode = $LASTEXITCODE
$endTime = Get-Date
$duration = $endTime - $startTime

if ($syntheticExitCode -eq 0) {
    Write-Host ""
    Write-Host "✅ Synthetic dataset experiment completed in $($duration.TotalMinutes.ToString('0.00')) minutes!" -ForegroundColor Green
    
    # Save results
    if (Test-Path "results_synthetic_data") {
        Remove-Item -Path "results_synthetic_data" -Recurse -Force
    }
    Copy-Item -Path "results" -Destination "results_synthetic_data" -Recurse
    Write-Host "💾 Results saved to: results_synthetic_data/" -ForegroundColor Green
    
    # Show results
    Write-Host ""
    Write-Host "📊 Generated files:" -ForegroundColor Cyan
    Get-ChildItem -Path "results_synthetic_data" -Recurse -File | Select-Object FullName, @{Name="SizeKB";Expression={[math]::Round($_.Length/1KB,2)}} | Format-Table -AutoSize
} else {
    Write-Host ""
    Write-Host "❌ Synthetic dataset experiment failed with exit code $syntheticExitCode" -ForegroundColor Red
    Write-Host "Check the output above for errors." -ForegroundColor Yellow
    exit $syntheticExitCode
}

# Clean up
Remove-Item -Path "run_synthetic_experiment.py" -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "  🎉 ALL EXPERIMENTS COMPLETED!" -ForegroundColor Green
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📊 Results:" -ForegroundColor Cyan
Write-Host "   ✅ results_real_data/      - Real CIC-IDS2017 dataset results" -ForegroundColor Green
Write-Host "   ✅ results_synthetic_data/ - Synthetic dataset results" -ForegroundColor Green
Write-Host ""
Write-Host "🔍 Compare the performance.csv files in both folders to analyze differences!" -ForegroundColor Yellow
Write-Host ""
