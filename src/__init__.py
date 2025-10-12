"""Top-level package for FP‑Tree intrusion detection research.

This package exposes the subpackages for preprocessing, algorithms, streaming and evaluation
to simplify imports.  For example::

    from src.preprocessing import DataLoader, FeatureEngineer
    from src.algorithms import FPTree

"""

from . import preprocessing  # noqa: F401
from . import algorithms     # noqa: F401
from . import streaming       # noqa: F401
from . import evaluation      # noqa: F401