"""
synthetic_full_experiment.py
=============================

This script runs a comprehensive evaluation of all FP-Tree variants and
baseline algorithms on the complete synthetic CIC-IDS2017 dataset.

This provides a quick but thorough comparison of all algorithms before
running the full-scale experiments on the real dataset.

Usage
-----
Run this script from the project root:

```bash
python experiments/synthetic_full_experiment.py
```
"""

import sys
import time
import json
import signal
import keyboard
import threading
from pathlib import Path
import numpy as np
import pandas as pd
from tqdm import tqdm

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Global flag for graceful shutdown
shutdown_requested = False

def ctrl_c_handler(signum, frame):
    """Handle Ctrl+C - Do nothing (ignore it)."""
    print("\n💡 Ctrl+C detected. Use Ctrl+H to stop the process gracefully.")
    print("   This prevents accidental interruption while copying error messages.")

def shutdown_handler():
    """Handle Ctrl+H for graceful shutdown."""
    global shutdown_requested
    while True:
        try:
            if keyboard.is_pressed('ctrl+h'):
                if not shutdown_requested:
                    print("\n\n⚠️  Ctrl+H pressed - Shutdown requested. Saving checkpoint and cleaning up...")
                    shutdown_requested = True
                break
        except:
            pass

# Register signal handlers
signal.signal(signal.SIGINT, ctrl_c_handler)  # Ignore Ctrl+C

# Start keyboard listener for Ctrl+H in separate thread
keyboard_thread = threading.Thread(target=shutdown_handler, daemon=True)
keyboard_thread.start()

from src.preprocessing.feature_engineering import FeatureEngineer
from src.preprocessing.transaction_builder import TransactionBuilder
from src.algorithms.variants.no_reorder import NoReorderFPTree
from src.algorithms.variants.partial_rebuild import PartialRebuildFPTree
from src.algorithms.variants.two_tree import TwoTreeFPTree
from src.algorithms.variants.decay_hybrid import DecayHybridFPTree
from src.algorithms.baselines.half_space_trees import HalfSpaceTrees
from src.algorithms.baselines.random_cut_forest import RandomCutForest
from src.algorithms.baselines.online_autoencoder import OnlineAutoencoder
from src.streaming.window_manager import SlidingWindowManager
from src.evaluation.metrics import classification_metrics, pr_auc, throughput, memory_usage_mb
from src.evaluation.visualization import plot_throughput_latency

# Configuration
SYNTHETIC_DATA_PATH = "data/raw/synthetic_cic_ids2017.csv"
WINDOW_SIZE = 2000  # Reduced for faster execution
MIN_SUPPORT = 0.05  # Increased to reduce computational load
ANOMALY_THRESHOLD = 0.5
PATTERN_REFRESH_INTERVAL = 500  # Mine patterns less frequently
CHECKPOINT_INTERVAL = 2000  # Save checkpoint every 2000 transactions
CHECKPOINT_DIR = Path("results/checkpoints")


def save_checkpoint(algo_name, idx, y_pred, scores, mem_usages):
    """Save checkpoint for resuming later."""
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    checkpoint_file = CHECKPOINT_DIR / f"synthetic_{algo_name}_checkpoint.json"
    
    checkpoint_data = {
        'last_index': int(idx),
        'y_pred': y_pred.tolist(),
        'scores': scores.tolist(),
        'mem_usages': mem_usages
    }
    
    with open(checkpoint_file, 'w') as f:
        json.dump(checkpoint_data, f)
    

def load_checkpoint(algo_name):
    """Load checkpoint if it exists."""
    checkpoint_file = CHECKPOINT_DIR / f"synthetic_{algo_name}_checkpoint.json"
    
    if checkpoint_file.exists():
        with open(checkpoint_file, 'r') as f:
            return json.load(f)
    return None


