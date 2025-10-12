# Troubleshooting Guide

This document summarises common issues you may encounter when using
the `FP‑Tree‑IDS‑Research` project and provides guidance to resolve
them.  If you experience an issue not listed here, please open an
issue on the project repository.

## Data Download Fails

**Problem:** Running `python data/download_dataset.py` yields an
error such as “Failed to download dataset” or “HTTP 403: Forbidden”.

**Cause:** The CIC‑IDS2017 dataset requires accepting a licence and
cannot always be fetched via unauthenticated HTTP requests.

**Solution:** Manually download the dataset from the official
[CIC website](https://www.unb.ca/cic/datasets/ids-2017.html).  After
extracting the tar archive, copy the CSV files into the `data/raw/`
directory and rerun your experiment scripts.

## Memory Exhaustion

**Problem:** Experiments crash with a `MemoryError` or the system
runs out of memory when using large window sizes or many bins.

**Cause:** FP‑tree structures can consume significant memory when
large windows or high cardinality discretisation are used.

**Solution:**

1. Decrease the `window_size` and/or the number of bins in the
   configuration (e.g. use 3 bins instead of 5).
2. Reduce the tilt counter length for the NR variant.
3. Use the DH variant with a lower decay factor to approximate a
   sliding window with smaller memory.
4. Ensure the system has sufficient RAM; 32 GB is recommended for
   full experiments.

## Long Runtime

**Problem:** The experiments take an excessively long time to run.

**Solution:**

* Run a subset of the data by specifying smaller `window_sizes` in
  `experiment_params.yaml` or by using the scripts on a limited
  number of flows.  The `smoke_test.py` script processes only a small
  portion of the dataset to verify functionality.
* Adjust the `batch_size` parameter to process more transactions per
  update; this can reduce overhead at the expense of latency.

## No Output Generated

**Problem:** After running an experiment script, no files appear in
`results/`.

**Cause:** The results directories may not exist, or the script may
have failed silently.

**Solution:**

1. Ensure the `results/figures`, `results/tables` and
   `results/statistical_analysis` directories exist.  The scripts
   should create them automatically, but in some cases you may need
   to create them manually.
2. Check the console output for error messages.
3. Verify that you have write permissions in the repository
   directory.

## Mismatched Results

**Problem:** Your reproduced results differ significantly from those
reported in the paper.

**Possible causes and solutions:**

* **Dataset differences:** Ensure you are using the same CIC‑IDS2017
  version (5 days, labelled).  Some distributions exclude certain
  days or features.
* **Parameter mismatch:** Verify that your configuration matches
  those reported in the paper.  Check `default.yaml` and
  `experiment_params.yaml`.
* **Randomness:** Some algorithms (e.g. IsolationForest,
  Autoencoder) involve randomness.  Set a seed via environment
  variables or algorithm constructors (`random_state` parameters) to
  obtain deterministic results.

## Contact

If you need further assistance, please open an issue on GitHub with a
description of your problem, the steps you have taken and any error
messages.  We will do our best to help.