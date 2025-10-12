"""
test_preprocessing
==================

Unit tests for preprocessing utilities including feature selection and
discretisation.  These tests use synthetic data to validate that
quantile binning and feature selection behave as expected.
"""

import pandas as pd

from src.preprocessing.feature_engineering import FeatureEngineer


def test_feature_selection_returns_expected_columns() -> None:
    """Ensure that exactly 15 features plus the label are selected."""
    columns = [f"F{i}" for i in range(80)] + ['Label']
    data = pd.DataFrame([[i for i in range(81)]], columns=columns)
    fe = FeatureEngineer(n_bins=3)
    selected = fe.select_features(data)
    # Should select 15 columns plus Label
    assert len(selected.columns) == 16  # 15 features + Label
    assert 'Label' in selected.columns


def test_discretize_produces_bins() -> None:
    """Check that discretisation converts continuous features into categorical bins."""
    data = pd.DataFrame({
        'cont1': [1, 2, 3, 4, 5, 6],
        'Label': ['BENIGN'] * 6
    })
    fe = FeatureEngineer(n_bins=3)
    discretised = fe.discretize_continuous_features(data)
    # After discretisation a new column cont1_bin should exist
    assert any(col.startswith('cont1') and col.endswith('_bin') for col in discretised.columns)
    # The bin column values should be strings
    bin_col = [col for col in discretised.columns if col.endswith('_bin')][0]
    assert isinstance(discretised[bin_col].iloc[0], str)