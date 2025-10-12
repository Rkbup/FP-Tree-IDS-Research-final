"""
statistical_tests.py
====================

This module implements statistical significance tests used to compare
multiple algorithms across the same set of observations.  The tests
included are Cochran's Q test (for comparing more than two correlated
binary classifiers) and McNemar's test (for pairwise comparison of
two classifiers).  In addition we provide a Holm–Bonferroni
correction function to adjust p‑values when performing multiple
comparisons.
"""

from __future__ import annotations

from typing import Iterable, List, Tuple

import numpy as np
from scipy import stats


def cochran_q_test(success_matrix: np.ndarray) -> Tuple[float, float]:
    """Perform Cochran's Q test on a matrix of binary outcomes.

    Parameters
    ----------
    success_matrix : np.ndarray
        A two‑dimensional array of shape ``(n_subjects, k)`` where
        ``k`` is the number of methods and each entry is 0 or 1
        indicating success (e.g. correct detection) for the subject.

    Returns
    -------
    statistic : float
        The Q statistic.
    p_value : float
        The p‑value obtained by comparing the statistic to a chi‑square
        distribution with ``k-1`` degrees of freedom.
    """
    if success_matrix.ndim != 2:
        raise ValueError("success_matrix must be two-dimensional")
    n, k = success_matrix.shape
    # Sum across methods for each subject and across subjects for each method
    row_sums = success_matrix.sum(axis=1)
    col_sums = success_matrix.sum(axis=0)
    # Compute Q statistic (see Cochran 1950)
    numerator = (k - 1) * (k * np.sum(col_sums ** 2) - (np.sum(col_sums) ** 2))
    denominator = k * np.sum(row_sums) - np.sum(row_sums ** 2)
    if denominator == 0:
        return 0.0, 1.0
    q_stat = numerator / denominator
    p_value = 1 - stats.chi2.cdf(q_stat, df=k - 1)
    return float(q_stat), float(p_value)


def mcnemar_test(table: np.ndarray) -> Tuple[float, float]:
    """Perform McNemar's test for two related binary classifiers.

    Parameters
    ----------
    table : np.ndarray
        A 2×2 contingency table with elements

            [[n00, n01],
             [n10, n11]]

        where ``n01`` is the count of instances misclassified by
        classifier A but not by classifier B, and ``n10`` is the count of
        instances misclassified by classifier B but not by classifier A.

    Returns
    -------
    statistic : float
        The chi‑square statistic with continuity correction.
    p_value : float
        The p‑value from the chi‑square distribution with 1 degree of
        freedom.
    """
    if table.shape != (2, 2):
        raise ValueError("Input contingency table must be 2x2")
    n01 = table[0, 1]
    n10 = table[1, 0]
    # Use continuity correction
    diff = abs(n01 - n10) - 1
    chi2 = (diff ** 2) / (n01 + n10) if (n01 + n10) > 0 else 0.0
    p_value = 1 - stats.chi2.cdf(chi2, df=1)
    return float(chi2), float(p_value)


def holm_correction(p_values: List[float], alpha: float = 0.05) -> List[bool]:
    """Apply Holm–Bonferroni correction to a list of p‑values.

    Parameters
    ----------
    p_values : list of float
        Raw p‑values to correct.
    alpha : float, optional
        Family‑wise error rate.  Default is 0.05.

    Returns
    -------
    list of bool
        A list indicating whether each hypothesis is rejected (True) or
        not (False) after correction.
    """
    m = len(p_values)
    # Sort p‑values and keep track of original indices
    sorted_indices = np.argsort(p_values)
    sorted_p = np.array(p_values)[sorted_indices]
    rejections = [False] * m
    for i, p in enumerate(sorted_p):
        threshold = alpha / (m - i)
        if p <= threshold:
            rejections[sorted_indices[i]] = True
        else:
            # Once a p‑value is not significant, all larger p‑values are also
            # not significant
            break
    return rejections
