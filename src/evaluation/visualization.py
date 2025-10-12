"""
visualization.py
================

Functions to generate plots summarising the experimental results.  These
utilities build on Matplotlib and Seaborn to create publication‑quality
figures that illustrate throughput–latency trade‑offs, parameter
sensitivity, concept drift adaptation, and other metrics.  All
functions save the generated figures to disk rather than displaying
them interactively.
"""

from __future__ import annotations

from typing import Dict, List, Optional

import matplotlib.pyplot as plt
import numpy as np


def plot_throughput_latency(results: Dict[str, Dict[str, float]], filepath: str) -> None:
    """Create a throughput–latency scatter plot for multiple variants.

    Parameters
    ----------
    results : dict
        Mapping from variant names to a dictionary containing at least
        ``'throughput'`` and ``'latency'`` keys.
    filepath : str
        Destination path for the saved figure (PNG or PDF).
    """
    fig, ax = plt.subplots(figsize=(6, 4))
    for variant, metrics in results.items():
        ax.scatter(metrics['latency'], metrics['throughput'], label=variant)
        ax.annotate(variant, (metrics['latency'], metrics['throughput']),
                    textcoords="offset points", xytext=(5, 5), ha='left')
    ax.set_xlabel('Latency (ms)')
    ax.set_ylabel('Throughput (flows/s)')
    ax.set_title('Throughput–Latency Trade‑off')
    ax.grid(True, linestyle='--', alpha=0.5)
    ax.legend()
    fig.tight_layout()
    fig.savefig(filepath)
    plt.close(fig)


def plot_sensitivity_curves(curves: Dict[str, Dict[str, List[float]]], filepath: str) -> None:
    """Plot sensitivity curves for FP‑tree variants.

    Expects a nested dictionary with keys 'tau', 'window_size', 'sigma',
    'memory' for each variant, each mapping to a list of values over the
    x‑axis.  All variants should share the same x‑axis values for each
    subplot.

    Parameters
    ----------
    curves : dict
        Mapping from variant names to dictionaries of metric lists.
    filepath : str
        Destination file for the 2×2 panel figure.
    """
    fig, axs = plt.subplots(2, 2, figsize=(10, 8))
    # Determine x‑axes from first variant
    variants = list(curves.keys())
    example = curves[variants[0]]
    tau_vals = example['tau']
    n_vals = example['window_size']
    sigma_vals = example['sigma']
    mem_vals = example['window_size']  # x‑axis for memory vs N
    for variant, vals in curves.items():
        axs[0, 0].plot(tau_vals, vals['f1_tau'], label=variant)
        axs[0, 1].plot(n_vals, vals['f1_n'], label=variant)
        axs[1, 0].plot(sigma_vals, vals['pr_auc'], label=variant)
        axs[1, 1].plot(mem_vals, vals['memory'], label=variant)
    axs[0, 0].set_xlabel('Anomaly threshold τ')
    axs[0, 0].set_ylabel('F1 score')
    axs[0, 1].set_xlabel('Window size N')
    axs[0, 1].set_ylabel('F1 score')
    axs[1, 0].set_xlabel('Min support σ (%)')
    axs[1, 0].set_ylabel('PR‑AUC')
    axs[1, 1].set_xlabel('Window size N')
    axs[1, 1].set_ylabel('Memory usage (MB)')
    for ax in axs.ravel():
        ax.grid(True, linestyle='--', alpha=0.5)
    axs[0, 0].legend()
    fig.suptitle('Sensitivity Analysis of FP‑Tree Variants', fontsize=14)
    fig.tight_layout(rect=[0, 0.03, 1, 0.95])
    fig.savefig(filepath)
    plt.close(fig)


def plot_drift_f1_over_time(f1_timeseries: Dict[str, List[float]], day_boundaries: Optional[List[int]], filepath: str) -> None:
    """Plot F1 score over time for concept drift adaptation analysis.

    Parameters
    ----------
    f1_timeseries : dict
        Mapping from variant name to a list of F1 scores over time (per
        window).
    day_boundaries : list of int, optional
        Indices in the time series where day transitions occur.  Dashed
        vertical lines will be drawn at these positions.
    filepath : str
        Destination file for the plot.
    """
    fig, ax = plt.subplots(figsize=(8, 4))
    n_points = len(next(iter(f1_timeseries.values())))
    x = np.arange(n_points)
    for variant, scores in f1_timeseries.items():
        ax.plot(x, scores, label=variant)
    if day_boundaries:
        for b in day_boundaries:
            ax.axvline(b, linestyle='--', color='grey', alpha=0.7)
    ax.set_xlabel('Window index')
    ax.set_ylabel('F1 score')
    ax.set_title('Concept Drift Adaptation: F1 over time')
    ax.grid(True, linestyle='--', alpha=0.5)
    ax.legend()
    fig.tight_layout()
    fig.savefig(filepath)
    plt.close(fig)
