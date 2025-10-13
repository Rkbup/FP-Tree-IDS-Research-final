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

from src.preprocessing.data_loader import load_cic_ids2017
from src.preprocessing.feature_engineering import FeatureEngineer
from src.preprocessing.transaction_builder import TransactionBuilder
from src.algorithms.variants.no_reorder import NoReorderFPTree
from src.algorithms.variants.partial_rebuild import PartialRebuildFPTree
from src.algorithms.variants.two_tree import TwoTreeFPTree
from src.algorithms.variants.decay_hybrid import DecayHybridFPTree

# --- Configuration ---
DATA_SAMPLE_SIZE = 100_000  # Number of records to use for tuning
MIN_SUPPORT_THRESHOLDS = [0.01, 0.02, 0.05, 0.1, 0.15, 0.2]
WINDOW_SIZE = 10_000 # A reasonable window size for the sample

def tune_parameters():
    """
    Runs the parameter tuning experiment.
    """
    print("--- Phase 2: Dynamic Parameter Tuning ---")
    print(f"Using a sample of {DATA_SAMPLE_SIZE} records.")
    print(f"Testing min_support values: {MIN_SUPPORT_THRESHOLDS}")
    print("-" * 40)

    # 1. Load and preprocess a sample of the data
    print("Loading and preprocessing data sample...")
    try:
        df = load_cic_ids2017(raw_dir="data/raw", days=["Monday"], verbose=False)
        df_sample = df.head(DATA_SAMPLE_SIZE)
        
        feature_engineer = FeatureEngineer()
        df_selected = feature_engineer.select_features(df_sample)
        df_featured = feature_engineer.discretize_continuous_features(df_selected)

        # Convert string labels to binary (0/1)
        if 'Label' in df_featured.columns:
            df_featured['Label'] = (df_featured['Label'].str.upper() != 'BENIGN').astype(int)

        # Correctly build transactions
        builder = TransactionBuilder()
        transactions = builder.build_transactions(df_featured.drop(columns=['Label'], errors='ignore'))
        labels = df_featured['Label'].values if 'Label' in df_featured else np.zeros(len(df_featured))
        print(f"Data sample loaded and processed into {len(transactions)} transactions.")
    except Exception as e:
        print(f"Error loading or preprocessing data: {e}")
        return

    # 2. Define algorithms to tune
    # We instantiate them inside the loop to reset their state
    algorithm_classes = {
        "NR": NoReorderFPTree,
        "PR": PartialRebuildFPTree,
        "TT": TwoTreeFPTree,
        "DH": DecayHybridFPTree,
    }

    results = []

    # 3. Iterate over algorithms and min_support values
    for name, AlgoClass in algorithm_classes.items():
        print(f"\n--- Tuning Algorithm: {name} ---")
        for min_support in MIN_SUPPORT_THRESHOLDS:
            try:
                # Instantiate algorithm with the current min_support
                if name == "TT":
                     # TwoTree uses half_window_size
                    algorithm = AlgoClass(min_support=min_support, half_window_size=WINDOW_SIZE // 2)
                else:
                    algorithm = AlgoClass(min_support=min_support, window_size=WINDOW_SIZE)

                start_time = time.time()
                
                # Process transactions
                for i, transaction in enumerate(transactions):
                    algorithm.insert_transaction(transaction)
                    # Mine patterns periodically to simulate real-world usage
                    if (i + 1) % 1000 == 0:
                        patterns = algorithm.mine_frequent_patterns()

                # Final mining at the end
                patterns = algorithm.mine_frequent_patterns()
                num_patterns = len(patterns)
                
                end_time = time.time()
                execution_time = end_time - start_time

                print(f"  min_support: {min_support:<5} | Time: {execution_time:8.3f}s | Patterns: {num_patterns}")
                
                results.append({
                    "algorithm": name,
                    "min_support": min_support,
                    "execution_time": execution_time,
                    "num_patterns": num_patterns,
                })

            except Exception as e:
                print(f"  min_support: {min_support:<5} | FAILED with error: {e}")
                results.append({
                    "algorithm": name,
                    "min_support": min_support,
                    "execution_time": -1,
                    "num_patterns": -1,
                })

    # 4. Analyze and print summary
    print("\n--- Tuning Summary ---")
    results_df = pd.DataFrame(results)
    print(results_df.to_string())

    print("\n--- Recommendations ---")
    for name in algorithm_classes.keys():
        algo_results = results_df[results_df['algorithm'] == name]
        valid_results = algo_results[algo_results['execution_time'] > 0]
        
        if not valid_results.empty:
            # Find a balance: not too slow, but generates a good number of patterns
            # Heuristic: prefer lower time, but avoid zero patterns
            reasonable_time = valid_results[valid_results['num_patterns'] > 10]
            if not reasonable_time.empty:
                best_choice = reasonable_time.loc[reasonable_time['execution_time'].idxmin()]
            else: # If all generate few patterns, pick the fastest
                best_choice = valid_results.loc[valid_results['execution_time'].idxmin()]
            
            print(f"For {name}: Recommended min_support = {best_choice['min_support']} (Time: {best_choice['execution_time']:.2f}s, Patterns: {best_choice['num_patterns']})")
        else:
            print(f"For {name}: No successful runs. Manual inspection needed.")

if __name__ == "__main__":
    tune_parameters()
