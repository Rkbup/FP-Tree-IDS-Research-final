"""
resume_experiment.py
===================

An optimized version of main_experiment_with_checkpointing.py that:
1. Has more robust checkpointing
2. Better error handling
3. Progress reporting
4. Memory management improvements
"""

from __future__ import annotations

import argparse
import json
import os
import pickle
import sys
import time
import traceback
import gc
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

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


CHECKPOINT_DIR = Path("/app/checkpoints")
CHECKPOINT_INTERVAL = 1000  # Save every 1000 transactions


def ensure_dir_exists(path):
    """Create directory if it doesn't exist"""
    if not isinstance(path, Path):
        path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


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
    """Save checkpoint to disk with error handling."""
    ensure_dir_exists(checkpoint_path.parent)
    
    checkpoint_data = {
        'algorithm_name': algorithm_name,
        'current_idx': current_idx,
        'y_pred': y_pred,
        'scores': scores,
        'mem_usages': mem_usages,
        'start_time': start_time,
        'algorithm_state': algorithm_state
    }
    
    # First save to a temporary file
    temp_path = checkpoint_path.with_suffix('.tmp')
    try:
        with open(temp_path, 'wb') as f:
            pickle.dump(checkpoint_data, f)
        
        # If successful, rename to the actual checkpoint file
        if temp_path.exists():
            if checkpoint_path.exists():
                checkpoint_path.unlink()
            temp_path.rename(checkpoint_path)
            print(f"  💾 Checkpoint saved at transaction {current_idx}")
        else:
            print(f"  ⚠️ Failed to create temporary checkpoint file")
    except Exception as e:
        print(f"  ⚠️ Error saving checkpoint: {str(e)}")


