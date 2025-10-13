"""Synthetic dataset experiment runner with maximum performance settings."""

from __future__ import annotations

import multiprocessing
import os
from pathlib import Path
import sys

import numpy as np
import pandas as pd

from experiments.main_experiment import evaluate_streaming_performance
from src.algorithms.baselines.half_space_trees import HalfSpaceTrees
from src.algorithms.baselines.online_autoencoder import OnlineAutoencoder
from src.algorithms.baselines.random_cut_forest import RandomCutForest
from src.algorithms.variants.decay_hybrid import DecayHybridFPTree
from src.algorithms.variants.no_reorder import NoReorderFPTree
from src.algorithms.variants.partial_rebuild import PartialRebuildFPTree
from src.algorithms.variants.two_tree import TwoTreeFPTree
from src.preprocessing.feature_engineering import FeatureEngineer
from src.preprocessing.transaction_builder import TransactionBuilder
from src.evaluation.visualization import plot_throughput_latency


def configure_threads() -> None:
    """Configure numeric libraries to use all available CPU cores."""
    cpu_count = multiprocessing.cpu_count()
    env_vars = [
        "OMP_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
    ]
    for var in env_vars:
        os.environ[var] = str(cpu_count)
    print(f"Configured numeric libraries for {cpu_count} CPU cores")


def run_experiment() -> None:
    """Execute the synthetic dataset experiment."""
    configure_threads()
    # Allow deeper FP-tree recursion during mining.
    sys.setrecursionlimit(10000)

    print("=" * 60)
    print("SYNTHETIC DATASET EXPERIMENT (MAX PERFORMANCE)")
    print("=" * 60)

    data_path = Path("/app/data/raw/synthetic_cic_ids2017.csv")
    if not data_path.exists():
        raise FileNotFoundError(f"Synthetic dataset not found at {data_path}")

    print("Loading synthetic dataset...")
    data = pd.read_csv(data_path)
    print(f"✅ Loaded {len(data)} rows")

    Path("/app/results/figures").mkdir(parents=True, exist_ok=True)
    Path("/app/results/tables").mkdir(parents=True, exist_ok=True)

    print("\nProcessing features...")
    labels = (data["Label"] != "BENIGN").astype(int).to_numpy()
    fe = FeatureEngineer(n_bins=5)
    selected = fe.select_features(data)
    discretised = fe.discretize_continuous_features(selected)
    print("✅ Feature engineering complete")

    print("\nBuilding transactions...")
    tb = TransactionBuilder()
    transactions = tb.build_transactions(discretised)
    print(f"✅ Built {len(transactions)} transactions")

    print("\nInitializing algorithms...")
    algorithms = {
        "NR": NoReorderFPTree(min_support=0.005, window_size=2000),
        "PR": PartialRebuildFPTree(min_support=0.005, window_size=2000, rebuild_threshold=0.1),
        "TT": TwoTreeFPTree(min_support=0.005, half_window_size=1000),
        "DH": DecayHybridFPTree(min_support=0.005, window_size=2000, decay_factor=0.995),
        "HS-Trees": HalfSpaceTrees(n_trees=25, tree_depth=15),
        "RCF": RandomCutForest(n_trees=100, sample_size=256),
        "Autoencoder": OnlineAutoencoder(encoding_dim=0.5),
    }

    print("\nStarting evaluation...")
    results = evaluate_streaming_performance(
        algorithms=algorithms,
        transactions=transactions,
        labels=labels,
        window_size=2000,
        anomaly_threshold=0.5,
    )

    print("\nSaving results...")
    results_df = pd.DataFrame.from_dict(results, orient="index")
    results_df.to_csv("/app/results/tables/performance_synthetic.csv")
    print("✅ Results saved to: results/tables/performance_synthetic.csv")

    print("\nGenerating plots...")
    plot_throughput_latency(
        {name: {"throughput": m["throughput"], "latency": m["latency"]} for name, m in results.items()},
        "/app/results/figures/throughput_latency_synthetic.png",
    )
    print("✅ Plot saved to: results/figures/throughput_latency_synthetic.png")

    print("\n" + "=" * 60)
    print("✅ SYNTHETIC EXPERIMENT COMPLETED!")
    print("=" * 60)
    print("\nResults Summary:")
    print(results_df.to_string())


if __name__ == "__main__":
    run_experiment()
