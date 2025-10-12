"""Preprocessing subpackage.

This subpackage contains modules for loading raw CIC‑IDS2017 flows, performing
feature engineering (feature selection and discretisation) and converting flows
into transactions suitable for FP‑tree algorithms.
"""

from .data_loader import DataLoader  # noqa: F401
from .feature_engineering import FeatureEngineer  # noqa: F401
from .transaction_builder import TransactionBuilder  # noqa: F401