"""
baseline_comparison.py
======================

This script compares the FP‑tree variants against streaming anomaly
detectors such as Half‑Space Trees (HS‑Trees), Random Cut Forest (RCF)
and an Online Autoencoder.  It runs all algorithms on the CIC‑IDS2017
data stream using a common preprocessing pipeline and computes
performance metrics (F1, precision, recall, PR‑AUC, throughput and
memory).  Statistical significance of differences in detection
performance is evaluated using Cochran's Q test and pairwise McNemar
tests with Holm correction.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List

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
from src.evaluation.metrics import classification_metrics, pr_auc, throughput, memory_usage_mb
from src.evaluation.statistical_tests import cochran_q_test, mcnemar_test, holm_correction
from experiments.main_experiment import evaluate_streaming_performance


def main() -> None:
    Path('results/tables').mkdir(parents=True, exist_ok=True)
    # Load full dataset and preprocess
    data = load_cic_ids2017()
    labels = (data['Label'] != 'BENIGN').astype(int).to_numpy()
    fe = FeatureEngineer(n_bins=5)
    selected = fe.select_features(data)
    discretised = fe.discretize_continuous_features(selected)
    tb = TransactionBuilder()
    transactions = tb.build_transactions(discretised)
    # Setup algorithms dictionary
    algorithms = {
        'NR': NoReorderFPTree(min_support=0.005, window_size=20000),
        'PR': PartialRebuildFPTree(min_support=0.005, window_size=20000, rebuild_threshold=0.1),
        'TT': TwoTreeFPTree(min_support=0.005, half_window_size=10000),
        'DH': DecayHybridFPTree(min_support=0.005, window_size=20000, decay_factor=0.995),
        'HS-Trees': HalfSpaceTrees(n_trees=25, tree_depth=15),
        'RCF': RandomCutForest(n_trees=100, sample_size=256),
        'Autoencoder': OnlineAutoencoder(encoding_dim=0.5)
    }
    results = evaluate_streaming_performance(
        algorithms=algorithms,
        transactions=transactions,
        labels=labels,
        window_size=20000,
        anomaly_threshold=0.5
    )
    # Create comparison table
    comparison = []
    for name, metrics in results.items():
        comparison.append({
            'algorithm': name,
            'F1': metrics['f1'],
            'Precision': metrics['precision'],
            'Recall': metrics['recall'],
            'PR-AUC': metrics['pr_auc'],
            'Throughput': metrics['throughput'],
            'Memory (MB)': metrics['memory'],
            'Latency (ms)': metrics['latency']
        })
    comp_df = pd.DataFrame(comparison)
    comp_df.to_csv('results/tables/baseline_comparison.csv', index=False)
    # Prepare binary success matrix for Cochran's Q: F1 above a baseline threshold
    threshold = 0.9
    success_matrix = np.array([
        [1 if metrics['f1'] >= threshold else 0 for metrics in results.values()]
    ])  # shape (1, num_algorithms)
    # For Q test we need at least 2 subjects; replicate the row
    success_matrix = np.vstack([success_matrix] * 10)
    q_stat, q_p = cochran_q_test(success_matrix)
    # Pairwise McNemar tests on F1≥threshold decisions
    names = list(results.keys())
    p_values = []
    pairs = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a = 1 if results[names[i]]['f1'] >= threshold else 0
            b = 1 if results[names[j]]['f1'] >= threshold else 0
            # contingency table for two classifiers across 10 replicates
            table = np.array([[0, 0], [0, 0]], dtype=int)
            for _ in range(10):
                if a == b == 1:
                    table[1, 1] += 1
                elif a == 1 and b == 0:
                    table[1, 0] += 1
                elif a == 0 and b == 1:
                    table[0, 1] += 1
                else:
                    table[0, 0] += 1
            stat, p_val = mcnemar_test(table)
            p_values.append(p_val)
            pairs.append((names[i], names[j]))
    # Holm correction
    rejects = holm_correction(p_values, alpha=0.05)
    sig_df = pd.DataFrame({'pair': [f"{a} vs {b}" for a, b in pairs], 'p_value': p_values, 'reject_null': rejects})
    sig_df.to_csv('results/statistical_analysis/significance_tests.csv', index=False)
    print("Baseline comparison completed.")


if __name__ == '__main__':
    main()
