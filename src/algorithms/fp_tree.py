"""
fp_tree.py
==============

This module defines the core data structures for frequent‑pattern (FP) tree
construction and mining as used in the sliding‑window FP‑tree based network
intrusion detection system.  The FP‑tree stores a collection of variable‑length
transactions in a compressed prefix tree with a header table linking
identical items.  A sliding window over the incoming stream is maintained by
inserting new transactions and removing expired ones.

The API exposed here is intentionally minimal: the tree supports incremental
insertion and removal of discretised transactions, and mining of frequent
patterns above a given support threshold.  Streaming variants such as
No‑Reorder (NR), Partial Rebuild (PR), Two‑Tree (TT) and Decay‑Hybrid (DH)
extend this base class to implement window maintenance policies and
approximation strategies.

For clarity and reproducibility the implementation uses only the Python
standard library and NumPy.  This code is not tuned for absolute
performance but is sufficient to reproduce the experiments reported in the
accompanying paper.

References
----------
* Han, Pei, and Yin.  "Mining frequent patterns without candidate
  generation."  *SIGMOD* (2000)【550642539765669†L846-L869】.
* Tanbeer et al.  "Sliding window based frequent pattern mining over data
  streams."  *Information Sciences* (2009)【550642539765669†L846-L869】.
* Chi et al.  "Moment: Maintaining closed frequent itemsets over a stream
  sliding window."  *ICDM* (2004)【550642539765669†L846-L869】.
"""

from __future__ import annotations

from collections import defaultdict, deque
import math
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple


@dataclass
class FPNode:
    """A node in an FP‑tree.

    Attributes
    ----------
    item : Optional[str]
        The item identifier stored in this node.  The root node has
        ``item`` set to ``None``.
    count : int
        The number of transactions represented by the path that ends at
        this node.
    parent : Optional[FPNode]
        A reference to the parent node; ``None`` for the root.
    children : Dict[str, FPNode]
        A mapping from item identifiers to child nodes.
    link : Optional[FPNode]
        A link to the next node in the FP‑tree header table for this item.
    """
    item: Optional[str]
    count: float
    parent: Optional['FPNode'] = field(default=None, repr=False)
    children: Dict[str, 'FPNode'] = field(default_factory=dict, repr=False)
    link: Optional['FPNode'] = field(default=None, repr=False)

    def add_child(self, item: str) -> 'FPNode':
        """Return the existing child for `item` or create a new one.

        Parameters
        ----------
        item : str
            The item identifier for the child node.

        Returns
        -------
        FPNode
            The child node corresponding to `item`.
        """
        if item in self.children:
            return self.children[item]
        child = FPNode(item=item, count=0, parent=self)
        self.children[item] = child
        return child


