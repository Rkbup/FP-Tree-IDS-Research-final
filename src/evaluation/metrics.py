"""
metrics.py
==========

Utility functions for computing performance metrics for anomaly detection
and classification tasks.  These metrics are used throughout the
experiments to evaluate detection accuracy, throughput, memory usage and
statistical significance.  Where appropriate the implementations
delegate to scikit‑learn functions to ensure correctness.
"""

from __future__ import annotations

from typing import Iterable, Tuple, List

import numpy as np
import psutil
from sklearn.metrics import precision_recall_fscore_support, precision_recall_curve, auc


def classification_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """Compute precision, recall, F1 and support for binary classification.

    Parameters
    ----------
    y_true : np.ndarray
        Ground truth labels (0 for benign, 1 for anomaly).
    y_pred : np.ndarray
        Predicted labels (0/1) or scores thresholded at a chosen τ.

    Returns
    -------
    dict
        Dictionary containing precision, recall, F1 score and support.
    """
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, average='binary', zero_division=0
    )
    return {
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'support': support
    }


def pr_auc(y_true: np.ndarray, scores: np.ndarray) -> float:
    """Compute the area under the Precision–Recall curve.

    Parameters
    ----------
    y_true : np.ndarray
        Ground truth labels (0/1).
    scores : np.ndarray
        Continuous anomaly scores; larger values indicate greater
        anomalousness.

    Returns
    -------
    float
        Area under the PR curve.
    """
    precision, recall, _ = precision_recall_curve(y_true, scores)
    return auc(recall, precision)


def throughput(n_flows: int, elapsed_seconds: float) -> float:
    """Compute throughput in flows per second.

    Parameters
    ----------
    n_flows : int
        Number of flows processed.
    elapsed_seconds : float
        Time taken in seconds.

    Returns
    -------
    float
        Throughput (flows/s).  If ``elapsed_seconds`` is zero, returns 0.
    """
    if elapsed_seconds <= 0:
        return 0.0
    return n_flows / elapsed_seconds


def memory_usage_mb() -> float:
    """Return the current memory usage of the process in megabytes."""
    process = psutil.Process()
    return process.memory_info().rss / (1024 ** 2)


def bootstrap_confidence_interval(data: Iterable[float], n_resamples: int = 10000,
                                  conf_level: float = 0.95) -> Tuple[float, float]:
    """Compute a bootstrap confidence interval for the mean of `data`.

    Parameters
    ----------
    data : iterable of float
        The data samples.
    n_resamples : int, optional
        Number of bootstrap resamples.  Default is 10,000.
    conf_level : float, optional
        Confidence level (e.g. 0.95 for a 95% CI).

    Returns
    -------
    Tuple[float, float]
        Lower and upper confidence bounds.
    """
    values = np.array(list(data))
    if len(values) == 0:
        return (np.nan, np.nan)
    means = []
    rng = np.random.default_rng()
    for _ in range(n_resamples):
        sample = rng.choice(values, size=len(values), replace=True)
        means.append(sample.mean())
    lower = np.percentile(means, (1 - conf_level) / 2 * 100)
    upper = np.percentile(means, (1 + conf_level) / 2 * 100)
    return float(lower), float(upper)
