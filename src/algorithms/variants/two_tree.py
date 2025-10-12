"""
two_tree.py
===========

This module implements the **Two‑Tree (TT)** variant of the sliding‑window
FP‑tree.  TT maintains two FP‑trees corresponding to two half‑windows of
equal size.  Incoming transactions are inserted into the *current* tree
until the half‑window length is exceeded; then the current tree becomes
the *previous* tree, and a new current tree is created for the next half
window.  The previous tree is discarded once the second half is full,
effectively realising a sliding window of length ``2 * half_window_size``.

The advantage of TT is that it avoids the overhead of per‑transaction
deletions: old transactions expire en masse when a half window is
completed.  This yields high throughput but suffers from stale counts in
the previous half window, which can reduce precision【550642539765669†L846-L869】.

Attributes
----------
half_window_size : int
    Number of transactions in each half window.  The full window size is
    therefore ``2 * half_window_size``.

current_tree : FPTree
    FP‑tree storing transactions in the current half window.

old_tree : FPTree
    FP‑tree storing transactions in the previous half window.

current_window : deque
    History of transactions in the current half window.

old_window : deque
    History of transactions in the previous half window.

Note
----
This class implements only insertion; individual deletions are not
supported.  When a half window is full, the previous window is dropped
and the current window becomes the new previous window.
"""

from __future__ import annotations

from collections import deque
from typing import List

from ..fp_tree import FPTree


class TwoTreeFPTree:
    """Two‑Tree FP‑tree variant for high‑throughput streaming.

    Parameters
    ----------
    min_support : float
        Minimum support threshold for pattern mining within each half window.
    half_window_size : int
        Size of each half window in number of transactions.  The full
        sliding window covers two half windows.
    """

    def __init__(self, min_support: float = 0.01, half_window_size: int = 10_000) -> None:
        self.min_support = min_support
        self.half_window_size = half_window_size
        self.current_tree = FPTree(min_support=min_support, window_size=half_window_size)
        self.old_tree = FPTree(min_support=min_support, window_size=half_window_size)
        self.current_window: deque[List[str]] = deque()
        self.old_window: deque[List[str]] = deque()

    def insert_transaction(self, transaction: List[str]) -> None:
        """Insert a transaction into the current half window.

        When the current half window exceeds its capacity, the previous
        window is dropped, the current tree and window become the old
        structures, and a new empty current tree is created for the next
        half window.  This implements a sliding window of size
        ``2 * half_window_size``.
        """
        # Insert into current tree
        self.current_tree.insert_transaction(transaction)
        self.current_window.append(transaction)
        # If current half window exceeds capacity, rotate windows
        if len(self.current_window) > self.half_window_size:
            # Discard old structures
            self.old_tree = self.current_tree
            self.old_window = self.current_window
            # Create new empty current structures
            self.current_tree = FPTree(min_support=self.min_support, window_size=self.half_window_size)
            self.current_window = deque()

    def mine_frequent_patterns(self) -> dict:
        """Mine frequent itemsets across both half windows.

        This method merges the pattern counts from the current and old trees.
        Because items may appear in both windows, support counts are summed.
        The returned patterns include only those that meet the support
        threshold within at least one half window.  Patterns with total
        support below ``min_support * (2 * half_window_size)`` are filtered.
        """
        patterns: dict = {}
        # Mine patterns from each tree separately
        current_patterns = self.current_tree.mine_frequent_patterns()
        old_patterns = self.old_tree.mine_frequent_patterns()
        # Merge counts
        for pat, cnt in current_patterns.items():
            patterns[pat] = patterns.get(pat, 0) + cnt
        for pat, cnt in old_patterns.items():
            patterns[pat] = patterns.get(pat, 0) + cnt
        # Filter by combined support threshold
        min_count = int(self.min_support * (2 * self.half_window_size))
        return {pat: cnt for pat, cnt in patterns.items() if cnt >= min_count}
