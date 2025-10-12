"""
transaction_builder.py
======================

This module converts discretised flow records into FP‑tree transactions.
Each row in the input DataFrame is mapped to a list of "item"
strings of the form ``<feature>=<value>``.  These transactions are
consumed by the FP‑tree algorithms, which operate on sets of discrete
items rather than continuous numerical values.

Example
-------
Given a discretised flow with columns ``Protocol = 'TCP'``,
``Dst Port = '4444'``, ``Flow Duration = '2'``, the resulting
transaction would include items ``protocol=TCP``, ``dst_port=4444`` and
``flow_duration_bin_2``.
"""

from __future__ import annotations

from typing import List

import pandas as pd


class TransactionBuilder:
    """Convert discretised DataFrame rows into FP‑tree transactions."""

    def __init__(self) -> None:
        pass

    def build_transactions(self, data: pd.DataFrame) -> List[List[str]]:
        """Return a list of transactions from discretised data.

        Parameters
        ----------
        data : pd.DataFrame
            DataFrame with discretised feature values (strings).

        Returns
        -------
        List[List[str]]
            A list of transactions where each transaction is a list of
            strings ``<feature>=<value>``.  The order of items within a
            transaction is arbitrary; however, for FP‑tree efficiency it is
            common to sort items by global frequency before insertion.
        """
        transactions: List[List[str]] = []
        for _, row in data.iterrows():
            txn = []
            for col, val in row.items():
                # Normalise feature names: lowercase and replace spaces with underscores
                feature_name = col.lower().replace(' ', '_')
                item = f"{feature_name}={val}"
                txn.append(item)
            transactions.append(txn)
        return transactions
