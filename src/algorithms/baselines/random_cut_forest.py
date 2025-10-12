"""
random_cut_forest.py
====================

This module implements an approximate Random Cut Forest (RCF) anomaly
detector.  In the absence of a native RCF implementation in scikit‑learn,
we approximate its behaviour using IsolationForest.  RCF and Isolation
Forest both build ensembles of random trees to isolate anomalies, though
RCF uses random cuts in feature space while IsolationForest uses random
splits on single features.  This implementation should therefore be
treated as a baseline rather than a faithful reproduction of RCF.

The API closely mirrors that of the HalfSpaceTrees class.
"""

from __future__ import annotations

from typing import List, Optional

import numpy as np
from sklearn.ensemble import IsolationForest


class RandomCutForest:
    """Random Cut Forest anomaly detector (approximated).

    Parameters
    ----------
    n_trees : int
        Number of trees in the ensemble.
    sample_size : int
        Subsample size for each tree; analogous to the leaf size in RCF.
    contamination : float, optional
        Estimated proportion of anomalies.
    random_state : Optional[int], optional
        Random seed for reproducibility.
    """

    def __init__(self, n_trees: int = 100, sample_size: int = 256,
                 contamination: float = 0.01, random_state: Optional[int] = None) -> None:
        self.n_trees = n_trees
        self.sample_size = sample_size
        self.contamination = contamination
        self.model = IsolationForest(
            n_estimators=n_trees,
            max_samples=sample_size,
            contamination=contamination,
            random_state=random_state,
            n_jobs=-1,
        )
        self._fitted = False

    def fit(self, X: np.ndarray) -> None:
        self.model.fit(X)
        self._fitted = True

    def score_samples(self, X: np.ndarray) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("Model must be fitted before scoring.")
        return -self.model.decision_function(X)
