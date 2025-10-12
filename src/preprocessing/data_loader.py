"""
data_loader.py
==============

This module contains routines for loading the CIC‑IDS2017 dataset and
preparing it for further processing.  The CIC‑IDS2017 dataset consists
of network flow CSV files recorded over five days (Monday through Friday)
containing a variety of attack types and benign traffic.  Each file
contains approximately eighty features per flow in addition to a label.

The loader functions defined here abstract away the details of reading
multiple CSV files from disk and concatenating them into a single
`pandas.DataFrame` for further preprocessing.  If the raw dataset is
split across multiple directories, pass the directory containing all
CSV files and optionally filter by day.

Notes
-----
The CIC‑IDS2017 dataset is large (>20 GB) and may not be present in
distributed environments.  The function `download_cic_ids2017` in
``data/download_dataset.py`` can be used to fetch the dataset
automatically if network access is available.  Otherwise, please copy
the raw CSV files into the `data/raw/` directory before running
experiments.
"""

from __future__ import annotations

import glob
import os
import zipfile
from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path

import numpy as np

import pandas as pd


def load_cic_ids2017(raw_dir: str = "data/raw", days: Optional[List[str]] = None,
                     verbose: bool = True) -> pd.DataFrame:
    """Load the CIC‑IDS2017 dataset from CSV files.

    Parameters
    ----------
    raw_dir : str, optional
        Path to the directory containing the raw CSV files.  Defaults to
        ``data/raw``.
    days : list of str, optional
        List of days to load (e.g. ["Monday", "Tuesday"]).  If ``None``
        all available files are loaded.  The function performs a
        case‑insensitive match on the file names.
    verbose : bool, optional
        If ``True``, progress information is printed during loading.

    Returns
    -------
    pd.DataFrame
        Concatenated data containing all selected days.  Index is reset.
    """
    # Resolve file pattern. If a relative path is provided, interpret it relative to the
    # project root (parent of the "src" directory) so scripts can be run from subfolders.
    if not os.path.isabs(raw_dir):
        project_root = Path(__file__).resolve().parents[2]  # repo root
        raw_dir = str((project_root / raw_dir).resolve())
    raw_path = Path(raw_dir)
    zip_path = raw_path / "MachineLearningCSV.zip"
    # Automatically extract the official MachineLearningCSV archive if present.
    extract_target = raw_path / "MachineLearningCSV"
    if zip_path.exists() and not extract_target.exists():
        if verbose:
            print(f"Extracting {zip_path} ...")
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(raw_path)
    pattern = os.path.join(raw_dir, "**", "*.csv")
    files = sorted(glob.glob(pattern, recursive=True))
    files = [f for f in files if "__MACOSX" not in f]
    # Prefer official MachineLearningCSV files over derived CVE subsets if available.
    csv_priority = [f for f in files if "MachineLearningCSV" in Path(f).parts]
    if csv_priority:
        files = csv_priority
    # Prefer the full CIC-IDS2017 dump when both real and synthetic datasets are present.
    if len(files) > 1:
        non_synthetic = [f for f in files if "synthetic_cic_ids2017" not in Path(f).name.lower()]
        if non_synthetic:
            files = non_synthetic
    if not files:
        raise FileNotFoundError(
            f"No CSV files found in {raw_dir}. Please ensure the CIC-IDS2017 files are copied there."
        )
    frames = []
    for fpath in files:
        fname = os.path.basename(fpath).lower()
        if days:
            if not any(day.lower() in fname for day in days):
                continue
        if verbose:
            print(f"Loading {fpath} ...")
        df = pd.read_csv(fpath, low_memory=False)
        frames.append(df)
    if not frames:
        raise ValueError(
            "No matching files loaded; please check the day filter or file names."
        )
    data = pd.concat(frames, ignore_index=True)
    data.columns = [col.strip() for col in data.columns]
    if verbose:
        print(f"Loaded {len(data):,} rows from {len(frames)} file(s).")
    # Remove duplicate flows if any
    data = data.drop_duplicates()
    # Handle missing values: for numeric features fill with median; for
    # categorical features fill with mode
    for col in data.columns:
        if data[col].dtype.kind in {'i', 'u', 'f'}:
            series = data[col].replace([np.inf, -np.inf], np.nan)
            med = series.median()
            data[col] = series.fillna(med)
        else:
            mode = data[col].mode()
            if not mode.empty:
                data[col] = data[col].fillna(mode.iloc[0])
            else:
                data[col] = data[col].fillna("UNKNOWN")
    return data.reset_index(drop=True)


@dataclass
class DataLoader:
    """Thin wrapper that mirrors the historical API used by older notebooks.

    Attributes
    ----------
    raw_dir : str
        Directory containing raw CIC‑IDS2017 CSV files.
    days : Optional[List[str]]
        Optional day filters passed to :func:`load_cic_ids2017`.
    verbose : bool
        Whether to print progress information during loading.
    """

    raw_dir: str = "data/raw"
    days: Optional[List[str]] = None
    verbose: bool = True

    def load(self) -> pd.DataFrame:
        """Load the CIC‑IDS2017 dataset using the stored configuration."""

        return load_cic_ids2017(raw_dir=self.raw_dir, days=self.days, verbose=self.verbose)
