"""
window_manager.py
=================

This module defines a simple sliding window manager for streaming
transactions.  It serves as a thin wrapper around the FP‑tree
algorithms, handling insertion of new transactions and, when necessary,
removal of expired ones.  For variants that manage their own window
(e.g. Two‑Tree and Decay‑Hybrid), the window manager delegates
maintenance to the underlying algorithm.
"""

from __future__ import annotations

from collections import deque
from typing import Iterable, List, Tuple


class SlidingWindowManager:
    """Maintain a sliding window of transactions for an FP‑tree variant.

    Parameters
    ----------
    algorithm : object
        An instance of an FP‑tree variant (e.g. :class:`FPTree` or
        :class:`TwoTreeFPTree`).  The algorithm must implement an
        ``insert_transaction`` method and optionally ``remove_transaction``.
    max_size : int
        Maximum number of transactions to retain.  For algorithms that
        internally manage two half windows, ``max_size`` should be set to
        twice the half‑window size.
    """

    def __init__(self, algorithm: Any, max_size: int) -> None:
        self.algorithm = algorithm
        self.max_size = max_size
        self.window: deque[List[str]] = deque()

    def update(self, transaction: List[str]) -> None:
        """Insert a transaction and evict expired transactions.

        If the window exceeds ``max_size`` the oldest transaction is
        removed by calling the algorithm's ``remove_transaction`` method.
        For two‑tree and decay‑hybrid variants no explicit removal is
        needed because the algorithm handles expiration internally.
        """
        # Insert new transaction
        self.algorithm.insert_transaction(transaction)
        # Append to history for explicit eviction (if supported)
        self.window.append(transaction)
        # Check window size
        if len(self.window) > self.max_size:
            expired = self.window.popleft()
            # Try to call remove_transaction if available
            remove_fn = getattr(self.algorithm, 'remove_transaction', None)
            if callable(remove_fn):
                remove_fn(expired)
