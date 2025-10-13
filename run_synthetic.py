import sys
import os
import multiprocessing
sys.path.insert(0, "/app")

# Set number of threads to max
os.environ['OMP_NUM_THREADS'] = str(multiprocessing.cpu_count())
os.environ['MKL_NUM_THREADS'] = str(multiprocessing.cpu_count())
os.environ['NUMEXPR_NUM_THREADS'] = str(multiprocessing.cpu_count())

import pandas as pd
import numpy as np
from pathlib import Path
from src.preprocessing.feature_engineering import FeatureEngineer
from src.preprocessing.transaction_builder import TransactionBuilder
from experiments.main_experiment import evaluate_streaming_performance
from src.algorithms.variants.no_reorder import NoReorderFPTree
from src.algorithms.variants.partial_rebuild import PartialRebuildFPTree
from src.algorithms.variants.two_tree import TwoTreeFPTree
from src.algorithms.variants.decay_hybrid import DecayHybridFPTree
from src.algorithms.baselines.half_space_trees import HalfSpaceTrees
from src.algorithms.baselines.random_cut_forest import RandomCutForest
from src.algorithms.baselines.online_autoencoder import OnlineAutoencoder
from src.evaluation.visualization import plot_throughput_latency

print("="*60)
print("SYNTHETIC DATASET EXPERIMENT")
print("="*60)
print(f"Using {multiprocessing.cpu_count(^)} CPU cores")
print()

print("Loading synthetic dataset...")
data = pd.read_csv("/app/data/raw/synthetic_cic_ids2017.csv")
print(f"✅ Loaded {len(data^)} rows")

Path('/app/results/figures').mkdir(parents=True, exist_ok=True)
Path('/app/results/tables').mkdir(parents=True, exist_ok=True)

print("\\nProcessing features...")
labels = (data['Label'] != 'BENIGN').astype(int).to_numpy()
fe = FeatureEngineer(n_bins=5)
selected = fe.select_features(data)
discretised = fe.discretize_continuous_features(selected)
print("✅ Feature engineering complete")

print("\\nBuilding transactions...")
tb = TransactionBuilder()
transactions = tb.build_transactions(discretised)
print(f"✅ Built {len(transactions^)} transactions")

print("\\nInitializing algorithms...")
algorithms = {
    'NR': NoReorderFPTree(min_support=0.005, window_size=2000),
    'PR': PartialRebuildFPTree(min_support=0.005, window_size=2000, rebuild_threshold=0.1),
    'TT': TwoTreeFPTree(min_support=0.005, half_window_size=1000),
    'DH': DecayHybridFPTree(min_support=0.005, window_size=2000, decay_factor=0.995),
    'HS-Trees': HalfSpaceTrees(n_trees=25, tree_depth=15),
    'RCF': RandomCutForest(n_trees=100, sample_size=256),
    'Autoencoder': OnlineAutoencoder(encoding_dim=0.5)
}

print("\\nStarting evaluation...")
print("="*60)
results = evaluate_streaming_performance(
    algorithms=algorithms, 
    transactions=transactions, 
    labels=labels, 
    window_size=2000, 
    anomaly_threshold=0.5
)

print("\\nSaving results...")
results_df = pd.DataFrame.from_dict(results, orient='index')
results_df.to_csv('/app/results/tables/performance_synthetic.csv')
print(f"✅ Results saved to: results/tables/performance_synthetic.csv")

print("\\nGenerating plots...")
plot_throughput_latency(
    {name: {'throughput': m['throughput'], 'latency': m['latency']} 
     for name, m in results.items()}, 
    '/app/results/figures/throughput_latency_synthetic.png'
)
print(f"✅ Plot saved to: results/figures/throughput_latency_synthetic.png")

print("\\n" + "="*60)
print("✅ SYNTHETIC EXPERIMENT COMPLETED!")
print("="*60)
print("\\nResults Summary:")
print(results_df.to_string())
