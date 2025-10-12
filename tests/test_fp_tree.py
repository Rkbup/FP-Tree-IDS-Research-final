"""
test_fp_tree
============

Unit tests for the core FP‑Tree implementation.  These tests focus
on verifying insertion, removal and mining of patterns.  They do not
exhaustively cover the sliding window logic but provide basic
assurance that the FP‑tree maintains counts correctly.
"""

from src.algorithms.fp_tree import FPTree


def test_insert_and_mine_simple_pattern() -> None:
    """Insert transactions into the FP‑tree and verify mined patterns.

    After inserting two identical transactions and one distinct
    transaction, the single‑item support counts should match the
    number of occurrences of each item.  After removing a
    transaction, the counts should decrease accordingly.
    """
    tree = FPTree(min_support=0.5, window_size=10)
    txn1 = ['A', 'B', 'C']
    txn2 = ['A', 'B', 'C']
    txn3 = ['A', 'D']
    tree.insert_transaction(txn1)
    tree.insert_transaction(txn2)
    tree.insert_transaction(txn3)
    patterns = tree.mine_frequent_patterns()
    assert patterns[('A',)] == 3
    assert patterns[('B',)] == 2
    assert patterns[('C',)] == 2
    # Remove a transaction and recompute
    tree.remove_transaction(txn1)
    patterns = tree.mine_frequent_patterns()
    assert patterns[('A',)] == 2
    assert patterns[('B',)] == 1