"""
sensitivity_analysis.py
=======================

This script explores how the performance of each FP‑tree variant varies
with respect to key parameters: anomaly threshold τ, window size N,
minimum support σ and memory usage.  The results are plotted in a
four‑panel figure analogous to Figure 7 in the paper.  A summary
table is also written to ``results/tables/sensitivity_summary.csv``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from pathlib import Path

from src.preprocessing.data_loader import load_cic_ids2017
from src.preprocessing.feature_engineering import FeatureEngineer
from src.preprocessing.transaction_builder import TransactionBuilder
from src.algorithms.variants.no_reorder import NoReorderFPTree
from src.algorithms.variants.partial_rebuild import PartialRebuildFPTree
from src.algorithms.variants.two_tree import TwoTreeFPTree
from src.algorithms.variants.decay_hybrid import DecayHybridFPTree
from src.evaluation.metrics import classification_metrics, pr_auc, memory_usage_mb
from src.evaluation.visualization import plot_sensitivity_curves
from src.streaming.window_manager import SlidingWindowManager


def main() -> None:
    Path('results/figures').mkdir(parents=True, exist_ok=True)
    Path('results/tables').mkdir(parents=True, exist_ok=True)
    # Load and preprocess a subset of the data for efficiency
    data = load_cic_ids2017()
    # Use only first 50k flows for sensitivity analysis
    data = data.iloc[:50000]
    labels = (data['Label'] != 'BENIGN').astype(int).to_numpy()
    fe = FeatureEngineer(n_bins=5)
    selected = fe.select_features(data)
    discretised = fe.discretize_continuous_features(selected)
    tb = TransactionBuilder()
    transactions = tb.build_transactions(discretised)
    # Parameter ranges
    tau_values = np.linspace(0.1, 0.9, 5)
    window_sizes = [5000, 10000, 20000, 50000]
    sigma_values = [0.001, 0.005, 0.01, 0.02]
    # Build variants
    variants = {
        'PR': PartialRebuildFPTree(min_support=0.005, window_size=20000, rebuild_threshold=0.1),
        'NR': NoReorderFPTree(min_support=0.005, window_size=20000),
        'TT': TwoTreeFPTree(min_support=0.005, half_window_size=10000),
        'DH': DecayHybridFPTree(min_support=0.005, window_size=20000, decay_factor=0.995)
    }
    # Prepare container for curves
    curves = {name: {'tau': list(tau_values), 'f1_tau': [],
                     'window_size': window_sizes, 'f1_n': [],
                     'sigma': [s * 100 for s in sigma_values], 'pr_auc': [],
                     'memory': []} for name in variants}
    # F1 vs τ (fix window, sigma)
    for name, alg in variants.items():
        for tau in tau_values:
            window_manager = SlidingWindowManager(alg, max_size=20000)
            y_pred = []
            for idx, txn in enumerate(transactions):
                window_manager.update(txn)
                patterns = alg.mine_frequent_patterns() if hasattr(alg, 'mine_frequent_patterns') else alg.mine_frequent_patterns()
                score = 1.0
                if patterns:
                    if isinstance(alg, TwoTreeFPTree):
                        max_support = max(patterns.values())
                        score = 1.0 - (max_support / (2 * alg.half_window_size))
                    else:
                        max_support = max(patterns.values())
                        score = 1.0 - (max_support / max(1, len(window_manager.window)))
                y_pred.append(1 if score >= tau else 0)
            metrics = classification_metrics(labels[:len(y_pred)], np.array(y_pred))
            curves[name]['f1_tau'].append(metrics['f1'])
        # Reset algorithm state for next experiment
        variants[name] = type(alg)(min_support=0.005, window_size=20000)  # reinitialise
    # F1 vs N
    for name, alg in variants.items():
        f1_values = []
        for N in window_sizes:
            alg = type(alg)(min_support=0.005, window_size=N)
            window_manager = SlidingWindowManager(alg, max_size=N)
            y_pred = []
            for idx, txn in enumerate(transactions[:N]):
                window_manager.update(txn)
                patterns = alg.mine_frequent_patterns() if hasattr(alg, 'mine_frequent_patterns') else alg.mine_frequent_patterns()
                score = 1.0
                if patterns:
                    if isinstance(alg, TwoTreeFPTree):
                        max_support = max(patterns.values())
                        score = 1.0 - (max_support / (2 * alg.half_window_size))
                    else:
                        max_support = max(patterns.values())
                        score = 1.0 - (max_support / max(1, len(window_manager.window)))
                y_pred.append(1 if score >= 0.5 else 0)
            metrics = classification_metrics(labels[:len(y_pred)], np.array(y_pred))
            f1_values.append(metrics['f1'])
        curves[name]['f1_n'] = f1_values
    # PR-AUC vs sigma (vary support threshold).  We simulate by adjusting min_support of algorithm.
    for name, alg in variants.items():
        pr_values = []
        for sigma in sigma_values:
            alg = type(alg)(min_support=sigma, window_size=20000)
            window_manager = SlidingWindowManager(alg, max_size=20000)
            scores = []
            for idx, txn in enumerate(transactions):
                window_manager.update(txn)
                patterns = alg.mine_frequent_patterns() if hasattr(alg, 'mine_frequent_patterns') else alg.mine_frequent_patterns()
                score = 1.0
                if patterns:
                    if isinstance(alg, TwoTreeFPTree):
                        max_support = max(patterns.values())
                        score = 1.0 - (max_support / (2 * alg.half_window_size))
                    else:
                        max_support = max(patterns.values())
                        score = 1.0 - (max_support / max(1, len(window_manager.window)))
                scores.append(score)
            pr_values.append(pr_auc(labels[:len(scores)], np.array(scores)))
        curves[name]['pr_auc'] = pr_values
    # Memory usage vs N. We sample memory after building a tree of size N
    for name, alg in variants.items():
        mem_list = []
        for N in window_sizes:
            alg = type(alg)(min_support=0.005, window_size=N)
            window_manager = SlidingWindowManager(alg, max_size=N)
            for idx, txn in enumerate(transactions[:N]):
                window_manager.update(txn)
            mem_list.append(memory_usage_mb())
        curves[name]['memory'] = mem_list
    # Plot curves
    plot_sensitivity_curves(curves, filepath='results/figures/sensitivity_analysis.png')
    # Save summary table
    summary_rows = []
    for name in variants:
        for tau, f1_tau in zip(curves[name]['tau'], curves[name]['f1_tau']):
            summary_rows.append({'variant': name, 'parameter': f'tau={tau:.2f}', 'F1': f1_tau})
        for N, f1_n in zip(curves[name]['window_size'], curves[name]['f1_n']):
            summary_rows.append({'variant': name, 'parameter': f'N={N}', 'F1': f1_n})
        for sigma, pr in zip(curves[name]['sigma'], curves[name]['pr_auc']):
            summary_rows.append({'variant': name, 'parameter': f'sigma={sigma:.3f}%', 'PR-AUC': pr})
        for N, mem in zip(curves[name]['window_size'], curves[name]['memory']):
            summary_rows.append({'variant': name, 'parameter': f'N={N}', 'Memory (MB)': mem})
    pd.DataFrame(summary_rows).to_csv('results/tables/sensitivity_summary.csv', index=False)
    print("Sensitivity analysis completed.")


if __name__ == '__main__':
    main()
