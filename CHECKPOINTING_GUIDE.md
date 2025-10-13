# Checkpointing-Enabled Experiment Runner

This guide explains how to run the FP-Tree IDS experiments with periodic checkpointing so you can pause, power off, or recover from errors without losing progress.

## Highlights

- Auto-save: writes a checkpoint every N transactions (default 1000).
- Power-safe: safe to interrupt; re-run to resume from the last save.
- Auto-resume: continues from the last saved index per algorithm.
- Progress tracking: shows percentage, throughput, and ETA.

## How To Run

On Windows (PowerShell or cmd):

```cmd
run_with_checkpointing.bat
```

If interrupted, just run the script again. It will attempt to resume.

### Command-line flags (inside the runner)

The underlying Python entrypoint supports:

- `--resume`: resume from the last checkpoint if available.
- `--clear-checkpoints`: remove all checkpoints and start from scratch.
- `--raw-dir`: location of raw CSV files (defaults to `data/raw`).
- `--days`: optional subset of day names to load.

## Checkpoint Files

Checkpoints live under `checkpoints/` and are per algorithm:

```
checkpoints/
  checkpoint_NR.pkl           # NoReorder FP-Tree progress
  checkpoint_PR.pkl           # Partial Rebuild progress
  checkpoint_TT.pkl           # Two-Tree progress
  checkpoint_DH.pkl           # Decay Hybrid progress
  checkpoint_HS-Trees.pkl
  checkpoint_RCF.pkl
  checkpoint_Autoencoder.pkl
```

Each file stores:
- Current index (transaction offset)
- Predicted labels and scores up to that point
- Periodic memory usage samples
- Optional algorithm state

## Progress Output

Typical console output during a run:

```
============================================================
Evaluating PR
============================================================
Resuming from transaction 145000/2830743
Progress: 51.1% (144999/2830743) | Rate: 2550 txn/s | ETA: 17.3 min
Checkpoint saved at transaction 145000
```

## Clear / Reset

To remove all checkpoints and start fresh:

```cmd
rmdir /s /q checkpoints
```

Alternatively, pass `--clear-checkpoints` to the checkpointing runner.

## Performance Notes

- Real dataset (~2.8M transactions): 30–60 minutes on a modern desktop (depends on CPU/RAM and Docker limits).
- Resume mid-run (e.g., at 50%): often 15–30 minutes more.
- Synthetic dataset (~5K transactions): typically under 5 minutes.

## Troubleshooting

- “Resuming from transaction X” not shown:
  - No checkpoint exists for that algorithm, or the checkpoint filename differs.
  - Ensure you ran with `--resume` or re-launch the `.bat` runner which enables resume.
- Checkpoint corrupted:
  - Delete `checkpoints/` and re-run from the beginning.
- Progress is slow:
  - Increase Docker CPU/RAM limits in Docker Desktop.
  - Close heavy background applications.

## Outputs

Results are saved under `results/`:

```
results/
  figures/
    throughput_latency.png
  tables/
    performance.csv
  logs/
```

If you use the provided runners, they also copy results to
`results_real_data/` or `results_synthetic_data/` for convenience.

---

Tip: Use the robust runner (`run_robust.bat`) if you want additional error
handling and automatic emergency checkpoints during failures.

