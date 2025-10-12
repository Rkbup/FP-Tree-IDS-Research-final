"""
no_reorder.py
================

This module implements the **No‑Reorder (NR)** variant of the sliding‑window
FP‑tree.  NR is the simplest strategy: it inserts discretised transactions
into the FP‑tree in a fixed item order (typically by descending global
frequency) and removes expired transactions without reordering the tree.

The NR variant is deterministic and easy to implement, making it suitable
for environments where simplicity and throughput are more important than
absolute accuracy.  However, because item frequencies change over time in
streaming data, NR can become unbalanced and degrade in detection
performance【550642539765669†L846-L869】.  Other variants in this project (Partial
Rebuild, Two‑Tree, Decay‑Hybrid) address these limitations.

The `NoReorderFPTree` class is a thin wrapper around the base
``FPTree`` class; it exposes the same public API and adds a configuration
for the length of the tilted counter used in concept‑drift analysis.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from ..fp_tree import FPTree


@dataclass
class NoReorderConfig:
    """Configuration parameters for the No‑Reorder variant.

    Attributes
    ----------
    tilted_counter_length : int
        Length of the tilted counter (number of buckets) used to record
        historic support information for concept‑drift analysis.  A longer
        counter retains more history at the cost of additional memory.
    """
    tilted_counter_length: int = 10


class NoReorderFPTree(FPTree):
    """No‑Reorder FP‑tree variant.

    This subclass does not introduce any new behaviour on top of
    :class:`~FP-Tree-IDS-Research.src.algorithms.fp_tree.FPTree`.  It exists
    primarily to hold variant‑specific configuration and to provide a
    consistent API across variants.
    """

    def __init__(self, min_support: float = 0.01, window_size: int = 10_000,
                 tilted_counter_length: int = 10) -> None:
        super().__init__(min_support=min_support, window_size=window_size)
        self.config = NoReorderConfig(tilted_counter_length=tilted_counter_length)

    # No additional methods are needed; NR uses the base tree behaviour
