"""
Wrapper to run experiment with unbuffered output for live monitoring
"""
import sys
import subprocess

# Force unbuffered output
sys.stdout = sys.stdout.reconfigure(line_buffering=True)
sys.stderr = sys.stderr.reconfigure(line_buffering=True)

print("🚀 Starting FP-Tree IDS Main Experiment (Unbuffered)", flush=True)
print("=" * 60, flush=True)

# Run the experiment
subprocess.run([sys.executable, "experiments/main_experiment.py"], 
               bufsize=0, text=True)
