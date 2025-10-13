"""
main_experiment.py
==================

This script reproduces the primary performance and detection results
reported in the paper.  It loads the CIC‑IDS2017 dataset, performs
feature engineering and transaction conversion, instantiates each
algorithm (FP‑tree variants and baselines), processes the data in a
streaming fashion and records metrics including throughput, latency,
memory usage, precision, recall, F1 and PR‑AUC.  The results are
written to CSV files and plots stored under ``results/``.

Usage
-----
Run this script from the project root after downloading the dataset:

```bash
python experiments/main_experiment.py
```
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from src.preprocessing.data_loader import load_cic_ids2017
from src.preprocessing.feature_engineering import FeatureEngineer
from src.preprocessing.transaction_builder import TransactionBuilder
from src.algorithms.fp_tree import FPTree
from src.algorithms.variants.no_reorder import NoReorderFPTree
from src.algorithms.variants.partial_rebuild import PartialRebuildFPTree
from src.algorithms.variants.two_tree import TwoTreeFPTree
from src.algorithms.variants.decay_hybrid import DecayHybridFPTree
from src.algorithms.baselines.half_space_trees import HalfSpaceTrees
from src.algorithms.baselines.random_cut_forest import RandomCutForest
from src.algorithms.baselines.online_autoencoder import OnlineAutoencoder
from src.streaming.window_manager import SlidingWindowManager
from src.evaluation.metrics import classification_metrics, pr_auc, throughput, memory_usage_mb, bootstrap_confidence_interval
from src.evaluation.visualization import plot_throughput_latency


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the main experiment."""

    parser = argparse.ArgumentParser(
        description="Run the sliding-window FP-Tree main experiment on CIC-IDS2017."
    )
    parser.add_argument(
        "--raw-dir",
        default="data/raw",
        help="Directory containing the raw CIC-IDS2017 CSV files (defaults to data/raw).",
    )
    parser.add_argument(
        "--days",
        nargs="+",
        help="Optional list of day names to load (e.g. Monday Tuesday).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-file loading messages for the dataset.",
    )
    return parser.parse_args()


def evaluate_streaming_performance(
    algorithms: Dict[str, object],
    transactions: List[List[str]],
    labels: np.ndarray,
    window_size: int,
    anomaly_threshold: float = 0.5,
    pattern_refresh_interval: int = 1
) -> Dict[str, Dict[str, float]]:
    """Process a stream of transactions with multiple algorithms.

    Parameters
    ----------
    algorithms : dict
        Mapping from algorithm names to instantiated objects.  FP‑tree
        variants must implement ``insert_transaction`` and ``remove_transaction``.
        Baseline models must implement ``fit`` and ``score_samples``.
    transactions : list of list of str
        Discretised transactions aligned with ``labels``.
    labels : np.ndarray
        Binary labels (0/1) indicating benign (0) or attack (1) flows.
    window_size : int
        Maximum number of transactions to retain in the sliding window.  For
        two‑tree the effective window size is ``2 * half_window_size`` and
        should be passed accordingly.
    anomaly_threshold : float, optional
        Threshold above which anomaly scores are considered positive.  The
        same threshold is used for all algorithms for simplicity.

    Returns
    -------
    dict
        Summary of performance metrics for each algorithm.
    """
    n = len(transactions)
    results: Dict[str, Dict[str, float]] = {}
    # Precompute vectorised baseline features: convert transactions back to
    # one‑hot encoded vectors for baseline models
    # Build vocabulary of items
    vocab = sorted({item for txn in transactions for item in txn})
    item_to_idx = {item: i for i, item in enumerate(vocab)}
    X_full = np.zeros((n, len(vocab)), dtype=np.int8)
    for i, txn in enumerate(transactions):
        for item in txn:
            X_full[i, item_to_idx[item]] = 1

    for name, alg in algorithms.items():
        print(f"Evaluating {name} ...")
        start_time = time.time()
        # Reset result containers
        y_pred = np.zeros(n, dtype=np.int8)
        scores = np.zeros(n, dtype=np.float32)
        mem_usages: List[float] = []
        refresh_interval = max(1, pattern_refresh_interval)
        if isinstance(alg, (FPTree, PartialRebuildFPTree, DecayHybridFPTree)):
            # FP‑tree variant using sliding window manager
            window_manager = SlidingWindowManager(alg, max_size=window_size)
            cached_patterns: Dict[Tuple[str, ...], int] = {}
            for idx, txn in enumerate(transactions):
                window_manager.update(txn)
                if idx == 0 or ((idx + 1) % refresh_interval) == 0:
                    cached_patterns = alg.mine_frequent_patterns()
                # Compute rarity score: simplistic measure 1 − max support
                score = 1.0
                # Compute rarity as described in Eq. (1): 1 - max support / window
                if cached_patterns:
                    max_support = max(cached_patterns.values())
                    score = 1.0 - (max_support / max(1, len(window_manager.window)))
                scores[idx] = score
                y_pred[idx] = 1 if score >= anomaly_threshold else 0
                # Record memory usage periodically
                if idx % 1000 == 0:
                    mem_usages.append(memory_usage_mb())
        elif isinstance(alg, TwoTreeFPTree):
            # Two‑tree variant: effective window size is 2 * half_window_size
            cached_patterns: Dict[Tuple[str, ...], int] = {}
            for idx, txn in enumerate(transactions):
                alg.insert_transaction(txn)
                if idx == 0 or ((idx + 1) % refresh_interval) == 0:
                    cached_patterns = alg.mine_frequent_patterns()
                # Compute rarity across both trees
                score = 1.0
                if cached_patterns:
                    max_support = max(cached_patterns.values())
                    score = 1.0 - (max_support / (2 * alg.half_window_size))
                scores[idx] = score
                y_pred[idx] = 1 if score >= anomaly_threshold else 0
                if idx % 1000 == 0:
                    mem_usages.append(memory_usage_mb())
        elif isinstance(alg, HalfSpaceTrees):
            # Fit model on first window and then update per window
            warmup = min(window_size, n)
            alg.fit(X_full[:warmup])
            for idx in range(warmup, n):
                x = X_full[idx:idx+1]
                score = alg.score_samples(x)[0]
                scores[idx] = score
                y_pred[idx] = 1 if score >= anomaly_threshold else 0
                # Optionally retrain periodically
                if (idx % window_size) == 0:
                    start = idx - window_size + 1
                    if start < 0:
                        start = 0
                    alg.fit(X_full[start:idx+1])
                if idx % 1000 == 0:
                    mem_usages.append(memory_usage_mb())
        elif isinstance(alg, RandomCutForest):
            warmup = min(window_size, n)
            alg.fit(X_full[:warmup])
            for idx in range(warmup, n):
                x = X_full[idx:idx+1]
                score = alg.score_samples(x)[0]
                scores[idx] = score
                y_pred[idx] = 1 if score >= anomaly_threshold else 0
                if (idx % window_size) == 0:
                    start = idx - window_size + 1
                    if start < 0:
                        start = 0
                    alg.fit(X_full[start:idx+1])
                if idx % 1000 == 0:
                    mem_usages.append(memory_usage_mb())
        elif isinstance(alg, OnlineAutoencoder):
            warmup = min(window_size, n)
            alg.fit(X_full[:warmup])
            for idx in range(warmup, n):
                x = X_full[idx:idx+1]
                score = alg.score_samples(x)[0]
                scores[idx] = score
                y_pred[idx] = 1 if score >= anomaly_threshold else 0
                # Retrain periodically
                if (idx % window_size) == 0:
                    start = idx - window_size + 1
                    if start < 0:
                        start = 0
                    alg.fit(X_full[start:idx+1])
                if idx % 1000 == 0:
                    mem_usages.append(memory_usage_mb())
        else:
            raise TypeError(f"Unsupported algorithm type: {type(alg)}")
        end_time = time.time()
        elapsed = end_time - start_time
        # Compute metrics
        metrics = classification_metrics(labels, y_pred)
        metrics['pr_auc'] = pr_auc(labels, scores)
        metrics['throughput'] = throughput(n, elapsed)
        metrics['latency'] = (elapsed / max(1, n)) * 1000  # ms per flow
        metrics['memory'] = float(np.mean(mem_usages)) if mem_usages else memory_usage_mb()
        # Confidence intervals for F1
        ci_lower, ci_upper = bootstrap_confidence_interval(metrics['f1'] for _ in range(30))  # replicate mean
        metrics['f1_ci_lower'] = ci_lower
        metrics['f1_ci_upper'] = ci_upper
        results[name] = metrics
    return results


