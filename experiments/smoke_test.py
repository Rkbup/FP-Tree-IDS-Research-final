"""
smoke_test.py
==============

This script runs a minimal subset of the pipeline to verify that the
major components integrate correctly.  It is intended to be used in
continuous integration (CI) to catch obvious problems early.  The
script processes only a small portion of the CIC‑IDS2017 dataset (e.g.
the first 5 000 flows) with a simplified configuration.

Usage::

    python experiments/smoke_test.py

The test prints a small summary of metrics for one FP‑tree variant and
ensures that no errors are raised.
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from src.preprocessing.data_loader import load_cic_ids2017
from src.preprocessing.feature_engineering import FeatureEngineer
from src.preprocessing.transaction_builder import TransactionBuilder
from src.algorithms.variants.no_reorder import NoReorderFPTree
from src.streaming.window_manager import SlidingWindowManager
from src.evaluation.metrics import classification_metrics, pr_auc, throughput


def run_smoke_test() -> None:
    """Execute a lightweight end‑to‑end test of the pipeline.

    Loads a subset of the dataset, constructs transactions, runs the
    No‑Reorder FP‑tree variant on a small sliding window and reports
    basic performance metrics.  This function is intentionally
    minimal to avoid long runtimes in CI.
    """
    # Limit to a small number of flows for speed
    max_flows = 5000
    data = load_cic_ids2017()
    # Use only the first `max_flows` rows to keep the test lightweight
    data = data.iloc[:max_flows].copy()
    labels = (data['Label'] != 'BENIGN').astype(int).to_numpy()
    fe = FeatureEngineer(n_bins=3)
    selected = fe.select_features(data)
    discretised = fe.discretize_continuous_features(selected)
    tb = TransactionBuilder()
    transactions = tb.build_transactions(discretised)
    alg = NoReorderFPTree(min_support=0.01, window_size=5000)
    window_manager = SlidingWindowManager(alg, max_size=5000)
    y_pred = np.zeros(len(transactions), dtype=np.int8)
    scores = np.zeros(len(transactions), dtype=np.float32)
    start_time = time.time()
    for idx, txn in enumerate(transactions):
        window_manager.update(txn)
        patterns = alg.mine_frequent_patterns()
        score = 1.0
        if patterns:
            max_support = max(patterns.values())
            score = 1.0 - max_support / max(1, len(window_manager.window))
        scores[idx] = score
        y_pred[idx] = 1 if score >= 0.5 else 0
    elapsed = time.time() - start_time
    metrics = classification_metrics(labels, y_pred)
    metrics['pr_auc'] = pr_auc(labels, scores)
    metrics['throughput'] = throughput(len(transactions), elapsed)
    print("Smoke test complete. Metrics:\n", metrics)


if __name__ == '__main__':
    run_smoke_test()