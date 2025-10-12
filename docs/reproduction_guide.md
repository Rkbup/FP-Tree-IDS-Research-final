# Reproduction Guide

This guide provides detailed instructions to reproduce all experiments
and figures reported in the paper *“Sliding‑Window FP‑Tree
Reconstruction for Real‑Time Network Intrusion Detection”*.  You
should familiarise yourself with the repository structure and
installation steps described in `README.md` before proceeding.

## Step 1: Obtain the CIC‑IDS2017 Dataset

The experiments use the full 5‑day CIC‑IDS2017 dataset.  Download the
dataset by running:

```bash
python data/download_dataset.py
```

If the automated download fails (e.g. due to the need to accept
licensing terms), manually download the dataset from the [Canadian
Institute for Cybersecurity](https://www.unb.ca/cic/datasets/ids-2017.html)
and place the extracted CSV files into `data/raw/`.

## Step 2: Preprocess the Data

No explicit preprocessing step is required when running the
experiments: each script will automatically apply feature selection,
discretisation and transaction building on the fly if the processed
files are not yet available.  However, you can run the preprocessing
independently for inspection:

```bash
python -c "from src.preprocessing.data_loader import load_cic_ids2017; from src.preprocessing.feature_engineering import FeatureEngineer; from src.preprocessing.transaction_builder import TransactionBuilder; import pandas as pd; data=load_cic_ids2017(); fe=FeatureEngineer(n_bins=5); selected=fe.select_features(data); discretised=fe.discretize_continuous_features(selected); fe.save_bin_edges('data/bin_edges.json'); tb=TransactionBuilder(); transactions=tb.build_transactions(discretised); print(f'Generated {len(transactions)} transactions.')"
```

This command loads the dataset, selects 15 features, discretises them
into 5 bins, stores the bin edges to JSON and builds the list of
transactions.

## Step 3: Run the Main Experiment

Execute the main experiment script to reproduce the runtime and
detection results across all FP‑tree variants and baselines.  This
script will save performance metrics to `results/tables/` and a
throughput–latency plot to `results/figures/`.

```bash
python experiments/main_experiment.py
```

For convenience, you can override configuration values by editing
`config/experiment_params.yaml` or by passing environment variables.

## Step 4: Concept Drift Analysis

To evaluate how the FP‑tree variants adapt to natural concept drift
between different days, run the drift analysis script:

```bash
python experiments/concept_drift_analysis.py
```

This script generates a plot showing the F1 score over time with
dashed lines marking day boundaries and writes a table of recovery
times and stability scores to `results/tables/`.

## Step 5: Baseline Comparison

Run the baseline comparison script to compare the FP‑tree variants
with HS‑Trees, Random Cut Forest and an online autoencoder.  The
script reports detection metrics, throughput and memory usage along
with significance tests.

```bash
python experiments/baseline_comparison.py
```

## Step 6: Parameter Sensitivity Analysis

To explore how varying the anomaly threshold (τ), window size (N),
minimum support (σ) and decay factor affects performance, execute:

```bash
python experiments/sensitivity_analysis.py
```

The script produces a 2×2 panel figure of sensitivity curves and
saves a summary table.

## Step 7: Interpretability Demonstration

Finally, run the interpretability demonstration to see a real
anomaly flagged by the Partial Rebuild variant along with an
explanation of the underlying itemset:

```bash
python experiments/interpretability_demo.py
```

This script prints a report to the console and may generate a figure
if visualisation of the rare itemset is enabled.

## Step 8: View Results

All generated figures are saved under `results/figures/`, and tables
are stored in `results/tables/`.  Statistical test results can be
found in `results/statistical_analysis/`.  Use your preferred tools
to inspect these files or incorporate them into your own reports.

## Troubleshooting

If you encounter errors during reproduction, consult the
troubleshooting guide in `docs/troubleshooting.md`.  Common issues
include missing dependencies, incomplete dataset downloads or
insufficient memory for large window sizes.