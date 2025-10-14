@echo off
echo Starting all experiments in parallel...

start /b python experiments/main_experiment.py --config results/exp_01_exp-ms0.01-ws10k/config.yaml --output-dir results/exp_01_exp-ms0.01-ws10k
start /b python experiments/main_experiment.py --config results/exp_02_exp-ms0.05-ws10k/config.yaml --output-dir results/exp_02_exp-ms0.05-ws10k
start /b python experiments/main_experiment.py --config results/exp_03_exp-ms0.1-ws10k/config.yaml --output-dir results/exp_03_exp-ms0.1-ws10k
start /b python experiments/main_experiment.py --config results/exp_04_exp-ms0.02-ws20k/config.yaml --output-dir results/exp_04_exp-ms0.02-ws20k
start /b python experiments/main_experiment.py --config results/exp_05_exp-ms0.02-ws50k/config.yaml --output-dir results/exp_05_exp-ms0.02-ws50k
start /b python experiments/main_experiment.py --config results/exp_06_exp-pr-rebuild0.02/config.yaml --output-dir results/exp_06_exp-pr-rebuild0.02

echo All experiment processes have been launched.
echo Monitor the individual output directories in 'results/' for progress.
