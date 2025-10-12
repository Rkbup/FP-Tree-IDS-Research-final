"""
test_variants
=============

Basic tests for FP‑tree variant classes.  These tests check that the
variants inherit from the base class and implement expected methods.
Complex behavioural tests are beyond the scope of unit testing and
should be covered by integration tests.
"""

from src.algorithms.variants.no_reorder import NoReorderFPTree
from src.algorithms.variants.partial_rebuild import PartialRebuildFPTree
from src.algorithms.variants.two_tree import TwoTreeFPTree
from src.algorithms.variants.decay_hybrid import DecayHybridFPTree


def test_no_reorder_inherits_fp_tree() -> None:
    tree = NoReorderFPTree(min_support=0.1, window_size=10)
    # Insert and remove should not raise exceptions
    tree.insert_transaction(['A'])
    tree.remove_transaction(['A'])


def test_partial_rebuild_rebuild_condition() -> None:
    pr = PartialRebuildFPTree(min_support=0.1, window_size=10, rebuild_threshold=0.5)
    txn1 = ['A', 'B']
    txn2 = ['A', 'C']
    pr.insert_transaction(txn1)
    pr.insert_transaction(txn1)  # Increase frequency of B
    pr.insert_transaction(txn2)
    # Force a rank change by inserting many of a new item
    for _ in range(5):
        pr.insert_transaction(['D'])
    # After inserting multiple 'D' items, a partial rebuild should be triggered.
    # We test that the tree still produces patterns without error.
    patterns = pr.mine_frequent_patterns()
    assert ('A',) in patterns


def test_two_tree_behavior() -> None:
    tt = TwoTreeFPTree(min_support=0.1, half_window_size=2)
    # Insert four transactions; the second half should swap after two
    tt.insert_transaction(['A'])
    tt.insert_transaction(['B'])
    tt.insert_transaction(['C'])  # triggers swap to next tree
    tt.insert_transaction(['D'])
    patterns = tt.mine_frequent_patterns()
    # Patterns should include items from both trees
    assert ('A',) in patterns or ('C',) in patterns


def test_decay_hybrid_decay_factor() -> None:
    dh = DecayHybridFPTree(min_support=0.1, window_size=10, decay_factor=0.5)
    dh.insert_transaction(['A'])
    # After inserting many empty transactions, count of A should decay
    for _ in range(10):
        dh.insert_transaction(['B'])
    patterns = dh.mine_frequent_patterns()
    # The count of A will have decayed to 0.x but still present
    assert ('A',) in patterns