def load_checkpoint(checkpoint_path: Path) -> Optional[Dict]:
    """Load checkpoint from disk with error handling."""
    if not checkpoint_path.exists():
        return None
    
    try:
        with open(checkpoint_path, 'rb') as f:
            return pickle.load(f)
    except Exception as e:
        print(f"  ⚠️ Error loading checkpoint: {str(e)}")
        # Backup the corrupt checkpoint
        if checkpoint_path.exists():
            backup_path = checkpoint_path.with_suffix('.bak')
            try:
                checkpoint_path.rename(backup_path)
                print(f"  ⚠️ Corrupt checkpoint backed up to {backup_path}")
            except:
                pass
        return None


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run the FP-Tree experiment with robust checkpointing support."
    )
    parser.add_argument(
        "--raw-dir",
        default="/app/data/raw",
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
        "--algorithm",
        default="all",
        choices=["NR", "PR", "TT", "DH", "HS-Trees", "RCF", "Autoencoder", "all"],
        help="Specify a single algorithm to run or 'all'",
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
    """Process transactions with robust checkpointing support."""
    
    n = len(transactions)
    results: Dict[str, Dict[str, float]] = {}
    
    # Create checkpoint directory
    ensure_dir_exists(CHECKPOINT_DIR)
    
    # Precompute baseline features
    print("Preparing baseline features...")
    vocab = sorted({item for txn in transactions for item in txn})
    item_to_idx = {item: i for i, item in enumerate(vocab)}
    X_full = np.zeros((n, len(vocab)), dtype=np.int8)
    for i, txn in enumerate(transactions):
        for item in txn:
            X_full[i, item_to_idx[item]] = 1
    
    print(f"Features prepared: {X_full.shape}")
    
    for name, alg in algorithms.items():
        print(f"\n{'='*60}")
        print(f"Evaluating {name}")
        print(f"{'='*60}")
        
        # Periodically collect garbage to reduce memory footprint
        gc.collect()
        
        checkpoint_path = CHECKPOINT_DIR / f"checkpoint_{name}.pkl"
        print(f"Checkpoint path: {checkpoint_path}")
        
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
        try:
            if isinstance(alg, (FPTree, NoReorderFPTree, PartialRebuildFPTree, DecayHybridFPTree)):
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
                        
                        # Force garbage collection periodically
                        gc.collect()
                    
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
                        gc.collect()
                    
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
                    print(f"  Training baseline on initial {warmup} samples...")
                    alg.fit(X_full[:warmup])
                    print(f"  Initial training complete.")
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
                        gc.collect()
                    
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
        
        except KeyboardInterrupt:
            print("\n  ⚠️ Process interrupted by user.")
            # Save checkpoint before exiting
            save_checkpoint(
                checkpoint_path, name, idx,
                y_pred, scores, mem_usages, start_time
            )
            print("  💾 Checkpoint saved. Run with --resume to continue.")
            sys.exit(1)
            
        except Exception as e:
            print(f"\n  ❌ Error during processing: {str(e)}")
            traceback.print_exc()
            # Save checkpoint before exiting
            try:
                save_checkpoint(
                    checkpoint_path, name, idx,
                    y_pred, scores, mem_usages, start_time
                )
                print("  💾 Emergency checkpoint saved. Run with --resume to continue.")
            except:
                print("  ⚠️ Failed to save emergency checkpoint.")
            continue
        
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
            try:
                checkpoint_path.unlink()
                print(f"  ✅ Completed! Checkpoint removed.")
            except:
                print(f"  ⚠️ Could not remove checkpoint, but processing completed successfully.")
    
    return results


def main() -> None:
    args = parse_args()
    
    # Clear checkpoints if requested
    if args.clear_checkpoints:
        if CHECKPOINT_DIR.exists():
            import shutil
            try:
                shutil.rmtree(CHECKPOINT_DIR)
                print("🗑️  All checkpoints cleared.")
            except Exception as e:
                print(f"Failed to clear checkpoints: {str(e)}")
                pass
        ensure_dir_exists(CHECKPOINT_DIR)
    
    # Ensure results directories exist
    for path in ['results/figures', 'results/tables', 'results/logs']:
        ensure_dir_exists(path)
    
    print("\n" + "="*60)
    print("FP-Tree IDS Experiment (with Robust Checkpointing)")
    print("="*60)
    if args.resume:
        print("🔄 Resume mode: Will continue from last checkpoint if available")
    print()
    
    # Load dataset
    print("Loading dataset...")
    data = None
    try:
        data = load_cic_ids2017(raw_dir=args.raw_dir, days=args.days, verbose=not args.quiet)
        
        # Handle possible memory issues by forcing compression
        data = data.copy()
        
        # Convert data types to reduce memory
        for col in data.select_dtypes(include=['float64']).columns:
            data[col] = data[col].astype('float32')
            
        for col in data.select_dtypes(include=['int64']).columns:
            data[col] = data[col].astype('int32')
        
        labels = (data['Label'] != 'BENIGN').astype(int).to_numpy()
        print(f"✅ Loaded {len(data)} samples")
    except Exception as e:
        print(f"❌ Error loading dataset: {str(e)}")
        traceback.print_exc()
        sys.exit(1)
    
    # Feature engineering
    print("\nPerforming feature engineering...")
    try:
        fe = FeatureEngineer(n_bins=5)
        selected = fe.select_features(data)
        discretised = fe.discretize_continuous_features(selected)
        fe.save_bin_edges('/app/data/bin_edges.json')
        print("✅ Feature engineering complete")
        
        # Free up memory
        del data
        gc.collect()
    except Exception as e:
        print(f"❌ Error in feature engineering: {str(e)}")
        traceback.print_exc()
        sys.exit(1)
    
    # Build transactions
    print("\nBuilding transactions...")
    try:
        tb = TransactionBuilder()
        transactions = tb.build_transactions(discretised)
        print(f"✅ Built {len(transactions)} transactions")
        
        # Free up memory
        del discretised
        gc.collect()
    except Exception as e:
        print(f"❌ Error building transactions: {str(e)}")
        traceback.print_exc()
        sys.exit(1)
    
    # Prepare algorithms
    all_algorithms = {
        'NR': NoReorderFPTree(min_support=0.005, window_size=20000),
        'PR': PartialRebuildFPTree(min_support=0.005, window_size=20000, rebuild_threshold=0.1),
        'TT': TwoTreeFPTree(min_support=0.005, half_window_size=10000),
        'DH': DecayHybridFPTree(min_support=0.005, window_size=20000, decay_factor=0.995),
        'HS-Trees': HalfSpaceTrees(n_trees=25, tree_depth=15),
        'RCF': RandomCutForest(n_trees=100, sample_size=256),
        'Autoencoder': OnlineAutoencoder(encoding_dim=0.5)
    }
    
    # Select algorithms based on CLI argument
    algorithms = {}
    if args.algorithm == "all":
        algorithms = all_algorithms
    else:
        algorithms[args.algorithm] = all_algorithms[args.algorithm]
    
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
    results_df.to_csv('/app/results/tables/performance.csv')
    print(f"\n📊 Results saved to: results/tables/performance.csv")
    
    # Plot
    try:
        plot_throughput_latency(
            {name: {'throughput': m['throughput'], 'latency': m['latency']} 
             for name, m in results.items()},
            '/app/results/figures/throughput_latency.png'
        )
        print(f"📈 Plot saved to: results/figures/throughput_latency.png")
    except Exception as e:
        print(f"⚠️ Error creating plot: {str(e)}")
    
    print("\n" + "="*60)
    print("✅ EXPERIMENT COMPLETED SUCCESSFULLY!")
    print("="*60)
    print("\nResults Summary:")
    print(results_df.to_string())


if __name__ == '__main__':
    main()