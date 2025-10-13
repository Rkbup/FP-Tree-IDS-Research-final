# FP-Tree-IDS-Research-final

This repository provides the complete reproduction package for the paper “Sliding-Window FP-Tree Reconstruction for Real-Time Network Intrusion Detection”. It contains everything required to recreate the reported experiments: preprocessing pipelines, FP-tree variants, baseline models, streaming utilities, evaluation scripts, statistical analysis, and plotting routines.

The project is organised as a conventional Python package with clear boundaries between raw data, processed artefacts, source code, configuration, experiments, and generated results. Docker support is available for fully containerised runs, while Conda allows local execution.

## Quick Start

Choose either the Docker workflow (recommended for reproducibility) or a local Conda environment.

### Option 1: Docker

```bash
git clone https://github.com/yourusername/FP-Tree-IDS-Research.git
cd FP-Tree-IDS-Research

# Build and start the experiment container
docker-compose up

# Download the CIC-IDS2017 dataset (runs inside the container)
docker-compose run fp-tree-experiments python data/download_dataset.py

# Execute the main experiment
docker-compose run fp-tree-experiments python experiments/main_experiment.py
```

### Option 2: Conda Environment

```bash
git clone https://github.com/yourusername/FP-Tree-IDS-Research.git
cd FP-Tree-IDS-Research

# Create and activate the Conda environment
conda env create -f environment.yml
conda activate fp-tree-ids-research

# Install Python dependencies
pip install -r requirements.txt

# Download the dataset
python data/download_dataset.py

# Execute the main experiment
python experiments/main_experiment.py
```

## Repository Structure

```
FP-Tree-IDS-Research/
  README.md
  requirements.txt
  environment.yml
  docker-compose.yml
  data/
    raw/                 # Original CIC-IDS2017 CSV files (placeholder)
    processed/           # Cached processed artefacts
    bin_edges.json       # Quantile bin boundaries for discretisation
    download_dataset.py  # Dataset download/verification script
  src/
    preprocessing/       # Loading, feature engineering, transaction building
    algorithms/          # FP-tree variants and baseline anomaly detectors
    streaming/           # Sliding-window management utilities
    evaluation/          # Metrics, visualisation, statistical routines
  experiments/           # Reproduction scripts for each reported experiment
    main_experiment.py
    concept_drift_analysis.py
    baseline_comparison.py
    sensitivity_analysis.py
    interpretability_demo.py
    smoke_test.py
  config/                # YAML configuration files for experiments
    default.yaml
    experiment_params.yaml
    flink_config.yaml
  results/               # Generated outputs (figures, tables, logs, stats)
    figures/
    tables/
    statistical_analysis/
    logs/
  tests/                 # Unit tests for core functionality
  docs/                  # Extended documentation (installation, API, etc.)
```

## Reproducing the Results

1. Ensure the CIC-IDS2017 dataset is available. Running `data/download_dataset.py` will download and verify the archive into `data/raw/`. If you already have the files, copy them into `data/raw/` instead.
2. Preprocess the network flows into discretised transactions via `src/preprocessing/feature_engineering.py` and `src/preprocessing/transaction_builder.py`. The main experiment performs this automatically if processed data is absent.
3. Adjust experiment settings in `config/experiment_params.yaml` as required. Defaults for all hyper-parameters (window sizes, minimum support, decay factors, etc.) are stored in `config/default.yaml`.
4. Run any of the experiment scripts:
   - `experiments/main_experiment.py` reproduces the end-to-end performance results.
   - `experiments/concept_drift_analysis.py` evaluates behaviour under concept drift.
   - `experiments/baseline_comparison.py` benchmarks FP-tree variants against Half-Space Trees, Random Cut Forest, and the online autoencoder.
   - `experiments/sensitivity_analysis.py` explores hyper-parameter sensitivity.
   - `experiments/interpretability_demo.py` recreates the interpretability case study.
5. Inspect generated artefacts in `results/figures/`, `results/tables/`, and `results/statistical_analysis/`.

## Citation

```bibtex
@article{akand2025slidingwindow,
  title   = {Sliding-Window FP-Tree Reconstruction for Real-Time Network Intrusion Detection},
  author  = {Akand, Abdullah Rakib},
  journal = {Springer Journal of Network and Systems Management},
  year    = {2025}
}
```

## License

Released under the MIT License. See the LICENSE file for details.

