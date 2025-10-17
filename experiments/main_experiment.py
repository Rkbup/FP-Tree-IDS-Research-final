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
import signal
import time
import threading
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import yaml  # Add yaml import
from tqdm import tqdm

# Global flag for graceful shutdown
shutdown_requested = False

def ctrl_c_handler(signum, frame):
    """Handle Ctrl+C - Do nothing (ignore it)."""
    print("\n💡 Ctrl+C detected. Use Ctrl+H to stop the process gracefully.")
    print("   This prevents accidental interruption while copying error messages.")

def shutdown_handler():
    """Handle Ctrl+H for graceful shutdown."""
    global shutdown_requested
    try:
        import keyboard
        while True:
            if keyboard.is_pressed('ctrl+h'):
                if not shutdown_requested:
                    print("\n\n⚠️  Ctrl+H pressed - Shutdown requested. Saving checkpoint and cleaning up...")
                    shutdown_requested = True
                break
    except ImportError:
        print("⚠️  Warning: 'keyboard' module not installed. Ctrl+H shutdown not available.")
    except Exception as e:
        print(f"⚠️  Keyboard listener error: {e}")

# Register signal handlers and start keyboard listener
# Fully ignore Ctrl+C so copying text in terminal doesn't kill the process
signal.signal(signal.SIGINT, signal.SIG_IGN)
keyboard_thread = threading.Thread(target=shutdown_handler, daemon=True)
keyboard_thread.start()
print("Ctrl+C is ignored for safe copying. Press Ctrl+H to stop gracefully.")

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


def load_config(config_path: str) -> Dict:
    """Load experiment configuration from a YAML file."""
    if not config_path:
        # Default config if no path is provided
        print("Warning: No config file provided. Using default parameters.")
        return {
            'min_support': 0.005,
            'window_size': 20000,
            'rebuild_threshold': 0.1,
            'decay_factor': 0.995,
            'n_trees_hs': 25,
            'tree_depth_hs': 15,
            'n_trees_rcf': 100,
            'sample_size_rcf': 256,
            'encoding_dim_ae': 0.5,
            'anomaly_threshold': 0.5,
            'pattern_refresh_interval': 1
        }
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the main experiment."""

    parser = argparse.ArgumentParser(
        description="Run the sliding-window FP-Tree main experiment on CIC-IDS2017."
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to the experiment configuration YAML file."
    )
    parser.add_argument(
        "--output-dir",
        default="results",
        help="Directory to save experiment results (defaults to results/)."
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
            for idx, txn in tqdm(enumerate(transactions), total=n, desc=f"Processing {name}"):
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
            for idx, txn in tqdm(enumerate(transactions), total=n, desc=f"Processing {name}"):
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
            for idx in tqdm(range(warmup, n), total=n-warmup, desc=f"Processing {name}"):
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
            # Fit model on first window and then update per window
            warmup = min(window_size, n)
            alg.fit(X_full[:warmup])
            for idx in tqdm(range(warmup, n), total=n-warmup, desc=f"Processing {name}"):
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
            # Fit model on first window and then update per window
            warmup = min(window_size, n)
            alg.fit(X_full[:warmup])
            for idx in tqdm(range(warmup, n), total=n-warmup, desc=f"Processing {name}"):
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
    config = load_config(args.config)

    # Ensure results directories exist
    output_dir = Path(args.output_dir)
    output_dir.joinpath('figures').mkdir(parents=True, exist_ok=True)
    output_dir.joinpath('tables').mkdir(parents=True, exist_ok=True)
    output_dir.joinpath('logs').mkdir(parents=True, exist_ok=True)

    # Load dataset (all days)
    data = load_cic_ids2017(raw_dir=args.raw_dir, days=args.days, verbose=not args.quiet)
    # Map labels to binary (Attack=1, Benign=0)
    labels = (data['Label'] != 'BENIGN').astype(int).to_numpy()
    # Feature engineering
    fe = FeatureEngineer(n_bins=config.get('n_bins', 5))
    selected = fe.select_features(data)
    discretised = fe.discretize_continuous_features(selected)
    # Persist bin edges for reproducibility
    fe.save_bin_edges(output_dir.joinpath('bin_edges.json'))
    # Build transactions
    tb = TransactionBuilder()
    transactions = tb.build_transactions(discretised)
    
    # Prepare algorithms using config
    min_support = config['min_support']
    window_size = config['window_size']
    
    algorithms = {
        'NR': NoReorderFPTree(min_support=min_support, window_size=window_size),
        'PR': PartialRebuildFPTree(min_support=min_support, window_size=window_size, rebuild_threshold=config['rebuild_threshold']),
        'TT': TwoTreeFPTree(min_support=min_support, half_window_size=window_size // 2),
        'DH': DecayHybridFPTree(min_support=min_support, window_size=window_size, decay_factor=config['decay_factor']),
        'HS-Trees': HalfSpaceTrees(n_trees=config['n_trees_hs'], tree_depth=config['tree_depth_hs']),
        'RCF': RandomCutForest(n_trees=config['n_trees_rcf'], sample_size=config['sample_size_rcf']),
        'Autoencoder': OnlineAutoencoder(encoding_dim=config['encoding_dim_ae'])
    }
    # Evaluate performance
    results = evaluate_streaming_performance(
        algorithms=algorithms,
        transactions=transactions,
        labels=labels,
        window_size=window_size,
        anomaly_threshold=config['anomaly_threshold'],
        pattern_refresh_interval=config.get('pattern_refresh_interval', 1)
    )
    # Save performance metrics to CSV
    results_df = pd.DataFrame.from_dict(results, orient='index')
    results_df.to_csv(output_dir.joinpath('tables/performance.csv'))
    # Plot throughput–latency trade‑off
    plot_throughput_latency({name: {'throughput': m['throughput'], 'latency': m['latency']} for name, m in results.items()},
                            str(output_dir.joinpath('figures/throughput_latency.png')))
    print(f"Main experiment completed. Results saved to {args.output_dir} directory.")


if __name__ == '__main__':
    main()
