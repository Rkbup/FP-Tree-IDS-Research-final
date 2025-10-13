"""
main_experiment_with_checkpointing.py
=====================================

Checkpointing-enabled version of main_experiment.py that:
1. Saves progress every 1000 transactions
2. Can resume from the last checkpoint if interrupted
3. Preserves partial results
"""

from __future__ import annotations

import argparse
import json
import os
import pickle
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

# Increase recursion limit for deep FP-tree mining
sys.setrecursionlimit(10000)

from src.preprocessing.data_loader import load_cic_ids2017
from src.preprocessing.feature_engineering import FeatureEngineer
from src.preprocessing.transaction_builder import TransactionBuilder
from src.algorithms.fp_tree import FPTree
from src.algorithms.variants.no_reorder import NoReorderFPTree
from src.algorithms.variants.partial_rebuild import PartialRebuildFPTree
from src.algorithms.variants.two_tree import TwoTreeFPTree
from src.algorithms.variants.decay_hybrid import DecayHybridFPTree
from src.algorithms.baselines.half_space_trees import HalfSpaceTrees
from src.algorithms.baselines.random_cut_forest import RandomCutForest
from src.algorithms.baselines.online_autoencoder import OnlineAutoencoder
from src.streaming.window_manager import SlidingWindowManager
from src.evaluation.metrics import classification_metrics, pr_auc, throughput, memory_usage_mb, bootstrap_confidence_interval
from src.evaluation.visualization import plot_throughput_latency


CHECKPOINT_DIR = Path("checkpoints")
CHECKPOINT_INTERVAL = 1000  # Save every 1000 transactions


def save_checkpoint(
    checkpoint_path: Path,
    algorithm_name: str,
    current_idx: int,
    y_pred: np.ndarray,
    scores: np.ndarray,
    mem_usages: List[float],
    start_time: float,
    algorithm_state: Optional[object] = None
):
    """Save checkpoint to disk."""
    checkpoint_data = {
        'algorithm_name': algorithm_name,
        'current_idx': current_idx,
        'y_pred': y_pred,
        'scores': scores,
        'mem_usages': mem_usages,
        'start_time': start_time,
        'algorithm_state': algorithm_state
    }
    with open(checkpoint_path, 'wb') as f:
        pickle.dump(checkpoint_data, f)
    print(f"  💾 Checkpoint saved at transaction {current_idx}")


def load_checkpoint(checkpoint_path: Path) -> Optional[Dict]:
    """Load checkpoint from disk."""
    if checkpoint_path.exists():
        with open(checkpoint_path, 'rb') as f:
            return pickle.load(f)
    return None


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run the FP-Tree experiment with checkpointing support."
    )
    parser.add_argument(
        "--raw-dir",
        default="data/raw",
        help="Directory containing the raw CIC-IDS2017 CSV files.",
    )
    parser.add_argument(
        "--days",
        nargs="+",
        help="Optional list of day names to load.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-file loading messages.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from last checkpoint if available.",
    )
    parser.add_argument(
        "--clear-checkpoints",
        action="store_true",
        help="Clear all checkpoints and start fresh.",
    )
    return parser.parse_args()


