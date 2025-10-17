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
    """Deprecated: Ctrl+C handler (no-op)."""
    # Intentionally left as a no-op for backward compatibility.
    # SIGINT is fully ignored via signal.SIG_IGN below.
    pass

def shutdown_handler():
    """Handle Ctrl+H for graceful shutdown."""
    global shutdown_requested
    while True:
        try:
            if keyboard.is_pressed('ctrl+h'):
                if not shutdown_requested:
                    print("\n\n[WARN] Ctrl+H pressed - Shutdown requested. Saving checkpoint and cleaning up...")
                    shutdown_requested = True
                break
        except:
            pass

# Register signal handlers
# Fully ignore Ctrl+C so copying text in terminal doesn't kill the process
signal.signal(signal.SIGINT, signal.SIG_IGN)

# Start keyboard listener for Ctrl+H in separate thread
keyboard_thread = threading.Thread(target=shutdown_handler, daemon=True)
keyboard_thread.start()

print("[INFO] Ctrl+C is ignored for safe copying. Press Ctrl+H to stop gracefully.")

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
            print(f"  [INFO] Resuming from checkpoint at index {start_idx}/{n}")
        
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
                print(f"  [INFO] Rebuilding window state from scratch...")
                for idx in tqdm(range(start_idx), desc="Rebuilding window", leave=False):
                    window_manager.update(transactions[idx])
            
            for idx in tqdm(range(start_idx, n), total=n, initial=start_idx, desc=f"Processing {name}"):
                if shutdown_requested:
                    print(f"\n  [WARN] Shutdown requested. Saving checkpoint at index {idx}...")
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
                print(f"  [INFO] Rebuilding tree state from scratch...")
                for idx in tqdm(range(start_idx), desc="Rebuilding tree", leave=False):
                    alg.insert_transaction(transactions[idx])
            
            for idx in tqdm(range(start_idx, n), total=n, initial=start_idx, desc=f"Processing {name}"):
                if shutdown_requested:
                    print(f"\n  [WARN] Shutdown requested. Saving checkpoint at index {idx}...")
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
                print(f"  [INFO] Rebuilding model state from scratch...")
                alg.fit(X_full[:warmup])
            
            for idx in tqdm(range(start_idx, n), total=n, initial=start_idx, desc=f"Processing {name}"):
                if shutdown_requested:
                    print(f"\n  [WARN] Shutdown requested. Saving checkpoint at index {idx}...")
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
        
    print(f"  [OK] Precision: {metrics['precision']:.4f}")
    print(f"  [OK] Recall: {metrics['recall']:.4f}")
    print(f"  [OK] F1-Score: {metrics['f1']:.4f}")
    print(f"  [OK] PR-AUC: {metrics['pr_auc']:.4f}")
    print(f"  [OK] Throughput: {metrics['throughput']:.2f} flows/sec")

    import multiprocessing
    cpu_count = multiprocessing.cpu_count()
    print(f"Using {cpu_count} CPU cores for parallel processing.")

    def process_transaction(args):
        name, alg, idx, txn, window_manager, cached_patterns, anomaly_threshold, X_full = args
        score = 1.0
        if isinstance(alg, (NoReorderFPTree, PartialRebuildFPTree, DecayHybridFPTree)):
            window_manager.update(txn)
            if idx == 0 or ((idx + 1) % PATTERN_REFRESH_INTERVAL) == 0:
                cached_patterns = alg.mine_frequent_patterns()
            if cached_patterns:
                max_support = max(cached_patterns.values())
                score = 1.0 - (max_support / max(1, len(window_manager.window)))
            return score, 1 if score >= anomaly_threshold else 0
        elif isinstance(alg, TwoTreeFPTree):
            alg.insert_transaction(txn)
            if idx == 0 or ((idx + 1) % PATTERN_REFRESH_INTERVAL) == 0:
                cached_patterns = alg.mine_frequent_patterns()
            if cached_patterns:
                max_support = max(cached_patterns.values())
                score = 1.0 - (max_support / (2 * alg.half_window_size))
            return score, 1 if score >= anomaly_threshold else 0
        elif isinstance(alg, HalfSpaceTrees):
            x = X_full[idx:idx+1]
            score = alg.score_samples(x)[0]
            return score, 1 if score >= anomaly_threshold else 0
        elif isinstance(alg, RandomCutForest):
            x = X_full[idx:idx+1]
            score = alg.score_samples(x)[0]
            return score, 1 if score >= anomaly_threshold else 0
        elif isinstance(alg, OnlineAutoencoder):
            x = X_full[idx:idx+1]
            score = alg.score_samples(x)[0]
            return score, 1 if score >= anomaly_threshold else 0
        else:
            raise TypeError(f"Unsupported algorithm type: {type(alg)}")

    for name, alg in algorithms.items():
        print(f"\nEvaluating {name}...")
        start_time = time.time()
        y_pred = np.zeros(n, dtype=np.int8)
        scores = np.zeros(n, dtype=np.float32)
        mem_usages = []
        window_manager = None
        cached_patterns = None
        if isinstance(alg, (NoReorderFPTree, PartialRebuildFPTree, DecayHybridFPTree)):
            window_manager = SlidingWindowManager(alg, max_size=window_size)
            cached_patterns = {}
        args_list = [
            (name, alg, idx, txn, window_manager, cached_patterns, anomaly_threshold, X_full)
            for idx, txn in enumerate(transactions)
        ]
        with multiprocessing.Pool(cpu_count) as pool:
            results_list = pool.map(process_transaction, args_list)
        for idx, (score, pred) in enumerate(results_list):
            scores[idx] = score
            y_pred[idx] = pred
            if idx % 1000 == 0:
                mem_usages.append(memory_usage_mb())
            # Print progress percentage every 1% or 1000 transactions
            if n > 0 and (idx % max(1, n // 100) == 0 or idx == n - 1):
                percent = int((idx + 1) / n * 100)
                print(f"Progress: {percent}% complete", end='\r', flush=True)
        end_time = time.time()
        elapsed = end_time - start_time
        metrics = classification_metrics(labels, y_pred)
        metrics['pr_auc'] = pr_auc(labels, scores)
        metrics['throughput'] = throughput(n, elapsed)
        metrics['latency'] = (elapsed / max(1, n)) * 1000  # ms per flow
        metrics['memory'] = float(np.mean(mem_usages)) if mem_usages else memory_usage_mb()
        results[name] = metrics
        delete_checkpoint(name)
    return results
    print("\n" + results_df.to_string())
