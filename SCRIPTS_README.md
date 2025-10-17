# FP-Tree IDS Experiment - Automation Scripts

This directory contains automation scripts for managing the FP-Tree IDS experiments on Kubernetes.

## 📋 Prerequisites

- Docker Desktop with Kubernetes enabled
- kubectl configured and connected to cluster
- PowerShell 5.1 or higher

## 🚀 Quick Start

### 1. Check System Status
```powershell
.\status_report.ps1
```
Verifies Docker, Kubernetes, and experiment status.

### 2. Monitor Running Experiments
```powershell
# Quick one-time check
.\check_status.ps1

# Continuous monitoring with auto-refresh
.\watch_experiments.ps1 -RefreshSeconds 15
```

### 3. Extract Results (After Completion)
```powershell
.\extract_results.ps1
```
Copies all results from Kubernetes pods to `.\results-final\`

### 4. Archive Results
```powershell
# Basic archive
.\archive_results.ps1

# Include source code
.\archive_results.ps1 -IncludeCode
```
Creates timestamped archive in `.\archives\`

### 5. Cleanup
```powershell
# Delete jobs and pods (keep namespace)
.\cleanup.ps1

# Delete everything including namespace
.\cleanup.ps1 -DeleteNamespace

# Skip confirmation
.\cleanup.ps1 -Force
```

## 📁 Script Reference

### status_report.ps1
**Purpose:** Comprehensive system and experiment status check

**What it checks:**
- Docker Desktop status
- Kubernetes cluster connectivity
- fp-tree namespace existence
- Pod status and logs
- Results extraction status

**Usage:**
```powershell
.\status_report.ps1
```

**Output:** Detailed report with actionable next steps

---

### check_status.ps1
**Purpose:** Quick status snapshot

**What it shows:**
- Current pod status
- Recent log entries from both experiments
- Quick command reference

**Usage:**
```powershell
.\check_status.ps1
```

**Output:** Brief summary suitable for quick checks

---

### watch_experiments.ps1
**Purpose:** Real-time monitoring dashboard

**Parameters:**
- `RefreshSeconds` (default: 10) - Auto-refresh interval

**Usage:**
```powershell
# Default 10-second refresh
.\watch_experiments.ps1

# Custom refresh interval
.\watch_experiments.ps1 -RefreshSeconds 30
```

**Features:**
- Auto-refreshing display
- Color-coded status
- Recent log snippets
- Runtime tracking

**Exit:** Press Ctrl+C

---

### extract_results.ps1
**Purpose:** Extract experiment results from Kubernetes

**Parameters:**
- `OutputDir` (default: `.\results-final`) - Destination directory

**Usage:**
```powershell
# Default location
.\extract_results.ps1

# Custom location
.\extract_results.ps1 -OutputDir ".\my-results"
```

**What it does:**
1. Checks experiment completion status
2. Creates backup if directory exists
3. Copies results from each pod
4. Saves pod logs
5. Generates file summary

**Output Structure:**
```
results-final/
├── main/
│   ├── results/
│   │   ├── figures/
│   │   ├── tables/
│   │   └── logs/
│   └── experiment.log
└── synthetic/
    ├── results/
    │   ├── figures/
    │   ├── tables/
    │   └── logs/
    └── experiment.log
```

---

### archive_results.ps1
**Purpose:** Create timestamped archive of results

**Parameters:**
- `ArchiveDir` (default: `.\archives`) - Archive destination
- `IncludeCode` - Include source code in archive

**Usage:**
```powershell
# Basic archive (results only)
.\archive_results.ps1

# Include source code
.\archive_results.ps1 -IncludeCode

# Custom archive location
.\archive_results.ps1 -ArchiveDir "D:\Backups"
```

**What it creates:**
- Timestamped directory with all results
- metadata.json with archive information
- README.md with experiment details
- ZIP archive for easy sharing
- Optionally includes source code

**Archive naming:** `fp-tree-results-YYYYMMDD_HHMMSS`

---

### cleanup.ps1
**Purpose:** Remove Kubernetes resources

**Parameters:**
- `DeleteNamespace` - Also delete the fp-tree namespace
- `Force` - Skip confirmation prompts

**Usage:**
```powershell
# Standard cleanup (interactive)
.\cleanup.ps1

# Delete everything including namespace
.\cleanup.ps1 -DeleteNamespace

# Force cleanup without prompts
.\cleanup.ps1 -Force

