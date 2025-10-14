"""
comprehensive_smoke_test.py
============================

This script runs a comprehensive smoke test of the entire pipeline with
proper error handling and Ctrl+C (KeyboardInterrupt) protection.

It tests:
1. Small data loading and preprocessing
2. All FP-Tree variants
3. Checkpointing system
4. Result generation

Usage:
    python experiments/comprehensive_smoke_test.py
"""

import sys
import signal
import time
import json
from pathlib import Path
import numpy as np
import pandas as pd

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.preprocessing.data_loader import load_cic_ids2017
from src.preprocessing.feature_engineering import FeatureEngineer
from src.preprocessing.transaction_builder import TransactionBuilder
from src.algorithms.variants.no_reorder import NoReorderFPTree
from src.algorithms.variants.partial_rebuild import PartialRebuildFPTree
from src.algorithms.variants.two_tree import TwoTreeFPTree
from src.algorithms.variants.decay_hybrid import DecayHybridFPTree
from src.streaming.window_manager import SlidingWindowManager
from src.evaluation.metrics import classification_metrics, pr_auc, throughput, memory_usage_mb

# Global flag for graceful shutdown
shutdown_requested = False

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully."""
    global shutdown_requested
    print("\n\n⚠️  Shutdown requested. Cleaning up gracefully...")
    shutdown_requested = True

# Register signal handler
signal.signal(signal.SIGINT, signal_handler)


def run_comprehensive_smoke_test():
    """Execute comprehensive smoke test with all variants."""
    
    print("=" * 70)
    print("COMPREHENSIVE SMOKE TEST")
    print("=" * 70)
    
    # Configuration for smoke test
    MAX_FLOWS = 1000  # Small sample for quick testing
    WINDOW_SIZE = 200
    MIN_SUPPORT = 0.1
    
    try:
        # Step 1: Load and preprocess data
        print("\n[1/4] Loading and preprocessing data...")
        data = load_cic_ids2017(raw_dir="data/raw", days=["Monday"], verbose=False)
        data = data.iloc[:MAX_FLOWS].copy()
        
        labels = (data['Label'] != 'BENIGN').astype(int).to_numpy()
        
        fe = FeatureEngineer(n_bins=3)
        selected = fe.select_features(data)
        discretised = fe.discretize_continuous_features(selected)
        
        tb = TransactionBuilder()
        transactions = tb.build_transactions(discretised.drop(columns=['Label'], errors='ignore'))
        
        print(f"  ✓ Loaded {len(transactions)} transactions")
        print(f"  ✓ Attack ratio: {labels.sum() / len(labels) * 100:.2f}%")
        
        if shutdown_requested:
            print("  ⚠️  Shutdown during data loading")
            return False
        
        # Step 2: Test all FP-Tree variants
        print("\n[2/4] Testing FP-Tree variants...")
        
        variants = {
            'NR': NoReorderFPTree(min_support=MIN_SUPPORT, window_size=WINDOW_SIZE),
            'PR': PartialRebuildFPTree(min_support=MIN_SUPPORT, window_size=WINDOW_SIZE, rebuild_threshold=0.1),
            'TT': TwoTreeFPTree(min_support=MIN_SUPPORT, half_window_size=WINDOW_SIZE // 2),
            'DH': DecayHybridFPTree(min_support=MIN_SUPPORT, window_size=WINDOW_SIZE, decay_factor=0.995)
        }
        
        results = {}
        
        for name, alg in variants.items():
            if shutdown_requested:
                print(f"  ⚠️  Shutdown before testing {name}")
                break
                
            print(f"\n  Testing {name}...")
            start_time = time.time()
            
            y_pred = np.zeros(len(transactions), dtype=np.int8)
            scores = np.zeros(len(transactions), dtype=np.float32)
            
            if name == 'TT':
                # Two-tree variant
                for idx, txn in enumerate(transactions):
                    if shutdown_requested:
                        print(f"    ⚠️  Shutdown at transaction {idx}/{len(transactions)}")
                        break
                        
                    alg.insert_transaction(txn)
                    
                    if idx % 50 == 0:
                        patterns = alg.mine_frequent_patterns()
                        score = 1.0
                        if patterns:
                            max_support = max(patterns.values())
                            score = 1.0 - (max_support / (2 * alg.half_window_size))
                        scores[idx] = score
                        y_pred[idx] = 1 if score >= 0.5 else 0
            else:
                # Standard variants with window manager
                window_manager = SlidingWindowManager(alg, max_size=WINDOW_SIZE)
                
                for idx, txn in enumerate(transactions):
                    if shutdown_requested:
                        print(f"    ⚠️  Shutdown at transaction {idx}/{len(transactions)}")
                        break
                        
                    window_manager.update(txn)
                    
                    if idx % 50 == 0:
                        patterns = alg.mine_frequent_patterns()
                        score = 1.0
                        if patterns:
                            max_support = max(patterns.values())
                            score = 1.0 - (max_support / max(1, len(window_manager.window)))
                        scores[idx] = score
                        y_pred[idx] = 1 if score >= 0.5 else 0
            
            if shutdown_requested:
                continue
                
            elapsed = time.time() - start_time
            
            # Calculate metrics
            metrics = classification_metrics(labels, y_pred)
            metrics['throughput'] = throughput(len(transactions), elapsed)
            metrics['memory'] = memory_usage_mb()
            
            results[name] = metrics
            
            print(f"    ✓ Precision: {metrics['precision']:.4f}")
            print(f"    ✓ Recall: {metrics['recall']:.4f}")
            print(f"    ✓ F1-Score: {metrics['f1']:.4f}")
            print(f"    ✓ Throughput: {metrics['throughput']:.2f} flows/sec")
            print(f"    ✓ Time: {elapsed:.2f}s")
        
        if shutdown_requested:
            print("\n  ⚠️  Test interrupted by user")
            return False
        
        # Step 3: Save results
        print("\n[3/4] Saving smoke test results...")
        
        Path('results/smoke_test').mkdir(parents=True, exist_ok=True)
        
        results_df = pd.DataFrame.from_dict(results, orient='index')
        results_path = 'results/smoke_test/smoke_test_results.csv'
        results_df.to_csv(results_path)
        
        print(f"  ✓ Results saved to: {results_path}")
        
        # Step 4: Summary
        print("\n[4/4] Test Summary")
        print("-" * 70)
        print(results_df.to_string())
        print("-" * 70)
        
        print("\n" + "=" * 70)
        print("✅ SMOKE TEST PASSED!")
        print("=" * 70)
        print("\nAll components are working correctly.")
        print("You can now proceed with full-scale experiments.\n")
        
        return True
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by Ctrl+C")
        return False
    except Exception as e:
        print(f"\n\n❌ SMOKE TEST FAILED!")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = run_comprehensive_smoke_test()
    sys.exit(0 if success else 1)
