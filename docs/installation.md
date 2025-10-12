# Installation Guide

This document provides step‑by‑step instructions for installing the
`FP‑Tree‑IDS‑Research` project and its dependencies.  We recommend
using the provided Docker container for a reproducible environment,
but Conda can be used for local development.

## Prerequisites

Before you begin, ensure the following software is installed:

* **Git** for cloning the repository.
* **Docker** (version 20.10 or newer) and **Docker Compose** (version 1.29
  or newer) **– recommended** for containerised execution.
* Alternatively, **Conda** for managing Python environments.  We
  recommend Miniconda or Anaconda (Python 3.8+).

## Option 1: Docker Installation

Docker is the easiest way to run the code without polluting your
system with dependencies.  Follow these steps:

```bash
# Clone the repository
git clone https://github.com/yourusername/FP-Tree-IDS-Research.git
cd FP-Tree-IDS-Research

# Pull the base images (optional but recommended)
docker-compose pull

# Start a shell inside the container
docker-compose run fp-tree-experiments bash

# Inside the container, you can run Python scripts.  For example:
python data/download_dataset.py
python experiments/main_experiment.py
```

The `docker-compose.yml` file mounts the `data` and `results`
directories, so any datasets downloaded or results generated inside the
container will persist on your host.

## Option 2: Conda Installation

If you prefer to run the code outside Docker, you can create a Conda
environment using the provided `environment.yml` file.  This file
specifies all necessary dependencies, including Java for the Flink
connector and Python libraries.

```bash
git clone https://github.com/yourusername/FP-Tree-IDS-Research.git
cd FP-Tree-IDS-Research

# Create the environment
conda env create -f environment.yml

# Activate the environment
conda activate fp-tree-ids-research

# Install any remaining Python dependencies
pip install -r requirements.txt

# Run experiments
python data/download_dataset.py
python experiments/main_experiment.py
```

### Troubleshooting Conda installation

* If the environment fails to resolve, ensure you have updated the
  Conda package channels (`conda update -n base -c defaults conda`).
* Should conflicts arise, try creating the environment with
  `conda env create -f environment.yml --no-update-deps`.

## Dataset Acquisition

The experiments require the **CIC‑IDS2017** dataset.  The script
`data/download_dataset.py` contains a convenience function for
downloading the dataset; however, you must agree to the CIC licence
terms before downloading.  If the script fails due to network or
authentication issues, download the dataset manually from the official
CIC website and place the files in `data/raw/`.

## Running Experiments

Once the environment is set up and the dataset is available, you can
reproduce the results described in the paper by running the scripts in
the `experiments/` directory.  See `docs/reproduction_guide.md` for
detailed instructions on reproducing each experiment and interpreting
the outputs.