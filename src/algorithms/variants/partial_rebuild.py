"""
partial_rebuild.py
==================

This module implements the **Partial Rebuild (PR)** variant of the
sliding‑window FP‑tree.  PR dynamically reorganises the FP‑tree structure
whenever item frequency drifts exceed a specified threshold.  Unlike
CanTree (fixed global item order) or CPS‑Tree (continuous reordering)【550642539765669†L846-L869】,
PR only rebuilds *affected subtrees* when item ranks change significantly,
thereby balancing the trade‑off between compactness and computational
overhead.

The algorithm tracks item frequencies over time and triggers a partial
rebuild when the relative change in rank exceeds ``rebuild_threshold``.
Rebuilding involves reconstructing the FP‑tree with transactions sorted
according to the new frequency order.  The implementation here takes a
simplified approach: when a rebuild is triggered, the entire tree is
reconstructed from the current sliding window.  For large windows this
incurs additional cost, but in practice rebuilds occur infrequently and
the windows are bounded (≤50k)【550642539765669†L846-L869】.

Attributes
----------
rebuild_threshold : float
    The maximum allowable relative change in item rank before a rebuild is
    triggered.  A threshold of 0.1 means that if an item’s rank changes by
    more than 10% of the total number of items, a rebuild is initiated.

item_frequencies : Counter
    Tracks the frequency counts of individual items in the current window.

prev_ranks : Dict[str, int]
    Stores the previous rank ordering of items.  Used to detect rank
    drift.
"""

from __future__ import annotations

from collections import Counter
from typing import Dict, List, Tuple

from ..fp_tree import FPTree, FPNode


class PartialRebuildFPTree(FPTree):
    """Partial‑Rebuild FP‑tree variant with dynamic reordering.

    Parameters
    ----------
    rebuild_threshold : float
        Relative change in item rank that triggers a rebuild (between 0 and 1).
    kwargs : dict
        Additional keyword arguments forwarded to :class:`~FPTree`.
    """

    def __init__(self, rebuild_threshold: float = 0.1, **kwargs) -> None:
        super().__init__(**kwargs)
        self.rebuild_threshold = rebuild_threshold
        self.item_frequencies: Counter[str] = Counter()
        self.prev_ranks: Dict[str, int] = {}

    # ------------------------------------------------------------------
    # Overridden insertion/removal methods
    # ------------------------------------------------------------------

    def insert_transaction(self, transaction: List[str]) -> None:
        # Update item frequencies
        self.item_frequencies.update(transaction)
        super().insert_transaction(transaction)
        # Check if the rank ordering has drifted significantly
        if self._check_rebuild_condition():
            self.partial_rebuild()

    def remove_transaction(self, transaction: List[str]) -> None:
        # Update item frequencies
        self.item_frequencies.subtract(transaction)
        super().remove_transaction(transaction)
        # Keep frequencies non‑negative
        for item in list(self.item_frequencies):
            if self.item_frequencies[item] <= 0:
                del self.item_frequencies[item]

    # ------------------------------------------------------------------
    # Rebuild logic
    # ------------------------------------------------------------------

    def _check_rebuild_condition(self) -> bool:
        """Return ``True`` if a rebuild is required due to rank drift.

        The method computes the current item ranks (by descending frequency)
        and compares them with the previous ranks.  If the maximum relative
        change in rank across all items exceeds ``rebuild_threshold`` the
        method returns ``True``; otherwise it returns ``False``.
        """
        if not self.item_frequencies:
            return False
        # Compute current ranks: sort items by decreasing frequency
        sorted_items = [item for item, _ in self.item_frequencies.most_common()]
        current_ranks: Dict[str, int] = {item: idx for idx, item in enumerate(sorted_items)}
        # If no previous ranks, initialise and do not trigger rebuild
        if not self.prev_ranks:
            self.prev_ranks = current_ranks
            return False
        # Compute relative rank changes
        max_items = max(len(self.prev_ranks), len(current_ranks))
        max_change = 0.0
        for item, curr_rank in current_ranks.items():
            prev_rank = self.prev_ranks.get(item, max_items)
            change = abs(curr_rank - prev_rank) / max(1, max_items)
            max_change = max(max_change, change)
        self.prev_ranks = current_ranks
        return max_change > self.rebuild_threshold

    def partial_rebuild(self) -> None:
        """Rebuild the FP‑tree to reflect the current item ordering.

        This method discards the existing tree and reconstructs it by
        inserting all transactions in the window according to the new
        frequency order.  For simplicity we rebuild the entire tree rather
        than selectively rebuilding subtrees.  In a production system this
        could be optimised to only rebuild paths affected by the rank change.
        """
        # Extract all transactions from the window
        transactions = list(self._window)
        # Reset tree structures
        self.root = FPNode(item=None, count=0)  # type: ignore[name-defined]
        self.header_table.clear()
        # Reinsert transactions sorted by current frequency order
        # Compute global order once for efficiency
        sorted_items = [item for item, _ in self.item_frequencies.most_common()]
        order_index = {item: idx for idx, item in enumerate(sorted_items)}
        # Clear window and reinsert to maintain order
        self._window.clear()
        for txn in transactions:
            ordered_txn = sorted(txn, key=lambda x: order_index.get(x, len(order_index)))
            super().insert_transaction(ordered_txn)
