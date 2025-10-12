import sys
import os
import subprocess
from pathlib import Path

# The project root is the directory containing this script.
project_root = Path(__file__).resolve().parent

# Prefer a local venv Python if present; otherwise fall back to current interpreter
venv_python = project_root / '.venv' / 'Scripts' / 'python.exe'
if not venv_python.exists():
    venv_python = Path(sys.executable)

print(f"Project root: {project_root}")
print(f"Using Python executable: {venv_python}")

# Prepare environment so that `src` is importable when running as a module
env = os.environ.copy()
env["PYTHONPATH"] = str(project_root) + (os.pathsep + env["PYTHONPATH"] if "PYTHONPATH" in env else "")

# Run the main experiment as a module to avoid path issues
cmd = [str(venv_python), "-m", "experiments.main_experiment"]
print(f"Executing command: {' '.join(cmd)}")
try:
    subprocess.run(cmd, check=True, cwd=str(project_root), env=env, shell=False)
    print("Experiment script finished.")
except subprocess.CalledProcessError as e:
    print(f"Experiment script failed with exit code {e.returncode}")
except FileNotFoundError:
    print(f"Error: Could not find the python executable at {venv_python}")