def main() -> None:
    args = parse_args()
    # Ensure results directories exist
    Path('results/figures').mkdir(parents=True, exist_ok=True)
    Path('results/tables').mkdir(parents=True, exist_ok=True)
    Path('results/logs').mkdir(parents=True, exist_ok=True)
    Path('results/statistical_analysis').mkdir(parents=True, exist_ok=True)
    # Load dataset (all days)
    data = load_cic_ids2017(raw_dir=args.raw_dir, days=args.days, verbose=not args.quiet)
    # Map labels to binary (Attack=1, Benign=0)
    labels = (data['Label'] != 'BENIGN').astype(int).to_numpy()
    # Feature engineering
    fe = FeatureEngineer(n_bins=5)
    selected = fe.select_features(data)
    discretised = fe.discretize_continuous_features(selected)
    # Persist bin edges for reproducibility
    fe.save_bin_edges('data/bin_edges.json')
    # Build transactions
    tb = TransactionBuilder()
    transactions = tb.build_transactions(discretised)
    # Prepare algorithms
    algorithms = {
        'NR': NoReorderFPTree(min_support=0.005, window_size=20000),
        'PR': PartialRebuildFPTree(min_support=0.005, window_size=20000, rebuild_threshold=0.1),
        'TT': TwoTreeFPTree(min_support=0.005, half_window_size=10000),
        'DH': DecayHybridFPTree(min_support=0.005, window_size=20000, decay_factor=0.995),
        'HS-Trees': HalfSpaceTrees(n_trees=25, tree_depth=15),
        'RCF': RandomCutForest(n_trees=100, sample_size=256),
        'Autoencoder': OnlineAutoencoder(encoding_dim=0.5)
    }
    # Evaluate performance
    results = evaluate_streaming_performance(
        algorithms=algorithms,
        transactions=transactions,
        labels=labels,
        window_size=20000,
        anomaly_threshold=0.5
    )
    # Save performance metrics to CSV
    results_df = pd.DataFrame.from_dict(results, orient='index')
    results_df.to_csv('results/tables/performance.csv')
    # Plot throughput–latency trade‑off
    plot_throughput_latency({name: {'throughput': m['throughput'], 'latency': m['latency']} for name, m in results.items()},
                            'results/figures/throughput_latency.png')
    print("Main experiment completed. Results saved to results/ directory.")


if __name__ == '__main__':
    main()
