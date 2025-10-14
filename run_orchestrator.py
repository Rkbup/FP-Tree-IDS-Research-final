"""
run_orchestrator.py
===================

This script orchestrates running multiple experiments in parallel based on a 
configuration matrix. It is designed to work with different execution backends.

The script performs the following steps:
1.  Parses the experiment matrix file (`config/experiment_matrix.yaml`).
2.  For each experiment defined in the matrix:
    a. Creates a unique output directory (e.g., `results/exp_01_low_support`).
    b. Generates a specific YAML configuration file within that directory, 
       overriding default parameters with the ones from the matrix.
    c. Generates a command to execute the main experiment script 
       (`experiments/main_experiment.py`) with the generated config and output directory.
3.  Collects all commands into a single shell script (`run_all_experiments.bat` 
    for Windows) that can be executed to run all experiments in parallel.

Usage
-----
Run this script from the project root:

```bash
python run_orchestrator.py
```

This will generate the `run_all_experiments.bat` file, which you can then run.
"""

import yaml
import os
from pathlib import Path
import argparse
import shutil

def generate_experiment_commands(matrix_path: str, default_config_path: str, output_script_path: str):
    """
    Generates a batch script to run multiple experiments in parallel.

    Args:
        matrix_path (str): Path to the experiment matrix YAML file.
        default_config_path (str): Path to the default configuration YAML file.
        output_script_path (str): Path to write the final batch script.
    """
    # Load the experiment matrix
    with open(matrix_path, 'r') as f:
        matrix = yaml.safe_load(f)

    # Load the default configuration
    with open(default_config_path, 'r') as f:
        default_config = yaml.safe_load(f)

    commands = []
    base_results_dir = Path("results")

    print("Generating experiment configurations...")

    for i, experiment in enumerate(matrix['experiments']):
        exp_name = experiment['name']
        exp_dir = base_results_dir / f"exp_{i+1:02d}_{exp_name}"
        
        # Create a clean directory for the experiment
        if exp_dir.exists():
            shutil.rmtree(exp_dir)
        exp_dir.mkdir(parents=True)

        # Create a new config for this specific experiment
        exp_config = default_config.copy()
        exp_config.update(experiment['params'])
        
        # Write the specific config file
        exp_config_path = exp_dir / "config.yaml"
        with open(exp_config_path, 'w') as f:
            yaml.dump(exp_config, f)
            
        print(f"  - Created config for '{exp_name}' in {exp_dir}")

        # Generate the command to run the experiment
        # We use start /b to run commands in parallel on Windows
        command = (
            f"start /b python experiments/main_experiment.py "
            f"--config {exp_config_path.as_posix()} "
            f"--output-dir {exp_dir.as_posix()}"
        )
        commands.append(command)

    # Write all commands to a batch file
    with open(output_script_path, 'w') as f:
        f.write("@echo off\n")
        f.write("echo Starting all experiments in parallel...\n\n")
        for command in commands:
            f.write(f"{command}\n")
        f.write("\n")
        f.write("echo All experiment processes have been launched.\n")
        f.write("echo Monitor the individual output directories in 'results/' for progress.\n")

    print(f"\nSuccessfully generated batch script: {output_script_path}")
    print("You can now run this script to start all experiments.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Experiment Orchestrator")
    parser.add_argument(
        "--matrix",
        default="config/experiment_matrix.yaml",
        help="Path to the experiment matrix file."
    )
    parser.add_argument(
        "--default-config",
        default="config/default.yaml",
        help="Path to the default parameters config file."
    )
    parser.add_argument(
        "--output-script",
        default="run_all_experiments.bat",
        help="Name of the generated batch script."
    )
    args = parser.parse_args()

    generate_experiment_commands(
        matrix_path=args.matrix,
        default_config_path=args.default_config,
        output_script_path=args.output_script
    )