def delete_checkpoint(algo_name):
    """Delete checkpoint file after successful completion."""
    checkpoint_file = CHECKPOINT_DIR / f"synthetic_{algo_name}_checkpoint.json"
    if checkpoint_file.exists():
        checkpoint_file.unlink()


def evaluate_streaming_performance(
    algorithms: dict,
    transactions: list,
    labels: np.ndarray,
    window_size: int,
    anomaly_threshold: float = 0.5
) -> dict:
    """Process a stream of transactions with multiple algorithms."""
    n = len(transactions)
    results = {}
    
    # Precompute vectorized baseline features
    vocab = sorted({item for txn in transactions for item in txn})
    item_to_idx = {item: i for i, item in enumerate(vocab)}
    X_full = np.zeros((n, len(vocab)), dtype=np.int8)
    for i, txn in enumerate(transactions):
        for item in txn:
            X_full[i, item_to_idx[item]] = 1

    for name, alg in algorithms.items():
        print(f"\nEvaluating {name}...")
        
        # Check for checkpoint
        checkpoint = load_checkpoint(name)
        start_idx = 0
        
        if checkpoint:
            start_idx = checkpoint['last_index'] + 1
            print(f"  ℹ Resuming from checkpoint at index {start_idx}/{n}")
        
        start_time = time.time()
        
        y_pred = np.zeros(n, dtype=np.int8)
        scores = np.zeros(n, dtype=np.float32)
        mem_usages = []
        
        # Restore from checkpoint if available
        if checkpoint:
            y_pred = np.array(checkpoint['y_pred'], dtype=np.int8)
            scores = np.array(checkpoint['scores'], dtype=np.float32)
            mem_usages = checkpoint['mem_usages']
        
        if isinstance(alg, (NoReorderFPTree, PartialRebuildFPTree, DecayHybridFPTree)):
            # FP-tree variant using sliding window manager
            window_manager = SlidingWindowManager(alg, max_size=window_size)
            cached_patterns = {}
            
            # Rebuild window state from checkpoint
            if start_idx > 0:
                print(f"  ℹ Rebuilding window state from scratch...")
                for idx in tqdm(range(start_idx), desc="Rebuilding window", leave=False):
                    window_manager.update(transactions[idx])
            
            for idx in tqdm(range(start_idx, n), total=n, initial=start_idx, desc=f"Processing {name}"):
                if shutdown_requested:
                    print(f"\n  ⚠️  Shutdown requested. Saving checkpoint at index {idx}...")
                    save_checkpoint(name, idx - 1, y_pred, scores, mem_usages)
                    return results
                    
                window_manager.update(transactions[idx])
                
                if idx == 0 or ((idx + 1) % PATTERN_REFRESH_INTERVAL) == 0:
                    cached_patterns = alg.mine_frequent_patterns()
                
                score = 1.0
                if cached_patterns:
                    max_support = max(cached_patterns.values())
                    score = 1.0 - (max_support / max(1, len(window_manager.window)))
                
                scores[idx] = score
                y_pred[idx] = 1 if score >= anomaly_threshold else 0
                
                if idx % 1000 == 0:
                    mem_usages.append(memory_usage_mb())
                    
                # Save checkpoint periodically
                if (idx + 1) % CHECKPOINT_INTERVAL == 0:
                    save_checkpoint(name, idx, y_pred, scores, mem_usages)
                    
        elif isinstance(alg, TwoTreeFPTree):
            # Two-tree variant
            cached_patterns = {}
            
            # Rebuild tree state from checkpoint
            if start_idx > 0:
                print(f"  ℹ Rebuilding tree state from scratch...")
                for idx in tqdm(range(start_idx), desc="Rebuilding tree", leave=False):
                    alg.insert_transaction(transactions[idx])
            
            for idx in tqdm(range(start_idx, n), total=n, initial=start_idx, desc=f"Processing {name}"):
                if shutdown_requested:
                    print(f"\n  ⚠️  Shutdown requested. Saving checkpoint at index {idx}...")
                    save_checkpoint(name, idx - 1, y_pred, scores, mem_usages)
                    return results
                    
                alg.insert_transaction(transactions[idx])
                
                if idx == 0 or ((idx + 1) % PATTERN_REFRESH_INTERVAL) == 0:
                    cached_patterns = alg.mine_frequent_patterns()
                
                score = 1.0
                if cached_patterns:
                    max_support = max(cached_patterns.values())
                    score = 1.0 - (max_support / (2 * alg.half_window_size))
                
                scores[idx] = score
                y_pred[idx] = 1 if score >= anomaly_threshold else 0
                
                if idx % 1000 == 0:
                    mem_usages.append(memory_usage_mb())

                # Save checkpoint periodically
                if (idx + 1) % CHECKPOINT_INTERVAL == 0:
                    save_checkpoint(name, idx, y_pred, scores, mem_usages)
                    
        elif isinstance(alg, (HalfSpaceTrees, RandomCutForest, OnlineAutoencoder)):
            # Baseline models
            warmup = min(window_size, n)
            
            if start_idx == 0:
                alg.fit(X_full[:warmup])
                start_idx = warmup
            else:
                # Rebuild model state from checkpoint
                print(f"  ℹ Rebuilding model state from scratch...")
                alg.fit(X_full[:warmup])
            
            for idx in tqdm(range(start_idx, n), total=n, initial=start_idx, desc=f"Processing {name}"):
                if shutdown_requested:
                    print(f"\n  ⚠️  Shutdown requested. Saving checkpoint at index {idx}...")
                    save_checkpoint(name, idx - 1, y_pred, scores, mem_usages)
                    return results
                    
                x = X_full[idx:idx+1]
                score = alg.score_samples(x)[0]
                scores[idx] = score
                y_pred[idx] = 1 if score >= anomaly_threshold else 0
                
                if (idx % window_size) == 0:
                    start_idx_retrain = max(0, idx - window_size + 1)
                    alg.fit(X_full[start_idx_retrain:idx+1])
                
                if idx % 1000 == 0:
                    mem_usages.append(memory_usage_mb())

                # Save checkpoint periodically
                if (idx + 1) % CHECKPOINT_INTERVAL == 0:
                    save_checkpoint(name, idx, y_pred, scores, mem_usages)
        else:
            raise TypeError(f"Unsupported algorithm type: {type(alg)}")
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        # Compute metrics
        metrics = classification_metrics(labels, y_pred)
        metrics['pr_auc'] = pr_auc(labels, scores)
        metrics['throughput'] = throughput(n, elapsed)
        metrics['latency'] = (elapsed / max(1, n)) * 1000  # ms per flow
        metrics['memory'] = float(np.mean(mem_usages)) if mem_usages else memory_usage_mb()
        
        results[name] = metrics
        
        # Delete checkpoint after successful completion
        delete_checkpoint(name)
        
        print(f"  ✓ Precision: {metrics['precision']:.4f}")
        print(f"  ✓ Recall: {metrics['recall']:.4f}")
        print(f"  ✓ F1-Score: {metrics['f1']:.4f}")
        print(f"  ✓ PR-AUC: {metrics['pr_auc']:.4f}")
        print(f"  ✓ Throughput: {metrics['throughput']:.2f} flows/sec")
        print(f"  ✓ Latency: {metrics['latency']:.4f} ms/flow")
        print(f"  ✓ Memory: {metrics['memory']:.2f} MB")
    
    return results


