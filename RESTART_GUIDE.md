# Docker Desktop Restart Guide

## Current Issue
Docker Desktop is not responding (500 Internal Server Error). This typically happens after extended operation and requires a restart.

## Solution Steps

### 1. Restart Docker Desktop

**Windows:**
1. Right-click the Docker icon in system tray (bottom-right)
2. Select "Quit Docker Desktop"
3. Wait 10 seconds
4. Open Docker Desktop from Start Menu
5. Wait for the whale icon to stabilize (no animation)
6. Wait for Kubernetes indicator to turn green

**Or use PowerShell:**
```powershell
# Stop Docker Desktop
Stop-Process -Name "Docker Desktop" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 10

# Start Docker Desktop
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"

# Wait for startup (this will take 30-60 seconds)
Write-Host "Waiting for Docker Desktop to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 60
```

### 2. Verify System is Ready

After Docker Desktop restarts, run:

```powershell
.\quick_status.ps1
```

You should see:
- ✓ Docker is running
- ✓ Kubernetes is accessible
- Pod status for both experiments

### 3. Check Experiment Status

If pods are still running:
```powershell
kubectl get pods -n fp-tree
```

Expected output:
```
NAME                                  READY   STATUS    RESTARTS   AGE
fp-tree-main-experiment-xxxxx         1/1     Running   0          Xh
fp-tree-synthetic-experiment-xxxxx    1/1     Running   0          Xh
```

### 4. Monitor Experiments

Use the watch script:
```powershell
.\watch_experiments.ps1 -RefreshSeconds 20
```

Or check logs manually:
```powershell
# Main experiment
kubectl logs -f -n fp-tree fp-tree-main-experiment-<pod-id>

# Synthetic experiment
kubectl logs -f -n fp-tree fp-tree-synthetic-experiment-<pod-id>
```

## If Experiments Were Lost

If pods were terminated during Docker restart, redeploy:

```powershell
# Create namespace and PVC
kubectl apply -f k8s/results-pvc.yaml

# Deploy both experiments
kubectl apply -f k8s/job.yaml
kubectl apply -f k8s/synthetic-job.yaml

# Verify deployment
kubectl get pods -n fp-tree -w
```

## Troubleshooting

### Docker Won't Start
1. Check Task Manager - kill any stuck Docker processes
2. Restart Windows (if Docker is completely stuck)
3. Check Docker Desktop logs: `%APPDATA%\Docker\log.txt`

### Kubernetes Not Green
1. Docker Desktop → Settings → Kubernetes
2. Uncheck "Enable Kubernetes"
3. Apply & Restart
4. Re-check "Enable Kubernetes"
5. Apply & Restart

### Pods Missing
1. Check if namespace exists: `kubectl get namespaces | Select-String fp-tree`
2. If missing, redeploy everything: `kubectl apply -f k8s/`
3. Check pod logs: `kubectl describe pod -n fp-tree <pod-name>`

## Expected Timeline

- Docker Desktop restart: 30-60 seconds
- Kubernetes ready: additional 30 seconds
- Pods restart (if lost): 2-3 minutes
- Experiments continue: 2-5 hours total

## Quick Commands

```powershell
# System status
.\quick_status.ps1

# Pod status
kubectl get pods -n fp-tree

# Watch pods
kubectl get pods -n fp-tree -w

# Logs (replace <pod-name>)
kubectl logs -f -n fp-tree <pod-name>

# Monitor dashboard
.\watch_experiments.ps1

# Extract results (when complete)
.\extract_results.ps1
```

---

**Bottom Line:** Restart Docker Desktop, wait for Kubernetes to go green, run `.\quick_status.ps1` to verify everything is back up.
