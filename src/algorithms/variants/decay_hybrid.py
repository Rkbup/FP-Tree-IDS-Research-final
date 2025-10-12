"""
decay_hybrid.py
===============

This module implements the **Decay Hybrid (DH)** variant of the sliding
window FP‑tree.  DH applies an exponential decay to transaction counts
within the FP‑tree so that older transactions gradually lose influence
without being explicitly deleted.  The decay factor λ ∈ (0, 1) determines
the rate at which counts decrease: after each insert, all counts are
multiplied by λ before the new transaction is added.  This yields a
memory‑efficient approximation of a sliding window but can blur the
boundary between recent and outdated transactions【550642539765669†L846-L869】.

Attributes
----------
decay_factor : float
    Multiplicative decay applied to all node counts after each insertion.

Note
----
For ease of implementation counts are stored as floating‑point values.
Threshold comparisons in pattern mining should take this into account by
using a fractional support threshold rather than absolute counts.
"""

from __future__ import annotations

from typing import List

from ..fp_tree import FPTree, FPNode


class DecayHybridFPTree(FPTree):
    """Decay‑Hybrid FP‑tree variant with exponential decay.

    Parameters
    ----------
    decay_factor : float
        Exponential decay applied after each insertion (0 < λ ≤ 1).  A
        decay factor close to 1.0 retains long memory; smaller values
        emphasise recent transactions.  The default of 0.995 was shown to
        offer a good trade‑off between accuracy and memory usage in the
        accompanying paper【550642539765669†L846-L869】.
    kwargs : dict
        Additional keyword arguments forwarded to :class:`~FPTree`.
    """

    def __init__(self, decay_factor: float = 0.995, **kwargs) -> None:
        super().__init__(**kwargs)
        if not (0 < decay_factor <= 1.0):
            raise ValueError("decay_factor must be in (0, 1]")
        self.decay_factor = decay_factor

    def insert_transaction(self, transaction: List[str]) -> None:
        """Insert a transaction with exponential decay of existing counts.

        This overrides the base insertion method to apply decay to all
        node counts in the tree before inserting the new transaction.  The
        decay gradually diminishes the influence of older transactions,
        approximating a sliding window without explicit deletions.
        """
        # Apply decay to all node counts
        self._apply_decay(self.root)
        # Insert without touching the base class window queue to avoid
        # evicting old transactions; DH approximates the window via decay.
        current_node = self.root
        current_node.count += 1
        for item in transaction:
            child = current_node.add_child(item)
            child.count += 1
            if child.count == 1:
                # First occurrence; maintain header table links
                if item not in self.header_table:
                    self.header_table[item] = child
                else:
                    node = self.header_table[item]
                    while node.link is not None:
                        node = node.link
                    node.link = child
            current_node = child

    def _apply_decay(self, node: FPNode) -> None:
        """Recursively multiply counts by the decay factor.

        Parameters
        ----------
        node : FPNode
            The node whose count and children are to be decayed.
        """
        node.count *= self.decay_factor
        for child in node.children.values():
            self._apply_decay(child)
