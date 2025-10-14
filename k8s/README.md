# Kubernetes Deployment Guide

This directory contains Kubernetes manifests that let you run the FP-Tree IDS
experiments on a cluster. The manifests are opinionated but designed so you can
override storage classes, resource requests and container image names without
editing the application code.

## 1. Build and push the container image

1. Authenticate to your registry (GitHub Container Registry is used as an
  example):

  ```bash
  echo "<TOKEN>" | docker login ghcr.io -u <USERNAME> --password-stdin
  ```

1. Build the image from the project root:

  ```bash
  docker build -t ghcr.io/<USERNAME>/fp-tree-ids:latest .
  ```

1. Push the image:

  ```bash
  docker push ghcr.io/<USERNAME>/fp-tree-ids:latest
  ```

Update the image reference in `job.yaml` if you choose a different registry or
image tag.

## 2. Prepare storage for data and results

The manifests assume two persistent volume claims:

- `fp-tree-data` – mounted at `/app/data` inside the container. Populate the
  CIC-IDS2017 CSV files under `data/raw/` before submitting the job.
- `fp-tree-results` – mounted at `/app/results` to capture experiment outputs.

The default PVC definition uses the cluster's default storage class. Adjust the
`storageClassName`, size, or access modes in `pvc.yaml` if needed.

## 3. Apply the manifests

Create the namespace, config map, PVCs, and job:

```bash
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f pvc.yaml
kubectl apply -f job.yaml
```

Monitor progress:

```bash
kubectl -n fp-tree get pods
kubectl -n fp-tree logs job/fp-tree-main-experiment
```

When the job completes you can copy results out of the cluster, e.g.:

```bash
kubectl -n fp-tree cp <pod-name>:/app/results ./results
```

## 4. Clean up

After collecting your results, delete the job and PVCs if you no longer need
persistent storage:

```bash
kubectl delete -n fp-tree job fp-tree-main-experiment
kubectl delete -n fp-tree pvc fp-tree-data fp-tree-results
kubectl delete namespace fp-tree
```

## 5. Customisations

- **Config overrides** – edit `configmap.yaml` to change any experiment
  parameters. The ConfigMap is mounted at `/app/config/experiment_params.yaml`.
- **Resource requests** – update the `resources` section in `job.yaml` to match
  your cluster's capacity (CPU, memory, GPU).
- **Alternate scripts** – adjust the command in `job.yaml` if you want to run
  `run_with_checkpointing.bat` or any other experiment entry point.
