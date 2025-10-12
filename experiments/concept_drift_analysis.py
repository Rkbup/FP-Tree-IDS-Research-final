"""
concept_drift_analysis.py
=========================

This script evaluates how quickly different FP‑tree variants adapt to
concept drift in network traffic.  In the CIC‑IDS2017 dataset the
distribution of attack types changes from day to day; the primary drift
occurs from Tuesday's brute‑force attacks to Wednesday's DoS attacks
and onward.  We measure two metrics for each variant:

* **Recovery Time (RT):** number of windows required for the F1 score to
  return within ±0.02 of its pre‑drift level after a day change.
* **Stability Score (SS):** variance of F1 scores within each day; lower
  variance indicates more stable performance.

Results are saved to a table in ``results/tables/drift_metrics.csv`` and a
figure showing F1 over time is saved to
``results/figures/drift_f1_over_time.png``.
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
from src.streaming.window_manager import SlidingWindowManager
from src.evaluation.metrics import classification_metrics
from src.evaluation.visualization import plot_drift_f1_over_time


def compute_drift_metrics(f1_series: List[float], day_boundaries: List[int]) -> Dict[str, float]:
    """Compute recovery time and stability score for a single variant.

    Parameters
    ----------
    f1_series : list of float
        F1 score measured at each window index.
    day_boundaries : list of int
        Indices marking the start of new days.

    Returns
    -------
    dict
        Dictionary with keys ``'recovery_time'`` and ``'stability_score'``.
    """
    # Compute baseline F1 as mean of first day
    if not day_boundaries:
        return {'recovery_time': np.nan, 'stability_score': np.var(f1_series)}
    baseline_end = day_boundaries[0]
    baseline_f1 = np.mean(f1_series[:baseline_end])
    # Recovery: after each boundary, find first point within ±0.02 of baseline
    recovery_times = []
    for i, bound in enumerate(day_boundaries):
        if i + 1 < len(day_boundaries):
            segment = f1_series[bound:day_boundaries[i+1]]
        else:
            segment = f1_series[bound:]
        # difference from baseline
        diff = np.abs(np.array(segment) - baseline_f1)
        within = np.where(diff <= 0.02)[0]
        if within.size > 0:
            recovery_times.append(within[0])
        else:
            recovery_times.append(len(segment))
    # Stability: variance within each day
    stabilities = []
    for i, bound in enumerate(day_boundaries):
        if i + 1 < len(day_boundaries):
            segment = f1_series[bound:day_boundaries[i+1]]
        else:
            segment = f1_series[bound:]
        stabilities.append(float(np.var(segment)))
    return {
        'recovery_time': float(np.mean(recovery_times)),
        'stability_score': float(np.mean(stabilities))
    }


def main() -> None:
    Path('results/figures').mkdir(parents=True, exist_ok=True)
    Path('results/tables').mkdir(parents=True, exist_ok=True)
    # Load data for all days in order
    data = load_cic_ids2017()
    labels = (data['Label'] != 'BENIGN').astype(int).to_numpy()
    fe = FeatureEngineer(n_bins=5)
    selected = fe.select_features(data)
    discretised = fe.discretize_continuous_features(selected)
    tb = TransactionBuilder()
    transactions = tb.build_transactions(discretised)
    # Determine day boundaries based on 'Timestamp' column if present
    day_boundaries: List[int] = []
    if 'Timestamp' in data.columns:
        timestamps = pd.to_datetime(data['Timestamp'])
        days = timestamps.dt.day
        current_day = days.iloc[0]
        for idx, d in enumerate(days):
            if d != current_day:
                day_boundaries.append(idx)
                current_day = d
    # Instantiate variants
    variants = {
        'NR': NoReorderFPTree(min_support=0.005, window_size=20000),
        'PR': PartialRebuildFPTree(min_support=0.005, window_size=20000, rebuild_threshold=0.1),
        'TT': TwoTreeFPTree(min_support=0.005, half_window_size=10000),
        'DH': DecayHybridFPTree(min_support=0.005, window_size=20000, decay_factor=0.995)
    }
    # Process transactions and record F1 per window
    window_size = 20000
    f1_timeseries: Dict[str, List[float]] = {name: [] for name in variants}
    for name, alg in variants.items():
        window_manager = SlidingWindowManager(alg, max_size=window_size)
        y_pred: List[int] = []
        f1_list: List[float] = []
        for idx, txn in enumerate(transactions):
            window_manager.update(txn)
            # simplistic scoring: use rarity measure
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
            # compute F1 every 1000 flows
            if (idx + 1) % 1000 == 0:
                y_true_slice = labels[idx-999:idx+1]
                y_pred_slice = np.array(y_pred[-1000:])
                f1 = classification_metrics(y_true_slice, y_pred_slice)['f1']
                f1_list.append(f1)
        f1_timeseries[name] = f1_list
    # Compute drift metrics per variant
    metrics_rows = []
    for name, f1_series in f1_timeseries.items():
        met = compute_drift_metrics(f1_series, day_boundaries=[b//1000 for b in day_boundaries])
        metrics_rows.append({'variant': name, **met})
    drift_df = pd.DataFrame(metrics_rows)
    drift_df.to_csv('results/tables/drift_metrics.csv', index=False)
    # Plot F1 over time
    plot_drift_f1_over_time(f1_timeseries, day_boundaries=[b//1000 for b in day_boundaries],
                            filepath='results/figures/drift_f1_over_time.png')
    print("Concept drift analysis completed.")


if __name__ == '__main__':
    main()