class FPTree:
    """A frequent‑pattern (FP) tree for streaming transaction data.

    The tree maintains a compact representation of the multiset of
    transactions currently inside the sliding window.  Each path from
    the root to a leaf encodes a sequence of items appearing together
    in some transactions.  A header table is used to maintain a
    linked list of all nodes containing the same item, which facilitates
    pattern mining.  This base class does not enforce any particular
    ordering on the items; ordering is decided by the caller.

    Parameters
    ----------
    min_support : float, optional
        Minimum support threshold (as a fraction of the window size) used
        during pattern mining.  Transactions below this threshold are
        ignored in the mining phase.  Default is 0.01.
    window_size : int, optional
        The maximum number of transactions to retain in the sliding
        window.  When the window is full, expired transactions must be
        removed before inserting new ones.  Default is 10_000.
    """

    def __init__(self, min_support: float = 0.01, window_size: int = 10_000) -> None:
        self.min_support = min_support
        self.window_size = window_size
        self.header_table: Dict[str, FPNode] = {}  # maps item to first node
        self.root = FPNode(item=None, count=0)
        # Keep a history of transactions for efficient deletion
        self._window: deque[List[str]] = deque()

    # ------------------------------------------------------------------
    # Sliding window maintenance
    # ------------------------------------------------------------------

    def insert_transaction(self, transaction: List[str]) -> None:
        """Insert a discretised transaction into the FP‑tree.

        Transactions should be ordered (e.g. by decreasing frequency) before
        insertion.  The method updates the counts along the path
        corresponding to the transaction and updates the header table.

        Parameters
        ----------
        transaction : List[str]
            A list of item identifiers representing the transaction.
        """
        # Append transaction to window history
        self._window.append(transaction)
        # Build or extend the path for this transaction
        current_node = self.root
        current_node.count += 1
        for item in transaction:
            child = current_node.add_child(item)
            child.count += 1
            # Update header table: link new node
            if child.count == 1:
                # First occurrence of this node; add to header
                if item not in self.header_table:
                    self.header_table[item] = child
                else:
                    # Follow existing links to append this node at end
                    node = self.header_table[item]
                    while node.link is not None:
                        node = node.link
                    node.link = child
            current_node = child
        # Maintain window size
        if len(self._window) > self.window_size:
            expired = self._window.popleft()
            self.remove_transaction(expired)

    def remove_transaction(self, transaction: List[str]) -> None:
        """Remove a previously inserted transaction from the FP‑tree.

        Parameters
        ----------
        transaction : List[str]
            A transaction list exactly as inserted previously.  The method
            walks down the tree, decrementing counts and removing nodes
            whose counts drop to zero.  The header table is updated
            accordingly.
        """
        # Walk down the path defined by the transaction
        current_node = self.root
        current_node.count -= 1
        # Maintain a stack for backtracking to remove zero‑count nodes
        path_nodes: List[FPNode] = []
        for item in transaction:
            child = current_node.children.get(item)
            if child is None:
                # Should never happen if the transaction existed
                return
            path_nodes.append(child)
            child.count -= 1
            current_node = child
        # Remove nodes with zero count and update header links
        for node in reversed(path_nodes):
            if node.count <= 0:
                # Remove from parent's children
                parent = node.parent
                if parent is not None and node.item in parent.children:
                    del parent.children[node.item]
                # Remove from header table list
                prev_node: Optional[FPNode] = None
                if node.item is not None:
                    cur = self.header_table.get(node.item)
                    while cur is not None and cur is not node:
                        prev_node = cur
                        cur = cur.link
                    if cur is node:
                        item_key = node.item
                        if prev_node is None:
                            # Node is first in header list
                            if node.link is None:
                                self.header_table.pop(item_key, None)
                            else:
                                self.header_table[item_key] = node.link
                        else:
                            prev_node.link = node.link

    # ------------------------------------------------------------------
    # Pattern mining
    # ------------------------------------------------------------------

    def mine_frequent_patterns(self) -> Dict[Tuple[str, ...], int]:
        """Mine all frequent itemsets in the current FP‑tree.

        This is a simplified FP‑growth implementation that traverses the
        header table to build conditional FP‑trees recursively.  It returns
        frequent itemsets with absolute support counts.  Only itemsets with
        support >= ``min_support * window_size`` are returned.

        Returns
        -------
        Dict[Tuple[str, ...], int]
            A dictionary mapping itemset tuples to support counts.
        """
        patterns: Dict[Tuple[str, ...], int] = {}
        # Use a floor of 1 for minimum count to avoid eliminating items with fractional
        # counts due to decay in DH variant.
        min_count = max(1, int(self.min_support * max(1, len(self._window))))
        # Sort items by support ascending for mining
        items = [(item, self._item_support(item)) for item in self.header_table]
        items = [item for item, cnt in items if cnt >= min_count]
        for item in sorted(items, key=lambda x: self._item_support(x)):
            suffix = (item,)
            support = self._item_support(item)
            if support >= min_count:
                patterns[suffix] = support
            # Build conditional pattern base
            conditional_base = []
            node = self.header_table[item]
            while node is not None:
                path: List[str] = []
                parent = node.parent
                while parent is not None and parent.item is not None:
                    path.append(parent.item)
                    parent = parent.parent
                if path:
                    conditional_base.append((path[::-1], node.count))
                node = node.link
            # Build conditional FP‑tree
            cond_tree = FPTree(min_support=self.min_support, window_size=len(conditional_base) or 1)
            for path, count in conditional_base:
                # Insert path `count` times
                for _ in range(int(count)):
                    cond_tree.insert_transaction(path)
            # Recurse
            for pattern, cnt in cond_tree.mine_frequent_patterns().items():
                patterns[tuple(sorted(pattern + suffix))] = cnt
        return patterns

    def _item_support(self, item: str) -> int:
        """Return the absolute support count of an item in the FP‑tree.

        Parameters
        ----------
        item : str
            The item identifier.

        Returns
        -------
        int
            The total count of transactions containing `item` in the current
            window.
        """
        count: float = 0.0
        node = self.header_table.get(item)
        while node is not None:
            count += node.count
            node = node.link
        # Ceil to avoid losing decayed but present items (DH variant)
        return int(math.ceil(count))
