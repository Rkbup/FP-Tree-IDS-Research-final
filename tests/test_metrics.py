"""
test_metrics
============

Tests for evaluation metrics functions.  These tests verify that
classification metrics and PR‑AUC calculations produce expected values
for simple cases.
"""

import numpy as np

from src.evaluation.metrics import classification_metrics, pr_auc, throughput, memory_usage_mb


def test_classification_metrics_perfect_prediction() -> None:
    labels = np.array([0, 1, 0, 1])
    preds = np.array([0, 1, 0, 1])
    metrics = classification_metrics(labels, preds)
    assert metrics['precision'] == 1.0
    assert metrics['recall'] == 1.0
    assert metrics['f1'] == 1.0


def test_pr_auc_random_prediction() -> None:
    labels = np.array([0, 1, 0, 1])
    scores = np.array([0.1, 0.9, 0.4, 0.6])
    auc = pr_auc(labels, scores)
    # PR‑AUC should be between 0 and 1
    assert 0.0 <= auc <= 1.0


def test_throughput_calculation() -> None:
    n_events = 100
    elapsed = 0.5
    th = throughput(n_events, elapsed)
    assert abs(th - 200.0) < 1e-6


def test_memory_usage_returns_float() -> None:
    mem = memory_usage_mb()
    assert isinstance(mem, float)