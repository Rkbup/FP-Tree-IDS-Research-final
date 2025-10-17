# FP-Tree IDS Experiment Recovery Instructions
**Date:** October 17, 2025  
**Status:** PC Restart - Resume from here

---

## ✅ What Was Successfully Completed

### 1. Docker Image Built ✅
- **Image Name:** `fp-tree-ids:latest`
- **Size:** 747MB (includes complete CIC-IDS2017 dataset)
- **Dataset:** All 8 CSV files included (~864MB total)
  - Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv (77MB)
  - Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv (77MB)
  - Friday-WorkingHours-Morning.pcap_ISCX.csv (58MB)
  - Monday-WorkingHours.pcap_ISCX.csv (177MB)
  - Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv (83MB)
  - Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv (52MB)
  - Tuesday-WorkingHours.pcap_ISCX.csv (135MB)
  - Wednesday-workingHours.pcap_ISCX.csv (225MB)

### 2. Fix Applied ✅
- **Problem:** CSV files were excluded by `.dockerignore`
- **Solution:** Renamed `.dockerignore` to `.dockerignore.bak`
- **Result:** Dataset successfully included in Docker image

### 3. Kubernetes Deployment ✅
- **Namespace:** `fp-tree` (created)
- **PVC:** `fp-tree-results` (10Gi) - created
- **Jobs Deployed:**
  - `fp-tree-main-experiment` → Pod: `fp-tree-main-experiment-rhxql`
  - `fp-tree-synthetic-experiment` → Pod: `fp-tree-synthetic-experiment-qdnbd`

### 4. Verification ✅
- Both pods were **Running**
- Main experiment: Loading all 8 CSV files successfully
- Synthetic experiment: Performing feature engineering
- **NO FileNotFoundError!** ✅

---

## 🔄 After PC Restart - Recovery Steps

### Step 1: Start Docker Desktop
```powershell
# Docker Desktop should auto-start, or manually open it
# Wait 30-60 seconds for it to be fully ready

# Verify Docker is running
docker version
```

### Step 2: Verify Docker Image Still Exists
```powershell
# Check if the image is still there
docker images fp-tree-ids

# Expected output: fp-tree-ids:latest with size ~747MB
# If MISSING → Need to rebuild (see rebuild section below)
```

### Step 3: Check Kubernetes Cluster
```powershell
# Verify Kubernetes is running
kubectl cluster-info

# Check if namespace exists
kubectl get namespace fp-tree

# If namespace missing → Need to recreate (see recovery section)
```

### Step 4: Check Experiment Status
```powershell
# Check if jobs still exist
kubectl get jobs -n fp-tree

# Check pod status
kubectl get pods -n fp-tree

# Possible statuses:
# - Running: Great! Experiments still running
# - Completed: Extract results
# - Failed/Error: Check logs and redeploy
# - No pods found: Redeploy from scratch
```

### Step 5: Review Pod Logs (if pods exist)
```powershell
# Main experiment logs
kubectl logs -n fp-tree fp-tree-main-experiment-rhxql --tail=100

# Synthetic experiment logs
kubectl logs -n fp-tree fp-tree-synthetic-experiment-qdnbd --tail=100

# Check how far experiments progressed
```

---

## 🚀 Quick Resume Commands

### Scenario A: Pods Still Running (Best Case)
```powershell
# Just monitor them
kubectl get pods -n fp-tree -w

# Follow logs
kubectl logs -f -n fp-tree fp-tree-main-experiment-rhxql
kubectl logs -f -n fp-tree fp-tree-synthetic-experiment-qdnbd
```

### Scenario B: Experiments Need to be Restarted
```powershell
# 1. Clean up old jobs
kubectl delete job --all -n fp-tree

# 2. Verify PVC still exists (or recreate)
kubectl get pvc -n fp-tree
# If missing:
kubectl apply -f k8s/results-pvc.yaml

# 3. Deploy main experiment
kubectl apply -f k8s/job.yaml

# 4. Deploy synthetic experiment
kubectl apply -f k8s/synthetic-job.yaml

# 5. Verify pods are running
kubectl get pods -n fp-tree

# 6. Check logs for no errors
kubectl logs -f -n fp-tree <pod-name>
```

### Scenario C: Docker Image Missing (Worst Case)
```powershell
# Ensure .dockerignore is still disabled
# (Should be renamed to .dockerignore.bak)
Test-Path ".dockerignore.bak"  # Should return True

# Rebuild the image (takes ~12-15 minutes)
docker build -t fp-tree-ids:latest .

# Verify CSV files in image
docker run --rm fp-tree-ids:latest ls -la /app/data/raw/MachineLearningCSV/MachineLearningCVE/

# Then proceed with Scenario B above
```

---

## 📝 Important Files Reference

### Kubernetes Manifests
- `k8s/job.yaml` - Main experiment job definition
- `k8s/synthetic-job.yaml` - Synthetic experiment job
- `k8s/results-pvc.yaml` - Results storage PVC

### Configuration Files
- `Dockerfile` - Docker image build instructions
- `.dockerignore.bak` - Disabled to include dataset
- `config/default.yaml` - Default configuration
- `config/experiment_params.yaml` - Experiment parameters

### Key Directories
- `data/raw/MachineLearningCSV/MachineLearningCVE/` - Dataset location (local)
- `/app/data/raw/` - Dataset location in Docker image
- `/app/results/` - Results output directory in containers

---

## 🎯 Expected Duration

- **Main Experiment (CIC-IDS2017 real data):** 4-5 hours
- **Synthetic Experiment:** 2-3 hours
- Both run in parallel on Kubernetes

---

## 📊 Resource Allocation

### Main Experiment Pod
- Requests: 2 CPU, 4Gi RAM
- Limits: 4 CPU, 8Gi RAM

### Synthetic Experiment Pod
- Requests: 1 CPU, 2Gi RAM
- Limits: 2 CPU, 4Gi RAM

---

## ✅ Success Criteria

When experiments complete successfully, you should see:
- Pod status: `Completed`
- Results in PVC: `fp-tree-results`
- No errors in logs
- Output files generated

---

## 🔧 Troubleshooting

### If Docker Desktop won't start:
1. Check Task Manager → Docker Desktop process
2. Restart Docker Desktop service
3. Reinstall Docker Desktop (last resort)

### If Kubernetes cluster is broken:
1. Docker Desktop → Settings → Kubernetes → Reset Kubernetes Cluster
2. Wait for cluster to restart
3. Recreate namespace and redeploy

### If pods keep failing:
1. Check pod describe: `kubectl describe pod -n fp-tree <pod-name>`
2. Check resource availability: `kubectl top nodes`
3. Check image pull: Verify `fp-tree-ids:latest` exists locally

---

## 📞 Quick Help Commands

```powershell
# Check everything at once
Write-Host "=== Docker Status ===" -ForegroundColor Cyan
docker version

Write-Host "`n=== Docker Images ===" -ForegroundColor Cyan
docker images fp-tree-ids

Write-Host "`n=== Kubernetes Cluster ===" -ForegroundColor Cyan
kubectl cluster-info

Write-Host "`n=== Namespace ===" -ForegroundColor Cyan
kubectl get namespace fp-tree

Write-Host "`n=== Jobs ===" -ForegroundColor Cyan
kubectl get jobs -n fp-tree

Write-Host "`n=== Pods ===" -ForegroundColor Cyan
kubectl get pods -n fp-tree

Write-Host "`n=== PVC ===" -ForegroundColor Cyan
kubectl get pvc -n fp-tree
```

---

**🎉 You're all set! After PC restart, follow the steps above to resume your experiments.**