def evaluate_streaming_performance_with_checkpointing(
    algorithms: Dict[str, object],
    transactions: List[List[str]],
    labels: np.ndarray,
    window_size: int,
    anomaly_threshold: float = 0.5,
    resume: bool = False,
) -> Dict[str, Dict[str, float]]:
    """Process transactions with checkpointing support."""
    
    n = len(transactions)
    results: Dict[str, Dict[str, float]] = {}
    
    # Create checkpoint directory
    CHECKPOINT_DIR.mkdir(exist_ok=True)
    
    # Precompute baseline features
    print("Preparing baseline features...")
    vocab = sorted({item for txn in transactions for item in txn})
    item_to_idx = {item: i for i, item in enumerate(vocab)}
    X_full = np.zeros((n, len(vocab)), dtype=np.int8)
    for i, txn in enumerate(transactions):
        for item in txn:
            X_full[i, item_to_idx[item]] = 1
    
    for name, alg in algorithms.items():
        print(f"\n{'='*60}")
        print(f"Evaluating {name}")
        print(f"{'='*60}")
        
        checkpoint_path = CHECKPOINT_DIR / f"checkpoint_{name}.pkl"
        
        # Try to load checkpoint
        checkpoint = None
        start_idx = 0
        if resume:
            checkpoint = load_checkpoint(checkpoint_path)
            if checkpoint and checkpoint['algorithm_name'] == name:
                start_idx = checkpoint['current_idx'] + 1
                print(f"  ♻️  Resuming from transaction {start_idx}/{n}")
        
        # Initialize containers
        if checkpoint:
            y_pred = checkpoint['y_pred']
            scores = checkpoint['scores']
            mem_usages = checkpoint['mem_usages']
            start_time = checkpoint['start_time']
        else:
            y_pred = np.zeros(n, dtype=np.int8)
            scores = np.zeros(n, dtype=np.float32)
            mem_usages: List[float] = []
            start_time = time.time()
        
        # Process transactions
        if isinstance(alg, (FPTree, PartialRebuildFPTree, DecayHybridFPTree)):
            window_manager = SlidingWindowManager(alg, max_size=window_size)
            
            for idx in range(start_idx, n):
                txn = transactions[idx]
                window_manager.update(txn)
                
                patterns = alg.mine_frequent_patterns()
                score = 1.0
                if patterns:
                    max_support = max(patterns.values())
                    score = 1.0 - (max_support / max(1, len(window_manager.window)))
                
                scores[idx] = score
                y_pred[idx] = 1 if score >= anomaly_threshold else 0
                
                if idx % 1000 == 0:
                    mem_usages.append(memory_usage_mb())
                
                # Checkpoint every CHECKPOINT_INTERVAL
                if (idx + 1) % CHECKPOINT_INTERVAL == 0:
                    save_checkpoint(
                        checkpoint_path, name, idx,
                        y_pred, scores, mem_usages, start_time
                    )
                
                # Progress indicator
                if (idx + 1) % 5000 == 0:
                    elapsed = time.time() - start_time
                    progress = (idx + 1) / n * 100
                    rate = (idx + 1) / elapsed
                    eta = (n - idx - 1) / rate if rate > 0 else 0
                    print(f"  Progress: {progress:.1f}% ({idx+1}/{n}) | "
                          f"Rate: {rate:.0f} txn/s | ETA: {eta/60:.1f} min")
        
        elif isinstance(alg, TwoTreeFPTree):
            for idx in range(start_idx, n):
                txn = transactions[idx]
                alg.insert_transaction(txn)
                
                patterns = alg.mine_frequent_patterns()
                score = 1.0
                if patterns:
                    max_support = max(patterns.values())
                    score = 1.0 - (max_support / (2 * alg.half_window_size))
                
                scores[idx] = score
                y_pred[idx] = 1 if score >= anomaly_threshold else 0
                
                if idx % 1000 == 0:
                    mem_usages.append(memory_usage_mb())
                
                if (idx + 1) % CHECKPOINT_INTERVAL == 0:
                    save_checkpoint(
                        checkpoint_path, name, idx,
                        y_pred, scores, mem_usages, start_time
                    )
                
                if (idx + 1) % 5000 == 0:
                    elapsed = time.time() - start_time
                    progress = (idx + 1) / n * 100
                    rate = (idx + 1) / elapsed
                    eta = (n - idx - 1) / rate if rate > 0 else 0
                    print(f"  Progress: {progress:.1f}% ({idx+1}/{n}) | "
                          f"Rate: {rate:.0f} txn/s | ETA: {eta/60:.1f} min")
        
        elif isinstance(alg, (HalfSpaceTrees, RandomCutForest, OnlineAutoencoder)):
            warmup = min(window_size, n)
            if start_idx == 0:
                alg.fit(X_full[:warmup])
                start_idx = warmup
            
            for idx in range(start_idx, n):
                x = X_full[idx:idx+1]
                score = alg.score_samples(x)[0]
                scores[idx] = score
                y_pred[idx] = 1 if score >= anomaly_threshold else 0
                
                if (idx % window_size) == 0:
                    start = max(0, idx - window_size + 1)
                    alg.fit(X_full[start:idx+1])
                
                if idx % 1000 == 0:
                    mem_usages.append(memory_usage_mb())
                
                if (idx + 1) % CHECKPOINT_INTERVAL == 0:
                    save_checkpoint(
                        checkpoint_path, name, idx,
                        y_pred, scores, mem_usages, start_time
                    )
                
                if (idx + 1) % 5000 == 0:
                    elapsed = time.time() - start_time
                    progress = (idx + 1) / n * 100
                    rate = (idx + 1) / elapsed
                    eta = (n - idx - 1) / rate if rate > 0 else 0
                    print(f"  Progress: {progress:.1f}% ({idx+1}/{n}) | "
                          f"Rate: {rate:.0f} txn/s | ETA: {eta/60:.1f} min")
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        # Compute metrics
        metrics = classification_metrics(labels, y_pred)
        metrics['pr_auc'] = pr_auc(labels, scores)
        metrics['throughput'] = throughput(n, elapsed)
        metrics['latency'] = (elapsed / max(1, n)) * 1000
        metrics['memory'] = float(np.mean(mem_usages)) if mem_usages else memory_usage_mb()
        
        ci_lower, ci_upper = bootstrap_confidence_interval(metrics['f1'] for _ in range(30))
        metrics['f1_ci_lower'] = ci_lower
        metrics['f1_ci_upper'] = ci_upper
        
        results[name] = metrics
        
        # Remove checkpoint after successful completion
        if checkpoint_path.exists():
            checkpoint_path.unlink()
            print(f"  ✅ Completed! Checkpoint removed.")
    
    return results


