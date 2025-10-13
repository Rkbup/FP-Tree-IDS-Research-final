# Docker-based Experiment Runner — Quick Start

## Prerequisites
- Docker Desktop installed and running
- Dataset extracted in `data/raw/` (use `data/download_dataset.py` if needed)

## Run All Experiments (Automated)

PowerShell:

```powershell
./run_docker_experiments.ps1
```

This will:
1. Build the Docker image
2. Run the real CIC-IDS2017 experiment
3. Save results to `results_real_data/`
4. Run the synthetic dataset experiment
5. Save results to `results_synthetic_data/`

## What Happens

### Step 1: Real Dataset Experiment (30–60 minutes)
- Uses all available CPU and up to 16 GB RAM (configurable)
- Processes all CIC-IDS2017 CSV files
- Generates performance metrics and visualizations

### Step 2: Synthetic Dataset Experiment (< 5 minutes)
- Smaller window sizes for faster processing
- Generates comparable metrics and plots

## Output Structure

```
results_real_data/
  figures/
    throughput_latency.png
  tables/
    performance.csv
  logs/

results_synthetic_data/
  figures/
    throughput_latency.png
  tables/
    performance.csv
  logs/
```

## Manual Docker Commands

### Build image
```powershell
docker build -t fp-tree-ids:latest .
```

### Run real dataset experiment
```powershell
docker run --rm `
    --cpus="0.000" --memory="16g" `
    -v "${PWD}/data:/app/data" `
    -v "${PWD}/results:/app/results" `
    fp-tree-ids:latest
```

### Run with custom parameters
```powershell
docker run --rm `
    -v "${PWD}/data:/app/data" `
    -v "${PWD}/results:/app/results" `
    fp-tree-ids:latest `
    python experiments/main_experiment.py --raw-dir /app/data/raw/MachineLearningCVE
```

## Troubleshooting

### Docker not running
- Start Docker Desktop
- Wait for it to fully initialize

### Out of memory
- Increase Docker's memory limit in Docker Desktop settings
- Recommended: At least 16 GB for the real dataset

### Permission errors
- Run PowerShell as Administrator
- Ensure Docker Desktop has access to the drive containing the repo

## Resource Usage

The script configures Docker to use:
- Real dataset: All available CPUs, 16 GB RAM
- Synthetic dataset: All available CPUs, 8 GB RAM

Modify `--cpus` and `--memory` in the scripts if needed.

