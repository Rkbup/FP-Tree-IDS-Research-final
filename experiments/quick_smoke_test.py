"""
quick_smoke_test.py
===================

A minimal, fast smoke test to verify the system is working correctly.
Tests only one algorithm with a tiny dataset sample.

Usage:
    python experiments/quick_smoke_test.py
"""

import sys
import signal
from pathlib import Path
import pandas as pd

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("=" * 60)
print("QUICK SMOKE TEST")
print("=" * 60)

# Handle Ctrl+C gracefully
def signal_handler(sig, frame):
    print("\n\n⚠ Test interrupted by user (Ctrl+C)")
    print("Exiting gracefully...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

try:
    print("\n[1/5] Importing modules...")
    from src.preprocessing.feature_engineering import FeatureEngineer
    from src.preprocessing.transaction_builder import TransactionBuilder
    from src.algorithms.variants.no_reorder import NoReorderFPTree
    print("  ✓ All imports successful")
    
    print("\n[2/5] Loading synthetic dataset...")
    df = pd.read_csv("data/raw/synthetic_cic_ids2017.csv")
    print(f"  ✓ Loaded {len(df)} records")
    
    # Use only first 1000 records for quick test
    df_sample = df.head(1000)
    print(f"  ✓ Using {len(df_sample)} records for smoke test")
    
    print("\n[3/5] Feature engineering...")
    fe = FeatureEngineer(n_bins=5)
    df_selected = fe.select_features(df_sample)
    df_featured = fe.discretize_continuous_features(df_selected)
    print("  ✓ Features engineered")
    
    print("\n[4/5] Building transactions...")
    tb = TransactionBuilder()
    transactions = tb.build_transactions(df_featured.drop(columns=['Label'], errors='ignore'))
    print(f"  ✓ Built {len(transactions)} transactions")
    
    print("\n[5/5] Testing FP-Tree algorithm...")
    algorithm = NoReorderFPTree(min_support=0.05, window_size=500)
    
    for i, txn in enumerate(transactions):
        algorithm.insert_transaction(txn)
        
        # Mine patterns periodically
        if (i + 1) % 100 == 0:
            patterns = algorithm.mine_frequent_patterns()
            print(f"  Progress: {i+1}/{len(transactions)} | Patterns: {len(patterns)}")
    
    # Final mining
    final_patterns = algorithm.mine_frequent_patterns()
    
    print("\n" + "=" * 60)
    print("✅ SMOKE TEST PASSED!")
    print("=" * 60)
    print(f"Total transactions processed: {len(transactions)}")
    print(f"Final frequent patterns found: {len(final_patterns)}")
    print("\nSystem is working correctly!")
    print("You can now run the full experiments.")
    
except Exception as e:
    print("\n" + "=" * 60)
    print("❌ SMOKE TEST FAILED!")
    print("=" * 60)
    print(f"Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
