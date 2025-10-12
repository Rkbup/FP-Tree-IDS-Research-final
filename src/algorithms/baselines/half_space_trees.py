"""
half_space_trees.py
===================

This module implements a simplified Half‑Space Trees (HS‑Trees) anomaly
detector, which serves as a lightweight streaming baseline.  The original
HS‑Trees algorithm partitions the feature space using random hyperplanes
and maintains histograms of region densities to identify anomalies.  Here
we approximate the behaviour using scikit‑learn's IsolationForest,
which also constructs random trees and isolates outliers without
requiring labelled data.

For streaming evaluation the model is trained on a sliding window of
transactions converted into numerical feature vectors.  When the window
shifts the model is retrained.  The anomaly score is the negative
decision function of the IsolationForest; higher scores indicate more
anomalous transactions.
"""

from __future__ import annotations

from typing import List, Optional

import numpy as np
from sklearn.ensemble import IsolationForest


class HalfSpaceTrees:
    """Half‑Space Trees anomaly detector (approximation using IsolationForest).

    Parameters
    ----------
    n_trees : int
        Number of trees in the ensemble.
    tree_depth : int
        Maximum depth of each tree.  In IsolationForest this controls
        the subsample size; we approximate depth by setting
        ``max_samples = 2 ** depth``.
    contamination : float, optional
        Proportion of anomalies expected in the data; influences the
        threshold used to convert scores to flags.  Default 0.01.
    random_state : Optional[int], optional
        Seed for reproducibility.
    """

    def __init__(self, n_trees: int = 25, tree_depth: int = 15,
                 contamination: float = 0.01, random_state: Optional[int] = None) -> None:
        self.n_trees = n_trees
        self.tree_depth = tree_depth
        self.contamination = contamination
        # Estimate subsample size as power of two of depth
        max_samples = min(2 ** tree_depth, 256)
        self.model = IsolationForest(
            n_estimators=n_trees,
            max_samples=max_samples,
            contamination=contamination,
            random_state=random_state,
            n_jobs=-1,
        )
        self._fitted = False

    def fit(self, X: np.ndarray) -> None:
        """Fit the model on a batch of feature vectors.

        Parameters
        ----------
        X : np.ndarray
            Two‑dimensional array of shape ``(n_samples, n_features)``.
        """
        self.model.fit(X)
        self._fitted = True

    def score_samples(self, X: np.ndarray) -> np.ndarray:
        """Return anomaly scores for the given feature vectors.

        Parameters
        ----------
        X : np.ndarray
            Two‑dimensional array of shape ``(n_samples, n_features)``.

        Returns
        -------
        np.ndarray
            Array of anomaly scores; higher values indicate more anomalous
            observations.
        """
        if not self._fitted:
            raise RuntimeError("Model must be fitted before scoring.")
        # IsolationForest returns negative scores for anomalies; negate them
        return -self.model.decision_function(X)