# Force delete everything
.\cleanup.ps1 -DeleteNamespace -Force
```

**What it removes:**
1. Experiment jobs
2. Experiment pods
3. PersistentVolumeClaims (results volume)
4. Optionally: fp-tree namespace

**What it preserves:**
- Docker image (fp-tree-ids:latest)
- Extracted results (if already copied)
- Kubernetes config files (k8s/*.yaml)
- Source code

---

## 🔄 Typical Workflow

### Initial Deployment
```powershell
# Already done in your case:
# 1. Build Docker image
# 2. Deploy to Kubernetes
# 3. Verify pods are running
```

### Monitoring Phase
```powershell
# Check status periodically
.\check_status.ps1

# Or watch continuously
.\watch_experiments.ps1 -RefreshSeconds 20
```

### After Completion
```powershell
# 1. Verify completion
.\status_report.ps1

# 2. Extract results
.\extract_results.ps1

# 3. Archive for safekeeping
.\archive_results.ps1 -IncludeCode

# 4. Clean up Kubernetes
.\cleanup.ps1
```

### Re-running Experiments
```powershell
# Cleanup previous run
.\cleanup.ps1

# Re-deploy
kubectl apply -f k8s/results-pvc.yaml
kubectl apply -f k8s/job.yaml
kubectl apply -f k8s/synthetic-job.yaml

# Monitor new run
.\watch_experiments.ps1
```

## 📊 Kubernetes Commands Reference

### Pod Management
```powershell
# List all pods
kubectl get pods -n fp-tree

# Watch pod status (auto-refresh)
kubectl get pods -n fp-tree -w

# Describe specific pod
kubectl describe pod -n fp-tree <pod-name>

# Delete specific pod
kubectl delete pod -n fp-tree <pod-name>
```

### Logs
```powershell
# View logs
kubectl logs -n fp-tree <pod-name>

# Follow logs (real-time)
kubectl logs -f -n fp-tree <pod-name>

# Last N lines
kubectl logs -n fp-tree <pod-name> --tail=50

# Previous container logs (if restarted)
kubectl logs -n fp-tree <pod-name> --previous
```

### Jobs
```powershell
# List jobs
kubectl get jobs -n fp-tree

# Describe job
kubectl describe job -n fp-tree <job-name>

# Delete job
kubectl delete job -n fp-tree <job-name>
```

### Resources
```powershell
# View all resources in namespace
kubectl get all -n fp-tree

# View PVCs
kubectl get pvc -n fp-tree

# View detailed resource usage
kubectl top pods -n fp-tree
```

## 🐛 Troubleshooting

### Docker Desktop Issues
```powershell
# Check if Docker is running
docker ps

# Restart Docker Desktop
# Use Docker Desktop GUI: Settings > Restart
```

### Kubernetes Connection Issues
```powershell
# Test connection
kubectl cluster-info

# Check context
kubectl config current-context

# If needed, switch to docker-desktop context
kubectl config use-context docker-desktop
```

### Pod Failures
```powershell
# Check pod events
kubectl describe pod -n fp-tree <pod-name>

# Check logs for errors
kubectl logs -n fp-tree <pod-name> | Select-String -Pattern "error|failed|exception"

# Check previous logs if crashed
kubectl logs -n fp-tree <pod-name> --previous
```

### Resource Issues
```powershell
# Check node resources
kubectl describe nodes

# Check pod resource requests vs limits
kubectl describe pod -n fp-tree <pod-name> | Select-String -Pattern "Requests|Limits"
```

### Results Extraction Failures
```powershell
# Verify pod is still running or succeeded
kubectl get pods -n fp-tree

# Manually copy specific files
kubectl cp fp-tree/<pod-name>:/app/results/specific-file.txt ./local-file.txt

# Check what's in the pod
kubectl exec -n fp-tree <pod-name> -- ls -la /app/results
```

## 📝 Notes

- **Timing:** Main experiment takes 4-5 hours, synthetic takes 2-3 hours
- **Resources:** Ensure sufficient CPU and memory available in Docker Desktop
- **Persistence:** Results are lost if not extracted before cleanup
- **Logs:** Pod logs are automatically saved during extraction
- **Archives:** Keep timestamped archives for reproducibility

## 🆘 Getting Help

If experiments fail or behave unexpectedly:

1. Run `.\status_report.ps1` for comprehensive diagnostics
2. Check pod logs: `kubectl logs -n fp-tree <pod-name>`
3. Review pod events: `kubectl describe pod -n fp-tree <pod-name>`
4. Ensure Docker Desktop has sufficient resources allocated
5. Verify Kubernetes is fully initialized (green status in Docker Desktop)

## 📧 Support

For issues related to:
- FP-Tree algorithm: See main repository README
- Kubernetes deployment: Check k8s/ directory READMEs
- Docker builds: Review Dockerfile and build logs
- Dataset issues: Verify CIC-IDS2017 dataset integrity

---

**Last Updated:** 2025-10-17
**Version:** 1.0
**Author:** FP-Tree IDS Research Team
