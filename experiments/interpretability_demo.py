"""
interpretability_demo.py
========================

This script demonstrates the interpretability of the Partial
Rebuild FP‑tree variant by flagging a rare pattern in the
CIC‑IDS2017 dataset and analysing the underlying itemset.  The
script processes the data in a streaming fashion, applies the PR
variant and prints the first anomalous transaction detected along
with the most infrequent itemset that triggered the alert.  It also
contrasts the suspicious transaction with typical benign patterns.

Usage:

    python experiments/interpretability_demo.py

The output will be printed to the console and stored in
``results/interpretability_report.txt``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

from src.preprocessing.data_loader import load_cic_ids2017
from src.preprocessing.feature_engineering import FeatureEngineer
from src.preprocessing.transaction_builder import TransactionBuilder
from src.algorithms.variants.partial_rebuild import PartialRebuildFPTree
from src.streaming.window_manager import SlidingWindowManager


def rarity_score(patterns: Dict[Tuple[str, ...], int], window_size: int) -> float:
    """Compute the rarity score as in Eq. (1): 1 − max support / window size.

    If no patterns are mined, returns 1.0 (most anomalous).

    Parameters
    ----------
    patterns : dict
        Frequent patterns mined from the FP‑tree.
    window_size : int
        Current sliding window length.

    Returns
    -------
    float
        Rarity score in [0, 1].
    """
    if not patterns:
        return 1.0
    max_support = max(patterns.values())
    return 1.0 - max_support / max(1, window_size)


def run_demo() -> None:
    """Run the interpretability demonstration.

    Processes the full dataset using the Partial Rebuild FP‑tree
    variant and prints the first anomalous transaction detected above
    a rarity threshold.  The underlying rare itemset is extracted and
    a comparison to benign patterns is presented.
    """
    # Ensure results directory exists
    Path('results').mkdir(exist_ok=True)
    # Load data and precompute transactions
    data = load_cic_ids2017()
    labels = (data['Label'] != 'BENIGN').astype(int).to_numpy()
    fe = FeatureEngineer(n_bins=5)
    selected = fe.select_features(data)
    discretised = fe.discretize_continuous_features(selected)
    tb = TransactionBuilder()
    transactions = tb.build_transactions(discretised)
    # Instantiate Partial Rebuild FP‑tree with moderate parameters
    pr_tree = PartialRebuildFPTree(min_support=0.005, window_size=20000, rebuild_threshold=0.1)
    window_manager = SlidingWindowManager(pr_tree, max_size=20000)
    threshold = 0.5  # threshold for rarity score
    flagged_index = None
    flagged_txn: List[str] = []
    flagged_score = 0.0
    # Maintain aggregate statistics for benign patterns (for contrast)
    benign_counts: Dict[str, int] = {}
    benign_total = 0
    for idx, txn in enumerate(transactions):
        window_manager.update(txn)
        # Update benign statistics if flow is benign
        if labels[idx] == 0:
            benign_total += 1
            for item in txn:
                benign_counts[item] = benign_counts.get(item, 0) + 1
        # Compute rarity of current transaction
        patterns = pr_tree.mine_frequent_patterns()
        score = rarity_score(patterns, len(window_manager.window))
        if score >= threshold and flagged_index is None:
            # First anomaly detected
            flagged_index = idx
            flagged_txn = txn
            flagged_score = score
            break
    if flagged_index is None:
        report = "No anomalous transaction found above the threshold."
    else:
        # Determine rarest itemset within flagged transaction: find the
        # item with lowest frequency in benign data as a proxy
        # (frequency is approximated by benign_counts).  If an item is
        # unseen in benign flows, its frequency is zero.
        rare_item = min(flagged_txn, key=lambda i: benign_counts.get(i, 0))
        report_lines = []
        report_lines.append(f"First anomalous transaction at index {flagged_index} with rarity score {flagged_score:.3f}\n")
        report_lines.append("Flagged transaction items:")
        report_lines.extend([f"  - {item}" for item in flagged_txn])
        report_lines.append("\nMost rare item in flagged transaction (based on benign frequency):")
        report_lines.append(f"  {rare_item}\n")
        # Provide context on why this item may be suspicious
        # For example, if destination port is an unusual value with SYN flag
        if 'dst_port' in rare_item and any('flags_SYN=1' in it for it in flagged_txn):
            report_lines.append("Security rationale: A TCP SYN to a rare destination port may indicate a port scan or backdoor probe.")
        elif 'duration_bin=Very_Short' in flagged_txn:
            report_lines.append("Security rationale: Very short connections with very low bytes often correspond to reconnaissance scans.")
        else:
            report_lines.append("Security rationale: Combination of features is unusual compared to benign distribution.")
        # Summarise typical benign patterns
        sorted_counts = sorted(benign_counts.items(), key=lambda kv: kv[1], reverse=True)[:5]
        report_lines.append("\nMost common benign items (top 5):")
        for item, count in sorted_counts:
            report_lines.append(f"  - {item}: {count / max(1, benign_total):.2%} of benign flows")
        report = "\n".join(report_lines)
    # Write report to file
    with open('results/interpretability_report.txt', 'w') as f:
        f.write(report)
    print(report)


if __name__ == '__main__':
    run_demo()