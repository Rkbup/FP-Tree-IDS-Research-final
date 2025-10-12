# API Reference

This document summarises the most important classes and functions in
the `FP‑Tree‑IDS‑Research` codebase.  Detailed docstrings are
provided in the source files; this reference serves as a quick
overview of the available functionality.

## Preprocessing (`src/preprocessing`)

### `load_cic_ids2017()`
Loads the raw CIC‑IDS2017 dataset into a pandas `DataFrame`, handling
missing values and duplicate removal.  By default it reads the CSV
files found in `data/raw/`, but you can pass a custom path if you
downloaded the dataset elsewhere.

### `FeatureEngineer`
Performs feature selection and discretisation.  The class offers the
following methods:

* `select_features(data: pd.DataFrame) -> pd.DataFrame`: Returns a
  subset of the 15 most discriminative features used in the
  experiments.
* `discretize_continuous_features(data: pd.DataFrame) -> pd.DataFrame`:
  Applies quantile‑based binning to continuous features.  The number
  of bins can be specified via the constructor.
* `save_bin_edges(filepath: str) -> None`: Stores the bin boundaries in
  JSON format for reproducibility.

### `TransactionBuilder`
Converts a discretised `DataFrame` into a list of transactions.  Each
transaction is a list of `str` items of the form
`feature_name=value`.  Use the `build_transactions(data: pd.DataFrame)`
method to perform this conversion.

## Algorithms (`src/algorithms`)

### `FPTree`
Base class implementing a sliding‑window Frequent Pattern tree.  Key
methods include:

* `insert_transaction(transaction: List[str]) -> None`: Insert a
  single transaction into the FP‑tree, updating counts and header
  table.
* `remove_transaction(transaction: List[str]) -> None`: Remove a
  transaction when it exits the sliding window.
* `mine_frequent_patterns() -> Dict[Tuple[str, ...], int]`: Perform
  pattern mining using the FP‑Growth algorithm.  Returns a dictionary
  mapping itemsets to their support counts.

### Variants (in `src/algorithms/variants`)

* `NoReorderFPTree`: Simple sliding‑window FP‑tree that does not
  reorder items on insert or delete.  Configurable tilted counter
  length to summarise historic support.
* `PartialRebuildFPTree`: Monitors changes in item support rank and
  triggers a local rebuild of affected subtrees when the change
  exceeds a threshold.  Provides a better trade‑off between runtime
  and tree balance.
* `TwoTreeFPTree`: Maintains two half‑window trees and periodically
  swaps them.  Maximises throughput but uses more memory and can
  suffer precision loss due to stale patterns in the old tree.
* `DecayHybridFPTree`: Applies exponential decay to counts, providing
  an approximation of sliding‑window behaviour with reduced memory.

### Baselines (in `src/algorithms/baselines`)

* `HalfSpaceTrees`: Implements the Half‑Space Trees streaming anomaly
  detector using the Isolation Forest algorithm as a proxy.
* `RandomCutForest`: Implements Random Cut Forest using scikit‑learn’s
  `IsolationForest` as a surrogate for the Amazon RCF algorithm.
* `OnlineAutoencoder`: Implements a simple incremental autoencoder
  using `MLPRegressor` from scikit‑learn; reconstructs inputs and
  computes reconstruction error as an anomaly score.

## Streaming (`src/streaming`)

### `SlidingWindowManager`
Manages a sliding window of a fixed size for FP‑tree variants.  It
handles the insertion of new transactions, removal of old ones, and
provides access to the current window for pattern mining.

### `flink_connector.py`
Contains placeholder functions to integrate with Apache Flink for
distributed streaming.  Actual Flink usage is optional; the provided
experiments implement streaming in pure Python for reproducibility.

## Evaluation (`src/evaluation`)

### `classification_metrics(labels, predictions)`
Returns a dictionary of standard binary classification metrics (F1,
precision, recall) given arrays of true labels and predicted labels.

### `pr_auc(labels, scores)`
Computes the area under the precision–recall curve for anomaly scores.

### `throughput(n_events, elapsed_seconds)`
Returns the number of events per second given a count and elapsed time.

### `memory_usage_mb()`
Measures current process memory usage in megabytes using `psutil`.

### `bootstrap_confidence_interval(data, confidence_level)`
Computes a bootstrap confidence interval around the mean of the data.

### `cochrans_q_test(data)`
Performs Cochran’s Q test to detect differences in performance across
multiple algorithms.

### `mcnemar_test(y_true, y_pred1, y_pred2)`
Performs McNemar’s test to compare two classifiers on paired binary
outcomes; returns the test statistic and p‑value.

### `holm_correction(p_values)`
Applies the Holm–Bonferroni method to control the familywise error
rate when multiple hypotheses are tested.

### `plot_throughput_latency(results, filepath)`
Generates a scatter plot of throughput versus latency for a set of
algorithms and saves it to the specified path.

### `plot_sensitivity_curves(sensitivity_data, filepath)`
Creates a 2×2 panel figure showing the sensitivity of the FP‑tree
variants to anomaly threshold τ, window size N, support threshold σ,
and memory usage.  Requires a dictionary of results produced by the
`sensitivity_analysis.py` script.

### `plot_drift_f1_over_time(drift_data, filepath)`
Plots the window‑level F1 scores across different days to illustrate
concept drift adaptation.  Dashed vertical lines denote day boundaries.

## Experiments (`experiments/`)

The scripts in the `experiments` directory orchestrate the end‑to‑end
evaluation pipelines.  Each script can be executed directly from the
repository root.  They load configuration parameters from
``config/`` and save results to ``results/``.

* `main_experiment.py`: Runs the main performance evaluation across
  FP‑tree variants and baseline methods.
* `concept_drift_analysis.py`: Measures recovery time and stability
  under natural concept drift between different days in CIC‑IDS2017.
* `baseline_comparison.py`: Compares FP‑tree variants with HS‑Trees,
  RCF and the autoencoder baseline, including statistical tests.
* `sensitivity_analysis.py`: Explores the effect of varying
  thresholds, window sizes and support thresholds on detection and
  system performance.
* `interpretability_demo.py`: Demonstrates the interpretability case
  study by flagging a rare PortScan transaction and analysing the
  underlying itemset.
* `smoke_test.py`: Runs a minimal subset of the data through the
  pipeline to ensure all components integrate correctly (used in
  CI).