def main():
    """Main function to run the synthetic dataset experiment."""
    print("=" * 60)
    print("COMPREHENSIVE SYNTHETIC DATASET EVALUATION")
    print("=" * 60)
    
    # Ensure results directories exist
    Path('results/figures').mkdir(parents=True, exist_ok=True)
    Path('results/tables').mkdir(parents=True, exist_ok=True)
    
    # Load synthetic dataset
    print(f"\n[1/4] Loading synthetic dataset from {SYNTHETIC_DATA_PATH}...")
    df = pd.read_csv(SYNTHETIC_DATA_PATH)
    print(f"  ✓ Loaded {len(df)} records")
    
    # Feature engineering
    print("\n[2/4] Performing feature engineering...")
    fe = FeatureEngineer(n_bins=5)
    df_selected = fe.select_features(df)
    df_featured = fe.discretize_continuous_features(df_selected)
    
    # Convert labels to binary
    if 'Label' in df_featured.columns:
        labels = (df_featured['Label'].str.upper() != 'BENIGN').astype(int).to_numpy()
    else:
        labels = np.zeros(len(df_featured))
    
    # Build transactions
    tb = TransactionBuilder()
    transactions = tb.build_transactions(df_featured.drop(columns=['Label'], errors='ignore'))
    print(f"  ✓ Created {len(transactions)} transactions")
    print(f"  ✓ Attack ratio: {labels.sum() / len(labels) * 100:.2f}%")
    
    # Prepare all algorithms
    print("\n[3/4] Initializing algorithms...")
    algorithms = {
        'NR': NoReorderFPTree(min_support=MIN_SUPPORT, window_size=WINDOW_SIZE),
        'PR': PartialRebuildFPTree(min_support=MIN_SUPPORT, window_size=WINDOW_SIZE, rebuild_threshold=0.1),
        'TT': TwoTreeFPTree(min_support=MIN_SUPPORT, half_window_size=WINDOW_SIZE // 2),
        'DH': DecayHybridFPTree(min_support=MIN_SUPPORT, window_size=WINDOW_SIZE, decay_factor=0.995),
        'HS-Trees': HalfSpaceTrees(n_trees=25, tree_depth=15),
        'RCF': RandomCutForest(n_trees=100, sample_size=256),
        'Autoencoder': OnlineAutoencoder(encoding_dim=0.5)
    }
    print(f"  ✓ Initialized {len(algorithms)} algorithms")
    
    # Evaluate all algorithms
    print("\n[4/4] Running comprehensive evaluation...")
    print("-" * 60)
    results = evaluate_streaming_performance(
        algorithms=algorithms,
        transactions=transactions,
        labels=labels,
        window_size=WINDOW_SIZE,
        anomaly_threshold=ANOMALY_THRESHOLD
    )
    
    # Save results
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    
    results_df = pd.DataFrame.from_dict(results, orient='index')
    results_df = results_df.round(4)
    
    print("\n" + results_df.to_string())
    
    # Save to CSV
    csv_path = 'results/tables/synthetic_performance.csv'
    results_df.to_csv(csv_path)
    print(f"\n✓ Results saved to: {csv_path}")
    
    # Plot throughput-latency trade-off
    plot_data = {
        name: {
            'throughput': m['throughput'],
            'latency': m['latency']
        }
        for name, m in results.items()
    }
    plot_path = 'results/figures/synthetic_throughput_latency.png'
    plot_throughput_latency(plot_data, plot_path)
    print(f"✓ Throughput-Latency plot saved to: {plot_path}")
    
    # Find best performers
    print("\n" + "=" * 60)
    print("BEST PERFORMERS")
    print("=" * 60)
    
    best_f1 = results_df['f1'].idxmax()
    best_throughput = results_df['throughput'].idxmax()
    best_memory = results_df['memory'].idxmin()
    
    print(f"\n🏆 Best F1-Score: {best_f1} ({results_df.loc[best_f1, 'f1']:.4f})")
    print(f"🏆 Best Throughput: {best_throughput} ({results_df.loc[best_throughput, 'throughput']:.2f} flows/sec)")
    print(f"🏆 Lowest Memory: {best_memory} ({results_df.loc[best_memory, 'memory']:.2f} MB)")
    
    print("\n" + "=" * 60)
    print("EVALUATION COMPLETE!")
    print("=" * 60)


if __name__ == '__main__':
    main()
