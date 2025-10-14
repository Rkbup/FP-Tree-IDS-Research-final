"""
parameter_tuning.py
===================

This script performs dynamic parameter tuning for the FP-Tree variants
to find an optimal `min_support` value. It runs each variant on a
sample of the dataset with different `min_support` thresholds and
logs the execution time and the number of frequent patterns generated.

This helps in finding a "sweet spot" that balances computational load
and the richness of the generated patterns, addressing the scalability
issues encountered with the full dataset.

Usage
-----
Run this script from the project root:

```bash
python experiments/parameter_tuning.py
```
"""

import time
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
import matplotlib.pyplot as plt
from pathlib import Path

from src.preprocessing.data_loader import load_cic_ids2017
from src.preprocessing.feature_engineering import FeatureEngineer
# ... existing code ...
from src.algorithms.variants.two_tree import TwoTreeFPTree
from src.algorithms.variants.decay_hybrid import DecayHybridFPTree
from src.evaluation.metrics import classification_metrics

# --- Configuration ---
SYNTHETIC_DATA_PATH = "data/raw/synthetic_cic_ids2017.csv"
MIN_SUPPORT_THRESHOLDS = np.linspace(0.001, 0.1, 20).tolist() # Test a wider range of values
WINDOW_SIZE = 5000  # Smaller window for faster tuning on synthetic data
N_JOBS = -1  # Use all available CPU cores

def run_single_experiment(AlgoClass, name, min_support, transactions, labels):
    """Runs a single experiment for a given algorithm and min_support."""
    try:
        if name == "TT":
            algorithm = AlgoClass(min_support=min_support, half_window_size=WINDOW_SIZE // 2)
        else:
            algorithm = AlgoClass(min_support=min_support, window_size=WINDOW_SIZE)

        y_pred = np.zeros(len(transactions))
        scores = np.zeros(len(transactions))

        for i, transaction in enumerate(transactions):
            algorithm.insert_transaction(transaction)
            patterns = algorithm.mine_frequent_patterns()
            
            score = 1.0
            if patterns:
                max_support = max(patterns.values(), default=0)
                score = 1.0 - (max_support / max(1, i + 1))
            
            scores[i] = score
            y_pred[i] = 1 if score >= 0.5 else 0

        metrics = classification_metrics(labels, y_pred)
        f1 = metrics.get('f1', 0)
        
        print(f"  {name} @ {min_support:.4f} -> F1-Score: {f1:.4f}")
        
        return {
            "algorithm": name,
            "min_support": min_support,
            "f1_score": f1,
        }
    except Exception as e:
        print(f"  {name} @ {min_support:.4f} -> FAILED with error: {e}")
        return {
            "algorithm": name,
            "min_support": min_support,
            "f1_score": -1,
        }

def tune_parameters():
    """
    Runs the parameter tuning experiment in parallel.
    """
    print("--- Efficient Parameter Tuning on Synthetic Data ---")
    print(f"Testing {len(MIN_SUPPORT_THRESHOLDS)} min_support values from {MIN_SUPPORT_THRESHOLDS[0]:.4f} to {MIN_SUPPORT_THRESHOLDS[-1]:.4f}")
    print(f"Using {N_JOBS if N_JOBS != -1 else 'all'} CPU cores.")
    print("-" * 40)

    # 1. Load and preprocess the synthetic data
    print("Loading and preprocessing synthetic data...")
    try:
        df = pd.read_csv(SYNTHETIC_DATA_PATH)
        
        feature_engineer = FeatureEngineer()
        df_selected = feature_engineer.select_features(df)
        df_featured = feature_engineer.discretize_continuous_features(df_selected)

        if 'Label' in df_featured.columns:
            df_featured['Label'] = (df_featured['Label'].str.upper() != 'BENIGN').astype(int)

        builder = TransactionBuilder()
        transactions = builder.build_transactions(df_featured.drop(columns=['Label'], errors='ignore'))
        labels = df_featured['Label'].values if 'Label' in df_featured else np.zeros(len(df_featured))
        print(f"Synthetic data loaded and processed into {len(transactions)} transactions.")
    except Exception as e:
        print(f"Error loading or preprocessing data: {e}")
        return

    # 2. Define algorithms to tune
    algorithm_classes = {
        "NR": NoReorderFPTree,
        "PR": PartialRebuildFPTree,
        "TT": TwoTreeFPTree,
        "DH": DecayHybridFPTree,
    }

    all_results = []

    # 3. Run experiments in parallel for each algorithm
    for name, AlgoClass in algorithm_classes.items():
        print(f"\n--- Tuning Algorithm: {name} ---")
        
        results = Parallel(n_jobs=N_JOBS)(
            delayed(run_single_experiment)(AlgoClass, name, ms, transactions, labels)
            for ms in MIN_SUPPORT_THRESHOLDS
        )
        all_results.extend(results)

    # 4. Analyze, plot, and print summary
    print("\n--- Tuning Summary ---")
    results_df = pd.DataFrame([r for r in all_results if r is not None])
    
    # Create figure directory if it doesn't exist
    fig_dir = Path("results/figures")
    fig_dir.mkdir(parents=True, exist_ok=True)
    
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(12, 7))

    print("\n--- Recommendations ---")
    for name in algorithm_classes.keys():
        algo_results = results_df[results_df['algorithm'] == name]
        valid_results = algo_results[algo_results['f1_score'] > 0]
        
        if not valid_results.empty:
            best_choice = valid_results.loc[valid_results['f1_score'].idxmax()]
            print(f"For {name}: Recommended min_support = {best_choice['min_support']:.4f} (F1-Score: {best_choice['f1_score']:.4f})")
            
            # Plotting
            ax.plot(algo_results['min_support'], algo_results['f1_score'], marker='o', linestyle='-', label=name)
        else:
            print(f"For {name}: No successful runs with F1 > 0. Manual inspection needed.")

    ax.set_title('Parameter Tuning: F1-Score vs. Min Support on Synthetic Data')
    ax.set_xlabel('Minimum Support Threshold')
    ax.set_ylabel('F1-Score')
    ax.legend()
    ax.set_ylim(0, 1)
    ax.grid(True)
    
    plot_path = fig_dir / "parameter_tuning_f1_vs_support.png"
    plt.savefig(plot_path)
    print(f"\nPlot saved to: {plot_path}")

if __name__ == "__main__":
    tune_parameters()
