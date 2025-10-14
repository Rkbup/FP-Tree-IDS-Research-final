@echo off
REM ============================================================
REM Quick Restart Commands After Power Outage
REM ============================================================

echo.
echo ============================================================
echo FP-Tree IDS Experiment Recovery
echo ============================================================
echo.

REM Check Kubernetes Status
echo [1/4] Checking Kubernetes Status...
kubectl get pods -n fp-tree
kubectl get pvc -n fp-tree
echo.

REM Show K8s Logs
echo [2/4] Showing Main Experiment Logs (Last 50 lines)...
kubectl logs fp-tree-main-experiment-dq6r9 -n fp-tree --tail=50
echo.

REM Show Checkpoint Status
echo [3/4] Checking Synthetic Experiment Checkpoints...
dir results\checkpoints\*.json
echo.

REM Resume Options
echo [4/4] Resume Options:
echo.
echo To resume SYNTHETIC experiment:
echo   "C:/Users/Abdullah Rakib Akand/Downloads/FP-Tree-IDS-Research-final/.venv/Scripts/python.exe" experiments/synthetic_full_experiment.py
echo.
echo To monitor K8S experiment:
echo   kubectl logs fp-tree-main-experiment-dq6r9 -n fp-tree -f
echo.
echo To start monitoring dashboard:
echo   "C:/Users/Abdullah Rakib Akand/Downloads/FP-Tree-IDS-Research-final/.venv/Scripts/python.exe" monitor_experiments.py
echo.
echo ============================================================
pause