def main() -> None:
    args = parse_args()
    
    # Clear checkpoints if requested
    if args.clear_checkpoints:
        if CHECKPOINT_DIR.exists():
            import shutil
            shutil.rmtree(CHECKPOINT_DIR)
            print("🗑️  All checkpoints cleared.")
    
    # Ensure results directories exist
    Path('results/figures').mkdir(parents=True, exist_ok=True)
    Path('results/tables').mkdir(parents=True, exist_ok=True)
    Path('results/logs').mkdir(parents=True, exist_ok=True)
    
    print("\n" + "="*60)
    print("FP-Tree IDS Experiment (with Checkpointing)")
    print("="*60)
    if args.resume:
        print("🔄 Resume mode: Will continue from last checkpoint if available")
    print()
    
    # Load dataset
    print("Loading dataset...")
    data = load_cic_ids2017(raw_dir=args.raw_dir, days=args.days, verbose=not args.quiet)
    labels = (data['Label'] != 'BENIGN').astype(int).to_numpy()
    print(f"✅ Loaded {len(data)} samples")
    
    # Feature engineering
    print("\nPerforming feature engineering...")
    fe = FeatureEngineer(n_bins=5)
    selected = fe.select_features(data)
    discretised = fe.discretize_continuous_features(selected)
    fe.save_bin_edges('data/bin_edges.json')
    print("✅ Feature engineering complete")
    
    # Build transactions
    print("\nBuilding transactions...")
    tb = TransactionBuilder()
    transactions = tb.build_transactions(discretised)
    print(f"✅ Built {len(transactions)} transactions")
    
    # Prepare algorithms (NR removed due to scalability issues on large datasets)
    algorithms = {
        # 'NR': NoReorderFPTree(min_support=0.1, window_size=20000),  # Disabled: too slow on 2.5M transactions
        'PR': PartialRebuildFPTree(min_support=0.005, window_size=20000, rebuild_threshold=0.1),
        'TT': TwoTreeFPTree(min_support=0.005, half_window_size=10000),
        'DH': DecayHybridFPTree(min_support=0.005, window_size=20000, decay_factor=0.995),
        'HS-Trees': HalfSpaceTrees(n_trees=25, tree_depth=15),
        'RCF': RandomCutForest(n_trees=100, sample_size=256),
        'Autoencoder': OnlineAutoencoder(encoding_dim=0.5)
    }
    
    # Evaluate performance
    results = evaluate_streaming_performance_with_checkpointing(
        algorithms=algorithms,
        transactions=transactions,
        labels=labels,
        window_size=20000,
        anomaly_threshold=0.5,
        resume=args.resume
    )
    
    # Save results
    results_df = pd.DataFrame.from_dict(results, orient='index')
    results_df.to_csv('results/tables/performance.csv')
    print(f"\n📊 Results saved to: results/tables/performance.csv")
    
    # Plot
    plot_throughput_latency(
        {name: {'throughput': m['throughput'], 'latency': m['latency']} 
         for name, m in results.items()},
        'results/figures/throughput_latency.png'
    )
    print(f"📈 Plot saved to: results/figures/throughput_latency.png")
    
    print("\n" + "="*60)
    print("✅ EXPERIMENT COMPLETED SUCCESSFULLY!")
    print("="*60)
    print("\nResults Summary:")
    print(results_df.to_string())


if __name__ == '__main__':
    main()
